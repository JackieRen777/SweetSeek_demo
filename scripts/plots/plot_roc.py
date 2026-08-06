"""重新生成 ROC 曲线（验证集），完整边框 + 等比例正方形。"""
import json, pickle
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc

ROOT = Path("/Users/jackieren/Desktop/FCN_SweetSeek")

X      = np.load(ROOT / "data/features/X.npy")
y      = np.load(ROOT / "data/features/y.npy")
splits = json.load(open(ROOT / "data/features/splits.json"))
val_idx = splits["val"]
X_val, y_val = X[val_idx], y[val_idx]

with open(ROOT / "data/models/rf.pkl", "rb") as f:
    rf_obj = pickle.load(f)
    rf = rf_obj["model"] if isinstance(rf_obj, dict) else rf_obj
with open(ROOT / "data/models/xgb.pkl", "rb") as f:
    xgb_obj = pickle.load(f)
    xgb = xgb_obj["model"] if isinstance(xgb_obj, dict) else xgb_obj

rf_prob  = rf.predict_proba(X_val)[:, 1]
xgb_prob = xgb.predict_proba(X_val)[:, 1]
ens_prob = (rf_prob + xgb_prob) / 2

rf_fpr,  rf_tpr,  _ = roc_curve(y_val, rf_prob)
xgb_fpr, xgb_tpr, _ = roc_curve(y_val, xgb_prob)
ens_fpr, ens_tpr, _ = roc_curve(y_val, ens_prob)

rf_auc  = auc(rf_fpr,  rf_tpr)
xgb_auc = auc(xgb_fpr, xgb_tpr)
ens_auc = auc(ens_fpr, ens_tpr)

print(f"RF       AUC = {rf_auc:.4f}")
print(f"XGB      AUC = {xgb_auc:.4f}")
print(f"Ensemble AUC = {ens_auc:.4f}")

plt.rcParams.update({
    "font.family": "Times New Roman",
    "axes.labelsize": 13,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "axes.linewidth": 1.2,
})

fig, ax = plt.subplots(figsize=(6, 6))

ax.plot([0, 1], [0, 1], color="gray", lw=1, linestyle="--", label="Random (AUC=0.500)")
ax.plot(rf_fpr,  rf_tpr,  color="#2E8B57", lw=2.2, label=f"RF        (AUC={rf_auc:.3f})")
ax.plot(xgb_fpr, xgb_tpr, color="#4682B4", lw=2.2, label=f"XGBoost   (AUC={xgb_auc:.3f})")
ax.plot(ens_fpr, ens_tpr, color="#DC143C", lw=2.4, label=f"Ensemble  (AUC={ens_auc:.3f})")

ax.set_xlim(0.0, 1.0)
ax.set_ylim(0.0, 1.005)
ax.set_aspect("equal", adjustable="box")
ax.set_xticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
ax.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])

# 完整四边框
for side in ("top", "right", "bottom", "left"):
    ax.spines[side].set_visible(True)
    ax.spines[side].set_linewidth(1.2)
    ax.spines[side].set_color("#222222")

ax.tick_params(direction="in", length=5, width=1.0, top=True, right=True)
ax.grid(True, alpha=0.3, linestyle=":")

ax.set_xlabel("False Positive Rate")
ax.set_ylabel("True Positive Rate")
ax.set_title("ROC Curves — Validation Set", fontsize=14, pad=10)
ax.legend(loc="lower right", frameon=True, fontsize=11,
          edgecolor="#222222", framealpha=0.95)

fig.tight_layout()
out = ROOT / "results/fig2_roc.png"
fig.savefig(out, dpi=300, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {out}")
