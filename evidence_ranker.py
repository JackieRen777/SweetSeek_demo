#!/usr/bin/env python3
"""
证据分级系统 - 简化版
"""

class EvidenceRanker:
    """证据分级器 - 简化版"""
    
    def rank_paper(self, paper_metadata: dict, paper_content: str = "") -> dict:
        """对单篇文献进行分级"""
        return {
            'evidence_level': 3,
            'evidence_label': "中等质量证据",
            'study_type': 'unknown',
            'study_type_score': 2.0,
            'journal_tier': 3,
            'journal_score': 2.0,
            'recency_score': 3.0,
            'data_quality': 2.0,
            'total_score': 2.5
        }
    
    def rank_papers(self, papers: list) -> list:
        """对多篇文献进行批量分级"""
        ranked_papers = []
        for paper in papers:
            metadata = {
                'journal': paper.get('journal', 'Unknown'),
                'year': paper.get('year', 'N/A'),
            }
            ranking = self.rank_paper(metadata, paper.get('content', ''))
            ranked_paper = {**paper, **ranking}
            ranked_papers.append(ranked_paper)
        
        ranked_papers.sort(key=lambda x: x.get('score', 0), reverse=True)
        return ranked_papers
