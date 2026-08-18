#!/usr/bin/env python3
"""
混合检索查询引擎 - 兼容LlamaIndex接口

将HybridRetriever包装成类似LlamaIndex QueryEngine的接口,
可以直接替换现有的query_engine使用。
"""

import logging
from typing import List, Dict, Optional
from pathlib import Path
import numpy as np

try:
    from llama_index.core import Settings
except ImportError:
    from llama_index import Settings

from sweetseek.hybrid_retriever_v2 import HybridRetriever

logger = logging.getLogger(__name__)


class HybridQueryEngine:
    """
    混合检索查询引擎 - 兼容LlamaIndex接口

    使用方式:
        engine = HybridQueryEngine(
            faiss_index_path="path/to/index.faiss",
            sqlite_db_path="path/to/metadata.db"
        )
        response = engine.query("你的问题")
        print(response.source_nodes)
    """

    def __init__(
        self,
        faiss_index_path: str,
        sqlite_db_path: str,
        embedding_dim: int = 512,
        similarity_top_k: int = 10,
        similarity_threshold: float = 0.3
    ):
        self.retriever = HybridRetriever(
            faiss_index_path=faiss_index_path,
            sqlite_db_path=sqlite_db_path,
            embedding_dim=embedding_dim
        )
        self.similarity_top_k = similarity_top_k
        self.similarity_threshold = similarity_threshold

        # 延迟加载索引
        self._index_loaded = False

    def _ensure_index_loaded(self):
        """确保索引已加载"""
        if not self._index_loaded:
            self.retriever.load_index()
            self._index_loaded = True

    def _get_query_embedding(self, query_str: str) -> np.ndarray:
        """获取查询向量 (使用LlamaIndex的embed_model)"""
        embed_model = Settings.embed_model
        if embed_model is None:
            raise ValueError("Settings.embed_model未配置")

        # 调用embed_model获取向量
        embedding = embed_model.get_query_embedding(query_str)
        return np.array(embedding, dtype=np.float32)

    def retrieve(self, query_str: str) -> List[Dict]:
        """
        检索相关文档

        Returns:
            [{"doc_id": "xxx", "content": "xxx", "metadata": {...}, "score": 0.xx}, ...]
        """
        self._ensure_index_loaded()

        # 获取查询向量
        query_embedding = self._get_query_embedding(query_str)

        # 检索
        results = self.retriever.retrieve(
            query_embedding=query_embedding,
            top_k=self.similarity_top_k,
            similarity_threshold=self.similarity_threshold
        )

        return results

    def query(self, query_str: str):
        """
        查询接口 - 兼容LlamaIndex QueryEngine

        返回包含source_nodes的Response对象
        """
        results = self.retrieve(query_str)

        # 构造简化的Response对象
        class SimpleResponse:
            def __init__(self, source_nodes):
                self.source_nodes = source_nodes
                self.response = ""  # 混合检索不生成回答,只返回检索结果

        # 将结果转换为node格式
        nodes = []
        for result in results:
            node = type('Node', (), {
                'node': type('NodeContent', (), {
                    'text': result['content'],
                    'metadata': result.get('metadata', {}),
                })(),
                'score': result['score'],
                'node_id': result['doc_id']
            })()
            nodes.append(node)

        return SimpleResponse(source_nodes=nodes)

    def get_stats(self) -> Dict:
        """获取统计信息"""
        self._ensure_index_loaded()
        return self.retriever.get_stats()


def create_hybrid_query_engine(
    persist_dir: str,
    embedding_dim: int = 512,
    similarity_top_k: int = 10,
    similarity_threshold: float = 0.3
) -> HybridQueryEngine:
    """
    创建混合查询引擎的工厂函数

    Args:
        persist_dir: 索引目录 (会自动在hybrid/子目录查找)
        embedding_dim: 向量维度
        similarity_top_k: 返回Top-K结果
        similarity_threshold: 相似度阈值

    Returns:
        HybridQueryEngine实例
    """
    hybrid_dir = Path(persist_dir) / "hybrid"
    faiss_index_path = hybrid_dir / "index.faiss"
    sqlite_db_path = hybrid_dir / "metadata.db"

    if not faiss_index_path.exists():
        raise FileNotFoundError(
            f"混合索引不存在: {faiss_index_path}\n"
            f"请先运行: python scripts/migrate_to_hybrid_index.py"
        )

    return HybridQueryEngine(
        faiss_index_path=str(faiss_index_path),
        sqlite_db_path=str(sqlite_db_path),
        embedding_dim=embedding_dim,
        similarity_top_k=similarity_top_k,
        similarity_threshold=similarity_threshold
    )
