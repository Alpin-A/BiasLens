from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.core.schemas import ShapExplainResponse, ColumnMapping, TradeInput
from backend.ml.shap_explainer import get_explainer
from backend.utils.data_loader import trades_to_dataframe

logger = logging.getLogger(__name__)
router = APIRouter()


class ShapExplainRequest(BaseModel):
    trades: list[TradeInput]
    mapping: ColumnMapping = Field(default_factory=ColumnMapping)


@router.post("/shap-explain", response_model=ShapExplainResponse)
async def shap_explain(body: ShapExplainRequest) -> ShapExplainResponse:
    """Compute SHAP explanations for bias predictions."""
    try:
        df = trades_to_dataframe(body.trades)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Trade processing error: {exc}") from exc

    if df.empty:
        raise HTTPException(status_code=400, detail="No valid trades found after processing.")

    explainer = get_explainer()
    if not explainer.is_available:
        raise HTTPException(
            status_code=503,
            detail="SHAP explainer not available (no trained model or shap library).",
        )

    try:
        result = explainer.explain_windows(df)
    except Exception as exc:
        logger.exception("SHAP computation failed")
        raise HTTPException(status_code=500, detail=f"SHAP computation error: {exc}") from exc

    return ShapExplainResponse(**result)
