#!/usr/bin/env python3
"""增量索引管理器 - 只处理新添加的文献"""

import os
import json
from pathlib import Path
from typing import List, Set
from llama_index.core import SimpleDirectoryReader
from persistent_storage import rag_system
from pdf_metadata_extractor import PDFMetadataExtractor
from metadata_storage import MetadataStorage

class IncrementalIndexer:
    """增量索引管理器"""
    
    def __init__(self, 
                 data_dir: str = "./food_research_data",
                 tracking_file: str = "./storage/indexed_files.json"):
        self.data_dir = data_dir
        self.tracking_file = tracking_file
        self.indexed_files = self._load_tracking()
        self.metadata_extractor = PDFMetadataExtractor()
        self.metadata_storage = MetadataStorage()
    
    def _load_tracking(self) -> Set[str]:
        """加载已索引文件列表"""
        if os.path.exists(self.tracking_file):
            try:
                with open(self.tracking_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            except Exception as e:
                print(f"加载跟踪文件失败: {e}")
                return set()
        return set()
    
    def _save_tracking(self):
        """保存已索引文件列表"""
        os.makedirs(os.path.dirname(self.tracking_file), exist_ok=True)
        with open(self.tracking_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.indexed_files), f, indent=2, ensure_ascii=False)
    
    def get_all_files(self) -> List[str]:
        """获取所有支持的文件"""
        all_files = []
        supported_extensions = ('.pdf', '.docx', '.txt', '.md', '.csv', '.json')
        
        for root, dirs, files in os.walk(self.data_dir):
            for f in files:
                if f.startswith('.'):
                    continue
                if f.lower().endswith(supported_extensions):
                    full_path = os.path.abspath(os.path.join(root, f))
                    all_files.append(full_path)
        
        return all_files
    
    def get_new_files(self) -> List[str]:
        """检测新文件"""
        all_files = self.get_all_files()
        new_files = [f for f in all_files if f not in self.indexed_files]
        return new_files
    
    def extract_metadata_for_new_files(self, new_files: List[str]):
        """为新PDF文件提取元数据"""
        pdf_count = 0
        for file_path in new_files:
            if file_path.lower().endswith('.pdf'):
                try:
                    if not self.metadata_storage.has_metadata(file_path):
                        print(f"提取元数据: {os.path.basename(file_path)}")
                        metadata = self.metadata_extractor.extract_metadata(file_path)
                        self.metadata_storage.save_metadata(file_path, metadata)
                        pdf_count += 1
                except Exception as e:
                    print(f"元数据提取失败 {file_path}: {e}")
        
        if pdf_count > 0:
            print(f"成功提取 {pdf_count} 个PDF文件的元数据")
    
    def add_new_documents(self) -> bool:
        """增量添加新文档到索引"""
        print("=" * 60)
        print("增量索引更新")
        print("=" * 60)
        
        # 检测新文件
        new_files = self.get_new_files()
        
        if not new_files:
            print("✅ 没有新文件需要索引")
            return True
        
        print(f"\n📁 发现 {len(new_files)} 个新文件:")
        for f in new_files[:5]:
            print(f"   - {os.path.basename(f)}")
        if len(new_files) > 5:
            print(f"   ... 还有 {len(new_files) - 5} 个文件")
        
        # 确保索引已初始化
        if rag_system.index is None:
            print("\n⚠️  索引未初始化，正在加载...")
            rag_system.load_or_create_index()
        
        # 提取元数据
        print("\n📊 提取PDF元数据...")
        self.extract_metadata_for_new_files(new_files)
        
        # 读取新文件
        print("\n📖 读取新文档...")
        reader = SimpleDirectoryReader(input_files=new_files)
        new_docs = reader.load_data()
        print(f"✅ 读取到 {len(new_docs)} 个文档块")
        
        # 增量添加到索引
        print("\n🔄 添加到索引...")
        success = rag_system.add_documents(new_docs)
        
        if success:
            # 更新跟踪列表
            self.indexed_files.update(new_files)
            self._save_tracking()
            print("\n✅ 增量索引更新成功！")
            print(f"📊 当前已索引文件数: {len(self.indexed_files)}")
        else:
            print("\n❌ 增量索引更新失败")
        
        print("=" * 60)
        return success
    
    def rebuild_tracking(self):
        """重建跟踪文件（基于当前所有文件）"""
        all_files = self.get_all_files()
        self.indexed_files = set(all_files)
        self._save_tracking()
        print(f"✅ 跟踪文件已重建，共 {len(all_files)} 个文件")

# 命令行使用
if __name__ == "__main__":
    import sys
    
    indexer = IncrementalIndexer()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--rebuild-tracking":
        # 重建跟踪文件
        indexer.rebuild_tracking()
    else:
        # 增量添加新文档
        indexer.add_new_documents()
