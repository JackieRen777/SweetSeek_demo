"""查询分析、信号提取、复杂度估计"""

import re
from typing import Any, Dict, List, Tuple


class QueryProcessor:
    def __init__(self, query_expander: Any):
        self.query_expander = query_expander

    def build_query_variants(self, expanded_query: str, original_question: str) -> List[str]:
        variants: List[str] = []
        for candidate in (expanded_query, original_question):
            value = (candidate or "").strip()
            if value and value not in variants:
                variants.append(value)
        if " OR " in (expanded_query or ""):
            first_segment = expanded_query.split(" OR ", 1)[0].strip()
            if first_segment and first_segment not in variants:
                variants.append(first_segment)
        topic_tokens = self.extract_topic_tokens(original_question)
        if topic_tokens:
            short = " ".join(topic_tokens[:3])
            if short not in variants:
                variants.append(short)
            if len(topic_tokens) >= 2:
                broad = f"{topic_tokens[0]} {topic_tokens[1]} 相互作用 机制"
                if broad not in variants:
                    variants.append(broad)
        return variants[:5]

    def extract_topic_tokens(self, query: str) -> List[str]:
        query_text = (query or "").strip().lower()
        if not query_text:
            return []
        query_text = re.sub(r"(如何|怎么|是什么|是怎样|请问|有关|相关|机制|机理)", " ", query_text)

        english_tokens = re.findall(r"[a-z][a-z0-9+._-]{2,}", query_text)
        chinese_chunks = re.findall(r"[一-鿿]{2,}", query_text)
        stopwords = {"如何", "怎么", "什么", "为何", "请问", "是否", "以及", "关于", "之间", "机制", "作用", "结合"}

        tokens = set(english_tokens)
        for chunk in chinese_chunks:
            for part in re.split(r"[和与及或、在是的了呢吗吧将把对跟同]", chunk):
                part = part.strip()
                if len(part) >= 2 and part not in stopwords:
                    tokens.add(part)
        return sorted(tokens)

    @staticmethod
    def normalize_signal_term(term: str) -> str:
        return (term or "").strip().lower()

    def get_query_signals(self, query: str) -> Dict[str, Any]:
        base_tokens = self.extract_topic_tokens(query)
        terms = {self.normalize_signal_term(t) for t in base_tokens if len(self.normalize_signal_term(t)) >= 2}
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
                    t_norm = self.normalize_signal_term(str(t))
                    if len(t_norm) >= 2:
                        terms.add(t_norm)

                synonyms_dict = getattr(self.query_expander, "term_synonyms", {}) or {}
                for concept in matched_concepts:
                    concept_norm = self.normalize_signal_term(str(concept))
                    if not concept_norm:
                        continue
                    aliases = [concept_norm]
                    for syn in synonyms_dict.get(concept, []):
                        s = self.normalize_signal_term(str(syn))
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

    def reference_overlap_score(self, ref_text: str, signals: Dict[str, Any]) -> Tuple[int, int]:
        terms = signals.get("terms", [])
        concept_aliases = signals.get("concept_aliases", {})
        overlap = sum(1 for t in terms if t in ref_text)
        concept_hits = 0
        for aliases in concept_aliases.values():
            if any(a and a in ref_text for a in aliases):
                concept_hits += 1
        return overlap, concept_hits

    def is_dual_quinoa_soy_query(self, signals: Dict[str, Any]) -> bool:
        matched = [self.normalize_signal_term(x) for x in (signals.get("matched_concepts_raw") or [])]
        if matched:
            has_quinoa = any(("藜麦" in x) or ("quinoa" in x) or ("chenopodium" in x) for x in matched)
            has_soy = any(("大豆" in x) or ("soy" in x) or ("soybean" in x) for x in matched)
            if has_quinoa and has_soy:
                return True
        terms = [self.normalize_signal_term(x) for x in (signals.get("terms") or [])]
        has_quinoa_t = any(("藜麦" in x) or ("quinoa" in x) or ("chenopodium" in x) for x in terms)
        has_soy_t = any(("大豆" in x) or ("soy" in x) or ("soybean" in x) or (x == "spi") for x in terms)
        return has_quinoa_t and has_soy_t

    def estimate_query_complexity(self, query: str) -> float:
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

    def adaptive_reference_window(self, query: str, target_min: int, target_max: int) -> Tuple[int, int]:
        base_min = max(1, target_min)
        base_max = max(base_min, target_max)
        complexity = self.estimate_query_complexity(query)
        if complexity < 0.20:
            t_max = max(base_min, min(base_max, base_min + 5))
        elif complexity < 0.30:
            t_max = max(base_min, min(base_max, base_min + 15))
        elif complexity < 0.55:
            t_max = max(base_min, min(base_max, base_min + 25))
        else:
            t_max = base_max
        return base_min, max(base_min, t_max)
