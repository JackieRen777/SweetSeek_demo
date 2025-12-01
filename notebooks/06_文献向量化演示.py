#!/usr/bin/env python3
"""
文献向量化过程演示
展示LlamaIndex如何处理和向量化文档
"""

import os
from dotenv import load_dotenv

load_dotenv()

def demo_document_loading():
    """演示文档加载"""
    print("=" * 60)
    print("步骤1：文档加载")
    print("=" * 60)
    
    from llama_index.core import SimpleDirectoryReader
    
    # 加载文档
    documents = SimpleDirectoryReader(
        "food_research_data",
        recursive=True
    ).load_data()
    
    print(f"\n加载的文档数量: {len(documents)}")
    
    for i, doc in enumerate(documents, 1):
        print(f"\n文档 {i}:")
        print(f"  文件名: {doc.metadata.get('file_name', '未知')}")
        print(f"  文件路径: {doc.metadata.get('file_path', '未知')}")
        print(f"  内容长度: {len(doc.text)} 字符")
        print(f"  内容预览: {doc.text[:100]}...")
    
    return documents

def demo_text_chunking(documents):
    """演示文本分块"""
    print("\n" + "=" * 60)
    print("步骤2：文本分块")
    print("=" * 60)
    
    from llama_index.core.node_parser import SimpleNodeParser
    
    # 创建分块器
    parser = SimpleNodeParser.from_defaults(
        chunk_size=512,      # 每块512个token
        chunk_overlap=50     # 重叠50个token
    )
    
    # 分块
    nodes = parser.get_nodes_from_documents(documents)
    
    print(f"\n原始文档数: {len(documents)}")
    print(f"分块后节点数: {len(nodes)}")
    print(f"平均每个文档分成: {len(nodes) / len(documents):.1f} 块")
    
    # 显示第一个节点的详细信息
    if nodes:
        node = nodes[0]
        print(f"\n第一个节点示例:")
        print(f"  来源文档: {node.metadata.get('file_name', '未知')}")
        print(f"  文本长度: {len(node.text)} 字符")
        print(f"  文本内容: {node.text[:200]}...")
    
    return nodes

def demo_embedding(nodes):
    """演示向量嵌入"""
    print("\n" + "=" * 60)
    print("步骤3：向量嵌入")
    print("=" * 60)
    
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    
    # 创建嵌入模型
    print("\n加载嵌入模型...")
    embed_model = HuggingFaceEmbedding(
        model_name="BAAI/bge-small-zh-v1.5",
        cache_folder="./models"
    )
    print("嵌入模型加载完成")
    
    # 对第一个节点进行嵌入
    if nodes:
        node = nodes[0]
        print(f"\n对第一个节点进行嵌入...")
        print(f"文本: {node.text[:100]}...")
        
        embedding = embed_model.get_text_embedding(node.text)
        
        print(f"\n嵌入结果:")
        print(f"  向量维度: {len(embedding)}")
        print(f"  向量类型: {type(embedding)}")
        print(f"  向量示例 (前10维): {embedding[:10]}")
        print(f"  向量范围: [{min(embedding):.4f}, {max(embedding):.4f}]")
    
    return embed_model

def demo_index_building(documents):
    """演示索引构建"""
    print("\n" + "=" * 60)
    print("步骤4：构建向量索引")
    print("=" * 60)
    
    from llama_index.core import VectorStoreIndex, Settings
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    
    # 配置嵌入模型
    Settings.embed_model = HuggingFaceEmbedding(
        model_name="BAAI/bge-small-zh-v1.5",
        cache_folder="./models"
    )
    
    print("\n构建向量索引...")
    print("这个过程会：")
    print("  1. 自动分块文档")
    print("  2. 对每个块进行向量嵌入")
    print("  3. 存储向量到内存数据库")
    print("  4. 创建检索索引")
    
    # 构建索引
    index = VectorStoreIndex.from_documents(documents)
    
    print("\n索引构建完成！")
    print(f"索引类型: {type(index)}")
    
    return index

def demo_similarity_search(index):
    """演示相似度搜索"""
    print("\n" + "=" * 60)
    print("步骤5：相似度搜索演示")
    print("=" * 60)
    
    # 创建检索器
    retriever = index.as_retriever(similarity_top_k=3)
    
    # 测试查询
    query = "抗氧化剂"
    print(f"\n查询: {query}")
    print("正在检索最相关的文档块...")
    
    # 检索
    nodes = retriever.retrieve(query)
    
    print(f"\n找到 {len(nodes)} 个相关结果:")
    
    for i, node in enumerate(nodes, 1):
        print(f"\n结果 {i}:")
        print(f"  相似度分数: {node.score:.4f}")
        print(f"  来源文档: {node.metadata.get('file_name', '未知')}")
        print(f"  文本内容: {node.text[:150]}...")

def demo_vector_comparison():
    """演示向量相似度计算"""
    print("\n" + "=" * 60)
    print("补充：向量相似度计算原理")
    print("=" * 60)
    
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    import numpy as np
    
    # 创建嵌入模型
    embed_model = HuggingFaceEmbedding(
        model_name="BAAI/bge-small-zh-v1.5",
        cache_folder="./models"
    )
    
    # 三个文本
    texts = [
        "维生素E是脂溶性抗氧化剂",
        "维生素C是水溶性抗氧化剂",
        "食品安全检测很重要"
    ]
    
    print("\n计算三个文本的向量相似度:")
    for text in texts:
        print(f"  - {text}")
    
    # 获取向量
    embeddings = [embed_model.get_text_embedding(text) for text in texts]
    
    # 计算余弦相似度
    def cosine_similarity(v1, v2):
        return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    
    print("\n相似度矩阵:")
    print("        文本1   文本2   文本3")
    for i, text1 in enumerate(texts):
        print(f"文本{i+1}  ", end="")
        for j, text2 in enumerate(texts):
            sim = cosine_similarity(embeddings[i], embeddings[j])
            print(f"{sim:.3f}  ", end="")
        print()
    
    print("\n解读:")
    print("  - 对角线都是1.000 (自己和自己完全相似)")
    print("  - 文本1和文本2相似度高 (都是关于抗氧化剂)")
    print("  - 文本3和前两个相似度低 (主题不同)")

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("LlamaIndex 文献向量化完整演示")
    print("=" * 60)
    
    try:
        # 步骤1：加载文档
        documents = demo_document_loading()
        
        # 步骤2：文本分块
        nodes = demo_text_chunking(documents)
        
        # 步骤3：向量嵌入
        embed_model = demo_embedding(nodes)
        
        # 步骤4：构建索引
        index = demo_index_building(documents)
        
        # 步骤5：相似度搜索
        demo_similarity_search(index)
        
        # 补充：向量相似度
        demo_vector_comparison()
        
        print("\n" + "=" * 60)
        print("演示完成！")
        print("=" * 60)
        
        print("\n关键要点:")
        print("1. 文档被自动分块成小段")
        print("2. 每个小段被转换成512维向量")
        print("3. 向量存储在内存数据库中")
        print("4. 查询时通过向量相似度找到最相关的内容")
        print("5. 相似的文本有相似的向量")
        
    except Exception as e:
        print(f"\n错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
