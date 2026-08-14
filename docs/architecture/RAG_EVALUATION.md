# RAG 评测与发布门禁

## 目标

甜味域使用 60 题候选集建立可重复的检索、生成和端到端基准。`candidate` 题目只用于准备标注；只有经过领域审核并改为 `approved` 的题目参与正式聚合指标与发布门禁。

## 标注流程

1. 运行一次检索评测并保存上下文快照：

   ```bash
   venv/bin/python -m evaluation.rag_benchmark \
     --mode retrieval \
     --context-output evaluation/contexts/sweet_v1.json
   ```

2. 从最新报告生成审核包：

   ```bash
   venv/bin/python -m evaluation.prepare_annotations \
     evaluation/reports/<retrieval-report>.json \
     evaluation/contexts/sweet_review.json
   ```

3. 领域审核人确认相关论文、证据原文、答案要点、禁止臆测项和拒答预期。
4. 将确认结果写回 `evaluation/questions/sweet_gold_v1.json`，把相应题目的 `annotation_status` 改为 `approved`。
5. 提交黄金标注；不要提交运行报告、上下文快照或包含完整模型回答的审核包。

稳定文档 ID 来自规范化论文路径，稳定 chunk ID 优先使用索引 node ID。论文移动或重新分块后必须重新核对标签。

## 三种评测模式

```bash
# 只测查询处理和检索，不调用回答模型
venv/bin/python -m evaluation.rag_benchmark --mode retrieval

# 使用冻结上下文测试生成；默认重复三次
venv/bin/python -m evaluation.rag_benchmark \
  --mode generation \
  --contexts evaluation/contexts/sweet_v1.json \
  --judge

# 完整问答；默认重复三次
venv/bin/python -m evaluation.rag_benchmark --mode end_to_end --judge
```

使用 `--baseline <report.json>` 计算版本差异和发布门禁，使用 `--limit N` 做本地冒烟。Judge 只有在 LLM 已配置且题目为 `approved` 时执行。输入和输出 Token 单价通过 `RAG_EVAL_INPUT_COST_PER_MILLION`、`RAG_EVAL_OUTPUT_COST_PER_MILLION` 配置；未配置时成本只记录为零，不满足完整成本门禁。

## 指标解释

- 检索：Document Recall@10、Evidence Recall@20、MRR、NDCG@10。
- 答案：答案要点覆盖、固定 Judge 的忠实度和完整性、无答案拒答 F1。
- 引用：引用是否来自正确论文、是否覆盖结论、模型引用与系统自动追加引用分别记录。
- 性能：P50/P95、标准差、Token 数、模型调用与估算成本。
- 综合分：仅在所有维度可计算时生成，不能覆盖任何硬门禁失败。

页码和章节完整率在现有索引中只作诊断；结构化解析与新索引完成后再加入正式得分。
