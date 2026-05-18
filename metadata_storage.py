#!/usr/bin/env python3
"""Metadata Storage Manager

管理PDF文献元数据的持久化存储。
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from path_utils import normalize_for_storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetadataStorage:
    """元数据存储管理器"""
    
    def __init__(self, storage_path: str = "./chroma_db/metadata.json"):
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
        
        if not self.storage_path.exists():
            backup_path = self.storage_path.with_suffix('.json.bak')
            if backup_path.exists():
                try:
                    import shutil
                    shutil.copy2(backup_path, self.storage_path)
                    logger.info(f"从备份恢复元数据存储文件: {self.storage_path}")
                except Exception:
                    self._save_to_disk({})
                    logger.info(f"创建元数据存储文件: {self.storage_path}")
            else:
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

        backup_path = self.storage_path.with_suffix('.json.bak')
        try:
            if backup_path.exists():
                with open(backup_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"从备份加载了 {len(data)} 个文件的元数据")
                    return data
        except Exception as e:
            logger.error(f"从备份加载元数据失败: {str(e)}")
        
        return {}
    
    def _save_to_disk(self, data: Dict):
        """保存元数据到磁盘"""
        import shutil
        import tempfile
        
        try:
            backup_path = self.storage_path.with_suffix('.json.bak')
            if self.storage_path.exists():
                shutil.copy2(self.storage_path, backup_path)

            fd, temp_path = tempfile.mkstemp(dir=self.storage_path.parent, text=True)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temp_path, self.storage_path)
                logger.debug(f"元数据已保存到 {self.storage_path}")
                
            except Exception as write_error:
                os.unlink(temp_path)
                raise write_error
            
        except Exception as e:
            logger.error(f"保存元数据失败: {str(e)}")
            backup_path = self.storage_path.with_suffix('.json.bak')
            if backup_path.exists():
                try:
                    shutil.copy2(backup_path, self.storage_path)
                    logger.info("已从备份恢复元数据")
                except Exception as restore_error:
                    logger.error(f"恢复备份失败: {str(restore_error)}")
    
    def save_metadata(self, file_path: str, metadata: Dict) -> None:
        """
        保存文件的元数据

        Args:
            file_path: 文件路径（作为键）
            metadata: 元数据字典
        """
        normalized_path = normalize_for_storage(file_path)

        metadata['last_modified'] = datetime.now().isoformat()
        metadata['file_path'] = normalized_path

        self._metadata_cache[normalized_path] = metadata
        self._save_to_disk(self._metadata_cache)

        logger.info(f"保存元数据: {metadata.get('title', 'Unknown')[:50]}...")
    
    def _parse_filename_metadata(self, filename: str) -> Optional[Dict]:
        """
        从文件名解析元数据
        格式: Author 等 - Year - Title.pdf 或 Author et al - Year - Title.pdf
        """
        import re
        # 移除扩展名
        name = Path(filename).stem
        
        # 尝试匹配: Author (等/et al) - Year - Title
        # 兼容多种分隔符和格式
        pattern = r'^(.+?)\s*(?:等|et al\.?|and others)?\s*-\s*(\d{4})\s*-\s*(.+)$'
        match = re.match(pattern, name)
        
        if match:
            author_str, year, title = match.groups()
            # 简单的作者处理
            authors = [author_str.strip()]
            
            return {
                'title': title.strip(),
                'authors': authors,
                'year': year,
                'journal': 'Unknown Journal', # 无法从文件名获知
                'doi': 'Not Available',
                'filename': filename,
                'source': 'filename_parsed',
                'file_path': filename
            }
        return None

    def get_metadata(self, file_path: str) -> Optional[Dict]:
        """
        获取文件的元数据
        支持路径模糊匹配和文件名解析回退

        Args:
            file_path: 文件路径

        Returns:
            元数据字典，如果不存在返回None
        """
        # 1. 尝试归一化相对路径匹配
        rel_key = normalize_for_storage(file_path)
        if rel_key in self._metadata_cache:
            return self._metadata_cache[rel_key]

        # 2. 尝试原始 POSIX 路径（向后兼容迁移前数据）
        raw_posix = str(Path(file_path).as_posix())
        if raw_posix in self._metadata_cache:
            return self._metadata_cache[raw_posix]

        # 3. 尝试通过文件名匹配（忽略路径差异）
        target_filename = Path(file_path).name
        for stored_path, meta in self._metadata_cache.items():
            if Path(stored_path).name == target_filename:
                logger.debug(f"通过文件名匹配找到元数据: {target_filename}")
                return meta

        # 4. 尝试从文件名解析（最后的回退策略）
        parsed_meta = self._parse_filename_metadata(target_filename)
        if parsed_meta:
            logger.info(f"从文件名解析元数据成功: {target_filename}")
            return parsed_meta

        return None
    
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
        normalized_path = normalize_for_storage(file_path)

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
        normalized_path = normalize_for_storage(file_path)
        if normalized_path in self._metadata_cache:
            return True
        # Fallback: filename match
        target_filename = Path(file_path).name
        for stored_path in self._metadata_cache:
            if Path(stored_path).name == target_filename:
                return True
        return False

    def migrate_to_relative_paths(self) -> int:
        """One-time migration: convert absolute-path keys to relative paths."""
        migrated = 0
        new_cache: Dict = {}
        for old_key, meta in self._metadata_cache.items():
            new_key = normalize_for_storage(old_key)
            if new_key != old_key:
                migrated += 1
            meta['file_path'] = new_key
            if new_key not in new_cache:
                new_cache[new_key] = meta

        if migrated > 0:
            self._metadata_cache = new_cache
            self._save_to_disk(self._metadata_cache)
            logger.info(f"Migrated {migrated} metadata keys from absolute to relative paths")
        return migrated
    
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
