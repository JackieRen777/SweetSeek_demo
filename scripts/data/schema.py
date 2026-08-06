"""Unified schema for the merged sweet/bitter ML dataset.

Every adapter in scripts/data/fetch_*.py must produce a DataFrame with
exactly these columns. Downstream merge/featurize/train scripts consume
the unified schema, never the source-specific columns.

4 layers:
  - Identity:       molecule itself (SMILES variants, InChIKey)
  - Provenance:     where the row came from (DB, IDs, refs)
  - Targets:        labels for ML (raw + canonicalized)
  - Stratification: features used to split / balance, not features used
                    to train (those are computed by featurize.py)
"""

from __future__ import annotations

# --- Identity ------------------------------------------------------------
# mol_id        Our primary key, e.g. "CTD-0001" / "BDB-7"
# name          Common chemical name (Unicode allowed)
# smiles_raw    The SMILES string as the source DB provided it
# smiles_canonical  Day 2: RDKit canonical SMILES after salt removal + neutralize
# inchi         Day 2: InChI string
# inchi_key     Day 2: 27-char InChIKey, used as cross-DB dedup key

IDENTITY_COLUMNS = [
    "mol_id",
    "name",
    "smiles_raw",
    "smiles_canonical",
    "inchi",
    "inchi_key",
]

# --- Provenance ----------------------------------------------------------
# source_db     "ChemTastesDB" | "BitterDB"
# source_id     Original ID in that DB (string, never int)
# source_refs   Citation codes joined by "; "
# pubchem_cid   PubChem CID, may be empty
# cas_number    CAS, may be empty

PROVENANCE_COLUMNS = [
    "source_db",
    "source_id",
    "source_refs",
    "pubchem_cid",
    "cas_number",
]

# --- Targets -------------------------------------------------------------
# taste_class_raw   The label as the source DB phrased it
#                   (ChemTastesDB "Class taste" enum, or const "Bitter" for BDB)
# taste_class       Day 2: canonicalized to {"Sweet","Bitter","Tasteless",
#                   "NonSweet","Umami","Sour","Salty","Multitaste",
#                   "Miscellaneous"}
# is_sweet          Day 2: 0/1 binary target for V1
# label_confidence  Day 2: "high" if from ChemTastesDB curated, "medium" if BDB,
#                   used for tie-breaking on conflict

TARGETS_COLUMNS = [
    "taste_class_raw",
    "taste_class",
    "is_sweet",
    "label_confidence",
]

# --- Stratification ------------------------------------------------------
# is_natural    1=natural, 0=synthetic, None=unknown
# mw            Day 2: molecular weight from canonical mol
# n_heavy_atoms Day 2: heavy atom count

STRATIFICATION_COLUMNS = [
    "is_natural",
    "mw",
    "n_heavy_atoms",
]

UNIFIED_COLUMNS = (
    IDENTITY_COLUMNS
    + PROVENANCE_COLUMNS
    + TARGETS_COLUMNS
    + STRATIFICATION_COLUMNS
)


def empty_unified_row() -> dict:
    """Return a dict with all unified columns set to None.

    Adapters use this as a starting point so missing fields are explicit
    rather than being silently dropped.
    """
    return {col: None for col in UNIFIED_COLUMNS}


def validate_columns(df_columns) -> None:
    """Raise if a DataFrame is missing any unified column."""
    missing = set(UNIFIED_COLUMNS) - set(df_columns)
    extra = set(df_columns) - set(UNIFIED_COLUMNS)
    if missing:
        raise ValueError(f"Missing unified columns: {sorted(missing)}")
    if extra:
        raise ValueError(f"Unexpected columns (rename or drop): {sorted(extra)}")
