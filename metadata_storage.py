#!/usr/bin/env python3
"""Metadata Storage Manager

管理PDF文献元数据的持久化存储。
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetadataStorage:
    """元数据存储管理器"""
    
    def __init__(self, storage_path: str = "./storage/metadata.json"):
        """
        初始化存储管理器
        
        Args:
            storage_path: 元数据JSON文件路径
        """
        self.storage_path = Path(storage_path)
        self._ensure_storage_dir()
        self._metadata_cache = self._load_metadata()
    
    def _ensure_storage_dir(self):
        """确保存储目录存在"""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 如果文件不存在，创建空的JSON文件
        if not self.storage_path.exists():
            self._save_to_disk({})
            logger.info(f"创建元数据存储文件: {self.storage_path}")
    
    def _load_metadata(self) -> Dict:
        """从磁盘加载元数据"""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"加载了 {len(data)} 个文件的元数据")
                    return data
        except Exception as e:
            logger.error(f"加载元数据失败: {str(e)}")
        
        return {}
    
    def _save_to_disk(self, data: Dict):
        """保存元数据到磁盘"""
        try:
            # 创建备份
            if self.storage_path.exists():
                backup_path = self.storage_path.with_suffix('.json.bak')
                self.storage_path.rename(backup_path)
            
            # 保存新数据
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 删除备份
            backup_path = self.storage_path.with_suffix('.json.bak')
            if backup_path.exists():
                backup_path.unlink()
                
            logger.debug(f"元数据已保存到 {self.storage_path}")
            
        except Exception as e:
            logger.error(f"保存元数据失败: {str(e)}")
            # 尝试恢复备份
            backup_path = self.storage_path.with_suffix('.json.bak')
            if backup_path.exists():
                backup_path.rename(self.storage_path)
                logger.info("已从备份恢复元数据")
    
    def save_metadata(self, file_path: str, metadata: Dict) -> None:
        """
        保存文件的元数据
        
        Args:
            file_path: 文件路径（作为键）
            metadata: 元数据字典
        """
        # 标准化文件路径
        normalized_path = str(Path(file_path).as_posix())
        
        # 添加时间戳
        metadata['last_modified'] = datetime.now().isoformat()
        metadata['file_path'] = normalized_path
        
        # 更新缓存
        self._metadata_cache[normalized_path] = metadata
        
        # 保存到磁盘
        self._save_to_disk(self._metadata_cache)
        
        logger.info(f"保存元数据: {metadata.get('title', 'Unknown')[:50]}...")
    
    def get_metadata(self, file_path: str) -> Optional[Dict]:
        """
        获取文件的元数据
        
        Args:
            file_path: 文件路径
            
        Returns:
            元数据字典，如果不存在返回None
        """
        normalized_path = str(Path(file_path).as_posix())
        return self._metadata_cache.get(normalized_path)
    
    def get_all_metadata(self) -> Dict:
        """
        获取所有文件的元数据
        
        Returns:
            所有元数据的字典
        """
        return self._metadata_cache.copy()
    
    def update_metadata(self, file_path: str, metadata: Dict) -> None:
        """
        更新文件的元数据
        
        Args:
            file_path: 文件路径
            metadata: 新的元数据字典
        """
        self.save_metadata(file_path, metadata)
    
    def delete_metadata(self, file_path: str) -> bool:
        """
        删除文件的元数据
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否成功删除
        """
        normalized_path = str(Path(file_path).as_posix())
        
        if normalized_path in self._metadata_cache:
            del self._metadata_cache[normalized_path]
            self._save_to_disk(self._metadata_cache)
            logger.info(f"删除元数据: {file_path}")
            return True
        
        return False
    
    def has_metadata(self, file_path: str) -> bool:
        """
        检查文件是否有元数据
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否存在元数据
        """
        normalized_path = str(Path(file_path).as_posix())
        return normalized_path in self._metadata_cache
    
    def get_stats(self) -> Dict:
        """
        获取存储统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'total_files': len(self._metadata_cache),
            'storage_path': str(self.storage_path),
            'storage_size': self.storage_path.stat().st_size if self.storage_path.exists() else 0
        }


# 测试函数
if __name__ == '__main__':
    storage = MetadataStorage()
    
    # 测试保存
    test_metadata = {
        'journal': 'Test Journal',
        'year': '2024',
        'title': 'Test Article',
        'authors': ['Author A', 'Author B'],
        'doi': '10.1234/test',
        'filename': 'test.pdf'
    }
    
    storage.save_metadata('test/path/test.pdf', test_metadata)
    
    # 测试读取
    retrieved = storage.get_metadata('test/path/test.pdf')
    print("\n检索的元数据:")
    print(json.dumps(retrieved, indent=2, ensure_ascii=False))
    
    # 测试统计
    stats = storage.get_stats()
    print("\n存储统计:")
    print(json.dumps(stats, indent=2))
