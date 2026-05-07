import json
import logging
import os
import re
import time
import traceback
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, Tuple

from config import config
from services.llm_client import DeepSeekLLMClient

class ChatService:
    def __init__(
        self,
        rag_system: Any,
        query_expander: Any,
        evidence_ranker: Any,
        llm_client: Optional[DeepSeekLLMClient],
    ):
        self.logger = logging.getLogger("sweetseek.chat_service")
        self.rag_system = rag_system
        self.query_expander = query_expander
        self.evidence_ranker = evidence_ranker
        self.llm_client = llm_client
        self.conversations: List[Dict[str, Any]] = []
        self.qa_max_tokens = int(os.getenv("QA_MAX_TOKENS", "1200"))
        self.show_reasoning = os.getenv("QA_SHOW_REASONING", "false").lower() == "true"
        self.disable_reasoning_hard = os.getenv("QA_DISABLE_REASONING_HARD", "true").lower() == "true"
        self.retrieval_target_min = int(os.getenv("RETRIEVAL_TARGET_MIN", "8"))
        self.retrieval_target_max = int(os.getenv("RETRIEVAL_TARGET_MAX", "20"))
        self.retrieval_min_threshold = float(os.getenv("RETRIEVAL_MIN_THRESHOLD", "0.12"))
        self.retrieval_threshold_step = float(os.getenv("RETRIEVAL_THRESHOLD_STEP", "0.05"))
        self.retrieval_max_top_k = int(os.getenv("RETRIEVAL_MAX_TOP_K", str(config.RAG_MAX_RESULTS)))
        self.max_chunks_per_paper = int(os.getenv("RETRIEVAL_MAX_CHUNKS_PER_PAPER", "3"))

    def get_conversations(self) -> List[Dict[str, Any]]:
        return self.conversations

    def clear_conversations(self) -> None:
        self.conversations = []

    def ask(
        self,
        question: str,
        similarity_threshold: float = config.RAG_SIMILARITY_THRESHOLD,
        max_results: int = config.RAG_MAX_RESULTS,
    ) -> Dict[str, Any]:
        """
        处理问答请求
        """
        if not self.rag_system or not getattr(self.rag_system, "index", None):
            return {
                "success": False,
                "error": "知识库未初始化或数据缺失，请联系管理员或稍后重试。"
            }

        self.logger.info(f"收到问答请求: {question[:100]}")

        start_time = time.time()

        # 0. 查询扩展
        query_expansion = self.query_expander.expand_query(question)
        expanded_query = query_expansion['search_query'] if query_expansion['expanded_terms'] else question
        
        if query_expansion['matched_concepts']:
            print(f"[查询扩展] 匹配概念: {query_expansion['matched_concepts']}")

        retrieval = self._retrieve_references(expanded_query, similarity_threshold, max_results, question)

        if not retrieval["retrieved_chunks"]:
            end_time = time.time()
            return self._create_empty_response(question, start_time, end_time)

        unique_papers_dict = retrieval["unique_papers_dict"]
        references = retrieval["references"]

        # 6. 构建上下文和提示词
        context = self._build_context(references, unique_papers_dict, config.RAG_CONTEXT_WINDOW)
        prompt = self._build_prompt(references, context, question)

        # 调用 LLM
        answer = None
        reasoning = None
        
        if self.llm_client:
            try:
                answer, reasoning = self._call_llm(prompt, references)
            except Exception as e:
                self.logger.error(f"LLM调用失败: {e}")
                answer = f"抱歉，DeepSeek服务当前繁忙或出错，请稍后再试。\n\n基于检索到的文档，我可以提供以下参考信息：\n\n{context[:500]}..."
        else:
            answer = "DeepSeek API 未配置，无法生成回答。"

        end_time = time.time()
        
        # 保存对话
        conversation = {
            'id': len(self.conversations) + 1,
            'question': question,
            'answer': answer,
            'references': self._format_references_for_frontend(references),
            'references_raw': references,
            'retrieval_stats': retrieval["stats"],
            'retrieval_warning': retrieval["warning"],
            'timestamp': datetime.now().isoformat(),
            'response_time': round(end_time - start_time, 2)
        }
        self.conversations.append(conversation)

        return {
            'success': True,
            'answer': answer,
            'references': self._format_references_for_frontend(references),
            'retrieval_stats': retrieval["stats"],
            'retrieval_warning': retrieval["warning"],
            'response_time': conversation['response_time']
        }

    def ask_stream(
        self,
        question: str,
        similarity_threshold: float = config.RAG_SIMILARITY_THRESHOLD,
        max_results: int = config.RAG_MAX_RESULTS,
    ) -> Generator[str, None, None]:
        """
        流式问答
        """
        if not self.rag_system or not getattr(self.rag_system, "index", None):
            yield f"data: {json.dumps({'type': 'error', 'error': '知识库未初始化或数据缺失，请联系管理员或稍后重试。'}, ensure_ascii=False)}\n\n"
            return
        try:
            yield f"data: {json.dumps({'type': 'start', 'message': '开始检索文献...'}, ensure_ascii=False)}\n\n"
            
            # 查询扩展
            query_expansion = self.query_expander.expand_query(question)
            expanded_query = query_expansion['search_query'] if query_expansion['expanded_terms'] else question
            
            yield f"data: {json.dumps({'type': 'status', 'message': '正在检索相关文献...'}, ensure_ascii=False)}\n\n"
            
            retrieval = self._retrieve_references(expanded_query, similarity_threshold, max_results, question)
            retrieved_chunks = retrieval["retrieved_chunks"]
            
            if not retrieved_chunks:
                yield f"data: {json.dumps({'type': 'references', 'references': []}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'retrieval_stats', 'stats': self._empty_retrieval_stats(), 'warning': '未检索到相关文献'}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'answer_start'}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'answer', 'content': '未检索到相关文献，请尝试更具体的关键词或降低相似度阈值。'}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                return

            unique_papers_dict = retrieval["unique_papers_dict"]
            references = retrieval["references"]
            stats = retrieval["stats"]
            filtered_count = stats["after_threshold"]
            unique_count = stats["unique_papers"]

            yield f"data: {json.dumps({'type': 'status', 'message': f'找到 {filtered_count} 个相关文本块'}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'status', 'message': f'去重后找到 {unique_count} 篇唯一文献'}, ensure_ascii=False)}\n\n"
            
            # 发送参考文献
            references_for_frontend = []
            import math
            for ref in references:
                item = {
                    'ref_id': ref['ref_id'],
                    'title': ref.get('title', ref.get('filename', 'Unknown')),
                    'journal': ref.get('journal', 'Unknown'),
                    'year': ref.get('year', 'N/A'),
                    'authors': ref.get('authors', []),
                    'doi': ref.get('doi', 'Not Available'),
                    'filename': ref.get('filename', '')
                }
                # 安全处理 score
                try:
                    score_val = float(ref.get('final_score', ref.get('score', 0)) or 0)
                    if not math.isfinite(score_val):
                        score_val = 0.0
                except (ValueError, TypeError):
                    score_val = 0.0
                item['score'] = score_val
                references_for_frontend.append(item)

            yield f"data: {json.dumps({'type': 'references', 'references': references_for_frontend}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'retrieval_stats', 'stats': retrieval['stats'], 'warning': retrieval['warning']}, ensure_ascii=False)}\n\n"
            
            yield f"data: {json.dumps({'type': 'status', 'message': '正在生成答案...'}, ensure_ascii=False)}\n\n"
            
            # 构建上下文 (Max 12000 chars for stream)
            context = self._build_context(references, unique_papers_dict, 12000)
            prompt = self._build_prompt(references, context, question)
            
            if not self.llm_client:
                yield f"data: {json.dumps({'type': 'error', 'error': 'DeepSeek API 未配置，无法生成回答。'}, ensure_ascii=False)}\n\n"
                return

            messages = [
                {"role": "system", "content": f"你是甜味科学领域的专业知识系统。重要：你只能引用ref_1到ref_{len(references)}这{len(references)}篇文献，不要使用其他编号。"},
                {"role": "user", "content": prompt},
            ]

            reasoning_started = False
            answer_started = False
            content_buffer = ""
            BUFFER_SIZE = 5

            for delta in self.llm_client.stream_chat(messages, temperature=0.6, max_tokens=self.qa_max_tokens):
                if (not self.disable_reasoning_hard) and delta.reasoning_content:
                    if not reasoning_started:
                        yield f"data: {json.dumps({'type': 'reasoning_start'}, ensure_ascii=False)}\n\n"
                        reasoning_started = True
                    yield f"data: {json.dumps({'type': 'reasoning', 'content': delta.reasoning_content}, ensure_ascii=False)}\n\n"

                if delta.content:
                    if not answer_started:
                        if reasoning_started:
                            yield f"data: {json.dumps({'type': 'reasoning_end'}, ensure_ascii=False)}\n\n"
                        yield f"data: {json.dumps({'type': 'answer_start'}, ensure_ascii=False)}\n\n"
                        answer_started = True
                    
                    content_buffer += delta.content
                    if len(content_buffer) >= BUFFER_SIZE:
                        yield f"data: {json.dumps({'type': 'answer', 'content': content_buffer}, ensure_ascii=False)}\n\n"
                        content_buffer = ""
            
            if content_buffer:
                yield f"data: {json.dumps({'type': 'answer', 'content': content_buffer}, ensure_ascii=False)}\n\n"
            
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"

    def _create_empty_response(self, question, start_time, end_time):
        conversation = {
            'id': len(self.conversations) + 1,
            'question': question,
            'answer': '未检索到相关文献，请尝试更具体的关键词或降低相似度阈值。',
            'references': [],
            'timestamp': datetime.now().isoformat(),
            'response_time': round(end_time - start_time, 2)
        }
        self.conversations.append(conversation)
        return {
            'success': True,
            'answer': conversation['answer'],
            'references': [],
            'retrieval_stats': self._empty_retrieval_stats(),
            'retrieval_warning': '未检索到相关文献',
            'response_time': conversation['response_time']
        }

    def _retrieve_references(self, query: str, similarity_threshold: float, max_results: int, original_query: str = "") -> Dict[str, Any]:
        top_k = min(max(1, int(max_results), self.retrieval_max_top_k), 200)
        retriever = self.rag_system.index.as_retriever(similarity_top_k=top_k)
        retrieved_chunks = retriever.retrieve(query)
        valid_chunks = [chunk for chunk in retrieved_chunks if getattr(chunk, 'text', None)]

        threshold = float(similarity_threshold)
        filtered_chunks = self._filter_chunks(valid_chunks, threshold)
        selected_chunks = self._diversify_chunks(filtered_chunks)
        unique_papers_dict = self._deduplicate_chunks(selected_chunks)

        while len(unique_papers_dict) < self.retrieval_target_min and threshold > self.retrieval_min_threshold:
            threshold = max(self.retrieval_min_threshold, threshold - self.retrieval_threshold_step)
            filtered_chunks = self._filter_chunks(valid_chunks, threshold)
            selected_chunks = self._diversify_chunks(filtered_chunks)
            unique_papers_dict = self._deduplicate_chunks(selected_chunks)

        if len(unique_papers_dict) < self.retrieval_target_min and valid_chunks:
            selected_chunks = self._diversify_chunks(valid_chunks)
            unique_papers_dict = self._deduplicate_chunks(selected_chunks)

        if not selected_chunks and valid_chunks:
            selected_chunks = self._diversify_chunks(valid_chunks[:config.RAG_FORCE_MIN_DOCS])
            unique_papers_dict = self._deduplicate_chunks(selected_chunks)

        unique_papers_list = sorted(unique_papers_dict.values(), key=lambda paper: paper['max_score'], reverse=True)
        references = self._rank_references(unique_papers_list)
        references = self._apply_topic_boundary(references, original_query)
        if len(references) > self.retrieval_target_max:
            references = references[:self.retrieval_target_max]
            keep_paths = {ref['file_path'] for ref in references}
            unique_papers_dict = {path: info for path, info in unique_papers_dict.items() if path in keep_paths}

        stats = {
            'raw_chunks': len(retrieved_chunks),
            'valid_chunks': len(valid_chunks),
            'after_threshold': len(filtered_chunks),
            'selected_chunks': len(selected_chunks),
            'unique_papers': len(unique_papers_list),
            'final_references': len(references),
            'requested_threshold': float(similarity_threshold),
            'effective_threshold': threshold,
            'top_k': top_k,
            'max_chunks_per_paper': self.max_chunks_per_paper,
        }
        warning = self._build_retrieval_warning(references, original_query)

        return {
            'retrieved_chunks': retrieved_chunks,
            'selected_chunks': selected_chunks,
            'unique_papers_dict': unique_papers_dict,
            'references': references,
            'stats': stats,
            'warning': warning,
        }

    def _extract_topic_tokens(self, query: str) -> List[str]:
        """提取查询中的主题词（中英文），用于弱约束的主题相关性判断。"""
        query_text = (query or "").strip().lower()
        if not query_text:
            return []
        query_text = re.sub(r"(如何|怎么|是什么|是怎样|请问|有关|相关|机制|机理)", " ", query_text)

        english_tokens = re.findall(r"[a-z][a-z0-9+._-]{2,}", query_text)
        chinese_chunks = re.findall(r"[\u4e00-\u9fff]{2,}", query_text)
        stopwords = {"如何", "怎么", "什么", "为何", "请问", "是否", "以及", "关于", "之间", "机制", "作用", "结合"}

        tokens = set(english_tokens)
        for chunk in chinese_chunks:
            for part in re.split(r"[和与及或、在是的了呢吗吧将把对跟同]", chunk):
                part = part.strip()
                if len(part) >= 2 and part not in stopwords:
                    tokens.add(part)

        return sorted(tokens)

    def _reference_text(self, ref: Dict[str, Any]) -> str:
        return " ".join([
            str(ref.get("title", "")),
            str(ref.get("filename", "")),
            str(ref.get("content", "")),
            " ".join(str(x) for x in ref.get("authors", []) if x),
        ]).lower()

    def _apply_topic_boundary(self, references: List[Dict[str, Any]], original_query: str) -> List[Dict[str, Any]]:
        """主题约束：优先保留主题命中的文献；若命中不足则回退到原结果，避免误清空。"""
        if not references:
            return references

        topic_tokens = self._extract_topic_tokens(original_query)
        if not topic_tokens:
            return references

        matched_refs = []
        unmatched_refs = []
        for ref in references:
            ref_text = self._reference_text(ref)
            if any(token in ref_text for token in topic_tokens):
                matched_refs.append(ref)
            else:
                unmatched_refs.append(ref)

        # 不再硬过滤为空：命中不足时保留原排序，防止“明明检索到了却无文献”。
        min_keep = max(1, int(os.getenv("TOPIC_BOUNDARY_MIN_KEEP", "3")))
        if len(matched_refs) >= min_keep:
            merged = matched_refs + unmatched_refs
        elif matched_refs:
            merged = matched_refs + unmatched_refs
        else:
            merged = references

        for idx, ref in enumerate(merged, 1):
            ref["ref_id"] = f"ref_{idx}"
        return merged

    def _build_retrieval_warning(self, references: List[Dict[str, Any]], original_query: str) -> Optional[str]:
        warnings = []
        min_refs = max(1, int(os.getenv("RETRIEVAL_WARNING_MIN_REFS", "6")))
        if len(references) < min_refs:
            warnings.append("相关文献较少，请尝试英文名/缩写或补充语料。")

        topic_tokens = self._extract_topic_tokens(original_query)
        if topic_tokens and references:
            ref_text = " ".join(self._reference_text(ref) for ref in references)
            missed_tokens = [token for token in topic_tokens if token not in ref_text]
            if len(missed_tokens) == len(topic_tokens):
                sample = ", ".join(missed_tokens[:3])
                warnings.append(f"当前结果未发现与主题词直接匹配的文献（示例：{sample}），可尝试英文名/缩写或补充语料。")

        return " ".join(warnings) if warnings else None

    def _filter_chunks(self, chunks, threshold: float) -> List[Any]:
        filtered = []
        for chunk in chunks:
            try:
                score = float(chunk.score) if hasattr(chunk, 'score') else 0.0
            except (TypeError, ValueError):
                score = 0.0
            if score >= threshold:
                filtered.append(chunk)
        return filtered

    def _diversify_chunks(self, chunks) -> List[Any]:
        selected = []
        per_paper: Dict[str, int] = {}
        for chunk in chunks:
            metadata = getattr(chunk, 'metadata', {}) or {}
            paper_file_path = metadata.get('file_path') or metadata.get('file_name') or 'unknown'
            if per_paper.get(paper_file_path, 0) >= self.max_chunks_per_paper:
                continue
            selected.append(chunk)
            per_paper[paper_file_path] = per_paper.get(paper_file_path, 0) + 1
            if len(per_paper) >= self.retrieval_target_max and len(selected) >= self.retrieval_target_max:
                break
        return selected

    def _rank_references(self, unique_papers_list) -> List[Dict[str, Any]]:
        references_raw = self._build_references_raw(unique_papers_list)
        references_ranked = self.evidence_ranker.rank_papers(references_raw)
        for ref in references_ranked:
            ref['final_score'] = ref['score'] * 0.6 + (ref['total_score'] / 5.0) * 0.4
        references_ranked.sort(key=lambda x: x['final_score'], reverse=True)
        references = []
        for idx, ref in enumerate(references_ranked, 1):
            ref['ref_id'] = f'ref_{idx}'
            references.append(ref)
        return references

    def _empty_retrieval_stats(self) -> Dict[str, Any]:
        return {
            'raw_chunks': 0,
            'valid_chunks': 0,
            'after_threshold': 0,
            'selected_chunks': 0,
            'unique_papers': 0,
            'final_references': 0,
            'requested_threshold': None,
            'effective_threshold': None,
            'top_k': 0,
            'max_chunks_per_paper': self.max_chunks_per_paper,
        }

    def _deduplicate_chunks(self, chunks) -> Dict[str, Any]:
        unique_papers_dict = {}
        for chunk in chunks:
            paper_file_path = chunk.metadata.get('file_path', '')
            paper_filename = chunk.metadata.get('file_name', '未知文档')
            chunk_score = float(chunk.score) if hasattr(chunk, 'score') else 0.0
            
            if paper_file_path not in unique_papers_dict:
                unique_papers_dict[paper_file_path] = {
                    'file_path': paper_file_path,
                    'filename': paper_filename,
                    'max_score': chunk_score,
                    'chunks': [chunk],
                    'sample_content': chunk.text[:200] + '...' if len(chunk.text) > 200 else chunk.text
                }
            else:
                if chunk_score > unique_papers_dict[paper_file_path]['max_score']:
                    unique_papers_dict[paper_file_path]['max_score'] = chunk_score
                unique_papers_dict[paper_file_path]['chunks'].append(chunk)
        return unique_papers_dict

    def _format_references_for_frontend(self, references: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将内部 references 转换为前端期望的扁平化、类型安全的格式。"""
        out = []
        import math
        for ref in references:
            item = {
                'ref_id': ref.get('ref_id', 'ref_0'),
                'title': ref.get('title', ref.get('filename', 'Unknown')),
                'journal': ref.get('journal', 'Unknown'),
                'year': ref.get('year', 'N/A'),
                'authors': ref.get('authors', []) if isinstance(ref.get('authors', []), list) else [ref.get('authors')] if ref.get('authors') else [],
                'doi': ref.get('doi', 'Not Available'),
                'filename': ref.get('filename', ''),
                'score': 0.0,
            }
            try:
                v = float(ref.get('final_score', ref.get('score', 0) or 0))
            except Exception:
                v = 0.0
            if not math.isfinite(v):
                v = 0.0
            item['score'] = v
            out.append(item)
        return out

    def _build_references_raw(self, unique_papers_list) -> List[Dict[str, Any]]:
        references_raw = []
        for paper_index, paper_info in enumerate(unique_papers_list, 1):
            file_path = paper_info['file_path']
            # Convert to relative path if needed, similar to app.py logic if required
            # But here we rely on file_path being consistent with metadata storage
            
            paper_metadata = self.rag_system.metadata_storage.get_metadata(file_path) if file_path else None
            
            if paper_metadata:
                references_raw.append({
                    'ref_id': f'ref_{paper_index}', # Temporary ID
                    'journal': paper_metadata.get('journal', 'Unknown Journal'),
                    'year': paper_metadata.get('year', 'N/A'),
                    'title': paper_metadata.get('title', 'Unknown Title'),
                    'authors': paper_metadata.get('authors', []),
                    'doi': paper_metadata.get('doi', 'Not Available'),
                    'filename': paper_info['filename'],
                    'file_path': paper_info['file_path'],
                    'score': paper_info['max_score'],
                    'content': paper_info['sample_content']
                })
            else:
                is_dataset = 'datasets' in file_path.lower() or 'dataset' in paper_info['filename'].lower()
                references_raw.append({
                    'ref_id': f'ref_{paper_index}',
                    'journal': '营养数据集' if is_dataset else 'Unknown',
                    'year': 'N/A',
                    'title': paper_info['filename'],
                    'authors': [],
                    'doi': 'Not Available',
                    'filename': paper_info['filename'],
                    'file_path': paper_info['file_path'],
                    'score': paper_info['max_score'],
                    'content': paper_info['sample_content']
                })
        return references_raw

    def _build_context(self, references, unique_papers_dict, max_context_length) -> str:
        numbered_context_chunks = []
        total_length = 0
        
        for ref in references:
            ref_file_path = ref['file_path']
            ref_id = ref['ref_id']
            
            if ref_file_path in unique_papers_dict:
                paper_chunks = unique_papers_dict[ref_file_path]['chunks']
                
                for chunk in paper_chunks:
                    chunk_text = chunk.text
                    chunk_text = re.sub(r'\[\d+\]', '', chunk_text)
                    chunk_text = re.sub(r'\[CrossRef\]|\[PubMed\]|\[Google Scholar\]', '', chunk_text, flags=re.IGNORECASE)
                    chunk_text = re.sub(r'^\d+\.\s+', '', chunk_text, flags=re.MULTILINE)
                    chunk_text = re.sub(r'\s+', ' ', chunk_text).strip()
                    
                    if total_length + len(chunk_text) > max_context_length:
                        break
                    
                    numbered_chunk = f"[{ref_id}] {chunk_text}"
                    numbered_context_chunks.append(numbered_chunk)
                    total_length += len(chunk_text)
                
                if total_length >= max_context_length:
                    break
        
        return "\n\n".join(numbered_context_chunks)

    def _build_prompt(self, references, context, question) -> str:
        ref_list_summary = "\n".join([
            f"{ref['ref_id']}: {ref.get('title', ref['filename'])} ({ref.get('journal', 'Unknown')}, {ref.get('year', 'N/A')})"
            for ref in references
        ])
        
        return f"""你是甜味科学领域的专业知识系统。请基于以下参考文献回答问题。

【参考文献列表】（共{len(references)}篇，编号为ref_1到ref_{len(references)}）：
{ref_list_summary}

【重要】：
- 只能使用ref_1到ref_{len(references)}这些编号
- 在回答的关键信息后用[ref_X]或[ref_X, ref_Y]标注来源
- 不要引用任何其他编号
- 只输出最终答案，不要输出思维链、推理过程、分析过程或自我说明

【参考文献内容】：
{context}

【问题】：{question}

请用中文回答，结构清晰，在重要观点后标注文献来源。"""

    def _call_llm(self, prompt, references) -> Tuple[str, Optional[str]]:
        messages = [
            {"role": "system", "content": f"你是甜味科学领域的专业知识系统。重要：你只能引用ref_1到ref_{len(references)}这{len(references)}篇文献，不要使用其他编号。只输出最终答案，不要输出思维链、推理过程、分析过程或自我说明。"},
            {"role": "user", "content": prompt},
        ]
        
        # Retry logic could be here, but for brevity simplifying
        answer, reasoning = self.llm_client.chat(messages, temperature=0.6, max_tokens=self.qa_max_tokens)
        
        valid_ref_ids = {ref['ref_id'] for ref in references}

        def clean_ref_brackets(text: str) -> str:
            if not text:
                return text
            if not valid_ref_ids:
                return re.sub(r'\[ref_\d+(?:\s*,\s*ref_\d+)*\]', '', text)

            def _normalize(match):
                content = match.group(1)
                parts = [part.strip() for part in content.split(",")]
                kept = [part for part in parts if part in valid_ref_ids]
                if not kept:
                    return ""
                return "[" + ", ".join(kept) + "]"

            text = re.sub(r'\[((?:ref_\d+\s*,\s*)*ref_\d+)\]', _normalize, text)
            text = re.sub(r'\s{2,}', ' ', text)
            return text

        answer = clean_ref_brackets(answer)
        if reasoning:
            reasoning = clean_ref_brackets(reasoning)

        if self.show_reasoning and (not self.disable_reasoning_hard) and reasoning and len(reasoning.strip()) > 0:
            answer = f"<details><summary>思维链（点击展开）</summary>\n\n{reasoning}\n\n</details>\n\n---\n\n{answer}"
        if self.disable_reasoning_hard:
            answer = re.sub(r"<details><summary>思维链（点击展开）</summary>[\s\S]*?</details>\s*---\s*", "", answer, flags=re.IGNORECASE)
            
        return answer, reasoning
