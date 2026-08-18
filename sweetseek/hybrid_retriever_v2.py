#!/usr/bin/env python3
"""
FAISS + SQLite 混合检索器

Architecture:
┌─────────────────────────────────────┐
│  查询请求 (Query)                   │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│  Step 1: FAISS向量检索              │
│  → 输入: query_embedding            │
│  → 输出: Top-N ID列表 + 相似度分数  │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│  Step 2: SQLite元数据查询           │
│  → 输入: ID列表                     │
│  → 输出: 完整文档内容 + 元数据      │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│  返回前端                           │
└─────────────────────────────────────┘

优势:
- FAISS: 快速向量相似度计算(100ms内)
- SQLite: 快速ID查询(B+树索引)
- 关注点分离: 向量检索 vs 数据存储
"""

import logging
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path

try:
    import faiss
except ImportError:
    faiss = None

from sweetseek.metadata_db import MetadataDB

logger = logging.getLogger(__name__)


class HybridRetriever:
    """FAISS向量索引 + SQLite元数据存储的混合检索器"""

    def __init__(
        self,
        faiss_index_path: str,
        sqlite_db_path: str,
        embedding_dim: int = 768,
        read_only: bool = False,
    ):
        """
        Args:
            faiss_index_path: FAISS索引文件路径
            sqlite_db_path: SQLite数据库路径
            embedding_dim: 向量维度
        """
        if faiss is None:
            raise ImportError("需要安装faiss-cpu: pip install faiss-cpu")

        self.faiss_index_path = Path(faiss_index_path)
        self.sqlite_db_path = Path(sqlite_db_path)
        self.embedding_dim = embedding_dim

        # 初始化SQLite
        self.metadata_db = MetadataDB(
            str(sqlite_db_path), read_only=read_only, immutable=read_only
        )

        # FAISS索引(延迟加载)
        self.faiss_index: Optional[faiss.Index] = None
        self.doc_ids: List[str] = []  # 与FAISS索引对应的文档ID列表

    def build_index(
        self,
        documents: List[Dict],
        embeddings: np.ndarray
    ):
        """构建FAISS索引和SQLite元数据存储

        Args:
            documents: 文档列表 [{"doc_id": "xxx", "content": "xxx", "metadata": {...}}, ...]
            embeddings: 对应的向量矩阵 (N, embedding_dim)
        """
        if len(documents) != embeddings.shape[0]:
            raise ValueError(f"文档数量({len(documents)})与向量数量({embeddings.shape[0]})不匹配")

        logger.info(f"开始构建混合索引: {len(documents)}条文档")

        # Step 1: 构建FAISS索引
        logger.info("构建FAISS索引...")
        self.faiss_index = faiss.IndexFlatIP(self.embedding_dim)  # 内积相似度

        # 归一化向量(使内积等价于余弦相似度)
        embeddings_normalized = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        self.faiss_index.add(embeddings_normalized.astype(np.float32))

        # 保存FAISS索引
        self.faiss_index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.faiss_index, str(self.faiss_index_path))
        logger.info(f"FAISS索引已保存: {self.faiss_index_path}")

        # Step 2: 保存文档ID映射
        self.doc_ids = [doc["doc_id"] for doc in documents]
        id_map_path = self.faiss_index_path.with_suffix(".ids.txt")
        with open(id_map_path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.doc_ids))
        logger.info(f"ID映射已保存: {id_map_path}")

        # Step 3: 批量插入SQLite
        logger.info("插入SQLite元数据...")
        self.metadata_db.insert_batch(documents)

        logger.info(f"✅ 混合索引构建完成: FAISS({len(self.doc_ids)}条) + SQLite({self.metadata_db.count()}条)")

    def load_index(self):
        """加载已有的FAISS索引和ID映射"""
        if not self.faiss_index_path.exists():
            raise FileNotFoundError(f"FAISS索引不存在: {self.faiss_index_path}")

        # 加载FAISS索引
        logger.info(f"加载FAISS索引: {self.faiss_index_path}")
        self.faiss_index = faiss.read_index(str(self.faiss_index_path))

        # 加载ID映射
        id_map_path = self.faiss_index_path.with_suffix(".ids.txt")
        if not id_map_path.exists():
            raise FileNotFoundError(f"ID映射文件不存在: {id_map_path}")

        with open(id_map_path, "r", encoding="utf-8") as f:
            self.doc_ids = [line.strip() for line in f if line.strip()]

        logger.info(f"✅ 索引加载完成: FAISS({len(self.doc_ids)}条) + SQLite({self.metadata_db.count()}条)")

    def retrieve(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        similarity_threshold: float = 0.3
    ) -> List[Dict]:
        """混合检索: FAISS检索 → SQLite查询

        Args:
            query_embedding: 查询向量 (embedding_dim,)
            top_k: 返回Top-K结果
            similarity_threshold: 相似度阈值

        Returns:
            [{"doc_id": "xxx", "content": "xxx", "metadata": {...}, "score": 0.xx}, ...]
        """
        if self.faiss_index is None:
            self.load_index()

        # Step 1: FAISS向量检索
        query_normalized = query_embedding / np.linalg.norm(query_embedding)
        query_normalized = query_normalized.astype(np.float32).reshape(1, -1)

        scores, indices = self.faiss_index.search(query_normalized, top_k)
        scores = scores[0]  # (top_k,)
        indices = indices[0]  # (top_k,)

        # 过滤低于阈值的结果
        valid_mask = scores >= similarity_threshold
        scores = scores[valid_mask]
        indices = indices[valid_mask]

        if len(indices) == 0:
            logger.warning(f"没有找到相似度 >= {similarity_threshold} 的结果")
            return []

        # Step 2: 获取对应的文档ID
        retrieved_doc_ids = [self.doc_ids[idx] for idx in indices]

        # Step 3: 从SQLite查询完整文档
        documents = self.metadata_db.get_by_ids(retrieved_doc_ids)

        # Step 4: 添加相似度分数
        doc_id_to_score = dict(zip(retrieved_doc_ids, scores))
        for doc in documents:
            doc["score"] = float(doc_id_to_score[doc["doc_id"]])

        logger.info(f"检索到 {len(documents)} 条结果 (阈值={similarity_threshold})")
        return documents

    def get_stats(self) -> Dict:
        """获取索引统计信息"""
        stats = {
            "faiss_index_exists": self.faiss_index is not None,
            "faiss_doc_count": len(self.doc_ids) if self.doc_ids else 0,
            "sqlite_doc_count": self.metadata_db.count(),
            "embedding_dim": self.embedding_dim
        }
        return stats
