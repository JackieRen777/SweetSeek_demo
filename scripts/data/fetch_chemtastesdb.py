"""ChemTastesDB v1.2 adapter.

Reads data/raw/chemtastesdb_v1.1/ChemTastesDB_database.xlsx and emits
data/interim/chemtastesdb.parquet conforming to scripts/data/schema.UNIFIED_COLUMNS.

Day 1 scope:
  - read xlsx with ID as string ("0001" not 1)
  - strip trailing whitespace / NBSP from text columns
  - map source columns -> unified column names
  - DO NOT standardize SMILES yet (that runs in merge step on Day 2)
  - DO NOT canonicalize taste_class yet (Day 2)
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
SOURCE_XLSX = REPO_ROOT / "data" / "raw" / "chemtastesdb_v1.1" / "ChemTastesDB_database.xlsx"
OUTPUT_PARQUET = REPO_ROOT / "data" / "interim" / "chemtastesdb.parquet"


def _clean_text(value):
    """Strip ASCII whitespace + NBSP from a cell, keep None for null/empty."""
    if pd.isna(value):
        return None
    s = str(value).replace("\xa0", " ").strip()
    return s if s else None


def load_raw() -> pd.DataFrame:
    """Read the source xlsx with the ID column forced to string."""
    if not SOURCE_XLSX.exists():
        raise FileNotFoundError(
            f"Source file not found: {SOURCE_XLSX}\n"
            f"Re-download per data/raw/README.md."
        )
    df = pd.read_excel(SOURCE_XLSX, dtype={"ID": str})
    return df


def to_unified(raw: pd.DataFrame) -> pd.DataFrame:
    """Map ChemTastesDB columns to the unified schema."""
    rows = []
    for _, r in raw.iterrows():
        row = empty_unified_row()
        # Identity
        row["mol_id"] = f"CTD-{_clean_text(r['ID'])}"
        row["name"] = _clean_text(r["Name"])
        row["smiles_raw"] = _clean_text(r["canonical SMILES"])
        # Provenance
        row["source_db"] = "ChemTastesDB"
        row["source_id"] = _clean_text(r["ID"])
        row["source_refs"] = _clean_text(r["Reference_(cod)/[pp]"])
        cid = r["PubChem CID"]
        row["pubchem_cid"] = None if pd.isna(cid) else str(int(cid)) if isinstance(cid, (int, float)) else str(cid).strip()
        row["cas_number"] = _clean_text(r["CAS number"])
        # Targets (raw only on Day 1)
        row["taste_class_raw"] = _clean_text(r["Class taste"])
        # taste_class / is_sweet / label_confidence -> filled in merge step
        # Stratification
        # is_natural unknown for ChemTastesDB -> None
        # mw / n_heavy_atoms computed in merge step from canonical mol
        rows.append(row)

    df = pd.DataFrame(rows, columns=UNIFIED_COLUMNS)
    return df


def main():
    print(f"[ChemTastesDB] Reading {SOURCE_XLSX.name} ...")
    raw = load_raw()
    print(f"[ChemTastesDB] Raw rows: {len(raw)}")
    print(f"[ChemTastesDB] Class taste distribution:\n{raw['Class taste'].value_counts(dropna=False).to_string()}")

    df = to_unified(raw)
    validate_columns(df.columns)

    OUTPUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT_PARQUET, index=False)
    print(f"[ChemTastesDB] Wrote {len(df)} rows -> {OUTPUT_PARQUET.relative_to(REPO_ROOT)}")
    print(f"[ChemTastesDB] Unique taste_class_raw: {df['taste_class_raw'].nunique()}")
    print(f"[ChemTastesDB] mol_id sample: {df['mol_id'].head(3).tolist()}")


if __name__ == "__main__":
    main()
