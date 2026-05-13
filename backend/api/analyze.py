from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.core.analysis_engine import analyze_biases, MODE_MIXED, VALID_MODES
from backend.core.schemas import AnalyzeRequest, AnalyzeResponse, ColumnMapping
from backend.utils.data_loader import csv_to_dataframe, dataframe_to_json_records, trades_to_dataframe

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_trades(
    file: Optional[UploadFile] = File(None),
    mapping: Optional[str] = Form(None),
    analysis_mode: Optional[str] = Form(None),
    body: Optional[AnalyzeRequest] = None,
) -> AnalyzeResponse:
    """Detect trading biases from uploaded CSV or JSON trade list."""

    parsed_mapping = ColumnMapping()
    if mapping:
        try:
            parsed_mapping = ColumnMapping(**json.loads(mapping))
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=f"Invalid mapping JSON: {exc}") from exc

    mode = analysis_mode if analysis_mode and analysis_mode in VALID_MODES else MODE_MIXED

    # Branch 1: CSV upload via multipart form
    if file is not None:
        if not file.filename or not file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="Please upload a .csv file.")
        file_bytes = await file.read()
        try:
            csv_content = file_bytes.decode("utf-8")
            df = csv_to_dataframe(csv_content, parsed_mapping)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"CSV processing error: {exc}") from exc

    # Branch 2: JSON body
    elif body is not None:
        parsed_mapping = body.mapping
        if body.analysis_mode and body.analysis_mode in VALID_MODES:
            mode = body.analysis_mode
        if body.csv_content:
            try:
                df = csv_to_dataframe(body.csv_content, parsed_mapping)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"CSV processing error: {exc}") from exc
        elif body.trades:
            try:
                df = trades_to_dataframe(body.trades)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"Trade processing error: {exc}") from exc
        else:
            raise HTTPException(status_code=400, detail="Provide csv_content, trades, or upload a file.")
    else:
        raise HTTPException(status_code=400, detail="No input provided.")

    if df.empty:
        raise HTTPException(status_code=400, detail="No valid trades found after processing.")

    result = analyze_biases(df, analysis_mode=mode)
    result["normalized_trades"] = dataframe_to_json_records(df)

    return AnalyzeResponse(**result)
