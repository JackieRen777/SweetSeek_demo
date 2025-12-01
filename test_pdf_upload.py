#!/usr/bin/env python3
"""
测试PDF上传和向量化
演示如何处理不同格式的文献
"""

import os
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

def test_document_reading():
    """测试文档读取"""
    print("=" * 60)
    print("📄 测试文档读取功能")
    print("=" * 60)
    
    # 配置嵌入模型
    Settings.embed_model = HuggingFaceEmbedding(
        model_name="BAAI/bge-small-zh-v1.5",
        cache_folder="./models"
    )
    
    # 读取所有文档
    print("\n[1] 读取 food_research_data 目录...")
    try:
        documents = SimpleDirectoryReader(
            "food_research_data",
            recursive=True
        ).load_data()
        
        print(f"✅ 成功读取 {len(documents)} 个文档\n")
        
        # 显示每个文档的详细信息
        for i, doc in enumerate(documents, 1):
            filename = doc.metadata.get('file_name', '未知文件')
            file_path = doc.metadata.get('file_path', '')
            file_type = os.path.splitext(filename)[1]
            content_length = len(doc.text)
            
            print(f"文档 {i}:")
            print(f"  📁 文件名: {filename}")
            print(f"  📂 路径: {file_path}")
            print(f"  📝 格式: {file_type}")
            print(f"  📊 内容长度: {content_length} 字符")
            print(f"  📖 前150字预览:")
            print(f"     {doc.text[:150].replace(chr(10), ' ')}...")
            print()
        
        return documents
        
    except Exception as e:
        print(f"❌ 读取失败: {e}")
        return None

def test_vectorization(documents):
    """测试向量化"""
    print("=" * 60)
    print("🔄 测试向量化功能")
    print("=" * 60)
    
    if not documents:
        print("❌ 没有文档可以向量化")
        return None
    
    try:
        print("\n[2] 开始向量化...")
        print("⏳ 这可能需要几秒到几分钟，取决于文档数量...")
        
        # 构建向量索引
        index = VectorStoreIndex.from_documents(documents)
        
        print("✅ 向量化完成！")
        
        # 获取向量存储信息
        vector_store = index.storage_context.vector_store
        print(f"\n📊 向量数据库统计:")
        print(f"  - 文档数: {len(documents)}")
        print(f"  - 向量维度: 512 (bge-small-zh-v1.5)")
        
        return index
        
    except Exception as e:
        print(f"❌ 向量化失败: {e}")
        return None

def test_query(index):
    """测试查询"""
    print("\n" + "=" * 60)
    print("🔍 测试查询功能")
    print("=" * 60)
    
    if not index:
        print("❌ 索引未创建，无法查询")
        return
    
    # 创建查询引擎
    query_engine = index.as_query_engine(
        similarity_top_k=3,
        response_mode="compact"
    )
    
    # 测试查询
    test_questions = [
        "这些文献主要研究什么内容？",
        "有关于食品安全的内容吗？",
        "抗氧化剂有什么作用？"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n[问题 {i}] {question}")
        print("-" * 60)
        
        try:
            # 只检索，不生成答案（因为没有配置LLM）
            retriever = index.as_retriever(similarity_top_k=3)
            nodes = retriever.retrieve(question)
            
            print(f"✅ 找到 {len(nodes)} 个相关文档片段:\n")
            
            for j, node in enumerate(nodes, 1):
                score = node.score if hasattr(node, 'score') else 0.0
                filename = node.metadata.get('file_name', '未知')
                content = node.text[:200].replace('\n', ' ')
                
                print(f"  [{j}] 相关度: {score:.3f}")
                print(f"      来源: {filename}")
                print(f"      内容: {content}...")
                print()
                
        except Exception as e:
            print(f"❌ 查询失败: {e}")

def test_supported_formats():
    """测试支持的文件格式"""
    print("\n" + "=" * 60)
    print("📋 支持的文件格式")
    print("=" * 60)
    
    supported_formats = {
        "文本文件": [".txt", ".md", ".rst"],
        "文档文件": [".pdf", ".doc", ".docx"],
        "数据文件": [".csv", ".json", ".jsonl"],
        "代码文件": [".py", ".js", ".java", ".cpp"],
        "网页文件": [".html", ".htm"]
    }
    
    print("\nLlamaIndex 自动支持以下格式:\n")
    for category, formats in supported_formats.items():
        print(f"  {category}:")
        for fmt in formats:
            print(f"    ✅ {fmt}")
    
    print("\n💡 提示:")
    print("  - PDF文件会自动提取文本")
    print("  - Word文件需要安装: pip install python-docx")
    print("  - 扫描版PDF需要OCR: pip install pytesseract")

def show_upload_instructions():
    """显示上传说明"""
    print("\n" + "=" * 60)
    print("📤 如何上传新文献")
    print("=" * 60)
    
    print("""
方法1: 直接复制文件
    cp your_paper.pdf food_research_data/papers/
    python app.py

方法2: Web界面上传
    python app.py
    访问: http://localhost:5001/upload.html
    
方法3: 批量上传
    cp *.pdf food_research_data/papers/
    python app.py

📁 目录结构:
    food_research_data/
    ├── papers/      ← 研究论文放这里
    └── datasets/    ← 数据集放这里
    """)

def main():
    """主函数"""
    print("\n" + "🚀 " * 20)
    print("PDF上传和向量化测试工具")
    print("🚀 " * 20 + "\n")
    
    # 检查目录
    if not os.path.exists("food_research_data"):
        print("❌ 找不到 food_research_data 目录")
        print("💡 请先创建目录: mkdir -p food_research_data/papers food_research_data/datasets")
        return
    
    # 测试1: 读取文档
    documents = test_document_reading()
    
    if not documents:
        print("\n⚠️  没有找到文档，请先上传文献")
        show_upload_instructions()
        return
    
    # 测试2: 向量化
    index = test_vectorization(documents)
    
    # 测试3: 查询
    if index:
        test_query(index)
    
    # 显示支持的格式
    test_supported_formats()
    
    # 显示上传说明
    show_upload_instructions()
    
    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)
    print("\n💡 下一步:")
    print("  1. 上传更多PDF文献到 food_research_data/papers/")
    print("  2. 运行 python app.py 启动完整系统")
    print("  3. 访问 http://localhost:5001 开始使用\n")

if __name__ == "__main__":
    main()
