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
from pathlib import Path
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from metadata_storage import MetadataStorage

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
    def __init__(self, data_dir: str = "./food_research_data/datasets", persist_dir: str = "./storage", metadata_path: str = "./chroma_db_v3/metadata.json"):
        self.data_dir = data_dir
        self.persist_dir = persist_dir
        self.metadata_storage = MetadataStorage(storage_path=metadata_path)
        self.index: Optional[VectorStoreIndex] = None
        self.query_engine = None
        self.models_configured = False
        self.last_error: Optional[str] = None
        self.embedding_dim: int = 768
        self.embedding_mode: str = "unknown"
        self.last_build_report: Dict[str, Any] = {}

    def _infer_embedding_dim(self) -> int:
        """从现有持久化索引中推断向量维度，避免维度不一致导致检索失败。"""
        try:
            vector_store_path = os.path.join(self.persist_dir, "default__vector_store.json")
            if not os.path.exists(vector_store_path):
                return self.embedding_dim
            import json
            with open(vector_store_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            embeddings = data.get("embedding_dict", {})
            if not embeddings:
                return self.embedding_dim
            first_vec = next(iter(embeddings.values()))
            if isinstance(first_vec, list) and first_vec:
                return len(first_vec)
        except Exception as e:
            logging.warning(f"推断 embedding 维度失败，使用默认值: {e}")
        return self.embedding_dim

    def _collect_index_embedding_dims(self) -> set:
        """收集持久化索引中向量维度集合（用于识别混合维度污染）。"""
        dims = set()
        try:
            vector_store_path = os.path.join(self.persist_dir, "default__vector_store.json")
            if not os.path.exists(vector_store_path):
                return dims
            import json
            with open(vector_store_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            emb_dict = data.get("embedding_dict", {})
            for vec in emb_dict.values():
                if isinstance(vec, list):
                    dims.add(len(vec))
                    # 维度异常只需发现前两类即可判定污染
                    if len(dims) > 1:
                        break
        except Exception as e:
            logging.warning(f"收集索引维度失败: {e}")
        return dims

    def _iter_supported_files(self) -> List[str]:
        supported = (".pdf", ".docx", ".txt", ".md", ".csv", ".json")
        files: List[str] = []
        for root, _, names in os.walk(self.data_dir):
            for name in names:
                if name.startswith("."):
                    continue
                if name.lower().endswith(supported):
                    files.append(os.path.abspath(os.path.join(root, name)))
        return sorted(files)

    def _preflight_readable_files(self, files: List[str]) -> Tuple[List[str], List[Dict[str, str]]]:
        """重建前预检：跳过损坏/不可读文件并记录原因。"""
        usable: List[str] = []
        skipped: List[Dict[str, str]] = []

        pdf_reader = None
        pdf_reader_err = None
        try:
            from pypdf import PdfReader as _PdfReader
            pdf_reader = _PdfReader
        except Exception as e:
            pdf_reader_err = e

        for file_path in files:
            ext = os.path.splitext(file_path)[1].lower()
            try:
                if ext == ".pdf":
                    if pdf_reader is None:
                        # 无 pypdf 时仅检查文件可打开，避免直接阻断索引。
                        with open(file_path, "rb") as fh:
                            fh.read(1024)
                    else:
                        reader = pdf_reader(file_path)
                        _ = len(reader.pages)
                else:
                    with open(file_path, "rb") as fh:
                        fh.read(1024)
                usable.append(file_path)
            except Exception as e:
                reason = f"{type(e).__name__}: {e}"
                skipped.append({"file": file_path, "reason": reason})

        if pdf_reader is None and pdf_reader_err is not None:
            logging.warning(f"未启用 pypdf 预检，仅执行基础可读性检查: {pdf_reader_err}")

        return usable, skipped

    def _build_basic_metadata(self, file_path: str) -> dict:
        """为未提取到结构化信息的文件生成基础元数据。"""
        filename = os.path.basename(file_path)
        stem = Path(filename).stem
        year = "N/A"
        year_match = re.search(r"(19|20)\d{2}", stem)
        if year_match:
            year = year_match.group(0)
        return {
            "title": stem,
            "authors": [],
            "year": year,
            "journal": "Unknown Journal",
            "doi": "Not Available",
            "filename": filename,
            "source": "dual_protein_basic",
        }

    def _ensure_metadata_for_files(self, files: List[str]) -> None:
        """确保每个文档至少有一条可用元数据，便于健康检查和前端引用。"""
        created = 0
        for file_path in files:
            try:
                existing = self.metadata_storage.get_metadata(file_path)
                if existing:
                    continue
                self.metadata_storage.save_metadata(file_path, self._build_basic_metadata(file_path))
                created += 1
            except Exception as e:
                logging.warning(f"写入基础元数据失败（跳过）: {file_path} -> {e}")
        if created > 0:
            logging.info(f"已为 {created} 个文件补齐基础元数据")

    def _configure_models(self) -> None:
        """配置全局 embed_model，优先使用真实嵌入模型。"""
        if self.models_configured:
            return

        emb = None
        # 先给一个默认值，真实值在模型加载成功后覆盖
        self.embedding_dim = self._infer_embedding_dim()
        # 使用配置中的模型路径或模型名（禁止写死本地快照）
        try:
            from config import config as _cfg
            model_path = str(getattr(_cfg, "EMBED_MODEL_NAME", "BAAI/bge-small-zh-v1.5"))
            embed_source = str(getattr(_cfg, "EMBED_MODEL_SOURCE", "modelscope")).lower()
        except Exception:
            model_path = "BAAI/bge-small-zh-v1.5"
            embed_source = "modelscope"
        required_weights = ("model.safetensors", "pytorch_model.bin")
        is_local_dir = os.path.isdir(model_path)
        has_weights = any(os.path.exists(os.path.join(model_path, name)) for name in required_weights) if is_local_dir else True
        if is_local_dir and not has_weights:
            logging.warning(
                f"嵌入模型目录或权重不完整: {model_path}。"
                "将回退到占位向量模式，检索质量会下降。"
            )
        
        # 尝试使用真实的嵌入模型
        try:
            from sentence_transformers import SentenceTransformer
            from llama_index.core.embeddings import BaseEmbedding as _BaseEmb
            if embed_source == "modelscope" and not os.path.isdir(model_path):
                try:
                    from modelscope import snapshot_download
                    cache_root = os.path.abspath("models/modelscope_cache")
                    os.makedirs(cache_root, exist_ok=True)
                    model_path = snapshot_download(model_path, cache_dir=cache_root)
                    logging.info(f"通过 ModelScope 下载并使用模型目录: {model_path}")
                except Exception as ms_e:
                    logging.warning(f"ModelScope 下载失败，将尝试按原路径/模型名加载: {ms_e}")

            st_model = SentenceTransformer(model_path)
            logging.info(f"成功加载嵌入模型: {model_path}")
            try:
                model_dim = int(st_model.get_sentence_embedding_dimension())
                if model_dim > 0:
                    self.embedding_dim = model_dim
                    logging.info(f"检测到真实嵌入维度: {self.embedding_dim}")
            except Exception:
                pass

            class _STEmbedding(_BaseEmb):
                model_config = {"arbitrary_types_allowed": True}

                def _get_query_embedding(self, text: str) -> List[float]:
                    vec = st_model.encode(text)
                    return [float(x) for x in vec.tolist()] if hasattr(vec, 'tolist') else [float(x) for x in vec]

                def _get_text_embedding(self, text: str) -> List[float]:
                    vec = st_model.encode(text)
                    return [float(x) for x in vec.tolist()] if hasattr(vec, 'tolist') else [float(x) for x in vec]

                async def _aget_query_embedding(self, text: str) -> List[float]:
                    return self._get_query_embedding(text)

            emb = _STEmbedding()
            Settings.embed_model = emb
            self.embedding_mode = "real"
            logging.info(f"已配置真实嵌入模型")
        except Exception as e:
            self.embedding_mode = "failed"
            self.last_error = f"加载真实嵌入模型失败: {e}"
            logging.error(f"加载真实嵌入模型失败，已停止索引操作: {e}")
            raise

        self.models_configured = True

    def load_or_create_index(self) -> bool:
        """尝试加载已存在索引，失败则构建新索引。"""
        # reset last error on each attempt
        self.last_error = None
        if os.path.exists(self.persist_dir):
            logging.info("检测到持久化索引，尝试加载...")
            try:
                self._configure_models()
                storage_context = StorageContext.from_defaults(persist_dir=self.persist_dir)
                self.index = load_index_from_storage(storage_context)
                # 自动校验索引向量维度与当前模型维度是否一致，不一致则自动重建
                try:
                    model_dim = int(getattr(self, "embedding_dim", 0) or 0)
                    index_dims = self._collect_index_embedding_dims()
                    # 三种情况都重建：空索引维度未知、混合维度、唯一维度但与模型不一致
                    need_rebuild = False
                    if not index_dims:
                        need_rebuild = False
                    elif len(index_dims) > 1:
                        need_rebuild = True
                    elif model_dim and next(iter(index_dims)) != model_dim:
                        need_rebuild = True
                    if need_rebuild:
                        logging.warning(
                            f"检测到索引维度异常: index_dims={sorted(index_dims)}, model_dim={model_dim}，自动重建索引"
                        )
                        self.index = None
                        return self.rebuild_index()
                except Exception as dim_e:
                    logging.warning(f"索引维度校验失败（忽略并继续）: {dim_e}")
                logging.info("索引加载成功")
                return True
            except Exception as e:
                logging.warning(f"加载索引失败：{e}，将尝试重建")
                self.last_error = f"加载持久化索引失败: {e}"
                return self._build_new_index()

        logging.info("未检测到持久化索引，开始构建新索引")
        return self._build_new_index()

    def _build_new_index(self) -> bool:
        """从 data_dir 读取支持的文档并构建索引，构建成功后持久化。"""
        try:
            self._configure_models()
            files = self._iter_supported_files()
            total_supported_files = len(files)
            usable_files, skipped_files = self._preflight_readable_files(files)
            file_count = len(usable_files)
            self._ensure_metadata_for_files(usable_files)

            self.last_build_report = {
                "data_dir": os.path.abspath(self.data_dir),
                "persist_dir": os.path.abspath(self.persist_dir),
                "total_supported_files": total_supported_files,
                "usable_files": file_count,
                "skipped_files_count": len(skipped_files),
                "skipped_files": skipped_files,
                "indexed_documents": 0,
                "status": "running",
            }

            logging.info(
                f"将从 {self.data_dir} 构建索引：支持文件 {total_supported_files}，可用文件 {file_count}，跳过 {len(skipped_files)}"
            )
            if skipped_files:
                sample = ", ".join(item["file"] for item in skipped_files[:5])
                logging.warning(f"预检跳过 {len(skipped_files)} 个不可读文件，示例: {sample}")

            if file_count == 0:
                msg = f"数据目录 {self.data_dir} 中未检测到支持的文档，无法构建索引。"
                logging.error(msg)
                self.last_error = msg
                self.last_build_report["status"] = "failed"
                return False

            # 配置安全的文本分割器（避免RecursionError）
            try:
                from llama_index.core.node_parser import SentenceSplitter
                # 使用较小的chunk_size和简单的分割策略
                text_splitter = SentenceSplitter(
                    chunk_size=512,  # 减小chunk大小
                    chunk_overlap=50,
                    paragraph_separator="\n\n",
                    secondary_chunking_regex="[^,.;。？！]+[,.;。？！]?",  # 简单的句子分割
                )
                Settings.text_splitter = text_splitter
                Settings.chunk_size = 512
                Settings.chunk_overlap = 50
                logging.info("已配置安全的文本分割器（chunk_size=512, chunk_overlap=50）")
            except Exception as e:
                logging.warning(f"配置文本分割器失败，使用默认配置: {e}")

            # 分批读文件并增量写入，降低一次性内存峰值
            batch_size = 25
            try:
                from config import config as _cfg
                batch_size = max(1, int(getattr(_cfg, "INDEX_BUILD_BATCH_SIZE", 25)))
            except Exception:
                pass

            self.index = None
            total_docs = 0
            for i in range(0, file_count, batch_size):
                batch_files = usable_files[i:i + batch_size]
                logging.info(f"处理批次 {i // batch_size + 1}，文件数 {len(batch_files)}")
                reader = SimpleDirectoryReader(input_files=batch_files)
                documents = reader.load_data()
                total_docs += len(documents)

                if self.index is None:
                    self.index = VectorStoreIndex.from_documents(documents)
                else:
                    for doc in documents:
                        self.index.insert(doc)

            if self.index is None:
                msg = "文档读取完成但未生成有效索引"
                logging.error(msg)
                self.last_error = msg
                self.last_build_report["status"] = "failed"
                return False
            logging.info(f"索引构建成功，共文档块 {total_docs}")
            self.last_build_report["indexed_documents"] = total_docs
            self.last_build_report["status"] = "success"

            try:
                self.index.storage_context.persist(persist_dir=self.persist_dir)
                logging.info(f"索引已持久化到 {self.persist_dir}")
            except Exception as e:
                logging.warning(f"索引构建成功但持久化失败：{e}")

            return True
        except Exception as e:
            logging.exception("构建索引失败：")
            self.last_error = str(e)
            if self.last_build_report:
                self.last_build_report["status"] = "failed"
            return False

    def load_existing_index(self) -> bool:
        """仅加载已有索引；不存在时返回 False。"""
        self.last_error = None
        if not os.path.exists(self.persist_dir):
            self.last_error = f"索引目录不存在: {self.persist_dir}"
            return False
        try:
            self._configure_models()
            storage_context = StorageContext.from_defaults(persist_dir=self.persist_dir)
            self.index = load_index_from_storage(storage_context)
            return True
        except Exception as e:
            self.last_error = f"加载已有索引失败: {e}"
            logging.warning(self.last_error)
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
                self.query_engine = self.index.as_query_engine(similarity_top_k=similarity_top_k, response_mode="compact")
            except Exception:
                # 若底层版本不支持 as_query_engine，则返回索引本身
                return self.index

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


try:
    from config import config
except Exception:
    config = None

# 全局实例：使用 config 中的目录（避免默认指向空目录）
if config is not None:
    rag_system = PersistentRAGSystem(data_dir=config.DATA_DIR, persist_dir=config.PERSIST_DIR, metadata_path=str(config.CHROMA_DB_DIR / 'metadata.json'))
else:
    rag_system = PersistentRAGSystem()


# ============================================================
# LLM 配置 (延迟加载)
# ============================================================

deepseek_client = None
deepseek_model = None

def configure_llm():
    """配置 DeepSeek LLM 客户端"""
    global deepseek_client, deepseek_model
    if deepseek_client is not None:
        return

    try:
        from config import config
        from openai import OpenAI

        if config.DEEPSEEK_API_KEY and config.DEEPSEEK_BASE_URL:
            deepseek_client = OpenAI(
                api_key=config.DEEPSEEK_API_KEY,
                base_url=config.DEEPSEEK_BASE_URL,
            )
            deepseek_model = config.DEEPSEEK_MODEL
            logging.info(f"DeepSeek client 已配置，模型: {deepseek_model}, URL: {config.DEEPSEEK_BASE_URL}")
        else:
            logging.warning("环境变量 DEEPSEEK_API_KEY 或 DEEPSEEK_BASE_URL 未设置，LLM 功能将不可用。")

    except ImportError as e:
        logging.error(f"导入 OpenAI 库失败，请确保 'openai' 已安装: {e}")
    except Exception as e:
        logging.error(f"配置 DeepSeek client 失败: {e}")
