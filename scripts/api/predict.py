"""Day 6: Sweetness prediction API.

Inference pipeline:
  1. Input: SMILES string(s)
  2. Standardize via Day 1 pipeline (RDKit desalt + neutralize + tautomer)
  3. Featurize: ECFP4(1024) + MACCS(167) + RDKit2D(216) = 1407 dim
  4. Preprocess: apply Day 3 fitted scaler (data/features/preprocessor.pkl)
  5. Predict: ensemble (RF + XGB) with Day 5 tuned threshold (0.36)
  6. SHAP: compute feature contributions for the prediction
  7. Output: {smiles, is_sweet_pred, sweet_prob, shap_top5, status}

Usage:
    from scripts.api.predict import SweetnessPredictor
    predictor = SweetnessPredictor()
    result = predictor.predict("CCO")  # ethanol
    print(result)
    # {'smiles': 'CCO', 'smiles_canonical': 'CCO', 'is_sweet_pred': 0,
    #  'sweet_prob': 0.23, 'shap_top5': [...], 'status': 'ok'}

CLI:
    venv/bin/python -m scripts.api.predict "CCO" "C1=CC=C(C=C1)O"
"""

from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path
from typing import Any

import numpy as np
from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors

# Reuse Day 1 standardization + Day 3 featurization
from scripts.data.standardize import standardize
from scripts.features.featurize import ecfp4, maccs, rdkit_2d

RDLogger.DisableLog("rdApp.*")

REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = REPO_ROOT / "data" / "models"
FEAT_DIR = REPO_ROOT / "data" / "features"
REG_DIR = REPO_ROOT / "data" / "regression"

# Day 5 tuned threshold
THRESHOLD = 0.36


class SweetnessPredictor:
    """Ensemble sweetness predictor with SHAP explanations."""

    def __init__(self):
        """Load models, preprocessor, and feature names. SHAP explainer is loaded lazily."""
        with open(MODEL_DIR / "rf.pkl", "rb") as f:
            self.rf_model = pickle.load(f)["model"]
        with open(MODEL_DIR / "xgb.pkl", "rb") as f:
            self.xgb_model = pickle.load(f)["model"]
        with open(FEAT_DIR / "preprocessor.pkl", "rb") as f:
            self.preprocessor = pickle.load(f)
        self.feature_names = json.loads((FEAT_DIR / "feature_names.json").read_text(encoding="utf-8"))
        self.feature_meta = json.loads((FEAT_DIR / "feature_meta.json").read_text(encoding="utf-8"))

        # Regression models (BrixDB-trained)
        self._rf_reg = None
        self._xgb_reg = None
        self._reg_preprocessor = None

        # Defer SHAP TreeExplainer init to first predict() call.
        # Reason: importing shap and constructing TreeExplainer at Flask startup
        # has caused SIGSEGV crashes on macOS ARM64 (multithreading conflict).
        self._shap_explainer = None

    def _load_regression_models(self):
        """Lazy-load regression models."""
        if self._rf_reg is not None:
            return True
        try:
            with open(REG_DIR / "rf_reg.pkl", "rb") as f:
                self._rf_reg = pickle.load(f)["model"]
            with open(REG_DIR / "xgb_reg.pkl", "rb") as f:
                self._xgb_reg = pickle.load(f)["model"]
            with open(REG_DIR / "preprocessor.pkl", "rb") as f:
                self._reg_preprocessor = pickle.load(f)
            return True
        except FileNotFoundError:
            return False

    @property
    def shap_explainer(self):
        if self._shap_explainer is None:
            import shap
            self._shap_explainer = shap.TreeExplainer(
                self.rf_model, feature_perturbation="tree_path_dependent"
            )
        return self._shap_explainer

    def _featurize_one(self, smiles_canonical: str) -> np.ndarray | None:
        """Compute 1407-dim feature vector for a single molecule."""
        mol = Chem.MolFromSmiles(smiles_canonical)
        if mol is None:
            return None
        try:
            v_ecfp = ecfp4(mol)
            v_maccs = maccs(mol)
            v_desc = rdkit_2d(mol)
            return np.concatenate([v_ecfp.astype(np.float32),
                                   v_maccs.astype(np.float32),
                                   v_desc.astype(np.float32)])
        except Exception:
            return None

    def predict(self, smiles: str) -> dict[str, Any]:
        """Predict sweetness for a single SMILES.

        Returns:
            {
                'smiles': original input,
                'smiles_canonical': standardized SMILES,
                'is_sweet_pred': 0 or 1,
                'sweet_prob': float [0, 1],
                'shap_top5': [{'feature': name, 'shap': value}, ...],
                'status': 'ok' | 'standardization_failed' | 'featurization_failed'
            }
        """
        # Step 1: standardize
        std_result = standardize(smiles)
        if not std_result["valid"]:
            return {
                "smiles": smiles,
                "smiles_canonical": None,
                "is_sweet_pred": None,
                "sweet_prob": None,
                "shap_top5": None,
                "status": f"standardization_failed:{std_result['reason']}",
            }

        smiles_canonical = std_result["smiles_canonical"]

        # Step 2: featurize
        X_raw = self._featurize_one(smiles_canonical)
        if X_raw is None:
            return {
                "smiles": smiles,
                "smiles_canonical": smiles_canonical,
                "is_sweet_pred": None,
                "sweet_prob": None,
                "shap_top5": None,
                "status": "featurization_failed",
            }

        # Step 3: preprocess (apply Day 3 fitted scaler)
        X = self.preprocessor.transform(X_raw.reshape(1, -1)).astype(np.float32)

        # Step 4: ensemble prediction
        proba_rf = self.rf_model.predict_proba(X)[0, 1]
        proba_xgb = self.xgb_model.predict_proba(X)[0, 1]
        proba_ens = (proba_rf + proba_xgb) / 2.0
        is_sweet = int(proba_ens >= THRESHOLD)

        # Step 5: SHAP explanation (RF only) — best effort
        shap_top5 = []
        try:
            shap_vals = self.shap_explainer.shap_values(X)
            if isinstance(shap_vals, list):
                shap_vals = shap_vals[1]  # class 1 (Sweet)
            elif shap_vals.ndim == 3:
                shap_vals = shap_vals[:, :, 1]
            shap_vals = shap_vals.flatten()  # (1, 1407) -> (1407,)

            top_idx = np.argsort(-np.abs(shap_vals))[:5]
            shap_top5 = [
                {"feature": self.feature_names[int(i)], "shap": float(shap_vals[int(i)])}
                for i in top_idx
            ]
        except Exception as e:
            print(f"[SweetnessPredictor] SHAP failed: {e}", file=sys.stderr)

        # Step 6: physicochemical properties for visualization
        properties = {}
        try:
            mol = Chem.MolFromSmiles(smiles_canonical)
            if mol is not None:
                properties = {
                    "mw": round(float(Descriptors.MolWt(mol)), 2),
                    "logp": round(float(Descriptors.MolLogP(mol)), 2),
                    "tpsa": round(float(Descriptors.TPSA(mol)), 2),
                    "hba": int(Descriptors.NumHAcceptors(mol)),
                    "hbd": int(Descriptors.NumHDonors(mol)),
                    "rot_bonds": int(Descriptors.NumRotatableBonds(mol)),
                    "aromatic_rings": int(Descriptors.NumAromaticRings(mol)),
                    "heavy_atoms": int(Descriptors.HeavyAtomCount(mol)),
                }
        except Exception as e:
            print(f"[SweetnessPredictor] descriptor calc failed: {e}", file=sys.stderr)

        # Step 7: regression prediction (sweetness intensity)
        regression = None
        if self._load_regression_models():
            try:
                X_reg = self._reg_preprocessor.transform(X_raw.reshape(1, -1)).astype(np.float32)
                pred_rf_reg = self._rf_reg.predict(X_reg)[0]
                pred_xgb_reg = self._xgb_reg.predict(X_reg)[0]
                log_sw = float((pred_rf_reg + pred_xgb_reg) / 2.0)
                relative_sweetness = round(10 ** log_sw, 1)
                regression = {
                    "log_sw": round(log_sw, 3),
                    "relative_sweetness": relative_sweetness,
                    "model_r2": 0.679,
                }
            except Exception as e:
                print(f"[SweetnessPredictor] regression failed: {e}", file=sys.stderr)

        return {
            "smiles": smiles,
            "smiles_canonical": smiles_canonical,
            "is_sweet_pred": is_sweet,
            "sweet_prob": float(proba_ens),
            "shap_top5": shap_top5,
            "properties": properties,
            "regression": regression,
            "status": "ok",
        }

    def predict_batch(self, smiles_list: list[str]) -> list[dict[str, Any]]:
        """Predict sweetness for a batch of SMILES."""
        return [self.predict(smi) for smi in smiles_list]


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.api.predict <SMILES1> [SMILES2] ...")
        print("\nExample:")
        print("  python -m scripts.api.predict 'CCO' 'C1=CC=C(C=C1)O'")
        sys.exit(1)

    predictor = SweetnessPredictor()
    smiles_list = sys.argv[1:]

    print("=" * 60)
    print(f"Sweetness Prediction API (threshold={THRESHOLD})")
    print("=" * 60)

    for i, smi in enumerate(smiles_list, 1):
        result = predictor.predict(smi)
        print(f"\n[{i}/{len(smiles_list)}] {smi}")
        print(f"  Canonical: {result['smiles_canonical']}")
        print(f"  Status: {result['status']}")
        if result["status"] == "ok":
            label = "Sweet" if result["is_sweet_pred"] == 1 else "NonSweet"
            print(f"  Prediction: {label} (prob={result['sweet_prob']:.4f})")
            print("  SHAP Top-5:")
            for j, item in enumerate(result["shap_top5"], 1):
                print(f"    {j}. {item['feature']:30s} SHAP={item['shap']:+.4f}")


if __name__ == "__main__":
    main()
