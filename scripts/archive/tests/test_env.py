
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('DEEPSEEK_API_KEY')
print(f"API Key found: {api_key is not None}")
if api_key:
    print(f"Key length: {len(api_key)}")
    print(f"First 5 chars: {api_key[:5]}")
