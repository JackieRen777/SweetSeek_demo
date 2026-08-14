## SweetSeek 迁移到新 ECS（8.136.8.223）

### 0) 一次性准备
```bash
cd /Users/jackieren/Desktop/FCN_SweetSeek
cp scripts/maintenance/deploy/ecs.env.example scripts/maintenance/deploy/ecs.env
chmod +x scripts/maintenance/deploy/bootstrap_ecs.sh
chmod +x scripts/maintenance/deploy/deploy_ecs_oneclick.sh
```

### 1) 初始化新 ECS（只做一次）
```bash
bash scripts/maintenance/deploy/bootstrap_ecs.sh
```

论文数据库固定放在 `/data/sweetseek/SweetSeek_paper_database`，不会随代码部署同步或删除。

### 2) 一键上线（以后每次都用这条）
```bash
bash scripts/maintenance/deploy/deploy_ecs_oneclick.sh
```

### 3) 切换域名
把 `sweetseek.top` 的 A 记录改到 `8.136.8.223`，TTL 设为 60 秒。

### 4) 切换顺序（不要先删旧机）
1. 新 ECS 上线并验收
2. 切 DNS
3. 观察 24-48 小时
4. 再停旧机 `8.136.8.223`
5. 最后删除旧机

### 5) 回退（紧急）
把 `sweetseek.top` A 记录改回旧 IP `8.136.8.223`。
