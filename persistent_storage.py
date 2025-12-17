#!/usr/bin/env python3
"""persistent_storage.py

稳健的持久化索引管理器（单文件实现，避免导入时触发模型下载）。

主要特性：
- 延迟模型/嵌入配置
- 索引构建时备份 + 失败恢复
- 支持增量添加与查询引擎获取
"""

from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime
from typing import List, Optional

try:
    from llama_index.core import (
        VectorStoreIndex,
        SimpleDirectoryReader,
        Settings,
        StorageContext,
        load_index_from_storage,
    )
except Exception:
    # 兼容不同版本的导入路径
    from llama_index import (
        VectorStoreIndex,
        SimpleDirectoryReader,
        Settings,
        StorageContext,
        load_index_from_storage,
    )


logging.basicConfig(level=logging.INFO)


class PersistentRAGSystem:
    def __init__(self, data_dir: str = "./food_research_data", persist_dir: str = "./storage"):
        self.data_dir = data_dir
        self.persist_dir = persist_dir
        self.index: Optional[VectorStoreIndex] = None
        self.query_engine = None
        self.models_configured = False
        
        # 初始化元数据管理器
        from metadata_storage import MetadataStorage
        from pdf_metadata_extractor import PDFMetadataExtractor
        self.metadata_storage = MetadataStorage()
        self.metadata_extractor = PDFMetadataExtractor()

    def _configure_models(self) -> None:
        """延迟配置模型/嵌入；尽量保持轻量。

        如果需要在这里初始化具体的嵌入或 LLM，请谨慎实现，避免阻塞导入。
        """
        if self.models_configured:
            return

        # 配置DeepSeek LLM（直接使用原生OpenAI客户端）
        try:
            from openai import OpenAI as OpenAIClient
            from dotenv import load_dotenv
            
            load_dotenv()
            
            api_key = os.getenv("DEEPSEEK_API_KEY")
            base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
            model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
            
            if api_key:
                # 创建DeepSeek客户端（存储为全局变量供查询时使用）
                import sys
                current_module = sys.modules[__name__]
                current_module.deepseek_client = OpenAIClient(
                    api_key=api_key,
                    base_url=base_url
                )
                current_module.deepseek_model = model
                logging.info(f"成功配置 DeepSeek 客户端: {model} at {base_url}")
            else:
                logging.warning("未找到 DEEPSEEK_API_KEY，LLM 功能可能无法使用")
        except Exception as e:
            logging.warning(f"配置 DeepSeek 客户端失败: {e}")

        # 配置嵌入模型（支持多种类型）
        embed_model_type = os.getenv("EMBED_MODEL_TYPE", "huggingface").lower()
        
        try:
            if embed_model_type == "huggingface":
                # 使用HuggingFace本地模型（推荐）
                embed_model_name = os.getenv("EMBED_MODEL_NAME", "BAAI/bge-small-zh-v1.5")
                try:
                    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
                    embed_model = HuggingFaceEmbedding(model_name=embed_model_name)
                    Settings.embed_model = embed_model
                    logging.info(f"成功配置 HuggingFace 嵌入模型: {embed_model_name}")
                except Exception as e:
                    logging.error(f"加载 HuggingFace 嵌入模型失败: {e}")
                    raise
                    
            elif embed_model_type == "openai":
                # 使用OpenAI嵌入模型
                openai_api_key = os.getenv("OPENAI_API_KEY")
                openai_model = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
                
                if not openai_api_key:
                    raise ValueError("EMBED_MODEL_TYPE=openai 但未设置 OPENAI_API_KEY")
                
                try:
                    from llama_index.embeddings.openai import OpenAIEmbedding
                    embed_model = OpenAIEmbedding(
                        api_key=openai_api_key,
                        model=openai_model
                    )
                    Settings.embed_model = embed_model
                    logging.info(f"成功配置 OpenAI 嵌入模型: {openai_model}")
                except Exception as e:
                    logging.error(f"加载 OpenAI 嵌入模型失败: {e}")
                    raise
                    
            elif embed_model_type == "local":
                # 使用默认本地模型
                Settings.embed_model = "local"
                logging.info("使用默认本地嵌入模型")
                
            else:
                logging.warning(f"未知的嵌入模型类型: {embed_model_type}，使用默认配置")
                Settings.embed_model = "local"
                
        except Exception as e:
            logging.error(f"配置嵌入模型失败: {e}")
            # 回退到默认配置
            try:
                Settings.embed_model = "local"
                logging.info("回退到默认本地嵌入模型")
            except Exception:
                pass

        self.models_configured = True

    def load_or_create_index(self) -> bool:
        """尝试加载已存在索引，失败则构建新索引。"""
        if os.path.exists(self.persist_dir):
            logging.info("检测到持久化索引，尝试加载...")
            try:
                storage_context = StorageContext.from_defaults(persist_dir=self.persist_dir)
                self.index = load_index_from_storage(storage_context)
                logging.info("索引加载成功")
                return True
            except Exception as e:
                logging.warning(f"加载索引失败：{e}，将尝试重建")
                return self._build_new_index()

        logging.info("未检测到持久化索引，开始构建新索引")
        return self._build_new_index()

    def _build_new_index(self) -> bool:
        """从 data_dir 读取支持的文档并构建索引，构建成功后持久化。"""
        try:
            self._configure_models()

            supported = (".pdf", ".docx", ".txt", ".md", ".csv", ".json")
            file_count = 0
            for root, dirs, files in os.walk(self.data_dir):
                for f in files:
                    if f.startswith("."):
                        continue
                    if f.lower().endswith(supported):
                        file_count += 1

            logging.info(f"将从 {self.data_dir} 读取 {file_count} 个支持的文档进行索引构建")

            reader = SimpleDirectoryReader(self.data_dir, recursive=True)
            documents = reader.load_data()

            logging.info(f"读取到 {len(documents)} 个文档，开始构建向量索引...")
            
            # 提取PDF元数据
            logging.info("开始提取PDF元数据...")
            pdf_count = 0
            for doc in documents:
                file_path = doc.metadata.get('file_path', '')
                if file_path.lower().endswith('.pdf'):
                    try:
                        # 检查是否已有元数据
                        if not self.metadata_storage.has_metadata(file_path):
                            metadata = self.metadata_extractor.extract_metadata(file_path)
                            self.metadata_storage.save_metadata(file_path, metadata)
                            pdf_count += 1
                    except Exception as e:
                        logging.error(f"提取元数据失败 {file_path}: {str(e)}")
            
            logging.info(f"成功提取 {pdf_count} 个PDF文件的元数据")

            # 构造嵌入实现：使用 HuggingFace 本地模型
            emb = None
            
            # 尝试使用正确的导入路径
            try:
                from llama_index.embeddings.huggingface import HuggingFaceEmbedding
                
                # 使用模型名称而不是本地路径，让它自动下载
                emb = HuggingFaceEmbedding(model_name="BAAI/bge-small-zh-v1.5")
                logging.info("成功加载 HuggingFace 嵌入模型: BAAI/bge-small-zh-v1.5")
            except Exception as e:
                logging.warning(f"加载 HuggingFace 嵌入模型失败: {e}")
                
                # 如果失败，设置环境变量避免使用 OpenAI
                os.environ.setdefault("OPENAI_API_KEY", "sk-dummy")
                emb = None

            # 构建索引
            try:
                if emb is not None:
                    # 使用自定义嵌入模型
                    self.index = VectorStoreIndex.from_documents(documents, embed_model=emb)
                    logging.info("使用自定义嵌入模型构建索引")
                else:
                    # 使用默认配置（需要设置 OPENAI_API_KEY）
                    self.index = VectorStoreIndex.from_documents(documents)
                    logging.info("使用默认嵌入模型构建索引")
            except Exception as e:
                logging.exception("索引构建失败：")
                return False

            try:
                self.index.storage_context.persist(persist_dir=self.persist_dir)
                logging.info(f"索引已持久化到 {self.persist_dir}")
            except Exception as e:
                logging.warning(f"索引构建成功但持久化失败：{e}")

            return True
        except Exception as e:
            logging.exception("构建索引失败：")
            return False

    def rebuild_index(self) -> bool:
        """备份旧索引后重建；重建失败则尝试恢复备份。"""
        logging.info("开始重建索引（备份旧索引）...")
        backup_dir = None
        if os.path.exists(self.persist_dir):
            ts = datetime.now().strftime("%Y%m%d%H%M%S")
            backup_dir = f"{self.persist_dir}.bak_{ts}"
            try:
                shutil.move(self.persist_dir, backup_dir)
                logging.info(f"已将旧索引备份到 {backup_dir}")
            except Exception as e:
                logging.warning(f"备份旧索引失败：{e}")

        success = self._build_new_index()
        if success:
            if backup_dir and os.path.exists(backup_dir):
                try:
                    shutil.rmtree(backup_dir)
                    logging.info(f"已删除备份 {backup_dir}")
                except Exception as e:
                    logging.warning(f"删除备份失败：{e}")
            return True

        # 构建失败，恢复备份（如有）
        if backup_dir and os.path.exists(backup_dir):
            try:
                if os.path.exists(self.persist_dir):
                    shutil.rmtree(self.persist_dir)
                shutil.move(backup_dir, self.persist_dir)
                logging.info("重建失败，已从备份恢复旧索引")
            except Exception as e:
                logging.error(f"恢复备份失败：{e}")
        return False

    def get_query_engine(self, similarity_top_k: int = 3):
        """返回查询引擎或索引供调用方使用。"""
        if self.index is None:
            raise ValueError("索引未初始化，请先调用 load_or_create_index() 或 rebuild_index()")

        self._configure_models()

        if self.query_engine is None:
            try:
                self.query_engine = self.index.as_query_engine(
                    similarity_top_k=similarity_top_k, 
                    response_mode="compact"
                )
            except Exception as e:
                logging.warning(f"创建查询引擎失败: {e}，尝试使用默认参数")
                try:
                    # 尝试不带参数创建
                    self.query_engine = self.index.as_query_engine()
                except Exception as e2:
                    logging.error(f"无法创建查询引擎: {e2}")
                    raise ValueError(f"无法创建查询引擎: {e2}")

        return self.query_engine

    def add_documents(self, new_docs: List) -> bool:
        """增量添加文档并持久化索引。"""
        if self.index is None:
            raise ValueError("索引未初始化")

        logging.info(f"增量添加 {len(new_docs)} 个文档到索引...")
        self._configure_models()

        for doc in new_docs:
            try:
                self.index.insert(doc)
            except Exception as e:
                logging.warning(f"插入文档失败（跳过）：{e}")

        try:
            self.index.storage_context.persist(persist_dir=self.persist_dir)
            logging.info("增量添加完成并已持久化")
        except Exception as e:
            logging.error(f"持久化失败：{e}")
            return False

        self.query_engine = None
        return True

    def get_stats(self) -> dict:
        """返回索引统计信息。"""
        if self.index is None:
            return {"status": "未初始化", "persist_dir": self.persist_dir, "index_exists": os.path.exists(self.persist_dir)}

        try:
            store = self.index.storage_context.docstore
            total = len(getattr(store, "docs", {}))
        except Exception:
            total = 0

        return {"status": "已初始化", "total_documents": total, "persist_dir": self.persist_dir, "index_exists": os.path.exists(self.persist_dir)}


# 全局实例：导入模块不会触发索引构建或模型下载
rag_system = PersistentRAGSystem()
