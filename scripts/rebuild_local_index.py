#!/usr/bin/env python3
"""
强制重建本地索引脚本
用于解决 "未检索到相关文献" 的问题
"""

import os
import sys
import shutil
import logging
import argparse
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from persistent_storage import rag_system

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def _bytes_to_gb(num_bytes: int) -> float:
    return round(num_bytes / (1024 ** 3), 2)


def _preflight_checks(data_dir: str, persist_dir: str, min_free_gb: float = 8.0) -> bool:
    """重建前检查：目录存在、磁盘可用空间。"""
    if not os.path.exists(data_dir):
        print(f"❌ 错误: 数据目录不存在: {data_dir}")
        return False

    disk_root = Path(persist_dir).resolve().anchor or "/"
    usage = shutil.disk_usage(disk_root)
    free_gb = _bytes_to_gb(usage.free)
    print(f"💽 磁盘剩余空间: {free_gb} GiB")
    if free_gb < min_free_gb:
        print(f"❌ 可用磁盘空间不足（至少需要 {min_free_gb} GiB）")
        return False
    return True


def rebuild_index(batch_size: int):
    print("="*50)
    print("🧹 开始重建本地索引")
    print("="*50)
    
    # 1. 确认配置
    data_dir = config.DATA_DIR
    persist_dir = config.PERSIST_DIR
    
    print(f"📄 PDF 数据目录: {data_dir}")
    print(f"💾 索引目录: {persist_dir}")
    print(f"🧠 Embedding 模型: {config.EMBED_MODEL_NAME}")

    if not _preflight_checks(data_dir, persist_dir):
        return

    # 2. 设置批次大小，降低重建峰值内存
    os.environ["INDEX_BUILD_BATCH_SIZE"] = str(batch_size)
    print(f"🧩 构建批次大小: {batch_size}")
    
    # 3. 重新初始化 RAG 系统
    print("🚀 正在重新扫描文档并构建索引...")
    print("这可能需要几分钟，请耐心等待...")
    
    try:
        # 强制重新加载
        rag_system.load_or_create_index()
        
        # 4. 验证统计
        stats = rag_system.get_stats()
        print(f"✅ 索引构建完成！")
        print(f"📚 文档总数: {stats.get('total_documents', 0)}")
        
        # 5. 测试检索
        test_query = "什么是甜味剂"
        print(f"\n🔍 测试检索: '{test_query}'")
        
        retriever = rag_system.index.as_retriever(similarity_top_k=3)
        results = retriever.retrieve(test_query)
        
        if results:
            print(f"✅ 成功检索到 {len(results)} 个结果:")
            for i, node in enumerate(results):
                score = node.score if hasattr(node, 'score') else 0
                print(f"   [{i+1}] Score: {score:.4f} - {node.text[:50]}...")
        else:
            print("❌ 测试检索失败: 未找到结果")
            
    except Exception as e:
        print(f"❌ 重建过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="重建本地索引（低内存模式）")
    parser.add_argument("--batch-size", type=int, default=25, help="每批处理文件数，默认25")
    args = parser.parse_args()
    rebuild_index(batch_size=max(1, args.batch_size))
