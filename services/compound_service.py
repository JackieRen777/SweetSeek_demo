import pandas as pd
from thefuzz import fuzz, process
from typing import List, Dict, Optional, Any
import logging
import os

class CompoundService:
    def __init__(self, data_path: str = "data/compounds_sweet.xlsx"):
        self.logger = logging.getLogger("sweetseek.compound_service")
        self.data_path = data_path
        self._df = None
        self._load_data()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if self._df.empty:
            return {"total_count": 0}
        
        return {
            "total_count": len(self._df),
            # 可以添加其他统计，例如平均分子量等
        }

    def _load_data(self):
        """加载Excel数据"""
        try:
            if os.path.exists(self.data_path):
                # Load all columns, force some to string to prevent parsing errors
                self._df = pd.read_excel(self.data_path)
                # 填充NaN值为空字符串，避免后续处理出错
                self._df = self._df.fillna("")
                
                # 尝试标准化列名（如果存在用户指定的列）
                # 用户列: Compound Name, PubChem CID, MolecularFormula, MolecularWeight, CanonicalSMILES, ... Relative_Sweetness
                column_mapping = {
                    'Compound Name': 'name',
                    'PubChem CID': 'cid',
                    'MolecularFormula': 'formula',
                    'MolecularWeight': 'mw',
                    'CanonicalSMILES': 'smiles',
                    'Relative_Sweetness': 'sweetness',
                    'XLogP': 'logp',
                    'IUPACName': 'iupac_name',
                    'InChI': 'inchi',
                    'InChIKey': 'inchikey',
                    'IsomericSMILES': 'isomeric_smiles',
                    'TPSA': 'tpsa',
                    'HBondDonorCount': 'hbond_donor',
                    'HBondAcceptorCount': 'hbond_acceptor',
                    'RotatableBondCount': 'rotatable_bond',
                    'HeavyAtomCount': 'heavy_atom',
                    'QED_Value': 'qed',
                    'SA_Score': 'sa_score',
                    'Lipinski': 'lipinski'
                }
                
                # 重命名存在的列
                self._df = self._df.rename(columns=column_mapping)
                
                # 确保必要的列存在，如果不存在则使用默认值或保留原名
                if 'name' not in self._df.columns and 'Compound Name' not in self._df.columns:
                     # 兼容旧的测试数据格式
                     self.logger.warning("未找到 'Compound Name' 或 'name' 列，数据可能不完整")

                # 数据清洗：强制转换数值列
                numeric_cols = ['sweetness', 'mw', 'logp', 'cid', 'tpsa', 'hbond_donor', 'hbond_acceptor', 'rotatable_bond', 'heavy_atom', 'qed', 'sa_score', 'lipinski']
                for col in numeric_cols:
                    if col in self._df.columns:
                        self._df[col] = pd.to_numeric(self._df[col], errors='coerce').fillna(0)
                
                # 数据清洗：去重 (优先保留CID存在的)
                if 'cid' in self._df.columns:
                    initial_len = len(self._df)
                    # Don't drop duplicates if they might be isomers with same CID but different names
                    # Or keep them if names are different
                    # For now, let's keep all rows to ensure Glucose is loaded even if it shares CID with something else (unlikely for pure Glucose)
                    # self._df = self._df.drop_duplicates(subset=['cid'], keep='first')
                    pass 
                
                # 如果没有ID列，创建一个
                if 'id' not in self._df.columns:
                    # Use index as ID to ensure uniqueness and stability
                    self._df['id'] = range(1, len(self._df) + 1)

                self.logger.info(f"成功加载化合物数据，共 {len(self._df)} 条记录")
                
                # Log some sample names to verify
                if 'name' in self._df.columns:
                    self.logger.info(f"Sample compounds: {self._df['name'].head(5).tolist()}")
            else:
                self.logger.warning(f"数据文件不存在: {self.data_path}")
                self._df = pd.DataFrame()
        except Exception as e:
            self.logger.error(f"加载化合物数据失败: {e}")
            self._df = pd.DataFrame()

    def search(self, query: str, limit: int = 50, threshold: int = 60) -> List[Dict[str, Any]]:
        """
        搜索化合物
        :param query: 搜索查询词
        :param limit: 返回结果数量限制
        :param threshold: 相似度阈值 (0-100)
        :return: 匹配的化合物列表
        """
        if self._df.empty:
            return []
            
        if not query:
             # Return top N compounds if query is empty
             return self.get_all(limit)

        # 准备用于搜索的字典 {index: text}
        # 优先搜索 name (Compound Name)
        df_len = len(self._df)
        choices = {}
        
        # 确定要搜索的列
        search_cols = []
        # Add common name columns if they exist in your excel (check headers)
        potential_name_cols = ['name', 'common_name', 'iupac_name', 'synonyms', '中文名', 'Common Name']
        
        for col in potential_name_cols:
            if col in self._df.columns:
                search_cols.append(col)
            
        # 如果没有找到标准列，尝试使用所有字符串列
        if not search_cols:
            search_cols = [col for col in self._df.columns if self._df[col].dtype == 'object']

        # 构建搜索池
        for col_idx, col in enumerate(search_cols):
            values = self._df[col].astype(str).tolist()
            for i, val in enumerate(values):
                if val and val.strip():
                    # Key format: index + offset
                    key = i + (col_idx * df_len)
                    choices[key] = val
        
        # 使用thefuzz进行模糊匹配
        # 当传入字典时，返回格式: List[(match_string, score, key)]
        results = process.extract(query, choices, scorer=fuzz.token_set_ratio, limit=limit * 2)
        
        matched_indices = set()
        final_results = []
        
        for match, score, key in results:
            if score < threshold:
                continue
                
            # 计算原始DataFrame中的行索引
            original_idx = key % df_len
            col_idx = key // df_len
            match_source = search_cols[col_idx] if col_idx < len(search_cols) else "unknown"
            
            if original_idx in matched_indices:
                continue
                
            matched_indices.add(original_idx)
            if 0 <= original_idx < df_len:
                row = self._df.iloc[original_idx]
                item = row.to_dict()
                # 处理NaN和特殊值
                for k, v in item.items():
                    if pd.isna(v):
                        item[k] = ""
                
                item['match_score'] = score
                # 添加匹配来源说明
                item['match_source'] = match_source
                final_results.append(item)
            
            if len(final_results) >= limit:
                break
                
        return final_results

    def get_by_id(self, compound_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取化合物详情
        """
        if self._df.empty:
            return None
            
        try:
            # 尝试匹配 id 或 cid
            result = self._df[self._df['id'] == compound_id]
            if result.empty and 'cid' in self._df.columns:
                 result = self._df[self._df['cid'] == compound_id]
                 
            if not result.empty:
                item = result.iloc[0].to_dict()
                # 处理NaN
                for k, v in item.items():
                    if pd.isna(v):
                        item[k] = ""
                return item
        except Exception as e:
            self.logger.error(f"获取化合物ID {compound_id} 失败: {e}")
            
        return None

    def get_all(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取所有化合物"""
        if self._df.empty:
            return []
        
        data = self._df.head(limit).to_dict('records')
        # 处理NaN
        for item in data:
            for k, v in item.items():
                if pd.isna(v):
                    item[k] = ""
        return data
