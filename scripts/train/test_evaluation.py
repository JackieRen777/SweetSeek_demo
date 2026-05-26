"""Day 8: Final test set evaluation.

CRITICAL: This is the FIRST and ONLY time we touch the test set.
All previous work (Day 4-5) used only train + val.

Pipeline:
  1. Load best ensemble (RF + XGB) from Day 4
  2. Load test set indices from splits.json (577 rows, NEVER used before)
  3. Predict on test set with Day 5 tuned threshold (0.36)
  4. Report full metrics: Acc / F1 / Precision / Recall / ROC-AUC / PR-AUC
  5. Confusion matrix
  6. Compare test vs val performance (sanity check for overfitting)
  7. Per-class breakdown (Sweet vs NonSweet)

Outputs:
  results/test_metrics.csv          (final test performance)
  results/test_confusion.csv        (confusion matrix)
  results/test_roc.csv              (ROC curve points)
  results/test_pr.csv               (PR curve points)
  results/final_report.txt          (human-readable summary)
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FEAT_DIR = REPO_ROOT / "data" / "features"
MODEL_DIR = REPO_ROOT / "data" / "models"
RESULTS_DIR = REPO_ROOT / "results"

THRESHOLD = 0.36  # Day 5 tuned threshold


def _load():
    X = np.load(FEAT_DIR / "X.npy")
    y = np.load(FEAT_DIR / "y.npy")
    splits = json.loads((FEAT_DIR / "splits.json").read_text(encoding="utf-8"))
    with open(MODEL_DIR / "rf.pkl", "rb") as f:
        rf_model = pickle.load(f)["model"]
    with open(MODEL_DIR / "xgb.pkl", "rb") as f:
        xgb_model = pickle.load(f)["model"]
    return X, y, splits, rf_model, xgb_model


def _eval_metrics(y_true: np.ndarray, proba: np.ndarray, threshold: float) -> dict:
    pred = (proba >= threshold).astype(np.int8)
    tn, fp, fn, tp = confusion_matrix(y_true, pred).ravel()
    return {
        "n": int(len(y_true)),
        "threshold": threshold,
        "acc": accuracy_score(y_true, pred),
        "f1": f1_score(y_true, pred),
        "precision": precision_score(y_true, pred),
        "recall": recall_score(y_true, pred),
        "roc_auc": roc_auc_score(y_true, proba),
        "pr_auc": average_precision_score(y_true, proba),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }


def main():
    print("=" * 60)
    print("Day 8: FINAL TEST SET EVALUATION")
    print("=" * 60)
    print("⚠️  WARNING: This is the FIRST time we access the test set.")
    print("⚠️  All hyperparameters were tuned on train+val ONLY.\n")

    X, y, splits, rf_model, xgb_model = _load()
    idx_val = np.array(splits["val"], dtype=int)
    idx_test = np.array(splits["test"], dtype=int)
    X_va, y_va = X[idx_val], y[idx_val]
    X_te, y_te = X[idx_test], y[idx_test]

    print(f"[load] val={len(idx_val)}  test={len(idx_test)}")
    print(f"[test] Sweet={int((y_te == 1).sum())}  NonSweet={int((y_te == 0).sum())}")
    print(f"       Sweet ratio={float((y_te == 1).mean()):.4f}\n")

    # ---- Ensemble prediction ----
    proba_rf_te = rf_model.predict_proba(X_te)[:, 1]
    proba_xgb_te = xgb_model.predict_proba(X_te)[:, 1]
    proba_ens_te = (proba_rf_te + proba_xgb_te) / 2.0

    proba_rf_va = rf_model.predict_proba(X_va)[:, 1]
    proba_xgb_va = xgb_model.predict_proba(X_va)[:, 1]
    proba_ens_va = (proba_rf_va + proba_xgb_va) / 2.0

    # ---- Metrics ----
    test_metrics = _eval_metrics(y_te, proba_ens_te, THRESHOLD)
    val_metrics = _eval_metrics(y_va, proba_ens_va, THRESHOLD)

    print("=" * 60)
    print("VALIDATION SET (Day 5 reference)")
    print("=" * 60)
    print(f"  n={val_metrics['n']}")
    print(f"  Accuracy:  {val_metrics['acc']:.4f}")
    print(f"  F1:        {val_metrics['f1']:.4f}")
    print(f"  Precision: {val_metrics['precision']:.4f}")
    print(f"  Recall:    {val_metrics['recall']:.4f}")
    print(f"  ROC-AUC:   {val_metrics['roc_auc']:.4f}")
    print(f"  PR-AUC:    {val_metrics['pr_auc']:.4f}")
    print(f"  Confusion: TN={val_metrics['tn']} FP={val_metrics['fp']} FN={val_metrics['fn']} TP={val_metrics['tp']}\n")

    print("=" * 60)
    print("TEST SET (FINAL EVALUATION)")
    print("=" * 60)
    print(f"  n={test_metrics['n']}")
    print(f"  Accuracy:  {test_metrics['acc']:.4f}")
    print(f"  F1:        {test_metrics['f1']:.4f}")
    print(f"  Precision: {test_metrics['precision']:.4f}")
    print(f"  Recall:    {test_metrics['recall']:.4f}")
    print(f"  ROC-AUC:   {test_metrics['roc_auc']:.4f}")
    print(f"  PR-AUC:    {test_metrics['pr_auc']:.4f}")
    print(f"  Confusion: TN={test_metrics['tn']} FP={test_metrics['fp']} FN={test_metrics['fn']} TP={test_metrics['tp']}\n")

    # ---- Comparison ----
    print("=" * 60)
    print("VAL vs TEST COMPARISON")
    print("=" * 60)
    for metric in ["acc", "f1", "precision", "recall", "roc_auc", "pr_auc"]:
        val_v = val_metrics[metric]
        test_v = test_metrics[metric]
        diff = test_v - val_v
        sign = "+" if diff >= 0 else ""
        print(f"  {metric:10s}  val={val_v:.4f}  test={test_v:.4f}  diff={sign}{diff:.4f}")

    # ---- ROC + PR curves ----
    fpr_te, tpr_te, _ = roc_curve(y_te, proba_ens_te)
    precision_te, recall_te, _ = precision_recall_curve(y_te, proba_ens_te)

    roc_df = pd.DataFrame({"fpr": fpr_te, "tpr": tpr_te})
    pr_df = pd.DataFrame({"precision": precision_te, "recall": recall_te})

    # ---- Persist ----
    pd.DataFrame([test_metrics]).to_csv(RESULTS_DIR / "test_metrics.csv", index=False)
    pd.DataFrame([
        {"actual": "NonSweet", "pred": "NonSweet", "n": test_metrics["tn"]},
        {"actual": "NonSweet", "pred": "Sweet", "n": test_metrics["fp"]},
        {"actual": "Sweet", "pred": "NonSweet", "n": test_metrics["fn"]},
        {"actual": "Sweet", "pred": "Sweet", "n": test_metrics["tp"]},
    ]).to_csv(RESULTS_DIR / "test_confusion.csv", index=False)
    roc_df.to_csv(RESULTS_DIR / "test_roc.csv", index=False)
    pr_df.to_csv(RESULTS_DIR / "test_pr.csv", index=False)

    # ---- Final report ----
    report = f"""
SweetSeek V1 - Final Test Set Evaluation Report
================================================

Date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
Model: Ensemble (RF + XGBoost), threshold={THRESHOLD}

TEST SET PERFORMANCE (n={test_metrics['n']}, Sweet={int((y_te == 1).sum())}, NonSweet={int((y_te == 0).sum())}):
  Accuracy:  {test_metrics['acc']:.4f}
  F1 Score:  {test_metrics['f1']:.4f}
  Precision: {test_metrics['precision']:.4f}
  Recall:    {test_metrics['recall']:.4f}
  ROC-AUC:   {test_metrics['roc_auc']:.4f}
  PR-AUC:    {test_metrics['pr_auc']:.4f}

CONFUSION MATRIX:
                Predicted NonSweet  Predicted Sweet
  Actual NonSweet      {test_metrics['tn']:4d}              {test_metrics['fp']:4d}
  Actual Sweet         {test_metrics['fn']:4d}              {test_metrics['tp']:4d}

VAL vs TEST GENERALIZATION:
  Accuracy:  val={val_metrics['acc']:.4f}  test={test_metrics['acc']:.4f}  (diff={test_metrics['acc'] - val_metrics['acc']:+.4f})
  F1:        val={val_metrics['f1']:.4f}  test={test_metrics['f1']:.4f}  (diff={test_metrics['f1'] - val_metrics['f1']:+.4f})
  ROC-AUC:   val={val_metrics['roc_auc']:.4f}  test={test_metrics['roc_auc']:.4f}  (diff={test_metrics['roc_auc'] - val_metrics['roc_auc']:+.4f})

CONCLUSION:
  {'✓ Test performance matches validation, no overfitting detected.' if abs(test_metrics['f1'] - val_metrics['f1']) < 0.05 else '⚠ Test performance differs from validation by >0.05 F1, investigate further.'}
  {'✓ F1 >= 0.80 target achieved.' if test_metrics['f1'] >= 0.80 else '⚠ F1 < 0.80, consider retuning threshold or model.'}
  {'✓ ROC-AUC >= 0.95, strong ranking ability.' if test_metrics['roc_auc'] >= 0.95 else '⚠ ROC-AUC < 0.95, ranking ability moderate.'}

FILES GENERATED:
  - results/test_metrics.csv
  - results/test_confusion.csv
  - results/test_roc.csv
  - results/test_pr.csv
  - results/final_report.txt
"""
    (RESULTS_DIR / "final_report.txt").write_text(report, encoding="utf-8")

    print("\n" + "=" * 60)
    print("FILES WRITTEN")
    print("=" * 60)
    print(f"  {RESULTS_DIR / 'test_metrics.csv'}")
    print(f"  {RESULTS_DIR / 'test_confusion.csv'}")
    print(f"  {RESULTS_DIR / 'test_roc.csv'}")
    print(f"  {RESULTS_DIR / 'test_pr.csv'}")
    print(f"  {RESULTS_DIR / 'final_report.txt'}")
    print("\n✅ Day 8 test set evaluation complete.")


if __name__ == "__main__":
    main()
