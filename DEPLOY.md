# SweetSeek ECS 部署

## 边界

- 代码目录：`SERVER_PATH`，由部署脚本同步。
- 论文目录：`PAPER_DATABASE_ROOT`，独立数据盘，不随代码发布。
- 索引目录：`faiss_db`、`storage_*`，服务器本地维护，不随代码发布。
- 环境配置：服务器 `.env` 与本地 `ecs.env`，均不得进入 Git。
- 前端：本地构建 `frontend-react/dist` 后同步到服务器。
- 后端：单进程 Gunicorn，监听 `127.0.0.1:5001`，由 Nginx 代理。

## 首次部署

```bash
cp scripts/maintenance/deploy/ecs.env.example scripts/maintenance/deploy/ecs.env
```

编辑 `ecs.env`，设置服务器地址、SSH 用户、代码目录和域名。认证使用 SSH 密钥，不在脚本中保存密码。

```bash
bash scripts/maintenance/deploy/bootstrap_ecs.sh
bash scripts/maintenance/deploy/deploy_ecs_oneclick.sh
```

服务器代码目录中的 `.env` 至少配置：

```dotenv
DEEPSEEK_API_KEY=replace-with-secret
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
PAPER_DATABASE_ROOT=/data/sweetseek/SweetSeek_paper_database
EMBED_MODEL_TYPE=modelscope
EMBED_MODEL_NAME=BAAI/bge-small-zh-v1.5
```

## 日常发布

```bash
./scripts/maintenance/verify_cleanup.sh
bash scripts/maintenance/deploy/deploy_ecs_oneclick.sh
```

发布脚本会构建前端、同步代码、安装依赖、重启 Gunicorn、更新 Nginx 并执行健康检查。它明确排除论文、索引、模型缓存、虚拟环境、日志和私有环境文件。

## 验证

```bash
curl -fsS http://127.0.0.1:5001/api/health
curl -N -X POST http://127.0.0.1:5001/api/ask_stream \
  -H 'Content-Type: application/json' \
  -d '{"question":"甜味受体如何识别甜味剂？"}'
```

Nginx 的 `/api/` 必须关闭代理缓冲并保留 300 秒读写超时，确保 SSE 正常输出。

## 回退

代码回退使用 Git 提交；论文和索引不参与代码回退。索引更新脚本必须使用 staging 目录并在成功后原子替换，禁止在发布脚本中删除现有索引。
