#!/usr/bin/env python3
"""
测试混合检索器的性能

对比:
1. 原始JSON索引检索速度
2. FAISS+SQLite混合索引检索速度
"""

import sys
import time
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
from sweetseek.hybrid_retriever_v2 import HybridRetriever
from knowledge_paths import get_domain_paths

def test_hybrid_retrieval():
    """测试混合检索性能"""
    print("=" * 60)
    print("测试FAISS+SQLite混合检索性能")
    print("=" * 60)

    # 路径设置
    paths = get_domain_paths("sweetness")
    hybrid_dir = Path(paths.index) / "hybrid"
    faiss_index_path = hybrid_dir / "index.faiss"
    sqlite_db_path = hybrid_dir / "metadata.db"

    # 初始化检索器
    print("\n1️⃣ 初始化检索器...")
    start = time.time()
    retriever = HybridRetriever(
        faiss_index_path=str(faiss_index_path),
        sqlite_db_path=str(sqlite_db_path),
        embedding_dim=512
    )
    retriever.load_index()
    load_time = time.time() - start
    print(f"✅ 加载完成: {load_time:.2f}秒")

    # 获取统计信息
    stats = retriever.get_stats()
    print(f"\n📊 索引统计:")
    print(f"  - FAISS文档数: {stats['faiss_doc_count']:,}")
    print(f"  - SQLite文档数: {stats['sqlite_doc_count']:,}")
    print(f"  - 向量维度: {stats['embedding_dim']}")

    # 模拟查询向量
    print("\n2️⃣ 模拟检索查询...")
    query_embedding = np.random.rand(512).astype(np.float32)

    # 测试多次查询取平均
    num_tests = 10
    total_time = 0

    for i in range(num_tests):
        start = time.time()
        results = retriever.retrieve(
            query_embedding=query_embedding,
            top_k=10,
            similarity_threshold=0.3
        )
        elapsed = time.time() - start
        total_time += elapsed

        if i == 0:
            print(f"\n首次查询结果:")
            print(f"  - 返回文档数: {len(results)}")
            print(f"  - 查询耗时: {elapsed*1000:.1f}ms")
            if results:
                print(f"  - 最高相似度: {results[0]['score']:.3f}")
                print(f"  - 最低相似度: {results[-1]['score']:.3f}")

    avg_time = total_time / num_tests
    print(f"\n3️⃣ 平均查询性能 ({num_tests}次):")
    print(f"  - 平均耗时: {avg_time*1000:.1f}ms")
    print(f"  - QPS: {1/avg_time:.1f} 查询/秒")

    print("\n✅ 测试完成!")

if __name__ == "__main__":
    test_hybrid_retrieval()
