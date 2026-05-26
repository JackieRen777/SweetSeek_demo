"""Test sweetness prediction integration with RAG.

Simulates a user asking about a molecule's sweetness via the RAG system.
"""

import sys
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from services.sweetness_prediction_service import get_sweetness_prediction_service


def test_smiles_detection():
    """Test SMILES detection in various question formats."""
    service = get_sweetness_prediction_service()

    test_cases = [
        ("CCO 这个分子甜不甜?", ["CCO"]),
        ("请问 C1=CC=C(C=C1)O 的甜味如何?", ["C1=CC=C(C=C1)O"]),
        ("阿司匹林 CC(=O)Oc1ccccc1C(=O)O 有甜味吗?", ["CC(=O)Oc1ccccc1C(=O)O"]),
        ("TPSA 和 ECFP4 是什么?", []),  # Should filter out false positives
        ("甜味的分子机制是什么?", []),  # No SMILES
    ]

    print("=" * 60)
    print("SMILES Detection Test")
    print("=" * 60)

    for question, expected in test_cases:
        detected = service.detect_smiles(question)
        status = "✓" if detected == expected else "✗"
        print(f"\n{status} Question: {question}")
        print(f"  Expected: {expected}")
        print(f"  Detected: {detected}")


def test_answer_augmentation():
    """Test answer augmentation with ML prediction."""
    service = get_sweetness_prediction_service()

    question = "CCO 这个分子甜不甜?"
    original_answer = "乙醇(CCO)是一种常见的醇类化合物,通常不具有甜味。"

    print("\n" + "=" * 60)
    print("Answer Augmentation Test")
    print("=" * 60)
    print(f"\nQuestion: {question}")
    print(f"\nOriginal Answer:\n{original_answer}")

    augmented_answer, prediction = service.augment_answer(question, original_answer)

    print(f"\nAugmented Answer:\n{augmented_answer}")
    print(f"\nPrediction Result:")
    if prediction:
        print(f"  Status: {prediction['status']}")
        if prediction['status'] == 'ok':
            print(f"  SMILES: {prediction['smiles_canonical']}")
            print(f"  Prediction: {'Sweet' if prediction['is_sweet_pred'] == 1 else 'NonSweet'}")
            print(f"  Probability: {prediction['sweet_prob']:.4f}")


if __name__ == "__main__":
    test_smiles_detection()
    test_answer_augmentation()
    print("\n" + "=" * 60)
    print("All tests completed")
    print("=" * 60)
