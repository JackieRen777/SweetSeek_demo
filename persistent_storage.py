#!/usr/bin/env python3
"""
持久化存储管理
避免每次重启都重新构建索引
"""
import os
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, StorageContext, load_index_from_storage
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai_like import OpenAILike
from dotenv import load_dotenv

load_dotenv()

class PersistentRAGSystem:
    def __init__(self, 
                 data_dir="food_research_data",
                 persist_dir="./storage"):
        self.data_dir = data_dir
        self.persist_dir = persist_dir
        self.index = None
        self.query_engine = None
        
        # 配置LLM和嵌入模型
        self._configure_models()
    
    def _configure_models(self):
        """配置模型"""
        Settings.llm = OpenAILike(
            model="deepseek-reasoner",
            api_key=os.getenv('DEEPSEEK_API_KEY'),
            api_base="https://api.deepseek.com",
            is_chat_model=True,
            temperature=0.1,
            max_tokens=2000
        )
        
        Settings.embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-small-zh-v1.5",
            cache_folder="./models"
        )
    
    def load_or_create_index(self):
        """加载已有索引或创建新索引"""
        if os.path.exists(self.persist_dir):
            print(f"[加载] 从 {self.persist_dir} 加载已有索引...")
            try:
                # 从磁盘加载索引
                storage_context = StorageContext.from_defaults(persist_dir=self.persist_dir)
                self.index = load_index_from_storage(storage_context)
                print("[成功] 索引加载完成")
                return True
            except Exception as e:
                print(f"[警告] 加载索引失败: {e}")
                print("[重建] 将重新构建索引...")
                return self._build_new_index()
        else:
            print("[构建] 首次运行，构建新索引...")
            return self._build_new_index()
    
    def _build_new_index(self):
        """构建新索引"""
        try:
            # 加载文档
            documents = SimpleDirectoryReader(
                self.data_dir,
                recursive=True
            ).load_data()
            
            print(f"[加载] 读取了 {len(documents)} 个文档")
            
            # 构建索引
            self.index = VectorStoreIndex.from_documents(documents)
            
            # 持久化到磁盘
            self.index.storage_context.persist(persist_dir=self.persist_dir)
            print(f"[保存] 索引已保存到 {self.persist_dir}")
            
            return True
        except Exception as e:
            print(f"[失败] 构建索引失败: {e}")
            return False
    
    def rebuild_index(self):
        """强制重建索引（上传新文档后调用）"""
        print("[重建] 重新构建索引...")
        
        # 删除旧索引
        if os.path.exists(self.persist_dir):
            import shutil
            shutil.rmtree(self.persist_dir)
        
        return self._build_new_index()
    
    def get_query_engine(self, similarity_top_k=3):
        """获取查询引擎"""
        if self.index is None:
            raise ValueError("索引未初始化，请先调用 load_or_create_index()")
        
        if self.query_engine is None:
            self.query_engine = self.index.as_query_engine(
                similarity_top_k=similarity_top_k,
                response_mode="compact"
            )
        
        return self.query_engine
    
    def add_documents(self, new_docs):
        """增量添加文档（不重建整个索引）"""
        if self.index is None:
            raise ValueError("索引未初始化")
        
        print(f"[增量] 添加 {len(new_docs)} 个新文档...")
        
        # 插入新文档
        for doc in new_docs:
            self.index.insert(doc)
        
        # 保存更新后的索引
        self.index.storage_context.persist(persist_dir=self.persist_dir)
        print("[保存] 索引已更新")
        
        # 重置查询引擎以使用新索引
        self.query_engine = None
    
    def get_stats(self):
        """获取索引统计信息"""
        if self.index is None:
            return {"status": "未初始化"}
        
        # 获取文档数量
        doc_store = self.index.storage_context.docstore
        docs = doc_store.docs
        
        return {
            "status": "已初始化",
            "total_documents": len(docs),
            "persist_dir": self.persist_dir,
            "index_exists": os.path.exists(self.persist_dir)
        }

# 全局实例
rag_system = PersistentRAGSystem()
