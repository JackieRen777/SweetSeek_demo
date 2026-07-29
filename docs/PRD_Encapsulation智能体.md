# SweetSeek「Encapsulation」智能体产品需求文档

| 项目 | 内容 |
| --- | --- |
| 文档版本 | v1.0 |
| 文档状态 | 待评审 |
| 产品名称 | Encapsulation 智能体（包埋智能体） |
| 所属产品 | SweetSeek |
| 目标用户 | 食品科学、功能食品、蛋白质与包埋方向的科研人员 |
| 预计范围 | MVP：独立知识库 + RAG 问答 + PDF 数据库入口 |

## 1. 背景与问题

SweetSeek 当前提供 Sweetness 和 Dual-Protein 两类科研问答。包埋（encapsulation）相关文献、术语和实验条件与现有知识域有明显差异，继续混用同一个知识库会造成召回噪声、引用不准确和回答主题漂移。用户需要一个可直接切换的「Encapsulation」智能体，用与甜味智能体一致的问答体验，并有独立的 PDF 文献库作为数据入口。

## 2. 产品目标

1. 在主导航中将 `Encapsulation` 放置于 `Dual-Protein` 与 `References` 之间，用户可一键进入包埋智能体。
2. 提供与 Sweet Q&A 一致的单轮/连续对话、流式输出、检索状态、引用文献和证据说明。
3. 建立独立的 Encapsulation PDF 数据库入口，支持上传、查看、删除、重新索引和索引状态查询。
4. 确保回答只基于 Encapsulation 知识域文献，并在无足够证据时明确告知用户。

## 3. 非目标（MVP 不做）

- 不在本期实现新的包埋预测模型、配方优化模型或实验自动控制。
- 不把 Encapsulation 文献混入 Sweetness 或 Dual-Protein 的检索结果。
- 不开放匿名用户直接删除全站文献；删除和重建索引需要管理员权限。
- 不承诺论文全文版权合规，上传者需对文献拥有合法使用权。

## 4. 用户故事

- 作为科研人员，我可以从导航进入 Encapsulation，并直接提出“不同壁材对乳液包埋效率的影响”等问题。
- 作为科研人员，我可以看到回答引用的论文标题、作者、年份、DOI 和原始 PDF，并判断证据来源。
- 作为知识库管理员，我可以从 Encapsulation 数据库入口上传 PDF，看到解析/索引进度，失败后重试。
- 作为知识库管理员，我可以按标题、文件名、年份筛选文献并移除过期或错误文件。

## 5. 信息架构与入口

桌面端主导航顺序：`Home` → `Sweetness`（下拉）→ `Dual-Protein`（下拉）→ `Encapsulation` → `References`。

`Encapsulation` 是独立的一级入口，点击后进入 `/encapsulation`（或现有前端路由对应的 Encapsulation screen），默认展示问答页。Encapsulation 数据库入口建议放在该智能体页面的页签/次级导航中，名称为 `Encapsulation Database`；管理员也可从 Encapsulation 页面右上角进入。

移动端需在现有菜单中保持同样顺序，并保证入口可访问。

## 6. 功能需求

### 6.1 Encapsulation 问答

| 编号 | 需求 | 优先级 |
| --- | --- | --- |
| Q1 | 支持文本问题输入、发送、停止生成、清空当前对话和历史对话展示 | P0 |
| Q2 | 支持流式响应；展示“检索文献/生成答案”等状态 | P0 |
| Q3 | 问答使用 Encapsulation 专属 RAG 实例、查询扩展器和配置，不调用 Sweetness/Dual-Protein 索引 | P0 |
| Q4 | 回答显示引用卡片，包含 ref_id、标题、期刊、年份、作者、DOI、相关度和文件名 | P0 |
| Q5 | 支持点击引用查看/下载 PDF；文件不可用时给出明确错误 | P1 |
| Q6 | 无命中文献、知识库未就绪或 LLM 失败时，返回可理解的错误/降级文案，不编造引用 | P0 |
| Q7 | 默认支持中文，也接受英文专业术语；保留用户原始问题 | P1 |

### 6.2 Encapsulation 数据库

| 编号 | 需求 | 优先级 |
| --- | --- | --- |
| D1 | 展示文献总数、已索引数、处理中数、失败数及最后更新时间 | P0 |
| D2 | 管理员上传一个或多个 PDF；限制扩展名为 `.pdf`，单文件大小上限由部署配置控制（建议 50 MB） | P0 |
| D3 | 上传后执行：文件校验 → 文本抽取 → 元数据抽取 → 分块 → 向量化/Embedding → 持久化索引 | P0 |
| D4 | 展示每个文件的状态：待处理、处理中、已索引、失败；失败显示原因并支持重试 | P0 |
| D5 | 支持按文件名/标题/作者/年份搜索和分页 | P1 |
| D6 | 支持管理员删除文件；删除前二次确认，同时删除原文件、元数据和向量记录 | P0 |
| D7 | 支持单文件“重新索引”；增量更新不能影响其他文件可检索性 | P0 |
| D8 | 检测文件哈希去重；同一文件重复上传时提示已存在，不创建重复向量 | P1 |

### 6.3 References 联动

Encapsulation 问答页只显示 Encapsulation 知识域引用。全局 `References` 页可增加知识域筛选（Sweetness / Dual-Protein / Encapsulation），默认不改变现有行为。引用详情应标记 `domain=encapsulation`。

## 7. 交互与页面要求

### 7.1 问答页

复用现有 Sweet Q&A 布局、输入框、流式消息、加载态、错误态和引用区。页面标题建议为 `Encapsulation Q&A`，中文辅助文案为“包埋科研智能体”。回答下方显示“基于 N 篇 Encapsulation 文献”，并提供引用展开/收起。

### 7.2 数据库页

页面顶部：标题、知识库统计、上传 PDF 按钮（带上传图标）和刷新按钮。主体为文献表格，列包括：文件名、标题、作者、年份、页数、索引状态、更新时间、操作。长文件名省略但支持悬浮查看；处理中状态需有进度或阶段文案。空状态提供上传入口；失败状态提供原因和重试操作。

## 8. 技术方案与系统边界

### 8.1 后端

- 新增独立 `encapsulation_rag`（`PersistentRAGSystem`）实例，建议数据目录 `./Encapsulation_related_paper/papers`，持久化目录 `./storage_encapsulation`。
- 新增 `EncapsulationQueryExpander`，维护包埋术语、同义词和中英文映射（如 encapsulation、microencapsulation、wall material、encapsulation efficiency、release profile 等）。
- 复用 `ChatService`，新增 `mode="encapsulation"`；复用 SSE 事件协议：`start`、`status`、`references`、`retrieval_stats`、`answer_start`、`answer`、`done`、`error`。
- 新增 Encapsulation API（路径可按现有版本规范调整）：
  - `POST /api/encapsulation/ask`：非流式问答。
  - `GET /api/encapsulation/ask/stream` 或现有 SSE 约定：流式问答。
  - `GET /api/encapsulation/documents`：分页、筛选和统计。
  - `POST /api/encapsulation/documents/upload`：上传并创建索引任务。
  - `POST /api/encapsulation/documents/{id}/reindex`：重建单文件索引。
  - `DELETE /api/encapsulation/documents/{id}`：删除文件、元数据和向量。
  - `GET /api/encapsulation/documents/{id}/file`：鉴权后下载/预览 PDF。
- 启动时异步初始化 Encapsulation 索引；系统未就绪时问答接口返回可重试状态，不阻塞其他智能体。

### 8.2 数据模型

`encapsulation_documents`：`id`、`sha256`、`filename`、`storage_path`、`title`、`authors`、`journal`、`year`、`doi`、`page_count`、`status`、`error_message`、`chunk_count`、`created_at`、`updated_at`、`indexed_at`。

向量记录 metadata 至少包含 `domain=encapsulation`、`document_id`、`filename`、`page`、`chunk_id`。原文件与索引数据应使用持久化磁盘/数据卷，禁止只存容器临时目录。

### 8.3 安全与权限

- 问答和文献列表可按现有登录策略开放；上传、删除、重索引、文件下载至少需要管理员/研究组权限。
- 校验 MIME、扩展名、文件大小和 PDF 可解析性；文件名需安全规范化，防止路径穿越。
- 接口限制上传频率，记录操作者、文件哈希和操作时间；日志不得记录 API 密钥或全文内容。

## 9. 非功能要求

- 可靠性：单篇文献索引失败不影响已完成文献和其他智能体；任务可重试且幂等。
- 性能：已完成索引的问答首字节目标 ≤ 3 秒（不含 LLM 外部服务异常）；上传任务异步执行。
- 可观测性：记录检索耗时、命中块数、唯一文献数、LLM 耗时、索引失败原因。
- 一致性：所有引用必须能通过 `document_id` 找到对应 PDF；删除后不得继续被检索。
- 兼容性：不改变现有 Sweetness、Dual-Protein API 字段和前端行为。

## 10. 验收标准

1. 桌面和移动导航均显示 `Encapsulation`，位置在 Dual-Protein 与 References 之间；点击可进入问答页。
2. Encapsulation 问答能完成非流式和流式请求，事件顺序和现有问答兼容，回答引用仅来自 Encapsulation 文献。
3. 上传合法 PDF 后，文献状态从处理中变为已索引，且可被问答召回；重复哈希不会产生重复记录。
4. 上传损坏 PDF、超限文件或非 PDF 文件时，前端显示失败原因，其他文献仍可用。
5. 删除文献后，原文件、元数据和向量均不可再检索；已有历史回答保留文本，但引用打开时显示文件已删除。
6. 数据库页统计、搜索、分页、重试和权限控制可用。
7. 现有 Sweetness/Dual-Protein 回归测试通过，并新增 Encapsulation API、索引隔离、上传去重、删除一致性测试。

## 11. 埋点与成功指标

- `encapsulation_entry_click`、`encapsulation_question_submit`、`encapsulation_answer_success`、`encapsulation_no_evidence`、`encapsulation_upload`、`encapsulation_index_success/failure`、`encapsulation_document_download`。
- 首月关注：Encapsulation 问答成功率 ≥ 98%（排除外部 LLM 故障）、引用可打开率 ≥ 99%、索引任务成功率 ≥ 98%、P95 首字节 ≤ 5 秒。
- 质量抽检：至少 30 个包埋领域问题，人工评估“相关性、证据充分性、引用准确性、无幻觉”四项，作为上线门槛。

## 12. 里程碑与风险

### 里程碑

1. 方案评审：确认命名、权限、PDF 存储位置和模型配置。
2. 后端 MVP：独立索引、问答 API、上传/索引任务、文献 CRUD。
3. 前端 MVP：导航入口、问答页复用、数据库页和错误态。
4. 联调与质量评估：数据导入、隔离测试、30 题人工评估。
5. 灰度上线：管理员先导入并验证文献，再向研究组开放。

### 风险与应对

- 文献版权或敏感数据：上传提示与权限审计，提供删除能力。
- PDF 扫描件无文本：标记为需 OCR，MVP 可先失败并给出原因；后续接入 OCR。
- 向量模型维度或版本变化：在索引元数据记录模型名/维度，变更时新建索引并校验后切换。
- 知识域边界不清：强制 `domain` 隔离，提示词要求仅使用检索证据，定期抽检越界回答。

## 13. 待确认事项

- “Encapsulation”是否作为英文导航名称，同时页面标题是否需要显示中文“包埋”。
- 数据库入口是否仅管理员可见，还是所有登录用户可查看、管理员可编辑。
- 首批 PDF 来源、预计规模、版权审核责任人和 OCR 需求。
- Encapsulation 是否沿用当前本地 `BAAI/bge-small-zh-v1.5`，还是单独配置多语言模型。
- 文件预览采用浏览器内嵌 PDF，还是仅提供下载。
