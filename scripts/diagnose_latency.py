#!/usr/bin/env python3
"""
诊断RAG查询延迟的各个环节

分析:
1. Embedding生成耗时
2. FAISS检索耗时
3. LLM首字出现时间(TTFT)
4. 总查询时间
"""

import sys
import time
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import requests
from sentence_transformers import SentenceTransformer
from sweetseek.hybrid_retriever_v2 import HybridRetriever
from knowledge_paths import get_domain_paths

def diagnose_latency():
    """诊断延迟瓶颈"""
    print("=" * 60)
    print("RAG查询延迟诊断")
    print("=" * 60)

    # 1. 加载模型
    print("\n【阶段1】加载Embedding模型")
    model_path = project_root / "models" / "modelscope_cache" / "BAAI" / "bge-small-zh-v1___5"

    start = time.time()
    embed_model = SentenceTransformer(str(model_path))
    load_time = time.time() - start
    print(f"✅ 模型加载: {load_time:.2f}秒")

    # 2. 初始化检索器
    print("\n【阶段2】初始化FAISS检索器")
    paths = get_domain_paths("sweetness")
    hybrid_dir = Path(paths.index) / "hybrid"

    start = time.time()
    retriever = HybridRetriever(
        faiss_index_path=str(hybrid_dir / "index.faiss"),
        sqlite_db_path=str(hybrid_dir / "metadata.db"),
        embedding_dim=512
    )
    retriever.load_index()
    index_load_time = time.time() - start
    print(f"✅ 索引加载: {index_load_time:.2f}秒")

    # 3. 测试查询
    query = "甜味剂的种类和特点"
    print(f"\n【阶段3】测试查询: '{query}'")
    print("-" * 60)

    # 3.1 Embedding生成
    start = time.time()
    query_embedding = embed_model.encode(query, convert_to_numpy=True)
    embed_time = time.time() - start
    print(f"⏱️  Embedding生成: {embed_time*1000:.1f}ms")

    # 3.2 FAISS检索
    start = time.time()
    results = retriever.retrieve(
        query_embedding=query_embedding,
        top_k=5,
        similarity_threshold=0.2
    )
    retrieve_time = time.time() - start
    print(f"⏱️  FAISS检索: {retrieve_time*1000:.1f}ms")

    # 3.3 构造context
    context = "\n\n".join([r['content'][:200] for r in results[:3]])
    print(f"📄 检索到 {len(results)} 条结果")

    # 3.4 LLM首字出现时间(TTFT)
    print("\n【阶段4】测试LLM API延迟")

    # 测试GLM-4-Flash (硅基流动)
    api_url = "https://api.siliconflow.cn/v1/chat/completions"
    api_key = "sk-your-key-here"  # 从环境变量读取

    import os
    api_key = os.getenv("SILICONFLOW_API_KEY", "")

    if not api_key:
        print("⚠️  未设置SILICONFLOW_API_KEY环境变量，跳过LLM测试")
    else:
        prompt = f"""基于以下文档回答问题。

文档:
{context}

问题: {query}

回答:"""

        payload = {
            "model": "Qwen/Qwen2.5-7B-Instruct",
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "max_tokens": 512,
            "temperature": 0.7
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        print("   正在调用LLM API (流式)...")
        start = time.time()

        try:
            response = requests.post(api_url, json=payload, headers=headers, stream=True, timeout=30)

            first_token_time = None
            total_tokens = 0

            for line in response.iter_lines():
                if line:
                    if first_token_time is None:
                        first_token_time = time.time() - start
                    total_tokens += 1

                    if total_tokens >= 10:  # 只测试前10个token
                        break

            if first_token_time:
                print(f"⏱️  LLM首字延迟(TTFT): {first_token_time*1000:.1f}ms")
            else:
                print("⚠️  未收到LLM响应")

        except Exception as e:
            print(f"❌ LLM API调用失败: {e}")

    # 总结
    print("\n" + "=" * 60)
    print("【性能总结】")
    print("=" * 60)
    total_retrieval = embed_time + retrieve_time
    print(f"检索总耗时: {total_retrieval*1000:.1f}ms")
    print(f"  ├─ Embedding: {embed_time*1000:.1f}ms ({embed_time/total_retrieval*100:.1f}%)")
    print(f"  └─ FAISS检索: {retrieve_time*1000:.1f}ms ({retrieve_time/total_retrieval*100:.1f}%)")

    print("\n📌 优化建议:")
    if embed_time > 0.1:
        print("  • Embedding较慢 → 考虑使用GPU/MPS加速")
    if retrieve_time > 0.05:
        print("  • FAISS检索较慢 → 检查索引大小或硬件")
    print("  • 如果LLM TTFT > 500ms → 考虑更换更快的API")

if __name__ == "__main__":
    diagnose_latency()
