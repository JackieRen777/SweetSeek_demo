#!/usr/bin/env python3
"""PDF Metadata Extractor

从PDF文件中提取元数据，包括期刊名、年份、标题、作者和DOI。
"""

import re
import logging
from typing import Dict, List, Optional
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFMetadataExtractor:
    """PDF元数据提取器"""
    
    # 常见期刊名称映射
    JOURNAL_PATTERNS = {
        'nutrients': 'Nutrients',
        'ijms': 'International Journal of Molecular Sciences',
        'life': 'Life',
        'scientific reports': 'Scientific Reports',
        'nature': 'Nature',
        'science': 'Science',
        'cell': 'Cell',
        'plos': 'PLOS ONE',
        'bmc': 'BMC',
        'diabetes care': 'Diabetes Care',
        'molecules': 'Molecules',
        'nihms': 'NIH Manuscript',
    }
    
    # DOI正则表达式
    DOI_PATTERN = re.compile(r'10\.\d{4,}/[^\s]+')
    
    # 年份正则表达式 (1900-2099)
    YEAR_PATTERN = re.compile(r'\b(19|20)\d{2}\b')
    
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
            
            # 尝试从文件名推断期刊
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
                    except:
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
                # 取最后一个匹配的年份（通常是发表年份）
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
        
        for pattern, journal_name in self.JOURNAL_PATTERNS.items():
            if pattern in text_lower:
                return journal_name
        
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
    test_pdf = 'food_research_data/papers/nutrients-12-03408_1.pdf'
    if Path(test_pdf).exists():
        metadata = extractor.extract_metadata(test_pdf)
        print("\n提取的元数据:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
