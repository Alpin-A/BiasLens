"""
Revenge trading classifier – training stub.

Approach: time-series classifier with 3–5 trade context window.
Labels via weak supervision: re-entry within 30 min of a loss with increased size.
"""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

MODEL_DIR = Path(__file__).parent / "saved_models"
MODEL_DIR.mkdir(exist_ok=True)
MODEL_PATH = MODEL_DIR / "revenge_trading_clf.pkl"


def generate_synthetic_data(n_trades: int = 2000) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    data = pd.DataFrame(
        {
            "minutes_since_loss": rng.exponential(scale=60, size=n_trades),
            "size_increase_pct": rng.normal(loc=0, scale=0.3, size=n_trades),
            "loss_streak": rng.integers(0, 6, size=n_trades),
            "prev_pnl": rng.normal(loc=0, scale=200, size=n_trades),
            "trade_size": rng.lognormal(mean=3, sigma=0.5, size=n_trades),
        }
    )
    data["label"] = (
        (data["minutes_since_loss"] < 30)
        & (data["prev_pnl"] < 0)
        & (data["size_increase_pct"] > 0.1)
    ).astype(int)
    return data


def train(save: bool = True) -> GradientBoostingClassifier:
    df = generate_synthetic_data()
    features = [
        "minutes_since_loss",
        "size_increase_pct",
        "loss_streak",
        "prev_pnl",
        "trade_size",
    ]
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
