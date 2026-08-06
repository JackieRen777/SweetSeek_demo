"""Generate 3 publication-quality figures for sweetness prediction ML paper."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pickle
from sklearn.metrics import roc_curve, auc

# ── paths ─────────────────────────────────────────────────────────────────────
ROOT = "/Users/jackieren/Desktop/FCN_SweetSeek"
X = np.load(f"{ROOT}/data/features/X.npy")
y = np.load(f"{ROOT}/data/features/y.npy")
splits = json.load(open(f"{ROOT}/data/features/splits.json"))
val_idx = splits["val"]
X_val = X[val_idx]; y_val = y[val_idx]

# ── shared style ──────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "Times New Roman",
    "axes.labelsize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

def savefig(fig, path):
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {path}")

# ─────────────────────────────────────────────────────────────────────────────
# Figure 1: Chemical Space (UMAP / PCA fallback)
# ─────────────────────────────────────────────────────────────────────────────
try:
    from umap import UMAP
    reducer = UMAP(n_components=2, random_state=42)
    embedding = reducer.fit_transform(X)
    ax1_label, ax2_label = "UMAP-1", "UMAP-2"
    print("Using UMAP")
except ImportError:
    from sklearn.decomposition import PCA
    embedding = PCA(n_components=2, random_state=42).fit_transform(X)
    ax1_label, ax2_label = "PC1", "PC2"
    print("UMAP not available, using PCA")

fig, ax = plt.subplots(figsize=(6, 5))
for label, color, name in [(0, "#AAAAAA", "NonSweet"), (1, "#2E8B57", "Sweet")]:
    mask = y == label
    ax.scatter(embedding[mask, 0], embedding[mask, 1],
               c=color, alpha=0.5, s=8, linewidths=0,
               label=f"{name} (n={mask.sum()})")
ax.set_xlabel(ax1_label); ax.set_ylabel(ax2_label)
ax.set_title("Chemical Space of Sweetness Dataset")
ax.legend(markerscale=2, frameon=False)
ax.grid(True, alpha=0.3)
savefig(fig, f"{ROOT}/results/fig1_umap.png")

# ─────────────────────────────────────────────────────────────────────────────
# Figure 2: ROC Curves
# ─────────────────────────────────────────────────────────────────────────────
roc_df = pd.read_csv(f"{ROOT}/results/val_roc.csv")

with open(f"{ROOT}/data/models/rf.pkl", "rb") as f:
    rf_obj = pickle.load(f)
    rf = rf_obj["model"] if isinstance(rf_obj, dict) else rf_obj
with open(f"{ROOT}/data/models/xgb.pkl", "rb") as f:
    xgb_obj = pickle.load(f)
    xgb = xgb_obj["model"] if isinstance(xgb_obj, dict) else xgb_obj

rf_prob  = rf.predict_proba(X_val)[:, 1]
xgb_prob = xgb.predict_proba(X_val)[:, 1]
ens_prob = (rf_prob + xgb_prob) / 2
ens_fpr, ens_tpr, _ = roc_curve(y_val, ens_prob)
ens_auc = auc(ens_fpr, ens_tpr)

fig, ax = plt.subplots(figsize=(5, 5))
ax.plot([0, 1], [0, 1], color="gray", lw=1, linestyle="--")

colors = {"RF": "#2E8B57", "XGB": "#4682B4"}
for model, color in colors.items():
    sub = roc_df[roc_df["model"] == model]
    fpr, tpr = sub["fpr"].values, sub["tpr"].values
    roc_auc = auc(fpr, tpr)
    ax.plot(fpr, tpr, color=color, lw=2, label=f"{model} (AUC={roc_auc:.3f})")

ax.plot(ens_fpr, ens_tpr, color="#DC143C", lw=2,
        label=f"Ensemble (AUC={ens_auc:.3f})")

ax.set_xlabel("False Positive Rate"); ax.set_ylabel("True Positive Rate")
ax.set_title("ROC Curves — Validation Set")
ax.legend(frameon=False, loc="lower right")
ax.grid(True, alpha=0.3)
savefig(fig, f"{ROOT}/results/fig2_roc.png")

# ─────────────────────────────────────────────────────────────────────────────
# Figure 3: SHAP Feature Importance — Block + Top-5
# ─────────────────────────────────────────────────────────────────────────────
shap_vals = np.load(f"{ROOT}/results/shap_values_val.npy")
shap_top20 = pd.read_csv(f"{ROOT}/results/shap_top20.csv")

mean_abs = np.abs(shap_vals).mean(axis=0)
blocks = {
    "ECFP4\n(0–1023)":      mean_abs[0:1024].mean(),
    "MACCS\n(1024–1190)":   mean_abs[1024:1191].mean(),
    "RDKit2D\n(1191–1406)": mean_abs[1191:1407].mean(),
}

top5 = shap_top20.head(5).iloc[::-1]  # reverse for horizontal bar

fig, axes = plt.subplots(1, 2, figsize=(11, 4))

# Left: block bar chart
ax = axes[0]
ax.bar(list(blocks.keys()), list(blocks.values()), color="#2E8B57", alpha=0.85)
ax.set_ylabel("Mean |SHAP|")
ax.set_title("Mean |SHAP| by Feature Block")
ax.grid(axis="y", alpha=0.3)

# Right: top-5 horizontal bar
ax = axes[1]
ax.barh(top5["feature_name"], top5["mean_abs_shap"], color="#2E8B57", alpha=0.85)
ax.set_xlabel("Mean |SHAP|")
ax.set_title("Top-5 Features")
ax.grid(axis="x", alpha=0.3)

fig.suptitle("SHAP Feature Importance", fontsize=13, y=1.01)
savefig(fig, f"{ROOT}/results/fig3_shap_blocks.png")
