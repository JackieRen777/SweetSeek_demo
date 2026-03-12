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
# 屏蔽第三方库的嘈杂日志
logging.getLogger("chromadb").setLevel(logging.ERROR)
logging.getLogger("posthog").setLevel(logging.ERROR)
logging.getLogger("backoff").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)

logger = logging.getLogger("sweetseek.rag")

# 禁用 PostHog 遥测
import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
# 禁用 ChromaDB 遥测
os.environ["CHROMA_TELEMETRY_IMPL"] = "chromadb.telemetry.product.posthog.Posthog" 
# 尝试通过环境变量禁用 huggingface 遥测
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

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
        # ChromaDB path: 使用配置中的绝对路径，避免使用相对路径
        self.chroma_path = str(config.CHROMA_DB_DIR)
        logger.info(f"💾 ChromaDB 存储路径: {self.chroma_path}")
        
        self.index: Optional[VectorStoreIndex] = None
        self.query_engine = None
        self.models_configured = False
        
        # 初始化元数据管理器
        from metadata_storage import MetadataStorage
        from pdf_metadata_extractor import PDFMetadataExtractor
        
        metadata_path = os.path.join(self.chroma_path, "metadata.json")
        self.metadata_storage = MetadataStorage(storage_path=metadata_path)
        self.metadata_extractor = PDFMetadataExtractor()

    def _configure_models(self) -> None:
        """配置模型/嵌入"""
        if self.models_configured:
            return

        # 3. 初始化 LLM（优先使用 DeepSeek）
        llm = None
        try:
            # 显式禁用 OpenAI 以防 LlamaIndex 自动回退
            os.environ["OPENAI_API_KEY"] = "sk-placeholder-to-prevent-error"
            
            # 使用 OpenAI 兼容模式连接 DeepSeek
            # 注意：LlamaIndex 的 OpenAI 类会校验 model name，如果 deepseek-chat 不在它的允许列表里，可能会报错。
            # 但我们可以尝试直接使用 OpenAI 类并配合 api_base。
            from llama_index.llms.openai import OpenAI
            
            # 使用一个 OpenAI 允许的模型名，但在 api_base 指向 DeepSeek
            # 或者，如果 LlamaIndex 版本较新，可以直接用 deepseek-chat，但似乎当前的 validation 失败了。
            # 这里的 trick 是：用一个通用名字，或者忽略校验（如果库支持）。
            # 让我们尝试使用 OpenAI 类，并指定 api_base，同时把 model 设为 "deepseek-chat"
            # 如果还报错，可能需要 patch 一下 metadata 或者换用其他通用类。
            
            llm = OpenAI(
                model="deepseek-chat",
                api_key=config.DEEPSEEK_API_KEY,
                api_base="https://api.deepseek.com/v1",
                temperature=0.1,
                max_retries=3,
                timeout=60.0,
                # 关键：跳过模型名称校验（如果库支持这个参数，或者我们需要更底层的 hack）
                # LlamaIndex 的 OpenAI 类通常没有直接的 skip_validation 参数。
                # 尝试改用 OpenAILike 类（如果存在），它通常更宽容。
            )
            
            # 尝试导入 OpenAILike，它通常用于兼容 OpenAI 接口的其他模型
            try:
                from llama_index.llms.openai_like import OpenAILike
                llm = OpenAILike(
                    model="deepseek-chat",
                    api_key=config.DEEPSEEK_API_KEY,
                    api_base="https://api.deepseek.com/v1",
                    temperature=0.1,
                    is_chat_model=True
                )
                logger.info("✅ 使用 OpenAILike 配置 DeepSeek")
            except ImportError:
                logger.warning("OpenAILike 未找到，回退到 OpenAI 类 (可能会有校验警告)")
                # 保持上面的 llm = OpenAI(...)
                pass

            logger.info("✅ 成功配置 DeepSeek 客户端")
        except ImportError:
            logger.warning("DeepSeek 模块未安装，尝试使用 OpenAI 兼容模式")
            from llama_index.llms.openai import OpenAI
            llm = OpenAI(
                model="deepseek-chat",
                api_key=config.DEEPSEEK_API_KEY,
                api_base="https://api.deepseek.com/v1"
            )
            
            # 尝试导入 OpenAILike
            try:
                from llama_index.llms.openai_like import OpenAILike
                llm = OpenAILike(
                    model="deepseek-chat",
                    api_key=config.DEEPSEEK_API_KEY,
                    api_base="https://api.deepseek.com/v1",
                    is_chat_model=True
                )
                # 显式覆盖 metadata，防止 LlamaIndex 尝试校验上下文窗口
                # OpenAILike 类有时会自动推断，如果不行，我们需要 mock 它的 metadata
            except ImportError:
                # 如果 OpenAILike 不可用，回退到 OpenAI 并尝试绕过校验
                # 注意：这在较新版本的 LlamaIndex 中可能很难绕过
                pass
  
            Settings.llm = llm

        try:
            local_model_path = os.path.abspath(config.EMBED_MODEL_NAME)
            
            # 模型路径检查逻辑
            if os.path.exists(local_model_path):
                # 1. 本地路径存在，直接使用
                logger.info(f"✅ 使用本地 Embedding 模型: {local_model_path}")
                embed_model_name = local_model_path
            elif "/" in config.EMBED_MODEL_NAME and not config.EMBED_MODEL_NAME.startswith("/"):
                # 2. 看起来是 HuggingFace/ModelScope ID
                # 尝试从 ModelScope 下载（如果配置了）
                model_id = config.EMBED_MODEL_NAME
                
                if hasattr(config, 'EMBED_MODEL_SOURCE') and config.EMBED_MODEL_SOURCE == 'modelscope':
                    try:
                        logger.info(f"📥 尝试从 ModelScope 下载模型: {model_id}")
                        from modelscope.hub.snapshot_download import snapshot_download
                        # 下载到默认缓存目录
                        embed_model_name = snapshot_download(model_id)
                        logger.info(f"✅ ModelScope 模型下载成功: {embed_model_name}")
                    except ImportError:
                        logger.warning("⚠️ 未安装 modelscope，尝试直接连接 HuggingFace")
                        logger.info("建议运行: pip install modelscope")
                        embed_model_name = model_id
                    except Exception as e:
                        logger.error(f"❌ ModelScope 下载失败: {e}，将尝试 HuggingFace")
                        embed_model_name = model_id
                else:
                    logger.info(f"ℹ️ 使用 HuggingFace Hub 模型: {model_id}")
                    embed_model_name = model_id
            else:
                logger.error(f"❌ 本地模型不存在且不是有效的模型ID: {local_model_path}")
                embed_model_name = "local" # Fallback

            # 2. 配置 Embedding 模型
            try:
                # 尝试使用 llama_index 的官方 HuggingFaceEmbedding
                from llama_index.embeddings.huggingface import HuggingFaceEmbedding
                embed_model = HuggingFaceEmbedding(
                    model_name=embed_model_name,
                    trust_remote_code=True,
                    device='cpu'
                )
            except ImportError as e:
                # Fallback: 如果 huggingface-hub 版本冲突，使用自定义的 SentenceTransformers 实现
                logger.warning(f"⚠️ llama-index-embeddings-huggingface 导入失败 ({e})，切换到本地 SentenceTransformers 实现")
                from llama_index.core.base.embeddings.base import BaseEmbedding
                from sentence_transformers import SentenceTransformer
                
                class LocalSentenceTransformerEmbedding(BaseEmbedding):
                    _model: SentenceTransformer = None
                    
                    def __init__(self, model_name: str, **kwargs):
                        super().__init__(**kwargs)
                        self._model = SentenceTransformer(model_name, device='cpu')
                        
                    def _get_query_embedding(self, query: str) -> List[float]:
                        return self._model.encode(query).tolist()
                        
                    def _get_text_embedding(self, text: str) -> List[float]:
                        return self._model.encode(text).tolist()
                        
                    async def _aget_query_embedding(self, query: str) -> List[float]:
                        return self._get_query_embedding(query)
                        
                    async def _aget_text_embedding(self, text: str) -> List[float]:
                        return self._get_text_embedding(text)

                embed_model = LocalSentenceTransformerEmbedding(model_name=embed_model_name)

            Settings.embed_model = embed_model
            logger.info("✅ 成功配置嵌入模型")
            
        except Exception as e:
            logger.error(f"配置嵌入模型失败: {e}")
            Settings.embed_model = "local"

        self.models_configured = True

    def load_or_create_index(self):
        """加载现有索引或创建新索引"""
        # 1. 显式配置全局 Settings，防止 LlamaIndex 自动下载默认模型
        logger.info(f"正在配置全局 Embedding 模型: {config.EMBED_MODEL_NAME}")
        try:
            # 显式加载本地模型
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
            embed_model = HuggingFaceEmbedding(
                model_name=config.EMBED_MODEL_NAME,
                trust_remote_code=True
            )
            Settings.embed_model = embed_model
            logger.info("✅ 全局 Embedding 模型配置完成")
        except Exception as e:
            logger.error(f"❌ 配置 Embedding 模型失败: {e}")
            return False

        # 初始化 LLM 变量
        llm = None
        try:
             # 确保 LLM 被正确初始化
             self._configure_models()
             if hasattr(Settings, 'llm'):
                 llm = Settings.llm
        except Exception as e:
             logger.warning(f"LLM 初始化警告: {e}")

        # 检查是否已存在索引
        index_exists = os.path.exists(self.chroma_path) and os.listdir(self.chroma_path)
        if index_exists:
            logger.info("正在加载现有 ChromaDB 索引...")
            if self._load_from_disk():
                # 检查索引是否为空
                try:
                    chroma_client = chromadb.PersistentClient(path=self.chroma_path)
                    collection = chroma_client.get_or_create_collection("sweetseek_docs")
                    count = collection.count()
                    logger.info(f"📊 现有索引包含 {count} 个文档片段")
                    if count > 0:
                        return True
                    else:
                        logger.warning("⚠️ 现有索引为空，准备重新扫描...")
                except Exception as e:
                    logger.warning(f"⚠️ 无法检查索引数量: {e}")
        
        logger.info("未找到有效索引或索引为空，开始构建...")
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

            # 配置检索器
            self.query_engine = self.index.as_query_engine(
                similarity_top_k=config.RAG_TOP_K,
                # node_postprocessors=[
                #     SimilarityPostprocessor(similarity_cutoff=config.RAG_SIMILARITY_THRESHOLD)
                # ]
            )
            # 手动添加自定义后处理逻辑，以便记录日志
            logger.info(f"✅ 查询引擎已就绪 (Top-K={config.RAG_TOP_K}, Threshold={config.RAG_SIMILARITY_THRESHOLD})")

            logger.info("✅ ChromaDB 索引加载成功")
            return True
        except Exception as e:
            logger.error(f"从磁盘加载失败: {e}")
            # 如果加载失败，不要直接抛出，而是尝试重建
            # self.query_engine = None # 不要设置为 None，让它有机会重建
            logger.info("尝试重建索引...")
            return False

    def _build_new_index(self) -> bool:
        """构建新索引"""
        try:
            if not os.path.exists(self.data_dir):
                logger.error(f"数据目录不存在: {self.data_dir}")
                return False

            all_files = []
            for ext in ['*.pdf', '*.PDF', '*.txt', '*.md']:
                found = glob.glob(os.path.join(self.data_dir, "**", ext), recursive=True)
                logger.info(f"🔎 扫描 {ext}: 找到 {len(found)} 个文件")
                all_files.extend(found)
            
            logger.info(f"📚 总计扫描到 {len(all_files)} 个文件 (目录: {self.data_dir})")
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

    async def aquery(self, query_text: str):
        if not self.query_engine:
            logger.warning("Query engine not initialized")
            return "System not initialized"
        
        try:
            logger.info(f"🔍 执行检索: {query_text}")
            
            # 1. 获取检索器
            retriever = self.index.as_retriever(similarity_top_k=config.RAG_TOP_K)
            nodes = await retriever.aretrieve(query_text)
            
            if not nodes:
                logger.warning("❌ 未检索到任何文档")
                return "未检索到相关文献。"
                
            logger.info(f"📚 原始检索到 {len(nodes)} 个文档:")
            filtered_nodes = []
            
            for i, node in enumerate(nodes):
                score = getattr(node, 'score', 0.0)
                logger.info(f"   [{i}] Score: {score:.4f} | Text: {node.text[:30]}...")
                
                # 手动应用阈值过滤
                if score >= config.RAG_SIMILARITY_THRESHOLD:
                    filtered_nodes.append(node)
                else:
                    logger.info(f"   ⚠️ 过滤掉 (低于阈值 {config.RAG_SIMILARITY_THRESHOLD})")
            
            if not filtered_nodes:
                logger.warning(f"❌ 过滤后无文档保留 (Threshold={config.RAG_SIMILARITY_THRESHOLD})")
                return "未检索到相关文献，请尝试更具体的关键词或降低相似度阈值。"
                
            logger.info(f"✅ 最终保留 {len(filtered_nodes)} 个文档")
            
            # 2. 生成回答 (使用 DeepSeek)
            # 这里简化处理，实际应该调用 DeepSeek API
            # 为了调试，我们先返回检索到的内容摘要
            context = "\n\n".join([n.text for n in filtered_nodes])
            return f"[检索成功] 找到 {len(filtered_nodes)} 篇文献。\n\n摘要内容：\n{context[:500]}..."
            
        except Exception as e:
            logger.error(f"检索出错: {e}")
            return f"检索出错: {str(e)}"

# 全局实例
rag_system = PersistentRAGSystem()
