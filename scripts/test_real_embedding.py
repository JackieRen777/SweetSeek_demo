#!/usr/bin/env python3
"""
使用真实embedding模型测试混合检索

对比查询:"甜味剂在食品中的应用"
"""

import sys
import time
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
from sweetseek.hybrid_retriever_v2 import HybridRetriever
from knowledge_paths import get_domain_paths

# 导入embedding模型
from sentence_transformers import SentenceTransformer

def test_real_query():
    """使用真实查询测试检索"""
    print("=" * 60)
    print("使用真实embedding模型测试混合检索")
    print("=" * 60)

    # 加载embedding模型
    print("\n1️⃣ 加载embedding模型...")
    model_name = "BAAI/bge-small-zh-v1.5"
    start = time.time()
    embed_model = SentenceTransformer(model_name)
    embed_time = time.time() - start
    print(f"✅ 模型加载完成: {embed_time:.2f}秒")

    # 初始化检索器
    print("\n2️⃣ 初始化混合检索器...")
    paths = get_domain_paths("sweetness")
    hybrid_dir = Path(paths.index) / "hybrid"

    start = time.time()
    retriever = HybridRetriever(
        faiss_index_path=str(hybrid_dir / "index.faiss"),
        sqlite_db_path=str(hybrid_dir / "metadata.db"),
        embedding_dim=512
    )
    retriever.load_index()
    load_time = time.time() - start
    print(f"✅ 索引加载完成: {load_time:.2f}秒")

    # 测试查询
    test_queries = [
        "甜味剂在食品中的应用",
        "蛋白质与多糖相互作用",
        "天然甜味物质的结构",
    ]

    print("\n3️⃣ 测试真实查询:")
    print("=" * 60)

    for query in test_queries:
        print(f"\n📝 查询: {query}")

        # 生成query embedding
        start = time.time()
        query_embedding = embed_model.encode(query, convert_to_numpy=True)
        embed_time = time.time() - start

        # 检索
        start = time.time()
        results = retriever.retrieve(
            query_embedding=query_embedding,
            top_k=5,
            similarity_threshold=0.2
        )
        retrieve_time = time.time() - start

        # 显示结果
        print(f"   ⏱️  Embedding耗时: {embed_time*1000:.1f}ms")
        print(f"   ⏱️  检索耗时: {retrieve_time*1000:.1f}ms")
        print(f"   ⏱️  总耗时: {(embed_time+retrieve_time)*1000:.1f}ms")
        print(f"   📊 返回结果: {len(results)}条")

        if results:
            print(f"   🥇 最高相似度: {results[0]['score']:.3f}")
            print(f"   📄 Top-1内容预览: {results[0]['content'][:100]}...")

    print("\n✅ 测试完成!")

if __name__ == "__main__":
    test_real_query()
