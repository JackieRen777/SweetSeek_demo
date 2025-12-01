#!/usr/bin/env python3
"""
外部数据库集成示例
演示如何连接Chroma、Pinecone、Qdrant等向量数据库
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================
# 方案1: Chroma 向量数据库（推荐，免费本地）
# ============================================
def demo_chroma():
    """使用Chroma向量数据库"""
    print("=" * 60)
    print("方案1: Chroma 向量数据库（本地免费）")
    print("=" * 60)
    
    try:
        # 安装: pip install chromadb
        import chromadb
        from llama_index.vector_stores.chroma import ChromaVectorStore
        from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        from llama_index.core import Settings
        
        # 配置嵌入模型
        Settings.embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-small-zh-v1.5",
            cache_folder="./models"
        )
        
        # 创建Chroma客户端（持久化到本地）
        chroma_client = chromadb.PersistentClient(path="./chroma_db")
        
        # 创建或获取集合
        collection_name = "food_research"
        try:
            chroma_collection = chroma_client.create_collection(collection_name)
            print(f"✅ 创建新集合: {collection_name}")
        except:
            chroma_collection = chroma_client.get_collection(collection_name)
            print(f"✅ 加载已有集合: {collection_name}")
        
        # 创建向量存储
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        # 检查是否已有数据
        if chroma_collection.count() == 0:
            print("📄 加载文档...")
            documents = SimpleDirectoryReader("food_research_data").load_data()
            print(f"📊 读取了 {len(documents)} 个文档")
            
            # 构建索引（数据存储在Chroma中）
            index = VectorStoreIndex.from_documents(
                documents,
                storage_context=storage_context
            )
            print(f"✅ 成功将文档存储到 Chroma 数据库")
        else:
            print(f"✅ 数据库已有 {chroma_collection.count()} 条记录")
            # 从已有数据加载索引
            index = VectorStoreIndex.from_vector_store(
                vector_store,
                storage_context=storage_context
            )
        
        # 查询测试
        query_engine = index.as_query_engine()
        response = query_engine.query("什么是抗氧化剂？")
        print(f"\n🔍 查询结果: {str(response)[:200]}...\n")
        
        print("💡 优点:")
        print("  - 完全免费，本地运行")
        print("  - 数据持久化，重启不丢失")
        print("  - 支持增量更新")
        print("  - 安装简单: pip install chromadb")
        
        return index
        
    except ImportError:
        print("❌ 需要安装: pip install chromadb")
        return None
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None


# ============================================
# 方案2: Qdrant 向量数据库（推荐，功能强大）
# ============================================
def demo_qdrant():
    """使用Qdrant向量数据库"""
    print("\n" + "=" * 60)
    print("方案2: Qdrant 向量数据库（本地/云端）")
    print("=" * 60)
    
    try:
        # 安装: pip install qdrant-client
        from qdrant_client import QdrantClient
        from llama_index.vector_stores.qdrant import QdrantVectorStore
        from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        from llama_index.core import Settings
        
        # 配置嵌入模型
        Settings.embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-small-zh-v1.5",
            cache_folder="./models"
        )
        
        # 创建Qdrant客户端（本地模式）
        client = QdrantClient(path="./qdrant_db")
        
        collection_name = "food_research"
        
        # 创建向量存储
        vector_store = QdrantVectorStore(
            client=client,
            collection_name=collection_name
        )
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        # 检查集合是否存在
        collections = [c.name for c in client.get_collections().collections]
        
        if collection_name not in collections:
            print("📄 加载文档...")
            documents = SimpleDirectoryReader("food_research_data").load_data()
            print(f"📊 读取了 {len(documents)} 个文档")
            
            # 构建索引
            index = VectorStoreIndex.from_documents(
                documents,
                storage_context=storage_context
            )
            print(f"✅ 成功将文档存储到 Qdrant 数据库")
        else:
            print(f"✅ 集合已存在，加载索引...")
            index = VectorStoreIndex.from_vector_store(
                vector_store,
                storage_context=storage_context
            )
        
        # 查询测试
        query_engine = index.as_query_engine()
        response = query_engine.query("食品添加剂有哪些类型？")
        print(f"\n🔍 查询结果: {str(response)[:200]}...\n")
        
        print("💡 优点:")
        print("  - 性能优秀，支持大规模数据")
        print("  - 支持过滤和混合搜索")
        print("  - 可本地运行或使用云服务")
        print("  - 安装: pip install qdrant-client")
        
        return index
        
    except ImportError:
        print("❌ 需要安装: pip install qdrant-client")
        return None
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None


# ============================================
# 方案3: Pinecone 云向量数据库
# ============================================
def demo_pinecone():
    """使用Pinecone向量数据库"""
    print("\n" + "=" * 60)
    print("方案3: Pinecone 向量数据库（云端，需要API Key）")
    print("=" * 60)
    
    api_key = os.getenv('PINECONE_API_KEY')
    if not api_key:
        print("❌ 需要设置 PINECONE_API_KEY 环境变量")
        print("💡 注册地址: https://www.pinecone.io/")
        return None
    
    try:
        # 安装: pip install pinecone-client
        from pinecone import Pinecone, ServerlessSpec
        from llama_index.vector_stores.pinecone import PineconeVectorStore
        from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        from llama_index.core import Settings
        
        # 配置嵌入模型
        Settings.embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-small-zh-v1.5",
            cache_folder="./models"
        )
        
        # 初始化Pinecone
        pc = Pinecone(api_key=api_key)
        
        index_name = "food-research"
        
        # 创建或连接索引
        if index_name not in pc.list_indexes().names():
            print(f"📝 创建新索引: {index_name}")
            pc.create_index(
                name=index_name,
                dimension=512,  # BGE模型的维度
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
        
        # 连接索引
        pinecone_index = pc.Index(index_name)
        
        # 创建向量存储
        vector_store = PineconeVectorStore(pinecone_index=pinecone_index)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        # 检查是否有数据
        stats = pinecone_index.describe_index_stats()
        
        if stats['total_vector_count'] == 0:
            print("📄 加载文档...")
            documents = SimpleDirectoryReader("food_research_data").load_data()
            print(f"📊 读取了 {len(documents)} 个文档")
            
            # 构建索引
            index = VectorStoreIndex.from_documents(
                documents,
                storage_context=storage_context
            )
            print(f"✅ 成功将文档存储到 Pinecone")
        else:
            print(f"✅ 索引已有 {stats['total_vector_count']} 个向量")
            index = VectorStoreIndex.from_vector_store(
                vector_store,
                storage_context=storage_context
            )
        
        # 查询测试
        query_engine = index.as_query_engine()
        response = query_engine.query("营养标签包含哪些信息？")
        print(f"\n🔍 查询结果: {str(response)[:200]}...\n")
        
        print("💡 优点:")
        print("  - 完全托管，无需维护")
        print("  - 高性能，低延迟")
        print("  - 自动扩展")
        print("  - 有免费额度")
        
        return index
        
    except ImportError:
        print("❌ 需要安装: pip install pinecone-client")
        return None
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None


# ============================================
# 方案4: 传统数据库（PostgreSQL + pgvector）
# ============================================
def demo_postgres():
    """使用PostgreSQL + pgvector"""
    print("\n" + "=" * 60)
    print("方案4: PostgreSQL + pgvector（传统数据库）")
    print("=" * 60)
    
    try:
        # 安装: pip install psycopg2-binary pgvector
        from llama_index.vector_stores.postgres import PGVectorStore
        from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
        
        # 数据库连接
        connection_string = os.getenv(
            'POSTGRES_CONNECTION',
            "postgresql://user:password@localhost:5432/food_research"
        )
        
        # 创建向量存储
        vector_store = PGVectorStore.from_params(
            database="food_research",
            host="localhost",
            password=os.getenv('POSTGRES_PASSWORD', 'password'),
            port=5432,
            user=os.getenv('POSTGRES_USER', 'postgres'),
            table_name="embeddings",
            embed_dim=512
        )
        
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        print("📄 加载文档...")
        documents = SimpleDirectoryReader("food_research_data").load_data()
        
        # 构建索引
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context
        )
        
        print("✅ 成功将文档存储到 PostgreSQL")
        
        print("\n💡 优点:")
        print("  - 结合传统数据库和向量搜索")
        print("  - 适合已有PostgreSQL的项目")
        print("  - 支持复杂查询和事务")
        
        return index
        
    except ImportError:
        print("❌ 需要安装: pip install psycopg2-binary pgvector")
        print("❌ 需要PostgreSQL安装pgvector扩展")
        return None
    except Exception as e:
        print(f"❌ 错误: {e}")
        print("💡 确保PostgreSQL已安装并配置pgvector扩展")
        return None


# ============================================
# 主函数
# ============================================
if __name__ == "__main__":
    print("\n🚀 外部数据库集成演示\n")
    
    # 方案1: Chroma（推荐新手）
    demo_chroma()
    
    # 方案2: Qdrant（推荐生产环境）
    demo_qdrant()
    
    # 方案3: Pinecone（云端方案）
    # demo_pinecone()  # 需要API Key
    
    # 方案4: PostgreSQL（已有数据库）
    # demo_postgres()  # 需要PostgreSQL
    
    print("\n" + "=" * 60)
    print("📋 总结对比")
    print("=" * 60)
    print("""
    | 数据库      | 部署方式 | 成本   | 性能 | 推荐场景           |
    |------------|---------|--------|------|-------------------|
    | Chroma     | 本地    | 免费   | 中等 | 开发测试、小规模   |
    | Qdrant     | 本地/云 | 免费起 | 高   | 生产环境、大规模   |
    | Pinecone   | 云端    | 付费   | 高   | 快速上线、无运维   |
    | PostgreSQL | 本地/云 | 免费起 | 中等 | 已有PG数据库项目  |
    
    💡 推荐方案:
    - 学习/开发: Chroma（最简单）
    - 生产环境: Qdrant（性能好，免费）
    - 快速上线: Pinecone（托管服务）
    """)
