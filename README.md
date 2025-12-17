# SweetSeek

AI-powered research Q&A system based on LlamaIndex + DeepSeek-R1, designed for food science research.

## 核心特性

- **智能问答**：基于DeepSeek-R1推理模型，深度理解科研问题
- **文献检索**：自动从上传的文献中检索相关内容
- **中文优化**：使用本地中文嵌入模型BAAI/bge-small-zh-v1.5，完全免费
- **持久化存储**：索引自动保存，重启秒级加载
- **Web上传**：支持Web界面上传PDF、Word等文档
- **隐私保护**：文档本地处理，数据不上传云端

---

## 快速开始

### 方式一：使用启动脚本（推荐）

```bash
# macOS / Linux
./start.sh

# Windows
start.bat
```

启动脚本会自动：
- 创建虚拟环境
- 安装依赖
- 启动系统

### 方式二：手动启动

**第一步：安装依赖**
```bash
# 创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# 或 Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

**第二步：配置API密钥**
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入你的DeepSeek API密钥
# 获取密钥：https://platform.deepseek.com/
```

在 `.env` 文件中填入：
```bash
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_MODEL=deepseek-reasoner
```

**第三步：启动系统**
```bash
python app.py
```

**第四步：访问界面**
打开浏览器访问：**http://localhost:5001**

> 💡 **提示**: 首次启动会下载中文嵌入模型（约400MB），请耐心等待

---

## 功能页面

| 页面 | 地址 | 功能 |
|------|------|------|
| 主页 | http://localhost:5001/ | 系统介绍 |
| 搜索问答 | http://localhost:5001/search.html | 智能问答 |
| 上传文献 | http://localhost:5001/upload.html | 文献上传 |
| 文档管理 | http://localhost:5001/management.html | 文档管理 |
| 关于系统 | http://localhost:5001/about.html | 系统信息 |

---

## 项目结构

```
SweetSeek/
│
├── 📄 核心代码
│   ├── app.py                      # Flask主应用 + API路由
│   ├── persistent_storage.py       # RAG系统 + 持久化索引
│   ├── upload_handler.py           # 文件上传处理
│   └── check_system.py             # 系统检查脚本
│
├── 🔧 配置文件
│   ├── .env                        # 环境变量（API密钥，不提交）
│   ├── .env.example                # 环境变量模板
│   ├── requirements.txt            # Python依赖
│   ├── README.md                   # 完整文档（本文件）
│   ├── QUICKSTART.md               # 快速开始指南
│   └── PROJECT_STRUCTURE.md        # 项目结构详解
│
├── 🚀 启动脚本
│   ├── start.sh                    # Linux/macOS启动脚本
│   └── start.bat                   # Windows启动脚本
│
├── 🌐 前端文件
│   ├── frontend/                   # HTML页面
│   │   ├── index.html             # 主页（聊天界面）
│   │   ├── search.html            # 文献搜索
│   │   ├── upload.html            # 文档上传
│   │   ├── management.html        # 管理面板
│   │   └── about.html             # 关于页面
│   │
│   └── static/                     # 静态资源
│       ├── style.css              # 全局样式（专业蓝色主题）
│       ├── main.js                # 主页逻辑
│       ├── search.js              # 搜索功能
│       ├── upload.js              # 上传功能
│       └── management.js          # 管理功能
│
├── 📚 数据目录
│   ├── food_research_data/         # 文献存储
│   │   ├── papers/                # 论文目录
│   │   └── datasets/              # 数据集目录
│   │
│   ├── storage/                    # 向量索引（自动生成）
│   └── models/                     # 嵌入模型（自动下载）
│
└── 🧪 测试
    └── tests/
        └── test_app.py            # 应用测试

详细结构说明请查看 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
```

---

## 上传文献

### 方式1: Web界面上传（推荐）
1. 访问 http://localhost:5001/upload.html
2. 选择文件类型（论文/数据集）
3. 选择文件并上传
4. 系统自动向量化

### 方式2: 直接复制文件
```bash
# 将文件放入对应目录
cp your_paper.pdf food_research_data/papers/
cp your_data.csv food_research_data/datasets/

# 重启系统（自动向量化）
python app.py
```

### 支持的文件格式
- PDF (.pdf)
- Word (.doc, .docx)
- 文本 (.txt, .md)
- CSV (.csv)
- JSON (.json)

---

## 技术架构

### 系统架构
```
用户问题 → 向量化 → 检索文档 → DeepSeek-R1推理 → 答案
```

### 技术栈
- **LLM**: DeepSeek-R1 推理模型
- **嵌入**: BAAI/bge-small-zh-v1.5 (本地中文)
- **框架**: LlamaIndex RAG
- **前端**: Flask + HTML/CSS/JS
- **存储**: 本地持久化存储

### 嵌入模型说明

**什么是嵌入模型？**
嵌入模型将文本转换为数字向量，捕捉文本的语义信息。

**为什么选择本地模型？**
- 完全免费
- 数据隐私保护（本地处理）
- 离线可用
- 无API调用限制
- 中文效果更好

**推荐模型：BAAI/bge-small-zh-v1.5**
- 模型大小：约400MB
- 向量维度：512维
- 中文优化：专门针对中文训练
- 首次运行会自动下载到 `models/` 目录

---

## 数据库和存储

### 持久化存储（默认方案）
- 自动保存索引到 `./storage` 目录
- 重启后自动加载，无需重建
- 只在上传新文档时才重建
- 完全免费，无需外部服务

### 外部数据库选项（可选升级）

#### 1. Chroma（推荐升级方案）
```bash
pip install chromadb
```
- 完全免费，本地运行
- 支持增量更新
- 性能优秀

#### 2. Qdrant（生产环境推荐）
```bash
pip install qdrant-client
```
- 高性能，支持大规模数据
- 可本地或云端部署
- 有免费云服务额度

#### 3. Pinecone（云端托管）
```bash
pip install pinecone-client
```
- 完全托管，无需维护
- 自动扩展，高可用性
- 有免费额度

---

## 系统要求

- Python 3.8+
- 2GB+ 内存
- 500MB+ 磁盘空间（用于模型缓存）
- 网络连接（首次下载模型和调用API）

---

## 成本说明

| 项目 | 成本 | 说明 |
|------|------|------|
| 嵌入模型 | 免费 | 本地运行 |
| DeepSeek API | ¥0.014/千tokens | 非常便宜 |
| 向量存储 | 免费 | 本地存储 |

**示例成本计算：**
- 处理1000个问题 ≈ ¥1-2
- 向量化100篇论文 ≈ 免费

---

## 性能对比

| 模型 | 大小 | 维度 | 中文效果 | 速度 | 成本 |
|------|------|------|----------|------|------|
| OpenAI ada-002 | API | 1536 | 优秀 | 快 | 付费 |
| bge-small-zh | 400MB | 512 | 极佳 | 快 | 免费 |
| bge-large-zh | 1.3GB | 1024 | 极佳 | 中 | 免费 |

---

## 常见问题

### Q: 首次启动很慢？
**A:** 首次运行会下载中文嵌入模型（约400MB），请耐心等待。可以使用国内镜像加速：
```python
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
```

### Q: 如何添加文献？
**A:** 两种方式：
1. 访问上传页面 http://localhost:5001/upload.html
2. 直接将文件放入 `food_research_data/papers/` 目录

### Q: 索引需要重建吗？
**A:** 不需要！索引会自动保存到 `storage/` 目录，重启后自动加载。只有上传新文档时才会重建。

### Q: 如何停止系统？
**A:** 在终端按 `Ctrl + C` 停止Flask应用。

### Q: 索引加载失败怎么办？
**A:** 删除 `storage/` 目录，重新启动系统：
```bash
rm -rf storage/
python app.py
```

### Q: 内存不足怎么办？
**A:** 可以减少chunk_size或使用外部数据库（Chroma/Qdrant）。

### Q: 查询速度慢怎么办？
**A:** 减少检索数量（similarity_top_k参数）。

---

## 最佳实践

### 开发阶段
- 使用默认的本地持久化存储
- 使用 bge-small-zh 嵌入模型（快速、够用）

### 生产环境
- **小规模**：使用 Chroma 数据库
- **大规模**：使用 Qdrant 云服务
- **企业级**：使用 Pinecone 或自建 Qdrant 集群

### 配置优化
```python
# 在代码中调整参数
Settings.chunk_size = 512        # 文档分块大小
similarity_top_k = 5             # 检索文档数量
```

---

## 使用流程

1. **启动系统**
   ```bash
   python app.py
   ```

2. **上传文献**
   - 访问上传页面
   - 选择文件上传
   - 等待向量化完成

3. **开始提问**
   - 访问搜索页面
   - 输入问题
   - 获得AI回答和参考文献

4. **管理文档**
   - 访问管理页面
   - 查看已上传文档
   - 删除不需要的文档

---

## 贡献指南

欢迎提交Issue和Pull Request！

### 如何贡献
1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

---

## 致谢

- [LlamaIndex](https://www.llamaindex.ai/) - RAG框架
- [DeepSeek](https://www.deepseek.com/) - LLM服务
- [BAAI](https://www.baai.ac.cn/) - 中文嵌入模型

---

## 联系方式

如有问题，请提交Issue或联系维护者。

---

## 推荐配置

**DeepSeek API (LLM) + bge-small-zh-v1.5 (嵌入)**

**为什么选择这个组合？**
- DeepSeek便宜且中文能力强
- 本地嵌入模型免费且隐私安全
- bge-small-zh专门针对中文优化
- 组合使用性价比最高

---

**开始你的 SweetSeek 科研之旅！**

如果这个项目对你有帮助，请给个Star！
