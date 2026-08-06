"""Day 4: train RF + XGBoost on the train split, tune via 5-fold CV, then
report validation metrics. The test set is NEVER touched here.

Pipeline:
  1. Load X.npy / y.npy / splits.json from data/features/
  2. For each model:
       - Build a small grid + StratifiedKFold(5) on the train split
       - Refit best estimator on the full train split
       - Score on val (Acc / F1 / ROC-AUC / PR-AUC / confusion matrix)
  3. Persist:
       data/models/rf.pkl
       data/models/xgb.pkl
       results/cv_results.csv         (one row per (model, params) combo)
       results/val_metrics.csv        (one row per model — validation set)
       results/val_roc.csv            (fpr/tpr per model for plotting)

Imbalance handling:
  - RF      : class_weight='balanced' (sklearn handles per-class reweighting)
  - XGBoost : scale_pos_weight = NonSweet/Sweet ratio on TRAIN ONLY
              (computed from y[train] so val/test stay isolated)
"""

from __future__ import annotations

import json
import pickle
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from xgboost import XGBClassifier

REPO_ROOT = Path(__file__).resolve().parents[2]
FEAT_DIR = REPO_ROOT / "data" / "features"
MODEL_DIR = REPO_ROOT / "data" / "models"
RESULTS_DIR = REPO_ROOT / "results"

RANDOM_STATE = 42
N_FOLDS = 5
N_JOBS = -1
SCORING = "f1"  # primary tuning metric; we still log all metrics


def _load():
    X = np.load(FEAT_DIR / "X.npy")
    y = np.load(FEAT_DIR / "y.npy")
    splits = json.loads((FEAT_DIR / "splits.json").read_text(encoding="utf-8"))
    return X, y, splits


def _eval(name: str, model, X_val, y_val) -> dict:
    proba = model.predict_proba(X_val)[:, 1]
    pred = (proba >= 0.5).astype(np.int8)
    tn, fp, fn, tp = confusion_matrix(y_val, pred).ravel()
    return {
        "model": name,
        "n_val": int(len(y_val)),
        "acc": accuracy_score(y_val, pred),
        "f1": f1_score(y_val, pred),
        "precision": precision_score(y_val, pred),
        "recall": recall_score(y_val, pred),
        "roc_auc": roc_auc_score(y_val, proba),
        "pr_auc": average_precision_score(y_val, proba),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }


def _roc_rows(name: str, model, X_val, y_val) -> pd.DataFrame:
    proba = model.predict_proba(X_val)[:, 1]
    fpr, tpr, thr = roc_curve(y_val, proba)
    return pd.DataFrame({"model": name, "fpr": fpr, "tpr": tpr, "threshold": thr})


def _grid_search(name: str, estimator, grid: dict, X_tr, y_tr) -> GridSearchCV:
    cv = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    print(f"\n[{name}] grid={grid}  cv={N_FOLDS}-fold  scoring={SCORING}")
    t0 = time.time()
    gs = GridSearchCV(
        estimator=estimator,
        param_grid=grid,
        scoring=SCORING,
        cv=cv,
        n_jobs=N_JOBS,
        refit=True,
        return_train_score=False,
        verbose=1,
    )
    gs.fit(X_tr, y_tr)
    print(f"[{name}] best params: {gs.best_params_}")
    print(f"[{name}] best CV {SCORING} = {gs.best_score_:.4f}  | elapsed={time.time() - t0:.1f}s")
    return gs


def _cv_table(name: str, gs: GridSearchCV) -> pd.DataFrame:
    cv = pd.DataFrame(gs.cv_results_)
    cols = ["params", "mean_test_score", "std_test_score", "rank_test_score", "mean_fit_time"]
    out = cv[cols].copy()
    out.insert(0, "model", name)
    out["params"] = out["params"].apply(json.dumps)
    return out.sort_values("rank_test_score").reset_index(drop=True)


def main():
    print("=" * 60)
    print("Day 4: train RF + XGBoost (CV on train, eval on val)")
    print("=" * 60)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    X, y, splits = _load()
    idx_train = np.array(splits["train"], dtype=int)
    idx_val = np.array(splits["val"], dtype=int)
    idx_test = np.array(splits["test"], dtype=int)
    X_tr, y_tr = X[idx_train], y[idx_train]
    X_va, y_va = X[idx_val], y[idx_val]
    print(f"[load] X={X.shape}  train={len(idx_train)}  val={len(idx_val)}  test(LOCKED)={len(idx_test)}")

    # imbalance — compute ON TRAIN ONLY to keep val/test isolated
    n_pos = int((y_tr == 1).sum())
    n_neg = int((y_tr == 0).sum())
    spw = n_neg / max(n_pos, 1)
    print(f"[imbalance] train Sweet={n_pos}  NonSweet={n_neg}  scale_pos_weight={spw:.3f}")

    # ---------- Random Forest ----------
    rf = RandomForestClassifier(
        random_state=RANDOM_STATE,
        n_jobs=N_JOBS,
        class_weight="balanced",
    )
    rf_grid = {
        "n_estimators": [100, 300, 500],
        "max_depth": [10, 20, None],
        "min_samples_split": [2],
        "min_samples_leaf": [1],
    }
    rf_gs = _grid_search("RF", rf, rf_grid, X_tr, y_tr)

    # ---------- XGBoost ----------
    xgb = XGBClassifier(
        random_state=RANDOM_STATE,
        n_jobs=N_JOBS,
        eval_metric="logloss",
        scale_pos_weight=spw,
        tree_method="hist",
    )
    xgb_grid = {
        "n_estimators": [100, 300],
        "max_depth": [3, 6, 9],
        "learning_rate": [0.01, 0.1],
    }
    xgb_gs = _grid_search("XGB", xgb, xgb_grid, X_tr, y_tr)

    # ---------- Persist CV grids ----------
    cv_table = pd.concat([_cv_table("RF", rf_gs), _cv_table("XGB", xgb_gs)], ignore_index=True)
    cv_path = RESULTS_DIR / "cv_results.csv"
    cv_table.to_csv(cv_path, index=False)
    print(f"\n[persist] {cv_path.relative_to(REPO_ROOT)}  rows={len(cv_table)}")

    # ---------- Validation eval ----------
    rf_best = rf_gs.best_estimator_
    xgb_best = xgb_gs.best_estimator_
    val_rows = [_eval("RF", rf_best, X_va, y_va), _eval("XGB", xgb_best, X_va, y_va)]
    val_df = pd.DataFrame(val_rows)
    val_df.to_csv(RESULTS_DIR / "val_metrics.csv", index=False)
    print("\n[validation]")
    print(val_df.to_string(index=False, float_format=lambda v: f"{v:.4f}"))

    roc_df = pd.concat([_roc_rows("RF", rf_best, X_va, y_va),
                         _roc_rows("XGB", xgb_best, X_va, y_va)], ignore_index=True)
    roc_df.to_csv(RESULTS_DIR / "val_roc.csv", index=False)

    # ---------- Persist models ----------
    with open(MODEL_DIR / "rf.pkl", "wb") as f:
        pickle.dump({"model": rf_best, "best_params": rf_gs.best_params_,
                     "best_cv_f1": float(rf_gs.best_score_)}, f)
    with open(MODEL_DIR / "xgb.pkl", "wb") as f:
        pickle.dump({"model": xgb_best, "best_params": xgb_gs.best_params_,
                     "best_cv_f1": float(xgb_gs.best_score_),
                     "scale_pos_weight": float(spw)}, f)
    print(f"\n[persist] {MODEL_DIR / 'rf.pkl'}")
    print(f"[persist] {MODEL_DIR / 'xgb.pkl'}")

    # ---------- Day-4 self-check ----------
    print("\n" + "=" * 60)
    print("Day 4 self-check")
    print("=" * 60)
    print(f"  test set untouched : True (never indexed in this script)")
    targets = {"acc": 0.85, "f1": 0.80}
    for row in val_rows:
        ok_acc = row["acc"] >= targets["acc"]
        ok_f1 = row["f1"] >= targets["f1"]
        flag = "PASS" if (ok_acc and ok_f1) else "REVIEW"
        print(f"  [{flag}] {row['model']}: acc={row['acc']:.4f} (>={targets['acc']})  f1={row['f1']:.4f} (>={targets['f1']})")


if __name__ == "__main__":
    main()
