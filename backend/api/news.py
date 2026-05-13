from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend.core.schemas import NewsResponse, NewsItem
from backend.llm.gemini_client import search_ticker_news, search_general_news

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/news", response_model=NewsResponse)
def news_insights(
    date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    bias: str = Query("", description="Bias type filter"),
    symbols: Optional[str] = Query(None, description="Comma-separated ticker symbols"),
    date_to: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
) -> NewsResponse:
    try:
        if symbols:
            # Ticker-aware search via Gemini + Google Search grounding
            symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
            end_date = date_to or date
            result = search_ticker_news(
                symbols=symbol_list,
                date_from=date,
                date_to=end_date,
            )
        else:
            # General market news search
            result = search_general_news(date=date, bias=bias)

        headlines = [
            NewsItem(
                title=h.get("title", ""),
                source=h.get("source", ""),
                published_at=datetime.fromisoformat(
                    h.get("published_at", f"{date}T00:00:00Z").replace("Z", "+00:00")
                ),
                url=h.get("url", ""),
                symbol=h.get("symbol", None),
            )
            for h in result.get("headlines", [])
        ]

        from datetime import date as date_type

        return NewsResponse(
            date=date_type.fromisoformat(date),
            headlines=headlines,
            context=result.get("context"),
            symbols=result.get("symbols", []),
        )
    except RuntimeError as exc:
        # Graceful fallback for rate-limit / API errors
        if "429" in str(exc) or "Too Many Requests" in str(exc):
            logger.warning("Gemini rate-limited for news – returning fallback.")
            from datetime import date as date_type
            return NewsResponse(
                date=date_type.fromisoformat(date),
                headlines=[],
                context=(
                    "⏳ News search is temporarily rate-limited. "
                    "Please wait a minute and try again."
                ),
                symbols=[s.strip().upper() for s in symbols.split(",")] if symbols else [],
            )
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("News error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
