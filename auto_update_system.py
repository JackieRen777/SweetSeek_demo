#!/usr/bin/env python3
"""
自动更新系统 - 完全自动化的文献处理流程

功能：
1. 自动检测新文件
2. 自动提取元数据
3. 自动增量索引
4. 无需重启服务器
"""

import os
import time
import logging
from pathlib import Path
from typing import Set, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from incremental_indexer import IncrementalIndexer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PaperWatcher(FileSystemEventHandler):
    """文件监控处理器"""
    
    def __init__(self, indexer: IncrementalIndexer, debounce_seconds: int = 5):
        self.indexer = indexer
        self.debounce_seconds = debounce_seconds
        self.pending_files: Set[str] = set()
        self.last_event_time = 0
        
    def on_created(self, event):
        """文件创建事件"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        if self._is_supported_file(file_path):
            logger.info(f"检测到新文件: {os.path.basename(file_path)}")
            self.pending_files.add(file_path)
            self.last_event_time = time.time()
    
    def on_modified(self, event):
        """文件修改事件"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        if self._is_supported_file(file_path):
            # 文件可能正在复制中，等待完成
            self.pending_files.add(file_path)
            self.last_event_time = time.time()
    
    def _is_supported_file(self, file_path: str) -> bool:
        """检查是否是支持的文件类型"""
        supported_extensions = ('.pdf', '.docx', '.txt', '.md', '.csv', '.json')
        return file_path.lower().endswith(supported_extensions)
    
    def process_pending_files(self):
        """处理待处理的文件"""
        if not self.pending_files:
            return
        
        # 防抖：等待文件复制完成
        if time.time() - self.last_event_time < self.debounce_seconds:
            return
        
        logger.info(f"开始处理 {len(self.pending_files)} 个新文件...")
        
        # 处理文件
        try:
            # 触发增量索引
            self.indexer.add_new_documents()
            logger.info("✅ 新文件处理完成")
        except Exception as e:
            logger.error(f"❌ 处理文件失败: {e}")
        finally:
            self.pending_files.clear()


class AutoUpdateSystem:
    """自动更新系统"""
    
    def __init__(self, watch_dir: str = "./sweet_related_paper"):
        self.watch_dir = watch_dir
        self.indexer = IncrementalIndexer()
        self.observer = None
        self.watcher = None
        
    def start(self, background: bool = False):
        """启动自动更新系统"""
        logger.info("=" * 60)
        logger.info("🚀 启动自动更新系统")
        logger.info("=" * 60)
        logger.info(f"监控目录: {self.watch_dir}")
        logger.info(f"支持格式: PDF, DOCX, TXT, MD, CSV, JSON")
        logger.info("=" * 60)
        
        # 创建文件监控器
        self.watcher = PaperWatcher(self.indexer)
        self.observer = Observer()
        self.observer.schedule(self.watcher, self.watch_dir, recursive=True)
        self.observer.start()
        
        logger.info("✅ 文件监控已启动")
        logger.info("💡 现在可以直接将PDF文件拖到papers目录，系统会自动处理")
        logger.info("=" * 60)
        
        if not background:
            try:
                while True:
                    time.sleep(1)
                    # 定期检查待处理文件
                    if self.watcher:
                        self.watcher.process_pending_files()
            except KeyboardInterrupt:
                self.stop()
    
    def stop(self):
        """停止自动更新系统"""
        logger.info("\n正在停止自动更新系统...")
        if self.observer:
            self.observer.stop()
            self.observer.join()
        logger.info("✅ 自动更新系统已停止")


def main():
    """主函数"""
    import sys
    
    # 检查是否安装了watchdog
    try:
        import watchdog
    except ImportError:
        print("❌ 缺少依赖: watchdog")
        print("请运行: pip install watchdog")
        sys.exit(1)
    
    # 启动系统
    system = AutoUpdateSystem()
    
    try:
        system.start()
    except KeyboardInterrupt:
        print("\n\n👋 再见！")


if __name__ == "__main__":
    main()
