"""Chat endpoint — multi-turn conversation about the user's analysis."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.llm.gemini_client import GeminiClient

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|model)$")
    text: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    analysis_context: dict[str, Any] = Field(
        ...,
        description="The full AnalyzeResponse object (bias_scores, flagged_trades, feature_stats, etc.)",
    )


class ChatResponse(BaseModel):
    reply: str


def _build_context_summary(ctx: dict[str, Any]) -> str:
    """Condense the analysis context into a readable string for the system prompt.

    We don't send the entire normalized_trades array (could be 10K+ rows).
    Instead we send bias scores, feature stats, and the first 30 flagged trades.
    """
    parts: list[str] = []

    # Bias scores
    bias_scores = ctx.get("bias_scores", {})
    if bias_scores:
        parts.append("### Bias Scores")
        for name, info in bias_scores.items():
            score = info.get("score", "?")
            severity = info.get("severity", "?")
            rationale = info.get("rationale", "")
            parts.append(f"- **{name}**: {score}/100 ({severity}) — {rationale}")

    # Feature stats
    feature_stats = ctx.get("feature_stats", {})
    if feature_stats:
        parts.append("\n### Feature Stats")
        for key, val in feature_stats.items():
            if key in ("ml_probabilities",):
                parts.append(f"- {key}: {json.dumps(val)}")
            else:
                parts.append(f"- {key}: {val}")

    # Flagged trades (cap at 30 to keep prompt size manageable)
    flagged = ctx.get("flagged_trades", [])
    if flagged:
        shown = flagged[:30]
        parts.append(f"\n### Flagged Trades ({len(flagged)} total, showing first {len(shown)})")
        for ft in shown:
            idx = ft.get("trade_index", "?")
            ts = ft.get("timestamp", "")
            sym = ft.get("symbol", "")
            pnl = ft.get("pnl", 0)
            tags = ", ".join(ft.get("tags", []))
            reason = ft.get("reason", "")
            parts.append(f"- #{idx} [{ts}] {sym} PnL={pnl} | tags: {tags} | {reason}")

    # Trade summary (not full list)
    trades = ctx.get("normalized_trades", [])
    if trades:
        total_pnl = sum(float(t.get("pnl", 0) or 0) for t in trades)
        wins = sum(1 for t in trades if float(t.get("pnl", 0) or 0) > 0)
        losses = sum(1 for t in trades if float(t.get("pnl", 0) or 0) < 0)
        symbols = list({t.get("symbol", "") for t in trades if t.get("symbol")})
        parts.append(f"\n### Trade Summary")
        parts.append(f"- Total trades: {len(trades)}")
        parts.append(f"- Total PnL: {total_pnl:.2f}")
        parts.append(f"- Wins: {wins}, Losses: {losses}")
        parts.append(f"- Symbols: {', '.join(symbols[:20])}")

    return "\n".join(parts)


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Handle a multi-turn chat message about the user's analysis."""
    if not req.messages:
        raise HTTPException(status_code=400, detail="No messages provided.")

    last_msg = req.messages[-1]
    if last_msg.role != "user":
        raise HTTPException(status_code=400, detail="Last message must be from the user.")

    # Build condensed context string
    context_str = _build_context_summary(req.analysis_context)

    # Convert to format expected by GeminiClient
    messages = [{"role": m.role, "text": m.text} for m in req.messages]

    try:
        client = GeminiClient()
        reply = client.chat(messages, analysis_context=context_str)
        return ChatResponse(reply=reply)
    except RuntimeError as exc:
        logger.error("Chat Gemini error: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))
