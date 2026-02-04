#!/usr/bin/env python3
"""PDF Metadata Extractor

从PDF文件中提取元数据，包括期刊名、年份、标题、作者和DOI。
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFMetadataExtractor:
    """PDF元数据提取器"""
    
    # 常见期刊名称映射（扩展版）
    JOURNAL_PATTERNS = {
        # 高影响力期刊
        'nature': 'Nature',
        'science': 'Science',
        'cell': 'Cell',
        'lancet': 'The Lancet',
        'jama': 'JAMA',
        'nejm': 'New England Journal of Medicine',
        
        # 食品科学期刊
        'food chemistry': 'Food Chemistry',
        'food research international': 'Food Research International',
        'journal of agricultural and food chemistry': 'Journal of Agricultural and Food Chemistry',
        'food hydrocolloids': 'Food Hydrocolloids',
        'food quality and preference': 'Food Quality and Preference',
        'lwt': 'LWT - Food Science and Technology',
        'trends in food science': 'Trends in Food Science & Technology',
        'comprehensive reviews in food science': 'Comprehensive Reviews in Food Science and Food Safety',
        'journal of food science': 'Journal of Food Science',
        'food science and nutrition': 'Food Science & Nutrition',
        
        # 营养学期刊
        'nutrients': 'Nutrients',
        'nutrition': 'Nutrition',
        'american journal of clinical nutrition': 'American Journal of Clinical Nutrition',
        'journal of nutrition': 'Journal of Nutrition',
        'british journal of nutrition': 'British Journal of Nutrition',
        'frontiers in nutrition': 'Frontiers in Nutrition',
        
        # 感官科学期刊
        'chemical senses': 'Chemical Senses',
        'physiology & behavior': 'Physiology & Behavior',
        'appetite': 'Appetite',
        
        # 综合期刊
        'plos one': 'PLOS ONE',
        'plos': 'PLOS ONE',
        'scientific reports': 'Scientific Reports',
        'bmc': 'BMC',
        'frontiers': 'Frontiers',
        
        # 分子生物学期刊
        'ijms': 'International Journal of Molecular Sciences',
        'molecules': 'Molecules',
        'life': 'Life',
        'foods': 'Foods',
        
        # 其他
        'diabetes care': 'Diabetes Care',
        'nihms': 'NIH Manuscript',
        'proceedings': 'Proceedings',
    }
    
    # DOI正则表达式
    DOI_PATTERN = re.compile(r'10\.\d{4,}/[^\s]+')
    
    # 年份正则表达式 (1900-2099)
    YEAR_PATTERN = re.compile(r'\b(?:19|20)\d{2}\b')
    
    def extract_metadata(self, pdf_path: str) -> Dict[str, any]:
        """
        从PDF文件提取元数据
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            包含元数据的字典
        """
        logger.info(f"开始提取元数据: {pdf_path}")
        
        # 初始化默认值
        metadata = {
            'journal': 'Unknown Journal',
            'year': 'N/A',
            'title': 'Unknown Title',
            'authors': [],
            'doi': 'Not Available',
            'filename': Path(pdf_path).name
        }
        
        try:
            # 尝试从PDF元数据提取
            pdf_metadata = self.extract_from_pdf_metadata(pdf_path)
            metadata.update({k: v for k, v in pdf_metadata.items() if v})
            
            # 如果元数据不完整，从第一页提取
            if metadata['title'] == 'Unknown Title' or metadata['doi'] == 'Not Available':
                first_page_data = self.extract_from_first_page(pdf_path)
                # 只更新缺失的字段
                for key, value in first_page_data.items():
                    if value and (not metadata.get(key) or metadata[key] in ['Unknown Journal', 'Unknown Title', 'Not Available', 'N/A']):
                        metadata[key] = value
            
            # 尝试从DOI推断期刊（如果期刊仍然未知）
            if metadata['journal'] == 'Unknown Journal' and metadata['doi'] != 'Not Available':
                journal_from_doi = self._extract_journal_from_doi(metadata['doi'])
                if journal_from_doi:
                    metadata['journal'] = journal_from_doi
            
            # 尝试从文件名推断期刊（最后的备选）
            if metadata['journal'] == 'Unknown Journal':
                metadata['journal'] = self._extract_journal_from_filename(pdf_path)
            
            logger.info(f"元数据提取完成: {metadata['title'][:50]}...")
            
        except Exception as e:
            logger.error(f"提取元数据失败 {pdf_path}: {str(e)}")
        
        return metadata
    
    def extract_from_pdf_metadata(self, pdf_path: str) -> Dict[str, any]:
        """从PDF元数据字段提取信息"""
        metadata = {}
        
        try:
            reader = PdfReader(pdf_path)
            pdf_info = reader.metadata
            
            if pdf_info:
                # 提取标题（但要验证是否是有效标题）
                if pdf_info.title:
                    title = pdf_info.title.strip()
                    # 如果标题看起来像文件名（包含.pdf或太短），忽略它
                    if '.pdf' not in title.lower() and len(title) > 15:
                        metadata['title'] = title
                
                # 提取作者
                if pdf_info.author:
                    authors_str = pdf_info.author.strip()
                    metadata['authors'] = self._parse_authors(authors_str)
                
                # 提取创建日期中的年份
                if pdf_info.creation_date:
                    try:
                        year = pdf_info.creation_date.year
                        if 1900 <= year <= 2099:
                            metadata['year'] = str(year)
                    except Exception:
                        pass
                
                # 检查subject或keywords中的DOI
                if pdf_info.subject:
                    doi_match = self.DOI_PATTERN.search(pdf_info.subject)
                    if doi_match:
                        metadata['doi'] = doi_match.group(0)
                
        except Exception as e:
            logger.warning(f"读取PDF元数据失败: {str(e)}")
        
        return metadata
    
    def extract_from_first_page(self, pdf_path: str) -> Dict[str, any]:
        """从PDF第一页文本提取信息"""
        metadata = {}
        
        try:
            reader = PdfReader(pdf_path)
            if len(reader.pages) == 0:
                return metadata
            
            # 读取第一页文本
            first_page = reader.pages[0]
            text = first_page.extract_text()
            
            if not text:
                return metadata
            
            # 提取DOI
            doi_match = self.DOI_PATTERN.search(text)
            if doi_match:
                metadata['doi'] = doi_match.group(0).rstrip('.,;')
            
            # 提取年份
            year_matches = self.YEAR_PATTERN.findall(text)
            if year_matches:
                metadata['year'] = year_matches[-1]
            
            # 提取标题（通常在第一页前几行，字体较大）
            lines = text.split('\n')
            title_candidates = []
            for i, line in enumerate(lines[:15]):  # 看前15行
                line = line.strip()
                # 跳过太短或太长的行
                if len(line) < 20 or len(line) > 300:
                    continue
                # 跳过包含特定关键词的行（可能是作者、日期等）
                skip_keywords = ['doi:', 'http', 'www', '©', 'copyright', 'published', 'received']
                if any(kw in line.lower() for kw in skip_keywords):
                    continue
                title_candidates.append(line)
            
            # 合并多行标题
            if title_candidates:
                # 如果第一行和第二行看起来是连续的，合并它们
                if len(title_candidates) >= 2:
                    first_line = title_candidates[0]
                    second_line = title_candidates[1]
                    # 如果第一行不以句号结尾，且第二行首字母大写，可能是多行标题
                    if not first_line.endswith('.') and second_line[0].isupper():
                        metadata['title'] = f"{first_line} {second_line}"
                    else:
                        metadata['title'] = first_line
                else:
                    metadata['title'] = title_candidates[0]
            
            # 尝试提取期刊名
            journal = self._extract_journal_from_text(text)
            if journal:
                metadata['journal'] = journal
            
            # 尝试提取作者（通常在标题后）
            authors = self._extract_authors_from_text(text)
            if authors:
                metadata['authors'] = authors
                
        except Exception as e:
            logger.warning(f"从第一页提取信息失败: {str(e)}")
        
        return metadata
    
    def _extract_journal_from_filename(self, pdf_path: str) -> str:
        """从文件名推断期刊名"""
        filename = Path(pdf_path).stem.lower()
        
        for pattern, journal_name in self.JOURNAL_PATTERNS.items():
            if pattern in filename:
                return journal_name
        
        return 'Unknown Journal'
    
    def _extract_journal_from_text(self, text: str) -> Optional[str]:
        """从文本中提取期刊名"""
        text_lower = text.lower()
        
        # 按匹配长度排序，优先匹配长的期刊名
        sorted_patterns = sorted(self.JOURNAL_PATTERNS.items(), key=lambda x: len(x[0]), reverse=True)
        
        for pattern, journal_name in sorted_patterns:
            if pattern in text_lower:
                return journal_name
        
        return None
    
    def _extract_journal_from_doi(self, doi: str) -> Optional[str]:
        """从DOI推断期刊名"""
        if not doi or doi == 'Not Available':
            return None
        
        doi_lower = doi.lower()
        
        # 特殊期刊的完整DOI模式匹配（扩展版）
        special_journals = {
            '10.1038/srep': 'Scientific Reports',
            '10.1038/s41538': 'npj Science of Food',
            '10.1038/s41467': 'Nature Communications',
            '10.1038/s41586': 'Nature',
            '10.1038/s41598': 'Scientific Reports',
            '10.1038/ijo': 'International Journal of Obesity',
            '10.1017/s0029665': 'Proceedings of the Nutrition Society',
            '10.1039/': 'Royal Society of Chemistry',
        }
        
        # 先检查特殊期刊
        for pattern, journal in special_journals.items():
            if doi_lower.startswith(pattern):
                return journal
        
        # DOI前缀到出版商/期刊的映射（扩展版）
        doi_publisher_map = {
            '10.3390': 'MDPI',
            '10.1038': 'Nature Publishing Group',
            '10.1126': 'Science',
            '10.1016': 'Elsevier',
            '10.1371': 'PLOS',
            '10.3389': 'Frontiers',
            '10.1186': 'BMC',
            '10.1002': 'Wiley',
            '10.1021': 'ACS Publications',
            '10.1093': 'Oxford University Press',
            '10.1080': 'Taylor & Francis',
            '10.1007': 'Springer',
            '10.1111': 'Wiley',
            '10.1177': 'SAGE Publications',
            '10.1152': 'American Physiological Society',
            '10.2337': 'American Diabetes Association',
            '10.21203': 'Research Square',
            '10.1017': 'Cambridge University Press',
            '10.1039': 'Royal Society of Chemistry',
        }
        
        # 检查DOI前缀
        for prefix, publisher in doi_publisher_map.items():
            if doi_lower.startswith(prefix):
                # 如果是MDPI，尝试从DOI中提取具体期刊
                if prefix == '10.3390':
                    # DOI格式: 10.3390/foods14061034
                    parts = doi.split('/')
                    if len(parts) >= 2:
                        journal_code = ''.join([c for c in parts[1] if c.isalpha()])
                        if journal_code:
                            # 常见MDPI期刊
                            mdpi_journals = {
                                'nutrients': 'Nutrients',
                                'foods': 'Foods',
                                'molecules': 'Molecules',
                                'ijms': 'International Journal of Molecular Sciences',
                                'sensors': 'Sensors',
                                'life': 'Life',
                            }
                            return mdpi_journals.get(journal_code.lower(), f'MDPI - {journal_code.capitalize()}')
                
                # 如果是Springer，尝试识别具体期刊
                elif prefix == '10.1007':
                    # 常见Springer期刊代码
                    springer_journals = {
                        's00217': 'European Food Research and Technology',
                        's10068': 'Food Science and Biotechnology',
                        's11694': 'Journal of Food Measurement and Characterization',
                        's11248': 'Transgenic Research',
                        's002170': 'European Food Research and Technology',
                    }
                    for code, journal in springer_journals.items():
                        if code in doi_lower:
                            return journal
                
                return publisher
        
        return None
    
    def _parse_authors(self, authors_str: str) -> List[str]:
        """解析作者字符串为列表"""
        if not authors_str:
            return []
        
        # 尝试不同的分隔符
        separators = [';', ',', ' and ', '&']
        authors = [authors_str]
        
        for sep in separators:
            if sep in authors_str:
                authors = [a.strip() for a in authors_str.split(sep)]
                break
        
        # 清理和格式化
        cleaned_authors = []
        for author in authors:
            author = author.strip()
            if author and len(author) > 2:
                cleaned_authors.append(author)
        
        return cleaned_authors[:10]  # 最多保留10个作者
    
    def _extract_authors_from_text(self, text: str) -> List[str]:
        """从文本中提取作者列表"""
        # 这是一个简化的实现，实际可能需要更复杂的解析
        lines = text.split('\n')
        
        # 查找包含常见作者模式的行
        author_patterns = [
            r'[A-Z][a-z]+\s+[A-Z]\.',  # Smith J.
            r'[A-Z][a-z]+,\s+[A-Z]\.',  # Smith, J.
        ]
        
        authors = []
        for line in lines[:20]:  # 只看前20行
            line = line.strip()
            for pattern in author_patterns:
                if re.search(pattern, line):
                    # 简单提取，可能需要改进
                    potential_authors = re.findall(r'[A-Z][a-z]+(?:,?\s+[A-Z]\.)+', line)
                    authors.extend(potential_authors)
                    if len(authors) >= 5:
                        break
            if len(authors) >= 5:
                break
        
        return authors[:5] if authors else []


# 测试函数
if __name__ == '__main__':
    extractor = PDFMetadataExtractor()
    
    # 测试一个PDF文件
    test_pdf = 'sweet_related_paper/papers/nutrients-12-03408_1.pdf'
    if Path(test_pdf).exists():
        metadata = extractor.extract_metadata(test_pdf)
        print("\n提取的元数据:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
