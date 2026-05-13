"""
SHAP explainability for the XGBoost bias classifier.

Computes per-window SHAP values using TreeExplainer, showing
how each feature contributed to the predicted bias probabilities.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

try:
    import shap
except Exception:  # pragma: no cover
    shap = None  # type: ignore[assignment]

from backend.ml.features import FEATURE_NAMES, extract_features, extract_windowed_features
from backend.ml.model import BiasMLClassifier


class ShapExplainer:
    """Wraps shap.TreeExplainer around the loaded XGBoost bias model."""

    def __init__(self) -> None:
        self.classifier = BiasMLClassifier()
        self.explainer = None
        self.classes: list[str] = list(self.classifier.classes)

        if shap is not None and self.classifier.is_loaded:
            self.explainer = shap.TreeExplainer(self.classifier.model)

    @property
    def is_available(self) -> bool:
        return self.explainer is not None

    def explain_windows(
        self,
        df: pd.DataFrame,
        window_size: int = 50,
        stride: int = 25,
    ) -> dict[str, Any]:
        """Compute SHAP values for all trade windows.

        Returns a dict matching the ShapExplainResponse schema.
        """
        if not self.is_available:
            raise RuntimeError("SHAP explainer not available (no model or shap library).")

        # Extract windowed features (same logic as analysis_engine)
        if len(df) >= window_size:
            feature_vectors = extract_windowed_features(df, window_size=window_size, stride=stride)
        else:
            feature_vectors = [extract_features(df)]

        X = np.array(feature_vectors)

        # Compute SHAP values — for multi-class XGBoost this returns
        # a list of arrays, one per class, each (n_windows, n_features)
        shap_values = self.explainer.shap_values(X)
        base_values = self.explainer.expected_value

        # Get predictions for context
        predictions: list[dict[str, float]] = []
        for feat in feature_vectors:
            predictions.append(self.classifier.predict_bias_probabilities(feat))

        # Build per-window response
        windows: list[dict[str, Any]] = []
        for w in range(len(feature_vectors)):
            sv: dict[str, list[float]] = {}
            for i, cls in enumerate(self.classes):
                raw = shap_values[i][w] if isinstance(shap_values, list) else shap_values[w, :, i]
                # Sanitize NaN/Inf
                clean = np.where(np.isfinite(raw), raw, 0.0)
                sv[cls] = clean.tolist()

            start_idx = w * stride if len(df) >= window_size else 0
            end_idx = start_idx + window_size if len(df) >= window_size else len(df)

            windows.append({
                "window_index": w,
                "trade_range": [start_idx, min(end_idx, len(df))],
                "feature_values": X[w].tolist(),
                "predictions": predictions[w],
                "shap_values": sv,
            })

        # Base values per class
        bv: dict[str, float] = {}
        if isinstance(base_values, (list, np.ndarray)):
            for i, cls in enumerate(self.classes):
                bv[cls] = float(base_values[i])
        else:
            for cls in self.classes:
                bv[cls] = float(base_values)

        return {
            "feature_names": list(FEATURE_NAMES),
            "classes": list(self.classes),
            "n_windows": len(feature_vectors),
            "base_values": bv,
            "windows": windows,
        }


# Module-level singleton to avoid re-creating the explainer on every request
_cached_explainer: ShapExplainer | None = None


def get_explainer() -> ShapExplainer:
    global _cached_explainer
    if _cached_explainer is None:
        _cached_explainer = ShapExplainer()
    return _cached_explainer
