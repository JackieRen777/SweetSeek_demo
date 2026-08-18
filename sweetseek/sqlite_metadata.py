"""
SQLite元数据存储 - 配合FAISS索引使用
流程：FAISS检索 → 获取Top-N ID → SQLite查询详情
"""
import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class SQLiteMetadataStore:
    """轻量级SQLite元数据存储"""

    def __init__(self, db_path: str = "data/metadata.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self._init_db()

    def _init_db(self):
        """初始化数据库表结构"""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # 返回字典格式

        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY,
                file_path TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(file_path, chunk_index)
            )
        """)

        # 创建索引加速查询
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_path
            ON documents(file_path)
        """)

        self.conn.commit()
        logger.info(f"SQLite数据库初始化完成: {self.db_path}")

    def insert_batch(self, documents: List[Dict[str, Any]]):
        """批量插入文档"""
        cursor = self.conn.cursor()

        for doc in documents:
            metadata_json = json.dumps(doc.get('metadata', {}), ensure_ascii=False)

            cursor.execute("""
                INSERT OR REPLACE INTO documents
                (id, file_path, chunk_index, content, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                doc['id'],
                doc['file_path'],
                doc['chunk_index'],
                doc['content'],
                metadata_json
            ))

        self.conn.commit()
        logger.info(f"批量插入 {len(documents)} 条文档")

    def get_by_ids(self, doc_ids: List[int]) -> List[Dict[str, Any]]:
        """根据ID列表批量查询文档"""
        if not doc_ids:
            return []

        placeholders = ','.join('?' * len(doc_ids))
        cursor = self.conn.cursor()

        cursor.execute(f"""
            SELECT id, file_path, chunk_index, content, metadata
            FROM documents
            WHERE id IN ({placeholders})
        """, doc_ids)

        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row['id'],
                'file_path': row['file_path'],
                'chunk_index': row['chunk_index'],
                'content': row['content'],
                'metadata': json.loads(row['metadata']) if row['metadata'] else {}
            })

        return results

    def get_by_file(self, file_path: str) -> List[Dict[str, Any]]:
        """查询某个文件的所有chunks"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, file_path, chunk_index, content, metadata
            FROM documents
            WHERE file_path = ?
            ORDER BY chunk_index
        """, (file_path,))

        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row['id'],
                'file_path': row['file_path'],
                'chunk_index': row['chunk_index'],
                'content': row['content'],
                'metadata': json.loads(row['metadata']) if row['metadata'] else {}
            })

        return results

    def count(self) -> int:
        """统计文档总数"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents")
        return cursor.fetchone()[0]

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
