# SweetDatabase 门户验收报告

验收日期：2026-09-11
数据版本：`sweet_database_source_20260910.xlsx`
工作表：`current_sweet_compounds_1296`

## 验收结论

SweetDatabase 完整门户框架已通过本地验收。当前版本适合用于确认整体信息架构、视觉层级和核心工作流；数据不足的模块使用明确空状态，不生成或推断不存在的数据。数据模型保留 `entityType`，没有把产品永久限定为小分子数据库，后续可加入甜味蛋白。

## 四阶段验收

### 阶段 1：产品入口与信息架构

- 通过：Database 使用独立的 SweetDatabase 产品头部。
- 通过：提供 Home、Browse、Evidence、Literature、Statistics、Downloads、Data Guide。
- 通过：提供返回 SweetSeek 的入口，避免双重导航。
- 通过：桌面端与 390 px 移动端没有页面级横向溢出。

### 阶段 2：数据浏览与检索

- 通过：首页搜索支持名称、稳定 ID、分子式、InChIKey、PubChem CID。
- 通过：搜索词和证据等级写入 URL 并带入 Browse。
- 通过：详情页区分工作簿字段与 PubChem 外部补充字段。
- 通过：工作簿 1,296 行、1,296 个唯一 ID，与前端生成数据一致。

### 阶段 3：证据、质量与可追溯性

- 通过：公开 R1-R4 证据等级和定义。
- 通过：公开工作簿中的 170 条人工复核标记。
- 通过：PubChem 校验获得 878 条匹配，其中 877 条完全通过交叉校验。
- 通过：发现外部校验冲突时不覆盖源数据，详情页显示 Manual review。
- 通过：下载入口保留但 3 个下载动作全部禁用。

### 阶段 4：工程与界面质量

- 通过：Vitest 11 个测试文件、42 项测试全部通过。
- 通过：TypeScript 与 Vite 生产构建通过。
- 通过：改动范围 ESLint 通过，`git diff --check` 通过。
- 通过：实际浏览器验证首页、组合搜索、Data Guide、下载权限、问题记录和返回入口。
- 通过：浏览器控制台无警告或错误。

## 当前数据缺失

| 数据项 | 缺失或未覆盖 | 影响 |
| --- | ---: | --- |
| PubChem 匹配 | 418 条 | 无法展示已验证的外部结构与属性 |
| `heavy_atom_count` | 3 条 | 个别结构统计字段不完整 |
| `canonical_tautomer_inchikey` | 1,296 条 | 当前版本不能按标准互变异构体键归并 |
| 定量甜度 | 1,296 条 | 不能进行甜度数值比较或排序 |
| 逐条实验条件 | 1,296 条 | 不能解释测量体系、浓度、基准和感官条件 |
| DOI / PMID 与证据摘录 | 1,296 条 | Literature 暂时只能展示空状态和待补字段 |
| 食品应用、受体证据、安全与法规 | 全部未提供 | 对应专业模块不能发布实质性结论 |
| 甜味蛋白 | 0 条 | 数据模型已预留，等待后续版本导入 |

完整缺失 ID 和 170 条工作簿人工复核 ID 保存在：

`frontend-react/src/features/database/data/quality.generated.json`

## 需要优先人工复核的外部校验冲突

`CMP_VEXZGXHMUGYJMC-UHFFFAOYSA-N`

- 工作簿名称：Beryllium chloride
- 工作簿结构字段：HCl / `Cl`
- PubChem CID：313
- PubChem IUPAC 名称：chlorane
- 处理方式：源字段未被覆盖；门户中不显示为 Released，统一显示 Manual review 与 discrepancy 警告。

## 下一数据版本建议

1. 先解决身份冲突、3 条重原子缺失和 418 条未匹配记录。
2. 增加 assertion 级表：`compound_id`、证据类型、数值、单位、基准、实验条件、原文摘录、DOI/PMID、复核状态。
3. 建立独立实体表支持 protein，并为化合物和蛋白共用稳定 ID、证据和文献关系。
4. 数据补齐后再开放 Literature 内容、定量比较、应用、安全法规和下载功能。
