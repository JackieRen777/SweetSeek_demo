# SweetSeek 项目边界

## 核心源码

- `app.py`：Flask 应用和兼容 API。
- `services/`：业务服务与问答编排。
- `persistent_storage.py`：FAISS 索引生命周期。
- `knowledge_paths.py`：知识域路径的唯一来源。
- `frontend-react/src/`：九个正式前端功能。
- `tests/`、`frontend-react/src/**/*.test.*`：回归保护。

## 不可再生或生产敏感资产

- `SweetSeek_paper_database/`：论文原文和 JSON 元数据。
- `models/`：本地嵌入模型。
- `data/`：甜味化合物与 ML 模型输入/产物。
- `results/`：论文图表和已确认评测结果。

这些目录不能按“未导入源码”判断为垃圾。

## 可再生运行资产

- `faiss_db/`：甜味知识域索引。
- `storage_dual_protein/`、`storage_encapsulation/`、`storage_proteoglycan/`：领域索引。
- `frontend-react/dist/`、`frontend-react/node_modules/`、Python/测试缓存和日志。

可再生不代表可在生产发布时删除；索引只由维护命令更新。

## 运维入口

- `scripts/maintenance/deploy/deploy_ecs_oneclick.sh`：唯一生产发布入口。
- `scripts/maintenance/deploy/bootstrap_ecs.sh`：首次服务器初始化。
- `scripts/maintenance/restart-local-5001.sh`：本地后端启动。
- `scripts/maintenance/incremental_all_kb.py`：知识库增量更新。
- `scripts/maintenance/verify_cleanup.sh`：只读质量门禁。
