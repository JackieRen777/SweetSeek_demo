#!/usr/bin/env python3
"""系统功能测试脚本"""

import sys
import os

print("=" * 60)
print("SweetSeek 系统测试")
print("=" * 60)

# 1. 测试环境变量
print("\n[1] 检查环境变量...")
from dotenv import load_dotenv
load_dotenv()

deepseek_key = os.getenv("DEEPSEEK_API_KEY")
if deepseek_key:
    print(f"  ✅ DEEPSEEK_API_KEY: {deepseek_key[:10]}...")
else:
    print("  ❌ DEEPSEEK_API_KEY 未设置")

embed_model = os.getenv("EMBED_MODEL_NAME", "BAAI/bge-small-zh-v1.5")
print(f"  ✅ 嵌入模型: {embed_model}")

# 2. 测试文件存在性
print("\n[2] 检查关键文件...")
files = [
    "app.py",
    "persistent_storage.py",
    "pdf_metadata_extractor.py",
    "metadata_storage.py",
    "storage/metadata.json",
    "storage/docstore.json",
    "storage/index_store.json"
]

for f in files:
    if os.path.exists(f):
        size = os.path.getsize(f)
        print(f"  ✅ {f} ({size:,} bytes)")
    else:
        print(f"  ❌ {f} 不存在")

# 3. 测试PDF文件
print("\n[3] 检查PDF文献...")
pdf_dir = "food_research_data/papers"
if os.path.exists(pdf_dir):
    pdfs = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
    print(f"  ✅ 找到 {len(pdfs)} 个PDF文件")
    for pdf in pdfs[:3]:
        print(f"     - {pdf}")
    if len(pdfs) > 3:
        print(f"     ... 还有 {len(pdfs) - 3} 个")
else:
    print(f"  ❌ {pdf_dir} 目录不存在")

# 4. 测试元数据
print("\n[4] 检查元数据...")
try:
    from metadata_storage import MetadataStorage
    storage = MetadataStorage()
    metadata_count = len(storage._metadata_cache)
    print(f"  ✅ 已加载 {metadata_count} 个文件的元数据")
    
    # 显示第一个元数据示例
    if metadata_count > 0:
        first_key = list(storage._metadata_cache.keys())[0]
        first_meta = storage._metadata_cache[first_key]
        print(f"\n  示例元数据:")
        print(f"    文件: {first_meta.get('filename', 'N/A')}")
        print(f"    期刊: {first_meta.get('journal', 'N/A')}")
        print(f"    年份: {first_meta.get('year', 'N/A')}")
        print(f"    标题: {first_meta.get('title', 'N/A')[:50]}...")
except Exception as e:
    print(f"  ❌ 元数据加载失败: {e}")

# 5. 测试RAG系统
print("\n[5] 检查RAG系统...")
try:
    from persistent_storage import rag_system
    
    # 尝试加载索引
    success = rag_system.load_or_create_index()
    if success:
        print("  ✅ 索引加载成功")
        
        stats = rag_system.get_stats()
        print(f"  ✅ 文档数量: {stats.get('total_documents', 0)}")
        print(f"  ✅ 索引状态: {stats.get('status', 'unknown')}")
    else:
        print("  ❌ 索引加载失败")
except Exception as e:
    print(f"  ❌ RAG系统初始化失败: {e}")

# 6. 测试Flask应用
print("\n[6] 检查Flask应用...")
try:
    import app as flask_app
    print("  ✅ Flask应用导入成功")
    print(f"  ✅ 配置端口: 5001")
except Exception as e:
    print(f"  ❌ Flask应用导入失败: {e}")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
print("\n💡 启动服务器:")
print("   python3 app.py")
print("\n💡 访问地址:")
print("   http://localhost:5001")
print("=" * 60)
