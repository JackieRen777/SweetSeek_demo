"""BrixDB sweetness regression pilot experiment.
Full pipeline: featurize → split → train → evaluate → SHAP → plot.
"""
import json, pickle, warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import pearsonr

from sklearn.model_selection import train_test_split, GridSearchCV, KFold
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

import shap

warnings.filterwarnings("ignore")

ROOT = Path("/Users/jackieren/Desktop/FCN_SweetSeek")
DATA_OUT = ROOT / "data/regression"
RESULTS = ROOT / "results/regression"
DATA_OUT.mkdir(parents=True, exist_ok=True)
RESULTS.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42
# ─── Step 1: Featurize ─────────────────────────────────────────────────────────

print("Step 1: Feature engineering (using V1 featurize logic)...")

import sys
sys.path.insert(0, str(ROOT))

BRIXDB = Path("/Users/jackieren/Desktop/回归/BrixDB.xlsx")
df = pd.read_excel(BRIXDB)
df = df.dropna(subset=["SMILES", "logSw"]).reset_index(drop=True)

from scripts.features.featurize import ecfp4, maccs, rdkit_2d, DESC_NAMES, ECFP_NBITS, MACCS_NBITS
from rdkit import Chem

feature_names = (
    [f"ECFP4_{i}" for i in range(ECFP_NBITS)]
    + [f"MACCS_{i}" for i in range(MACCS_NBITS)]
    + [f"RDKit2D::{n}" for n in DESC_NAMES]
)

X_list, y_list, valid_idx = [], [], []
for i, row in df.iterrows():
    mol = Chem.MolFromSmiles(row["SMILES"])
    if mol is None:
        continue
    try:
        vec = np.concatenate([
            ecfp4(mol).astype(np.float32),
            maccs(mol).astype(np.float32),
            rdkit_2d(mol).astype(np.float32),
        ])
        X_list.append(vec)
        y_list.append(row["logSw"])
        valid_idx.append(i)
    except Exception:
        continue

X_raw = np.array(X_list, dtype=np.float32)
y = np.array(y_list, dtype=np.float32)
print(f"  Featurized: {X_raw.shape[0]} molecules, {X_raw.shape[1]} features")
# ─── Step 2: Split + Preprocess ────────────────────────────────────────────────

print("Step 2: Splitting 70/15/15...")

idx_all = np.arange(len(y))
idx_train_val, idx_test = train_test_split(idx_all, test_size=0.15, random_state=RANDOM_STATE)
val_rel = 0.15 / 0.85
idx_train, idx_val = train_test_split(idx_train_val, test_size=val_rel, random_state=RANDOM_STATE)

print(f"  Train: {len(idx_train)}, Val: {len(idx_val)}, Test: {len(idx_test)}")

n_binary = ECFP_NBITS + MACCS_NBITS  # ECFP4 + MACCS
binary_cols = list(range(n_binary))
cont_cols = list(range(n_binary, X_raw.shape[1]))

preproc = ColumnTransformer([
    ("binary", "passthrough", binary_cols),
    ("continuous", Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
    ]), cont_cols),
])

preproc.fit(X_raw[idx_train])
X = preproc.transform(X_raw).astype(np.float32)

X_train, y_train = X[idx_train], y[idx_train]
X_val, y_val = X[idx_val], y[idx_val]
X_test, y_test = X[idx_test], y[idx_test]

np.save(DATA_OUT / "X.npy", X)
np.save(DATA_OUT / "y.npy", y)
json.dump({"train": idx_train.tolist(), "val": idx_val.tolist(), "test": idx_test.tolist()},
          open(DATA_OUT / "splits.json", "w"))
json.dump(feature_names, open(DATA_OUT / "feature_names.json", "w"))
pickle.dump(preproc, open(DATA_OUT / "preprocessor.pkl", "wb"))
# ─── Step 3: Model Training ────────────────────────────────────────────────────

print("Step 3: Training RF + XGBoost regressors...")

from xgboost import XGBRegressor

cv = KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)

rf_grid = {
    "n_estimators": [100, 300, 500],
    "max_depth": [10, 20, None],
    "min_samples_leaf": [1, 3],
}
rf_gs = GridSearchCV(
    RandomForestRegressor(random_state=RANDOM_STATE, n_jobs=-1),
    rf_grid, cv=cv, scoring="neg_mean_squared_error", n_jobs=-1
)
rf_gs.fit(X_train, y_train)
rf_model = rf_gs.best_estimator_
print(f"  RF best params: {rf_gs.best_params_}, CV RMSE: {(-rf_gs.best_score_)**0.5:.4f}")

xgb_grid = {
    "n_estimators": [100, 300],
    "max_depth": [3, 6, 9],
    "learning_rate": [0.01, 0.1],
}
xgb_gs = GridSearchCV(
    XGBRegressor(random_state=RANDOM_STATE, n_jobs=-1, verbosity=0),
    xgb_grid, cv=cv, scoring="neg_mean_squared_error", n_jobs=-1
)
xgb_gs.fit(X_train, y_train)
xgb_model = xgb_gs.best_estimator_
print(f"  XGB best params: {xgb_gs.best_params_}, CV RMSE: {(-xgb_gs.best_score_)**0.5:.4f}")

pickle.dump({"model": rf_model, "best_params": rf_gs.best_params_}, open(DATA_OUT / "rf_reg.pkl", "wb"))
pickle.dump({"model": xgb_model, "best_params": xgb_gs.best_params_}, open(DATA_OUT / "xgb_reg.pkl", "wb"))

cv_df = pd.DataFrame(rf_gs.cv_results_)[["params", "mean_test_score", "rank_test_score"]]
cv_df["model"] = "RF"
cv_xgb = pd.DataFrame(xgb_gs.cv_results_)[["params", "mean_test_score", "rank_test_score"]]
cv_xgb["model"] = "XGB"
pd.concat([cv_df, cv_xgb]).to_csv(RESULTS / "cv_results.csv", index=False)
# ─── Step 4: Evaluation ────────────────────────────────────────────────────────

print("Step 4: Evaluating...")


def eval_metrics(y_true, y_pred):
    r2 = r2_score(y_true, y_pred)
    mae = mean_absolute_error(y_true, y_pred)
    rmse = mean_squared_error(y_true, y_pred) ** 0.5
    r, _ = pearsonr(y_true, y_pred)
    return {"R2": r2, "MAE": mae, "RMSE": rmse, "Pearson_r": r}


pred_rf_val = rf_model.predict(X_val)
pred_xgb_val = xgb_model.predict(X_val)
pred_ens_val = (pred_rf_val + pred_xgb_val) / 2

pred_rf_test = rf_model.predict(X_test)
pred_xgb_test = xgb_model.predict(X_test)
pred_ens_test = (pred_rf_test + pred_xgb_test) / 2

val_results = {
    "RF": eval_metrics(y_val, pred_rf_val),
    "XGB": eval_metrics(y_val, pred_xgb_val),
    "Ensemble": eval_metrics(y_val, pred_ens_val),
}
test_results = {
    "RF": eval_metrics(y_test, pred_rf_test),
    "XGB": eval_metrics(y_test, pred_xgb_test),
    "Ensemble": eval_metrics(y_test, pred_ens_test),
}

val_df = pd.DataFrame(val_results).T
test_df = pd.DataFrame(test_results).T
val_df.to_csv(RESULTS / "val_metrics.csv")
test_df.to_csv(RESULTS / "test_metrics.csv")

print("\n  Validation Metrics:")
print(val_df.to_string())
print("\n  Test Metrics:")
print(test_df.to_string())
# ─── Step 5: SHAP ─────────────────────────────────────────────────────────────

print("Step 5: SHAP analysis...")

explainer = shap.TreeExplainer(rf_model)
shap_values = explainer.shap_values(X_val)
mean_abs_shap = np.abs(shap_values).mean(axis=0)
top20_idx = np.argsort(-mean_abs_shap)[:20]
top20_names = [feature_names[i] for i in top20_idx]
top20_importance = mean_abs_shap[top20_idx]

shap_df = pd.DataFrame({"feature": top20_names, "mean_abs_shap": top20_importance})
shap_df.to_csv(RESULTS / "shap_top20.csv", index=False)
print(f"  Top 5 features: {top20_names[:5]}")

plt.figure(figsize=(10, 6))
shap.summary_plot(shap_values, X_val, feature_names=feature_names, max_display=20, show=False)
plt.tight_layout()
plt.savefig(RESULTS / "shap_summary.png", dpi=200, bbox_inches="tight")
plt.close()

# ─── Step 6: Plots ─────────────────────────────────────────────────────────────

print("Step 6: Generating plots...")

plt.rcParams.update({"font.family": "Times New Roman", "axes.linewidth": 1.2})

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

for ax, (y_true, y_pred, title) in zip(axes, [
    (y_val, pred_ens_val, "Validation"),
    (y_test, pred_ens_test, "Test"),
]):
    ax.scatter(y_true, y_pred, alpha=0.5, s=20, c="#2A9D6A")
    lo = min(y_true.min(), y_pred.min()) - 0.3
    hi = max(y_true.max(), y_pred.max()) + 0.3
    ax.plot([lo, hi], [lo, hi], "k--", lw=1)
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal")
    ax.set_xlabel("Actual logSw")
    ax.set_ylabel("Predicted logSw")
    r2 = r2_score(y_true, y_pred)
    ax.set_title(f"{title} (R²={r2:.3f})")
    for side in ("top", "right", "bottom", "left"):
        ax.spines[side].set_visible(True)
    ax.tick_params(direction="in", top=True, right=True)

fig.tight_layout()
fig.savefig(RESULTS / "fig_pred_vs_actual.png", dpi=300, bbox_inches="tight")
plt.close()

fig, ax = plt.subplots(figsize=(6, 4))
residuals = y_test - pred_ens_test
ax.hist(residuals, bins=30, color="#4682B4", edgecolor="white", alpha=0.8)
ax.axvline(0, color="red", linestyle="--", lw=1)
ax.set_xlabel("Residual (Actual - Predicted)")
ax.set_ylabel("Count")
ax.set_title("Test Set Residual Distribution")
fig.tight_layout()
fig.savefig(RESULTS / "fig_residuals.png", dpi=300, bbox_inches="tight")
plt.close()

print(f"\nDone! Results saved to {RESULTS}")
print(f"Models saved to {DATA_OUT}")

