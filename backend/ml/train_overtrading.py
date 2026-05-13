"""
Overtrading classifier – training stub.

Approach: binary classifier on daily-aggregated features.
Labels generated via weak supervision heuristics (trades_per_day > threshold).
"""
from __future__ import annotations

import os
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

MODEL_DIR = Path(__file__).parent / "saved_models"
MODEL_DIR.mkdir(exist_ok=True)
MODEL_PATH = MODEL_DIR / "overtrading_clf.pkl"


def generate_synthetic_data(n_days: int = 500) -> pd.DataFrame:
    """Create synthetic daily metrics for training."""
    rng = np.random.default_rng(42)
    data = pd.DataFrame(
        {
            "trades_per_day": rng.poisson(lam=12, size=n_days),
            "avg_trade_size": rng.lognormal(mean=3, sigma=0.5, size=n_days),
            "pnl_sum": rng.normal(loc=0, scale=500, size=n_days),
            "max_burst_5min": rng.poisson(lam=3, size=n_days),
            "unique_symbols": rng.integers(1, 10, size=n_days),
        }
    )
    # Weak label: overtrade if trades > mean + 1 std
    threshold = data["trades_per_day"].mean() + data["trades_per_day"].std()
    data["label"] = (data["trades_per_day"] > threshold).astype(int)
    return data


def train(save: bool = True) -> GradientBoostingClassifier:
    df = generate_synthetic_data()
    features = ["trades_per_day", "avg_trade_size", "pnl_sum", "max_burst_5min", "unique_symbols"]
    X = df[features]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    clf = GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=42)
    clf.fit(X_train, y_train)

    print(classification_report(y_test, clf.predict(X_test)))

    if save:
        with open(MODEL_PATH, "wb") as f:
            pickle.dump(clf, f)
        print(f"Model saved to {MODEL_PATH}")

    return clf


if __name__ == "__main__":
    train()
