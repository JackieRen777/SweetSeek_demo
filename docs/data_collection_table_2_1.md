# 表 2-1 数据初步收集情况

> 生成时间:2026-05-26(Day 2 merge 完成后)
> 数据源:ChemTastesDB v1.2 + BitterDB 2024
> 标准化方法:RDKit 去盐 + 中和电荷 + 规范互变异构 + InChIKey 计算
> 处理脚本:`scripts/data/{fetch_*,merge}.py`,产物 `data/processed/master.parquet`

---

## 1. 数据源规模总览(Table 2-1)

| 数据源 | 原始记录 | 含 SMILES | 标准化成功 | 库内去重后 | 跨库去重后保留 |
|---|---:|---:|---:|---:|---:|
| ChemTastesDB v1.2 | 2947 | 2944 | 2930 | 2683 | 2683(优先保留) |
| BitterDB 2024 | 2250 | 2250 | 2228 | 2128 | 1478(扣除 650 重复) |
| **合计** | **5197** | **5194** | **5158** | **4811** | **4161** |

- **跨库重复**(同 InChIKey 在两库均出现):**650** 个分子 → 以 ChemTastesDB 标签为准
- **全库去重后**:**4161** 个分子(进入下一步标签映射)

---

## 2. 按味觉类别细分(库内去重后,跨库合并前)

| 味觉类别 | ChemTastesDB | BitterDB | 合计 |
|---|---:|---:|---:|
| Sweetness | 881 | 0 | 881 |
| Bitterness | 1085 | 1478 | 2563 |
| Non-sweetness | 227 | 0 | 227 |
| Tastelessness | 191 | 0 | 191 |
| Multitaste | 99 | 0 | 99 |
| Umaminess | 81 | 0 | 81 |
| Miscellaneous | 77 | 0 | 77 |
| Sourness | 35 | 0 | 35 |
| Saltiness | 7 | 0 | 7 |
| **合计** | **2683** | **1478** | **4161** |

> 说明:`Bitterness` 这一行同时包含 ChemTastesDB 自报的苦味分子(1085)和 BitterDB 独有的苦味分子(1478,已扣除 650 个跨库重复)。两库 `Bitterness` 标签现已统一拼写。

---

## 3. V1 二分类标签映射(经 ChemTastesDB 优先 + 跨库去重后)

**映射规则**(详见 [docs/ml_v1_plan_revised.md](ml_v1_plan_revised.md)):

| 原始类别 | V1 标签 | 处理 |
|---|---|---|
| Sweetness | **Sweet**(正类,is_sweet=1) | 保留 |
| Bitterness / Non-sweetness / Tastelessness | **NonSweet**(负类,is_sweet=0) | 保留 |
| Multitaste / Miscellaneous | — | 丢弃(标签歧义) |
| Umaminess / Sourness / Saltiness | — | 丢弃(V1 不涉及) |

| V1 标签 | 分子数 |
|---|---:|
| **Sweet(正类)** | **881** |
| **NonSweet(负类)** | **2981** |
| 丢弃:Multitaste/Miscellaneous(歧义) | 176 |
| 丢弃:Umami/Sour/Salty(其他味觉) | 123 |
| **进入质量过滤前的可用样本** | **3862** |

**类别不平衡比** Sweet : NonSweet = **1 : 3.38**(下游需 `class_weight='balanced'` 或 `scale_pos_weight≈3.38`)

---

## 4. 质量过滤(MW 范围 + 原子白名单)

**白名单原子**:H, C, N, O, P, S, F, Cl, Br, I(在标准化阶段已过滤)
**分子量范围**:50 ≤ MW ≤ 2000 Da

| 过滤步骤 | 输入 | 丢弃 | 保留 |
|---|---:|---:|---:|
| MW < 50 | 3862 | 4 | 3858 |
| MW > 2000 | 3858 | 12 | 3846 |
| **最终保留** | — | **16** | **3846** |

---

## 5. 最终训练集统计(`data/processed/master.parquet`)

| 项 | 值 |
|---|---:|
| **总行数** | **3846** |
| Sweet(正类) | 881(22.9%) |
| NonSweet(负类) | 2965(77.1%) |
| 不平衡比(NonSweet : Sweet) | 3.37 |
| 唯一 InChIKey 数 | 3846(无重复) |
| 来自 ChemTastesDB | 2381(61.9%) |
| 来自 BitterDB | 1465(38.1%) |

> 注:NonSweet 从 2981 降到 2965 是因为质量过滤丢了 16 个超 MW 范围的分子(Sweet 正类不受影响)。

---

## 6. SMILES 标准化失败原因(共 39 行被丢弃)

| 失败原因 | ChemTastesDB | BitterDB | 合计 |
|---|---:|---:|---:|
| no_smiles(原表无 SMILES) | 3 | 0 | 3 |
| disallowed_atoms(含金属) | 14 | 22 | 36 |
| **合计** | **17** | **22** | **39** |

含金属分子(Hg/Mg/Fe/Cu/Zn/Mn/Ba/Be/Ca/K/Li/Na/Si/Sr 等)按传统 QSAR 共识丢弃 — 这些原子在 ECFP/MACCS 指纹中表征不稳定,且训练集占比 < 1%,丢弃不影响整体表现。

---

## 7. 与已发表工作的数据规模对比

| 工作 | 年份 | 数据规模(Sweet / NonSweet) | 标签维度 |
|---|---|---|---|
| BitterSweet | 2019 | 435 / 1899(Bitter 685 + Non-sweet 1214) | 二分类×2 |
| e-Sweet | 2019 | 530 / 680 | 二分类 + 回归 |
| VirtualTaste | 2021 | 1608 / — | 多任务(三味觉) |
| ChemSweet | 2024 | 6 个子集(规模未统一) | 多层次分类 |
| **本工作 V1** | **2026** | **881 / 2965** | **二分类** |

**亮点**:
- 总样本量 **3846**,**超过 BitterSweet(2334)、e-Sweet(1210)** 的二分类训练集
- NonSweet 类容量充足(2965),覆盖苦味 / 无味 / 非甜的三种异质负样本,有助于模型学习真正的"甜味决定结构"而非"非甜的偶然结构"
- 数据来源**全部有文献溯源**(ChemTastesDB 每分子有引用代码)
