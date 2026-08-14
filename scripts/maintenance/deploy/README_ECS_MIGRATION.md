# ECS 迁移检查表

1. 从 `ecs.env.example` 创建未跟踪的 `ecs.env`，使用 SSH 密钥认证。
2. 在目标服务器的数据盘准备 `SweetSeek_paper_database` 和已有索引。
3. 执行 `bootstrap_ecs.sh` 初始化依赖和目录。
4. 执行 `deploy_ecs_oneclick.sh` 发布代码并完成健康检查。
5. 验证九个前端功能、四个知识域健康接口和 SSE 流式回答。
6. 切换 DNS 后观察至少一个发布周期，再停用旧服务器。

代码部署不会同步或删除论文、元数据、模型、索引和私有环境文件。回退代码使用 Git，数据与索引使用独立备份。
