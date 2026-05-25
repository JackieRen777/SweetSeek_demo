"""BitterDB 2024 adapter.

Reads:
  data/raw/bitterdb_2024/BitterCompoundsPropA_2024.csv  (props, 31 cols)
  data/raw/bitterdb_2024/compoundsnamesA_2024.csv       (cID, cName, order)

Emits:
  data/interim/bitterdb.parquet  conforming to schema.UNIFIED_COLUMNS

Day 1 scope:
  - dedup props by cid (a few rows duplicate, keep first)
  - join primary name (order=0) from names CSV
  - SMILES priority: Isomeric_smiles -> canonical_smiles -> cStruc
  - taste_class_raw is constant "Bitter" (whole DB is bitter compounds)
  - is_natural mapping: 'n' -> 1, 's' -> 0, '' / NaN -> None
  - DO NOT use the source's pre-computed InChiKey directly; we recompute
    from canonical mol on Day 2 to ensure consistency with ChemTastesDB
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.data.schema import (
    UNIFIED_COLUMNS,
    empty_unified_row,
    validate_columns,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PROPS_CSV = REPO_ROOT / "data" / "raw" / "bitterdb_2024" / "BitterCompoundsPropA_2024.csv"
NAMES_CSV = REPO_ROOT / "data" / "raw" / "bitterdb_2024" / "compoundsnamesA_2024.csv"
OUTPUT_PARQUET = REPO_ROOT / "data" / "interim" / "bitterdb.parquet"


def _clean_text(value):
    if pd.isna(value):
        return None
    s = str(value).replace("\xa0", " ").strip()
    return s if s else None


def _map_is_natural(value):
    """BitterDB isNatural: 'n' natural, 's' synthetic, '' unknown."""
    if pd.isna(value):
        return None
    s = str(value).strip().lower()
    if s == "n":
        return 1
    if s == "s":
        return 0
    return None


def _pick_smiles(row):
    """Prefer Isomeric_smiles (preserves chirality), fall back to canonical, then cStruc."""
    for col in ("Isomeric_smiles", "canonical_smiles", "cStruc"):
        val = _clean_text(row.get(col))
        if val:
            return val
    return None


def load_raw() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not PROPS_CSV.exists():
        raise FileNotFoundError(f"Missing {PROPS_CSV}; re-download per data/raw/README.md")
    if not NAMES_CSV.exists():
        raise FileNotFoundError(f"Missing {NAMES_CSV}; re-download per data/raw/README.md")
    props = pd.read_csv(PROPS_CSV, dtype={"cid": str, "pubChemID": str})
    names = pd.read_csv(NAMES_CSV, dtype={"cID": str})
    return props, names


def build_name_map(names: pd.DataFrame) -> dict:
    """Return {cID: primary_name} where primary_name is the row with order=0.

    If a cID has no order=0 row, fall back to the smallest order value present.
    """
    primary = names[names["order"] == 0][["cID", "cName"]]
    name_map = dict(zip(primary["cID"].astype(str), primary["cName"].astype(str)))
    missing = set(names["cID"].astype(str)) - set(name_map.keys())
    if missing:
        fallback = names[names["cID"].astype(str).isin(missing)].sort_values(["cID", "order"])
        for cid, sub in fallback.groupby(fallback["cID"].astype(str)):
            name_map[cid] = str(sub["cName"].iloc[0])
    return name_map


def to_unified(props: pd.DataFrame, names: pd.DataFrame) -> pd.DataFrame:
    name_map = build_name_map(names)
    before = len(props)
    props = props.drop_duplicates(subset=["cid"], keep="first").reset_index(drop=True)
    deduped = before - len(props)
    if deduped:
        print(f"[BitterDB] Dropped {deduped} duplicate cid rows (kept first)")

    rows = []
    for _, r in props.iterrows():
        row = empty_unified_row()
        cid = _clean_text(r["cid"])
        # Identity
        row["mol_id"] = f"BDB-{cid}"
        row["name"] = name_map.get(cid) or _clean_text(r.get("IUPAC"))
        row["smiles_raw"] = _pick_smiles(r)
        # Provenance
        row["source_db"] = "BitterDB"
        row["source_id"] = cid
        row["source_refs"] = None  # BitterDB props CSV has no per-row refs column
        row["pubchem_cid"] = _clean_text(r.get("pubChemID"))
        row["cas_number"] = _clean_text(r.get("Cas_Number_Final"))
        # Targets — whole DB is bitter
        row["taste_class_raw"] = "Bitter"
        # Stratification
        row["is_natural"] = _map_is_natural(r.get("isNatural"))
        rows.append(row)

    df = pd.DataFrame(rows, columns=UNIFIED_COLUMNS)
    return df


def main():
    print(f"[BitterDB] Reading {PROPS_CSV.name} + {NAMES_CSV.name} ...")
    props, names = load_raw()
    print(f"[BitterDB] Props raw rows: {len(props)} | Names raw rows: {len(names)}")
    print(f"[BitterDB] isNatural raw distribution:\n{props['isNatural'].fillna('').value_counts().to_string()}")

    df = to_unified(props, names)
    validate_columns(df.columns)

    n_with_smiles = df["smiles_raw"].notna().sum()
    n_with_name = df["name"].notna().sum()
    print(f"[BitterDB] Rows with SMILES: {n_with_smiles}/{len(df)}")
    print(f"[BitterDB] Rows with name:   {n_with_name}/{len(df)}")
    print(f"[BitterDB] is_natural after mapping:\n{df['is_natural'].fillna('None').astype(str).value_counts().to_string()}")

    OUTPUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT_PARQUET, index=False)
    print(f"[BitterDB] Wrote {len(df)} rows -> {OUTPUT_PARQUET.relative_to(REPO_ROOT)}")
    print(f"[BitterDB] mol_id sample: {df['mol_id'].head(3).tolist()}")


if __name__ == "__main__":
    main()
