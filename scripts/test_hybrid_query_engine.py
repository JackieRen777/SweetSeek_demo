#!/usr/bin/env python3
"""
测试混合查询引擎(兼容LlamaIndex接口)

验证:
1. 能否正常初始化
2. 能否正常检索
3. 返回结果格式是否正确
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import time
import logging
from knowledge_paths import get_domain_paths

# 配置embedding模型
from llama_index.core import Settings
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_hybrid_query_engine():
    """测试混合查询引擎"""
    print("=" * 60)
    print("测试混合查询引擎 (LlamaIndex接口)")
    print("=" * 60)

    # 1. 配置embedding模型
    print("\n1️⃣ 配置embedding模型...")
    model_path = project_root / "models" / "modelscope_cache" / "BAAI" / "bge-small-zh-v1___5"

    if not model_path.exists():
        raise FileNotFoundError(f"本地模型不存在: {model_path}")

    print(f"   使用本地模型: {model_path}")
    embed_model = SentenceTransformer(str(model_path))

    # 包装成LlamaIndex格式
    from llama_index.core.embeddings import BaseEmbedding
    from llama_index.core.bridge.pydantic import PrivateAttr

    class STEmbedding(BaseEmbedding):
        _model: object = PrivateAttr()

        def __init__(self, model, **kwargs):
            super().__init__(**kwargs)
            self._model = model

        def _get_query_embedding(self, query: str):
            vec = self._model.encode(query, show_progress_bar=False)
            return vec.tolist()

        def _get_text_embedding(self, text: str):
            vec = self._model.encode(text, show_progress_bar=False)
            return vec.tolist()

        async def _aget_query_embedding(self, query: str):
            return self._get_query_embedding(query)

    Settings.embed_model = STEmbedding(embed_model)
    print("✅ Embedding模型已配置")

    # 2. 创建混合查询引擎
    print("\n2️⃣ 创建混合查询引擎...")
    from sweetseek.hybrid_query_engine import create_hybrid_query_engine

    paths = get_domain_paths("sweetness")
    persist_dir = str(paths.index)

    start = time.time()
    engine = create_hybrid_query_engine(
        persist_dir=persist_dir,
        embedding_dim=512,
        similarity_top_k=5,
        similarity_threshold=0.2
    )
    init_time = time.time() - start

    stats = engine.get_stats()
    print(f"✅ 引擎创建完成 ({init_time:.2f}秒)")
    print(f"   索引统计: {stats}")

    # 3. 测试查询
    print("\n3️⃣ 测试查询...")
    test_queries = [
        "甜味剂的分类和特点",
        "天然甜味物质有哪些",
        "人工甜味剂的安全性",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n查询 {i}: {query}")
        print("-" * 60)

        start = time.time()
        response = engine.query(query)
        elapsed = time.time() - start

        print(f"⏱️  查询耗时: {elapsed*1000:.1f}ms")
        print(f"📊 返回结果: {len(response.source_nodes)}条")

        # 显示Top-3结果
        for j, node in enumerate(response.source_nodes[:3], 1):
            score = node.score
            content_preview = node.node.text[:80].replace("\n", " ")
            print(f"  {j}. 相似度={score:.3f} | {content_preview}...")

    print("\n✅ 所有测试通过!")

if __name__ == "__main__":
    test_hybrid_query_engine()
