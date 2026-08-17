"""
混合检索器：FAISS向量索引 + SQLite元数据存储
流程：查询 → FAISS检索Top-N ID → SQLite批量查询详情
"""
import faiss
import numpy as np
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from sweetseek.sqlite_metadata import SQLiteMetadataStore

logger = logging.getLogger(__name__)


class HybridRetriever:
    """FAISS + SQLite混合检索器"""

    def __init__(
        self,
        faiss_index_path: str = "data/faiss_index.bin",
        sqlite_db_path: str = "data/metadata.db",
        embedding_dim: int = 1024
    ):
        self.faiss_index_path = Path(faiss_index_path)
        self.embedding_dim = embedding_dim

        # 初始化FAISS索引
        self.index = None
        self._load_or_create_faiss_index()

        # 初始化SQLite存储
        self.metadata_store = SQLiteMetadataStore(sqlite_db_path)

        logger.info(f"混合检索器初始化完成 - FAISS: {self.index.ntotal}条, SQLite: {self.metadata_store.count()}条")

    def _load_or_create_faiss_index(self):
        """加载或创建FAISS索引"""
        if self.faiss_index_path.exists():
            self.index = faiss.read_index(str(self.faiss_index_path))
            logger.info(f"加载FAISS索引: {self.index.ntotal}条向量")
        else:
            # 使用IndexFlatIP (内积，适合归一化向量)
            self.index = faiss.IndexFlatIP(self.embedding_dim)
            logger.info(f"创建新的FAISS索引 (维度: {self.embedding_dim})")

    def add_documents(
        self,
        embeddings: np.ndarray,
        documents: List[Dict[str, Any]]
    ):
        """
        添加文档到混合索引

        Args:
            embeddings: shape (N, embedding_dim) 的向量
            documents: 文档列表，每个文档需包含 id, file_path, chunk_index, content, metadata
        """
        if len(embeddings) != len(documents):
            raise ValueError(f"向量数量({len(embeddings)})与文档数量({len(documents)})不匹配")

        # 归一化向量(用于内积相似度)
        faiss.normalize_L2(embeddings)

        # 添加到FAISS
        self.index.add(embeddings)

        # 添加到SQLite
        self.metadata_store.insert_batch(documents)

        logger.info(f"添加 {len(documents)} 条文档到混合索引")

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        混合检索

        流程：
        1. FAISS检索 → 获取Top-K的ID和相似度分数
        2. SQLite批量查询 → 获取完整文档内容
        3. 合并结果返回

        Args:
            query_embedding: shape (embedding_dim,) 的查询向量
            top_k: 返回top-k个结果

        Returns:
            包含 id, score, content, file_path, metadata 的文档列表
        """
        # 归一化查询向量
        query_embedding = query_embedding.reshape(1, -1).astype(np.float32)
        faiss.normalize_L2(query_embedding)

        # Step 1: FAISS检索获取ID和分数
        scores, indices = self.index.search(query_embedding, top_k)
        scores = scores[0]  # shape: (top_k,)
        indices = indices[0]  # shape: (top_k,)

        # 过滤掉无效ID (-1表示没有足够的结果)
        valid_mask = indices >= 0
        valid_indices = indices[valid_mask].tolist()
        valid_scores = scores[valid_mask].tolist()

        if not valid_indices:
            return []

        # Step 2: SQLite批量查询详情
        documents = self.metadata_store.get_by_ids(valid_indices)

        # Step 3: 创建ID到文档的映射
        doc_map = {doc['id']: doc for doc in documents}

        # Step 4: 按FAISS返回的顺序组装结果，附加分数
        results = []
        for idx, score in zip(valid_indices, valid_scores):
            if idx in doc_map:
                doc = doc_map[idx]
                doc['score'] = float(score)
                results.append(doc)

        logger.info(f"检索完成: Top-{top_k} → 返回 {len(results)} 条结果")
        return results

    def save_index(self):
        """保存FAISS索引到磁盘"""
        self.faiss_index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.faiss_index_path))
        logger.info(f"FAISS索引已保存: {self.faiss_index_path}")

    def get_stats(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        return {
            'faiss_count': self.index.ntotal,
            'sqlite_count': self.metadata_store.count(),
            'embedding_dim': self.embedding_dim,
            'index_type': type(self.index).__name__
        }
