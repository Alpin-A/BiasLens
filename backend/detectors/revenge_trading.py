from __future__ import annotations

import numpy as np
import pandas as pd


def detect_revenge_trading(
    df: pd.DataFrame,
    reentry_window_minutes: int = 15,
    size_multiplier_threshold: float = 1.25,
    streak_threshold: int = 2,
) -> dict:
    if df.empty:
        return {
            "score": 0.0,
            "flags": [],
            "evidence": [],
            "stats": {
                "revenge_events": 0,
                "event_rate": 0.0,
                "streak_events": 0,
            },
        }

    sorted_df = df.sort_values("timestamp").reset_index()
    flagged_original_indices: set[int] = set()
    events = 0

    # ── Single-loss rapid re-entry ──
    for idx, row in sorted_df.iterrows():
        if row["pnl"] >= 0:
            continue

        future = sorted_df.iloc[idx + 1 : idx + 6]
        if future.empty:
            continue

        time_boundary = row["timestamp"] + pd.Timedelta(minutes=reentry_window_minutes)
        candidates = future[future["timestamp"] <= time_boundary]

        if candidates.empty:
            continue

        bigger_size = candidates[candidates["quantity"] >= row["quantity"] * size_multiplier_threshold]
        if bigger_size.empty:
            continue

        first_reentry = bigger_size.iloc[0]
        flagged_original_indices.add(int(first_reentry["index"]))
        events += 1

    # ── Streak-based detection ──
    # After N consecutive losses, if the trader increases size → revenge
    streak_events = 0
    loss_streak = 0
    for idx, row in sorted_df.iterrows():
        if row["pnl"] < 0:
            loss_streak += 1
        else:
            if loss_streak >= streak_threshold:
                streak_start = max(0, idx - loss_streak)
                streak_trades = sorted_df.iloc[streak_start:idx]
                avg_streak_qty = float(streak_trades["quantity"].mean()) if not streak_trades.empty else 0.0
                if avg_streak_qty > 0 and row["quantity"] >= avg_streak_qty * 1.1:
                    streak_events += 1
                    flagged_original_indices.add(int(row["index"]))
            loss_streak = 0

    total_events = events + streak_events
    event_rate = total_events / max(len(df), 1)
    score = float(np.clip(event_rate * 350, 0, 100))

    evidence = [
        {
            "metric": "revenge_events",
            "value": events,
            "note": "Rapid larger re-entries after a single loss.",
        },
        {
            "metric": "streak_events",
            "value": streak_events,
            "note": f"Increased size after {streak_threshold}+ consecutive losses.",
        },
        {
            "metric": "event_rate",
            "value": round(event_rate, 3),
            "note": "Total revenge events per trade in sample.",
        },
        {
            "metric": "reentry_window_minutes",
            "value": reentry_window_minutes,
            "note": "Configured time window for re-entry detection.",
        },
    ]

    return {
        "score": score,
        "flags": sorted(flagged_original_indices),
        "evidence": evidence,
        "stats": {
            "revenge_events": events,
            "event_rate": round(event_rate, 3),
            "streak_events": streak_events,
        },
    }
