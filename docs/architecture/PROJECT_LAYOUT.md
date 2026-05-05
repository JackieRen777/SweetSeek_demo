# FCN_SweetSeek 项目结构（V1.0 现状整理）

## 核心运行路径
- `app.py`: Flask 入口 + API 路由
- `services/`: 问答编排、依赖注入、化合物服务
- `persistent_storage.py`: RAG 索引加载/构建/增量写入
- `incremental_indexer.py`: 文献增量索引入口
- `config.py`: 配置层（端口、索引目录、模型等）

## 数据与索引目录
- `sweet_related_paper/`: 文献源数据
- `faiss_db/`: 当前检索索引持久化目录（PERSIST_DIR 默认）
- `chroma_db_v3/`: 元数据目录（metadata.json）
- `storage_dual_protein/`: 双蛋白模块索引

## 前端
- `frontend-react/`: React 前端工程

## 运维与维护脚本
- `scripts/rebuild_local_index.py`: 本地强制重建索引脚本
- `scripts/maintenance/`: 部署/重启/回滚/诊断脚本

## 文档
- `docs/`: 项目文档
- `docs/reports/`: 历史报告归档

## 待清理候选（不影响运行）
- 根目录历史临时文件与重复报告
- 无引用的旧部署脚本
- 明显过时的备份索引目录（需确认后删）
