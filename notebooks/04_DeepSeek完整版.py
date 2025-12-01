#!/usr/bin/env python3
"""
DeepSeek + 本地嵌入模型 - 完整RAG系统
使用原生OpenAI客户端调用DeepSeek API
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

# 加载环境变量
load_dotenv()

def test_deepseek_api():
    """测试DeepSeek API连接"""
    print("🧪 测试DeepSeek API连接...")
    
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        print("❌ 未找到DEEPSEEK_API_KEY")
        return False
    
    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        
        response = client.chat.completions.create(
            model="deepseek-reasoner",  # DeepSeek-R1 推理模型
            messages=[
                {"role": "system", "content": "你是一个食品科学助手"},
                {"role": "user", "content": "简单介绍一下抗氧化剂"}
            ],
            max_tokens=100
        )
        
        print("✅ DeepSeek API连接成功！")
        print(f"📝 测试回答: {response.choices[0].message.content[:100]}...")
        return True
        
    except Exception as e:
        print(f"❌ DeepSeek API测试失败: {e}")
        return False

def build_rag_with_deepseek():
    """使用DeepSeek构建RAG系统"""
    print("\n🔨 构建DeepSeek RAG系统...")
    
    try:
        from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        from llama_index.llms.openai_like import OpenAILike
        
        print("✅ 导入LlamaIndex库成功")
        
        # 配置DeepSeek-R1 推理模型
        print("🚀 配置DeepSeek-R1 推理模型...")
        Settings.llm = OpenAILike(
            model="deepseek-reasoner",  # DeepSeek-R1 推理模型
            api_key=os.getenv('DEEPSEEK_API_KEY'),
            api_base="https://api.deepseek.com",
            is_chat_model=True,
            temperature=0.1,
            max_tokens=2000  # R1模型需要更多tokens用于推理过程
        )
        print("✅ DeepSeek-R1 推理模型配置完成")
        
        # 配置本地嵌入模型
        print("📥 加载本地中文嵌入模型...")
        Settings.embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-small-zh-v1.5",
            cache_folder="./models"
        )
        print("✅ 本地嵌入模型加载完成")
        
        # 加载文档
        print("📚 加载食品科研文档...")
        documents = SimpleDirectoryReader(
            "food_research_data",
            recursive=True
        ).load_data()
        print(f"✅ 成功加载 {len(documents)} 个文档")
        
        # 构建索引
        print("🔍 构建向量索引...")
        index = VectorStoreIndex.from_documents(documents)
        print("✅ 向量索引构建完成")
        
        # 创建查询引擎
        query_engine = index.as_query_engine(
            similarity_top_k=3,
            response_mode="compact"
        )
        print("✅ 查询引擎创建完成")
        
        return query_engine
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("💡 请安装: pip install llama-index-llms-openai-like")
        return None
    except Exception as e:
        print(f"❌ 构建失败: {e}")
        return None

def test_rag_system(query_engine):
    """测试RAG系统"""
    print("\n🧪 测试食品AI科研问答系统...")
    
    test_questions = [
        "食品中有哪些主要的天然抗氧化剂？",
        "食品安全检测主要检测哪些项目？",
        "苹果和橙子的营养成分有什么区别？"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{'='*60}")
        print(f"🤔 问题 {i}: {question}")
        print("-" * 40)
        
        try:
            response = query_engine.query(question)
            print(f"🤖 回答: {response}")
            
            if hasattr(response, 'source_nodes') and response.source_nodes:
                print("\n📚 参考文档:")
                for j, node in enumerate(response.source_nodes, 1):
                    filename = node.metadata.get('file_name', '未知文档')
                    print(f"   {j}. {filename}")
                    
        except Exception as e:
            print(f"❌ 查询失败: {e}")
        
        print("=" * 60)

def main():
    """主函数"""
    print("🍎 DeepSeek + 本地嵌入 RAG系统")
    print("=" * 50)
    
    # 测试DeepSeek API
    if not test_deepseek_api():
        print("\n❌ DeepSeek API测试失败，请检查配置")
        return
    
    # 构建RAG系统
    query_engine = build_rag_with_deepseek()
    if not query_engine:
        return
    
    # 测试系统
    test_rag_system(query_engine)
    
    print("\n🎉 系统测试完成！")

if __name__ == "__main__":
    main()