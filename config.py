import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def _normalize_openai_base_url(url: str) -> str:
    cleaned = (url or "").strip().rstrip("/")
    if not cleaned:
        return "https://api.deepseek.com/v1"
    return cleaned if cleaned.endswith("/v1") else f"{cleaned}/v1"


class Config:
    """Base configuration."""
    # Base Paths
    BASE_DIR = Path(__file__).resolve().parent
    CHROMA_DB_DIR = BASE_DIR / "chroma_db"
    LOG_DIR = BASE_DIR / "logs"
    STATIC_DIR = BASE_DIR / "static"
    TEMPLATE_DIR = BASE_DIR / "frontend"
    
    # Server
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5001))
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # DeepSeek API
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
    DEEPSEEK_BASE_URL = _normalize_openai_base_url(os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1'))
    DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-reasoner')
    
    # RAG Settings
    DATA_DIR = os.getenv('DATA_DIR', str(BASE_DIR / "sweet_related_paper"))
    PERSIST_DIR = os.getenv('PERSIST_DIR', str(CHROMA_DB_DIR))

    EMBED_MODEL_TYPE = os.getenv("EMBED_MODEL_TYPE", "huggingface").lower()
    EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "BAAI/bge-small-zh-v1.5")
    COLLECTION_NAME = "sweetseek_papers"
    
    # RAG Retrieval & Generation Settings (Tunable)
    # 相似度阈值：低于此分数的文档块将被过滤 (0-1)
    RAG_SIMILARITY_THRESHOLD = float(os.getenv('RAG_SIMILARITY_THRESHOLD', 0.35))
    # 强制最小文档数：即使分数不足，也至少保留前N个文档
    RAG_FORCE_MIN_DOCS = int(os.getenv('RAG_FORCE_MIN_DOCS', 3))
    # 最大召回数量：从向量库初筛多少个片段
    RAG_MAX_RESULTS = int(os.getenv('RAG_MAX_RESULTS', 100))
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
