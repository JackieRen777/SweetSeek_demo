#!/usr/bin/env python3
"""
SQLite元数据存储 - 用于快速ID查询
配合FAISS向量索引使用

Architecture:
1. FAISS: 向量检索 → Top-N ID列表
2. SQLite: ID查询 → 完整文档内容
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class MetadataDB:
    """SQLite元数据存储，支持按ID快速查询"""

    def __init__(self, db_path: str, *, read_only: bool = False, immutable: bool = False):
        self.db_path = Path(db_path)
        self.read_only = read_only
        self.immutable = immutable
        if read_only:
            if not self.db_path.is_file():
                raise FileNotFoundError(f"SQLite metadata database does not exist: {self.db_path}")
        else:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_db()

    def _init_db(self):
        """初始化数据库schema"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # 创建索引加速查询
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_doc_id
                ON documents(doc_id)
            """)
            conn.commit()

    @contextmanager
    def _get_connection(self):
        """上下文管理器获取数据库连接"""
        if self.read_only:
            immutable = "&immutable=1" if self.immutable else ""
            conn = sqlite3.connect(
                f"file:{self.db_path.resolve()}?mode=ro{immutable}", uri=True
            )
            conn.execute("PRAGMA query_only=ON")
        else:
            conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def insert_document(self, doc_id: str, content: str, metadata: Optional[Dict] = None):
        """插入单个文档"""
        self._require_writable()
        metadata_json = json.dumps(metadata) if metadata else None
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO documents (doc_id, content, metadata) VALUES (?, ?, ?)",
                (doc_id, content, metadata_json)
            )
            conn.commit()

    def insert_batch(self, documents: List[Dict[str, Any]]):
        """批量插入文档

        Args:
            documents: [{"doc_id": "xxx", "content": "xxx", "metadata": {...}}, ...]
        """
        self._require_writable()
        with self._get_connection() as conn:
            for doc in documents:
                metadata_json = json.dumps(doc.get("metadata")) if doc.get("metadata") else None
                conn.execute(
                    "INSERT OR REPLACE INTO documents (doc_id, content, metadata) VALUES (?, ?, ?)",
                    (doc["doc_id"], doc["content"], metadata_json)
                )
            conn.commit()
        logger.info(f"批量插入 {len(documents)} 条文档到SQLite")

    def get_by_id(self, doc_id: str) -> Optional[Dict]:
        """根据ID查询单个文档"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT doc_id, content, metadata FROM documents WHERE doc_id = ?",
                (doc_id,)
            ).fetchone()

            if row:
                return {
                    "doc_id": row["doc_id"],
                    "content": row["content"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else None
                }
            return None

    def get_by_ids(self, doc_ids: List[str]) -> List[Dict]:
        """根据ID列表批量查询文档(保持顺序)"""
        if not doc_ids:
            return []

        with self._get_connection() as conn:
            placeholders = ",".join(["?"] * len(doc_ids))
            rows = conn.execute(
                f"SELECT doc_id, content, metadata FROM documents WHERE doc_id IN ({placeholders})",
                doc_ids
            ).fetchall()

            # 构建ID到文档的映射
            doc_map = {}
            for row in rows:
                doc_map[row["doc_id"]] = {
                    "doc_id": row["doc_id"],
                    "content": row["content"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else None
                }

            # 按原始ID顺序返回
            return [doc_map[doc_id] for doc_id in doc_ids if doc_id in doc_map]

    def count(self) -> int:
        """返回文档总数"""
        with self._get_connection() as conn:
            return conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]

    def all_ids(self) -> List[str]:
        """Return chunk IDs for integrity checks and resumable migrations."""
        with self._get_connection() as conn:
            return [row[0] for row in conn.execute("SELECT doc_id FROM documents")]

    def delete_by_id(self, doc_id: str):
        """删除单个文档"""
        self._require_writable()
        with self._get_connection() as conn:
            conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
            conn.commit()

    def clear_all(self):
        """清空所有文档"""
        self._require_writable()
        with self._get_connection() as conn:
            conn.execute("DELETE FROM documents")
            conn.commit()
        logger.info("已清空SQLite数据库")

    def _require_writable(self) -> None:
        if self.read_only:
            raise RuntimeError(f"SQLite metadata database is read-only: {self.db_path}")
