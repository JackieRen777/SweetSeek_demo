# 🚀 SweetSeek 快速开始指南

## ⚡ 启动服务器

### 方式1：手动启动（默认）

**每次使用前需要手动启动**

```bash
# 后台启动（推荐，日常使用）
./start.sh -d

# 前台启动（开发调试）
./start.sh

# 停止服务器
./stop.sh
```

### 方式2：开机自动启动（可选）

**一次设置，永久生效**

```bash
# 安装开机自动启动
./install_autostart.sh

# 卸载开机自动启动
./uninstall_autostart.sh
```

安装后，每次开机 SweetSeek 会自动在后台启动。

---

**访问地址**：http://localhost:5001

---

## 📋 系统功能

✅ **自动化系统已完成！**

- 增量索引：已实现
- 文件监控：已实现
- Web上传：已实现
- 元数据提取：已优化
- 查询扩展：已实现
- 证据分级：已实现

---

## 🎯 三种添加文献的方式

### 方式1：文件监控（推荐）⭐⭐⭐⭐⭐

**最自动化，拖入即处理**

```bash
# 1. 启动系统（会询问是否启用文件监控）
./start.sh

# 2. 选择 'y' 启用文件监控

# 3. 直接拖文件到 food_research_data/papers/ 目录
# 系统会自动：
#   - 检测新文件
#   - 提取元数据
#   - 增量索引
#   - 无需重启
```

---

### 方式2：Web上传 ⭐⭐⭐⭐

**最方便，图形界面**

```bash
# 1. 访问上传页面
http://localhost:5001/upload.html

# 2. 选择PDF文件

# 3. 点击上传
# 系统会自动选择最优方法（增量或全量）
```

---

### 方式3：命令行 ⭐⭐⭐

**最灵活，完全控制**

```bash
# 1. 添加文件
cp ~/Downloads/*.pdf food_research_data/papers/

# 2. 运行增量索引
source .venv/bin/activate
python3 incremental_indexer.py

# 3. 完成（无需重启服务器）
```

---

## 🔧 安装依赖

```bash
# 激活虚拟环境
source .venv/bin/activate

# 安装所有依赖（包括watchdog）
pip install -r requirements.txt
```

---

## 🧪 测试系统

```bash
# 运行自动化测试
source .venv/bin/activate
python3 tests/test_auto_update.py
```

**预期输出**：
```
🧪 SweetSeek 自动化系统测试
============================================================
增量索引器                ✅ 通过
文件监控器                ✅ 通过
元数据提取                ✅ 通过
API上传                ✅ 通过
============================================================
通过: 4 | 失败: 0 | 跳过: 0
============================================================
🎉 所有测试通过！自动化系统已就绪。
```

---

## 📊 当前系统状态

```bash
# 检查系统状态
curl http://localhost:5001/api/stats
```

**当前数据**：
- 📄 PDF文件：16个
- 📚 文档节点：361个
- ✅ 元数据：100%正确
- 🚀 系统状态：运行中

---

## 🎯 日常使用流程

### 启动系统

```bash
# 方式A：使用启动脚本（推荐）
./start.sh

# 方式B：手动启动
source .venv/bin/activate
python3 app.py
```

### 添加新文献

```bash
# 方式A：直接拖文件（如果启用了文件监控）
# 拖到 food_research_data/papers/ 目录即可

# 方式B：Web上传
# 访问 http://localhost:5001/upload.html

# 方式C：命令行
cp ~/Downloads/*.pdf food_research_data/papers/
python3 incremental_indexer.py
```

### 使用系统

```bash
# 访问主页
http://localhost:5001

# 搜索文献
http://localhost:5001/search.html

# 管理文献
http://localhost:5001/management.html
```

---

## 🔍 性能对比

| 操作 | 旧方法 | 新方法（增量） | 提升 |
|------|--------|--------------|------|
| 添加10篇 | 30-60秒 | 10-20秒 | 3倍 |
| 添加100篇 | 10-15分钟 | 2-3分钟 | 5倍 |
| 需要重启 | 是 | 否 | ✅ |
| 自动化 | 否 | 是 | ✅ |

---

## 🛠️ 故障排除

### 问题1：watchdog未安装

```bash
source .venv/bin/activate
pip install watchdog
```

### 问题2：文件监控不工作

```bash
# 检查进程
ps aux | grep auto_update_system

# 手动启动
source .venv/bin/activate
python3 auto_update_system.py &
```

### 问题3：元数据不正确

```bash
# 重新提取元数据
source .venv/bin/activate
python3 -c "
from metadata_storage import MetadataStorage
from pdf_metadata_extractor import PDFMetadataExtractor
import os

storage = MetadataStorage()
extractor = PDFMetadataExtractor()

for filename in os.listdir('food_research_data/papers'):
    if filename.endswith('.pdf'):
        path = os.path.join('food_research_data/papers', filename)
        metadata = extractor.extract_metadata(path)
        storage.save_metadata(path, metadata)
        print(f'✅ {filename}')
"
```

### 问题4：索引不同步

```bash
# 重建跟踪文件
source .venv/bin/activate
python3 incremental_indexer.py --rebuild-tracking

# 重新运行增量索引
python3 incremental_indexer.py
```

---

## 📚 详细文档

- [自动化工作流程](./AUTOMATED_WORKFLOW.md) - 完整的自动化指南
- [扩展方案](./SCALABILITY_SOLUTION.md) - 大规模扩展方案
- [README](./README.md) - 项目总览

---

## 🎉 总结

现在你可以：

✅ **拖入文件** → 自动处理（10-20秒）  
✅ **Web上传** → 自动处理（10-20秒）  
✅ **命令行** → 手动触发（10-20秒）

**无需**：
- ❌ 重启服务器
- ❌ 手动提取元数据
- ❌ 重建整个索引
- ❌ 等待很长时间

**效果**：
- 🚀 快速添加（10-20秒）
- 🔄 立即可用
- 🤖 完全自动化
- 📈 适应长期迭代

---

## 🚀 开始使用

```bash
# 1. 启动系统
./start.sh

# 2. 选择启用文件监控 (y)

# 3. 访问系统
open http://localhost:5001

# 4. 添加文献（拖入文件即可）

# 5. 享受自动化！🎉
```

---

**祝使用愉快！** 🎊
