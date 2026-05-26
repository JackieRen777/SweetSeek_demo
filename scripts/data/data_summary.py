"""Preliminary data collection summary (Table 2-1 style).

Generates a snapshot of what we have before Day 2's merge step:
  - per-source raw counts
  - per-source taste_class_raw distribution
  - InChIKey-based dedup numbers (within source + across sources)
  - V1 binary label mapping preview (Sweet vs NonSweet vs Drop)

Output:
  docs/data_collection_table_2_1.md  (markdown table for paper draft)
  console summary
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from scripts.data.standardize import standardize

REPO_ROOT = Path(__file__).resolve().parents[2]
CTD_PARQUET = REPO_ROOT / "data" / "interim" / "chemtastesdb.parquet"
BDB_PARQUET = REPO_ROOT / "data" / "interim" / "bitterdb.parquet"
OUTPUT_MD = REPO_ROOT / "docs" / "data_collection_table_2_1.md"

# V1 label mapping policy (per docs/ml_v1_plan_revised.md)
SWEET_LABELS = {"Sweetness"}
NONSWEET_LABELS = {"Bitterness", "Bitter", "Non-sweetness", "Tastelessness"}
DROP_LABELS = {"Multitaste", "Miscellaneous"}
OTHER_LABELS = {"Umaminess", "Sourness", "Saltiness"}  # not used in V1 binary task


def map_v1_label(taste_class_raw):
    if taste_class_raw is None or pd.isna(taste_class_raw):
        return "Drop(missing)"
    if taste_class_raw in SWEET_LABELS:
        return "Sweet"
    if taste_class_raw in NONSWEET_LABELS:
        return "NonSweet"
    if taste_class_raw in DROP_LABELS:
        return "Drop(ambiguous)"
    if taste_class_raw in OTHER_LABELS:
        return "Drop(other_taste)"
    return "Drop(unknown)"


def add_inchi_key(df: pd.DataFrame) -> pd.DataFrame:
    """Run standardize() on every row, attach inchi_key + standardize_status."""
    keys, statuses = [], []
    t0 = time.time()
    for smi in df["smiles_raw"]:
        if smi is None or pd.isna(smi):
            keys.append(None)
            statuses.append("no_smiles")
            continue
        out = standardize(smi)
        if out["valid"]:
            keys.append(out["inchi_key"])
            statuses.append("ok")
        else:
            keys.append(None)
            statuses.append(out["reason"])
    print(f"  [standardize] {len(df)} rows in {time.time() - t0:.1f}s")
    df = df.copy()
    df["inchi_key"] = keys
    df["std_status"] = statuses
    return df


def main():
    print("=== Loading interim parquets ===")
    ctd = pd.read_parquet(CTD_PARQUET)
    bdb = pd.read_parquet(BDB_PARQUET)
    print(f"  CTD: {len(ctd)} rows | BDB: {len(bdb)} rows")

    print("\n=== Standardizing SMILES (computing InChIKey) ===")
    print("  ChemTastesDB ...")
    ctd = add_inchi_key(ctd)
    print("  BitterDB ...")
    bdb = add_inchi_key(bdb)

    # ---- per-source numbers ----
    ctd_ok = ctd[ctd["std_status"] == "ok"]
    bdb_ok = bdb[bdb["std_status"] == "ok"]

    ctd_unique = ctd_ok["inchi_key"].nunique()
    bdb_unique = bdb_ok["inchi_key"].nunique()
    overlap = set(ctd_ok["inchi_key"]) & set(bdb_ok["inchi_key"])
    n_overlap = len(overlap)

    print("\n=== Source-level summary ===")
    print(f"  CTD raw rows:                 {len(ctd)}")
    print(f"  CTD with valid InChIKey:      {len(ctd_ok)}")
    print(f"  CTD unique InChIKeys:         {ctd_unique}")
    print(f"  BDB raw rows:                 {len(bdb)}")
    print(f"  BDB with valid InChIKey:      {len(bdb_ok)}")
    print(f"  BDB unique InChIKeys:         {bdb_unique}")
    print(f"  Cross-DB overlap (InChIKey):  {n_overlap}")
    print(f"  Union after dedup:            {ctd_unique + bdb_unique - n_overlap}")

    # ---- standardize failure modes ----
    print("\n=== Standardize failure breakdown ===")
    print("  CTD:")
    print(ctd["std_status"].value_counts().to_string())
    print("  BDB:")
    print(bdb["std_status"].value_counts().to_string())

    # ---- taste_class_raw distribution per source ----
    print("\n=== taste_class_raw distribution ===")
    ctd_dist = ctd_ok["taste_class_raw"].value_counts(dropna=False).to_dict()
    bdb_dist = bdb_ok["taste_class_raw"].value_counts(dropna=False).to_dict()

    # ---- V1 label mapping preview ----
    ctd_ok = ctd_ok.assign(v1_label=ctd_ok["taste_class_raw"].map(map_v1_label))
    bdb_ok = bdb_ok.assign(v1_label=bdb_ok["taste_class_raw"].map(map_v1_label))

    # Apply CTD-priority on overlap: drop BDB rows whose inchi_key is in CTD
    bdb_after_priority = bdb_ok[~bdb_ok["inchi_key"].isin(set(ctd_ok["inchi_key"]))]
    # Within-source dedup by inchi_key (keep first)
    ctd_dedup = ctd_ok.drop_duplicates(subset=["inchi_key"], keep="first")
    bdb_dedup = bdb_after_priority.drop_duplicates(subset=["inchi_key"], keep="first")

    merged_preview = pd.concat([ctd_dedup, bdb_dedup], ignore_index=True)
    label_counts = merged_preview["v1_label"].value_counts().to_dict()
    print("\n=== V1 binary label preview (after CTD-priority + dedup) ===")
    for k, v in label_counts.items():
        print(f"  {k:25s} {v}")

    # ---- write markdown table ----
    md = generate_markdown(
        ctd_total=len(ctd),
        ctd_ok=len(ctd_ok),
        ctd_unique=ctd_unique,
        bdb_total=len(bdb),
        bdb_ok=len(bdb_ok),
        bdb_unique=bdb_unique,
        n_overlap=n_overlap,
        ctd_dist=ctd_dist,
        bdb_dist=bdb_dist,
        label_counts=label_counts,
        ctd_failures=ctd[ctd["std_status"] != "ok"]["std_status"].value_counts().to_dict(),
        bdb_failures=bdb[bdb["std_status"] != "ok"]["std_status"].value_counts().to_dict(),
    )
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(md, encoding="utf-8")
    print(f"\n=== Wrote {OUTPUT_MD.relative_to(REPO_ROOT)} ===")


def generate_markdown(**kw) -> str:
    ctd_dist = kw["ctd_dist"]
    bdb_dist = kw["bdb_dist"]
    label_counts = kw["label_counts"]
    union_after = kw["ctd_unique"] + kw["bdb_unique"] - kw["n_overlap"]

    all_classes = ["Sweetness", "Bitterness", "Bitter", "Non-sweetness",
                   "Tastelessness", "Multitaste", "Umaminess", "Miscellaneous",
                   "Sourness", "Saltiness"]

    lines = []
    lines.append("# 表 2-1 数据初步收集情况")
    lines.append("")
    lines.append("> 生成时间:2026-05-26 (Day 1 完成后)  ")
    lines.append("> 数据源:ChemTastesDB v1.2 + BitterDB 2024  ")
    lines.append("> 标准化方法:RDKit 去盐 + 中和电荷 + 规范互变异构 + InChIKey 计算")
    lines.append("")
    lines.append("## 1. 数据源规模总览")
    lines.append("")
    lines.append("| 数据源 | 原始记录 | 含 SMILES | InChIKey 标准化成功 | 库内去重后 |")
    lines.append("|---|---:|---:|---:|---:|")
    lines.append(f"| ChemTastesDB v1.2 | {kw['ctd_total']} | {kw['ctd_ok']} | {kw['ctd_ok']} | {kw['ctd_unique']} |")
    lines.append(f"| BitterDB 2024 | {kw['bdb_total']} | {kw['bdb_ok']} | {kw['bdb_ok']} | {kw['bdb_unique']} |")
    lines.append(f"| **合计** | **{kw['ctd_total'] + kw['bdb_total']}** | **{kw['ctd_ok'] + kw['bdb_ok']}** | **{kw['ctd_ok'] + kw['bdb_ok']}** | — |")
    lines.append("")
    lines.append(f"- 跨库重复(同 InChIKey 在两库都出现):**{kw['n_overlap']}** 个分子  ")
    lines.append(f"- 全库去重后(union):**{union_after}** 个分子")
    lines.append("")

    lines.append("## 2. 按味觉类别细分(标准化后,库内去重前)")
    lines.append("")
    lines.append("| 味觉类别 | ChemTastesDB | BitterDB | 合计 |")
    lines.append("|---|---:|---:|---:|")
    for cls in all_classes:
        c = ctd_dist.get(cls, 0)
        b = bdb_dist.get(cls, 0)
        if c or b:
            lines.append(f"| {cls} | {c} | {b} | {c + b} |")
    lines.append(f"| **合计** | **{sum(ctd_dist.values())}** | **{sum(bdb_dist.values())}** | **{sum(ctd_dist.values()) + sum(bdb_dist.values())}** |")
    lines.append("")

    lines.append("## 3. V1 二分类标签映射预览")
    lines.append("")
    lines.append("**映射规则**(详见 `docs/ml_v1_plan_revised.md`):")
    lines.append("- **Sweet(正类)**:Sweetness")
    lines.append("- **NonSweet(负类)**:Bitterness, Bitter, Non-sweetness, Tastelessness")
    lines.append("- **丢弃**:Multitaste, Miscellaneous(标签歧义);Umaminess, Sourness, Saltiness(V1 不涉及)")
    lines.append("- **冲突解决**:同 InChIKey 跨库出现时,以 ChemTastesDB 标签为准(有人工策展 + 文献溯源)")
    lines.append("")
    lines.append("| V1 标签 | 分子数 |")
    lines.append("|---|---:|")
    order = ["Sweet", "NonSweet", "Drop(ambiguous)", "Drop(other_taste)",
             "Drop(missing)", "Drop(unknown)"]
    total_used = label_counts.get("Sweet", 0) + label_counts.get("NonSweet", 0)
    total_all = sum(label_counts.values())
    for k in order:
        if k in label_counts:
            lines.append(f"| {k} | {label_counts[k]} |")
    lines.append(f"| **可用样本(Sweet + NonSweet)** | **{total_used}** |")
    lines.append(f"| **全库去重后总数** | **{total_all}** |")
    lines.append("")

    if total_used:
        sweet = label_counts.get("Sweet", 0)
        nonsweet = label_counts.get("NonSweet", 0)
        ratio = nonsweet / sweet if sweet else float("inf")
        lines.append(f"**类别不平衡比** Sweet : NonSweet = 1 : {ratio:.2f}")
        lines.append("")

    lines.append("## 4. SMILES 标准化失败原因")
    lines.append("")
    lines.append("| 失败原因 | ChemTastesDB | BitterDB |")
    lines.append("|---|---:|---:|")
    all_reasons = sorted(set(kw["ctd_failures"]) | set(kw["bdb_failures"]))
    for reason in all_reasons:
        c = kw["ctd_failures"].get(reason, 0)
        b = kw["bdb_failures"].get(reason, 0)
        lines.append(f"| {reason} | {c} | {b} |")
    lines.append("")

    lines.append("## 5. 与已发表工作的数据规模对比")
    lines.append("")
    lines.append("| 工作 | 年份 | 数据规模 | 标签维度 |")
    lines.append("|---|---|---:|---|")
    lines.append("| BitterSweet | 2019 | Sweet 435 / Bitter 685 / Non-sweet 1214 | 二分类×2 |")
    lines.append("| e-Sweet | 2019 | Sweet 530 / Non-sweet 680 | 二分类 + 回归 |")
    lines.append("| VirtualTaste | 2021 | Sweet 1608 / Bitter 1289 / Sour 403 | 多任务 |")
    lines.append("| ChemSweet | 2024 | 6 个子集(天然/合成/...) | 多层次分类 |")
    lines.append(f"| **本工作 V1** | **2026** | **Sweet {label_counts.get('Sweet', 0)} / NonSweet {label_counts.get('NonSweet', 0)}** | **二分类** |")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    main()
