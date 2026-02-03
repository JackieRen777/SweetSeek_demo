#!/usr/bin/env python3
"""
修复向量数据库中的文件路径格式
将绝对路径转换为相对路径，以匹配元数据数据库的格式
"""

import chromadb
import os
from pathlib import Path

def fix_vector_db_paths():
    """修复向量数据库中的路径"""
    
    # 连接到Chroma数据库
    client = chromadb.PersistentClient(path='./chroma_db')
    collection = client.get_collection('sweetseek_papers')
    
    print(f"向量数据库中的文档数量: {collection.count()}")
    
    # 获取所有文档
    results = collection.get(include=['metadatas'])
    
    ids = results['ids']
    metadatas = results['metadatas']
    
    print(f"\n开始修复路径格式...")
    
    fixed_count = 0
    base_path = os.getcwd()
    
    # 批量更新元数据
    updated_metadatas = []
    updated_ids = []
    
    for doc_id, metadata in zip(ids, metadatas):
        file_path = metadata.get('file_path', '')
        
        if file_path.startswith('/'):
            # 绝对路径，需要转换为相对路径
            try:
                # 转换为相对路径
                relative_path = os.path.relpath(file_path, base_path)
                
                # 更新元数据
                metadata['file_path'] = relative_path
                updated_metadatas.append(metadata)
                updated_ids.append(doc_id)
                
                fixed_count += 1
                
                if fixed_count <= 3:
                    print(f"\n示例 {fixed_count}:")
                    print(f"  原路径: {file_path}")
                    print(f"  新路径: {relative_path}")
            
            except Exception as e:
                print(f"转换路径失败 {file_path}: {e}")
    
    # 批量更新Chroma集合
    if updated_ids:
        print(f"\n正在更新 {len(updated_ids)} 个文档的元数据...")
        collection.update(
            ids=updated_ids,
            metadatas=updated_metadatas
        )
        print(f"✅ 成功修复 {fixed_count} 个文档的路径格式")
    else:
        print("✅ 所有路径已经是相对格式，无需修复")
    
    # 验证修复结果
    print("\n验证修复结果...")
    results = collection.get(limit=3, include=['metadatas'])
    print("前3个文档的路径:")
    for i, meta in enumerate(results['metadatas'][:3], 1):
        print(f"{i}. {meta.get('file_path', 'NO PATH')}")

if __name__ == '__main__':
    fix_vector_db_paths()
