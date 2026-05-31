"""Export plotting-ready Excel: one sheet per paper figure.

Output: reports/sweetseek_v1_plotting_data.xlsx
- README sheet with figure-by-figure plotting recipe
- 11 data sheets, each tidy-format, ready to paste into Origin/Prism/Excel.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors

RDLogger.DisableLog("rdApp.*")

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
RESULTS_DIR = REPO_ROOT / "results"
REPORTS_DIR = REPO_ROOT / "reports"
SRC_XLSX = REPORTS_DIR / "sweetseek_v1_data.xlsx"
OUT_XLSX = REPORTS_DIR / "sweetseek_v1_plotting_data.xlsx"


def fig_2_1_pipeline() -> pd.DataFrame:
    """Long-format: stage × source × n_molecules."""
    rows = [
        ("1_Raw",            "ChemTastesDB", 2947),
        ("1_Raw",            "BitterDB",     2250),
        ("1_Raw",            "Total",        5197),
        ("2_Standardized",   "ChemTastesDB", 2930),
        ("2_Standardized",   "BitterDB",     2228),
        ("2_Standardized",   "Total",        5158),
        ("3_WithinDedup",    "ChemTastesDB", 2683),
        ("3_WithinDedup",    "BitterDB",     2128),
        ("3_WithinDedup",    "Total",        4811),
        ("4_CrossDedup",     "ChemTastesDB", 2683),
        ("4_CrossDedup",     "BitterDB",     1478),
        ("4_CrossDedup",     "Total",        4161),
        ("5_LabelFiltered",  "Total",        3862),
        ("6_MWFiltered",     "Total",        3846),
    ]
    return pd.DataFrame(rows, columns=["stage", "source", "n_molecules"])


def fig_2_2_taste_distribution(src: pd.ExcelFile) -> pd.DataFrame:
    df = pd.read_excel(src, sheet_name="02_taste_distribution")
    return df


def fig_2_3_property_distributions() -> pd.DataFrame:
    """Per-molecule physicochemical properties + is_sweet label.
    Plot: histogram or violin grid (MW / LogP / TPSA / HBA / HBD) by class.
    """
    master = pd.read_parquet(DATA_DIR / "processed" / "master.parquet")
    rows = []
    for _, row in master.iterrows():
        mol = Chem.MolFromSmiles(row["smiles_canonical"])
        if mol is None:
            continue
        rows.append({
            "mol_id": row["mol_id"],
            "is_sweet": int(row["is_sweet"]),
            "class": "Sweet" if row["is_sweet"] == 1 else "NonSweet",
            "MW": Descriptors.MolWt(mol),
            "LogP": Descriptors.MolLogP(mol),
            "TPSA": Descriptors.TPSA(mol),
            "NumHBA": Descriptors.NumHAcceptors(mol),
            "NumHBD": Descriptors.NumHDonors(mol),
            "NumRotBonds": Descriptors.NumRotatableBonds(mol),
            "NumAromaticRings": Descriptors.NumAromaticRings(mol),
        })
    return pd.DataFrame(rows)


def fig_2_4_lit_comparison(src: pd.ExcelFile) -> pd.DataFrame:
    return pd.read_excel(src, sheet_name="14_lit_comparison")


def fig_3_1_feature_blocks(src: pd.ExcelFile) -> pd.DataFrame:
    return pd.read_excel(src, sheet_name="07_descriptors_block")


def fig_3_2_split_summary(src: pd.ExcelFile) -> pd.DataFrame:
    return pd.read_excel(src, sheet_name="08_split_summary")


def fig_4_top12_descriptors(src: pd.ExcelFile) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Top-12 most discriminative RDKit2D descriptors (by |mean_sweet - mean_nonsweet|).
    Returns (long_format_for_violin, summary_table).
    """
    stats = pd.read_excel(src, sheet_name="09_descriptor_stats")
    top12 = stats.sort_values("abs_mean_diff", ascending=False).head(12).reset_index(drop=True)

    feature_names = json.loads((DATA_DIR / "features" / "feature_names.json").read_text())
    X = np.load(DATA_DIR / "features" / "X.npy")
    y = np.load(DATA_DIR / "features" / "y.npy")

    name_to_idx = {n: i for i, n in enumerate(feature_names)}
    long_rows = []
    for _, row in top12.iterrows():
        desc = row["descriptor"]
        full_name = f"RDKit2D::{desc}"
        if full_name not in name_to_idx:
            continue
        col = name_to_idx[full_name]
        for i in range(X.shape[0]):
            long_rows.append({
                "descriptor": desc,
                "class": "Sweet" if y[i] == 1 else "NonSweet",
                "value": float(X[i, col]),
            })
    long_df = pd.DataFrame(long_rows)
    summary = top12[["descriptor", "mean_sweet", "mean_nonsweet", "abs_mean_diff"]]
    summary = summary.assign(rank=range(1, len(summary) + 1))
    return long_df, summary


def fig_5_1_hyperparameter_heatmaps(src: pd.ExcelFile) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pivot CV grid into RF and XGB heatmaps."""
    cv = pd.read_excel(src, sheet_name="10_cv_grid")
    cv["params_dict"] = cv["params"].apply(json.loads)

    rf = cv[cv["model"] == "RF"].copy()
    rf["max_depth"] = rf["params_dict"].apply(lambda d: d.get("max_depth"))
    rf["n_estimators"] = rf["params_dict"].apply(lambda d: d.get("n_estimators"))
    rf_pivot = (rf.groupby(["max_depth", "n_estimators"])["mean_test_score"]
                  .mean().reset_index()
                  .pivot(index="max_depth", columns="n_estimators", values="mean_test_score"))
    rf_long = rf[["max_depth", "n_estimators", "mean_test_score", "std_test_score", "rank_test_score"]]

    xgb = cv[cv["model"] == "XGB"].copy()
    if len(xgb) > 0:
        xgb["max_depth"] = xgb["params_dict"].apply(lambda d: d.get("max_depth"))
        xgb["learning_rate"] = xgb["params_dict"].apply(lambda d: d.get("learning_rate"))
        xgb["n_estimators"] = xgb["params_dict"].apply(lambda d: d.get("n_estimators"))
        xgb_long = xgb[["max_depth", "learning_rate", "n_estimators",
                         "mean_test_score", "std_test_score", "rank_test_score"]]
    else:
        xgb_long = pd.DataFrame()

    rf_pivot = rf_pivot.reset_index()
    return rf_pivot, rf_long, xgb_long


def fig_5_2_roc_pr() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Concat val + test ROC, plus test PR."""
    val_roc = pd.read_csv(RESULTS_DIR / "val_roc.csv").assign(split="Validation")
    test_roc = pd.read_csv(RESULTS_DIR / "test_roc.csv").assign(split="Test")
    # Some ROC files have only fpr/tpr (no threshold). Keep what's there.
    roc_cols = ["split", "fpr", "tpr"]
    if "threshold" in val_roc.columns and "threshold" in test_roc.columns:
        roc_cols.append("threshold")
    elif "threshold" in val_roc.columns:
        val_roc = val_roc.drop(columns=["threshold"])
    roc = pd.concat([val_roc[roc_cols] if "threshold" in roc_cols else val_roc[["split", "fpr", "tpr"]],
                     test_roc[["split", "fpr", "tpr"]]], ignore_index=True)

    test_pr = pd.read_csv(RESULTS_DIR / "test_pr.csv").assign(split="Test")
    pr_cols = ["split", "recall", "precision"]
    if "threshold" in test_pr.columns:
        pr_cols.append("threshold")
    pr = test_pr[pr_cols]
    return roc, pr


def fig_5_3_confusion(src: pd.ExcelFile) -> pd.DataFrame:
    return pd.read_excel(src, sheet_name="13_confusion_matrix")


def fig_S1_failures(src: pd.ExcelFile) -> pd.DataFrame:
    return pd.read_excel(src, sheet_name="06_failure_atoms")


def build_readme() -> pd.DataFrame:
    rows = [
        ("Fig 2-1", "fig_2_1_pipeline",          "数据收集管道",         "分组柱状图（Stage × Source）",    "x=stage, y=n_molecules, hue=source",                "审稿人：你扔了多少分子？为什么？→ 答：管道每步可追溯"),
        ("Fig 2-2", "fig_2_2_taste_dist",        "味觉类别分布",         "对数刻度分组柱状图",              "x=taste, y=count, hue=source；y 轴 log scale",        "为何只做二分类？→ 答：其他类别样本太少（≤200）"),
        ("Fig 2-3", "fig_2_3_properties",        "理化性质分布（按类）", "小提琴图网格 / 直方图 + 箱线图",  "y=value, hue=class; subplot per property",          "甜与非甜分子化学上有差异吗？→ 答：MW/LogP/TPSA 都有"),
        ("Fig 2-4", "fig_2_4_lit_comparison",    "文献规模对比",         "分组柱状图（含 NaN）",            "x=work, y=Sweet/NonSweet 两根柱",                   "你比前人强在哪？→ 答：数据集最大（n=3,846）"),
        ("Fig 3-1", "fig_3_1_feature_blocks",    "特征空间结构",         "饼图 / 堆叠条形图",               "value=dim, label=block；或 share_of_total",         "1407 维怎么来的？→ 答：ECFP+MACCS+RDKit2D 三层"),
        ("Fig 3-2", "fig_3_2_split",             "70/15/15 分层划分",    "堆叠柱状图（Sweet+NonSweet）",   "x=split, stack=Sweet/NonSweet；标注比例",          "划分有偏倚吗？→ 答：三集甜味比例几乎一致"),
        ("Fig 4",   "fig_4_top12_violin",        "Top-12 判别性描述符",  "12 子图小提琴图（按类别分色）",   "x=class, y=value, facet=descriptor (12)",          "数据本身有信号吗？→ 答：单维度就有显著差异"),
        ("Fig 4",   "fig_4_top12_summary",       "Top-12 描述符均值对比", "条形图（mean_diff 排序）",       "x=descriptor, y=abs_mean_diff",                     "为什么这 12 个最关键？→ 见 mean_sweet vs mean_nonsweet"),
        ("Fig 5-1", "fig_5_1_rf_pivot",          "RF 超参数热力图",      "热力图（max_depth × n_estimators）", "z=mean_test_score (5-fold CV F1)",               "调参充分吗？→ 答：21 组组合 × 5 折"),
        ("Fig 5-1", "fig_5_1_rf_long",           "RF 超参数完整结果",    "可选：散点 + 误差棒",             "y=mean_test_score, err=std_test_score",            "性能曲面是否平滑？"),
        ("Fig 5-1", "fig_5_1_xgb_long",          "XGB 超参数完整结果",   "热力图（max_depth × LR）",       "z=mean_test_score",                                "XGB 同样系统调过"),
        ("Fig 5-2", "fig_5_2_roc",               "ROC 曲线（val+test）", "线图",                            "x=fpr, y=tpr, hue=split",                          "AUC 多少？过拟合验证集了吗？"),
        ("Fig 5-2", "fig_5_2_pr",                "PR 曲线（test）",      "线图 + 基线参考线",               "x=recall, y=precision；ref y=0.229 (Sweet ratio)", "在不平衡数据下仍有效（AP=0.92 vs 基线 0.23）"),
        ("Fig 5-3", "fig_5_3_confusion",         "混淆矩阵",             "2×2 热力图（val + test）",        "annot=count, cbar off",                            "实际决策点（threshold=0.36）下错了多少"),
        ("Fig S-1", "fig_S1_failures",           "标准化失败原因",       "横向条形图（按元素）",            "x=n, y=element, hue=source_db",                    "扔的分子是什么？→ 答：金属配合物等不适用范围"),
    ]
    return pd.DataFrame(rows, columns=[
        "figure", "sheet_name", "title_zh", "推荐图表类型", "X/Y/分组建议", "回答的科研问题"
    ])


def main():
    print("=" * 70)
    print("Building plotting-ready Excel...")
    print("=" * 70)
    print(f"Source: {SRC_XLSX}")
    print(f"Output: {OUT_XLSX}\n")

    src = pd.ExcelFile(SRC_XLSX)

    print("[1/11] Fig 2-1 pipeline ...")
    f2_1 = fig_2_1_pipeline()
    print("[2/11] Fig 2-2 taste distribution ...")
    f2_2 = fig_2_2_taste_distribution(src)
    print("[3/11] Fig 2-3 property distributions (computing RDKit descriptors for 3,846 mols) ...")
    f2_3 = fig_2_3_property_distributions()
    print(f"       → {len(f2_3)} molecules")
    print("[4/11] Fig 2-4 literature comparison ...")
    f2_4 = fig_2_4_lit_comparison(src)
    print("[5/11] Fig 3-1 feature blocks ...")
    f3_1 = fig_3_1_feature_blocks(src)
    print("[6/11] Fig 3-2 split summary ...")
    f3_2 = fig_3_2_split_summary(src)
    print("[7/11] Fig 4 top-12 discriminative descriptors ...")
    f4_long, f4_sum = fig_4_top12_descriptors(src)
    print(f"       → long-format: {len(f4_long)} rows (12 descriptors × ~3,846 mols)")
    print("[8/11] Fig 5-1 hyperparameter heatmaps ...")
    f5_1_rf_pivot, f5_1_rf_long, f5_1_xgb_long = fig_5_1_hyperparameter_heatmaps(src)
    print("[9/11] Fig 5-2 ROC + PR curves ...")
    f5_2_roc, f5_2_pr = fig_5_2_roc_pr()
    print("[10/11] Fig 5-3 confusion matrices ...")
    f5_3 = fig_5_3_confusion(src)
    print("[11/11] Fig S-1 standardization failures ...")
    fS1 = fig_S1_failures(src)

    readme = build_readme()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as writer:
        readme.to_excel(writer, sheet_name="00_README", index=False)
        f2_1.to_excel(writer, sheet_name="fig_2_1_pipeline", index=False)
        f2_2.to_excel(writer, sheet_name="fig_2_2_taste_dist", index=False)
        f2_3.to_excel(writer, sheet_name="fig_2_3_properties", index=False)
        f2_4.to_excel(writer, sheet_name="fig_2_4_lit_comparison", index=False)
        f3_1.to_excel(writer, sheet_name="fig_3_1_feature_blocks", index=False)
        f3_2.to_excel(writer, sheet_name="fig_3_2_split", index=False)
        f4_long.to_excel(writer, sheet_name="fig_4_top12_violin", index=False)
        f4_sum.to_excel(writer, sheet_name="fig_4_top12_summary", index=False)
        f5_1_rf_pivot.to_excel(writer, sheet_name="fig_5_1_rf_pivot", index=False)
        f5_1_rf_long.to_excel(writer, sheet_name="fig_5_1_rf_long", index=False)
        if len(f5_1_xgb_long) > 0:
            f5_1_xgb_long.to_excel(writer, sheet_name="fig_5_1_xgb_long", index=False)
        f5_2_roc.to_excel(writer, sheet_name="fig_5_2_roc", index=False)
        f5_2_pr.to_excel(writer, sheet_name="fig_5_2_pr", index=False)
        f5_3.to_excel(writer, sheet_name="fig_5_3_confusion", index=False)
        fS1.to_excel(writer, sheet_name="fig_S1_failures", index=False)

    print("\n" + "=" * 70)
    print(f"✅ Saved: {OUT_XLSX}")
    print(f"   File size: {OUT_XLSX.stat().st_size / 1024:.1f} KB")
    print("=" * 70)


if __name__ == "__main__":
    main()
