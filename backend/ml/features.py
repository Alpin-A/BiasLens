"""Feature engineering for bias classification."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

# Ordered list of feature names — must stay in sync with extract_features()
FEATURE_NAMES: list[str] = [
    "trades_per_hour",
    "mean_time_between_trades_sec",
    "std_time_between_trades_sec",
    "burst_count_60s",
    "pnl_mean",
    "pnl_std",
    "pnl_total",
    "win_rate",
    "avg_quantity",
    "std_quantity",
    "avg_trade_value",
    "loss_hold_to_win_hold_ratio",
    "avg_size_after_loss_ratio",
    "reentry_after_loss_mean_sec",
    "consecutive_loss_streak_max",
    "side_switch_rate",
    "unique_symbols",
    "balance_drawdown_pct",
]


def _time_between_trades(df: pd.DataFrame) -> pd.Series:
    """Return time deltas between consecutive trades in seconds."""
    return df["timestamp"].diff().dt.total_seconds().dropna()


def extract_features(df: pd.DataFrame) -> np.ndarray:
    """
    Extract a single feature vector from a DataFrame of trades.

    Expects columns: timestamp, asset/symbol, side, quantity,
                     entry_price, exit_price, profit_loss/pnl, balance (optional)

    Returns a 1-D numpy array matching FEATURE_NAMES order.
    """
    # Normalize column names to handle both raw CSV and app-internal formats
    col_map = {
        "asset": "symbol",
        "profit_loss": "pnl",
        "entry_price": "entry_price",
        "exit_price": "exit_price",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.sort_values("timestamp").reset_index(drop=True)

    n = len(df)
    if n < 2:
        return np.zeros(len(FEATURE_NAMES), dtype=float)

    # --- Time features ---
    deltas = _time_between_trades(df)
    total_hours = max((df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]).total_seconds() / 3600, 0.001)
    trades_per_hour = n / total_hours
    mean_delta = float(deltas.mean()) if len(deltas) > 0 else 0.0
    std_delta = float(deltas.std(ddof=0)) if len(deltas) > 0 else 0.0

    burst_count = int((deltas <= 60).sum())

    # --- PnL features ---
    pnl = df["pnl"].astype(float)
    pnl_mean = float(pnl.mean())
    pnl_std = float(pnl.std(ddof=0))
    pnl_total = float(pnl.sum())
    win_rate = float((pnl > 0).sum() / n)

    # --- Size features ---
    qty = df["quantity"].astype(float)
    avg_qty = float(qty.mean())
    std_qty = float(qty.std(ddof=0))

    if "entry_price" in df.columns:
        trade_values = qty * df["entry_price"].astype(float)
    elif "price" in df.columns:
        trade_values = qty * df["price"].astype(float)
    else:
        trade_values = qty
    avg_trade_value = float(trade_values.mean())

    # --- Loss aversion: hold time proxy ---
    # If we have entry/exit price, hold time is implicit (1 row = 1 round trip).
    # Use time_between_trades as a proxy for hold duration.
    wins_mask = pnl > 0
    losses_mask = pnl <= 0

    hold_proxy = deltas.reindex(range(n), fill_value=deltas.median() if len(deltas) > 0 else 60.0)

    win_hold = hold_proxy[wins_mask].mean() if wins_mask.sum() > 0 else 1.0
    loss_hold = hold_proxy[losses_mask].mean() if losses_mask.sum() > 0 else 1.0
    loss_hold_to_win_hold_ratio = float(loss_hold / max(win_hold, 0.001))

    # --- Revenge trading features ---
    sizes_after_loss: list[float] = []
    sizes_after_win: list[float] = []
    reentry_times_after_loss: list[float] = []

    for i in range(1, n):
        prev_pnl = float(pnl.iloc[i - 1])
        curr_qty = float(qty.iloc[i])
        prev_qty = float(qty.iloc[i - 1])

        if prev_pnl < 0:
            sizes_after_loss.append(curr_qty / max(prev_qty, 0.001))
            if i < len(deltas) + 1:
                reentry_times_after_loss.append(float(deltas.iloc[i - 1]) if i - 1 < len(deltas) else 60.0)
        else:
            sizes_after_win.append(curr_qty / max(prev_qty, 0.001))

    avg_size_after_loss_ratio = float(np.mean(sizes_after_loss)) if sizes_after_loss else 1.0
    reentry_after_loss_mean = float(np.mean(reentry_times_after_loss)) if reentry_times_after_loss else 300.0

    max_streak = 0
    current_streak = 0
    for p in pnl:
        if p <= 0:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0

    # --- Diversity features ---
    side_changes = (df["side"].str.lower() != df["side"].str.lower().shift()).sum()
    side_switch_rate = float(side_changes / max(n - 1, 1))
    unique_symbols = int(df["symbol"].nunique())

    # --- Balance drawdown ---
    if "balance" in df.columns:
        bal = df["balance"].astype(float)
        running_max = bal.cummax()
        drawdown = ((running_max - bal) / running_max.replace(0, 1)).max()
        balance_drawdown_pct = float(drawdown) * 100
    else:
        balance_drawdown_pct = 0.0

    return np.array(
        [
            trades_per_hour,
            mean_delta,
            std_delta,
            burst_count,
            pnl_mean,
            pnl_std,
            pnl_total,
            win_rate,
            avg_qty,
            std_qty,
            avg_trade_value,
            loss_hold_to_win_hold_ratio,
            avg_size_after_loss_ratio,
            reentry_after_loss_mean,
            max_streak,
            side_switch_rate,
            unique_symbols,
            balance_drawdown_pct,
        ],
        dtype=float,
    )


def extract_windowed_features(
    df: pd.DataFrame,
    window_size: int = 50,
    stride: int = 25,
) -> list[np.ndarray]:
    """
    Slide a window over the trade DataFrame and extract features for each window.
    Returns a list of feature vectors.
    """
    features = []
    for start in range(0, len(df) - window_size + 1, stride):
        window = df.iloc[start : start + window_size]
        features.append(extract_features(window))
    return features
