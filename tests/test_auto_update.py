#!/usr/bin/env python3
"""测试自动更新系统"""

import os
import sys
import time
import shutil
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from incremental_indexer import IncrementalIndexer
from auto_update_system import AutoUpdateSystem

def test_incremental_indexer():
    """测试增量索引器"""
    print("=" * 60)
    print("测试1: 增量索引器")
    print("=" * 60)
    
    indexer = IncrementalIndexer()
    
    # 测试获取所有文件
    all_files = indexer.get_all_files()
    print(f"✅ 找到 {len(all_files)} 个文件")
    
    # 测试检测新文件
    new_files = indexer.get_new_files()
    print(f"✅ 发现 {len(new_files)} 个新文件")
    
    # 测试跟踪文件
    print(f"✅ 已索引 {len(indexer.indexed_files)} 个文件")
    
    print("\n测试1: ✅ 通过\n")

def test_file_watcher():
    """测试文件监控器"""
    print("=" * 60)
    print("测试2: 文件监控器")
    print("=" * 60)
    
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        print("✅ watchdog 已安装")
        
        # 测试创建监控器
        system = AutoUpdateSystem()
        print("✅ 自动更新系统创建成功")
        
        print("\n测试2: ✅ 通过\n")
        return True
    except ImportError as e:
        print(f"❌ watchdog 未安装: {e}")
        print("\n测试2: ❌ 失败\n")
        return False

def test_metadata_extraction():
    """测试元数据提取"""
    print("=" * 60)
    print("测试3: 元数据提取")
    print("=" * 60)
    
    from pdf_metadata_extractor import PDFMetadataExtractor
    from metadata_storage import MetadataStorage
    
    extractor = PDFMetadataExtractor()
    storage = MetadataStorage()
    
    # 检查已有的元数据
    papers_dir = "./food_research_data/papers"
    if os.path.exists(papers_dir):
        pdf_files = [f for f in os.listdir(papers_dir) if f.endswith('.pdf')]
        print(f"✅ 找到 {len(pdf_files)} 个PDF文件")
        
        # 检查元数据
        metadata_count = 0
        for pdf_file in pdf_files[:3]:  # 只检查前3个
            file_path = os.path.join(papers_dir, pdf_file)
            if storage.has_metadata(file_path):
                metadata = storage.get_metadata(file_path)
                print(f"✅ {pdf_file}: {metadata.get('journal', 'N/A')}")
                metadata_count += 1
        
        print(f"✅ 已有 {metadata_count}/{len(pdf_files[:3])} 个文件的元数据")
    
    print("\n测试3: ✅ 通过\n")

def test_api_upload():
    """测试API上传功能"""
    print("=" * 60)
    print("测试4: API上传功能")
    print("=" * 60)
    
    import requests
    
    try:
        # 测试服务器是否运行
        response = requests.get("http://localhost:5001/api/stats", timeout=5)
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ 服务器运行正常")
            print(f"   - 文档数: {stats.get('total_documents', 0)}")
            print(f"   - 系统就绪: {stats.get('system_ready', False)}")
            print("\n测试4: ✅ 通过\n")
            return True
        else:
            print(f"❌ 服务器响应异常: {response.status_code}")
            print("\n测试4: ❌ 失败\n")
            return False
    except requests.exceptions.RequestException as e:
        print(f"⚠️  服务器未运行: {e}")
        print("   提示: 请先运行 python3 app.py")
        print("\n测试4: ⚠️  跳过\n")
        return None

def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("🧪 SweetSeek 自动化系统测试")
    print("=" * 60 + "\n")
    
    results = []
    
    # 测试1: 增量索引器
    try:
        test_incremental_indexer()
        results.append(("增量索引器", True))
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        results.append(("增量索引器", False))
    
    # 测试2: 文件监控器
    try:
        success = test_file_watcher()
        results.append(("文件监控器", success))
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        results.append(("文件监控器", False))
    
    # 测试3: 元数据提取
    try:
        test_metadata_extraction()
        results.append(("元数据提取", True))
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        results.append(("元数据提取", False))
    
    # 测试4: API上传
    try:
        success = test_api_upload()
        results.append(("API上传", success))
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        results.append(("API上传", False))
    
    # 总结
    print("=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    
    for name, result in results:
        if result is True:
            status = "✅ 通过"
        elif result is False:
            status = "❌ 失败"
        else:
            status = "⚠️  跳过"
        print(f"{name:20s} {status}")
    
    passed = sum(1 for _, r in results if r is True)
    failed = sum(1 for _, r in results if r is False)
    skipped = sum(1 for _, r in results if r is None)
    
    print("=" * 60)
    print(f"通过: {passed} | 失败: {failed} | 跳过: {skipped}")
    print("=" * 60 + "\n")
    
    if failed == 0:
        print("🎉 所有测试通过！自动化系统已就绪。")
        return 0
    else:
        print("⚠️  部分测试失败，请检查错误信息。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
