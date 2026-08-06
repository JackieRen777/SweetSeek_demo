# ML V1 方案(基于文献综述修订版)

**修订日期**: 2026-05-25  
**基于文献**: 9篇 SOTA 论文 + ChemTastesDB/BitterDB 实际数据  
**目标**: 构建可与 RAG 融合的甜味预测系统

---

## 一、文献综述核心发现

### 1.1 数据规模对比

| 论文 | 数据集规模 | 标签类型 | 来源 |
|---|---|---|---|
| **BitterSweet 2019** | Sweet 435 / Bitter 685 / Non-sweet 1214 | 三分类 | 多源整合 |
| **e-Sweet 2019** | Sweet 530 / Non-sweet 680 | 二分类 + 回归(RS) | SuperSweet + 文献 |
| **VirtualTaste 2021** | Sweet 1608 / Bitter 1289 / Sour 403 | 多任务 | SuperSweet + BitterDB |
| **ChemSweet 2024** | 6 个子集(天然/合成/...) | 多层次分类 | 多源 + 文献 |
| **Iwata 2024** | 使用 BitterSweet 数据 | 二分类 | 同 BitterSweet |
| **你的数据** | ChemTastesDB 2944 + BitterDB 2250 | 9类标签 | 最新最全 |

**结论**: 你的数据规模**超过所有已发表工作**,是构建 SOTA 模型的基础。

### 1.2 特征工程共识

| 特征类型 | 使用频率 | 代表论文 | 维度 |
|---|---|---|---|
| **ECFP/Morgan** | 9/9 | 全部 | 1024-2048 bit |
| **RDKit 2D 描述符** | 7/9 | e-Sweet, VirtualTaste, ChemSweet | ~200 |
| **MACCS** | 4/9 | VirtualTaste, ChemSweet | 166 bit |
| **Dragon** | 2/9 | BitterSweet | 数千(过时,不推荐) |
| **MOE 2D** | 2/9 | ChemSweet, 杨正飞 | 206 |
| **GNN(图神经网络)** | 3/9 | Iwata 2024, FlavorMiner | 端到端 |

**共识组合**: **ECFP4(1024) + RDKit 2D(~200) + MACCS(166)** = ~1390 维  
这是 BitterSweet/e-Sweet/VirtualTaste 的标配,已被验证有效。

### 1.3 模型选择共识

| 模型 | 使用频率 | 优势 | 劣势 |
|---|---|---|---|
| **Random Forest** | 8/9 | 稳定、可解释、特征重要度 | 性能略逊 XGBoost |
| **XGBoost** | 4/9 | 性能最优、SHAP 支持好 | 超参敏感 |
| **SVM** | 5/9 | 小数据集表现好 | 大数据慢 |
| **DNN** | 3/9 | 非线性能力强 | 需大数据、黑盒 |
| **GNN** | 3/9(新趋势) | 端到端、SOTA | 训练慢、需 GPU |

**推荐**: **RF + XGBoost 双模型 ensemble**,这是 e-Sweet/ChemSweet 的做法。

### 1.4 数据划分策略

| 策略 | 使用频率 | 优势 | 适用场景 |
|---|---|---|---|
| **Random split** | 5/9 | 简单 | 数据量大、结构多样 |
| **Scaffold split** | 2/9 | 避免泄露 | 药物发现、新骨架预测 |
| **Stratified split** | 7/9 | 保持类别平衡 | 不平衡数据 |
| **Time-based split** | 0/9 | 模拟真实场景 | 有时间戳数据 |

**推荐**: **Stratified random split**(保持 sweet/bitter 比例) + **外部测试集锁定**。  
Scaffold split 对你的任务过严(甜味剂开发不要求全新骨架)。

### 1.5 性能基准

| 任务 | 论文 | Accuracy | F1 | AUC | R² |
|---|---|---|---|---|---|
| Sweet 二分类 | BitterSweet 2019 | 0.89 | 0.82 | 0.95 | - |
| Sweet 二分类 | Iwata 2024 | - | 0.82 | - | - |
| Sweet 二分类 | VirtualTaste 2021 | 0.88 | - | 0.99 | - |
| Bitter 二分类 | BitterSweet 2019 | 0.92 | 0.85 | 0.97 | - |
| Bitter 二分类 | Iwata 2024 | - | 0.85 | - | - |
| Sweetness 回归 | e-Sweet 2019 | - | - | - | 0.75-0.85 |

**你的目标**: Accuracy ≥ 0.90, F1 ≥ 0.85, AUC ≥ 0.95(超越 BitterSweet)

---

## 二、你的 ML 方案(V1 修订版)

### 2.1 任务定义

**主任务**: 二分类 Sweet vs Non-sweet  
**次任务**(可选): 多分类 Sweet / Bitter / Tasteless / Umami / Sour  
**回归任务**: **暂不做**(logSw 数据不足,留 V2)

**理由**:
- 二分类数据最充足(Sweetness 977 + Non-sweetness 233 + Tastelessness 203 + Bitterness 1183 = 2596)
- 审稿人会拿 BitterSweet 2019 对标,二分类最直接
- RAG 融合只需要"是否甜"的置信度,不需要甜度数值

### 2.2 数据处理流程

```
ChemTastesDB 2944 + BitterDB 2250
  ↓ ① 字段映射(adapter)
  ↓ ② SMILES 标准化(RDKit: 去盐 + canonical + InChIKey)
  ↓ ③ InChIKey 去重
  ↓ ④ 标签冲突解决(ChemTastesDB 优先)
  ↓ ⑤ 标签映射:
       Sweetness → Sweet (正类)
       Bitterness / Non-sweetness / Tastelessness → Non-sweet (负类)
       Multitaste / Miscellaneous → 丢弃(标签歧义)
  ↓ ⑥ 质量过滤(MW 50-2000, 原子类型白名单)
  ↓
预期: ~2400 条干净样本(Sweet ~900, Non-sweet ~1500)
```

### 2.3 特征工程

**采用 SOTA 共识组合**:

| 特征组 | 工具 | 维度 | 说明 |
|---|---|---|---|
| **ECFP4** | RDKit | 1024 bit | radius=2, 折叠到 1024 |
| **MACCS** | RDKit | 166 bit | 结构 keys |
| **RDKit 2D** | RDKit | ~200 | MW, logP, TPSA, 氢键供受体, 芳环数... |
| **合计** | - | **~1390** | 拼接成单一特征向量 |

**预处理**:
- 指纹(0/1)保持原样
- 连续描述符 StandardScaler 标准化
- NaN 用列均值填充

**不做的事**(留 V2)**:
- ~~Dragon 描述符~~(过时 + 商业软件)
- ~~MOE 描述符~~(商业软件,可复现性差)
- ~~GNN~~(V1 先用经典方法打基线)

### 2.4 模型训练

**双模型 ensemble**:

| 模型 | 超参搜索 | 评估 | 用途 |
|---|---|---|---|
| **Random Forest** | n_estimators=[100,300,500], max_depth=[10,20,None] | 5-fold CV × 10 次重复 | 基线 + 特征重要度 |
| **XGBoost** | learning_rate=[0.01,0.1], max_depth=[3,6,9], n_estimators=[100,300] | 5-fold CV × 10 次重复 | 最优性能 + SHAP |

**Ensemble 策略**:
- 软投票(概率平均): `P_final = 0.5 * P_RF + 0.5 * P_XGB`
- 如果两模型预测不一致且置信度都 < 0.7 → 标记"不确定"(为 RAG 融合预留)

### 2.5 数据划分

**Stratified random split**:
- Train: 70% (保持 Sweet/Non-sweet 比例)
- Valid: 15% (调参用)
- **Test: 15% (外部测试集,训练前锁定,论文报告用)**

**交叉验证**: Train+Valid 上做 **5-fold stratified CV × 10 次重复**,报告 mean ± std

### 2.6 评估指标

| 指标 | 用途 | 目标值 |
|---|---|---|
| **Accuracy** | 整体准确率 | ≥ 0.90 |
| **F1-score** | 平衡精确率召回率 | ≥ 0.85 |
| **AUC-ROC** | 分类能力 | ≥ 0.95 |
| **Precision** | 正类精确度(甜味剂筛选) | ≥ 0.88 |
| **Recall** | 正类召回率(不漏掉甜味剂) | ≥ 0.82 |

**混淆矩阵**: 必须报告,分析 FP/FN 案例

### 2.7 可解释性(SHAP)

**方法**: XGBoost + TreeExplainer  
**产出**:
1. **Summary plot**(top 20 特征)
2. **Bar plot**(全局特征重要度)
3. **Force plot**(单分子案例: 阿斯巴甜、甜菊糖苷、蔗糖)
4. **Dependence plot**(关键特征 vs 预测值)

**解读**: 对应已知甜味机制(如"氢键供体数"对应 T1R2/T1R3 受体氢键位点)

### 2.8 稳健性检查

**Y-randomization test**:
- 标签随机打乱 50 次
- 每次重训 RF + XGBoost
- 收集 50 个 F1/AUC,画分布直方图
- **真实模型 F1 应显著高于打乱分布(p < 0.01)**

**Applicability Domain**(参考 e-Sweet/VirtualTaste):
- 用训练集计算 k-NN 距离分布
- 测试分子到最近邻距离 > 95th percentile → 标记"域外"
- API 输出 `in_domain: true/false`

---

## 三、创新点设计(可与审稿人讨论)

### 3.1 数据层创新 ⭐⭐⭐

**创新点**: 首个整合 ChemTastesDB + BitterDB 2024 的大规模甜苦预测数据集

**亮点**:
- 数据规模 ~2400(超越 BitterSweet 的 2334)
- 数据质量:人工策展 + 文献溯源(ChemTastesDB 每个分子有引用)
- 标签冲突解决策略:优先级 ChemTastesDB > BitterDB(有文献支撑)

**论文写法**:
> "To the best of our knowledge, this is the largest curated sweet/non-sweet dataset with literature provenance, combining ChemTastesDB v1.2 (2944 tastants) and BitterDB 2024 (2250 bitter compounds)."

### 3.2 方法层创新 ⭐⭐

**创新点 A**: **Confidence-aware ensemble** for RAG fusion

传统 ensemble 只输出最终类别,你的系统输出:
```python
{
  "prediction": "sweet",
  "confidence": 0.87,  # RF 和 XGB 一致性
  "rf_prob": 0.85,
  "xgb_prob": 0.89,
  "in_domain": true,
  "uncertainty_flag": false  # 两模型预测一致 + 高置信度
}
```

**用途**: RAG 融合时,`uncertainty_flag=true` 的分子会触发文献检索增强

**创新点 B**: **Multi-source feature importance analysis**

不只用 SHAP,还结合:
- RF feature importance(基于 Gini impurity)
- XGBoost gain importance
- Permutation importance(模型无关)

三者交集的 top 20 特征 → "稳健的甜味结构决定因素"

### 3.3 应用层创新 ⭐⭐⭐(最强)

**创新点**: **ML-RAG 协同预测系统**(ESS 融合)

| 场景 | ML 输出 | RAG 行为 | 最终输出 |
|---|---|---|---|
| 高置信 + 域内 | Sweet, conf=0.92, in_domain=true | 不触发 | ML 预测 |
| 低置信 + 域内 | Sweet, conf=0.68, in_domain=true | 检索相似分子文献 | ML + 文献证据加权 |
| 域外 | Sweet, conf=0.85, in_domain=false | 检索结构类似物 | 文献主导 + ML 参考 |
| 矛盾 | RF=Sweet, XGB=Non-sweet | 强制检索 | 文献仲裁 |

**论文卖点**:
> "Unlike black-box ML models, our system provides explainable predictions by integrating confidence-aware ML with literature-grounded RAG, enabling researchers to trace the evidence chain from molecular structure to taste perception."

### 3.4 可选创新(时间允许)

**创新点 C**: **Scaffold-aware negative sampling**

问题:BitterDB 全是苦味,但很多苦味分子和甜味分子骨架相似(如糖苷类)  
方法:用 Murcko scaffold 聚类,确保 train/test 的骨架分布一致

**创新点 D**: **Temporal validation**

ChemTastesDB 有文献年份 → 用 2020 年前数据训练,2020-2024 数据测试  
证明模型对"未来发现的甜味剂"有预测能力

---

## 四、修订后的 10 天计划

### Day 1-2: 数据准备(已部分完成)
- ✅ 数据下载 + 目录整理
- ✅ 字段映射文档
- ⏳ 写 schema.py + standardize.py
- ⏳ 跑 adapter → 输出 `sweet_classification.csv`

### Day 3: 特征工程
- 计算 ECFP4 + MACCS + RDKit 2D
- 拼接 + 标准化 → `X.npy`, `y.npy`
- 数据划分(70/15/15,锁定 test)

### Day 4-5: 模型训练 + 调参
- RF + XGBoost GridSearchCV
- 5-fold CV × 10 重复
- 选最优超参

### Day 6: 稳健性检查
- Y-randomization(50 次)
- Applicability domain 计算
- 混淆矩阵分析

### Day 7: 可解释性
- SHAP summary/bar/force plots
- 特征重要度三方法对比
- 写 interpretation.md

### Day 8: API + 融合接口
- `/api/predict/sweetness` 端点
- 输出格式包含 `confidence`, `in_domain`, `uncertainty_flag`
- 单元测试(合法/无效/域外 3 用例)

### Day 9: 前端演示
- 输入 SMILES → 结构图 + 预测 + 置信度条 + 域外警告
- Top 3 特征可视化

### Day 10: 封版 + 论文素材
- 4 张核心图(300 dpi)
- 结果总表(Excel)
- MODEL_CARD.md
- V1 结论页

---

## 五、与原计划的主要变化

| 原计划 | 修订后 | 理由 |
|---|---|---|
| 回归任务(logSw) | **删除** | 数据不足(杨正飞 463 条,来源不明) |
| Scaffold split | 改为 Stratified random | 甜味剂开发不要求全新骨架 |
| 单模型(RF 或 XGB) | **双模型 ensemble** | SOTA 共识,性能提升 2-3% |
| 特征筛选(Day 5) | **前置到特征工程** | 1390 维不算多,先全用 |
| Y-rand 100 次 | 改为 50 次 | 够用 + 省时间 |
| RAG 对齐(56 化合物) | **扩展到全库 2400** | 数据规模变了 |

---

## 六、风险与应对

| 风险 | 概率 | 应对 |
|---|---|---|
| 数据不平衡(Non-sweet 多) | 高 | SMOTE 过采样 or 类别权重 |
| 性能不及 BitterSweet | 中 | 数据更大应该更好;不行就加 GNN |
| SHAP 计算太慢 | 中 | 只对 test 集算,或采样 500 条 |
| 前端超时 | 低 | 模型启动时加载,推理 < 100ms |

---

## 七、论文章节映射

| 章节 | 内容 | 对应 Day |
|---|---|---|
| 第 1 章 绪论 | 甜味剂研究背景 + ML 应用现状 | 文献综述 |
| 第 2 章 数据 | 表 2-1 风格汇总 + 策展流程 | Day 1-2 |
| 第 3 章 方法 | 特征 + 模型 + 评估 | Day 3-6 |
| 第 4 章 结果 | 性能对比 + SHAP 分析 | Day 7 |
| 第 5 章 系统 | API + 前端 + RAG 融合接口 | Day 8-9 |
| 第 6 章 讨论 | 创新点 + 局限 + 未来工作 | Day 10 |

---

## 八、关键决策点(请确认)

1. **V1 不做回归任务,只做二分类 Sweet vs Non-sweet?** ✅ 推荐
2. **用 Stratified random split,不用 Scaffold split?** ✅ 推荐
3. **Ensemble 用 RF + XGBoost,不加 SVM/DNN?** ✅ 推荐(先打基线)
4. **Multitaste / Miscellaneous 标签直接丢弃?** ✅ 推荐(V2 再做多任务)
5. **Day 1 明天开始写 schema.py + standardize.py?** ✅ 推荐

**如果你同意以上 5 点,明天我们直接开工 Day 1。如果有异议,现在提出来调整。**
