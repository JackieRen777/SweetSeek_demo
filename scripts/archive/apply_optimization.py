import pexpect

password = None

# Safe script generation
# We will write the python script to a file on the server line by line to avoid quoting hell
commands = [
    "cd /www/wwwroot/FCN_SweetSeek",
    # 1. Create update_persistent.py
    "cat > update_persistent.py << 'EOF'",
    "from __future__ import annotations",
    "import os",
    "import sys",
    "import logging",
    "from pathlib import Path",
    "from typing import List, Optional",
    "",
    "# LlamaIndex",
    "from llama_index.core import (",
    "    VectorStoreIndex,",
    "    StorageContext,",
    "    SimpleDirectoryReader,",
    "    Settings,",
    "    load_index_from_storage,",
    "    Document",
    ")",
    "from llama_index.embeddings.huggingface import HuggingFaceEmbedding",
    "from llama_index.vector_stores.faiss import FaissVectorStore",
    "import faiss",
    "",
    "# Config",
    "from config import config",
    "",
    "# Logging",
    "logging.basicConfig(level=logging.INFO)",
    "logger = logging.getLogger(__name__)",
    "",
    "class RAGSystem:",
    "    def __init__(self):",
    "        self.index = None",
    "        self.query_engine = None",
    "        self._initialize_system()",
    "",
    "    def _initialize_system(self):",
    "        try:",
    "            logger.info('[System] Initializing RAG System (FAISS + Local Model)...')",
    "            ",
    "            # 1. Setup Embedding Model (Local)",
    "            model_path = config.EMBED_MODEL_NAME",
    "            # Fallback check",
    "            if not os.path.exists(model_path) and '/' not in model_path:",
    "                 local_check = os.path.join(config.BASE_DIR, 'models', model_path.split('/')[-1])",
    "                 if os.path.exists(local_check):",
    "                     model_path = local_check",
    "            ",
    "            logger.info(f'Loading embedding model from: {model_path}')",
    "            embed_model = HuggingFaceEmbedding(",
    "                model_name=model_path,",
    "                trust_remote_code=True",
    "            )",
    "            Settings.embed_model = embed_model",
    "            Settings.llm = None",
    "",
    "            # 2. Setup Vector Store (FAISS)",
    "            persist_dir = os.path.join(config.BASE_DIR, 'faiss_index')",
    "            ",
    "            if os.path.exists(persist_dir) and os.path.exists(os.path.join(persist_dir, 'default__vector_store.json')):",
    "                logger.info('Loading existing FAISS index...')",
    "                vector_store = FaissVectorStore.from_persist_dir(persist_dir)",
    "                storage_context = StorageContext.from_defaults(",
    "                    vector_store=vector_store, persist_dir=persist_dir",
    "                )",
    "                self.index = load_index_from_storage(storage_context=storage_context)",
    "            else:",
    "                logger.info('Creating new FAISS index...')",
    "                d = 512 # BGE-Small-ZH-v1.5 dimension",
    "                faiss_index = faiss.IndexFlatL2(d)",
    "                vector_store = FaissVectorStore(faiss_index=faiss_index)",
    "                storage_context = StorageContext.from_defaults(vector_store=vector_store)",
    "                ",
    "                # Load Documents",
    "                data_dir = config.DATA_DIR",
    "                if not os.path.exists(data_dir):",
    "                    os.makedirs(data_dir, exist_ok=True)",
    "                    logger.warning(f'Data directory {data_dir} created (empty).')",
    "                    documents = []",
    "                else:",
    "                    reader = SimpleDirectoryReader(input_dir=data_dir, recursive=True)",
    "                    documents = reader.load_data()",
    "                    logger.info(f'Loaded {len(documents)} documents.')",
    "",
    "                if documents:",
    "                    self.index = VectorStoreIndex.from_documents(",
    "                        documents, storage_context=storage_context",
    "                    )",
    "                    os.makedirs(persist_dir, exist_ok=True)",
    "                    self.index.storage_context.persist(persist_dir=persist_dir)",
    "                else:",
    "                    self.index = VectorStoreIndex.from_documents(",
    "                        [Document(text='Empty index initialized.')], ",
    "                        storage_context=storage_context",
    "                    )",
    "            ",
    "            # 3. Create Query Engine",
    "            self.query_engine = self.index.as_query_engine(",
    "                similarity_top_k=config.RAG_MAX_RESULTS",
    "            )",
    "            logger.info('RAG System Initialized Successfully.')",
    "",
    "        except Exception as e:",
    "            logger.error(f'RAG Initialization Failed: {e}', exc_info=True)",
    "            self.query_engine = None",
    "",
    "    def query(self, question: str) -> str:",
    "        if not self.query_engine:",
    "            return 'System initializing or failed. Please try again later.'",
    "        response = self.query_engine.query(question)",
    "        return str(response)",
    "",
    "# Global Instance",
    "rag_system = RAGSystem()",
    "EOF",
    
    # 2. Overwrite persistent_storage.py
    "mv update_persistent.py persistent_storage.py",
    
    # 3. Update config.py using sed
    "sed -i 's|EMBED_MODEL_NAME = .*|EMBED_MODEL_NAME = os.getenv(\"EMBED_MODEL_NAME\", str(BASE_DIR / \"models\" / \"bge-small-zh-v1.5\"))|' config.py",
    
    # 4. Restart
    "fuser -k 5001/tcp || true",
    "pkill -f app.py || true",
    "(nohup ./venv_311/bin/python3 app.py > backend.log 2>&1 &)"
]

cmd_str = " && ".join(commands)
full_cmd = f"ssh -o StrictHostKeyChecking=no root@sweetseek.top '{cmd_str}'"

print(f"Applying Updates: {full_cmd}")
child = pexpect.spawn(full_cmd)

try:
    i = child.expect(['password:', pexpect.EOF, pexpect.TIMEOUT], timeout=60)
    if i == 0:
        if not password:
            print("Password is not set; skip interactive login.")
            raise SystemExit(1)
        child.sendline(password)
        child.expect(pexpect.EOF)
        print(child.before.decode())
    else:
        print("Failed")
except Exception as e:
    print(f"Error: {e}")
