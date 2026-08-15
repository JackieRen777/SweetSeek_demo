import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from knowledge_paths import get_domain_paths

# Load environment variables
load_dotenv()


def _normalize_openai_base_url(url: str) -> str:
    cleaned = (url or "").strip().rstrip("/")
    if not cleaned:
        return "https://api.deepseek.com/v1"
    return cleaned if cleaned.endswith("/v1") else f"{cleaned}/v1"


@dataclass
class RAGConfig:
    """甜味模式 RAG 参数（默认值偏快、偏精）"""
    target_min: int = 15
    target_max: int = 30
    similarity_threshold: float = 0.3
    min_threshold: float = 0.10
    threshold_step: float = 0.03
    max_top_k: int = 120
    hard_top_k: int = 200
    max_chunks_per_paper: int = 2
    context_window: int = 9000
    qa_max_tokens: int = 900
    show_reasoning: bool = False
    disable_reasoning_hard: bool = True
    allow_weak_supplement: bool = True

    @classmethod
    def from_env(cls, prefix: str = "SWEET") -> "RAGConfig":
        """从环境变量加载，prefix 为 SWEET 或空"""
        def _int(key: str, default: int) -> int:
            return int(os.getenv(f"{prefix}_{key}", os.getenv(key, str(default))))
        def _float(key: str, default: float) -> float:
            return float(os.getenv(f"{prefix}_{key}", os.getenv(key, str(default))))
        def _bool(key: str, default: bool) -> bool:
            return os.getenv(f"{prefix}_{key}", os.getenv(key, str(default).lower())).lower() in ("true", "1", "yes")

        return cls(
            target_min=_int("RETRIEVAL_TARGET_MIN", cls.target_min),
            target_max=_int("RETRIEVAL_TARGET_MAX", cls.target_max),
            similarity_threshold=_float("RAG_SIMILARITY_THRESHOLD", cls.similarity_threshold),
            min_threshold=_float("RETRIEVAL_MIN_THRESHOLD", cls.min_threshold),
            threshold_step=_float("RETRIEVAL_THRESHOLD_STEP", cls.threshold_step),
            max_top_k=_int("RETRIEVAL_TOPK_CAP", cls.max_top_k),
            hard_top_k=_int("RETRIEVAL_HARD_TOPK", cls.hard_top_k),
            max_chunks_per_paper=_int("RETRIEVAL_MAX_CHUNKS_PER_PAPER", cls.max_chunks_per_paper),
            context_window=_int("RAG_CONTEXT_WINDOW", cls.context_window),
            qa_max_tokens=_int("QA_MAX_TOKENS", cls.qa_max_tokens),
            show_reasoning=_bool("QA_SHOW_REASONING", cls.show_reasoning),
            disable_reasoning_hard=_bool("QA_DISABLE_REASONING_HARD", cls.disable_reasoning_hard),
            allow_weak_supplement=_bool("RETRIEVAL_ALLOW_WEAK_SUPPLEMENT", cls.allow_weak_supplement),
        )


@dataclass
class DualRAGConfig(RAGConfig):
    """双蛋白模式 RAG 参数（默认值偏深、偏广）"""
    target_min: int = 25
    target_max: int = 60
    similarity_threshold: float = 0.15
    min_threshold: float = 0.08
    threshold_step: float = 0.02
    max_top_k: int = 260
    hard_top_k: int = 400
    context_window: int = 18000
    qa_max_tokens: int = 1800
    allow_weak_supplement: bool = False

    @classmethod
    def from_env(cls) -> "DualRAGConfig":
        def _int(key: str, default: int) -> int:
            return int(os.getenv(f"DUAL_{key}", os.getenv(key, str(default))))
        def _float(key: str, default: float) -> float:
            return float(os.getenv(f"DUAL_{key}", os.getenv(key, str(default))))
        def _bool(key: str, default: bool) -> bool:
            val = os.getenv(f"DUAL_{key}", os.getenv(key, str(default).lower()))
            return val.lower() in ("true", "1", "yes")

        return cls(
            target_min=_int("RETRIEVAL_TARGET_MIN", cls.target_min),
            target_max=_int("RETRIEVAL_TARGET_MAX", cls.target_max),
            similarity_threshold=_float("RAG_SIMILARITY_THRESHOLD", cls.similarity_threshold),
            min_threshold=_float("RETRIEVAL_MIN_THRESHOLD", cls.min_threshold),
            threshold_step=_float("RETRIEVAL_THRESHOLD_STEP", cls.threshold_step),
            max_top_k=_int("RETRIEVAL_TOPK_CAP", cls.max_top_k),
            hard_top_k=_int("RETRIEVAL_HARD_TOPK", cls.hard_top_k),
            max_chunks_per_paper=_int("RETRIEVAL_MAX_CHUNKS_PER_PAPER", cls.max_chunks_per_paper),
            context_window=_int("RAG_CONTEXT_WINDOW", cls.context_window),
            qa_max_tokens=_int("QA_MAX_TOKENS", cls.qa_max_tokens),
            show_reasoning=_bool("QA_SHOW_REASONING", cls.show_reasoning),
            disable_reasoning_hard=_bool("QA_DISABLE_REASONING_HARD", cls.disable_reasoning_hard),
            allow_weak_supplement=_bool("RETRIEVAL_ALLOW_WEAK_SUPPLEMENT", cls.allow_weak_supplement),
        )


class Config:
    """Base configuration."""
    # Base Paths
    BASE_DIR = Path(__file__).resolve().parent
    _SWEETNESS_PATHS = get_domain_paths("sweetness")
    METADATA_PATH = _SWEETNESS_PATHS.metadata
    LOG_DIR = BASE_DIR / "logs"
    STATIC_DIR = BASE_DIR / "static"
    TEMPLATE_DIR = BASE_DIR / "frontend"
    
    # Server
    HOST = os.getenv('HOST', '0.0.0.0')
    # 固定默认端口 5001：与 gunicorn/nginx/部署脚本一致，减少多环境端口分叉导致的代理与健康检查失败。
    PORT = int(os.getenv('PORT', 5001))
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # DeepSeek API
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
    DEEPSEEK_BASE_URL = _normalize_openai_base_url(os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1'))
    DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-reasoner')
    
    # RAG Settings
    DATA_DIR = str(_SWEETNESS_PATHS.papers)
    PERSIST_DIR = str(_SWEETNESS_PATHS.index)
    # 索引构建批次大小（降低内存峰值）
    INDEX_BUILD_BATCH_SIZE = int(os.getenv('INDEX_BUILD_BATCH_SIZE', 25))

    EMBED_MODEL_TYPE = os.getenv("EMBED_MODEL_TYPE", "modelscope").lower()
    # Path to local model snapshot or HuggingFace ID
    # 推荐使用 BAAI/bge-small-zh-v1.5 以平衡速度与效果（CPU环境下首选）
    EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "BAAI/bge-small-zh-v1.5")
    # 模型源：huggingface 或 modelscope (推荐国内使用 modelscope)
    EMBED_MODEL_SOURCE = os.getenv("EMBED_MODEL_SOURCE", "modelscope")
    # 可显式指定 cpu/cuda/mps；留空时由 SentenceTransformers 自动选择。
    EMBED_DEVICE = os.getenv("EMBED_DEVICE", "").strip().lower()
    EMBED_BATCH_SIZE = max(1, int(os.getenv("EMBED_BATCH_SIZE", "8")))
    EMBED_NUM_THREADS = max(1, int(os.getenv("EMBED_NUM_THREADS", "1")))
    # 嵌入推理不使用 torch.compile；关闭探测可避免部分 macOS/PyTorch
    # 组合在首次请求时长时间加载 torch._dynamo。
    EMBED_DISABLE_TORCH_DYNAMO = os.getenv("EMBED_DISABLE_TORCH_DYNAMO", "false").lower() in (
        "true", "1", "yes"
    )
    
    COLLECTION_NAME = "sweetseek_papers"
    
    # RAG Retrieval & Generation Settings (Tunable)
    # RAG Top K
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", 5))
    # 相似度阈值：低于此分数的文档块将被过滤 (0-1)
    # 降低阈值以提高召回率
    RAG_SIMILARITY_THRESHOLD = float(os.getenv("RAG_SIMILARITY_THRESHOLD", 0.3))
    # 强制最小文档数：即使分数不足，也至少保留前N个文档 (5 -> 10)
    RAG_FORCE_MIN_DOCS = int(os.getenv('RAG_FORCE_MIN_DOCS', 10))
    # 最大召回数量：从向量库初筛多少个片段 (100 -> 200)
    RAG_MAX_RESULTS = int(os.getenv('RAG_MAX_RESULTS', 200))
    # 上下文窗口限制：喂给 LLM 的最大字符数
    RAG_CONTEXT_WINDOW = int(os.getenv('RAG_CONTEXT_WINDOW', 12000))
    
    # Evidence Ranker Settings
    TOP_JOURNALS = [
        'nature', 'science', 'cell', 'lancet', 
        'new england journal of medicine', 'jama',
        'british medical journal', 'bmj'
    ]
    TIER2_KEYWORDS = [
        'nutrition', 'metabolism', 'diabetes', 'obesity', 
        'clinical', 'american journal', 'european journal'
    ]

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False

# Select config based on environment
config = DevelopmentConfig() if os.getenv('FLASK_ENV') == 'development' else ProductionConfig()

# RAG parameter configs (single source of truth)
sweet_rag_config = RAGConfig.from_env(prefix="SWEET")
dual_rag_config = DualRAGConfig.from_env()
proteoglycan_rag_config = RAGConfig.from_env(prefix="PROTEOGLYCAN")
