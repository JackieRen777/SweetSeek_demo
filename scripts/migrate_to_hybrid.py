"""
数据迁移工具：从现有JSON索引迁移到FAISS+SQLite混合架构
"""
import json
import numpy as np
import logging
from pathlib import Path
from tqdm import tqdm
from sweetseek.hybrid_retriever import HybridRetriever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_from_json_to_hybrid(
    json_index_path: str = "data/proteoglycan_faiss.index",
    json_embeddings_path: str = "data/proteoglycan_embeddings.npy",
    output_faiss_path: str = "data/faiss_index.bin",
    output_sqlite_path: str = "data/metadata.db",
    batch_size: int = 1000
):
    """
    从JSON索引迁移到FAISS+SQLite

    Args:
        json_index_path: 原JSON索引文件路径
        json_embeddings_path: 原embeddings numpy文件路径
        output_faiss_path: 输出FAISS索引路径
        output_sqlite_path: 输出SQLite数据库路径
        batch_size: 批量插入大小
    """

    logger.info("=" * 60)
    logger.info("开始数据迁移: JSON → FAISS+SQLite")
    logger.info("=" * 60)

    # 1. 加载原JSON索引
    logger.info(f"[1/4] 加载JSON索引: {json_index_path}")
    with open(json_index_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    documents = json_data.get('documents', [])
    total_docs = len(documents)
    logger.info(f"✓ 加载了 {total_docs} 条文档")

    # 2. 加载embeddings
    logger.info(f"[2/4] 加载embeddings: {json_embeddings_path}")
    embeddings = np.load(json_embeddings_path)
    logger.info(f"✓ 加载了 {embeddings.shape[0]} 个向量, 维度: {embeddings.shape[1]}")

    if len(embeddings) != total_docs:
        raise ValueError(f"向量数量({len(embeddings)})与文档数量({total_docs})不匹配!")

    # 3. 初始化混合检索器
    logger.info(f"[3/4] 初始化混合检索器")
    retriever = HybridRetriever(
        faiss_index_path=output_faiss_path,
        sqlite_db_path=output_sqlite_path,
        embedding_dim=embeddings.shape[1]
    )

    # 4. 批量迁移数据
    logger.info(f"[4/4] 批量迁移数据 (batch_size={batch_size})")
    for i in tqdm(range(0, total_docs, batch_size), desc="迁移进度"):
        batch_end = min(i + batch_size, total_docs)

        batch_embeddings = embeddings[i:batch_end]
        batch_documents = documents[i:batch_end]

        # 确保每个文档都有ID
        for idx, doc in enumerate(batch_documents):
            if 'id' not in doc:
                doc['id'] = i + idx

        retriever.add_documents(batch_embeddings, batch_documents)

    # 5. 保存FAISS索引
    logger.info("[5/5] 保存FAISS索引")
    retriever.save_index()

    # 6. 输出统计信息
    stats = retriever.get_stats()
    logger.info("=" * 60)
    logger.info("迁移完成!")
    logger.info(f"  - FAISS索引: {stats['faiss_count']} 条")
    logger.info(f"  - SQLite文档: {stats['sqlite_count']} 条")
    logger.info(f"  - 向量维度: {stats['embedding_dim']}")
    logger.info(f"  - 索引类型: {stats['index_type']}")
    logger.info("=" * 60)

    return retriever


def test_retrieval(retriever: HybridRetriever, test_query_embedding: np.ndarray):
    """测试检索功能"""
    logger.info("\n测试检索功能...")

    results = retriever.search(test_query_embedding, top_k=5)

    logger.info(f"检索到 {len(results)} 条结果:")
    for i, doc in enumerate(results, 1):
        logger.info(f"\n[{i}] Score: {doc['score']:.4f}")
        logger.info(f"    File: {doc['file_path']}")
        logger.info(f"    Content: {doc['content'][:100]}...")


if __name__ == "__main__":
    # 执行迁移
    retriever = migrate_from_json_to_hybrid()

    # 测试检索 (使用第一个向量作为测试查询)
    embeddings = np.load("data/proteoglycan_embeddings.npy")
    test_query = embeddings[0]
    test_retrieval(retriever, test_query)

    logger.info("\n✅ 全部完成!")
