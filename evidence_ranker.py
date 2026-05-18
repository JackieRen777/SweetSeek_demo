#!/usr/bin/env python3
"""证据分级系统 — 多维度评分"""
import re
from datetime import datetime
from typing import Dict, List, Tuple


class EvidenceRanker:
    """多维度证据分级器：语义相关度 + 研究类型 + 期刊质量 + 时效性 + 证据强度"""

    def __init__(self):
        self.top_journals = [
            'nature', 'science', 'cell', 'lancet',
            'new england journal of medicine', 'jama',
            'british medical journal', 'bmj',
            'food chemistry', 'journal of agricultural and food chemistry',
            'trends in food science', 'comprehensive reviews in food science',
        ]
        self.tier2_keywords = [
            'nutrition', 'metabolism', 'diabetes', 'obesity',
            'clinical', 'american journal', 'european journal',
            'food hydrocolloids', 'food research international',
            'journal of food science', 'lwt', 'meat science',
        ]
        self.study_types = {
            'meta-analysis': {'score': 5.0, 'level': 1},
            'systematic review': {'score': 5.0, 'level': 1},
            'randomized controlled trial': {'score': 4.5, 'level': 1},
            'rct': {'score': 4.5, 'level': 1},
            'cohort': {'score': 3.5, 'level': 2},
            'case-control': {'score': 3.0, 'level': 2},
            'cross-sectional': {'score': 2.5, 'level': 3},
            'animal study': {'score': 2.0, 'level': 4},
            'in vivo': {'score': 2.0, 'level': 4},
            'in vitro': {'score': 1.5, 'level': 5},
            'review': {'score': 1.5, 'level': 5},
        }
        self._experimental_cues = [
            "results show", "we found", "significantly", "p<0.05", "p < 0.05",
            "p-value", "anova", "t-test", "实验表明", "结果显示", "显著",
            "measured", "determined", "observed", "demonstrated",
        ]
        self._review_cues = [
            "review", "reported that", "according to", "综述", "已有研究表明",
            "previous studies", "it has been shown", "literature",
        ]

    def rank_papers(self, papers: List[Dict]) -> List[Dict]:
        ranked = []
        for paper in papers:
            ranking = self._rank_single(paper)
            ranked.append({**paper, **ranking})
        ranked.sort(key=lambda x: (-x['total_score'],))
        return ranked

    def _rank_single(self, paper: Dict) -> Dict:
        title = paper.get('title', '')
        journal = paper.get('journal', '')
        year = paper.get('year', '')
        content = paper.get('content', '')
        similarity_score = float(paper.get('score', 0) or 0)

        # 1. 语义相关度 (0.35) — 直接用向量检索分数
        semantic = min(5.0, similarity_score * 10)

        # 2. 研究类型 (0.20)
        study_score = self._detect_study_type_score(title, content)

        # 3. 证据强度分类 (0.20)
        evidence_type, evidence_type_score = self._classify_evidence_type(content)

        # 4. 期刊质量 (0.10)
        journal_score = self._assess_journal_score(journal)

        # 5. 时效性 (0.10)
        recency_score = self._calculate_recency_score(year)

        total_score = (
            semantic * 0.35 +
            study_score * 0.20 +
            evidence_type_score * 0.20 +
            journal_score * 0.10 +
            recency_score * 0.10
        )

        # 综合判定 evidence_level 标签
        if total_score >= 3.2:
            evidence_level = "strong"
        elif total_score >= 2.2:
            evidence_level = "moderate"
        else:
            evidence_level = "weak"

        return {
            'total_score': round(total_score, 2),
            'evidence_level': evidence_level,
            'evidence_type': evidence_type,
            'semantic_score': round(semantic, 2),
            'study_type_score': round(study_score, 2),
            'evidence_type_score': round(evidence_type_score, 2),
            'journal_score': round(journal_score, 2),
            'recency_score': round(recency_score, 2),
        }

    def _detect_study_type_score(self, title: str, content: str) -> float:
        text = (title + " " + content[:800]).lower()
        best = 2.0
        for keyword, info in self.study_types.items():
            if keyword in text and info['score'] > best:
                best = info['score']
        return best

    def _classify_evidence_type(self, content: str) -> Tuple[str, float]:
        text = (content or "")[:1500].lower()
        if not text:
            return "indirect", 2.0
        exp_hits = sum(1 for cue in self._experimental_cues if cue in text)
        rev_hits = sum(1 for cue in self._review_cues if cue in text)
        if exp_hits >= 2:
            return "experimental", 4.5
        if rev_hits >= 2:
            return "review_citation", 2.5
        if exp_hits == 1:
            return "experimental", 3.5
        return "indirect", 2.0

    def _assess_journal_score(self, journal: str) -> float:
        if not journal or journal.lower() in ('unknown', 'unknown journal'):
            return 2.0
        j = journal.lower()
        for top in self.top_journals:
            if top in j:
                return 5.0
        for t2 in self.tier2_keywords:
            if t2 in j:
                return 3.5
        return 2.0

    def _calculate_recency_score(self, year_str: str) -> float:
        match = re.search(r'(19|20)\d{2}', str(year_str))
        if not match:
            return 3.0
        age = datetime.now().year - int(match.group(0))
        if age <= 2:
            return 5.0
        if age <= 5:
            return 4.0
        if age <= 10:
            return 3.0
        if age <= 20:
            return 2.0
        return 1.0
