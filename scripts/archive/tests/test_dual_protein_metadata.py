#!/usr/bin/env python3
"""测试Dual-Protein元数据在检索中的使用"""

from persistent_storage import PersistentRAGSystem
from metadata_storage import MetadataStorage
from pathlib import Path

# 初始化系统
dual_protein_rag = PersistentRAGSystem(
    data_dir='./Dual_Protein_related_paper/papers',
    persist_dir='./storage_dual_protein'
)

metadata_storage = MetadataStorage(storage_path='./chroma_db_v3/metadata.json')

print("加载Dual-Protein索引...")
success = dual_protein_rag.load_or_create_index()

if not success:
    print("❌ 索引加载失败")
    exit(1)

print("✅ 索引加载成功\n")

# 测试检索
test_query = "蛋白质相互作用"
print(f"测试查询: {test_query}")

retriever = dual_protein_rag.index.as_retriever(similarity_top_k=10)
results = retriever.retrieve(test_query)

print(f"\n检索到 {len(results)} 个结果\n")

# 检查元数据
print("=" * 80)
print("检索结果的元数据信息:")
print("=" * 80)

for i, chunk in enumerate(results[:5], 1):
    file_path = chunk.metadata.get('file_path', '')
    filename = chunk.metadata.get('file_name', 'Unknown')
    score = chunk.score if hasattr(chunk, 'score') else 'N/A'
    
    print(f"\n{i}. 文件名: {filename}")
    print(f"   Score: {score}")
    print(f"   文件路径: {file_path}")
    
    # 尝试获取元数据
    if file_path:
        meta = metadata_storage.get_metadata(file_path)
        if meta:
            print(f"   ✅ 元数据找到:")
            print(f"      标题: {meta.get('title', 'N/A')}")
            print(f"      期刊: {meta.get('journal', 'N/A')}")
            print(f"      年份: {meta.get('year', 'N/A')}")
            print(f"      作者: {meta.get('authors', [])}")
            print(f"      来源: {meta.get('source', 'N/A')}")
        else:
            print(f"   ❌ 元数据未找到")
            print(f"   尝试通过文件名查找...")
            # 尝试通过文件名查找
            meta = metadata_storage.get_metadata(filename)
            if meta:
                print(f"   ✅ 通过文件名找到元数据:")
                print(f"      标题: {meta.get('title', 'N/A')}")
                print(f"      期刊: {meta.get('journal', 'N/A')}")
                print(f"      年份: {meta.get('year', 'N/A')}")
            else:
                print(f"   ❌ 仍未找到元数据")

print("\n" + "=" * 80)
print("测试完成")
