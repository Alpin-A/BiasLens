from __future__ import annotations

from pathlib import Path

import numpy as np

try:
    import joblib
except Exception:  # pragma: no cover
    joblib = None

MODEL_DIR = Path(__file__).resolve().parent / "saved_models"
MODEL_PATH = MODEL_DIR / "bias_xgb.joblib"

# Fallback to legacy path if old model exists
LEGACY_MODEL_PATH = MODEL_DIR / "bias_logreg.joblib"

BIAS_CLASSES = ["calm", "loss_aversion", "overtrading", "revenge_trading"]


class BiasMLClassifier:
    """XGBoost-based bias classifier. Falls back to heuristic probabilities when no model exists."""

    def __init__(self) -> None:
        self.model = None
        self.classes: list[str] = BIAS_CLASSES

        if joblib:
            for path in [MODEL_PATH, LEGACY_MODEL_PATH]:
                if path.exists():
                    self.model = joblib.load(path)
                    if hasattr(self.model, "bias_classes_"):
                        self.classes = self.model.bias_classes_
                    break

    @property
    def is_loaded(self) -> bool:
        return self.model is not None

    def predict_bias_probabilities(self, feature_vector: np.ndarray) -> dict[str, float]:
        """
        Given a feature vector, return per-class probabilities.

        When a trained XGBoost model is available, uses predict_proba.
        Otherwise returns heuristic fallback probabilities.
        """
        if self.model is not None:
            x = feature_vector.reshape(1, -1)
            probabilities = self.model.predict_proba(x)[0]
            return {label: float(prob) for label, prob in zip(self.classes, probabilities)}

        # Heuristic fallback keeps endpoint deterministic without a trained model artifact.
        normalized = np.clip(feature_vector.astype(float), 0, 100) / 100
        overtrading = float(min(1.0, 0.4 + normalized[0] * 0.5 + normalized[1] * 0.2))
        loss_aversion = float(min(1.0, 0.2 + normalized[2] * 0.7))
        revenge = float(min(1.0, 0.2 + normalized[3] * 0.8))

        return {
            "calm": float(max(0, 1.0 - overtrading - loss_aversion - revenge)),
            "overtrading": overtrading,
            "loss_aversion": loss_aversion,
            "revenge_trading": revenge,
        }
