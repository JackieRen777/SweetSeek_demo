"""Day 2 merge pipeline: interim parquets -> master.parquet.

Pipeline:
  1. Load data/interim/{chemtastesdb,bitterdb}.parquet (Day 1 output)
  2. Standardize every SMILES (fills smiles_canonical / inchi / inchi_key
     / mw / n_heavy_atoms; flags rows with unparseable / disallowed atoms)
  3. Drop rows that failed standardization
  4. Within-source dedup by inchi_key (keep first)
  5. Cross-source merge with ChemTastesDB priority: BDB rows whose
     inchi_key already exists in CTD are dropped (CTD has literature refs
     so its label wins on conflict)
  6. Label mapping (V1 binary):
        Sweetness                                       -> Sweet     (is_sweet=1)
        Bitterness / Non-sweetness / Tastelessness      -> NonSweet  (is_sweet=0)
        Multitaste / Miscellaneous / Umami / Sour / Salt -> drop (V1 binary scope)
  7. Quality filter: MW 50-2000 (atom whitelist already enforced in
     standardize.py)
  8. Write data/processed/master.parquet + a JSON summary

Run:
    venv/bin/python -m scripts.data.merge
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

from scripts.data.schema import UNIFIED_COLUMNS, validate_columns
from scripts.data.standardize import standardize

REPO_ROOT = Path(__file__).resolve().parents[2]
CTD_PARQUET = REPO_ROOT / "data" / "interim" / "chemtastesdb.parquet"
BDB_PARQUET = REPO_ROOT / "data" / "interim" / "bitterdb.parquet"
OUT_DIR = REPO_ROOT / "data" / "processed"
MASTER_PARQUET = OUT_DIR / "master.parquet"
SUMMARY_JSON = OUT_DIR / "merge_summary.json"

# V1 binary label policy
SWEET_RAW = {"Sweetness"}
NONSWEET_RAW = {"Bitterness", "Non-sweetness", "Tastelessness"}
DROP_RAW = {"Multitaste", "Miscellaneous", "Umaminess", "Sourness", "Saltiness"}

# Per-source confidence: ChemTastesDB has per-row literature refs;
# BitterDB curates but no per-row refs in the public CSV.
CONFIDENCE_BY_SOURCE = {"ChemTastesDB": "high", "BitterDB": "medium"}

# Quality filter thresholds (atom whitelist is enforced inside standardize)
MW_MIN = 50.0
MW_MAX = 2000.0


def _standardize_table(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """Apply standardize() row-wise; fill canonical fields + std_status."""
    print(f"[{label}] Standardizing {len(df)} rows ...")
    t0 = time.time()
    canonical, inchis, keys, mws, n_atoms, statuses = [], [], [], [], [], []
    for smi in df["smiles_raw"]:
        if smi is None or pd.isna(smi):
            canonical.append(None); inchis.append(None); keys.append(None)
            mws.append(None); n_atoms.append(None); statuses.append("no_smiles")
            continue
        out = standardize(smi)
        if out["valid"]:
            canonical.append(out["smiles_canonical"])
            inchis.append(out["inchi"])
            keys.append(out["inchi_key"])
            mws.append(out["mw"])
            n_atoms.append(out["n_heavy_atoms"])
            statuses.append("ok")
        else:
            canonical.append(None); inchis.append(None); keys.append(None)
            mws.append(None); n_atoms.append(None)
            statuses.append(out["reason"])
    df = df.copy()
    df["smiles_canonical"] = canonical
    df["inchi"] = inchis
    df["inchi_key"] = keys
    df["mw"] = mws
    df["n_heavy_atoms"] = n_atoms
    df["std_status"] = statuses
    print(f"[{label}] Done in {time.time() - t0:.1f}s | ok={sum(s=='ok' for s in statuses)} fail={sum(s!='ok' for s in statuses)}")
    return df


def _map_label(taste_raw):
    if taste_raw in SWEET_RAW:
        return "Sweet", 1
    if taste_raw in NONSWEET_RAW:
        return "NonSweet", 0
    return None, None  # signals "drop"


def _apply_label_mapping(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    mapped = df["taste_class_raw"].apply(_map_label)
    df["taste_class"] = mapped.apply(lambda x: x[0])
    df["is_sweet"] = mapped.apply(lambda x: x[1])
    df["label_confidence"] = df["source_db"].map(CONFIDENCE_BY_SOURCE)
    return df


def _quality_filter(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Apply MW range filter; return cleaned df + dropped counts dict."""
    n_before = len(df)
    mw_low = df[df["mw"] < MW_MIN]
    mw_high = df[df["mw"] > MW_MAX]
    df = df[(df["mw"] >= MW_MIN) & (df["mw"] <= MW_MAX)].reset_index(drop=True)
    return df, {
        "input_rows": n_before,
        "dropped_mw_below_50": len(mw_low),
        "dropped_mw_above_2000": len(mw_high),
        "kept": len(df),
    }


def main():
    print("=" * 60)
    print("Day 2 merge pipeline")
    print("=" * 60)

    # ---- Step 1-2: load + standardize ----
    ctd = pd.read_parquet(CTD_PARQUET)
    bdb = pd.read_parquet(BDB_PARQUET)
    print(f"\n[load] CTD={len(ctd)} BDB={len(bdb)}")

    ctd = _standardize_table(ctd, "CTD")
    bdb = _standardize_table(bdb, "BDB")

    # ---- Step 3: drop standardization failures ----
    ctd_failures = ctd[ctd["std_status"] != "ok"]["std_status"].value_counts().to_dict()
    bdb_failures = bdb[bdb["std_status"] != "ok"]["std_status"].value_counts().to_dict()
    ctd = ctd[ctd["std_status"] == "ok"].drop(columns=["std_status"]).reset_index(drop=True)
    bdb = bdb[bdb["std_status"] == "ok"].drop(columns=["std_status"]).reset_index(drop=True)
    print(f"\n[std-filter] CTD ok={len(ctd)} BDB ok={len(bdb)}")

    # ---- Step 4: within-source dedup by inchi_key ----
    ctd_before = len(ctd)
    bdb_before = len(bdb)
    ctd = ctd.drop_duplicates(subset=["inchi_key"], keep="first").reset_index(drop=True)
    bdb = bdb.drop_duplicates(subset=["inchi_key"], keep="first").reset_index(drop=True)
    print(f"[dedup-within] CTD {ctd_before}->{len(ctd)} | BDB {bdb_before}->{len(bdb)}")

    # ---- Step 5: cross-source merge with CTD priority ----
    ctd_keys = set(ctd["inchi_key"])
    overlap_mask = bdb["inchi_key"].isin(ctd_keys)
    n_overlap = int(overlap_mask.sum())
    bdb_unique_to_bdb = bdb[~overlap_mask].reset_index(drop=True)
    print(f"[dedup-cross] overlap={n_overlap} | CTD kept={len(ctd)} | BDB-unique={len(bdb_unique_to_bdb)}")

    merged = pd.concat([ctd, bdb_unique_to_bdb], ignore_index=True)
    print(f"[merge] union after dedup = {len(merged)}")

    # ---- Step 6: label mapping ----
    merged = _apply_label_mapping(merged)
    raw_dist = merged["taste_class_raw"].value_counts(dropna=False).to_dict()
    print(f"\n[label] taste_class_raw distribution (post-merge):")
    for k, v in raw_dist.items():
        print(f"  {k!s:25s} {v}")

    n_before_label = len(merged)
    labeled = merged[merged["taste_class"].notna()].reset_index(drop=True)
    n_dropped_other = n_before_label - len(labeled)
    print(f"[label] kept rows with V1 label: {len(labeled)} (dropped {n_dropped_other} other-taste/ambiguous)")

    # ---- Step 7: quality filter (MW range) ----
    labeled, mw_stats = _quality_filter(labeled)
    print(f"[quality] MW range [{MW_MIN}, {MW_MAX}] kept={mw_stats['kept']} | dropped low={mw_stats['dropped_mw_below_50']} high={mw_stats['dropped_mw_above_2000']}")

    # ---- Step 8: enforce schema column order + drop interim helper col ----
    labeled = labeled[UNIFIED_COLUMNS]
    validate_columns(labeled.columns)

    # ---- Final summary ----
    final_label_dist = labeled["taste_class"].value_counts().to_dict()
    final_source_dist = labeled["source_db"].value_counts().to_dict()
    sweet_n = int(final_label_dist.get("Sweet", 0))
    nonsweet_n = int(final_label_dist.get("NonSweet", 0))
    ratio = nonsweet_n / sweet_n if sweet_n else None

    print("\n" + "=" * 60)
    print("FINAL master.parquet")
    print("=" * 60)
    print(f"  rows:            {len(labeled)}")
    print(f"  Sweet (1):       {sweet_n}")
    print(f"  NonSweet (0):    {nonsweet_n}")
    print(f"  imbalance ratio: 1 : {ratio:.2f}" if ratio else "  imbalance ratio: n/a")
    print(f"  per source:      {final_source_dist}")
    print(f"  unique InChIKey: {labeled['inchi_key'].nunique()}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    labeled.to_parquet(MASTER_PARQUET, index=False)
    print(f"\nWrote {MASTER_PARQUET.relative_to(REPO_ROOT)}")

    summary = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sources": {
            "ChemTastesDB": {"raw_rows": int(ctd_before), "after_dedup": int(len(ctd))},
            "BitterDB": {"raw_rows": int(bdb_before), "after_within_dedup": int(len(bdb)),
                          "after_cross_priority": int(len(bdb_unique_to_bdb))},
        },
        "standardization_failures": {
            "ChemTastesDB": ctd_failures,
            "BitterDB": bdb_failures,
        },
        "cross_source_overlap": n_overlap,
        "post_label_mapping": {
            "kept": int(len(labeled) + 0),  # post-quality kept
            "dropped_ambiguous_or_other_taste": int(n_dropped_other),
        },
        "quality_filter": mw_stats,
        "final": {
            "rows": int(len(labeled)),
            "Sweet": sweet_n,
            "NonSweet": nonsweet_n,
            "imbalance_ratio_nonsweet_per_sweet": round(ratio, 3) if ratio else None,
            "by_source": {k: int(v) for k, v in final_source_dist.items()},
            "unique_inchi_keys": int(labeled["inchi_key"].nunique()),
        },
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {SUMMARY_JSON.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
