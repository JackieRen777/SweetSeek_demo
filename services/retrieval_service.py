"""多查询检索、过滤、去重、多样化"""

from typing import Any, Dict, List, Optional, Tuple

from path_utils import normalize_for_storage
from services.query_processor import QueryProcessor


class RetrievalService:
    def __init__(self, rag_system: Any, query_processor: QueryProcessor, max_chunks_per_paper: int = 2):
        self.rag_system = rag_system
        self.query_processor = query_processor
        self.max_chunks_per_paper = max_chunks_per_paper

    def retrieve_chunks_multi_query(self, queries: List[str], top_k: int) -> List[Any]:
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

    def filter_chunks(self, chunks, threshold: float, signals: Optional[Dict[str, Any]] = None,
                      dual_focus_files=None) -> List[Any]:
        filtered = []
        for chunk in chunks:
            try:
                score = float(chunk.score) if hasattr(chunk, 'score') else 0.0
            except (TypeError, ValueError):
                score = 0.0
            if score >= threshold or self._chunk_matches_signals(chunk, signals, dual_focus_files):
                filtered.append(chunk)
        return filtered

    def diversify_chunks(self, chunks, target_max: int) -> List[Any]:
        selected = []
        target = max(1, target_max)
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

    def deduplicate_chunks(self, chunks) -> Dict[str, Any]:
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

    def _chunk_matches_signals(self, chunk: Any, signals: Optional[Dict[str, Any]],
                               dual_focus_files=None) -> bool:
        if not signals:
            return False
        metadata = getattr(chunk, "metadata", {}) or {}
        fp = metadata.get("file_path") or ""
        if dual_focus_files and self.query_processor.is_dual_quinoa_soy_query(signals):
            if fp and normalize_for_storage(fp) in dual_focus_files:
                return True
        text = " ".join([
            str(getattr(chunk, "text", "") or ""),
            str(metadata.get("file_name", "") or ""),
            str(fp),
        ]).lower()
        overlap, concept_hits = self.query_processor.reference_overlap_score(text, signals)
        return concept_hits > 0 or overlap >= 2
