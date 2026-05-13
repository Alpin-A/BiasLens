from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from backend.core.schemas import (
    TradeInsight,
    TradeInsightsRequest,
    TradeInsightsResponse,
)
from backend.llm.gemini_client import search_ticker_news, generate_trade_insights

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/trade-insights", response_model=TradeInsightsResponse)
def get_trade_insights(payload: TradeInsightsRequest) -> TradeInsightsResponse:
    """Generate per-flagged-trade AI insights with market news context."""
    try:
        # Extract symbols and date range from the request
        symbols = payload.symbols
        if not symbols:
            # Auto-extract unique symbols from flagged trades
            symbols = list({t.symbol.upper() for t in payload.flagged_trades})

        date_range = payload.date_range
        if not date_range or len(date_range) < 2:
            # Auto-extract from normalized trades
            timestamps = [
                t.get("timestamp", "") for t in payload.normalized_trades if t.get("timestamp")
            ]
            if timestamps:
                sorted_ts = sorted(timestamps)
                date_range = [sorted_ts[0][:10], sorted_ts[-1][:10]]
            else:
                date_range = ["2025-01-01", "2025-12-31"]

        # Use Gemini + Google Search grounding to find relevant news
        news_result = search_ticker_news(
            symbols=symbols,
            date_from=date_range[0],
            date_to=date_range[1],
        )
        headlines = news_result.get("headlines", [])
        search_context = news_result.get("context", "")

        # Prepare flagged trades as dicts for Gemini
        flagged_dicts = [
            {
                "trade_index": t.trade_index,
                "timestamp": t.timestamp.isoformat() if isinstance(t.timestamp, datetime) else str(t.timestamp),
                "symbol": t.symbol,
                "pnl": t.pnl,
                "tags": t.tags,
                "reason": t.reason,
                "side": _find_trade_side(t.trade_index, payload.normalized_trades),
            }
            for t in payload.flagged_trades
        ]

        # Prepare bias scores as dicts
        bias_dicts = {
            k: {"score": v.score, "severity": v.severity, "rationale": v.rationale}
            for k, v in payload.bias_scores.items()
        }

        # Generate per-trade Gemini insights
        raw_insights = generate_trade_insights(
            flagged_trades=flagged_dicts,
            bias_scores=bias_dicts,
            search_context=search_context,
        )

        # Build structured response
        insights: list[TradeInsight] = []
        for ft in flagged_dicts:
            # Find matching Gemini insight
            matching = next(
                (r for r in raw_insights if r.get("trade_index") == ft["trade_index"]),
                None,
            )
            insights.append(
                TradeInsight(
                    trade_index=ft["trade_index"],
                    timestamp=ft["timestamp"],
                    symbol=ft["symbol"],
                    side=ft.get("side", "unknown"),
                    pnl=ft["pnl"],
                    tags=ft["tags"],
                    reason=ft["reason"],
                    market_context=matching.get("market_context", "No market context available.") if matching else "No market context available.",
                    gemini_explanation=matching.get("gemini_explanation", "AI analysis unavailable.") if matching else "AI analysis unavailable.",
                    related_headlines=matching.get("related_headlines", []) if matching else [],
                )
            )

        # Build overall summary
        total_flagged = len(insights)
        bias_types_found = list({tag for i in insights for tag in i.tags})
        summary = (
            f"Analyzed {total_flagged} flagged trade(s) across {len(symbols)} symbol(s). "
            f"Detected bias patterns: {', '.join(bias_types_found)}."
        )

        # Build overall market context from headlines
        headline_summary = "; ".join(h["title"] for h in headlines[:5]) if headlines else "No market news available."

        return TradeInsightsResponse(
            insights=insights,
            summary=summary,
            market_context=headline_summary,
        )

    except RuntimeError as exc:
        # Graceful fallback for rate-limit / API errors
        if "429" in str(exc) or "Too Many Requests" in str(exc):
            logger.warning("Gemini rate-limited for trade insights – returning fallback.")
            fallback_insights = [
                TradeInsight(
                    trade_index=t.trade_index,
                    timestamp=t.timestamp.isoformat() if isinstance(t.timestamp, datetime) else str(t.timestamp),
                    symbol=t.symbol,
                    side=_find_trade_side(t.trade_index, payload.normalized_trades),
                    pnl=t.pnl,
                    tags=t.tags,
                    reason=t.reason,
                    market_context="⏳ Rate-limited – try again in ~60 seconds.",
                    gemini_explanation="AI analysis temporarily unavailable due to rate limiting.",
                    related_headlines=[],
                )
                for t in payload.flagged_trades
            ]
            return TradeInsightsResponse(
                insights=fallback_insights,
                summary="⏳ AI insights are temporarily rate-limited. Please wait and try again.",
                market_context="Rate-limited.",
            )
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Trade insights error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Trade insights failed: {exc}") from exc


def _find_trade_side(trade_index: int, normalized_trades: list[dict[str, Any]]) -> str:
    """Look up the side of a trade by index."""
    if 0 <= trade_index < len(normalized_trades):
        return normalized_trades[trade_index].get("side", "unknown")
    return "unknown"
