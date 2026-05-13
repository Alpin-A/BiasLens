from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from backend.core.schemas import CounterfactualRequest, CounterfactualResponse, CounterfactualTrade

logger = logging.getLogger(__name__)
router = APIRouter()


def _simulate_counterfactual(
    trades: list[dict[str, Any]],
    cooldown: int,
    max_per_day: int,
    cap_size: float,
) -> CounterfactualResponse:
    import pandas as pd

    df = pd.DataFrame(trades)
    if df.empty:
        return CounterfactualResponse(
            original_pnl=0.0,
            counterfactual_pnl=0.0,
            pnl_delta=0.0,
            kept_trades=0,
            removed_trades=0,
            modified_trades=0,
            modified_trade_list=[],
        )

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.sort_values("timestamp").reset_index(drop=True)
    original_pnl = float(df["pnl"].sum())

    trade_results: list[CounterfactualTrade] = []
    last_loss_time = None
    day_counts: dict[str, int] = {}
    kept_pnl = 0.0

    for idx, row in df.iterrows():
        day_key = str(row["timestamp"].date())
        day_counts.setdefault(day_key, 0)

        status = "kept"
        reason = None

        # Rule 1: max trades/day
        if day_counts[day_key] >= max_per_day:
            status = "removed"
            reason = f"Exceeded max {max_per_day} trades/day."
        # Rule 2: cooldown after loss
        elif last_loss_time is not None:
            minutes_since = (row["timestamp"] - last_loss_time).total_seconds() / 60
            if minutes_since < cooldown:
                status = "removed"
                reason = f"Within {cooldown}-min cooldown after loss ({minutes_since:.0f} min)."
        # Rule 3: cap size after loss
        if status == "kept" and last_loss_time is not None and float(row["quantity"]) > cap_size:
            status = "modified"
            reason = f"Position size {row['quantity']} capped to {cap_size}."

        if status == "kept":
            kept_pnl += float(row["pnl"])
            day_counts[day_key] += 1
        elif status == "modified":
            scale = cap_size / max(float(row["quantity"]), 0.01)
            kept_pnl += float(row["pnl"]) * scale
            day_counts[day_key] += 1

        if float(row["pnl"]) < 0:
            last_loss_time = row["timestamp"]

        trade_results.append(
            CounterfactualTrade(
                trade_index=int(idx),
                timestamp=row["timestamp"],
                symbol=str(row["symbol"]),
                side=str(row["side"]),
                quantity=float(row["quantity"]),
                pnl=float(row["pnl"]),
                status=status,
                reason=reason,
            )
        )

    removed = sum(1 for t in trade_results if t.status == "removed")
    modified = sum(1 for t in trade_results if t.status == "modified")

    return CounterfactualResponse(
        original_pnl=round(original_pnl, 2),
        counterfactual_pnl=round(kept_pnl, 2),
        pnl_delta=round(kept_pnl - original_pnl, 2),
        kept_trades=len(trade_results) - removed,
        removed_trades=removed,
        modified_trades=modified,
        modified_trade_list=trade_results,
    )


@router.post("/counterfactual", response_model=CounterfactualResponse)
def run_counterfactual(payload: CounterfactualRequest) -> CounterfactualResponse:
    try:
        trades = [t.model_dump(mode="json") for t in payload.trades]
        return _simulate_counterfactual(
            trades,
            cooldown=payload.rules.cooldown_minutes_after_loss or 30,
            max_per_day=payload.rules.max_trades_per_day or 20,
            cap_size=payload.rules.cap_size_after_loss or 1.0,
        )
    except Exception as exc:
        logger.error("Counterfactual error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
