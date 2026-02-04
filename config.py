import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
    DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
    DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
    
    # RAG Settings
    DATA_DIR = os.getenv('DATA_DIR', str(BASE_DIR / "sweet_related_paper"))
    PERSIST_DIR = os.getenv('PERSIST_DIR', str(CHROMA_DB_DIR))

    EMBED_MODEL_TYPE = os.getenv("EMBED_MODEL_TYPE", "huggingface").lower()
    EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "BAAI/bge-small-zh-v1.5")
    COLLECTION_NAME = "sweetseek_papers"
    
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
