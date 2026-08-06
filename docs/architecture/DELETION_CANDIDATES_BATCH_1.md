# 删除候选清单（Batch 1）

目标：仅清理非运行时必须文件，不影响 1.0 核心问答能力。

## A. 高置信可删（几乎零风险）
1. `.git/index 2`
2. `.git/index 3`
3. `chroma_db_v3/metadata.json.bak`

原因：
- `index 2/index 3` 为 Git 索引异常副本，不属于正常仓库结构。
- `metadata.json.bak` 为备份副本，正式运行读取的是 `metadata.json`。

## B. 可删但建议确认（体积较大/历史备份）
1. `faiss_db.bak_20260413160055/`
2. `chroma_db.tar.gz`
3. `papers.tar.gz`

原因：
- 均为历史备份或压缩包，不参与在线服务实时读取。
- 删除可释放磁盘，但会失去本地快速回滚介质。

## C. 暂缓（先不删）
1. `Dual_Protein_related_paper/`
2. `storage_dual_protein/`
3. `food_research_data/`

原因：
- 可能关联你正在扩展的双蛋白问答功能。

