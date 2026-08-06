"""Export Day 1-4 deliverables into a single multi-sheet Excel workbook.

Output: reports/sweetseek_v1_data.xlsx

Sheets (one per analysis angle, all paper-ready):
  00_README              — what each sheet is, and the recommended plot for it
  01_source_overview     — Day 1-2 raw vs deduped vs cross-source counts
  02_taste_distribution  — taste class breakdown per source
  03_label_mapping       — V1 binary mapping summary
  04_quality_filter      — MW filter audit trail
  05_final_dataset       — master.parquet identity + label per row (gitignored upstream)
  06_failure_atoms       — standardization failures by element
  07_descriptors_block   — feature block layout (1024 + 167 + 216 = 1407)
  08_split_summary       — train/val/test row counts + Sweet ratio per split
  09_descriptor_stats    — RDKit 2D descriptor mean/std/min/max on train (raw)
  10_cv_grid             — 5-fold CV grid scores (RF + XGB)
  11_val_metrics         — validation set metrics
  12_val_roc             — ROC curve points for plotting
  13_confusion_matrix    — confusion matrix in long form
  14_lit_comparison      — vs BitterSweet/e-Sweet/VirtualTaste/ChemSweet
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
FEAT_DIR = REPO_ROOT / "data" / "features"
RESULTS_DIR = REPO_ROOT / "results"
OUT_DIR = REPO_ROOT / "reports"
OUT_PATH = OUT_DIR / "sweetseek_v1_data.xlsx"


def _readme_sheet() -> pd.DataFrame:
    rows = [
        ("01_source_overview", "Day 1-2 数据收集总览(原始/去重/跨库)",
         "Stacked bar:每条柱子是一个数据源,堆叠 raw→within-dedup→cross-priority 三段;或 Sankey 桑基图(raw → standardized → deduped → final)"),
        ("02_taste_distribution", "各数据源的味觉类别细分",
         "Grouped bar(分组柱状图):x=味觉类别, y=分子数, hue=数据源(CTD/BDB)"),
        ("03_label_mapping", "Sweetness/Bitterness/... → Sweet/NonSweet 映射结果",
         "Donut chart(环形图):正/负/丢弃三段,中心写总数 4161"),
        ("04_quality_filter", "MW 过滤前后的样本数审计",
         "Waterfall(瀑布图):3862 →(-4 MW<50)→(-12 MW>2000)→ 3846"),
        ("05_final_dataset", "master.parquet 行级身份 + 标签",
         "MW 直方图 + KDE,按 Sweet/NonSweet 分组叠加;额外:n_heavy_atoms 箱线图"),
        ("06_failure_atoms", "标准化失败原因按元素拆分",
         "Horizontal bar(横向柱):y=金属元素, x=丢弃数, 颜色区分两个数据源"),
        ("07_descriptors_block", "ECFP4(1024) + MACCS(167) + RDKit2D(216) 特征结构",
         "Treemap(矩形树图)或简单的横向堆叠条:展示三块特征占总维度比例"),
        ("08_split_summary", "70/15/15 stratified split 的样本数 + Sweet 比例",
         "Stacked bar:三个 split 各一柱,堆叠 Sweet/NonSweet,顶部标注 Sweet%"),
        ("09_descriptor_stats", "RDKit 2D descriptors 的统计量(train 上 raw 值)",
         "前 20 个方差最大的描述符:Boxplot 按 Sweet/NonSweet 分组(揭示哪些描述符判别力强)"),
        ("10_cv_grid", "GridSearchCV 5-fold 全部参数组合的 mean/std F1",
         "Heatmap:RF 是 (n_estimators × max_depth);XGB 是 (max_depth × learning_rate × n_estimators) 拆三张"),
        ("11_val_metrics", "RF / XGB 在 validation 集上的全部指标",
         "Radar(雷达图)六指标对比 RF vs XGB;或 Grouped bar"),
        ("12_val_roc", "ROC 曲线坐标点(每模型一组 fpr/tpr)",
         "ROC curves 双曲线叠加,在图例标 AUC;同时画 PR curve(论文里通常并排展示)"),
        ("13_confusion_matrix", "RF / XGB 在 val 上的混淆矩阵(长表)",
         "两张 2×2 Heatmap 并排,annot 显示数字 + 百分比"),
        ("14_lit_comparison", "本工作 vs 已发表 4 个 sweet/bitter 模型的数据规模",
         "Grouped bar:x=工作名, y=样本数, 堆叠 Sweet/NonSweet/总计三色"),
    ]
    return pd.DataFrame(rows, columns=["sheet", "内容", "推荐绘图(scientific paper-ready)"])


def _source_overview() -> pd.DataFrame:
    summary = json.loads((PROCESSED_DIR / "merge_summary.json").read_text(encoding="utf-8"))
    return pd.DataFrame([
        {"source_db": "ChemTastesDB", "raw_records": 2947, "with_smiles": 2944,
         "standardization_ok": summary["sources"]["ChemTastesDB"]["raw_rows"],
         "after_within_dedup": summary["sources"]["ChemTastesDB"]["after_dedup"],
         "after_cross_priority": summary["sources"]["ChemTastesDB"]["after_dedup"]},
        {"source_db": "BitterDB", "raw_records": 2250, "with_smiles": 2250,
         "standardization_ok": summary["sources"]["BitterDB"]["raw_rows"],
         "after_within_dedup": summary["sources"]["BitterDB"]["after_within_dedup"],
         "after_cross_priority": summary["sources"]["BitterDB"]["after_cross_priority"]},
        {"source_db": "TOTAL", "raw_records": 5197, "with_smiles": 5194,
         "standardization_ok": 5158, "after_within_dedup": 4811,
         "after_cross_priority": 4161},
    ])


def _taste_distribution() -> pd.DataFrame:
    rows = [
        ("Sweetness",     881,    0,  881),
        ("Bitterness",    1085, 1478, 2563),
        ("Non-sweetness", 227,    0,  227),
        ("Tastelessness", 191,    0,  191),
        ("Multitaste",    99,     0,   99),
        ("Umaminess",     81,     0,   81),
        ("Miscellaneous", 77,     0,   77),
        ("Sourness",      35,     0,   35),
        ("Saltiness",     7,      0,    7),
    ]
    return pd.DataFrame(rows, columns=["taste_class_raw", "ChemTastesDB", "BitterDB", "total"])


def _label_mapping() -> pd.DataFrame:
    return pd.DataFrame([
        {"v1_label": "Sweet (positive, is_sweet=1)",  "raw_classes": "Sweetness",                                       "n_molecules": 881},
        {"v1_label": "NonSweet (negative, is_sweet=0)","raw_classes": "Bitterness | Non-sweetness | Tastelessness",     "n_molecules": 2981},
        {"v1_label": "DROP (label ambiguous)",        "raw_classes": "Multitaste | Miscellaneous",                     "n_molecules": 176},
        {"v1_label": "DROP (other tastes)",           "raw_classes": "Umaminess | Sourness | Saltiness",               "n_molecules": 123},
        {"v1_label": "TOTAL pre-MW",                  "raw_classes": "—",                                              "n_molecules": 4161},
    ])


def _quality_filter() -> pd.DataFrame:
    summary = json.loads((PROCESSED_DIR / "merge_summary.json").read_text(encoding="utf-8"))
    qf = summary["quality_filter"]
    return pd.DataFrame([
        {"step": "input",          "n_molecules": qf["input_rows"], "delta": 0,                          "filter": "—"},
        {"step": "MW < 50 (drop)", "n_molecules": qf["input_rows"] - qf["dropped_mw_below_50"],
         "delta": -qf["dropped_mw_below_50"], "filter": "MW >= 50 Da"},
        {"step": "MW > 2000 (drop)","n_molecules": qf["kept"],
         "delta": -qf["dropped_mw_above_2000"], "filter": "MW <= 2000 Da"},
        {"step": "kept",           "n_molecules": qf["kept"], "delta": 0,                              "filter": "final"},
    ])


def _final_dataset() -> pd.DataFrame:
    df = pd.read_parquet(PROCESSED_DIR / "master.parquet")
    cols = ["mol_id", "name", "source_db", "taste_class_raw", "taste_class",
            "is_sweet", "label_confidence", "mw", "n_heavy_atoms", "inchi_key",
            "smiles_canonical"]
    return df[[c for c in cols if c in df.columns]]


def _failure_atoms() -> pd.DataFrame:
    summary = json.loads((PROCESSED_DIR / "merge_summary.json").read_text(encoding="utf-8"))
    rows = []
    for src, fails in summary["standardization_failures"].items():
        for k, v in fails.items():
            if k.startswith("disallowed_atoms:"):
                element = k.split(":", 1)[1]
                rows.append({"source_db": src, "reason": "disallowed_atoms", "element": element, "n": v})
            else:
                rows.append({"source_db": src, "reason": k, "element": "—", "n": v})
    return pd.DataFrame(rows).sort_values(["element", "source_db"]).reset_index(drop=True)


def _descriptors_block() -> pd.DataFrame:
    meta = json.loads((FEAT_DIR / "feature_meta.json").read_text(encoding="utf-8"))
    rows = []
    for name, b in meta["blocks"].items():
        rows.append({
            "block": name,
            "start_idx": b["start"],
            "end_idx": b["end"],
            "dim": b["end"] - b["start"],
            "binary": b["binary"],
            "share_of_total": (b["end"] - b["start"]) / meta["n_features"],
        })
    rows.append({"block": "TOTAL", "start_idx": 0, "end_idx": meta["n_features"],
                 "dim": meta["n_features"], "binary": "—", "share_of_total": 1.0})
    return pd.DataFrame(rows)


def _split_summary() -> pd.DataFrame:
    splits = json.loads((FEAT_DIR / "splits.json").read_text(encoding="utf-8"))
    y = np.load(FEAT_DIR / "y.npy")
    rows = []
    for name in ["train", "val", "test"]:
        idx = np.array(splits[name], dtype=int)
        sw = int((y[idx] == 1).sum())
        ns = int((y[idx] == 0).sum())
        rows.append({"split": name, "n": len(idx), "Sweet": sw, "NonSweet": ns,
                     "sweet_ratio": sw / len(idx)})
    rows.append({"split": "TOTAL", "n": int(len(y)),
                 "Sweet": int((y == 1).sum()), "NonSweet": int((y == 0).sum()),
                 "sweet_ratio": float((y == 1).mean())})
    return pd.DataFrame(rows)


def _descriptor_stats() -> pd.DataFrame:
    """Mean/std/min/max for each RDKit 2D descriptor on the TRAIN subset (raw,
    pre-scaling). Useful for picking the most discriminative descriptors to plot."""
    X_raw = np.load(FEAT_DIR / "X_raw.npy")
    y = np.load(FEAT_DIR / "y.npy")
    splits = json.loads((FEAT_DIR / "splits.json").read_text(encoding="utf-8"))
    meta = json.loads((FEAT_DIR / "feature_meta.json").read_text(encoding="utf-8"))
    idx_tr = np.array(splits["train"], dtype=int)
    desc_start = meta["blocks"]["RDKit2D"]["start"]
    desc_end = meta["blocks"]["RDKit2D"]["end"]
    names = meta["rdkit_descriptor_names"]
    block = X_raw[idx_tr, desc_start:desc_end]
    y_tr = y[idx_tr]
    sweet_mask = y_tr == 1
    rows = []
    for j, n in enumerate(names):
        col = block[:, j]
        col_clean = col[~np.isnan(col)]
        if col_clean.size == 0:
            continue
        sw_col = block[sweet_mask, j]; sw_col = sw_col[~np.isnan(sw_col)]
        ns_col = block[~sweet_mask, j]; ns_col = ns_col[~np.isnan(ns_col)]
        rows.append({
            "descriptor": n,
            "mean": float(col_clean.mean()),
            "std": float(col_clean.std()),
            "min": float(col_clean.min()),
            "max": float(col_clean.max()),
            "mean_sweet": float(sw_col.mean()) if sw_col.size else np.nan,
            "mean_nonsweet": float(ns_col.mean()) if ns_col.size else np.nan,
            "abs_mean_diff": float(abs(sw_col.mean() - ns_col.mean())) if sw_col.size and ns_col.size else np.nan,
        })
    return pd.DataFrame(rows).sort_values("abs_mean_diff", ascending=False).reset_index(drop=True)


def _cv_grid() -> pd.DataFrame:
    return pd.read_csv(RESULTS_DIR / "cv_results.csv")


def _val_metrics() -> pd.DataFrame:
    return pd.read_csv(RESULTS_DIR / "val_metrics.csv")


def _val_roc() -> pd.DataFrame:
    return pd.read_csv(RESULTS_DIR / "val_roc.csv")


def _confusion_long() -> pd.DataFrame:
    val = pd.read_csv(RESULTS_DIR / "val_metrics.csv")
    rows = []
    for _, r in val.iterrows():
        rows.append({"model": r["model"], "actual": "NonSweet", "pred": "NonSweet", "n": int(r["tn"])})
        rows.append({"model": r["model"], "actual": "NonSweet", "pred": "Sweet",    "n": int(r["fp"])})
        rows.append({"model": r["model"], "actual": "Sweet",    "pred": "NonSweet", "n": int(r["fn"])})
        rows.append({"model": r["model"], "actual": "Sweet",    "pred": "Sweet",    "n": int(r["tp"])})
    return pd.DataFrame(rows)


def _lit_comparison() -> pd.DataFrame:
    return pd.DataFrame([
        {"work": "BitterSweet",      "year": 2019, "Sweet": 435,  "NonSweet": 1899, "total": 2334, "label_dim": "binary x2"},
        {"work": "e-Sweet",          "year": 2019, "Sweet": 530,  "NonSweet": 680,  "total": 1210, "label_dim": "binary + regression"},
        {"work": "VirtualTaste",     "year": 2021, "Sweet": 1608, "NonSweet": None, "total": None, "label_dim": "multi-task (3 tastes)"},
        {"work": "ChemSweet",        "year": 2024, "Sweet": None, "NonSweet": None, "total": None, "label_dim": "6 subsets"},
        {"work": "SweetSeek (this)", "year": 2026, "Sweet": 881,  "NonSweet": 2965, "total": 3846, "label_dim": "binary"},
    ])


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sheets = {
        "00_README":             _readme_sheet(),
        "01_source_overview":    _source_overview(),
        "02_taste_distribution": _taste_distribution(),
        "03_label_mapping":      _label_mapping(),
        "04_quality_filter":     _quality_filter(),
        "05_final_dataset":      _final_dataset(),
        "06_failure_atoms":      _failure_atoms(),
        "07_descriptors_block":  _descriptors_block(),
        "08_split_summary":      _split_summary(),
        "09_descriptor_stats":   _descriptor_stats(),
        "10_cv_grid":            _cv_grid(),
        "11_val_metrics":        _val_metrics(),
        "12_val_roc":            _val_roc(),
        "13_confusion_matrix":   _confusion_long(),
        "14_lit_comparison":     _lit_comparison(),
    }

    print("=" * 60)
    print(f"Writing {OUT_PATH.relative_to(REPO_ROOT)}")
    print("=" * 60)
    with pd.ExcelWriter(OUT_PATH, engine="openpyxl") as w:
        for name, df in sheets.items():
            df.to_excel(w, sheet_name=name, index=False)
            print(f"  [{name}]  rows={len(df)}  cols={len(df.columns)}")

    size_mb = OUT_PATH.stat().st_size / 1024 / 1024
    print(f"\nDone. {OUT_PATH.name}  ({size_mb:.2f} MB, {len(sheets)} sheets)")


if __name__ == "__main__":
    main()
