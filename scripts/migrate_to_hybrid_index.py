#!/usr/bin/env python3
"""
迁移脚本: 将现有的索引转换为FAISS+SQLite混合索引

支持从以下格式迁移:
1. LlamaIndex JSON索引
2. LlamaIndex FAISS索引(但没有SQLite元数据)

Usage:
    python scripts/migrate_to_hybrid_index.py --domain sweetness
    python scripts/migrate_to_hybrid_index.py --domain dual_protein
    python scripts/migrate_to_hybrid_index.py --domain proteoglycan
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import argparse
import logging
import json
import numpy as np
from typing import List, Dict, Any

try:
    import faiss
except ImportError:
    print("❌ 需要安装faiss-cpu: pip install faiss-cpu")
    sys.exit(1)

from sweetseek.hybrid_retriever_v2 import HybridRetriever
from knowledge_paths import get_domain_paths

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_from_json_index(persist_dir: str) -> tuple[List[Dict], np.ndarray]:
    """从JSON格式索引加载文档和向量"""
    vector_store_path = Path(persist_dir) / "default__vector_store.json"
    docstore_path = Path(persist_dir) / "docstore.json"

    if not vector_store_path.exists():
        raise FileNotFoundError(f"未找到向量存储: {vector_store_path}")
    if not docstore_path.exists():
        raise FileNotFoundError(f"未找到文档存储: {docstore_path}")

    logger.info(f"从JSON索引加载: {persist_dir}")

    # 加载向量
    with open(vector_store_path, "r", encoding="utf-8") as f:
        vector_data = json.load(f)

    embedding_dict = vector_data.get("embedding_dict", {})
    logger.info(f"加载了 {len(embedding_dict)} 个向量")

    # 加载文档
    with open(docstore_path, "r", encoding="utf-8") as f:
        docstore_data = json.load(f)

    doc_dict = docstore_data.get("docstore/data", {})
    logger.info(f"加载了 {len(doc_dict)} 个文档")

    # 构建文档列表和向量矩阵
    documents = []
    embeddings_list = []

    for doc_id, embedding in embedding_dict.items():
        if doc_id not in doc_dict:
            logger.warning(f"文档ID {doc_id} 在docstore中不存在,跳过")
            continue

        doc_info = doc_dict[doc_id]
        content = doc_info.get("__data__", {}).get("text", "")
        metadata = doc_info.get("__data__", {}).get("metadata", {})

        documents.append({
            "doc_id": doc_id,
            "content": content,
            "metadata": metadata
        })
        embeddings_list.append(embedding)

    embeddings = np.array(embeddings_list, dtype=np.float32)
    logger.info(f"✅ 提取了 {len(documents)} 条有效文档")

    return documents, embeddings


def load_from_faiss_index(persist_dir: str) -> tuple[List[Dict], np.ndarray]:
    """从FAISS格式索引加载文档和向量"""
    vector_store_path = Path(persist_dir) / "default__vector_store.json"
    docstore_path = Path(persist_dir) / "docstore.json"

    if not vector_store_path.exists():
        raise FileNotFoundError(f"未找到FAISS索引: {vector_store_path}")
    if not docstore_path.exists():
        raise FileNotFoundError(f"未找到文档存储: {docstore_path}")

    logger.info(f"从FAISS索引加载: {persist_dir}")

    # 加载FAISS索引
    faiss_index = faiss.read_index(str(vector_store_path))
    num_vectors = faiss_index.ntotal
    embedding_dim = faiss_index.d

    logger.info(f"FAISS索引: {num_vectors}个向量, 维度={embedding_dim}")

    # 重建向量矩阵
    embeddings = faiss_index.reconstruct_n(0, num_vectors)

    # 加载文档
    with open(docstore_path, "r", encoding="utf-8") as f:
        docstore_data = json.load(f)

    doc_dict = docstore_data.get("docstore/data", {})
    logger.info(f"加载了 {len(doc_dict)} 个文档")

    # 构建文档列表
    documents = []
    doc_ids = sorted(doc_dict.keys())  # 按ID排序保证顺序

    if len(doc_ids) != num_vectors:
        logger.warning(f"文档数量({len(doc_ids)})与向量数量({num_vectors})不匹配")

    for doc_id in doc_ids[:num_vectors]:
        doc_info = doc_dict[doc_id]
        content = doc_info.get("__data__", {}).get("text", "")
        metadata = doc_info.get("__data__", {}).get("metadata", {})

        documents.append({
            "doc_id": doc_id,
            "content": content,
            "metadata": metadata
        })

    logger.info(f"✅ 提取了 {len(documents)} 条有效文档")
    return documents, embeddings


def detect_index_format(persist_dir: str) -> str:
    """检测索引格式 (json 或 faiss)"""
    vector_store_path = Path(persist_dir) / "default__vector_store.json"

    if not vector_store_path.exists():
        raise FileNotFoundError(f"未找到索引文件: {vector_store_path}")

    # 读取文件头判断格式
    with open(vector_store_path, "rb") as f:
        header = f.read(16).lstrip()

    if header and header[:1] in {b"{", b"["}:
        return "json"
    else:
        return "faiss"


def migrate_domain(domain: str):
    """迁移指定领域的索引"""
    logger.info(f"{'='*60}")
    logger.info(f"开始迁移领域: {domain}")
    logger.info(f"{'='*60}")

    # 获取路径
    paths = get_domain_paths(domain)
    persist_dir = str(paths.index)

    # 检测索引格式
    try:
        index_format = detect_index_format(persist_dir)
        logger.info(f"检测到索引格式: {index_format.upper()}")
    except FileNotFoundError as e:
        logger.error(f"❌ {e}")
        return False

    # 加载文档和向量
    try:
        if index_format == "json":
            documents, embeddings = load_from_json_index(persist_dir)
        else:
            documents, embeddings = load_from_faiss_index(persist_dir)
    except Exception as e:
        logger.error(f"❌ 加载索引失败: {e}")
        return False

    # 构建混合索引
    hybrid_dir = Path(persist_dir) / "hybrid"
    hybrid_dir.mkdir(exist_ok=True)

    faiss_index_path = hybrid_dir / "index.faiss"
    sqlite_db_path = hybrid_dir / "metadata.db"

    logger.info(f"输出目录: {hybrid_dir}")
    logger.info(f"  - FAISS索引: {faiss_index_path.name}")
    logger.info(f"  - SQLite数据库: {sqlite_db_path.name}")

    try:
        retriever = HybridRetriever(
            faiss_index_path=str(faiss_index_path),
            sqlite_db_path=str(sqlite_db_path),
            embedding_dim=embeddings.shape[1]
        )

        retriever.build_index(documents=documents, embeddings=embeddings)

        # 验证
        stats = retriever.get_stats()
        logger.info(f"✅ 迁移完成!")
        logger.info(f"统计信息: {stats}")

        return True

    except Exception as e:
        logger.error(f"❌ 构建混合索引失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="迁移索引到FAISS+SQLite混合格式")
    parser.add_argument(
        "--domain",
        type=str,
        choices=["sweetness", "dual_protein", "proteoglycan"],
        required=True,
        help="领域名称"
    )

    args = parser.parse_args()

    success = migrate_domain(args.domain)

    if success:
        print(f"\n✅ 迁移成功: {args.domain}")
        print(f"混合索引位置: {get_domain_paths(args.domain).index}/hybrid/")
    else:
        print(f"\n❌ 迁移失败: {args.domain}")
        sys.exit(1)


if __name__ == "__main__":
    main()
