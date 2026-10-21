import pickle

import pytest

from scripts.api.predict import SweetnessPredictor


def test_optional_empty_model_is_skipped(tmp_path):
    model_path = tmp_path / "xgb.pkl"
    model_path.touch()

    assert SweetnessPredictor._load_model(model_path) is None


def test_required_empty_model_has_clear_error(tmp_path):
    model_path = tmp_path / "rf.pkl"
    model_path.touch()

    with pytest.raises(RuntimeError, match="Required prediction model could not be loaded"):
        SweetnessPredictor._load_model(model_path, required=True)


def test_valid_model_payload_is_loaded(tmp_path):
    model_path = tmp_path / "model.pkl"
    expected = {"name": "test-model"}
    with model_path.open("wb") as f:
        pickle.dump({"model": expected}, f)

    assert SweetnessPredictor._load_model(model_path) == expected


def test_committed_prediction_artifacts_run_with_locked_runtime():
    result = SweetnessPredictor().predict("CC(O)C(=O)O")

    assert result["status"] == "ok"
    assert {"random_forest", "xgboost"}.issubset(result["models_used"])
    assert len(result["shap_top5"]) == 5
    assert result["regression"] is not None
