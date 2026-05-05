# SweetSeek V1.0 日常维护 SOP

## 1. 关键目录
- `app.py`：后端入口
- `services/`：问答服务层
- `persistent_storage.py`：索引加载/构建/增量写入
- `scripts/maintenance/`：运维脚本主入口
- `scripts/archive/`：历史脚本归档（默认不参与运行）

## 2. 常用命令
### 检查模型状态
```bash
./scripts/maintenance/check_embedding_model.sh
```

### 稳健重建索引（推荐）
```bash
./scripts/maintenance/rebuild-index.sh 10
```

### 重启服务（本地/服务器按脚本内配置）
```bash
./scripts/maintenance/restart-server.sh
```

### 本地开发一键重启（127.0.0.1:5050）
```bash
./scripts/maintenance/restart-local-5050.sh
```

### 推送并可选部署
```bash
./scripts/maintenance/network/git_push.sh
```

### 直接部署
```bash
./scripts/maintenance/deploy/deploy.sh
```

## 3. 健康检查
```bash
python - <<'PY'
from app import app
c=app.test_client()
r=c.get('/api/health')
print(r.status_code)
print(r.get_json())
PY
```

## 4. 判定标准
- `embedding_model.mode=real`：检索质量正常
- `embedding_model.mode=placeholder`：说明模型不可用，仅可临时运行
- `status=healthy`：可正常对外使用
- `status=degraded`：可运行但需尽快修复

## 5. 变更原则
- 先小批量改动，再验证
- 先归档，后删除
- 对索引和模型目录先备份再做大改
