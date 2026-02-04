#!/usr/bin/env python3
"""
证据分级系统 - 增强版
"""
import re

class EvidenceRanker:
    """证据分级器 - 基于关键词和元数据的启发式评估"""
    
    def __init__(self):
        # 顶级期刊列表（示例）
        self.top_journals = [
            'nature', 'science', 'cell', 'lancet', 
            'new england journal of medicine', 'jama',
            'british medical journal', 'bmj'
        ]
        
        # 二级期刊关键词
        self.tier2_keywords = [
            'nutrition', 'metabolism', 'diabetes', 'obesity', 
            'clinical', 'american journal', 'european journal'
        ]
        
        # 研究类型关键词（按证据等级排序）
        self.study_types = {
            'meta-analysis': {'score': 5.0, 'level': 1, 'label': 'Meta分析/系统综述'},
            'systematic review': {'score': 5.0, 'level': 1, 'label': 'Meta分析/系统综述'},
            'randomized controlled trial': {'score': 4.5, 'level': 1, 'label': '随机对照试验(RCT)'},
            'rct': {'score': 4.5, 'level': 1, 'label': '随机对照试验(RCT)'},
            'cohort': {'score': 3.5, 'level': 2, 'label': '队列研究'},
            'case-control': {'score': 3.0, 'level': 2, 'label': '病例对照研究'},
            'cross-sectional': {'score': 2.5, 'level': 3, 'label': '横断面研究'},
            'animal study': {'score': 2.0, 'level': 4, 'label': '动物实验'},
            'in vivo': {'score': 2.0, 'level': 4, 'label': '动物实验'},
            'in vitro': {'score': 1.5, 'level': 5, 'label': '体外实验'},
            'review': {'score': 1.5, 'level': 5, 'label': '综述/专家意见'}
        }

    def _assess_journal_tier(self, journal_name: str) -> tuple[int, float]:
        """评估期刊等级"""
        if not journal_name or journal_name.lower() == 'unknown':
            return 3, 2.0
            
        j_lower = journal_name.lower()
        
        # 检查顶级期刊
        for top in self.top_journals:
            if top in j_lower:
                return 1, 5.0
                
        # 检查二级期刊
        for tier2 in self.tier2_keywords:
            if tier2 in j_lower:
                return 2, 3.5
                
        return 3, 2.0

    def _detect_study_type(self, title: str, content: str) -> dict:
        """从标题和内容中检测研究类型"""
        text = (title + " " + content[:1000]).lower()
        
        best_match = None
        highest_score = 0.0
        
        for keyword, info in self.study_types.items():
            if keyword in text:
                if info['score'] > highest_score:
                    highest_score = info['score']
                    best_match = info
        
        if best_match:
            return best_match
        
        return {'score': 2.0, 'level': 4, 'label': '普通研究/未分类'}

    def _calculate_recency_score(self, year_str: str) -> float:
        """计算年份时效性分数"""
        try:
            # 提取年份数字
            import datetime
            current_year = datetime.datetime.now().year
            
            # 简单提取4位数字
            match = re.search(r'20\d{2}|19\d{2}', str(year_str))
            if not match:
                return 3.0 # 默认中等分数
                
            year = int(match.group(0))
            age = current_year - year
            
            if age <= 2: return 5.0      # 极新 (0-2年)
            if age <= 5: return 4.0      # 很新 (3-5年)
            if age <= 10: return 3.0     # 较新 (6-10年)
            if age <= 20: return 2.0     # 陈旧 (11-20年)
            return 1.0                   # 极旧 (>20年)
            
        except:
            return 3.0

    def rank_paper(self, paper_metadata: dict, paper_content: str = "") -> dict:
        """对单篇文献进行分级"""
        title = paper_metadata.get('title', '')
        journal = paper_metadata.get('journal', '')
        year = paper_metadata.get('year', '')
        
        # 1. 评估研究类型 (40%)
        study_info = self._detect_study_type(title, paper_content)
        
        # 2. 评估期刊质量 (30%)
        journal_tier, journal_score = self._assess_journal_tier(journal)
        
        # 3. 评估时效性 (20%)
        recency_score = self._calculate_recency_score(year)
        
        # 4. 数据质量 (10% - 暂未实现深度检测，给基础分)
        data_quality = 3.0
        
        # 计算加权总分
        total_score = (
            study_info['score'] * 0.4 +
            journal_score * 0.3 +
            recency_score * 0.2 +
            data_quality * 0.1
        )
        
        return {
            'evidence_level': study_info['level'],
            'evidence_label': study_info['label'],
            'study_type': study_info['label'],
            'study_type_score': study_info['score'],
            'journal_tier': journal_tier,
            'journal_score': journal_score,
            'recency_score': recency_score,
            'data_quality': data_quality,
            'total_score': round(total_score, 1)
        }
    
    def rank_papers(self, papers: list) -> list:
        """对多篇文献进行批量分级"""
        ranked_papers = []
        for paper in papers:
            metadata = {
                'title': paper.get('title', ''),
                'journal': paper.get('journal', 'Unknown'),
                'year': paper.get('year', 'N/A'),
            }
            ranking = self.rank_paper(metadata, paper.get('content', ''))
            ranked_paper = {**paper, **ranking}
            ranked_papers.append(ranked_paper)
        
        # 排序：优先按Evidence Level (越小越好)，其次按Total Score (越大越好)
        ranked_papers.sort(key=lambda x: (x['evidence_level'], -x['total_score']))
        return ranked_papers
