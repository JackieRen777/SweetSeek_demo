
import os
import sys
import logging
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

logging.basicConfig(level=logging.INFO)

model_path = "/www/wwwroot/FCN_SweetSeek/models/AI-ModelScope/bge-small-en-v1___5"
print(f"Checking path: {model_path}")
if not os.path.exists(model_path):
    print("Path does not exist!")
    sys.exit(1)

print("Path exists. Attempting to load model...")

try:
    embed_model = HuggingFaceEmbedding(
        model_name=model_path,
        trust_remote_code=False,
        device='cpu'
    )
    print("Model loaded successfully!")
except Exception as e:
    print(f"Failed to load model: {e}")
    import traceback
    traceback.print_exc()
