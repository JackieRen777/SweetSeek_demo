#!/usr/bin/env python3
"""
查询扩展模块 - 甜味领域同义词和相关术语扩展
"""

class SweetnessQueryExpander:
    """甜味领域查询扩展器"""
    
    def __init__(self):
        # 甜味剂同义词词典
        self.sweetener_synonyms = {
            # 天然甜味剂
            "蔗糖": ["sucrose", "白糖", "食糖", "table sugar"],
            "果糖": ["fructose", "果葡糖浆", "HFCS"],
            "葡萄糖": ["glucose", "右旋糖", "dextrose"],
            "甜菊糖": ["stevia", "甜菊糖苷", "stevioside", "rebaudioside"],
            "罗汉果糖": ["monk fruit", "罗汉果甜苷", "mogroside"],
            
            # 人工甜味剂
            "阿斯巴甜": ["aspartame", "天冬酰苯丙氨酸甲酯", "APM"],
            "三氯蔗糖": ["sucralose", "蔗糖素", "Splenda"],
            "糖精": ["saccharin", "邻苯甲酰磺酰亚胺"],
            "安赛蜜": ["acesulfame", "乙酰磺胺酸钾", "Ace-K"],
            "纽甜": ["neotame", "N-[N-(3,3-二甲基丁基)-L-α-天冬氨酰]-L-苯丙氨酸"],
            "甜蜜素": ["cyclamate", "环己基氨基磺酸钠"],
            
            # 糖醇
            "赤藓糖醇": ["erythritol", "赤藓醇"],
            "木糖醇": ["xylitol", "戊五醇"],
            "山梨糖醇": ["sorbitol", "山梨醇"],
            "甘露糖醇": ["mannitol", "甘露醇"],
            "麦芽糖醇": ["maltitol", "麦芽糖醇"],
        }
        
        # 概念扩展词典
        self.concept_expansion = {
            "甜味": ["sweetness", "甜度", "甜感", "sweet taste", "甜味感知"],
            "甜味剂": ["sweetener", "甜味物质", "代糖", "sugar substitute"],
            "甜味受体": ["sweet receptor", "T1R2", "T1R3", "taste receptor"],
            "甜度": ["sweetness intensity", "相对甜度", "甜度值", "sweetness potency"],
            "后味": ["aftertaste", "余味", "回甘", "lingering taste"],
            "协同效应": ["synergy", "协同作用", "synergistic effect"],
            
            # 健康相关
            "糖尿病": ["diabetes", "血糖", "glucose", "insulin"],
            "肥胖": ["obesity", "体重", "BMI", "weight gain"],
            "代谢": ["metabolism", "代谢综合征", "metabolic syndrome"],
            "肠道菌群": ["gut microbiota", "肠道微生物", "intestinal flora"],
            
            # 食品应用
            "饮料": ["beverage", "软饮料", "soft drink"],
            "烘焙": ["baking", "焙烤", "bakery"],
            "乳制品": ["dairy", "奶制品", "milk products"],
        }
        
        # 反向索引（用于快速查找）
        self.reverse_index = self._build_reverse_index()
    
    def _build_reverse_index(self):
        """构建反向索引：任何术语 -> 标准术语"""
        reverse = {}
        
        # 处理甜味剂同义词
        for standard_term, synonyms in self.sweetener_synonyms.items():
            reverse[standard_term.lower()] = standard_term
            for syn in synonyms:
                reverse[syn.lower()] = standard_term
        
        # 处理概念扩展
        for standard_term, related in self.concept_expansion.items():
            reverse[standard_term.lower()] = standard_term
            for rel in related:
                reverse[rel.lower()] = standard_term
        
        return reverse
    
    def expand_query(self, query: str) -> dict:
        """
        扩展查询
        
        返回：
        {
            'original': 原始查询,
            'expanded_terms': [扩展术语列表],
            'search_query': 用于检索的完整查询
        }
        """
        query_lower = query.lower()
        expanded_terms = set()
        matched_concepts = set()
        
        # 查找匹配的术语
        for term, standard in self.reverse_index.items():
            if term in query_lower:
                matched_concepts.add(standard)
        
        # 为每个匹配的概念添加同义词
        for concept in matched_concepts:
            # 添加甜味剂同义词
            if concept in self.sweetener_synonyms:
                expanded_terms.update(self.sweetener_synonyms[concept])
            
            # 添加概念扩展
            if concept in self.concept_expansion:
                expanded_terms.update(self.concept_expansion[concept])
        
        # 构建扩展查询
        all_terms = [query] + list(expanded_terms)
        search_query = " OR ".join(all_terms[:10])  # 限制最多10个术语
        
        return {
            'original': query,
            'matched_concepts': list(matched_concepts),
            'expanded_terms': list(expanded_terms),
            'search_query': search_query
        }
    
    def get_related_terms(self, term: str) -> list:
        """获取相关术语"""
        term_lower = term.lower()
        
        # 查找标准术语
        if term_lower in self.reverse_index:
            standard = self.reverse_index[term_lower]
            
            # 返回所有同义词
            if standard in self.sweetener_synonyms:
                return self.sweetener_synonyms[standard]
            elif standard in self.concept_expansion:
                return self.concept_expansion[standard]
        
        return []


# 使用示例
if __name__ == "__main__":
    expander = SweetnessQueryExpander()
    
    # 测试查询扩展
    test_queries = [
        "阿斯巴甜对健康的影响",
        "stevia的甜度",
        "糖醇的代谢",
        "甜味受体机制"
    ]
    
    for query in test_queries:
        result = expander.expand_query(query)
        print(f"\n原始查询: {result['original']}")
        print(f"匹配概念: {result['matched_concepts']}")
        print(f"扩展术语: {result['expanded_terms'][:5]}...")  # 只显示前5个
