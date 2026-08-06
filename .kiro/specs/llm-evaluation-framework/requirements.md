# 需求文档：LLM 评估框架

## 引言

本文档定义了 SweetSeek 智能科研问答系统的 LLM 评估框架（llm-evaluation-framework）的功能需求。该框架是一个后台研究工具集，用于支持硕士论文研究中的基座模型选择、性能评估和实验预测能力分析。

**研究背景**：
- 现有系统基于 RAG 架构，使用 DeepSeek 作为 LLM，BAAI/bge-small-zh-v1.5 作为嵌入模型
- 研究目标是优化和强化 SweetQA 功能，使其能够对实验进行预测和指导
- 当前阶段聚焦于基座模型的选择和评估

**目标用户**：硕士研究生、科研人员

**使用场景**：后台研究工具（命令行工具或 Jupyter Notebook），不需要前端界面

## 术语表

- **Evaluation_Framework**: 评估框架系统，负责模型测试、性能评估和结果分析
- **LLM**: Large Language Model，大语言模型（如 DeepSeek、GPT-4、Claude、Qwen 等）
- **Embedding_Model**: 嵌入模型，用于将文本转换为向量表示（如 BAAI/bge-small-zh-v1.5）
- **Test_Suite**: 测试集，包含标准化的食品科学/甜味研究领域问题和参考答案
- **Evaluation_Metric**: 评估指标，用于量化模型性能的度量（如准确性、相关性、响应时间等）
- **Model_Configuration**: 模型配置，包含 API 密钥、端点 URL、模型参数等
- **Benchmark_Report**: 基准测试报告，包含多个模型的对比评估结果
- **Experiment_Predictor**: 实验预测器，评估模型对实验结果的预测能力
- **Visualization_Engine**: 可视化引擎，生成科研论文用的图表（折线图、柱状图、雷达图等）

## 需求

### 需求 1：模型配置管理

**用户故事**：作为研究人员，我想要配置和管理多个 LLM 和嵌入模型，以便进行对比测试。

#### 验收标准

1. THE Evaluation_Framework SHALL 支持通过配置文件定义多个 LLM 模型（包括 API 类型、端点 URL、API 密钥、模型名称、参数）
2. THE Evaluation_Framework SHALL 支持通过配置文件定义多个嵌入模型（包括模型类型、模型路径、维度）
3. THE Evaluation_Framework SHALL 验证模型配置的完整性和有效性
4. THE Evaluation_Framework SHALL 支持模型配置的版本控制（通过 Git 或配置文件版本号）
5. WHEN 配置文件格式错误或缺少必需字段，THEN THE Evaluation_Framework SHALL 返回详细的错误信息

### 需求 2：测试集构建与管理

**用户故事**：作为研究人员，我想要构建和管理标准化的测试集，以便评估模型在食品科学领域的表现。

#### 验收标准

1. THE Evaluation_Framework SHALL 支持创建测试集，包含问题、参考答案、难度等级、问题类型等字段
2. THE Evaluation_Framework SHALL 支持从 JSON、CSV、YAML 格式导入测试集
3. THE Evaluation_Framework SHALL 支持测试集的版本管理（包括版本号、创建时间、修改历史）
4. THE Evaluation_Framework SHALL 支持按难度等级、问题类型筛选测试问题
5. THE Evaluation_Framework SHALL 支持测试集的导出（JSON、CSV、YAML 格式）
6. THE Evaluation_Framework SHALL 验证测试集的完整性（检查缺失字段、重复问题）

### 需求 3：批量模型测试

**用户故事**：作为研究人员，我想要自动化地对多个模型进行批量测试，以便高效地收集性能数据。

#### 验收标准

1. THE Evaluation_Framework SHALL 支持对配置的所有模型执行批量测试
2. WHEN 执行批量测试，THE Evaluation_Framework SHALL 对每个模型使用相同的测试集和参数
3. THE Evaluation_Framework SHALL 记录每个测试的详细日志（包括请求时间、响应时间、输入输出、错误信息）
4. THE Evaluation_Framework SHALL 支持设置随机种子以确保实验可重复性
5. WHEN 模型 API 调用失败，THE Evaluation_Framework SHALL 记录错误并继续测试其他模型
6. THE Evaluation_Framework SHALL 支持断点续传（测试中断后可从上次位置继续）
7. THE Evaluation_Framework SHALL 显示测试进度（已完成/总数、预计剩余时间）

### 需求 4：多维度性能评估

**用户故事**：作为研究人员，我想要从多个维度评估模型性能，以便全面了解模型的优劣。

#### 验收标准

1. THE Evaluation_Framework SHALL 计算准确性指标（包括 BLEU、ROUGE、BERTScore）
2. THE Evaluation_Framework SHALL 计算相关性指标（基于嵌入向量的余弦相似度）
3. THE Evaluation_Framework SHALL 计算响应时间指标（平均响应时间、P50、P95、P99）
4. THE Evaluation_Framework SHALL 计算成本指标（基于 token 使用量和 API 定价）
5. THE Evaluation_Framework SHALL 计算答案完整性指标（答案长度、关键信息覆盖率）
6. THE Evaluation_Framework SHALL 支持自定义评估指标（通过插件或配置）
7. THE Evaluation_Framework SHALL 为每个指标生成统计摘要（均值、中位数、标准差、最小值、最大值）

### 需求 5：实验预测能力评估

**用户故事**：作为研究人员，我想要评估模型对实验结果的预测准确性，以便选择最适合实验指导的模型。

#### 验收标准

1. THE Evaluation_Framework SHALL 支持创建实验预测测试集（包含实验条件、预期结果、实际结果）
2. WHEN 评估实验预测能力，THE Evaluation_Framework SHALL 比较模型预测与实际结果的一致性
3. THE Evaluation_Framework SHALL 计算预测准确率（正确预测数/总预测数）
4. THE Evaluation_Framework SHALL 分析预测偏差（预测值与实际值的差异分布）
5. THE Evaluation_Framework SHALL 评估模型提供的实验指导的可行性（通过专家评分或规则检查）

### 需求 6：可视化报告生成

**用户故事**：作为研究人员，我想要生成高质量的可视化图表，以便在学术论文中展示评估结果。

#### 验收标准

1. THE Evaluation_Framework SHALL 生成折线图（展示不同模型在各指标上的趋势）
2. THE Evaluation_Framework SHALL 生成柱状图（对比不同模型在单一指标上的表现）
3. THE Evaluation_Framework SHALL 生成雷达图（展示单个模型在多个维度上的综合表现）
4. THE Evaluation_Framework SHALL 生成散点图（展示指标之间的相关性）
5. THE Evaluation_Framework SHALL 生成热力图（展示模型在不同问题类型上的表现）
6. THE Evaluation_Framework SHALL 支持导出图表为高分辨率图片（PNG、SVG、PDF 格式）
7. THE Evaluation_Framework SHALL 支持自定义图表样式（颜色、字体、标签、图例）
8. THE Evaluation_Framework SHALL 生成符合学术论文规范的图表（包含标题、坐标轴标签、图例）

### 需求 7：评估报告导出

**用户故事**：作为研究人员，我想要导出详细的评估报告，以便在论文中引用和分析。

#### 验收标准

1. THE Evaluation_Framework SHALL 生成 Markdown 格式的评估报告（包含摘要、详细结果、图表链接）
2. THE Evaluation_Framework SHALL 生成 LaTeX 格式的评估报告（包含表格、图表引用、统计数据）
3. THE Evaluation_Framework SHALL 生成 Excel 格式的评估报告（包含原始数据、统计摘要、图表）
4. THE Evaluation_Framework SHALL 在报告中包含实验配置信息（模型配置、测试集版本、随机种子、评估时间）
5. THE Evaluation_Framework SHALL 在报告中包含可重复性说明（如何复现实验结果）
6. THE Evaluation_Framework SHALL 支持报告模板自定义（通过 Jinja2 或类似模板引擎）

### 需求 8：RAG 系统集成

**用户故事**：作为研究人员，我想要评估框架能够与现有 SweetSeek RAG 系统集成，以便测试完整的问答流程。

#### 验收标准

1. THE Evaluation_Framework SHALL 支持加载 SweetSeek 的向量数据库（ChromaDB）
2. THE Evaluation_Framework SHALL 支持使用 SweetSeek 的查询扩展器（SweetnessQueryExpander）
3. THE Evaluation_Framework SHALL 支持使用 SweetSeek 的证据分级系统（EvidenceRanker）
4. THE Evaluation_Framework SHALL 支持测试不同的 RAG 参数组合（similarity_top_k、similarity_threshold）
5. THE Evaluation_Framework SHALL 评估检索质量（检索到的文档与问题的相关性）
6. THE Evaluation_Framework SHALL 评估端到端的问答质量（包括检索和生成两个阶段）

### 需求 9：命令行界面

**用户故事**：作为研究人员，我想要通过命令行工具执行评估任务，以便快速进行实验。

#### 验收标准

1. THE Evaluation_Framework SHALL 提供命令行工具用于创建测试集
2. THE Evaluation_Framework SHALL 提供命令行工具用于配置模型
3. THE Evaluation_Framework SHALL 提供命令行工具用于执行批量测试
4. THE Evaluation_Framework SHALL 提供命令行工具用于生成评估报告
5. THE Evaluation_Framework SHALL 提供命令行工具用于查看历史评估结果
6. THE Evaluation_Framework SHALL 支持命令行参数覆盖配置文件中的设置
7. THE Evaluation_Framework SHALL 提供详细的帮助文档（通过 --help 参数）

### 需求 10：Jupyter Notebook 支持

**用户故事**：作为研究人员，我想要在 Jupyter Notebook 中进行交互式分析，以便灵活地探索评估结果。

#### 验收标准

1. THE Evaluation_Framework SHALL 提供 Python API 用于在 Notebook 中加载评估结果
2. THE Evaluation_Framework SHALL 支持在 Notebook 中直接显示可视化图表
3. THE Evaluation_Framework SHALL 提供示例 Notebook 展示常见的分析流程
4. THE Evaluation_Framework SHALL 支持在 Notebook 中进行增量分析（加载部分结果、添加新模型）
5. THE Evaluation_Framework SHALL 提供数据框（DataFrame）格式的结果，便于使用 pandas 进行分析

### 需求 11：结果存储与查询

**用户故事**：作为研究人员，我想要持久化存储评估结果，以便后续查询和对比。

#### 验收标准

1. THE Evaluation_Framework SHALL 将评估结果存储到本地数据库（SQLite 或 JSON 文件）
2. THE Evaluation_Framework SHALL 为每次评估生成唯一标识符（UUID）
3. THE Evaluation_Framework SHALL 支持按模型名称、测试集版本、评估时间查询历史结果
4. THE Evaluation_Framework SHALL 支持对比不同评估运行的结果
5. THE Evaluation_Framework SHALL 支持导出历史结果为 CSV 或 JSON 格式

### 需求 12：错误处理与日志

**用户故事**：作为研究人员，我想要详细的错误信息和日志，以便调试和分析问题。

#### 验收标准

1. WHEN API 调用失败，THE Evaluation_Framework SHALL 记录详细的错误信息（包括错误类型、错误消息、请求参数）
2. THE Evaluation_Framework SHALL 将所有日志输出到文件（支持按日期轮转）
3. THE Evaluation_Framework SHALL 支持配置日志级别（DEBUG、INFO、WARNING、ERROR）
4. THE Evaluation_Framework SHALL 在控制台显示关键进度信息（使用进度条或百分比）
5. WHEN 测试中断，THE Evaluation_Framework SHALL 保存当前进度以便恢复

## 非功能性需求

### 性能要求

1. THE Evaluation_Framework SHALL 支持并发测试多个模型（通过多线程或异步 IO）
2. THE Evaluation_Framework SHALL 在 100 个测试问题的情况下，完成单个模型的评估时间不超过 30 分钟（取决于 API 响应速度）

### 可扩展性要求

1. THE Evaluation_Framework SHALL 支持通过插件机制添加新的评估指标
2. THE Evaluation_Framework SHALL 支持通过插件机制添加新的可视化类型
3. THE Evaluation_Framework SHALL 支持通过配置文件添加新的 LLM 提供商

### 可维护性要求

1. THE Evaluation_Framework SHALL 使用模块化设计（模型管理、测试执行、评估计算、可视化生成分离）
2. THE Evaluation_Framework SHALL 提供完整的单元测试（覆盖率 > 80%）
3. THE Evaluation_Framework SHALL 提供详细的开发文档（包括架构设计、API 文档、贡献指南）

### 兼容性要求

1. THE Evaluation_Framework SHALL 兼容 Python 3.10+
2. THE Evaluation_Framework SHALL 兼容现有 SweetSeek 系统的依赖（LlamaIndex、ChromaDB、Flask）
3. THE Evaluation_Framework SHALL 支持在 Linux、macOS、Windows 系统上运行

## 技术约束

1. 使用 Python 作为主要开发语言
2. 使用现有 SweetSeek 系统的技术栈（LlamaIndex、ChromaDB）
3. 支持 OpenAI 兼容的 API 接口（DeepSeek、GPT-4、Claude、Qwen 等）
4. 使用 matplotlib、seaborn 或 plotly 进行可视化
5. 使用 pandas 进行数据处理和分析
6. 使用 pytest 进行单元测试

## 优先级

**P0（必须实现）**：
- 需求 1：模型配置管理
- 需求 2：测试集构建与管理
- 需求 3：批量模型测试
- 需求 4：多维度性能评估
- 需求 6：可视化报告生成
- 需求 7：评估报告导出
- 需求 9：命令行界面

**P1（高优先级）**：
- 需求 5：实验预测能力评估
- 需求 8：RAG 系统集成
- 需求 11：结果存储与查询
- 需求 12：错误处理与日志

**P2（中优先级）**：
- 需求 10：Jupyter Notebook 支持

## 成功标准

1. 能够成功配置和测试至少 3 个不同的 LLM 模型（DeepSeek、GPT-4、Qwen）
2. 能够生成包含至少 50 个问题的标准化测试集
3. 能够在 30 分钟内完成单个模型的完整评估（100 个问题）
4. 能够生成符合学术论文要求的高质量可视化图表（至少 5 种图表类型）
5. 能够导出 Markdown、LaTeX、Excel 三种格式的评估报告
6. 能够与现有 SweetSeek RAG 系统无缝集成
7. 评估结果具有可重复性（相同配置和随机种子产生相同结果）
