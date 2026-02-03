#!/usr/bin/env python3
"""
简化版路径修复脚本
在服务器上运行，修复向量数据库中的绝对路径
"""

# 修复 SQLite 版本问题（必须在导入chromadb之前）
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
    print("✅ 已加载 pysqlite3")
except ImportError:
    print("⚠️  未找到 pysqlite3，使用系统 sqlite3")

import chromadb
import os

def fix_vector_db_paths():
    """修复向量数据库中的路径"""
    
    print("=" * 60)
    print("开始修复向量数据库路径")
    print("=" * 60)
    
    # 连接到Chroma数据库
    print("\n[1/5] 连接到Chroma数据库...")
    client = chromadb.PersistentClient(path='./chroma_db')
    collection = client.get_collection('sweetseek_papers')
    
    doc_count = collection.count()
    print(f"✅ 连接成功，文档数量: {doc_count}")
    
    # 获取所有文档
    print("\n[2/5] 获取所有文档元数据...")
    results = collection.get(include=['metadatas'])
    
    ids = results['ids']
    metadatas = results['metadatas']
    print(f"✅ 获取到 {len(ids)} 个文档")
    
    # 分析路径格式
    print("\n[3/5] 分析路径格式...")
    absolute_count = 0
    relative_count = 0
    
    for metadata in metadatas[:10]:  # 检查前10个
        file_path = metadata.get('file_path', '')
        if file_path.startswith('/'):
            absolute_count += 1
        else:
            relative_count += 1
    
    print(f"前10个文档中：")
    print(f"  - 绝对路径: {absolute_count} 个")
    print(f"  - 相对路径: {relative_count} 个")
    
    # 修复路径
    print("\n[4/5] 开始修复路径...")
    
    fixed_count = 0
    updated_metadatas = []
    updated_ids = []
    
    # 服务器的基础路径
    server_base = '/www/wwwroot/FCN_SweetSeek'
    
    for doc_id, metadata in zip(ids, metadatas):
        file_path = metadata.get('file_path', '')
        
        if file_path.startswith('/'):
            # 绝对路径，需要转换为相对路径
            if file_path.startswith(server_base):
                # 移除服务器基础路径
                relative_path = file_path[len(server_base):].lstrip('/')
            else:
                # 尝试提取相对路径部分
                if 'sweet_related_paper' in file_path:
                    idx = file_path.index('sweet_related_paper')
                    relative_path = file_path[idx:]
                else:
                    # 无法转换，跳过
                    continue
            
            # 更新元数据
            metadata['file_path'] = relative_path
            updated_metadatas.append(metadata)
            updated_ids.append(doc_id)
            
            fixed_count += 1
            
            # 显示前3个示例
            if fixed_count <= 3:
                print(f"\n示例 {fixed_count}:")
                print(f"  原路径: {file_path[:80]}")
                print(f"  新路径: {relative_path[:80]}")
    
    # 批量更新
    print(f"\n[5/5] 批量更新 {len(updated_ids)} 个文档...")
    
    if updated_ids:
        collection.update(
            ids=updated_ids,
            metadatas=updated_metadatas
        )
        print(f"✅ 成功修复 {fixed_count} 个文档的路径格式")
    else:
        print("✅ 所有路径已经是相对格式，无需修复")
    
    # 验证修复结果
    print("\n" + "=" * 60)
    print("验证修复结果")
    print("=" * 60)
    
    results = collection.get(limit=5, include=['metadatas'])
    print("\n前5个文档的路径:")
    for i, meta in enumerate(results['metadatas'][:5], 1):
        path = meta.get('file_path', 'NO PATH')
        print(f"{i}. {path[:80]}")
    
    print("\n" + "=" * 60)
    print("修复完成！")
    print("=" * 60)

if __name__ == '__main__':
    fix_vector_db_paths()
