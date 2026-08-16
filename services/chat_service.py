"""Public chat facade over the observable RAG pipeline."""

from __future__ import annotations

import json
import logging
import os
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

from config import RAGConfig, config, dual_rag_config, proteoglycan_rag_config, sweet_rag_config
from path_utils import normalize_for_storage
from services.answer_generator import AnswerGenerator
from services.citation_validator import CitationValidator
from services.context_builder import ContextBuilder
from services.encapsulation_references import serialize_encapsulation_references
from services.llm_client import DeepSeekLLMClient
from services.metadata_service import MetadataService
from services.query_processor import QueryProcessor
from services.rag_pipeline import RAGPipeline
from services.rag_types import StageTrace, stable_chunk_id, stable_document_id
from services.ranking_service import RankingService
from services.reference_selector import ReferenceSelector
from services.response_serializer import ResponseSerializer
from services.retrieval_service import RetrievalService
from services.supplement_service import SupplementService
from services.sweetness_prediction_service import get_sweetness_prediction_service


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
        self.last_run: Dict[str, Any] = {}

        configs = {"dual": dual_rag_config, "proteoglycan": proteoglycan_rag_config}
        rc: RAGConfig = configs.get(mode, sweet_rag_config)
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

        self.query_processor = QueryProcessor(query_expander)
        self.metadata_service = MetadataService(rag_system)
        self.retrieval_service = RetrievalService(rag_system, self.query_processor, rc.max_chunks_per_paper)
        self.context_builder = ContextBuilder(self.metadata_service, mode)
        self.ranking_service = RankingService(evidence_ranker, self.query_processor)
        self.supplement_service = SupplementService(self.metadata_service, self.query_processor)
        self.reference_selector = ReferenceSelector(
            self.context_builder, self.ranking_service, self.supplement_service
        )
        focus_path = os.getenv("DUAL_FOCUS_FILELIST", "./data/dual_focus_quinoa_soy_files.txt")
        self.dual_focus_files = (
            self.metadata_service.load_focus_filelist(focus_path) if mode == "dual" else set()
        )
        self.pipeline = RAGPipeline(
            self.query_processor,
            self.retrieval_service,
            self.reference_selector,
            target_min=rc.target_min,
            target_max=rc.target_max,
            min_threshold=rc.min_threshold,
            threshold_step=rc.threshold_step,
            max_top_k=rc.max_top_k,
            hard_top_k=rc.hard_top_k,
            max_chunks_per_paper=rc.max_chunks_per_paper,
            allow_weak_supplement=rc.allow_weak_supplement,
            dual_focus_files=self.dual_focus_files,
        )
        self.citation_validator = CitationValidator()
        self.answer_generator = AnswerGenerator(
            llm_client,
            self.context_builder,
            self.citation_validator,
            max_tokens=rc.qa_max_tokens,
            show_reasoning=rc.show_reasoning,
            disable_reasoning_hard=rc.disable_reasoning_hard,
        )
        self.response_serializer = ResponseSerializer(self.context_builder)
        self.sweetness_service = get_sweetness_prediction_service()

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
        if not self.rag_system or not getattr(self.rag_system, "index", None):
            return {"success": False, "error": "知识库未初始化或数据缺失，请联系管理员或稍后重试。"}

        started = time.time()
        expanded_query = self._expand_query(question)
        retrieval = self.pipeline.retrieve(expanded_query, similarity_threshold, max_results, question)
        if not retrieval.retrieved_chunks:
            return self._create_empty_response(question, started, time.time())

        context_started = time.perf_counter()
        context = self.context_builder.build_context(
            retrieval.references, retrieval.unique_papers_dict, self.context_window
        )
        prompt = self.context_builder.build_prompt(retrieval.references, context, question)
        traces = list(retrieval.traces)
        traces.append(
            StageTrace(
                "context",
                (time.perf_counter() - context_started) * 1000,
                {"characters": len(context), "references": len(retrieval.references)},
            )
        )

        citation_diagnostics: Dict[str, Any] = {}
        generation_started = time.perf_counter()
        if self.llm_client:
            try:
                self.answer_generator.llm_client = self.llm_client
                answer, _reasoning, citation_diagnostics = self.answer_generator.generate(
                    prompt, retrieval.references
                )
            except Exception as exc:
                self.logger.error("LLM调用失败: %s", exc)
                answer = (
                    "抱歉，DeepSeek服务当前繁忙或出错，请稍后再试。\n\n"
                    f"基于检索到的文档，我可以提供以下参考信息：\n\n{context[:500]}..."
                )
        else:
            answer = "DeepSeek API 未配置，无法生成回答。"
        traces.append(
            StageTrace(
                "generation",
                (time.perf_counter() - generation_started) * 1000,
                citation_diagnostics,
            )
        )

        ml_prediction = None
        if self.mode == "main":
            try:
                answer, ml_prediction = self.sweetness_service.augment_answer(question, answer)
            except Exception as exc:
                self.logger.warning("Sweetness prediction failed: %s", exc)

        response_time = round(time.time() - started, 2)
        frontend_references = self.context_builder.format_references_for_frontend(retrieval.references)
        conversation = {
            "id": len(self.conversations) + 1,
            "question": question,
            "answer": answer,
            "references": frontend_references,
            "references_raw": retrieval.references,
            "retrieval_stats": retrieval.stats,
            "retrieval_warning": retrieval.warning,
            "ml_prediction": ml_prediction,
            "timestamp": datetime.now().isoformat(),
            "response_time": response_time,
        }
        self.conversations.append(conversation)
        self.last_run = self._evaluation_payload(
            question, expanded_query, retrieval, context, prompt, answer, traces, citation_diagnostics
        )
        return self.response_serializer.success(
            answer,
            retrieval.references,
            retrieval.stats,
            retrieval.warning,
            ml_prediction,
            response_time,
        )

    def ask_stream(
        self,
        question: str,
        similarity_threshold: float = config.RAG_SIMILARITY_THRESHOLD,
        max_results: int = config.RAG_MAX_RESULTS,
    ) -> Generator[str, None, None]:
        if not self.rag_system or not getattr(self.rag_system, "index", None):
            yield self._event("error", error="知识库未初始化或数据缺失，请联系管理员或稍后重试。")
            return
        try:
            yield self._event("start", message="开始检索文献...")
            expanded_query = self._expand_query(question)
            yield self._event("status", message="正在检索相关文献...")
            retrieval_started = time.perf_counter()
            retrieval = self.pipeline.retrieve(expanded_query, similarity_threshold, max_results, question)
            self.logger.info(
                "%s retrieval completed in %.2fs: %s chunks, %s references",
                self.mode,
                time.perf_counter() - retrieval_started,
                retrieval.stats.get("after_threshold", 0),
                retrieval.stats.get("final_references", 0),
            )
            if not retrieval.retrieved_chunks:
                yield self._event("references", references=[])
                yield self._event(
                    "retrieval_stats", stats=self._empty_retrieval_stats(), warning="未检索到相关文献"
                )
                yield self._event("answer_start")
                yield self._event("answer", content="未检索到相关文献，请尝试更具体的关键词或降低相似度阈值。")
                yield self._event("done")
                return

            stats = retrieval.stats
            yield self._event("status", message=f"找到 {stats['after_threshold']} 个相关文本块")
            yield self._event("status", message=f"筛选出 {stats['final_references']} 篇核心文献")
            rich_references = serialize_encapsulation_references(
                retrieval.references,
                retrieval.unique_papers_dict,
                max_chunks=1 if self.mode == "proteoglycan" else None,
                text_limit=800 if self.mode == "proteoglycan" else 1600,
            )
            yield self._event("references", references=rich_references)
            yield self._event("retrieval_stats", stats=stats, warning=retrieval.warning)
            yield self._event("status", message="正在生成答案...")

            context = self.context_builder.build_context(
                retrieval.references, retrieval.unique_papers_dict, self.context_window
            )
            prompt = self.context_builder.build_prompt(retrieval.references, context, question)
            if not self.llm_client:
                yield self._event("error", error="DeepSeek API 未配置，无法生成回答。")
                return

            messages = self.answer_generator.messages(prompt, len(retrieval.references))
            reasoning_started = False
            answer_started = False
            buffer = ""
            answer_text = ""
            for delta in self.llm_client.stream_chat(messages, temperature=0.6, max_tokens=self.qa_max_tokens):
                if not self.disable_reasoning_hard and delta.reasoning_content:
                    if not reasoning_started:
                        yield self._event("reasoning_start")
                        reasoning_started = True
                    yield self._event("reasoning", content=delta.reasoning_content)
                if delta.content:
                    if not answer_started:
                        if reasoning_started:
                            yield self._event("reasoning_end")
                        yield self._event("answer_start")
                        answer_started = True
                    buffer += delta.content
                    answer_text += delta.content
                    if len(buffer) >= 5:
                        yield self._event("answer", content=buffer)
                        buffer = ""
            if buffer:
                yield self._event("answer", content=buffer)
            tail = self.context_builder.build_answer_tail(answer_text, retrieval.references)
            if tail:
                yield self._event("answer", content=tail)
            citation_diagnostics = self.citation_validator.diagnose(
                answer_text, answer_text + tail, retrieval.references
            )
            self.last_run = self._evaluation_payload(
                question,
                expanded_query,
                retrieval,
                context,
                prompt,
                answer_text + tail,
                retrieval.traces,
                citation_diagnostics,
            )
            yield self._event("done")
        except Exception as exc:
            traceback.print_exc()
            yield self._event("error", error=str(exc))

    def retrieve_for_evaluation(
        self,
        question: str,
        similarity_threshold: float = config.RAG_SIMILARITY_THRESHOLD,
        max_results: int = config.RAG_MAX_RESULTS,
    ) -> Dict[str, Any]:
        expanded_query = self._expand_query(question)
        retrieval = self.pipeline.retrieve(expanded_query, similarity_threshold, max_results, question)
        context = self.context_builder.build_context(
            retrieval.references, retrieval.unique_papers_dict, self.context_window
        )
        return self._evaluation_payload(
            question, expanded_query, retrieval, context, "", "", retrieval.traces, {}
        )

    def _expand_query(self, question: str) -> str:
        expansion = self.query_expander.expand_query(question)
        return expansion["search_query"] if expansion.get("expanded_terms") else question

    def _evaluation_payload(self, question, expanded_query, retrieval, context, prompt, answer, traces, citation):
        chunks = []
        for rank, chunk in enumerate(retrieval.retrieved_chunks, 1):
            metadata = getattr(chunk, "metadata", {}) or {}
            file_path = metadata.get("file_path") or metadata.get("file_name") or ""
            chunks.append(
                {
                    "rank": rank,
                    "chunk_id": stable_chunk_id(chunk, file_path),
                    "document_id": stable_document_id(file_path),
                    "file_path": normalize_for_storage(file_path),
                    "filename": metadata.get("file_name") or Path(file_path).name,
                    "page": metadata.get("page_label") or metadata.get("page_number") or metadata.get("page"),
                    "section": metadata.get("section") or metadata.get("section_title"),
                    "score": float(getattr(chunk, "score", 0) or 0),
                    "text": str(getattr(chunk, "text", "") or "")[:2000],
                }
            )
        return {
            "question": question,
            "expanded_query": expanded_query,
            "query_variants": retrieval.query_variants,
            "chunks": chunks,
            "references": retrieval.references,
            "context": context,
            "prompt": prompt,
            "answer": answer,
            "retrieval_stats": retrieval.stats,
            "retrieval_warning": retrieval.warning,
            "citation_diagnostics": citation,
            "stage_traces": [trace.to_dict() for trace in traces],
        }

    def _create_empty_response(self, question, start_time, end_time):
        response_time = round(end_time - start_time, 2)
        answer = "未检索到相关文献，请尝试更具体的关键词或降低相似度阈值。"
        self.conversations.append(
            {
                "id": len(self.conversations) + 1,
                "question": question,
                "answer": answer,
                "references": [],
                "timestamp": datetime.now().isoformat(),
                "response_time": response_time,
            }
        )
        return {
            "success": True,
            "answer": answer,
            "references": [],
            "retrieval_stats": self._empty_retrieval_stats(),
            "retrieval_warning": "未检索到相关文献",
            "response_time": response_time,
        }

    def _empty_retrieval_stats(self) -> Dict[str, Any]:
        return {
            "raw_chunks": 0,
            "valid_chunks": 0,
            "after_threshold": 0,
            "selected_chunks": 0,
            "unique_papers": 0,
            "final_references": 0,
            "requested_threshold": None,
            "effective_threshold": None,
            "top_k": 0,
            "max_chunks_per_paper": self.max_chunks_per_paper,
            "target_min_references": self.retrieval_target_min,
            "target_max_references": self.retrieval_target_max,
        }

    @staticmethod
    def _event(event_type: str, **payload: Any) -> str:
        return f"data: {json.dumps({'type': event_type, **payload}, ensure_ascii=False)}\n\n"

    # Compatibility hooks used by focused tests and local diagnostics.
    def _retrieve_references(self, query, similarity_threshold, max_results, original_query=""):
        return self.pipeline.retrieve(query, similarity_threshold, max_results, original_query).to_legacy_dict()

    def _build_context(self, references, unique_papers_dict, max_context_length):
        return self.context_builder.build_context(references, unique_papers_dict, max_context_length)

    def _build_prompt(self, references, context, question):
        return self.context_builder.build_prompt(references, context, question)

    def _system_message(self, reference_count: int) -> str:
        return self.context_builder.system_message(reference_count)

    def _format_references_for_frontend(self, references):
        return self.context_builder.format_references_for_frontend(references)

    def _build_answer_tail(self, answer, references):
        return self.context_builder.build_answer_tail(answer, references)

    def _call_llm(self, prompt, references) -> Tuple[str, Optional[str]]:
        self.answer_generator.llm_client = self.llm_client
        answer, reasoning, _ = self.answer_generator.generate(prompt, references, append_tail=False)
        return answer, reasoning
