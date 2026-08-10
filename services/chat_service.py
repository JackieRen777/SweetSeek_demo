import json
import logging
import os
import re
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

from config import config, sweet_rag_config, dual_rag_config, RAGConfig
from path_utils import normalize_for_storage
from services.llm_client import DeepSeekLLMClient
from services.sweetness_prediction_service import get_sweetness_prediction_service
from services.encapsulation_references import serialize_encapsulation_references

class ChatService:
    def __init__(
        self,
        rag_system: Any,
        query_expander: Any,
        evidence_ranker: Any,
        llm_client: Optional[DeepSeekLLMClient],
        mode: str = "main",
    ):
        self.logger = logging.getLogger("sweetseek.chat_service")
        self.rag_system = rag_system
        self.query_expander = query_expander
        self.evidence_ranker = evidence_ranker
        self.llm_client = llm_client
        self.mode = mode
        self.conversations: List[Dict[str, Any]] = []

        rc: RAGConfig = dual_rag_config if mode == "dual" else sweet_rag_config
        self.qa_max_tokens = rc.qa_max_tokens
        self.retrieval_target_min = rc.target_min
        self.retrieval_target_max = rc.target_max
        self.retrieval_min_threshold = rc.min_threshold
        self.retrieval_threshold_step = rc.threshold_step
        self.retrieval_max_top_k = rc.max_top_k
        self.retrieval_hard_top_k = rc.hard_top_k
        self.max_chunks_per_paper = rc.max_chunks_per_paper
        self.context_window = rc.context_window
        self.show_reasoning = rc.show_reasoning
        self.disable_reasoning_hard = rc.disable_reasoning_hard

        self._metadata_index_cache: Dict[str, Any] = {
            "size": -1,
            "by_path": {},
            "by_filename": {},
        }
        focus_file = os.getenv("DUAL_FOCUS_FILELIST", "./data/dual_focus_quinoa_soy_files.txt")
        self.dual_focus_files = self._load_focus_filelist(focus_file) if self.mode == "dual" else set()

        # Sweetness prediction service (lazy-loaded on first SMILES detection)
        self.sweetness_service = get_sweetness_prediction_service()

    def get_conversations(self) -> List[Dict[str, Any]]:
        return self.conversations

    def clear_conversations(self) -> None:
        self.conversations = []

    def _load_focus_filelist(self, path: str) -> set:
        out = set()
        try:
            p = Path(path)
            if not p.exists():
                return out
            for line in p.read_text(encoding="utf-8").splitlines():
                item = line.strip()
                if not item or item.startswith("#"):
                    continue
                out.add(normalize_for_storage(item))
            return out
        except Exception:
            return set()

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
        context = self._build_context(references, unique_papers_dict, self.context_window)
        prompt = self._build_prompt(references, context, question)

        # 调用 LLM
        answer = None
        reasoning = None
        
        if self.llm_client:
            try:
                answer, reasoning = self._call_llm(prompt, references)
                answer = self._augment_answer(answer, references)
            except Exception as e:
                self.logger.error(f"LLM调用失败: {e}")
                answer = f"抱歉，DeepSeek服务当前繁忙或出错，请稍后再试。\n\n基于检索到的文档，我可以提供以下参考信息：\n\n{context[:500]}..."
        else:
            answer = "DeepSeek API 未配置，无法生成回答。"

        # Augment answer with sweetness prediction if SMILES detected
        ml_prediction = None
        if self.mode == "main":  # Only for main RAG, not dual-protein
            try:
                answer, ml_prediction = self.sweetness_service.augment_answer(question, answer)
            except Exception as e:
                self.logger.warning(f"Sweetness prediction failed: {e}")

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
            'ml_prediction': ml_prediction,  # Add ML prediction to conversation history
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
            'ml_prediction': ml_prediction,  # Include in API response
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
            
            # All research domains share the same normalized citation payload.
            references_for_frontend = serialize_encapsulation_references(references, unique_papers_dict)

            yield f"data: {json.dumps({'type': 'references', 'references': references_for_frontend}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'retrieval_stats', 'stats': retrieval['stats'], 'warning': retrieval['warning']}, ensure_ascii=False)}\n\n"
            
            yield f"data: {json.dumps({'type': 'status', 'message': '正在生成答案...'}, ensure_ascii=False)}\n\n"
            
            # 构建上下文
            context = self._build_context(references, unique_papers_dict, self.context_window)
            prompt = self._build_prompt(references, context, question)
            
            if not self.llm_client:
                yield f"data: {json.dumps({'type': 'error', 'error': 'DeepSeek API 未配置，无法生成回答。'}, ensure_ascii=False)}\n\n"
                return

            messages = [
                {"role": "system", "content": f"你是食品科学专业领域的专家。重要：你只能引用ref_1到ref_{len(references)}这{len(references)}篇文献，不要使用其他编号。"},
                {"role": "user", "content": prompt},
            ]

            reasoning_started = False
            answer_started = False
            content_buffer = ""
            answer_text = ""
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
                    answer_text += delta.content
                    if len(content_buffer) >= BUFFER_SIZE:
                        yield f"data: {json.dumps({'type': 'answer', 'content': content_buffer}, ensure_ascii=False)}\n\n"
                        content_buffer = ""
            
            if content_buffer:
                yield f"data: {json.dumps({'type': 'answer', 'content': content_buffer}, ensure_ascii=False)}\n\n"

            tail = self._build_answer_tail(answer_text, references)
            if tail:
                yield f"data: {json.dumps({'type': 'answer', 'content': tail}, ensure_ascii=False)}\n\n"
            
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
        query_signals = self._get_query_signals(original_query)
        target_min, target_max = self._adaptive_reference_window(original_query)
        top_k_goal = max(int(max_results), self.retrieval_max_top_k, target_max * 5)
        top_k = min(max(1, top_k_goal), self.retrieval_hard_top_k)
        query_variants = self._build_query_variants(query, original_query)
        retrieved_chunks = self._retrieve_chunks_multi_query(query_variants, top_k)
        valid_chunks = [chunk for chunk in retrieved_chunks if getattr(chunk, 'text', None)]

        threshold = float(similarity_threshold)
        filtered_chunks = self._filter_chunks(valid_chunks, threshold, query_signals)
        selected_chunks = self._diversify_chunks(filtered_chunks, target_max)
        unique_papers_dict = self._deduplicate_chunks(selected_chunks)

        while len(unique_papers_dict) < target_min and threshold > self.retrieval_min_threshold:
            threshold = max(self.retrieval_min_threshold, threshold - self.retrieval_threshold_step)
            filtered_chunks = self._filter_chunks(valid_chunks, threshold, query_signals)
            selected_chunks = self._diversify_chunks(filtered_chunks, target_max)
            unique_papers_dict = self._deduplicate_chunks(selected_chunks)

        if len(unique_papers_dict) < target_min and valid_chunks:
            selected_chunks = self._diversify_chunks(valid_chunks, target_max)
            unique_papers_dict = self._deduplicate_chunks(selected_chunks)

        if not selected_chunks and valid_chunks:
            selected_chunks = self._diversify_chunks(valid_chunks[:config.RAG_FORCE_MIN_DOCS], target_max)
            unique_papers_dict = self._deduplicate_chunks(selected_chunks)

        unique_papers_list = sorted(unique_papers_dict.values(), key=lambda paper: paper['max_score'], reverse=True)
        references = self._rank_references(unique_papers_list)
        references = self._apply_topic_boundary(references, original_query)
        references = self._supplement_references_to_floor(references, target_min, original_query)
        if len(references) > target_max:
            references = references[:target_max]
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
            'target_min_references': target_min,
            'target_max_references': target_max,
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

    def _build_query_variants(self, query: str, original_query: str) -> List[str]:
        variants: List[str] = []
        for candidate in [query, original_query]:
            c = (candidate or "").strip()
            if c and c not in variants:
                variants.append(c)

        if " OR " in query:
            first_seg = query.split(" OR ", 1)[0].strip()
            if first_seg and first_seg not in variants:
                variants.append(first_seg)

        topic_tokens = self._extract_topic_tokens(original_query)
        if topic_tokens:
            short = " ".join(topic_tokens[:3])
            if short and short not in variants:
                variants.append(short)
            if len(topic_tokens) >= 2:
                broad = f"{topic_tokens[0]} {topic_tokens[1]} 相互作用 机制"
                if broad not in variants:
                    variants.append(broad)
        return variants[:5]

    def _retrieve_chunks_multi_query(self, queries: List[str], top_k: int) -> List[Any]:
        if not queries:
            return []
        per_query_top_k = max(40, top_k // len(queries))
        merged: Dict[str, Any] = {}
        for q in queries:
            retriever = self.rag_system.index.as_retriever(similarity_top_k=per_query_top_k)
            for chunk in retriever.retrieve(q):
                metadata = getattr(chunk, 'metadata', {}) or {}
                file_path = metadata.get('file_path') or metadata.get('file_name') or ''
                chunk_text = getattr(chunk, 'text', '') or ''
                node_id = getattr(chunk, 'node_id', None) or getattr(getattr(chunk, 'node', None), 'node_id', None)
                key = str(node_id or f"{file_path}:{hash(chunk_text[:160])}")
                prev = merged.get(key)
                if prev is None:
                    merged[key] = chunk
                    continue
                prev_score = float(getattr(prev, 'score', 0) or 0)
                cur_score = float(getattr(chunk, 'score', 0) or 0)
                if cur_score > prev_score:
                    merged[key] = chunk
        merged_chunks = list(merged.values())
        merged_chunks.sort(key=lambda c: float(getattr(c, 'score', 0) or 0), reverse=True)
        return merged_chunks[:top_k]

    def _supplement_references_to_floor(
        self,
        references: List[Dict[str, Any]],
        target_min: int,
        original_query: str,
    ) -> List[Dict[str, Any]]:
        if len(references) >= target_min:
            return references
        metadata_all = self._get_all_metadata()
        if not metadata_all:
            return references
        signals = self._get_query_signals(original_query)
        existing_paths = {str(ref.get("file_path", "")) for ref in references}
        existing_titles = {str(ref.get("title", "")).lower() for ref in references}
        strong_candidates: List[Dict[str, Any]] = []
        weak_candidates: List[Dict[str, Any]] = []
        dual_focus_mode = self.dual_focus_files and self._is_dual_quinoa_soy_query(signals)

        items = metadata_all.items()
        for path, meta in items:
            title = str(meta.get("title", ""))
            filename = str(meta.get("filename", ""))
            journal = str(meta.get("journal", "Unknown Journal"))
            text = " ".join([title, filename, journal]).lower()
            overlap, concept_hits = self._reference_overlap_score(text, signals)
            if str(path) in existing_paths or title.lower() in existing_titles:
                continue

            candidate = {
                "ref_id": "ref_0",
                "journal": journal or "Unknown Journal",
                "year": str(meta.get("year", "N/A")),
                "title": title or filename or "Unknown Title",
                "authors": meta.get("authors", []) if isinstance(meta.get("authors", []), list) else [],
                "doi": str(meta.get("doi", "Not Available")),
                "filename": filename or os.path.basename(str(path)),
                "file_path": str(path),
                "score": 0.04 + 0.01 * overlap,
                "final_score": 0.04 + 0.01 * overlap,
                "content": "",
                "_overlap": overlap,
                "_concept_hits": concept_hits,
                "_focus": 1 if (dual_focus_mode and normalize_for_storage(str(path)) in self.dual_focus_files) else 0,
            }
            if candidate["_focus"] or overlap > 0 or concept_hits > 0:
                strong_candidates.append(candidate)
            else:
                weak_candidates.append(candidate)

        # 词面命中优先，其次按年份新近程度。
        def _year_val(v: str) -> int:
            m = re.search(r"(19|20)\d{2}", str(v))
            return int(m.group(0)) if m else 0

        strong_candidates.sort(key=lambda c: (c["_focus"], c["_concept_hits"], c["_overlap"], _year_val(c.get("year", "0"))), reverse=True)
        weak_candidates.sort(key=lambda c: _year_val(c.get("year", "0")), reverse=True)
        needed = max(0, target_min - len(references))
        if needed > 0:
            supplements: List[Dict[str, Any]] = []
            supplements.extend(strong_candidates[:needed])
            allow_weak = os.getenv("RETRIEVAL_ALLOW_WEAK_SUPPLEMENT", "true").lower() == "true"
            if self.mode == "dual":
                allow_weak = os.getenv("DUAL_RETRIEVAL_ALLOW_WEAK_SUPPLEMENT", "false").lower() == "true"
            if allow_weak and len(supplements) < needed:
                supplements.extend(weak_candidates[:needed - len(supplements)])
            references = references + supplements

        for idx, ref in enumerate(references, 1):
            ref["ref_id"] = f"ref_{idx}"
            ref.pop("_overlap", None)
            ref.pop("_concept_hits", None)
            ref.pop("_focus", None)
        return references

    def _get_all_metadata(self) -> Dict[str, Dict[str, Any]]:
        if not hasattr(self.rag_system, "metadata_storage"):
            return {}
        try:
            metadata_all = self.rag_system.metadata_storage.get_all_metadata()
        except Exception:
            return {}
        return metadata_all if isinstance(metadata_all, dict) else {}

    def _refresh_metadata_index(self) -> None:
        metadata_all = self._get_all_metadata()
        if not metadata_all:
            self._metadata_index_cache = {"size": 0, "by_path": {}, "by_filename": {}}
            return
        if self._metadata_index_cache.get("size", -1) == len(metadata_all):
            return

        by_path: Dict[str, Dict[str, Any]] = {}
        by_filename: Dict[str, Dict[str, Any]] = {}
        for path, meta in metadata_all.items():
            # Index by both the stored key and its normalized form
            path_key = str(Path(str(path)).as_posix())
            by_path[path_key] = meta
            rel_key = normalize_for_storage(path)
            by_path[rel_key] = meta

            filename = str(meta.get("filename", Path(path_key).name)).strip()
            if filename and filename not in by_filename:
                by_filename[filename] = meta

        self._metadata_index_cache = {
            "size": len(metadata_all),
            "by_path": by_path,
            "by_filename": by_filename,
        }

    def _lookup_metadata_fast(self, file_path: str) -> Optional[Dict[str, Any]]:
        self._refresh_metadata_index()
        by_path = self._metadata_index_cache.get("by_path", {})

        # Try normalized relative path
        rel_key = normalize_for_storage(file_path)
        if rel_key in by_path:
            return by_path[rel_key]

        # Try raw posix (backward compat)
        path_key = str(Path(file_path).as_posix())
        if path_key in by_path:
            return by_path[path_key]

        # Filename fallback
        filename = Path(file_path).name
        by_filename = self._metadata_index_cache.get("by_filename", {})
        if filename in by_filename:
            return by_filename[filename]
        return None

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

    def _normalize_signal_term(self, term: str) -> str:
        return (term or "").strip().lower()

    def _get_query_signals(self, query: str) -> Dict[str, Any]:
        base_tokens = self._extract_topic_tokens(query)
        terms = {self._normalize_signal_term(t) for t in base_tokens if len(self._normalize_signal_term(t)) >= 2}
        protein_concepts: List[str] = []
        matched_concepts_raw: List[str] = []
        concept_aliases: Dict[str, List[str]] = {}

        if self.query_expander and hasattr(self.query_expander, "expand_query"):
            try:
                expanded = self.query_expander.expand_query(query) or {}
                matched_concepts = expanded.get("matched_concepts", []) or []
                matched_concepts_raw = [str(c) for c in matched_concepts if str(c).strip()]
                expanded_terms = expanded.get("expanded_terms", []) or []
                for t in matched_concepts + expanded_terms:
                    t_norm = self._normalize_signal_term(str(t))
                    if len(t_norm) >= 2:
                        terms.add(t_norm)

                synonyms_dict = getattr(self.query_expander, "term_synonyms", {}) or {}
                for concept in matched_concepts:
                    concept_norm = self._normalize_signal_term(str(concept))
                    if not concept_norm:
                        continue
                    aliases = [concept_norm]
                    for syn in synonyms_dict.get(concept, []):
                        s = self._normalize_signal_term(str(syn))
                        if len(s) >= 2:
                            aliases.append(s)
                            terms.add(s)
                    concept_aliases[concept_norm] = sorted(set(aliases))
                    if ("蛋白" in concept_norm) or ("protein" in concept_norm):
                        protein_concepts.append(concept_norm)
            except Exception:
                pass

        return {
            "terms": sorted(t for t in terms if t),
            "protein_concepts": sorted(set(protein_concepts)),
            "matched_concepts_raw": matched_concepts_raw,
            "concept_aliases": concept_aliases,
        }

    def _reference_overlap_score(self, ref_text: str, signals: Dict[str, Any]) -> Tuple[int, int]:
        terms = signals.get("terms", [])
        concept_aliases = signals.get("concept_aliases", {})
        overlap = sum(1 for t in terms if t in ref_text)
        concept_hits = 0
        for aliases in concept_aliases.values():
            if any(a and a in ref_text for a in aliases):
                concept_hits += 1
        return overlap, concept_hits

    def _is_dual_quinoa_soy_query(self, signals: Dict[str, Any]) -> bool:
        if self.mode != "dual":
            return False
        matched = [self._normalize_signal_term(x) for x in (signals.get("matched_concepts_raw") or [])]
        if matched:
            has_quinoa = any(("藜麦" in x) or ("quinoa" in x) or ("chenopodium" in x) for x in matched)
            has_soy = any(("大豆" in x) or ("soy" in x) or ("soybean" in x) for x in matched)
            if has_quinoa and has_soy:
                return True
        terms = [self._normalize_signal_term(x) for x in (signals.get("terms") or [])]
        has_quinoa_t = any(("藜麦" in x) or ("quinoa" in x) or ("chenopodium" in x) for x in terms)
        has_soy_t = any(("大豆" in x) or ("soy" in x) or ("soybean" in x) or (x == "spi") for x in terms)
        return has_quinoa_t and has_soy_t

    def _estimate_query_complexity(self, query: str) -> float:
        text = (query or "").lower()
        if not text:
            return 0.0
        score = min(0.4, len(text) / 120.0)
        complex_cues = [
            "机制", "机理", "路径", "调控", "比较", "差异", "综述", "评估", "证据", "局限",
            "mechanism", "pathway", "compare", "difference", "review", "evidence", "limitation"
        ]
        broad_cues = ["如何", "为什么", "关系", "影响", "驱动力", "相互作用", "结合", "how", "why", "interaction", "binding"]
        for cue in complex_cues:
            if cue in text:
                score += 0.15
        for cue in broad_cues:
            if cue in text:
                score += 0.08
        return min(1.0, score)

    def _adaptive_reference_window(self, query: str) -> Tuple[int, int]:
        base_min = max(1, self.retrieval_target_min)
        base_max = max(base_min, self.retrieval_target_max)
        complexity = self._estimate_query_complexity(query)
        target_max = int(round(base_min + (base_max - base_min) * complexity))
        if complexity < 0.20:
            target_max = max(base_min, min(base_max, base_min + 5))
        elif complexity < 0.30:
            target_max = max(base_min, min(base_max, base_min + 15))
        elif complexity < 0.55:
            target_max = max(base_min, min(base_max, base_min + 25))
        else:
            target_max = base_max
        return base_min, max(base_min, target_max)

    def _reference_text(self, ref: Dict[str, Any]) -> str:
        return " ".join([
            str(ref.get("title", "")),
            str(ref.get("filename", "")),
            str(ref.get("content", "")),
            " ".join(str(x) for x in ref.get("authors", []) if x),
        ]).lower()

    def _apply_topic_boundary(self, references: List[Dict[str, Any]], original_query: str) -> List[Dict[str, Any]]:
        """主题排序：按实体/主题命中重排，避免相关文献被泛化文献淹没。"""
        if not references:
            return references

        signals = self._get_query_signals(original_query)
        topic_terms = signals.get("terms", [])
        if not topic_terms:
            return references

        ranked = []
        dual_focus_mode = self.dual_focus_files and self._is_dual_quinoa_soy_query(signals)
        for ref in references:
            ref_text = self._reference_text(ref)
            overlap, concept_hits = self._reference_overlap_score(ref_text, signals)
            base = float(ref.get("final_score", ref.get("score", 0)) or 0)
            focus_bonus = 0
            if dual_focus_mode:
                ref_path = str(ref.get("file_path", "") or "")
                if ref_path and normalize_for_storage(ref_path) in self.dual_focus_files:
                    focus_bonus = 2000
            rank_score = focus_bonus + concept_hits * 1000 + overlap * 10 + base
            ranked.append((rank_score, ref))

        ranked.sort(key=lambda x: x[0], reverse=True)
        merged = [ref for _, ref in ranked]

        for idx, ref in enumerate(merged, 1):
            ref["ref_id"] = f"ref_{idx}"
        return merged

    def _build_retrieval_warning(self, references: List[Dict[str, Any]], original_query: str) -> Optional[str]:
        warnings = []
        min_refs = max(1, int(os.getenv("RETRIEVAL_WARNING_MIN_REFS", "6")))
        if len(references) < min_refs:
            warnings.append("相关文献较少，请尝试英文名/缩写或补充语料。")

        return " ".join(warnings) if warnings else None

    def _chunk_matches_signals(self, chunk: Any, signals: Optional[Dict[str, Any]]) -> bool:
        if not signals:
            return False
        metadata = getattr(chunk, "metadata", {}) or {}
        fp = metadata.get("file_path") or ""
        if self.dual_focus_files and self._is_dual_quinoa_soy_query(signals):
            if fp and normalize_for_storage(fp) in self.dual_focus_files:
                return True
        text = " ".join([
            str(getattr(chunk, "text", "") or ""),
            str(metadata.get("file_name", "") or ""),
            str(fp),
        ]).lower()
        overlap, concept_hits = self._reference_overlap_score(text, signals)
        return concept_hits > 0 or overlap >= 2

    def _filter_chunks(self, chunks, threshold: float, signals: Optional[Dict[str, Any]] = None) -> List[Any]:
        filtered = []
        for chunk in chunks:
            try:
                score = float(chunk.score) if hasattr(chunk, 'score') else 0.0
            except (TypeError, ValueError):
                score = 0.0
            if score >= threshold or self._chunk_matches_signals(chunk, signals):
                filtered.append(chunk)
        return filtered

    def _diversify_chunks(self, chunks, target_max: Optional[int] = None) -> List[Any]:
        selected = []
        target = max(1, target_max or self.retrieval_target_max)
        max_selected = max(target * self.max_chunks_per_paper * 3, target * 2)
        per_paper: Dict[str, int] = {}
        for chunk in chunks:
            metadata = getattr(chunk, 'metadata', {}) or {}
            paper_file_path = metadata.get('file_path') or metadata.get('file_name') or 'unknown'
            if per_paper.get(paper_file_path, 0) >= self.max_chunks_per_paper:
                continue
            selected.append(chunk)
            per_paper[paper_file_path] = per_paper.get(paper_file_path, 0) + 1
            if len(per_paper) >= target and len(selected) >= max_selected:
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
            'target_min_references': self.retrieval_target_min,
            'target_max_references': self.retrieval_target_max,
        }

    def _deduplicate_chunks(self, chunks) -> Dict[str, Any]:
        unique_papers_dict = {}
        for chunk in chunks:
            metadata = getattr(chunk, 'metadata', {}) or {}
            paper_filename = metadata.get('file_name', '未知文档')
            raw_file_path = metadata.get('file_path', '') or paper_filename
            paper_file_path = normalize_for_storage(raw_file_path) if raw_file_path else paper_filename
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
            
            paper_metadata = self._lookup_metadata_fast(file_path) if file_path else None
            
            if paper_metadata:
                references_raw.append({
                    'ref_id': f'ref_{paper_index}', # Temporary ID
                    'journal': paper_metadata.get('journal', 'Unknown Journal'),
                    'year': paper_metadata.get('year', 'N/A'),
                    'title': paper_metadata.get('title', 'Unknown Title'),
                    'authors': paper_metadata.get('authors', []),
                    'doi': paper_metadata.get('doi', 'Not Available'),
                    'volume': paper_metadata.get('volume', ''),
                    'issue': paper_metadata.get('issue', ''),
                    'pages': paper_metadata.get('pages', paper_metadata.get('page', '')),
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

        if self.mode == "dual":
            citation_target = min(max(6, len(references) // 3), 14)
            length_hint = "700-1200字"
            structure_hint = """【输出结构（中等篇幅科研风格）】：
1. 核心结论（2-4点）
2. 机制解释（按要点展开）
3. 证据与文献（说明关键证据来源、一致性与差异）
4. 局限性与不确定性
5. 结论与建议（可用于下一步实验/检索）"""
        else:
            citation_target = min(max(4, len(references) // 4), 10)
            length_hint = "450-700字"
            structure_hint = """【输出结构（快速科研摘要）】：
1. 关键结论（2-3点）
2. 主要证据（含文献编号）
3. 应用或风险提示（简短）"""

        return f"""你是食品科学专业领域的专家。请严格基于给定文献回答问题，保持科学严谨，避免臆测。

【参考文献列表】（共{len(references)}篇，编号为ref_1到ref_{len(references)}）：
{ref_list_summary}

【重要】：
- 只能使用ref_1到ref_{len(references)}这些编号
- 在回答的关键信息后用[ref_X]或[ref_X, ref_Y]标注来源，正文至少引用{citation_target}篇不同文献
- 不要引用任何其他编号
- 如果证据不充分，必须明确说明"不足之处"与"仍可参考的证据边界"
- 只输出最终答案，不要输出思维链、推理过程、分析过程或自我说明

{structure_hint}

【参考文献内容】：
{context}

【问题】：{question}

请用中文回答，结构清晰，正文控制在中等篇幅（通常约{length_hint}），并在关键观点后标注文献来源。"""

    def _build_extended_reference_block(self, references: List[Dict[str, Any]]) -> str:
        if not references:
            return ""
        # 追加一段"延伸文献"，提升文献可见度与可追溯性
        limit = min(max(8, len(references) // 4), 12)
        selected = references[:limit]
        lines = ["", "【延伸文献（按相关性）】"]
        for ref in selected:
            lines.append(f"- [{ref['ref_id']}] {ref.get('title', ref.get('filename', 'Unknown'))}")
        return "\n".join(lines)

    def _build_answer_tail(self, answer: str, references: List[Dict[str, Any]]) -> str:
        tail_parts: List[str] = []
        if references and not re.search(r"\[ref_\d+", answer or ""):
            fallback_refs = ", ".join(f"[{ref['ref_id']}]" for ref in references[:4])
            tail_parts.append(f"\n\n相关证据：{fallback_refs}。")

        # Bibliographies are rendered from structured reference data in the
        # shared frontend; do not append a second AI-generated reference list.
        return "".join(tail_parts)

    def _augment_answer(self, answer: str, references: List[Dict[str, Any]]) -> str:
        return (answer or "") + self._build_answer_tail(answer or "", references)

    def _call_llm(self, prompt, references) -> Tuple[str, Optional[str]]:
        messages = [
            {"role": "system", "content": f"你是食品科学专业领域的专家。重要：你只能引用ref_1到ref_{len(references)}这{len(references)}篇文献，不要使用其他编号。只输出最终答案，不要输出思维链、推理过程、分析过程或自我说明。"},
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
