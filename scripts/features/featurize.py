"""Day 3 step 1: compute molecular features for master.parquet.

Three feature blocks (SOTA consensus from BitterSweet/e-Sweet/VirtualTaste/ChemSweet):
  - ECFP4 (Morgan radius=2, 1024 bits)   -> binary 0/1
  - MACCS keys (166 bits)                 -> binary 0/1
  - RDKit 2D descriptors (~200 floats)    -> continuous

Concatenated row-wise into X_raw of shape (n_samples, 1024+166+~200).

Outputs (under data/features/):
  X_raw.npy            float32, n x d, raw features (no scaling, no NaN fill)
  y.npy                int8,    n,    binary labels (1=Sweet, 0=NonSweet)
  feature_names.json   list[str] of length d, in same column order
  feature_meta.json    block boundaries + descriptor column names

Day 3 step 2 (split.py) handles NaN imputation, scaling of the
continuous block, and stratified 70/15/15 split.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem, Descriptors, MACCSkeys
from rdkit.Chem.rdFingerprintGenerator import GetMorganGenerator

RDLogger.DisableLog("rdApp.*")

REPO_ROOT = Path(__file__).resolve().parents[2]
MASTER_PARQUET = REPO_ROOT / "data" / "processed" / "master.parquet"
OUT_DIR = REPO_ROOT / "data" / "features"

ECFP_RADIUS = 2          # ECFP4 == Morgan radius 2
ECFP_NBITS = 1024
MACCS_NBITS = 167        # RDKit returns 167 (bit 0 unused, kept for compatibility)


# ----- ECFP4 -----------------------------------------------------------------

_MORGAN_GEN = GetMorganGenerator(radius=ECFP_RADIUS, fpSize=ECFP_NBITS)

def ecfp4(mol: Chem.Mol) -> np.ndarray:
    bv = _MORGAN_GEN.GetFingerprint(mol)
    arr = np.zeros((ECFP_NBITS,), dtype=np.uint8)
    from rdkit.DataStructs import ConvertToNumpyArray
    ConvertToNumpyArray(bv, arr)
    return arr


# ----- MACCS -----------------------------------------------------------------

def maccs(mol: Chem.Mol) -> np.ndarray:
    bv = MACCSkeys.GenMACCSKeys(mol)
    arr = np.zeros((MACCS_NBITS,), dtype=np.uint8)
    from rdkit.DataStructs import ConvertToNumpyArray
    ConvertToNumpyArray(bv, arr)
    return arr


# ----- RDKit 2D descriptors --------------------------------------------------

# RDKit ships ~210 descriptors; some are slow / Ipc has known overflow issues.
# We take all named descriptors and skip Ipc explicitly.
_DESC_LIST = [(name, fn) for name, fn in Descriptors._descList if name != "Ipc"]
DESC_NAMES = [name for name, _ in _DESC_LIST]


def rdkit_2d(mol: Chem.Mol) -> np.ndarray:
    out = np.empty(len(_DESC_LIST), dtype=np.float32)
    for i, (_, fn) in enumerate(_DESC_LIST):
        try:
            out[i] = float(fn(mol))
        except Exception:
            out[i] = np.nan
    return out


# ----- Pipeline --------------------------------------------------------------

def featurize_one(smiles_canonical: str) -> tuple[np.ndarray | None, str | None]:
    """Compute concatenated feature vector for a single molecule.

    Returns (vector, None) on success; (None, reason) on failure.
    """
    mol = Chem.MolFromSmiles(smiles_canonical)
    if mol is None:
        return None, "parse_failed"
    try:
        v_ecfp = ecfp4(mol)
        v_maccs = maccs(mol)
        v_desc = rdkit_2d(mol)
    except Exception as e:
        return None, f"compute_failed:{type(e).__name__}"
    return np.concatenate([v_ecfp.astype(np.float32),
                           v_maccs.astype(np.float32),
                           v_desc.astype(np.float32)]), None


def main():
    print("=" * 60)
    print("Day 3 step 1: featurize")
    print("=" * 60)

    df = pd.read_parquet(MASTER_PARQUET)
    print(f"[load] master.parquet rows={len(df)}")
    assert "smiles_canonical" in df.columns and "is_sweet" in df.columns

    n = len(df)
    d = ECFP_NBITS + MACCS_NBITS + len(DESC_NAMES)
    print(f"[plan] feature dim = {ECFP_NBITS} (ECFP4) + {MACCS_NBITS} (MACCS) + {len(DESC_NAMES)} (RDKit 2D) = {d}")

    X = np.full((n, d), np.nan, dtype=np.float32)
    failures = []
    t0 = time.time()
    for i, smi in enumerate(df["smiles_canonical"]):
        vec, reason = featurize_one(smi)
        if vec is None:
            failures.append((i, df.iloc[i]["mol_id"], reason))
            continue
        X[i] = vec
        if (i + 1) % 500 == 0:
            print(f"  [{i + 1}/{n}] elapsed={time.time() - t0:.1f}s  fail_so_far={len(failures)}")
    print(f"[done] total={time.time() - t0:.1f}s  failures={len(failures)}/{n}")

    if failures:
        print("[failures] sample (first 10):")
        for idx, mid, reason in failures[:10]:
            print(f"  row {idx} {mid}: {reason}")

    # Drop fully-failed rows (defensive — should be 0 because Day 2 already
    # validated SMILES via the same RDKit; we keep the check for safety)
    if failures:
        keep_mask = np.ones(n, dtype=bool)
        for idx, _, _ in failures:
            keep_mask[idx] = False
        X = X[keep_mask]
        df = df[keep_mask].reset_index(drop=True)
        print(f"[filter] kept {len(df)} after featurize failures")

    y = df["is_sweet"].astype(np.int8).to_numpy()

    feature_names = (
        [f"ECFP4_{i}" for i in range(ECFP_NBITS)]
        + [f"MACCS_{i}" for i in range(MACCS_NBITS)]
        + [f"RDKit2D::{n}" for n in DESC_NAMES]
    )
    feature_meta = {
        "n_samples": int(len(df)),
        "n_features": int(X.shape[1]),
        "blocks": {
            "ECFP4":     {"start": 0,                                    "end": ECFP_NBITS,                   "binary": True},
            "MACCS":     {"start": ECFP_NBITS,                           "end": ECFP_NBITS + MACCS_NBITS,     "binary": True},
            "RDKit2D":   {"start": ECFP_NBITS + MACCS_NBITS,             "end": X.shape[1],                   "binary": False},
        },
        "rdkit_descriptor_names": DESC_NAMES,
        "ecfp_radius": ECFP_RADIUS,
        "ecfp_nbits": ECFP_NBITS,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    np.save(OUT_DIR / "X_raw.npy", X)
    np.save(OUT_DIR / "y.npy", y)
    (OUT_DIR / "feature_names.json").write_text(json.dumps(feature_names, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "feature_meta.json").write_text(json.dumps(feature_meta, ensure_ascii=False, indent=2), encoding="utf-8")
    # Persist the row-aligned mol_id list so split.py can reconstruct identity
    df[["mol_id", "name", "source_db", "is_sweet"]].to_parquet(OUT_DIR / "row_index.parquet", index=False)

    # ----- continuous block sanity ----------------------------------------
    desc_block = X[:, ECFP_NBITS + MACCS_NBITS:]
    nan_per_col = np.isnan(desc_block).sum(axis=0)
    print(f"[sanity] RDKit 2D NaN columns: {(nan_per_col > 0).sum()} / {desc_block.shape[1]}")
    if (nan_per_col > 0).any():
        worst = np.argsort(-nan_per_col)[:5]
        for j in worst:
            if nan_per_col[j] > 0:
                print(f"  {DESC_NAMES[j]:30s} NaN={nan_per_col[j]}")

    binary_block = X[:, :ECFP_NBITS + MACCS_NBITS]
    print(f"[sanity] binary block dtype/min/max = {binary_block.dtype} / {binary_block.min()} / {binary_block.max()}")
    print(f"[sanity] X.shape={X.shape}  y.shape={y.shape}  Sweet={int((y==1).sum())} NonSweet={int((y==0).sum())}")

    print(f"\nWrote {OUT_DIR / 'X_raw.npy'}  ({X.nbytes / 1024 / 1024:.1f} MB)")
    print(f"Wrote {OUT_DIR / 'y.npy'}")
    print(f"Wrote {OUT_DIR / 'feature_names.json'}")
    print(f"Wrote {OUT_DIR / 'feature_meta.json'}")
    print(f"Wrote {OUT_DIR / 'row_index.parquet'}")


if __name__ == "__main__":
    main()
