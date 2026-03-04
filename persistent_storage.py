#!/usr/bin/env python3
"""persistent_storage.py

使用 ChromaDB 向量数据库的RAG系统（本地化优化版本）

主要优势：
- 不依赖SQLite版本，兼容性更好
- 纯文件存储，无需数据库服务
- 支持本地模型加载，适合国内网络环境
"""

from __future__ import annotations

import logging
import os
import gc
import glob
from pathlib import Path
from typing import List, Optional

# 尝试导入 fitz (PyMuPDF)
try:
    import fitz
except ImportError:
    fitz = None

from llama_index.core import (
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document
from llama_index.core.node_parser import TokenTextSplitter

# ChromaDB
try:
    import chromadb
    from llama_index.vector_stores.chroma import ChromaVectorStore
except ImportError:
    logging.error("未检测到 chromadb，请运行 pip install chromadb llama-index-vector-stores-chroma")
    chromadb = None
    ChromaVectorStore = None

from config import config

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sweetseek.rag")


def validate_content(text: str, filename: str = "unknown") -> bool:
    """
    校验提取的文本内容质量
    如果返回 False，说明文件可能损坏、加密或包含大量乱码
    """
    if not text or len(text.strip()) < 10:
        logger.warning(f"❌ 校验失败 [{filename}]: 文本内容为空或过短")
        return False
        
    total_chars = len(text)
    control_chars = 0
    replacement_chars = text.count('\ufffd') # � 替换符
    
    for char in text:
        if char == '\ufffd':
            continue 
        code = ord(char)
        if (0 <= code <= 31 and code not in [9, 10, 13]) or code == 127:
            control_chars += 1
            
    control_ratio = control_chars / total_chars
    replacement_ratio = replacement_chars / total_chars
    
    # 放宽校验逻辑 (从 0.05 -> 0.20)
    if control_ratio > 0.20:
        logger.warning(f"❌ 校验失败 [{filename}]: 控制字符过多 ({control_ratio:.2%}), 可能为二进制文件")
        return False
        
    if replacement_ratio > 0.10:
        logger.warning(f"❌ 校验失败 [{filename}]: 乱码替换符过多 ({replacement_ratio:.2%}), 编码识别错误")
        return False
        
    return True

class PyMuPDFReader(BaseReader):
    """使用 PyMuPDF 读取 PDF 文件"""
    def load_data(self, file: Path, extra_info=None) -> List[Document]:
        if not fitz:
            raise ImportError("PyMuPDF is not installed.")
        try:
            doc = fitz.open(file)
            text = ""
            for page in doc:
                page_text = page.get_text("text", sort=True)
                text += page_text + "\n"
            doc.close()
            
            if not validate_content(text, filename=file.name):
                logger.error(f"🚫 拒绝索引文件: {file.name} (内容校验未通过)")
                raise ValueError(f"File {file.name} corrupted or encrypted")
                
            return [Document(text=text, extra_info=extra_info or {})]
        except Exception as e:
            logger.error(f"PyMuPDF 读取失败 {file}: {e}")
            return []

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
        # ChromaDB path
        self.chroma_path = "./chroma_db_v3"
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

        configure_llm()

        try:
            # 使用 config 中配置的模型路径
            local_model_path = os.path.abspath(config.EMBED_MODEL_NAME)
            
            if not os.path.exists(local_model_path):
                # 如果是 HuggingFace ID（如 BAAI/bge-small-zh-v1.5），则不检查本地路径
                if "/" in config.EMBED_MODEL_NAME and not config.EMBED_MODEL_NAME.startswith("/"):
                     logger.info(f"ℹ️ 使用 HuggingFace Hub 模型: {config.EMBED_MODEL_NAME}")
                     embed_model_name = config.EMBED_MODEL_NAME
                else:
                    logger.error(f"❌ 本地模型不存在: {local_model_path}")
                    embed_model_name = "local" # Fallback
            else:
                logger.info(f"✅ 使用本地 Embedding 模型: {local_model_path}")
                embed_model_name = local_model_path

            # 2. 配置 Embedding 模型
            # Settings.embed_model = "local"
            
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
            
            # 关键修改：
            # 1. trust_remote_code=False (本地模型不需要远程代码，更安全)
            # 2. device='cpu' (明确指定 CPU，避免 CUDA 警告)
            embed_model = HuggingFaceEmbedding(
                model_name=embed_model_name,
                trust_remote_code=False,
                device='cpu'
            )
            Settings.embed_model = embed_model
            logger.info("✅ 成功配置嵌入模型")
            
        except Exception as e:
            logger.error(f"配置嵌入模型失败: {e}")
            Settings.embed_model = "local"

        self.models_configured = True

    def load_or_create_index(self) -> bool:
        """加载或创建索引 (ChromaDB)"""
        self._configure_models()
        
        if not chromadb:
            logger.error("ChromaDB not installed!")
            return False

        try:
            # Check if ChromaDB data exists
            if os.path.exists(self.chroma_path):
                logger.info("正在加载现有 ChromaDB 索引...")
                return self._load_from_disk()
            else:
                logger.info("未找到索引，开始构建...")
                return self._build_new_index()
                    
        except Exception as e:
            logger.error(f"加载索引出错: {e}")
            return self._build_new_index()

    def _load_from_disk(self) -> bool:
        try:
            chroma_client = chromadb.PersistentClient(path=self.chroma_path)
            chroma_collection = chroma_client.get_or_create_collection("sweetseek_docs")
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            
            self.index = VectorStoreIndex.from_vector_store(
                vector_store,
                storage_context=storage_context
            )
            logger.info("✅ ChromaDB 索引加载成功")
            return True
        except Exception as e:
            logger.error(f"从磁盘加载失败: {e}")
            return False

    def _build_new_index(self) -> bool:
        """构建新索引"""
        try:
            if not os.path.exists(self.data_dir):
                logger.error(f"数据目录不存在: {self.data_dir}")
                return False

            all_files = []
            for ext in ['*.pdf', '*.PDF', '*.txt', '*.md']:
                all_files.extend(glob.glob(os.path.join(self.data_dir, "**", ext), recursive=True))
            
            logger.info(f"📚 扫描到 {len(all_files)} 个文件")
            if not all_files:
                logger.warning("未找到文档，跳过索引构建")
                return False

            # Initialize ChromaDB
            chroma_client = chromadb.PersistentClient(path=self.chroma_path)
            chroma_collection = chroma_client.get_or_create_collection("sweetseek_docs")
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            
            text_splitter = TokenTextSplitter(chunk_size=512, chunk_overlap=50)

            # Initialize empty index
            self.index = VectorStoreIndex.from_documents(
                [], 
                storage_context=storage_context,
                transformations=[text_splitter]
            )

            # Batch processing
            BATCH_SIZE = 5
            file_extractor = {}
            if fitz:
                file_extractor[".pdf"] = PyMuPDFReader()

            for i in range(0, len(all_files), BATCH_SIZE):
                batch_files = all_files[i : i + BATCH_SIZE]
                logger.info(f"🚀 处理批次 {i//BATCH_SIZE + 1}/{(len(all_files)-1)//BATCH_SIZE + 1}")
                
                try:
                    reader = SimpleDirectoryReader(
                        input_files=batch_files,
                        file_extractor=file_extractor
                    )
                    documents = reader.load_data()
                    
                    if documents:
                        # self.index.insert_documents(documents) # DEPRECATED
                        for doc in documents:
                            self.index.insert(doc)
                        logger.info(f"   ✅ 已插入 {len(documents)} 个文档片段")
                    
                except Exception as e:
                    logger.error(f"⚠️ 批次处理失败: {e}")
                    continue
                
                del documents
                if 'reader' in locals(): del reader
                gc.collect()

            logger.info("✅ 索引构建完成 (ChromaDB Persisted)")
            return True
            
        except Exception as e:
            logger.exception(f"构建索引失败: {e}")
            return False

    def get_stats(self) -> dict:
        """获取统计信息"""
        stats = {
            'total_documents': 0,
            'index_exists': False,
            'backend': 'chromadb'
        }
        try:
            if self.index:
                # Approximate count
                stats['total_documents'] = "N/A (ChromaDB)"
                stats['index_exists'] = True
        except Exception:
            pass
        return stats

# 全局实例
rag_system = PersistentRAGSystem()
