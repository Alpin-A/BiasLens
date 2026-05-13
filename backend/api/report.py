from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from backend.core.schemas import ReportRequest, ReportResponse
from backend.llm.gemini_client import generate_coaching_report

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/report", response_model=ReportResponse)
def generate_report(payload: ReportRequest) -> ReportResponse:
    try:
        counterfactual = None
        if hasattr(payload, "analysis") and "counterfactual" in (payload.analysis or {}):
            counterfactual = payload.analysis["counterfactual"]

        report_md, plan = generate_coaching_report(
            analysis=payload.analysis,
            counterfactual=counterfactual,
        )
        return ReportResponse(report_markdown=report_md, coaching_plan=plan)
    except RuntimeError as exc:
        # Graceful fallback for rate-limit / API errors
        if "429" in str(exc) or "Too Many Requests" in str(exc):
            logger.warning("Gemini rate-limited for report – returning fallback.")
            return ReportResponse(
                report_markdown=(
                    "## ⏳ AI Report Temporarily Unavailable\n\n"
                    "The AI coaching engine is currently rate-limited. "
                    "Please wait a minute and try again.\n\n"
                    "In the meantime, review the bias scores and flagged trades in the other tabs."
                ),
                coaching_plan=[
                    "1. Review your bias scores in the Insights tab.",
                    "2. Check flagged trades and their patterns.",
                    "3. Try generating this report again in ~60 seconds.",
                ],
            )
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Report generation error: %s", exc)
        raise HTTPException(status_code=500, detail="Report generation failed.") from exc
