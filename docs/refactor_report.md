# 重构报告（问题清单、修复方案与维护建议）

## 背景
本项目是 SweetSeek：基于 Flask + LlamaIndex + Chroma 的 RAG 问答系统，提供 references 引用列表与流式问答体验。核心入口为 [app.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/app.py)，索引与向量库由 [persistent_storage.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/persistent_storage.py) 管理，元数据由 [metadata_storage.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/metadata_storage.py) 管理。

## 问题清单（按优先级）

### P0（阻断/高风险）
- 增量索引脚本调用不存在的方法导致必然崩溃：[incremental_indexer.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/incremental_indexer.py)
- PDF 年份提取错误：捕获组+findall 导致年份变为 `19/20`：[pdf_metadata_extractor.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/pdf_metadata_extractor.py)
- `/api/ask` 与 `/api/ask_stream` 在“检索为空/引用为空”路径下缺乏兜底，可能触发 500：[app.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/app.py)
- ref 取模映射会造成“错误归因”，对学术引用是高风险设计：[app.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/app.py)

### P1（可维护性/一致性）
- 业务逻辑过度集中在 `app.py`，违反单一职责与开闭原则，难以替换检索/排序/LLM 策略。
- 配置与日志分散：`os.getenv()`、dotenv、日志 handler 在多个模块重复配置，环境迁移容易出错。
- 文件路径规范不统一：绝对/相对、不同机器根路径导致元数据匹配不稳定，长期依赖修复脚本。

### P2（工程化/运维）
- 全局可变状态（对话历史、初始化标记）不适合多进程部署与长期运行。
- 缺少单元/集成测试与质量门禁，导致“改动后线上行为漂移”风险高。

## 本轮已完成的修复与重构

### 1) 逻辑与边界修复
- 修复 PDF 年份提取：将年份正则改为非捕获组，保证提取完整年份：[pdf_metadata_extractor.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/pdf_metadata_extractor.py)
- 为 `/api/ask`、`/api/ask_stream` 增加空检索兜底与流式参数校验，避免空列表导致崩溃：[app.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/app.py)
- 移除 ref 取模映射：无效 ref 直接移除，避免错误归因（后续可升级为“无法定位来源”的显式提示）：[app.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/app.py)
- 实现 `rag_system.add_documents()` 以支持增量索引，修复脚本必炸点：[persistent_storage.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/persistent_storage.py)
- 元数据持久化更健壮：原子写入、备份恢复、缺失文件时优先从备份恢复：[metadata_storage.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/metadata_storage.py)

### 2) 配置与日志统一
- 配置聚合：补齐 DATA_DIR/PERSIST_DIR 与 embedding 配置字段：[config.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/config.py)
- 日志统一：`app.py` 使用统一 logger 工厂，避免重复 handler 与格式漂移：[logger.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/logger.py)、[app.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/app.py)
- `persistent_storage.py` 统一从 config 读取 DeepSeek 与 embedding 配置，减少模块内重复加载 dotenv：[persistent_storage.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/persistent_storage.py)

### 3) 模块边界与依赖注入（第一步）
- 新增 LLM 适配层：将 DeepSeek/OpenAI 兼容 SDK 的细节隔离在 `services/llm_client.py`：[llm_client.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/services/llm_client.py)
- 新增依赖装配入口：`services/dependencies.py` 提供 `build_services()`，由 `app.py` 注入使用：[dependencies.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/services/dependencies.py)、[app.py](file:///Users/jackieren/Desktop/FCN_SweetSeek/app.py)

### 4) 测试与质量门禁
- 新增 pytest 测试覆盖核心边界与回归路径：`tests/`：[tests](file:///Users/jackieren/Desktop/FCN_SweetSeek/tests)
- 新增质量工具与 CI：ruff/mypy/pytest-cov/bandit/pip-audit（初始覆盖率门禁为 20%，后续逐步抬升）：[pyproject.toml](file:///Users/jackieren/Desktop/FCN_SweetSeek/pyproject.toml)、[ci.yml](file:///Users/jackieren/Desktop/FCN_SweetSeek/.github/workflows/ci.yml)

## 性能影响评估
- RAG 主路径：新增“空检索兜底判断”与“无效 ref 清理”属于 O(n) 字符串处理，不改变向量检索复杂度，性能影响可忽略。
- 增量索引：新增 `add_documents()` 在插入时会执行分块转换，理论上与全量构建相比显著降低重建成本，但仍需实际评估文档规模与 chunk 数对写入耗时的影响。
- 元数据写入：原子写入增加 `fsync` 与备份拷贝，写入更安全但略增写入开销；该路径属于离线/低频操作，收益大于成本。

## 风险与兼容性
- 对外 API schema 保持兼容：仍返回 `success/answer/references/response_time`；在无检索结果时返回空 `references` 并给出可解释文案。
- LLM 适配层为“新增不破坏”模块；若 DeepSeek 未配置，行为明确为不可用提示。
- CI/工具为“新增约束”，不会影响运行时，但会对未来提交提出质量要求。

## 长期维护建议（下一步迭代）
- 把 `app.py` 内部的“检索→去重→排序→prompt 构建”进一步下沉到 `services/`，让路由层只负责参数校验与响应，提升 OCP 与可测试性。
- 引入统一的 request/response schema（例如 pydantic model），保证流式与非流式接口的参数校验一致。
- 逐步提升覆盖率门禁：优先补齐 `pdf_metadata_extractor.py` 与 `persistent_storage.py` 的高风险路径测试（PDF 元数据异常、Chroma 不可用、索引为空等）。
- 规范路径：将绝对/相对路径映射收敛到单一 `PathNormalizer`，并提供一次性迁移脚本替代长期“运行时兜底”。\n
