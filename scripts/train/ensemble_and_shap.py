"""Day 5: ensemble + Y-randomization + SHAP interpretability.

Pipeline:
  1. Load best RF + XGB from Day 4 (data/models/{rf,xgb}.pkl)
  2. Soft voting ensemble (average probabilities) on val set
  3. Threshold tuning: scan [0.3, 0.7] to find F1-optimal cutoff
  4. Y-randomization: shuffle labels 10 times, retrain RF, confirm AUC collapses
  5. SHAP TreeExplainer: compute feature importance on val set
  6. Map Top-20 SHAP features back to descriptor names

Outputs:
  results/ensemble_val_metrics.csv       (ensemble + threshold-tuned metrics)
  results/y_randomization.csv            (10 shuffled runs, AUC should ~0.5)
  results/shap_values_val.npy            (n_val × n_features SHAP matrix)
  results/shap_top20.csv                 (Top-20 features by |mean SHAP|)
  results/shap_summary.png               (SHAP beeswarm plot, top 20)
"""

from __future__ import annotations

import json
import pickle
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold

REPO_ROOT = Path(__file__).resolve().parents[2]
FEAT_DIR = REPO_ROOT / "data" / "features"
MODEL_DIR = REPO_ROOT / "data" / "models"
RESULTS_DIR = REPO_ROOT / "results"

RANDOM_STATE = 42
N_JOBS = -1


def _load():
    X = np.load(FEAT_DIR / "X.npy")
    y = np.load(FEAT_DIR / "y.npy")
    splits = json.loads((FEAT_DIR / "splits.json").read_text(encoding="utf-8"))
    feature_names = json.loads((FEAT_DIR / "feature_names.json").read_text(encoding="utf-8"))
    with open(MODEL_DIR / "rf.pkl", "rb") as f:
        rf_dict = pickle.load(f)
    with open(MODEL_DIR / "xgb.pkl", "rb") as f:
        xgb_dict = pickle.load(f)
    return X, y, splits, feature_names, rf_dict["model"], xgb_dict["model"]


def _eval_at_threshold(name: str, proba: np.ndarray, y_true: np.ndarray, thr: float) -> dict:
    pred = (proba >= thr).astype(np.int8)
    tn, fp, fn, tp = confusion_matrix(y_true, pred).ravel()
    return {
        "model": name,
        "threshold": thr,
        "n_val": int(len(y_true)),
        "acc": accuracy_score(y_true, pred),
        "f1": f1_score(y_true, pred),
        "precision": precision_score(y_true, pred),
        "recall": recall_score(y_true, pred),
        "roc_auc": roc_auc_score(y_true, proba),
        "pr_auc": average_precision_score(y_true, proba),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }


def _find_best_threshold(proba: np.ndarray, y_true: np.ndarray) -> tuple[float, float]:
    """Scan [0.3, 0.7] in 0.01 steps, return (best_thr, best_f1)."""
    best_thr, best_f1 = 0.5, 0.0
    for thr in np.arange(0.30, 0.71, 0.01):
        pred = (proba >= thr).astype(np.int8)
        f1 = f1_score(y_true, pred)
        if f1 > best_f1:
            best_f1, best_thr = f1, thr
    return best_thr, best_f1


def _y_randomization(X_tr: np.ndarray, y_tr: np.ndarray, X_va: np.ndarray, y_va: np.ndarray, n_runs: int = 10) -> pd.DataFrame:
    """Shuffle TRAIN labels n_runs times, retrain RF, test on REAL val (unshuffled).

    Null hypothesis: if model learns X→y structure, shuffling y should collapse val AUC to ~0.5.
    """
    print(f"\n[Y-randomization] {n_runs} runs (expect val AUC ~0.5 if model learns real signal)")
    rows = []
    # Use Day 4 best RF params
    for i in range(n_runs):
        rng = np.random.RandomState(RANDOM_STATE + i)
        y_shuffled = rng.permutation(y_tr)
        rf = RandomForestClassifier(
            n_estimators=500, max_depth=10, min_samples_split=2, min_samples_leaf=1,
            class_weight="balanced", random_state=RANDOM_STATE, n_jobs=N_JOBS
        )
        rf.fit(X_tr, y_shuffled)
        # Test on REAL validation set (y_va is NOT shuffled)
        proba = rf.predict_proba(X_va)[:, 1]
        auc = roc_auc_score(y_va, proba)
        rows.append({"run": i + 1, "val_auc": float(auc)})
        print(f"  run {i+1}/{n_runs}: val AUC={auc:.4f}")
    return pd.DataFrame(rows)


def _shap_analysis(rf_model, X_val: np.ndarray, feature_names: list[str]) -> tuple[np.ndarray, pd.DataFrame]:
    """Compute SHAP values for RF only (XGBoost 3.2.0 has compatibility issues with SHAP 0.46.0).

    Return SHAP matrix (n_val × n_features) and Top-20 features by |mean SHAP|.
    """
    print("\n[SHAP] TreeExplainer on RF (validation set) ...")
    t0 = time.time()

    explainer_rf = shap.TreeExplainer(rf_model, feature_perturbation="tree_path_dependent")
    shap_rf = explainer_rf.shap_values(X_val)

    # RF binary classifier returns [class_0_shap, class_1_shap] or (n, d, 2)
    if isinstance(shap_rf, list):
        shap_rf = shap_rf[1]  # class 1 (Sweet)
    elif shap_rf.ndim == 3:
        shap_rf = shap_rf[:, :, 1]  # (n, d, 2) -> (n, d) for class 1

    print(f"[SHAP] done in {time.time() - t0:.1f}s | shape={shap_rf.shape}")

    # Aggregate: mean |SHAP| per feature
    mean_abs_shap = np.abs(shap_rf).mean(axis=0)
    top_idx = np.argsort(-mean_abs_shap)[:20]
    top_df = pd.DataFrame({
        "rank": range(1, 21),
        "feature_idx": [int(i) for i in top_idx],
        "feature_name": [feature_names[int(i)] for i in top_idx],
        "mean_abs_shap": [float(mean_abs_shap[int(i)]) for i in top_idx],
    })
    return shap_rf, top_df


def _plot_shap_summary(shap_values: np.ndarray, X_val: np.ndarray, feature_names: list[str], top_idx: np.ndarray):
    """SHAP beeswarm plot for top 20 features."""
    shap_top = shap_values[:, top_idx]
    X_top = X_val[:, top_idx]
    names_top = [feature_names[i] for i in top_idx]

    plt.figure(figsize=(10, 8))
    shap.summary_plot(shap_top, X_top, feature_names=names_top, show=False, max_display=20)
    plt.tight_layout()
    out_path = RESULTS_DIR / "shap_summary.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[SHAP] plot saved to {out_path.relative_to(REPO_ROOT)}")


def main():
    print("=" * 60)
    print("Day 5: ensemble + Y-randomization + SHAP")
    print("=" * 60)

    X, y, splits, feature_names, rf_model, xgb_model = _load()
    idx_train = np.array(splits["train"], dtype=int)
    idx_val = np.array(splits["val"], dtype=int)
    X_tr, y_tr = X[idx_train], y[idx_train]
    X_va, y_va = X[idx_val], y[idx_val]
    print(f"[load] train={len(idx_train)}  val={len(idx_val)}")

    # ---- 1. Ensemble (soft voting) ----
    proba_rf = rf_model.predict_proba(X_va)[:, 1]
    proba_xgb = xgb_model.predict_proba(X_va)[:, 1]
    proba_ens = (proba_rf + proba_xgb) / 2.0

    # Default threshold 0.5
    ens_default = _eval_at_threshold("Ensemble(RF+XGB)", proba_ens, y_va, 0.5)
    print(f"\n[ensemble @ thr=0.5] F1={ens_default['f1']:.4f}  Acc={ens_default['acc']:.4f}  AUC={ens_default['roc_auc']:.4f}")

    # ---- 2. Threshold tuning ----
    best_thr, best_f1 = _find_best_threshold(proba_ens, y_va)
    ens_tuned = _eval_at_threshold("Ensemble(tuned)", proba_ens, y_va, best_thr)
    print(f"[ensemble @ thr={best_thr:.2f}] F1={ens_tuned['f1']:.4f}  Acc={ens_tuned['acc']:.4f}  (F1 gain={ens_tuned['f1'] - ens_default['f1']:.4f})")

    ens_df = pd.DataFrame([ens_default, ens_tuned])
    ens_df.to_csv(RESULTS_DIR / "ensemble_val_metrics.csv", index=False)
    print(f"\n[persist] {RESULTS_DIR / 'ensemble_val_metrics.csv'}")

    # ---- 3. Y-randomization ----
    y_rand_df = _y_randomization(X_tr, y_tr, X_va, y_va, n_runs=10)
    y_rand_df.to_csv(RESULTS_DIR / "y_randomization.csv", index=False)
    print(f"[persist] {RESULTS_DIR / 'y_randomization.csv'}")
    print(f"[Y-rand] mean val AUC across 10 runs = {y_rand_df['val_auc'].mean():.4f} (expect ~0.5)")

    # ---- 4. SHAP ----
    shap_vals, top20 = _shap_analysis(rf_model, X_va, feature_names)
    np.save(RESULTS_DIR / "shap_values_val.npy", shap_vals)
    top20.to_csv(RESULTS_DIR / "shap_top20.csv", index=False)
    print(f"[persist] {RESULTS_DIR / 'shap_values_val.npy'}  shape={shap_vals.shape}")
    print(f"[persist] {RESULTS_DIR / 'shap_top20.csv'}")
    print("\n[SHAP Top-5]")
    print(top20.head(5).to_string(index=False))

    _plot_shap_summary(shap_vals, X_va, feature_names, top20["feature_idx"].values)

    # ---- Day 5 self-check ----
    print("\n" + "=" * 60)
    print("Day 5 self-check")
    print("=" * 60)
    f1_pass = ens_tuned["f1"] >= 0.80
    y_rand_pass = y_rand_df["val_auc"].mean() < 0.60
    print(f"  [{'PASS' if f1_pass else 'REVIEW'}] Ensemble F1 >= 0.80: {ens_tuned['f1']:.4f}")
    print(f"  [{'PASS' if y_rand_pass else 'REVIEW'}] Y-randomization val AUC < 0.60: {y_rand_df['val_auc'].mean():.4f}")
    print(f"  [INFO] Top SHAP feature: {top20.iloc[0]['feature_name']} (|SHAP|={top20.iloc[0]['mean_abs_shap']:.4f})")


if __name__ == "__main__":
    main()
