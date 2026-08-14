# SweetSeek

SweetSeek 是面向食品科学研究的全栈科研平台。系统由 React 前端、Flask API、FAISS 检索、统一论文数据库和 DeepSeek 兼容 LLM 接口组成。

## 正式功能

- 甜味科学 RAG 问答
- 甜味感知方程与可视化
- 甜味化合物数据库与文献列表
- 双蛋白、包埋、蛋白-多糖独立知识域问答
- 甜度机器学习预测
- AMBER 分子动力学流程生成器

## 架构

```text
frontend-react/                  React + Vite 前端
app.py                           Flask 入口与 API 路由
services/                        问答、LLM、化合物和 MD Builder 服务
persistent_storage.py            FAISS 索引加载、构建与增量写入
knowledge_paths.py               四个知识域的统一路径配置
SweetSeek_paper_database/        论文与 JSON 元数据，不进入 Git
faiss_db/ + storage_*/           可重建运行索引，不进入 Git
evaluation/                      固定问题集与 RAG 基准
scripts/maintenance/             唯一维护和部署入口
```

详细边界见 `docs/architecture/PROJECT_LAYOUT.md` 和 `docs/architecture/CODE_ASSET_AUDIT.md`。

## 本地开发

要求 Python 3.10+ 和 Node.js 20+。

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cd frontend-react
npm ci
cd ..
```

复制 `.env.example` 为未跟踪的 `.env`，填入 LLM 配置。论文根目录默认是仓库内的 `SweetSeek_paper_database/`，也可通过 `PAPER_DATABASE_ROOT` 指向仓库外数据盘。

启动后端：

```bash
./scripts/maintenance/restart-local-5001.sh
```

启动前端：

```bash
cd frontend-react
npm run dev
```

## 测试与清理验证

```bash
venv/bin/python -m pytest -q
cd frontend-react && npm test -- --run && npm run build
```

完整只读检查：

```bash
./scripts/maintenance/verify_cleanup.sh
```

## RAG 评测

第一阶段使用甜味域 60 题候选集。检索评测不调用回答模型，也不会创建或重建索引：

```bash
venv/bin/python -m evaluation.rag_benchmark --mode retrieval --limit 5
```

生成和端到端评测、领域终审与发布门禁见 `docs/architecture/RAG_EVALUATION.md`。未经领域审核的 `candidate` 题目不会进入正式评分。

## 文献和索引维护

统一论文目录：

```text
SweetSeek_paper_database/<domain>/papers/
SweetSeek_paper_database/<domain>/metadata.json
```

其中 `<domain>` 为 `sweetness`、`dual_protein`、`encapsulation` 或 `proteoglycan`。

```bash
# 所有知识域增量更新
python scripts/maintenance/incremental_all_kb.py

# 甜味知识域完整重建
./scripts/maintenance/rebuild-index.sh 10

# 双蛋白元数据补全
python scripts/maintenance/extract_dual_protein_metadata.py
```

论文、元数据、模型和索引均属于运行资产，不通过代码部署覆盖。

## 生产部署

唯一发布入口：

```bash
cp scripts/maintenance/deploy/ecs.env.example scripts/maintenance/deploy/ecs.env
# 编辑未跟踪的 ecs.env
bash scripts/maintenance/deploy/deploy_ecs_oneclick.sh
```

首次配置服务器时先运行 `bootstrap_ecs.sh`。完整说明见 `DEPLOY.md`。
