# ECS 迁移检查表

1. 从 `ecs.env.example` 创建未跟踪的 `ecs.env`，仅允许 SSH 密钥和当前 IP 白名单。
2. 修复本地 FileProvider 占位文件并确保至少有 20 GiB 可用空间。
3. Gate 1 从干净且已推送的 `main` 构建，分域上传 512 维索引并完成两小时观察：

   ```bash
   scripts/maintenance/deploy/deploy_ecs_oneclick.sh gate1
   ```

4. Gate 1 通过后，在 `ecs.env` 配置三组真实 Docking 夹具，再发布 Gate 2：

   ```bash
   scripts/maintenance/deploy/deploy_ecs_oneclick.sh gate2
   ```

5. 任一阶段需要人工回切时执行：

   ```bash
   scripts/maintenance/deploy/rollback_release.sh --confirm
   ```

发布脚本仅接受与 `origin/main` 完全一致的干净本地 `main`，功能分支或包含未提交修改的工作区会被拒绝。代码、Web venv、计算环境和四域索引均使用版本目录；生产只通过软链接切换。
5. 验证九个前端功能、四个知识域健康接口和 SSE 流式回答。
6. 切换 DNS 后观察至少一个发布周期，再停用旧服务器。

代码部署不会同步或删除论文、元数据、模型、索引和私有环境文件。回退代码使用 Git，数据与索引使用独立备份。
