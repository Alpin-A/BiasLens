from __future__ import annotations

from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

try:
    import joblib
except Exception as exc:  # pragma: no cover
    raise RuntimeError("joblib is required to save the model") from exc

MODEL_DIR = Path(__file__).resolve().parent / "saved_models"
MODEL_PATH = MODEL_DIR / "bias_logreg.joblib"


def train_stub_model() -> None:
    """Train a lightweight placeholder classifier for local experimentation."""
    rng = np.random.default_rng(seed=42)

    # Features: [avg_trades_per_day, max_burst_trades, hold_ratio, revenge_event_rate]
    x = rng.normal(loc=0.5, scale=0.2, size=(500, 4)).clip(0, 1)
    y = np.where(x[:, 0] + x[:, 1] > 1.0, "overtrading", "loss_aversion")
    y = np.where(x[:, 3] > 0.7, "revenge_trading", y)

    model = LogisticRegression(max_iter=500, multi_class="multinomial")
    model.fit(x, y)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"Saved stub model to {MODEL_PATH}")


if __name__ == "__main__":
    train_stub_model()
