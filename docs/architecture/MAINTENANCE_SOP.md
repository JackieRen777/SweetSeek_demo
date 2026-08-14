# SweetSeek 维护 SOP

## 修改前

1. 确认工作分支和 `git status`。
2. 运行 `./scripts/maintenance/verify_cleanup.sh`。
3. 涉及论文或索引时，记录四个知识域的文件数和元数据条数。

## 代码修改

- 每个提交只处理一个边界：功能、测试、安全、存储、运维或文档。
- 不在同一提交中清理文件并修改 RAG 算法。
- 不提交 `.env`、`.env.production`、`ecs.env`、论文、模型、索引或日志。
- 不用静态“未引用”结果直接删除 Flask 路由或动态加载模块。

## 索引维护

```bash
python scripts/maintenance/incremental_all_kb.py
./scripts/maintenance/rebuild-index.sh 10
```

索引操作必须先 staging、验证后替换；不允许部署脚本重建或删除索引。

## 发布

```bash
./scripts/maintenance/verify_cleanup.sh
bash scripts/maintenance/deploy/deploy_ecs_oneclick.sh
```

发布后检查 `/api/health`、四个领域健康接口、一个普通问答和一个 SSE 问答。

## 回退

- 代码：回退对应 Git 提交。
- 索引：恢复维护脚本生成的独立索引备份。
- 论文：从数据盘备份恢复，禁止用 Git 恢复。
