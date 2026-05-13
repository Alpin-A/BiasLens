from __future__ import annotations

import numpy as np
import pandas as pd


def detect_loss_aversion(df: pd.DataFrame) -> dict:
    empty_stats = {
        "avg_loser_hold_minutes": 0.0,
        "avg_winner_hold_minutes": 0.0,
        "loser_to_winner_hold_ratio": 0.0,
        "avg_loss_size": 0.0,
        "avg_win_size": 0.0,
        "loss_to_win_ratio": 0.0,
        "risk_reward_ratio": 0.0,
    }
    if df.empty:
        return {"score": 0.0, "flags": [], "evidence": [], "stats": empty_stats}

    winners = df[df["pnl"] > 0]
    losers = df[df["pnl"] < 0]

    avg_winner_hold = float(winners["hold_minutes"].mean()) if not winners.empty else 0.0
    avg_loser_hold = float(losers["hold_minutes"].mean()) if not losers.empty else 0.0

    if avg_winner_hold <= 0:
        hold_ratio = 1.0 if avg_loser_hold > 0 else 0.0
    else:
        hold_ratio = avg_loser_hold / avg_winner_hold

    # ── Avg loss vs avg win size ──
    avg_win_size = float(winners["pnl"].mean()) if not winners.empty else 0.0
    avg_loss_size = float(losers["pnl"].abs().mean()) if not losers.empty else 0.0

    if avg_win_size > 0:
        loss_to_win_ratio = avg_loss_size / avg_win_size
    else:
        loss_to_win_ratio = 0.0

    # ── Risk / Reward ratio ──
    if avg_loss_size > 0:
        risk_reward_ratio = avg_win_size / avg_loss_size
    else:
        risk_reward_ratio = float("inf") if avg_win_size > 0 else 0.0

    # ── Composite score ──
    hold_component = float(np.clip((hold_ratio - 1.0) * 60, 0, 100))
    size_component = float(np.clip((loss_to_win_ratio - 1.0) * 50, 0, 100))
    score = float(np.clip(0.5 * hold_component + 0.5 * size_component, 0, 100))

    # ── Flags ──
    flag_condition = df["pnl"] < 0
    if avg_winner_hold > 0:
        flag_condition = flag_condition & (df["hold_minutes"] > (1.5 * avg_winner_hold))
    # Also flag trades where loss exceeds 2× avg win
    if avg_win_size > 0:
        big_loss = (df["pnl"] < 0) & (df["pnl"].abs() > 2.0 * avg_win_size)
        flag_condition = flag_condition | big_loss

    flagged_indices = df.index[flag_condition].tolist()

    evidence = [
        {
            "metric": "avg_loser_hold_minutes",
            "value": round(avg_loser_hold, 2),
            "note": "Mean hold duration for losing trades.",
        },
        {
            "metric": "avg_winner_hold_minutes",
            "value": round(avg_winner_hold, 2),
            "note": "Mean hold duration for winning trades.",
        },
        {
            "metric": "loser_to_winner_hold_ratio",
            "value": round(hold_ratio, 3),
            "note": "Values above 1.0 indicate longer hold time on losers.",
        },
        {
            "metric": "avg_loss_size",
            "value": round(avg_loss_size, 2),
            "note": "Mean absolute loss per losing trade.",
        },
        {
            "metric": "avg_win_size",
            "value": round(avg_win_size, 2),
            "note": "Mean profit per winning trade.",
        },
        {
            "metric": "loss_to_win_ratio",
            "value": round(loss_to_win_ratio, 3),
            "note": "Avg loss / avg win. Above 1.0 means losses are larger than wins.",
        },
        {
            "metric": "risk_reward_ratio",
            "value": round(risk_reward_ratio, 3) if risk_reward_ratio != float("inf") else "∞",
            "note": "Avg win / avg loss. Below 1.0 suggests poor risk management.",
        },
    ]

    return {
        "score": score,
        "flags": flagged_indices,
        "evidence": evidence,
        "stats": {
            "avg_loser_hold_minutes": round(avg_loser_hold, 2),
            "avg_winner_hold_minutes": round(avg_winner_hold, 2),
            "loser_to_winner_hold_ratio": round(hold_ratio, 3),
            "avg_loss_size": round(avg_loss_size, 2),
            "avg_win_size": round(avg_win_size, 2),
            "loss_to_win_ratio": round(loss_to_win_ratio, 3),
            "risk_reward_ratio": round(risk_reward_ratio, 3) if risk_reward_ratio != float("inf") else 999.0,
        },
    }
