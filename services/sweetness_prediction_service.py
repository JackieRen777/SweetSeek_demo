"""Sweetness prediction service for RAG integration.

Detects SMILES in user queries and augments RAG answers with ML predictions.
"""

from __future__ import annotations

import re
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from scripts.api.predict import SweetnessPredictor


class SweetnessPredictionService:
    """Wrapper for sweetness prediction API, integrated into RAG workflow."""

    # SMILES pattern: simplified heuristic (alphanumeric + common SMILES chars)
    # Matches strings like "CCO", "C1=CC=C(C=C1)O", "CC(=O)Oc1ccccc1C(=O)O"
    SMILES_PATTERN = re.compile(
        r'\b[A-Z][A-Za-z0-9@+\-\[\]\(\)=#$:/\\\.]{2,}\b'
    )

    def __init__(self):
        """Lazy-load predictor on first use."""
        self._predictor = None

    @property
    def predictor(self) -> SweetnessPredictor:
        if self._predictor is None:
            # RDKit and the prediction models are optional until a SMILES query arrives.
            from scripts.api.predict import SweetnessPredictor
            self._predictor = SweetnessPredictor()
        return self._predictor

    def detect_smiles(self, text: str) -> list[str]:
        """Extract potential SMILES strings from text.

        Returns:
            List of candidate SMILES (may include false positives like "TPSA").
        """
        candidates = self.SMILES_PATTERN.findall(text)
        # Filter out common false positives (descriptor names, acronyms)
        false_positives = {
            "TPSA", "BCUT2D", "VSA", "PEOE", "ECFP", "MACCS", "RDKit",
            "SHAP", "AUC", "ROC", "API", "RAG", "LLM", "PDF", "CSV"
        }
        return [s for s in candidates if s not in false_positives and len(s) >= 3]

    def augment_answer(self, question: str, answer: str) -> tuple[str, dict[str, Any] | None]:
        """Detect SMILES in question, predict sweetness, augment answer.

        Returns:
            (augmented_answer, prediction_result or None)
        """
        smiles_list = self.detect_smiles(question)
        if not smiles_list:
            return answer, None

        # Predict for the first detected SMILES (multi-SMILES support can be added later)
        smiles = smiles_list[0]
        try:
            result = self.predictor.predict(smiles)
        except Exception as e:
            # Prediction failed, return original answer
            return answer, {"status": "error", "error": str(e)}

        if result["status"] != "ok":
            return answer, result

        # Build augmentation text
        label = "甜味" if result["is_sweet_pred"] == 1 else "非甜味"
        prob = result["sweet_prob"]
        confidence = "高" if abs(prob - 0.5) > 0.3 else "中" if abs(prob - 0.5) > 0.15 else "低"

        augment_text = f"""

---

**🔬 分子甜味预测 (ML模型)**

检测到 SMILES: `{result['smiles_canonical']}`

- **预测结果**: {label} (置信度: {confidence})
- **甜味概率**: {prob:.2%}
- **关键特征 (SHAP Top-3)**:
"""
        for i, item in enumerate(result["shap_top5"][:3], 1):
            direction = "促进甜味" if item["shap"] > 0 else "抑制甜味"
            augment_text += f"\n  {i}. `{item['feature']}` ({direction}, SHAP={item['shap']:+.4f})"

        augment_text += "\n\n*注: 此预测基于 3846 个分子的训练集 (F1=0.82, AUC=0.97),仅供参考。*"

        augmented_answer = answer + augment_text
        return augmented_answer, result


# Singleton instance
_service = None


def get_sweetness_prediction_service() -> SweetnessPredictionService:
    """Get or create singleton service instance."""
    global _service
    if _service is None:
        _service = SweetnessPredictionService()
    return _service
