# 代码库功能说明（逐文件）

## 后端（Python）

### app.py
- 职责：Flask 服务入口；提供页面与 API（问答、流式问答、搜索、健康检查等）；编排 RAG 检索、文献去重、证据分级、Prompt 构建与 LLM 调用。
- 主要输入：
  - HTTP：`/api/init`、`/api/ask`、`/api/ask_stream`、`/api/search`、`/api/health` 等。
  - 配置：来自 [config.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/config.py) 的 HOST/PORT/DEBUG；DeepSeek 必需变量由 `validate_config()` 校验。
- 主要输出：
  - HTTP JSON/SSE：问答文本与 references 列表；健康检查与统计信息。
  - 日志：通过 [logger.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/logger.py) 写入 `logs/sweetseek.log` 并输出到 stdout。
- 关键依赖：Flask、flask-cors；[persistent_storage.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/persistent_storage.py) 的 `rag_system`；[query_expander.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/query_expander.py)；[evidence_ranker.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/evidence_ranker.py)；[services/llm_client.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/services/llm_client.py)。
- 对系统贡献：系统对外唯一运行入口；决定检索/引用/生成策略的最终行为与错误语义。

### persistent_storage.py
- 职责：构建/加载/重建 Chroma 向量索引；配置 Embedding 与 DeepSeek 客户端；提供增量插入接口；提供系统统计。
- 主要输入：
  - 文件系统：遍历 `Config.DATA_DIR` 文档；读取 PDF。
  - 配置：来自 [config.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/config.py) 的 `DATA_DIR`、`PERSIST_DIR`、Embedding/DeepSeek 配置。
- 主要输出：
  - 向量库：写入/更新 `chroma_db/`。
  - 元数据：通过 [metadata_storage.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/metadata_storage.py) 写入 `chroma_db/metadata.json`。
- 关键依赖：llama_index、chromadb、openai(OpenAI 兼容客户端，用于 DeepSeek)、dotenv；[pdf_metadata_extractor.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/pdf_metadata_extractor.py)。
- 对系统贡献：决定知识库载入与索引结构；是检索召回与稳定性的底座。

### metadata_storage.py
- 职责：维护 PDF 文献元数据的 JSON 持久化与内存缓存；提供查询、删除与统计；提供“按文件名回退解析”的容错策略；保证写入原子性与备份恢复。
- 主要输入：文献 `file_path` 与元数据字典；磁盘上的 `chroma_db/metadata.json`（及备份）。
- 主要输出：更新 `chroma_db/metadata.json`；对外返回元数据对象（用于 references 展示与 prompt 摘要）。
- 关键依赖：json、pathlib、tempfile；[pdf_metadata_extractor.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/pdf_metadata_extractor.py) 间接依赖（由上层调用）。
- 对系统贡献：实现“可追溯引用”的结构化索引，使问答具备可验证来源。

### pdf_metadata_extractor.py
- 职责：从 PDF 元数据字段与第一页文本抽取 DOI、年份、标题、作者，并推断期刊。
- 主要输入：PDF 文件路径。
- 主要输出：`{journal, year, title, authors, doi, filename}` 元数据。
- 关键依赖：pypdf/PyPDF2、re。
- 对系统贡献：提升 references 质量与检索可解释性；为证据分级提供关键字段。

### query_expander.py
- 职责：甜味科学领域查询扩展；把用户问题映射为检索 query（同义词/概念扩展），提升召回率。
- 主要输入：用户 query 字符串。
- 主要输出：`search_query` 与扩展术语集合。
- 关键依赖：纯 Python（无第三方）。
- 对系统贡献：提升检索召回，缓解用户表述与语料表述不一致问题。

### evidence_ranker.py
- 职责：对候选文献进行启发式证据分级与质量打分，用于 references 重排。
- 主要输入：references 列表（含 title/journal/year/score）。
- 主要输出：补充 evidence_level/total_score/final_score 等字段后的 references 列表。
- 关键依赖：re、datetime。
- 对系统贡献：将“相关性”与“证据质量”合并，使输出更符合学术检索预期。

### incremental_indexer.py
- 职责：检测新增文件并增量写入索引；维护 `chroma_db/indexed_files.json` 跟踪文件。
- 主要输入：`data_dir` 目录树；跟踪文件；新文档内容。
- 主要输出：向量库增量更新；更新跟踪文件；新增 PDF 的元数据写入。
- 关键依赖：llama_index SimpleDirectoryReader；[persistent_storage.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/persistent_storage.py) 的 `rag_system.add_documents()`。
- 对系统贡献：避免全量重建索引，适合持续增量更新知识库。

### services/llm_client.py
- 职责：定义 LLM 客户端适配层（当前实现 DeepSeek）；抽象流式/非流式输出，便于替换模型供应商。
- 主要输入：messages 列表、temperature、max_tokens。
- 主要输出：`ChatDelta` 流或 `(answer, reasoning)`。
- 关键依赖：DeepSeek(OpenAI 兼容) client 对象（由 persistent_storage 配置并注入）。
- 对系统贡献：隔离供应商实现细节，减少 `app.py` 与外部 SDK 的耦合。

### services/dependencies.py
- 职责：依赖注入入口；构建 query_expander/evidence_ranker/llm_client 等服务实例。
- 主要输入：进程环境（是否配置 DeepSeek）。
- 主要输出：`Services` 实例，供 `app.py` 使用。
- 关键依赖：[logger.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/logger.py)、[persistent_storage.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/persistent_storage.py)。
- 对系统贡献：提供可测试、可替换的依赖装配方式，为后续拆分服务层打基础。

### config.py
- 职责：配置聚合与环境切换；统一读取 env 并提供默认值。
- 输入：`.env`/环境变量。
- 输出：Config 对象字段（HOST/PORT/DEBUG、DATA_DIR/PERSIST_DIR、DeepSeek 与 Embedding 配置）。
- 关键依赖：python-dotenv、pathlib。
- 对系统贡献：消除配置散落与环境不一致问题，提升可移植性。

### logger.py
- 职责：统一日志创建与轮转；避免重复 handler；提供全局 logger。
- 输入：Config.LOG_DIR。
- 输出：RotatingFileHandler + stdout handler 的 logger。
- 关键依赖：logging、RotatingFileHandler。
- 对系统贡献：统一可观测性入口，便于排障与线上运维。

## 前端（HTML/JS/CSS）

### frontend/index.html
- 职责：主页 UI（问答 + references 面板）；挂载 `static/main.js`。
- 输入：用户交互（提问、参数）。
- 输出：调用后端 API 并渲染结果。
- 关键依赖：`static/main.js`、`static/style.css`。
- 对系统贡献：用户主体验入口。

### frontend/search.html
- 职责：文献检索页面；挂载 `static/search.js`。
- 输入：用户搜索关键词。
- 输出：调用 `/api/search` 并展示结果。
- 关键依赖：`static/search.js`、`static/style.css`。
- 对系统贡献：提供元数据搜索能力与浏览入口。

### frontend/about.html
- 职责：项目说明页面。
- 输入：无。
- 输出：静态展示。
- 对系统贡献：补充信息展示。

### static/main.js
- 职责：主页交互与 SSE 流式渲染；调用 `/api/init`、`/api/ask_stream`。
- 输入：用户问题、阈值与 max_results。
- 输出：逐步渲染 reasoning/answer/references；更新 UI 状态。
- 对系统贡献：实现实时回答体验与引用列表联动。

### static/search.js
- 职责：文献搜索页交互；调用 `/api/search`。
- 输入：搜索 query。
- 输出：渲染 search results。
- 对系统贡献：提供元数据检索入口，便于定位文献。

### static/style.css
- 职责：UI 样式（布局、组件样式、响应式）。
- 输入/输出：无（静态资源）。
- 对系统贡献：统一视觉体验。

## 运维与部署

### deploy.sh
- 职责：本地提交→推送→服务器拉取→重启→健康检查的一体化脚本（单次 SSH 连接）。
- 输入：可选提交信息；SSH 密码；服务器 `.env` 配置。
- 输出：服务重启结果与日志摘要。
- 关键依赖：git/ssh/netstat/nohup。
- 对系统贡献：将部署流程标准化，减少“拉代码但未生效”的风险。

### restart-server.sh
- 职责：仅重启服务并轮询端口检查。
- 输入：SSH 密码。
- 输出：端口监听状态与日志。
- 对系统贡献：用于快速恢复与排障。

### nginx_sweetseek.conf
- 职责：Nginx 反向代理配置（含 SSE/超时/静态资源）。
- 输入：HTTP 请求。
- 输出：代理到后端 5001。
- 对系统贡献：生产环境入口与连接管理策略。

