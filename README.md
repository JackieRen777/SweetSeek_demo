# 🍎 食品AI科研问答系统

基于 LlamaIndex + DeepSeek-R1 的智能科研问答系统，专为食品科学研究设计。

## ✨ 特性

- 🤖 **智能问答**：基于DeepSeek-R1推理模型，深度理解科研问题
- 📚 **文献检索**：自动从上传的文献中检索相关内容
- 🇨🇳 **中文优化**：使用本地中文嵌入模型，完全免费
- 💾 **持久化存储**：索引自动保存，重启秒级加载
- 📤 **Web上传**：支持Web界面上传PDF、Word等文档
- 🔒 **隐私保护**：文档本地处理，数据不上传云端

## 🚀 快速开始

### 1. 克隆项目

```bash
# GitHub
git clone https://github.com/YOUR_USERNAME/food-ai-research-qa.git

# 或 Gitee（国内推荐）
git clone https://gitee.com/YOUR_USERNAME/food-ai-research-qa.git

cd food-ai-research-qa
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入你的DeepSeek API密钥
nano .env
```

在 `.env` 文件中填入：
```bash
DEEPSEEK_API_KEY=your_api_key_here
```

> 💡 获取API密钥：访问 [DeepSeek开放平台](https://platform.deepseek.com/)

### 4. 启动系统

```bash
python app.py
```

### 5. 访问界面

```
http://localhost:5001
```

### 6. 开始提问

在Web界面输入问题，获得AI回答和参考文献！

## 技术栈

- **LLM**: DeepSeek-R1 推理模型
- **嵌入**: BAAI/bge-small-zh-v1.5 (本地中文)
- **框架**: LlamaIndex RAG
- **前端**: Flask + HTML/CSS/JS

## 项目结构

```
├── app.py                    # Flask后端
├── .env                      # API配置
├── frontend/                 # HTML模板
├── static/                   # CSS/JS
├── food_research_data/       # 文献目录
│   ├── papers/              # 论文
│   └── datasets/            # 数据
└── notebooks/               # 示例脚本
```

## 📤 上传文献

### 方式1: Web界面上传（推荐）

1. 访问 `http://localhost:5001/upload.html`
2. 选择文件类型（论文/数据集）
3. 选择文件并上传
4. 系统自动向量化

### 方式2: 直接复制文件

```bash
# 将文件放入目录
cp your_paper.pdf food_research_data/papers/

# 重启系统（自动向量化）
python app.py
```

### 支持格式

- ✅ PDF (.pdf)
- ✅ Word (.doc, .docx)
- ✅ 文本 (.txt, .md)
- ✅ CSV (.csv)
- ✅ JSON (.json)

> 💡 详细教程：查看 [文献上传完整指南.md](文献上传完整指南.md)

## 📖 使用文档

- [快速开始.md](快速开始.md) - 新手入门
- [文献上传完整指南.md](文献上传完整指南.md) - 上传和向量化
- [数据库使用指南.md](数据库使用指南.md) - 数据库配置
- [本地嵌入模型说明.md](本地嵌入模型说明.md) - 模型详解
- [Git使用指南.md](Git使用指南.md) - Git操作

## 🛠️ 系统要求

- Python 3.8+
- 2GB+ 内存
- 500MB+ 磁盘空间（用于模型缓存）
- 网络连接（首次下载模型和调用API）

## 💰 成本说明

- **嵌入模型**：完全免费（本地运行）
- **DeepSeek API**：约 ¥0.014/千tokens（非常便宜）
- **向量存储**：免费（本地存储）

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

- [LlamaIndex](https://www.llamaindex.ai/) - RAG框架
- [DeepSeek](https://www.deepseek.com/) - LLM服务
- [BAAI](https://www.baai.ac.cn/) - 中文嵌入模型

## 📧 联系方式

如有问题，请提交Issue或联系维护者。

---

⭐ 如果这个项目对你有帮助，请给个Star！

## 文档说明

- **快速开始.md** - 详细使用指南
- **文献处理教程.md** - 文献上传和向量化
- **DeepSeek-R1推理模型说明.md** - 模型说明
- **本地嵌入模型说明.md** - 嵌入模型详解

## 示例脚本

```bash
# 完整RAG系统
python notebooks/04_DeepSeek完整版.py

# 向量化演示
python notebooks/06_文献向量化演示.py
```

## 系统架构

```
用户问题 → 向量化 → 检索文档 → DeepSeek-R1推理 → 答案
```

## 配置

编辑 `.env` 文件：
```bash
DEEPSEEK_API_KEY=your_api_key
DEEPSEEK_MODEL=deepseek-reasoner
```

## 许可证

MIT License

---

**开始你的食品AI科研之旅！**

访问：http://localhost:5001
