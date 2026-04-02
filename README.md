# SweetSeek - 智能科研问答系统

基于 RAG（检索增强生成）技术的 AI 科研助手，专为食品科学与甜味研究设计。

**最后更新：2026-01-22**

## 🎯 核心功能

- **智能问答**：基于 DeepSeek 大模型，深度理解科研问题并生成专业回答
- **文献检索**：自动从本地文献库检索相关内容，支持 PDF、Word、Markdown 等格式
- **查询扩展**：自动识别甜味剂同义词和相关术语，提高检索准确率
- **证据分级**：对检索到的文献进行质量评估和分级
- **元数据提取**：自动提取 PDF 文献的期刊、作者、DOI 等信息
- **增量索引**：支持增量添加新文献，无需重建整个索引
- **持久化存储**：使用 Chroma 向量数据库，启动速度快，内存占用低

## 📁 项目结构

```
SweetSeek/
├── app.py                          # Flask 主应用
├── persistent_storage.py           # RAG 系统核心（Chroma 向量数据库）
├── persistent_storage_original.py  # 原始版本（JSON 存储，备用）
├── incremental_indexer.py          # 增量索引管理器
├── query_expander.py               # 查询扩展模块（同义词/术语扩展）
├── evidence_ranker.py              # 证据分级系统
├── metadata_storage.py             # 元数据存储管理器
├── pdf_metadata_extractor.py       # PDF 元数据提取器
├── upload_handler.py               # 文件上传处理器
├── test_performance.py             # 性能测试工具
├── requirements.txt                # Python 依赖
├── .env                            # 环境变量配置
├── frontend/                       # 前端 HTML 页面
│   ├── index.html                  # 主页
│   ├── search.html                 # 搜索页面
│   └── about.html                  # 关于页面
├── static/                         # 静态资源
│   ├── style.css                   # 样式表
│   ├── main.js                     # 主页脚本
│   └── search.js                   # 搜索页面脚本
├── chroma_db/                      # Chroma 向量数据库（自动生成）
│   ├── chroma.sqlite3              # 向量索引数据库
│   ├── metadata.json               # PDF 元数据
│   └── indexed_files.json          # 已索引文件列表
├── sweet_related_paper/            # 文献库
│   ├── papers/                     # 学术论文
│   └── datasets/                   # 数据集
└── models/                         # 本地嵌入模型（自动下载）
```

## 🚀 快速开始

### 1. 环境要求

- Python 3.10+
- 8GB+ RAM（推荐 16GB）
- 2GB+ 磁盘空间

### 2. 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd SweetSeek

# 创建虚拟环境（推荐）
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置 API 密钥

编辑 `.env` 文件，填入你的 DeepSeek API 密钥：

```bash
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# 嵌入模型配置（默认使用本地中文模型）
EMBED_MODEL_TYPE=huggingface
EMBED_MODEL_NAME=BAAI/bge-small-zh-v1.5
```

获取 DeepSeek API 密钥：https://platform.deepseek.com/

### 4. 启动系统

```bash
python app.py
```

首次启动会：
1. 下载中文嵌入模型（约 400MB，仅首次）
2. 构建向量索引（约 1-2 分钟，取决于文献数量）
3. 启动 Flask 服务器

### 5. 访问界面

打开浏览器访问：**http://localhost:5001**

## 📖 使用指南

### 添加文献（服务器端）

将 PDF 文件放到 `sweet_related_paper/papers/` 目录，然后：

**方法1：增量索引（推荐）**
```bash
python incremental_indexer.py
```

**方法2：重启服务器**
```bash
# 停止服务器 (Ctrl+C)
python app.py
# 系统会自动检测并索引新文件
```

### 智能问答

1. 访问 http://localhost:5001/search.html
2. 输入问题，例如：
   - "阿斯巴甜对健康的影响是什么？"
   - "甜菊糖的甜度是蔗糖的多少倍？"
   - "糖醇类甜味剂的代谢机制"
3. 系统会：
   - 自动扩展查询（识别同义词）
   - 检索相关文献
   - 生成专业回答
   - 提供文献引用和证据分级

## 🔧 核心模块说明

### 1. persistent_storage.py
RAG 系统核心，负责：
- 文档加载和向量化
- Chroma 向量数据库管理
- 索引构建和持久化
- 查询引擎

**优势**：
- 内存占用减少 40-50%
- 启动速度快 2-10 倍
- 支持增量更新

### 2. query_expander.py
查询扩展模块，包含：
- 甜味剂同义词词典（中英文）
- 概念扩展词典
- 自动术语识别和扩展

**示例**：
- "阿斯巴甜" → 扩展为 "aspartame", "天冬酰苯丙氨酸甲酯", "APM"
- "甜味" → 扩展为 "sweetness", "甜度", "sweet taste"

### 3. evidence_ranker.py
证据分级系统，评估文献质量：
- 研究类型评分
- 期刊等级评分
- 时效性评分
- 数据质量评分

### 4. metadata_storage.py
元数据管理器，负责：
- PDF 元数据持久化
- 元数据缓存
- 备份和恢复

### 5. pdf_metadata_extractor.py
PDF 元数据提取器，自动提取：
- 期刊名称（识别率 98.8%）
- 发表年份
- 文章标题
- 作者列表
- DOI

**期刊识别策略**：
1. 从 PDF 元数据提取
2. 从第一页文本提取
3. 从 DOI 推断（支持 40+ 期刊/出版商）
4. 从文件名推断

### 6. incremental_indexer.py
增量索引管理器，支持：
- 检测新文件
- 增量添加到索引
- 跟踪已索引文件
- 避免重复索引

## 🎨 前端页面

- **index.html**：主页，系统介绍和导航
- **search.html**：智能问答界面
- **about.html**：关于页面

## 🔍 技术栈

| 组件 | 技术 |
|------|------|
| LLM | DeepSeek (deepseek-chat) |
| 嵌入模型 | BAAI/bge-small-zh-v1.5 (本地) |
| RAG 框架 | LlamaIndex 0.14.10 |
| 向量数据库 | ChromaDB 1.4.0 |
| Web 框架 | Flask 3.1.2 |
| PDF 处理 | pypdf 6.4.1 |
| 前端 | HTML5 + CSS3 + Vanilla JS |

## 📊 性能指标

| 指标 | Chroma 版本 | 原始版本 |
|------|-------------|----------|
| 启动时间 | 2-5 秒 | 15-30 秒 |
| 内存占用 | 500-800 MB | 1.2-1.5 GB |
| 索引构建 | 1-2 分钟 | 3-5 分钟 |
| 查询速度 | 0.5-1 秒 | 1-2 秒 |

## 🛠️ 高级功能

### 重建索引

```python
from persistent_storage import rag_system
rag_system.rebuild_index()
```

### 增量添加文档

```bash
python incremental_indexer.py
```

### 重建跟踪文件

```bash
python incremental_indexer.py --rebuild-tracking
```

## 🐛 常见问题

**Q: 首次启动很慢？**  
A: 首次运行会下载中文嵌入模型（约 400MB）和构建索引，请耐心等待。

**Q: 如何添加新文献？**  
A: 通过上传页面上传，或直接将文件放入 `sweet_related_paper/papers/` 目录，系统会自动增量索引。

**Q: 索引需要重建吗？**  
A: 不需要！索引会自动保存在 `chroma_db/` 目录，重启后自动加载。

**Q: 如何切换回原始版本？**  
A: 将 `persistent_storage_original.py` 复制为 `persistent_storage.py` 即可。

**Q: 内存不足怎么办？**  
A: 减少 `similarity_top_k` 参数（在 `app.py` 中），或使用更小的嵌入模型。

**Q: 如何停止系统？**  
A: 在终端按 `Ctrl + C`。

## 📝 开发计划

- [ ] 支持更多文件格式（Excel、PPT）
- [ ] 多语言支持（英文界面）
- [ ] 文献自动分类
- [ ] 知识图谱可视化
- [ ] 批量导入功能
- [ ] API 接口

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 🚀 部署到服务器

### 日常开发流程

1. **修改代码并测试**
2. **推送到 GitHub**
   ```bash
   ./push.sh
   ```
   - 自动生成更新摘要
   - 可选添加自定义说明
   - 询问是否立即部署

3. **部署到服务器**
   ```bash
   ./deploy.sh
   ```
   - 自动拉取代码
   - 检查环境配置
   - 重启服务

4. **快速重启服务**
   ```bash
   ./restart-server.sh
   ```

### 可用脚本

- `push.sh` - 智能推送（推荐）
- `deploy.sh` - 部署到服务器
- `restart-server.sh` - 快速重启

---

**开始你的 SweetSeek 科研之旅！** 🚀
