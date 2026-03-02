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
from pathlib import Path
from typing import List, Optional

# 尝试导入 faiss
try:
    import faiss
except ImportError:
    logging.warning("未检测到 faiss，请运行 pip install faiss-cpu")
    faiss = None

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
from llama_index.vector_stores.faiss import FaissVectorStore

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
        
    # 1. 检查控制字符密度 (Control Character Density)
    # 正常文本不应包含大量非打印字符 (除了换行 \n, 制表符 \t, 回车 \r)
    # 使用 set 提高查找效率
    # printable_chars = set(chr(i) for i in range(32, 127)) | {'\n', '\r', '\t', '\f'} 
    # 扩展到 Unicode 可打印范围 (简单起见，只要不是 C0/C1 控制字符且不是删除符)
    # 更严谨的做法是检查 category，但这里用简单启发式
    
    total_chars = len(text)
    control_chars = 0
    replacement_chars = text.count('\ufffd') # � 替换符
    
    for char in text:
        if char == '\ufffd':
            continue # 已经在外面统计了
        # 0-31 (except 9,10,13) and 127 are ASCII control chars
        code = ord(char)
        if (0 <= code <= 31 and code not in [9, 10, 13]) or code == 127:
            control_chars += 1
            
    # 计算比例
    control_ratio = control_chars / total_chars
    replacement_ratio = replacement_chars / total_chars
    
    # 阈值设定 (经验值)
    # 如果控制字符超过 5% 或者 替换符超过 5%，通常是乱码
    if control_ratio > 0.05:
        logger.warning(f"❌ 校验失败 [{filename}]: 控制字符过多 ({control_ratio:.2%}), 可能为二进制文件")
        return False
        
    if replacement_ratio > 0.05:
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
                # 使用 "text" 模式并开启 sort=True，可以按阅读顺序提取并减少乱码
                page_text = page.get_text("text", sort=True)
                text += page_text + "\n"
            doc.close()
            
            # 执行质量校验
            if not validate_content(text, filename=file.name):
                logger.error(f"🚫 拒绝索引文件: {file.name} (内容校验未通过)")
                # 返回空列表表示不索引此文件，或者抛出异常让上层处理
                # 这里选择抛出异常，以便在日志中更明显地看到
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
            # 1. 优先尝试加载本地下载的模型 (ModelScope)
            local_model_path = "./models/AI-ModelScope/bge-small-en-v1___5"
            embed_model_name = config.EMBED_MODEL_NAME
            
            if os.path.exists(local_model_path):
                logger.info(f"Using local embedding model from: {local_model_path}")
                embed_model_name = local_model_path
            else:
                logger.info(f"Local model not found at {local_model_path}, using HuggingFace model name: {embed_model_name}")

            # 2. 配置 Embedding 模型
            Settings.embed_model = "local" # 显式告诉 llama-index 使用本地/HuggingFace 模式
            
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
            # trust_remote_code=True is sometimes needed for custom models
            embed_model = HuggingFaceEmbedding(model_name=embed_model_name, trust_remote_code=True)
            Settings.embed_model = embed_model
            logger.info("✅ 成功配置嵌入模型")
            
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
        """构建新索引 (Batch Processing & Memory Optimized)"""
        try:
            if not os.path.exists(self.data_dir):
                logger.error(f"数据目录不存在: {self.data_dir}")
                return False

            # 获取所有文件
            import glob
            all_files = []
            for ext in ['*.pdf', '*.PDF', '*.txt', '*.md']:
                all_files.extend(glob.glob(os.path.join(self.data_dir, "**", ext), recursive=True))
            
            logger.info(f"📚 扫描到 {len(all_files)} 个文件")
            if not all_files:
                logger.warning("未找到文档，跳过索引构建")
                return False

            # 初始化空的 Vector Store
            d = 512 
            faiss_index = faiss.IndexFlatIP(d)
            vector_store = FaissVectorStore(faiss_index=faiss_index)
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            
            from llama_index.core.node_parser import TokenTextSplitter
            text_splitter = TokenTextSplitter(chunk_size=512, chunk_overlap=50)

            # 初始化空索引
            self.index = VectorStoreIndex.from_documents(
                [], 
                storage_context=storage_context,
                transformations=[text_splitter]
            )

            # 分批处理 (Batch Processing)
            BATCH_SIZE = 5 # 每次处理 5 个文件，避免 OOM
            import gc

            file_extractor = {}
            if fitz:
                file_extractor[".pdf"] = PyMuPDFReader()

            for i in range(0, len(all_files), BATCH_SIZE):
                batch_files = all_files[i : i + BATCH_SIZE]
                logger.info(f"🚀 处理批次 {i//BATCH_SIZE + 1}/{(len(all_files)-1)//BATCH_SIZE + 1} (文件 {i+1}-{min(i+BATCH_SIZE, len(all_files))})")
                
                try:
                    reader = SimpleDirectoryReader(
                        input_files=batch_files,
                        file_extractor=file_extractor
                    )
                    documents = reader.load_data()
                    
                    if documents:
                        self.index.insert_documents(documents)
                        logger.info(f"   ✅ 已插入 {len(documents)} 个文档片段")
                    
                    # 每一批都持久化一次，防止中途崩溃前功尽弃
                    self.index.storage_context.persist(persist_dir=self.persist_dir)
                    
                except Exception as e:
                    logger.error(f"⚠️ 批次处理失败: {e}")
                    continue
                
                # 强制垃圾回收
                del documents
                if 'reader' in locals(): 
                    del reader
                gc.collect()

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
