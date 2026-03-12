import json
import logging
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
        if not self.rag_system.index: # Check if index is loaded/system ready
             # In app.py it checked system_ready global. 
             # Here we assume rag_system has a way to check, or we check if index is None
             # But persistent_storage.py initializes index to None.
             # We might need to expose system_ready or check rag_system.index
             pass

        self.logger.info(f"收到问答请求: {question[:100]}")

        start_time = time.time()

        # 0. 查询扩展
        query_expansion = self.query_expander.expand_query(question)
        expanded_query = query_expansion['search_query'] if query_expansion['expanded_terms'] else question
        
        if query_expansion['matched_concepts']:
            print(f"[查询扩展] 匹配概念: {query_expansion['matched_concepts']}")

        # 1. 检索文本块
        retriever = self.rag_system.index.as_retriever(similarity_top_k=max_results)
        retrieved_chunks = retriever.retrieve(expanded_query)
        
        if not retrieved_chunks:
            end_time = time.time()
            return self._create_empty_response(question, start_time, end_time)

        # 2. 过滤
        filtered_chunks = []
        for chunk in retrieved_chunks:
            if not getattr(chunk, 'text', None):
                continue
            chunk_score = float(chunk.score) if hasattr(chunk, 'score') else 0.0
            if chunk_score >= similarity_threshold:
                filtered_chunks.append(chunk)
        
        if len(filtered_chunks) == 0 and len(retrieved_chunks) > 0:
            filtered_chunks = retrieved_chunks[:config.RAG_FORCE_MIN_DOCS]

        # 4. 按文献去重
        unique_papers_dict = self._deduplicate_chunks(filtered_chunks)
        unique_papers_list = sorted(
            unique_papers_dict.values(), 
            key=lambda paper: paper['max_score'], 
            reverse=True
        )

        # 5. 构建参考文献列表
        references_raw = self._build_references_raw(unique_papers_list)

        # 5.5 证据分级
        references_ranked = self.evidence_ranker.rank_papers(references_raw)
        
        # 重新排序
        for ref in references_ranked:
            ref['final_score'] = ref['score'] * 0.6 + (ref['total_score'] / 5.0) * 0.4
        
        references_ranked.sort(key=lambda x: x['final_score'], reverse=True)
        
        references = []
        for idx, ref in enumerate(references_ranked, 1):
            ref['ref_id'] = f'ref_{idx}'
            references.append(ref)

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
            'references': references,
            'timestamp': datetime.now().isoformat(),
            'response_time': round(end_time - start_time, 2)
        }
        self.conversations.append(conversation)

        return {
            'success': True,
            'answer': answer,
            'references': references,
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
        try:
            yield f"data: {json.dumps({'type': 'start', 'message': '开始检索文献...'}, ensure_ascii=False)}\n\n"
            
            # 查询扩展
            query_expansion = self.query_expander.expand_query(question)
            expanded_query = query_expansion['search_query'] if query_expansion['expanded_terms'] else question
            
            yield f"data: {json.dumps({'type': 'status', 'message': '正在检索相关文献...'}, ensure_ascii=False)}\n\n"
            
            retriever = self.rag_system.index.as_retriever(similarity_top_k=max_results)
            retrieved_chunks = retriever.retrieve(expanded_query)
            
            if not retrieved_chunks:
                yield f"data: {json.dumps({'type': 'references', 'references': []}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'answer_start'}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'answer', 'content': '未检索到相关文献，请尝试更具体的关键词或降低相似度阈值。'}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                return

            # 过滤
            filtered_chunks = []
            for chunk in retrieved_chunks:
                if not getattr(chunk, 'text', None):
                    continue
                if float(chunk.score) >= similarity_threshold:
                    filtered_chunks.append(chunk)
            
            if len(filtered_chunks) == 0 and len(retrieved_chunks) > 0:
                valid_chunks = [c for c in retrieved_chunks if getattr(c, 'text', None)]
                if valid_chunks:
                    filtered_chunks = valid_chunks[:config.RAG_FORCE_MIN_DOCS]
            
            yield f"data: {json.dumps({'type': 'status', 'message': f'找到 {len(filtered_chunks)} 个相关文本块'}, ensure_ascii=False)}\n\n"
            
            # 去重
            unique_papers_dict = self._deduplicate_chunks(filtered_chunks)
            unique_papers_list = sorted(unique_papers_dict.values(), key=lambda paper: paper['max_score'], reverse=True)
            
            yield f"data: {json.dumps({'type': 'status', 'message': f'去重后找到 {len(unique_papers_list)} 篇唯一文献'}, ensure_ascii=False)}\n\n"
            
            # 构建参考文献
            references_raw = self._build_references_raw(unique_papers_list)
            
            # 证据分级
            references_ranked = self.evidence_ranker.rank_papers(references_raw)
            for ref in references_ranked:
                ref['final_score'] = ref['score'] * 0.6 + (ref['total_score'] / 5.0) * 0.4
            references_ranked.sort(key=lambda x: x['final_score'], reverse=True)
            
            references = []
            for idx, ref in enumerate(references_ranked, 1):
                ref['ref_id'] = f'ref_{idx}'
                references.append(ref)
            
            # 发送参考文献
            references_for_frontend = [
                {
                    'ref_id': ref['ref_id'],
                    'title': ref.get('title', ref.get('filename', 'Unknown')),
                    'journal': ref.get('journal', 'Unknown'),
                    'year': ref.get('year', 'N/A'),
                    'authors': ref.get('authors', []),
                    'doi': ref.get('doi', 'Not Available'),
                    'filename': ref.get('filename', ''),
                    'score': ref.get('final_score', 0)
                }
                for ref in references
            ]
            yield f"data: {json.dumps({'type': 'references', 'references': references_for_frontend}, ensure_ascii=False)}\n\n"
            
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

            for delta in self.llm_client.stream_chat(messages, temperature=0.6, max_tokens=2000):
                if delta.reasoning_content:
                    if not reasoning_started:
                        yield f"data: {json.dumps({'type': 'reasoning_start'}, ensure_ascii=False)}\n\n"
                        reasoning_started = True
                    yield f"data: {json.dumps({'type': 'reasoning', 'content': delta.reasoning_content}, ensure_ascii=False)}\n\n"

                if delta.content:
                    if not answer_started:
                        if reasoning_started:
                            yield f"data: {json.dumps({'type': 'reasoning_end'}, ensure_ascii=False)}\n\n"
                        yield f"data: {json.dumps({'type': 'references', 'references': references}, ensure_ascii=False)}\n\n"
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
            'response_time': conversation['response_time']
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

【参考文献内容】：
{context}

【问题】：{question}

请用中文回答，结构清晰，在重要观点后标注文献来源。"""

    def _call_llm(self, prompt, references) -> Tuple[str, Optional[str]]:
        messages = [
            {"role": "system", "content": f"你是甜味科学领域的专业知识系统。重要：你只能引用ref_1到ref_{len(references)}这{len(references)}篇文献，不要使用其他编号。"},
            {"role": "user", "content": prompt},
        ]
        
        # Retry logic could be here, but for brevity simplifying
        answer, reasoning = self.llm_client.chat(messages, temperature=0.6, max_tokens=2000)
        
        valid_ref_ids = {ref['ref_id'] for ref in references}
        
        def remove_invalid_ref(match):
            ref_num = match.group(1)
            return match.group(0) if f'ref_{ref_num}' in valid_ref_ids else ''

        answer = re.sub(r'\[ref_(\d+)\]', remove_invalid_ref, answer)
        if reasoning:
            reasoning = re.sub(r'\[ref_(\d+)\]', remove_invalid_ref, reasoning)

        if reasoning and len(reasoning.strip()) > 0:
            answer = f"<details><summary>思维链（点击展开）</summary>\n\n{reasoning}\n\n</details>\n\n---\n\n{answer}"
            
        return answer, reasoning
