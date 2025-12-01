#!/usr/bin/env python3
"""
第一个食品AI科研问答系统
这是一个完整的RAG系统示例，专门为食品科学研究设计
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def check_environment():
    """检查环境配置"""
    print("🔍 检查环境配置...")
    
    # 检查DeepSeek API密钥
    deepseek_key = os.getenv('DEEPSEEK_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')
    
    if deepseek_key and deepseek_key != "your_deepseek_api_key_here":
        print("✅ DeepSeek API密钥已配置")
        print("🚀 使用DeepSeek API (高性价比选择)")
    elif openai_key and openai_key != "your_openai_api_key_here":
        print("✅ OpenAI API密钥已配置")
        print("🚀 使用OpenAI API")
    else:
        print("❌ 请在.env文件中配置API密钥")
        print("💡 DeepSeek API: https://platform.deepseek.com/")
        print("💡 OpenAI API: https://platform.openai.com/api-keys")
        return False
    
    # 检查数据目录
    data_dir = "food_research_data"
    if not os.path.exists(data_dir):
        print(f"❌ 数据目录不存在: {data_dir}")
        return False
    
    # 检查是否有文档
    has_files = False
    for root, dirs, files in os.walk(data_dir):
        if files:
            has_files = True
            break
    
    if not has_files:
        print("⚠️  数据目录为空，请添加一些食品科研文档")
        print("💡 支持的格式: .txt, .pdf, .docx, .md")
        # 创建示例文档
        create_sample_documents()
    else:
        print("✅ 找到研究文档")
    
    return True

def create_sample_documents():
    """创建示例食品科学文档"""
    print("📝 创建示例食品科学文档...")
    
    sample_docs = {
        "food_research_data/papers/抗氧化剂研究.txt": """
# 食品中的抗氧化剂研究

## 概述
抗氧化剂是能够防止或延缓食品氧化的物质，在食品保鲜和营养保持中起重要作用。

## 主要类型

### 天然抗氧化剂
1. **维生素E (生育酚)**
   - 脂溶性抗氧化剂
   - 主要存在于植物油、坚果中
   - 能有效防止脂质过氧化

2. **维生素C (抗坏血酸)**
   - 水溶性抗氧化剂
   - 广泛存在于新鲜水果蔬菜中
   - 能清除自由基，防止褐变

3. **多酚类化合物**
   - 包括花青素、儿茶素、槲皮素等
   - 存在于茶叶、红酒、浆果中
   - 具有强抗氧化活性

### 合成抗氧化剂
1. **BHT (丁基羟基甲苯)**
   - 常用于油脂食品
   - 热稳定性好

2. **BHA (丁基羟基茴香醚)**
   - 适用于动物脂肪
   - 在酸性条件下稳定

## 应用原理
抗氧化剂通过以下机制发挥作用：
- 清除自由基
- 螯合金属离子
- 再生其他抗氧化剂
- 阻断氧化链反应

## 在食品工业中的应用
- 延长食品保质期
- 保持食品营养价值
- 防止食品变色变味
- 提高食品安全性

## 发展趋势
目前研究重点转向天然抗氧化剂的开发和应用，以满足消费者对天然、健康食品的需求。
        """,
        
        "food_research_data/papers/食品安全检测.txt": """
# 食品安全检测技术研究

## 引言
食品安全检测是保障公众健康的重要手段，涉及化学污染物、微生物、添加剂等多个方面的检测。

## 主要检测项目

### 化学污染物检测
1. **重金属检测**
   - 铅、汞、镉、砷等
   - 检测方法：原子吸收光谱法、ICP-MS

2. **农药残留检测**
   - 有机磷、有机氯、氨基甲酸酯类
   - 检测方法：气相色谱法、液相色谱法

3. **兽药残留检测**
   - 抗生素、激素类药物
   - 检测方法：ELISA、LC-MS/MS

### 微生物检测
1. **致病菌检测**
   - 沙门氏菌、大肠杆菌、李斯特菌
   - 检测方法：培养法、PCR法、免疫法

2. **霉菌毒素检测**
   - 黄曲霉毒素、呕吐毒素、玉米赤霉烯酮
   - 检测方法：HPLC、免疫亲和柱法

### 食品添加剂检测
1. **防腐剂检测**
   - 苯甲酸、山梨酸、丙酸等
   - 检测方法：HPLC法

2. **甜味剂检测**
   - 糖精、安赛蜜、阿斯巴甜
   - 检测方法：HPLC法、离子色谱法

## 快速检测技术
1. **免疫层析技术**
   - 操作简便，结果快速
   - 适用于现场检测

2. **生物传感器技术**
   - 高灵敏度、高特异性
   - 可实现实时监测

3. **拉曼光谱技术**
   - 无损检测
   - 可检测多种成分

## 发展趋势
- 检测技术向快速、准确、便携方向发展
- 多技术融合，提高检测效率
- 建立完善的食品安全追溯体系
        """,
        
        "food_research_data/datasets/营养成分数据.txt": """
# 常见食品营养成分数据

## 谷物类 (每100g)
### 大米
- 能量: 346 kcal
- 蛋白质: 7.4 g
- 脂肪: 0.8 g
- 碳水化合物: 77.9 g
- 膳食纤维: 0.7 g

### 小麦粉
- 能量: 366 kcal
- 蛋白质: 11.2 g
- 脂肪: 1.3 g
- 碳水化合物: 75.0 g
- 膳食纤维: 2.8 g

## 蔬菜类 (每100g)
### 菠菜
- 能量: 28 kcal
- 蛋白质: 2.6 g
- 脂肪: 0.3 g
- 碳水化合物: 4.5 g
- 维生素C: 32 mg
- 铁: 2.9 mg

### 胡萝卜
- 能量: 25 kcal
- 蛋白质: 1.0 g
- 脂肪: 0.2 g
- 碳水化合物: 6.0 g
- 胡萝卜素: 4010 μg

## 水果类 (每100g)
### 苹果
- 能量: 54 kcal
- 蛋白质: 0.2 g
- 脂肪: 0.2 g
- 碳水化合物: 13.5 g
- 维生素C: 4 mg

### 橙子
- 能量: 48 kcal
- 蛋白质: 0.8 g
- 脂肪: 0.2 g
- 碳水化合物: 11.1 g
- 维生素C: 33 mg

## 肉类 (每100g)
### 猪肉(瘦)
- 能量: 143 kcal
- 蛋白质: 20.3 g
- 脂肪: 6.2 g
- 铁: 3.0 mg
- 锌: 2.11 mg

### 鸡胸肉
- 能量: 133 kcal
- 蛋白质: 19.4 g
- 脂肪: 5.0 g
- 维生素B6: 0.6 mg
        """
    }
    
    for filepath, content in sample_docs.items():
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 创建: {filepath}")

def build_rag_system():
    """构建RAG系统"""
    print("\n🔨 构建食品AI科研问答系统...")
    
    try:
        # 导入必要的库
        from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
        from llama_index.core import Settings
        from llama_index.llms.openai import OpenAI
        from llama_index.embeddings.openai import OpenAIEmbedding
        
        print("✅ 成功导入LlamaIndex库")
        
        # 检查使用哪个API
        deepseek_key = os.getenv('DEEPSEEK_API_KEY')
        openai_key = os.getenv('OPENAI_API_KEY')
        
        if deepseek_key and deepseek_key != "your_deepseek_api_key_here":
            # 使用DeepSeek API
            print("🚀 配置DeepSeek API...")
            Settings.llm = OpenAI(
                model="gpt-3.5-turbo",  # 使用兼容的模型名
                api_key=deepseek_key,
                api_base="https://api.deepseek.com/v1",  # 添加/v1路径
                temperature=0.1,
                is_chat_model=True,
                system_prompt="""你是一个专业的食品科学研究助手。请基于提供的文档内容回答问题，
                如果文档中没有相关信息，请明确说明。回答要准确、专业，并且易于理解。"""
            )
            
            # 使用本地中文嵌入模型（免费且高质量）
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
            print("📥 加载本地中文嵌入模型（首次运行会下载，约400MB）...")
            Settings.embed_model = HuggingFaceEmbedding(
                model_name="BAAI/bge-small-zh-v1.5",  # 中文优化的嵌入模型
                cache_folder="./models"  # 模型缓存目录
            )
            print("✅ 配置DeepSeek LLM + 本地中文嵌入模型")
            
        elif openai_key and openai_key != "your_openai_api_key_here":
            # 使用OpenAI API
            print("🚀 配置OpenAI API...")
            Settings.llm = OpenAI(
                model="gpt-3.5-turbo",
                temperature=0.1,
                system_prompt="""你是一个专业的食品科学研究助手。请基于提供的文档内容回答问题，
                如果文档中没有相关信息，请明确说明。回答要准确、专业，并且易于理解。"""
            )
            
            Settings.embed_model = OpenAIEmbedding(
                model="text-embedding-ada-002"
            )
            print("✅ 配置OpenAI LLM和嵌入模型")
        else:
            print("❌ 未找到有效的API密钥")
            return None
        
        # 加载文档
        print("📚 加载食品科研文档...")
        documents = SimpleDirectoryReader(
            "food_research_data",
            recursive=True
        ).load_data()
        
        print(f"✅ 成功加载 {len(documents)} 个文档")
        
        # 构建向量索引
        print("🔍 构建向量索引...")
        index = VectorStoreIndex.from_documents(documents)
        print("✅ 向量索引构建完成")
        
        # 创建查询引擎
        query_engine = index.as_query_engine(
            similarity_top_k=3,  # 返回最相关的3个文档片段
            response_mode="compact"  # 紧凑的回答模式
        )
        print("✅ 查询引擎创建完成")
        
        return query_engine
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("💡 请确保已安装llama-index: pip install llama-index")
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
        "苹果和橙子的营养成分有什么区别？",
        "什么是维生素E？它在食品中的作用是什么？",
        "食品安全检测的发展趋势是什么？"
    ]
    
    print("📝 测试问题:")
    for i, question in enumerate(test_questions, 1):
        print(f"{i}. {question}")
    
    print("\n" + "="*60)
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n🤔 问题 {i}: {question}")
        print("-" * 40)
        
        try:
            response = query_engine.query(question)
            print(f"🤖 回答: {response}")
            
            # 显示相关文档来源
            if hasattr(response, 'source_nodes') and response.source_nodes:
                print("\n📚 参考文档:")
                for j, node in enumerate(response.source_nodes, 1):
                    filename = node.metadata.get('file_name', '未知文档')
                    print(f"   {j}. {filename}")
            
        except Exception as e:
            print(f"❌ 查询失败: {e}")
        
        print("\n" + "="*60)

def main():
    """主函数"""
    print("🍎 食品AI科研问答系统启动")
    print("="*50)
    
    # 检查环境
    if not check_environment():
        return
    
    # 构建RAG系统
    query_engine = build_rag_system()
    if not query_engine:
        return
    
    # 测试系统
    test_rag_system(query_engine)
    
    print("\n🎉 系统测试完成！")
    print("\n💡 接下来你可以:")
    print("1. 添加更多食品科研文档到 food_research_data/ 目录")
    print("2. 在Jupyter notebook中交互式使用这个系统")
    print("3. 根据你的研究需求定制查询和回答")
    print("4. 尝试不同的查询策略和参数优化")

if __name__ == "__main__":
    main()