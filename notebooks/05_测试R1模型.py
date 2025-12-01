#!/usr/bin/env python3
"""
快速测试 DeepSeek-R1 推理模型
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

def test_r1_simple():
    """简单测试 R1 模型"""
    print("🧪 测试 DeepSeek-R1 推理模型")
    print("=" * 50)
    
    client = OpenAI(
        api_key=os.getenv('DEEPSEEK_API_KEY'),
        base_url="https://api.deepseek.com"
    )
    
    # 简单测试
    print("\n📝 测试问题: 什么是抗氧化剂？")
    print("⏳ R1模型正在思考（可能需要10-30秒）...\n")
    
    response = client.chat.completions.create(
        model="deepseek-reasoner",
        messages=[
            {"role": "user", "content": "用一句话解释什么是抗氧化剂"}
        ],
        max_tokens=500
    )
    
    # 提取推理过程和答案
    content = response.choices[0].message.content
    
    # R1 模型的输出格式：<think>推理过程</think>答案
    if "<think>" in content and "</think>" in content:
        think_start = content.find("<think>") + 7
        think_end = content.find("</think>")
        thinking = content[think_start:think_end].strip()
        answer = content[think_end + 8:].strip()
        
        print("🧠 推理过程:")
        print("-" * 50)
        print(thinking[:200] + "..." if len(thinking) > 200 else thinking)
        print("\n💡 最终答案:")
        print("-" * 50)
        print(answer)
    else:
        print("🤖 回答:")
        print(content)
    
    print("\n" + "=" * 50)
    print("✅ R1 模型测试完成！")
    print("\n💡 R1 模型特点:")
    print("- 会展示推理过程（<think>标签内）")
    print("- 推理更深入，但速度较慢")
    print("- 适合复杂的科研分析")

if __name__ == "__main__":
    test_r1_simple()