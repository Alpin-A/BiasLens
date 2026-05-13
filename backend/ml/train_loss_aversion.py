"""
Loss aversion classifier – training stub.

Approach: per-trade binary classifier.
Labels via weak supervision: holding losers > 2× median winner hold time.
"""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

MODEL_DIR = Path(__file__).parent / "saved_models"
MODEL_DIR.mkdir(exist_ok=True)
MODEL_PATH = MODEL_DIR / "loss_aversion_clf.pkl"


def generate_synthetic_data(n_trades: int = 2000) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    data = pd.DataFrame(
        {
            "hold_minutes": rng.exponential(scale=60, size=n_trades),
            "realized_pnl": rng.normal(loc=0, scale=200, size=n_trades),
            "trade_size": rng.lognormal(mean=3, sigma=0.5, size=n_trades),
            "loss_streak": rng.integers(0, 5, size=n_trades),
            "pnl_ratio_to_avg": rng.normal(loc=1, scale=0.5, size=n_trades),
        }
    )
    median_winner_hold = data.loc[data["realized_pnl"] > 0, "hold_minutes"].median()
    if pd.isna(median_winner_hold):
        median_winner_hold = 30
    data["label"] = (
        (data["realized_pnl"] < 0) & (data["hold_minutes"] > 2 * median_winner_hold)
    ).astype(int)
    return data


def train(save: bool = True) -> RandomForestClassifier:
    df = generate_synthetic_data()
    features = ["hold_minutes", "realized_pnl", "trade_size", "loss_streak", "pnl_ratio_to_avg"]
    X = df[features]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    clf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    clf.fit(X_train, y_train)

    print(classification_report(y_test, clf.predict(X_test)))

    if save:
        with open(MODEL_PATH, "wb") as f:
            pickle.dump(clf, f)
        print(f"Model saved to {MODEL_PATH}")

    return clf


if __name__ == "__main__":
    train()
