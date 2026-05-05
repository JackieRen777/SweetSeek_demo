#!/usr/bin/env python3
"""测试检索功能"""

import sys
from persistent_storage import rag_system

# 加载索引
print("加载索引...")
success = rag_system.load_or_create_index()
if not success:
    print("❌ 索引加载失败")
    sys.exit(1)

print("✅ 索引加载成功")

# 获取统计信息
stats = rag_system.get_stats()
print(f"\n索引统计:")
print(f"  - 状态: {stats['status']}")
print(f"  - 文档数: {stats['total_documents']}")
print(f"  - 持久化目录: {stats['persist_dir']}")

# 测试检索
print("\n测试检索功能...")
test_query = "甜味剂的种类"
print(f"查询: {test_query}")

retriever = rag_system.index.as_retriever(similarity_top_k=200)
results = retriever.retrieve(test_query)

print(f"\n✅ 检索到 {len(results)} 个文本块")

# 统计唯一文件
unique_files = set()
for chunk in results:
    file_path = chunk.metadata.get('file_path', '')
    if file_path:
        unique_files.add(file_path)

print(f"✅ 来自 {len(unique_files)} 个唯一文件")

# 显示前5个结果
print("\n前5个检索结果:")
for i, chunk in enumerate(results[:5], 1):
    filename = chunk.metadata.get('file_name', 'Unknown')
    score = float(chunk.score) if hasattr(chunk, 'score') else 0.0
    text_preview = chunk.text[:100].replace('\n', ' ')
    print(f"\n{i}. {filename}")
    print(f"   Score: {score:.4f}")
    print(f"   Preview: {text_preview}...")

print("\n✅ 检索测试完成！")
