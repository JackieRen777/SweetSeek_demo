"""Day 3 step 2: stratified 70/15/15 split + preprocessing.

Reads X_raw.npy / y.npy from featurize.py, then:
  1. Stratified split: train 70% / val 15% / test 15% (preserves Sweet ratio)
  2. Test set indices are LOCKED — never used for fitting anything, including
     the StandardScaler. Fit-on-train-only is the standard guard against leakage.
  3. Preprocess pipeline:
       - Binary block (ECFP + MACCS): pass through unchanged
       - Continuous block (RDKit 2D): SimpleImputer(mean) -> StandardScaler
     Fit on train only, then transform train + val + test with the same fitted
     preprocessor.
  4. Persist:
       data/features/X.npy            (n, 1407) float32, fully preprocessed
       data/features/splits.json      train/val/test row indices
       data/features/preprocessor.pkl fitted scaler+imputer for inference

Day 4 (training) loads X.npy + y.npy + splits.json and only uses train+val
indices for CV. Test set stays untouched until the final report.
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

REPO_ROOT = Path(__file__).resolve().parents[2]
FEAT_DIR = REPO_ROOT / "data" / "features"

RANDOM_STATE = 42
TEST_FRAC = 0.15
VAL_FRAC = 0.15  # of the full set, so val = 15% / (1 - 15%) of post-test pool


def main():
    print("=" * 60)
    print("Day 3 step 2: split + preprocess")
    print("=" * 60)

    X_raw = np.load(FEAT_DIR / "X_raw.npy")
    y = np.load(FEAT_DIR / "y.npy")
    meta = json.loads((FEAT_DIR / "feature_meta.json").read_text(encoding="utf-8"))
    print(f"[load] X_raw.shape={X_raw.shape}  y.shape={y.shape}  Sweet={int((y==1).sum())} NonSweet={int((y==0).sum())}")

    desc_start = meta["blocks"]["RDKit2D"]["start"]
    desc_end = meta["blocks"]["RDKit2D"]["end"]
    binary_end = desc_start  # ECFP + MACCS occupy [0, desc_start)
    print(f"[blocks] binary=[0:{binary_end}]  continuous=[{desc_start}:{desc_end}]")

    # ---- Step 1: stratified 70/15/15 ----
    n = len(y)
    idx = np.arange(n)

    # First peel off the test set (15%)
    idx_trval, idx_test, y_trval, y_test = train_test_split(
        idx, y, test_size=TEST_FRAC, stratify=y, random_state=RANDOM_STATE
    )
    # Then split remaining 85% into train (70/85) + val (15/85)
    val_relative = VAL_FRAC / (1.0 - TEST_FRAC)
    idx_train, idx_val, y_train, y_val = train_test_split(
        idx_trval, y_trval, test_size=val_relative, stratify=y_trval, random_state=RANDOM_STATE
    )

    def stat(name, ix):
        sw = int((y[ix] == 1).sum())
        ns = int((y[ix] == 0).sum())
        return f"{name}: n={len(ix):4d}  Sweet={sw:3d} ({sw / len(ix):.1%})  NonSweet={ns:4d} ({ns / len(ix):.1%})"

    print("[split]")
    print("  " + stat("train", idx_train))
    print("  " + stat("val  ", idx_val))
    print("  " + stat("test ", idx_test))

    # Sanity: no overlap
    assert len(set(idx_train) & set(idx_val)) == 0
    assert len(set(idx_train) & set(idx_test)) == 0
    assert len(set(idx_val) & set(idx_test)) == 0
    assert len(idx_train) + len(idx_val) + len(idx_test) == n
    print("[split] no overlap, indices sum to n")

    # ---- Step 2: preprocessor — fit on train ONLY ----
    # Binary block (ECFP + MACCS) needs no scaling.
    # Continuous block (RDKit 2D) gets median imputation + StandardScaler.
    # We use 'median' rather than 'mean' because RDKit 2D includes things
    # like NumRadicalElectrons that are 0 for ~99% of rows; 'mean' would be
    # contaminated by occasional outliers. (No NaNs were observed in our
    # data but we keep the imputer for defensive inference-time safety.)
    preprocessor = ColumnTransformer(
        transformers=[
            ("binary", "passthrough", list(range(0, binary_end))),
            ("continuous",
             Pipeline([
                 ("impute", SimpleImputer(strategy="median")),
                 ("scale", StandardScaler()),
             ]),
             list(range(desc_start, desc_end))),
        ],
        remainder="drop",
        sparse_threshold=0,  # always return dense float32-friendly array
    )
    print(f"[preprocess] fitting on {len(idx_train)} train rows ...")
    preprocessor.fit(X_raw[idx_train])

    # Transform full matrix in one go (test rows go through but were not used to fit)
    X = preprocessor.transform(X_raw).astype(np.float32)
    print(f"[preprocess] X.shape after transform = {X.shape}  dtype={X.dtype}")
    assert X.shape == X_raw.shape, "ColumnTransformer changed the column count"

    # ---- Step 3: spot-check no scaling leakage ----
    # Continuous block on train should now be near zero mean / unit std.
    cont_train = X[idx_train, desc_start:desc_end]
    print(f"[check] continuous block on train: mean={cont_train.mean():.4f}  std={cont_train.std():.4f} (expect ~0 / ~1)")
    cont_test = X[idx_test, desc_start:desc_end]
    print(f"[check] continuous block on test:  mean={cont_test.mean():.4f}  std={cont_test.std():.4f} (expect close but not exactly 0/1)")

    # Binary block must still be 0/1
    bin_train = X[idx_train, :binary_end]
    print(f"[check] binary block dtype/min/max = {bin_train.dtype} / {bin_train.min()} / {bin_train.max()} (expect 0/1)")

    # ---- Step 4: persist ----
    np.save(FEAT_DIR / "X.npy", X)
    splits = {
        "train": idx_train.tolist(),
        "val": idx_val.tolist(),
        "test": idx_test.tolist(),
        "random_state": RANDOM_STATE,
        "test_frac": TEST_FRAC,
        "val_frac": VAL_FRAC,
        "n_total": int(n),
        "stratify_by": "is_sweet",
    }
    (FEAT_DIR / "splits.json").write_text(json.dumps(splits), encoding="utf-8")
    with open(FEAT_DIR / "preprocessor.pkl", "wb") as f:
        pickle.dump(preprocessor, f)

    print(f"\nWrote {FEAT_DIR / 'X.npy'} ({X.nbytes / 1024 / 1024:.1f} MB)")
    print(f"Wrote {FEAT_DIR / 'splits.json'}")
    print(f"Wrote {FEAT_DIR / 'preprocessor.pkl'}")


if __name__ == "__main__":
    main()
