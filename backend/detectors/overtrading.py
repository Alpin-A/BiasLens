from __future__ import annotations

import numpy as np
import pandas as pd


def detect_overtrading(
    df: pd.DataFrame,
    trades_per_day_threshold: int = 15,
    burst_window_minutes: int = 10,
    burst_threshold: int = 5,
) -> dict:
    if df.empty:
        return {
            "score": 0.0,
            "flags": [],
            "evidence": [],
            "stats": {
                "avg_trades_per_day": 0.0,
                "max_trades_per_day": 0,
                "max_burst_trades": 0,
                "position_switches": 0,
            },
        }

    result = df.copy()
    result["trade_date"] = result["timestamp"].dt.date

    trades_per_day = result.groupby("trade_date").size()
    avg_trades_per_day = float(trades_per_day.mean())
    max_trades_per_day = int(trades_per_day.max())

    # ── Burst detection ──
    timestamps = result["timestamp"]
    rolling_counts = []
    for timestamp in timestamps:
        in_window = (timestamps >= timestamp - pd.Timedelta(minutes=burst_window_minutes)) & (
            timestamps <= timestamp
        )
        rolling_counts.append(int(in_window.sum()))
    result["burst_count"] = rolling_counts
    max_burst_trades = int(result["burst_count"].max()) if not result.empty else 0

    # ── Position-switching detection ──
    sorted_df = result.sort_values("timestamp")
    position_switches = 0
    switch_indices: set[int] = set()
    for sym, grp in sorted_df.groupby("symbol"):
        if len(grp) < 2:
            continue
        sides = grp["side"].values
        times = grp["timestamp"].values
        idxs = grp.index.values
        for i in range(1, len(grp)):
            if sides[i] != sides[i - 1]:
                gap = (times[i] - times[i - 1]) / np.timedelta64(1, "m")
                if gap <= 5:
                    position_switches += 1
                    switch_indices.add(int(idxs[i]))

    # ── Score ──
    day_component = min(avg_trades_per_day / trades_per_day_threshold, 2.0)
    burst_component = min(max_burst_trades / burst_threshold, 2.0)
    switch_component = min(position_switches / max(len(df) * 0.05, 1), 2.0)
    score = float(np.clip(
        (0.45 * day_component + 0.3 * burst_component + 0.25 * switch_component) * 50,
        0, 100,
    ))

    # ── Flags ──
    high_day_dates = set(trades_per_day[trades_per_day > trades_per_day_threshold].index)
    flagged_indices = set(result.index[result["burst_count"] >= burst_threshold].tolist())
    flagged_indices.update(result.index[result["trade_date"].isin(high_day_dates)].tolist())
    flagged_indices.update(switch_indices)

    evidence = [
        {
            "metric": "avg_trades_per_day",
            "value": round(avg_trades_per_day, 2),
            "note": f"Threshold: {trades_per_day_threshold} trades/day.",
        },
        {
            "metric": "max_trades_per_day",
            "value": max_trades_per_day,
            "note": "Highest daily activity in the sample.",
        },
        {
            "metric": "max_burst_trades",
            "value": max_burst_trades,
            "note": f"Max trades in any {burst_window_minutes}-minute window.",
        },
        {
            "metric": "position_switches",
            "value": position_switches,
            "note": "Rapid buy↔sell flips on same symbol within 5 min.",
        },
    ]

    return {
        "score": score,
        "flags": sorted(flagged_indices),
        "evidence": evidence,
        "stats": {
            "avg_trades_per_day": round(avg_trades_per_day, 2),
            "max_trades_per_day": max_trades_per_day,
            "max_burst_trades": max_burst_trades,
            "position_switches": position_switches,
        },
    }
