#!/usr/bin/env python3
"""persistent_storage.py

使用FAISS向量数据库的RAG系统（本地化优化版本）

主要优势：
- 不依赖SQLite版本，兼容性更好
- 纯文件存储，无需数据库服务
- 支持本地模型加载，适合国内网络环境
"""

from __future__ import annotations

import logging
import os
import shutil
from typing import List, Optional
from pathlib import Path

# 尝试导入 faiss
try:
    import faiss
except ImportError:
    logging.warning("未检测到 faiss，请运行 pip install faiss-cpu")
    faiss = None

from llama_index.core import (
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.vector_stores.faiss import FaissVectorStore

from config import config

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sweetseek.rag")

def configure_llm() -> bool:
    """配置 DeepSeek LLM"""
    try:
        from openai import OpenAI as OpenAIClient
        
        api_key = config.DEEPSEEK_API_KEY
        base_url = config.DEEPSEEK_BASE_URL
        model = config.DEEPSEEK_MODEL
        
        if not api_key:
            logger.warning("未找到 DEEPSEEK_API_KEY")
            return False
            
        # 将客户端注入到模块级别，供其他模块使用
        import sys
        current_module = sys.modules[__name__]
        current_module.deepseek_client = OpenAIClient(api_key=api_key, base_url=base_url)
        current_module.deepseek_model = model
        
        logger.info(f"✅ 成功配置 DeepSeek 客户端: {model}")
        return True
    except Exception as e:
        logger.warning(f"配置 DeepSeek 客户端失败: {e}")
        return False

class PersistentRAGSystem:
    def __init__(self, data_dir: str = None, persist_dir: str = None):
        self.data_dir = data_dir or config.DATA_DIR
        self.persist_dir = persist_dir or config.PERSIST_DIR
        self.index: Optional[VectorStoreIndex] = None
        self.query_engine = None
        self.models_configured = False
        
        # 初始化元数据管理器
        from metadata_storage import MetadataStorage
        from pdf_metadata_extractor import PDFMetadataExtractor
        self.metadata_storage = MetadataStorage()
        self.metadata_extractor = PDFMetadataExtractor()

    def _configure_models(self) -> None:
        """配置模型/嵌入"""
        if self.models_configured:
            return

        # 配置LLM
        configure_llm()

        # 配置嵌入模型
        try:
            embed_model_name = config.EMBED_MODEL_NAME
            logger.info(f"正在加载嵌入模型: {embed_model_name}")
            
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
            
            # 检查是否为本地路径
            if os.path.exists(embed_model_name):
                logger.info(f"从本地路径加载模型: {embed_model_name}")
                embed_model = HuggingFaceEmbedding(model_name=embed_model_name, trust_remote_code=True)
            else:
                logger.info(f"从HuggingFace加载模型: {embed_model_name}")
                embed_model = HuggingFaceEmbedding(model_name=embed_model_name)
                
            Settings.embed_model = embed_model
            logger.info(f"✅ 成功配置嵌入模型")
            
        except Exception as e:
            logger.error(f"配置嵌入模型失败: {e}")
            # 回退到默认（虽然可能也会失败，但至少尝试）
            Settings.embed_model = "local"

        self.models_configured = True

    def load_or_create_index(self) -> bool:
        """加载或创建索引"""
        self._configure_models()
        
        persist_path = Path(self.persist_dir)
        index_file = persist_path / "default__vector_store.json"
        
        if persist_path.exists() and index_file.exists():
            logger.info(f"检测到现有索引: {self.persist_dir}")
            return self._load_from_disk()
        else:
            logger.info("未检测到有效索引，开始构建新索引")
            return self._build_new_index()

    def _load_from_disk(self) -> bool:
        """从磁盘加载 FAISS 索引"""
        try:
            # 重建 StorageContext
            vector_store = FaissVectorStore.from_persist_dir(self.persist_dir)
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store,
                persist_dir=self.persist_dir
            )
            
            self.index = load_index_from_storage(storage_context)
            logger.info("✅ 索引从磁盘加载成功")
            return True
        except Exception as e:
            logger.error(f"加载索引失败: {e}")
            logger.info("尝试重建索引...")
            return self._build_new_index()

    def _build_new_index(self) -> bool:
        """构建新索引"""
        try:
            if not os.path.exists(self.data_dir):
                logger.error(f"数据目录不存在: {self.data_dir}")
                return False

            # 读取文档
            logger.info(f"📚 正在读取文档: {self.data_dir}")
            reader = SimpleDirectoryReader(self.data_dir, recursive=True)
            documents = reader.load_data()
            logger.info(f"📖 读取到 {len(documents)} 个文档片段")

            if not documents:
                logger.warning("未找到文档，跳过索引构建")
                return False

            # 提取元数据
            self._extract_metadata(documents)

            # 创建 FAISS 索引
            # 维度取决于模型，bge-small-zh-v1.5 是 512 维
            d = 512 
            faiss_index = faiss.IndexFlatIP(d)
            vector_store = FaissVectorStore(faiss_index=faiss_index)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)

            from llama_index.core.node_parser import TokenTextSplitter
            text_splitter = TokenTextSplitter(chunk_size=512, chunk_overlap=50)

            logger.info("开始构建向量索引...")
            self.index = VectorStoreIndex.from_documents(
                documents,
                storage_context=storage_context,
                transformations=[text_splitter],
                show_progress=True
            )
            
            # 持久化
            logger.info(f"正在保存索引到: {self.persist_dir}")
            Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
            self.index.storage_context.persist(persist_dir=self.persist_dir)
            
            logger.info("✅ 索引构建并保存完成")
            return True
            
        except Exception as e:
            logger.exception(f"构建索引失败: {e}")
            return False

    def _extract_metadata(self, documents):
        """提取PDF元数据"""
        pdf_count = 0
        for doc in documents:
            file_path = doc.metadata.get('file_path', '')
            if file_path.lower().endswith('.pdf'):
                try:
                    if not self.metadata_storage.has_metadata(file_path):
                        metadata = self.metadata_extractor.extract_metadata(file_path)
                        self.metadata_storage.save_metadata(file_path, metadata)
                        pdf_count += 1
                except Exception as e:
                    logger.warning(f"提取元数据失败 {file_path}: {e}")
        if pdf_count > 0:
            logger.info(f"✅ 提取了 {pdf_count} 个PDF文件的元数据")

    def get_stats(self) -> dict:
        """获取统计信息"""
        stats = {
            'total_documents': 0,
            'index_exists': False,
            'backend': 'faiss'
        }
        try:
            if self.index:
                # FAISS index total (approximate)
                # 无法直接从 vector_store 获取 count，只能从 docstore
                stats['total_documents'] = len(self.index.docstore.docs)
                stats['index_exists'] = True
        except Exception:
            pass
        return stats

    def add_documents(self, documents: List[object]) -> bool:
        """增量添加文档"""
        if not self.index:
            return self.load_or_create_index()
            
        try:
            self.index.insert_nodes(documents) # Note: insert_nodes if they are nodes, or insert if docs
            # For simplicity, just insert
            for doc in documents:
                self.index.insert(doc)
            
            self.index.storage_context.persist(persist_dir=self.persist_dir)
            return True
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            return False

# 全局实例
rag_system = PersistentRAGSystem()
