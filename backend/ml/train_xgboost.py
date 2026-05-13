"""
Train an XGBoost multi-class classifier for trading bias detection.

Reads the four trader CSVs, engineers features over sliding windows,
trains the model with cross-validation, and saves it to saved_models/.

Usage:
    python -m backend.ml.train_xgboost
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_score
from xgboost import XGBClassifier

from backend.ml.features import FEATURE_NAMES, extract_windowed_features

# ── paths ──────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).resolve().parents[2] / "trading_datasets"
MODEL_DIR = Path(__file__).resolve().parent / "saved_models"
MODEL_PATH = MODEL_DIR / "bias_xgb.joblib"
REPORT_PATH = MODEL_DIR / "training_report.json"

# ── label mapping ──────────────────────────────────────────────────────
LABEL_MAP: dict[str, str] = {
    "calm_trader.csv": "calm",
    "overtrader.csv": "overtrading",
    "loss_averse_trader.csv": "loss_aversion",
    "revenge_trader.csv": "revenge_trading",
}


def load_and_featurize(
    window_size: int = 50,
    stride: int = 25,
) -> tuple[np.ndarray, np.ndarray]:
    """Load all CSVs, extract windowed features, return X and y arrays."""
    all_features: list[np.ndarray] = []
    all_labels: list[str] = []

    for filename, label in LABEL_MAP.items():
        csv_path = DATA_DIR / filename
        if not csv_path.exists():
            print(f"⚠️  Skipping {filename} (not found at {csv_path})")
            continue

        df = pd.read_csv(csv_path)
        print(f"📄 {filename}: {len(df)} trades → label='{label}'")

        windows = extract_windowed_features(df, window_size=window_size, stride=stride)
        all_features.extend(windows)
        all_labels.extend([label] * len(windows))
        print(f"   → {len(windows)} feature windows")

    X = np.array(all_features)
    y = np.array(all_labels)
    print(f"\n✅ Total dataset: {X.shape[0]} samples × {X.shape[1]} features")
    print(f"   Class distribution: { {lbl: int((y == lbl).sum()) for lbl in sorted(set(y))} }")
    return X, y


def train(
    window_size: int = 50,
    stride: int = 25,
    n_folds: int = 5,
) -> None:
    """Train XGBoost, evaluate with cross-validation, save model."""
    X, y = load_and_featurize(window_size=window_size, stride=stride)

    # Encode labels as integers for XGBoost
    classes = sorted(set(y))
    label_to_int = {lbl: i for i, lbl in enumerate(classes)}
    y_encoded = np.array([label_to_int[lbl] for lbl in y])

    # ── Model ──────────────────────────────────────────────────────────
    model = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        objective="multi:softprob",
        num_class=len(classes),
        eval_metric="mlogloss",
        random_state=42,
        n_jobs=-1,
        verbosity=0,
    )

    # ── Cross-validation ───────────────────────────────────────────────
    print("\n🔄 Running 5-fold stratified cross-validation...")
    cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X, y_encoded, cv=cv, scoring="accuracy")
    print(f"   CV Accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
    print(f"   Per-fold:    {[round(s, 4) for s in cv_scores]}")

    # ── Train on full data ─────────────────────────────────────────────
    print("\n🚀 Training final model on full dataset...")
    model.fit(X, y_encoded)

    # Classification report on training data (for reference)
    y_pred = model.predict(X)
    report = classification_report(y_encoded, y_pred, target_names=classes, output_dict=True)
    cm = confusion_matrix(y_encoded, y_pred)

    print("\n📊 Training classification report:")
    print(classification_report(y_encoded, y_pred, target_names=classes))
    print("Confusion matrix:")
    print(cm)

    # ── Feature importance ─────────────────────────────────────────────
    importances = model.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]
    print("\n🔑 Top 10 features:")
    for i in sorted_idx[:10]:
        print(f"   {FEATURE_NAMES[i]:40s} {importances[i]:.4f}")

    # ── Save ───────────────────────────────────────────────────────────
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # Store classes on the model so we can decode predictions later
    model.bias_classes_ = classes
    joblib.dump(model, MODEL_PATH)
    print(f"\n💾 Model saved to {MODEL_PATH}")

    # Save report
    training_report = {
        "cv_accuracy_mean": round(float(cv_scores.mean()), 4),
        "cv_accuracy_std": round(float(cv_scores.std()), 4),
        "cv_per_fold": [round(float(s), 4) for s in cv_scores],
        "classes": classes,
        "feature_names": FEATURE_NAMES,
        "feature_importances": {
            FEATURE_NAMES[i]: round(float(importances[i]), 4) for i in sorted_idx
        },
        "classification_report": {
            k: v for k, v in report.items() if isinstance(v, dict)
        },
        "confusion_matrix": cm.tolist(),
        "window_size": window_size,
        "stride": stride,
        "total_samples": int(X.shape[0]),
    }
    REPORT_PATH.write_text(json.dumps(training_report, indent=2))
    print(f"📋 Training report saved to {REPORT_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train XGBoost bias classifier")
    parser.add_argument("--window-size", type=int, default=50, help="Trades per window (default: 50)")
    parser.add_argument("--stride", type=int, default=25, help="Window stride (default: 25)")
    parser.add_argument("--folds", type=int, default=5, help="CV folds (default: 5)")
    args = parser.parse_args()

    train(window_size=args.window_size, stride=args.stride, n_folds=args.folds)
