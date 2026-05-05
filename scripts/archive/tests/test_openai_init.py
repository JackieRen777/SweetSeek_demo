
import os
import sys
try:
    from openai import OpenAI
    print(f"OpenAI imported from: {sys.modules['openai'].__file__}")
    client = OpenAI(api_key="test", base_url="http://test")
    print("Success")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
