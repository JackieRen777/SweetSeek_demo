#!/usr/bin/env python3
"""提取Dual-Protein文献的元数据"""

import os
import re
from pathlib import Path
from metadata_storage import MetadataStorage
from knowledge_paths import get_domain_paths

def parse_dual_protein_filename(filename: str) -> dict:
    """
    解析Dual-Protein文献的文件名
    支持多种格式：
    1. Year-Journal-Title.pdf (如: 2021-FC-egg white gel.pdf)
    2. Year-Journal Abbr-Title.pdf (如: 2021-Food Function-co-delivery system.pdf)
    3. Year-Chinese Journal-Title.pdf (如: 2021-中国食品学报-卵白蛋白.pdf)
    4. Journal-Title-Year.pdf (如: foodhyd-Mixing animal-2016.pdf)
    5. Author 等 - Year - Title.pdf
    6. Title.pdf
    """
    name = Path(filename).stem
    
    # 格式1: Year-Journal Abbr-Title (如: 2021-FC-egg white gel.pdf)
    # 匹配: 年份-大写字母期刊缩写-标题
    pattern1 = r'^(\d{4})-([A-Z]{2,})-(.+)$'
    match = re.match(pattern1, name)
    if match:
        year, journal, title = match.groups()
        # 期刊缩写映射
        journal_map = {
            'FC': 'Food Chemistry',
            'FH': 'Food Hydrocolloids',
            'FB': 'Food Bioscience',
            'FRI': 'Food Research International',
            'LWT': 'LWT - Food Science and Technology',
            'US': 'Ultrasonics Sonochemistry',
            'JFE': 'Journal of Food Engineering',
            'JAFC': 'Journal of Agricultural and Food Chemistry'
        }
        journal_full = journal_map.get(journal, journal)
        return {
            'title': title.strip(),
            'journal': journal_full,
            'year': year,
            'authors': [],
            'doi': 'Not Available',
            'filename': filename,
            'source': 'filename_parsed_format1'
        }
    
    # 格式2: Year-Journal Full Name-Title (如: 2021-Food Function-co-delivery system.pdf)
    # 匹配: 年份-英文期刊名-标题
    pattern2 = r'^(\d{4})-([A-Za-z\s\.&]+?)-(.+)$'
    match = re.match(pattern2, name)
    if match:
        year, journal, title = match.groups()
        journal = journal.strip()
        # 检查是否是有效的期刊名（包含Food, Journal, Int等关键词）
        if any(keyword in journal for keyword in ['Food', 'J.', 'Int', 'Journal', 'Chem', 'Phys', 'LWT']):
            return {
                'title': title.strip(),
                'journal': journal,
                'year': year,
                'authors': [],
                'doi': 'Not Available',
                'filename': filename,
                'source': 'filename_parsed_format2'
            }
    
    # 格式3: Year-Chinese Journal-Title (如: 2021-中国食品学报-卵白蛋白.pdf)
    # 匹配: 年份-中文期刊名-标题
    pattern3 = r'^(\d{4})-([\u4e00-\u9fa5]+)-(.+)$'
    match = re.match(pattern3, name)
    if match:
        year, journal, title = match.groups()
        return {
            'title': title.strip(),
            'journal': journal.strip(),
            'year': year,
            'authors': [],
            'doi': 'Not Available',
            'filename': filename,
            'source': 'filename_parsed_format3_chinese'
        }
    
    # 格式4: Journal-Title-Year (如: foodhyd-Mixing animal-2016.pdf)
    pattern4 = r'^([a-z]+)-(.+)-(\d{4})$'
    match = re.match(pattern4, name, re.IGNORECASE)
    if match:
        journal, title, year = match.groups()
        journal_map = {
            'foodhyd': 'Food Hydrocolloids',
            'jafc': 'Journal of Agricultural and Food Chemistry',
            'jpcb': 'Journal of Physical Chemistry B',
            'jcim': 'Journal of Chemical Information and Modeling',
            'jpclett': 'Journal of Physical Chemistry Letters'
        }
        journal_full = journal_map.get(journal.lower(), journal)
        return {
            'title': title.strip(),
            'journal': journal_full,
            'year': year,
            'authors': [],
            'doi': 'Not Available',
            'filename': filename,
            'source': 'filename_parsed_format4'
        }
    
    # 格式5: Author 等 - Year - Title
    pattern5 = r'^(.+?)\s*(?:等|et al\.?)\s*-\s*(\d{4})\s*-\s*(.+)$'
    match = re.match(pattern5, name)
    if match:
        author_str, year, title = match.groups()
        authors = [author_str.strip()]
        return {
            'title': title.strip(),
            'journal': 'Unknown Journal',
            'year': year,
            'authors': authors,
            'doi': 'Not Available',
            'filename': filename,
            'source': 'filename_parsed_format5'
        }
    
    # 尝试从文件名中提取年份（即使格式不标准）
    year_match = re.search(r'(\d{4})', name)
    year = year_match.group(1) if year_match else 'N/A'
    
    # 格式6: 只有标题
    return {
        'title': name,
        'journal': 'Unknown Journal',
        'year': year,
        'authors': [],
        'doi': 'Not Available',
        'filename': filename,
        'source': 'filename_only'
    }

def extract_metadata_for_dual_protein():
    """为Dual-Protein文献提取元数据"""
    
    # 文献目录
    paths = get_domain_paths("dual_protein")
    papers_dir = paths.papers
    
    if not papers_dir.exists():
        print(f"❌ 目录不存在: {papers_dir}")
        return
    
    # 获取所有PDF文件
    pdf_files = list(papers_dir.glob('*.pdf'))
    print(f"找到 {len(pdf_files)} 个PDF文件")
    
    # 初始化元数据存储
    metadata_storage = MetadataStorage(storage_path=str(paths.metadata))
    
    # 提取并保存元数据
    success_count = 0
    for pdf_file in pdf_files:
        try:
            # 解析文件名
            metadata = parse_dual_protein_filename(pdf_file.name)
            
            # 使用绝对路径作为键
            file_path = str(pdf_file.absolute())
            
            # 保存元数据
            metadata_storage.save_metadata(file_path, metadata)
            
            success_count += 1
            print(f"✅ [{success_count}/{len(pdf_files)}] {pdf_file.name[:60]}...")
            
        except Exception as e:
            print(f"❌ 处理失败: {pdf_file.name} - {e}")
    
    print(f"\n完成！成功提取 {success_count}/{len(pdf_files)} 个文献的元数据")
    
    # 显示统计
    stats = metadata_storage.get_stats()
    print(f"\n元数据存储统计:")
    print(f"  - 总文件数: {stats['total_files']}")
    print(f"  - 存储路径: {stats['storage_path']}")
    print(f"  - 存储大小: {stats['storage_size']} bytes")
    
    # 显示示例
    print(f"\n前3个元数据示例:")
    all_meta = metadata_storage.get_all_metadata()
    for i, (path, meta) in enumerate(list(all_meta.items())[:3], 1):
        print(f"\n{i}. 文件: {Path(path).name}")
        print(f"   标题: {meta.get('title', 'N/A')}")
        print(f"   期刊: {meta.get('journal', 'N/A')}")
        print(f"   年份: {meta.get('year', 'N/A')}")
        print(f"   来源: {meta.get('source', 'N/A')}")

if __name__ == '__main__':
    extract_metadata_for_dual_protein()
