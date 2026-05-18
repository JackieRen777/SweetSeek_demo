"""上下文组装、Prompt 构建、引用格式化"""

import math
import re
from typing import Any, Dict, List, Optional

from services.metadata_service import MetadataService


class ContextBuilder:
    def __init__(self, metadata_service: MetadataService, mode: str = "main"):
        self.metadata_service = metadata_service
        self.mode = mode

    def build_references_raw(self, unique_papers_list) -> List[Dict[str, Any]]:
        import os
        references_raw = []
        for paper_index, paper_info in enumerate(unique_papers_list, 1):
            file_path = paper_info['file_path']
            paper_metadata = self.metadata_service.lookup_metadata_fast(file_path) if file_path else None

            if paper_metadata:
                references_raw.append({
                    'ref_id': f'ref_{paper_index}',
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

    def build_context(self, references, unique_papers_dict, max_context_length) -> str:
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

    def build_prompt(self, references, context, question) -> str:
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

    def format_references_for_frontend(self, references: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
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

    @staticmethod
    def build_extended_reference_block(references: List[Dict[str, Any]]) -> str:
        if not references:
            return ""
        limit = min(max(8, len(references) // 4), 12)
        selected = references[:limit]
        lines = ["", "【延伸文献（按相关性）】"]
        for ref in selected:
            lines.append(f"- [{ref['ref_id']}] {ref.get('title', ref.get('filename', 'Unknown'))}")
        return "\n".join(lines)

    @staticmethod
    def build_answer_tail(answer: str, references: List[Dict[str, Any]]) -> str:
        tail_parts: List[str] = []
        if references and not re.search(r"\[ref_\d+", answer or ""):
            fallback_refs = ", ".join(f"[{ref['ref_id']}]" for ref in references[:4])
            tail_parts.append(f"\n\n【证据标注补充】该回答主要基于以下文献：{fallback_refs}。")

        ext = ContextBuilder.build_extended_reference_block(references)
        if ext and "延伸文献" not in (answer or ""):
            tail_parts.append("\n" + ext)
        return "".join(tail_parts)
