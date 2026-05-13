from __future__ import annotations

from io import StringIO
from typing import Iterable

import numpy as np
import pandas as pd

from backend.core.schemas import ColumnMapping, TradeInput

REQUIRED_COLUMNS = ["timestamp", "side", "symbol", "price", "quantity", "pnl"]

# Common aliases for auto-detection when default mapping fails
COLUMN_ALIASES: dict[str, list[str]] = {
    "timestamp": ["timestamp", "time", "date", "datetime", "date_time", "trade_time", "executed_at"],
    "side": ["side", "direction", "type", "action", "buy_sell", "order_side"],
    "symbol": ["symbol", "asset", "ticker", "instrument", "stock", "coin", "pair", "name"],
    "quantity": ["quantity", "qty", "size", "amount", "volume", "shares", "lots"],
    "price": ["price", "entry_price", "entryprice", "exec_price", "fill_price", "avg_price", "trade_price"],
    "pnl": ["pnl", "profit_loss", "profitloss", "profit", "pl", "p_l", "realized_pnl", "gain", "return"],
    "hold_minutes": ["hold_minutes", "holdminutes", "hold_time", "holdtime", "duration"],
}

# Extra columns we want to preserve if present (not renamed, just kept)
PASSTHROUGH_COLUMNS = ["entry_price", "exit_price", "balance"]


def _auto_detect_mapping(df: pd.DataFrame) -> ColumnMapping:
    """Try to guess column mapping from common aliases."""
    lower_cols = {c.lower().replace(" ", "_"): c for c in df.columns}
    detected: dict[str, str] = {}

    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lower_cols:
                detected[field] = lower_cols[alias]
                break

    return ColumnMapping(**{k: v for k, v in detected.items() if v})


def _rename_columns(df: pd.DataFrame, mapping: ColumnMapping) -> pd.DataFrame:
    rename_map = {
        mapping.timestamp: "timestamp",
        mapping.side: "side",
        mapping.symbol: "symbol",
        mapping.price: "price",
        mapping.quantity: "quantity",
        mapping.pnl: "pnl",
    }
    if mapping.hold_minutes:
        rename_map[mapping.hold_minutes] = "hold_minutes"

    available = {k: v for k, v in rename_map.items() if k in df.columns}
    renamed = df.rename(columns=available)

    # Preserve passthrough columns: if entry_price was renamed to price,
    # keep a copy so downstream ML features can still use it.
    for col in PASSTHROUGH_COLUMNS:
        if col not in renamed.columns and col in df.columns:
            renamed[col] = df[col]

    missing = [column for column in REQUIRED_COLUMNS if column not in renamed.columns]
    if missing:
        raise ValueError(f"Missing required columns after mapping: {', '.join(missing)}")

    return renamed


def _coerce_trade_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")
    result["side"] = result["side"].astype(str).str.lower().str.strip()
    result["symbol"] = result["symbol"].astype(str).str.upper().str.strip()

    for numeric_col in ["price", "quantity", "pnl"]:
        result[numeric_col] = pd.to_numeric(result[numeric_col], errors="coerce")

    for opt_col in ["entry_price", "exit_price", "balance"]:
        if opt_col in result.columns:
            result[opt_col] = pd.to_numeric(result[opt_col], errors="coerce")

    if "hold_minutes" in result.columns:
        result["hold_minutes"] = pd.to_numeric(result["hold_minutes"], errors="coerce")

    result = result.dropna(subset=["timestamp", "side", "symbol", "price", "quantity", "pnl"])

    if "hold_minutes" not in result.columns:
        result["hold_minutes"] = np.nan

    result = result.sort_values("timestamp").reset_index(drop=True)
    return result


def infer_hold_minutes(df: pd.DataFrame) -> pd.DataFrame:
    """Use a proxy hold duration when explicit hold data is not available.

    For each symbol, hold duration is estimated as minutes until the next trade in the same symbol.
    The last trade for each symbol falls back to the median inferred duration.
    """
    result = df.copy()

    if result["hold_minutes"].notna().sum() > 0:
        result["hold_minutes"] = result["hold_minutes"].fillna(result["hold_minutes"].median())
        return result

    result["next_timestamp"] = result.groupby("symbol")["timestamp"].shift(-1)
    inferred = (
        (result["next_timestamp"] - result["timestamp"])
        .dt.total_seconds()
        .div(60)
        .clip(lower=0)
    )

    default_hold = float(inferred.median()) if inferred.notna().sum() else 0.0
    result["hold_minutes"] = inferred.fillna(default_hold)
    result = result.drop(columns=["next_timestamp"])
    return result


def trades_to_dataframe(trades: Iterable[TradeInput]) -> pd.DataFrame:
    records = [trade.model_dump(mode="json") for trade in trades]
    df = pd.DataFrame(records)
    df = _coerce_trade_columns(df)
    return infer_hold_minutes(df)


def csv_to_dataframe(csv_content: str, mapping: ColumnMapping) -> pd.DataFrame:
    raw_df = pd.read_csv(StringIO(csv_content))

    default_mapping = ColumnMapping()
    mapping_dict = mapping.model_dump(exclude_none=True)
    default_dict = default_mapping.model_dump(exclude_none=True)

    # If the default mapping doesn't match the CSV columns, try auto-detection
    has_custom_mapping = mapping_dict != default_dict
    if not has_custom_mapping:
        missing_defaults = [c for c in REQUIRED_COLUMNS if c not in raw_df.columns]
        if missing_defaults:
            mapping = _auto_detect_mapping(raw_df)

    renamed = _rename_columns(raw_df, mapping)
    coerced = _coerce_trade_columns(renamed)
    return infer_hold_minutes(coerced)


def dataframe_to_json_records(df: pd.DataFrame) -> list[dict]:
    serializable = df.copy()
    serializable["timestamp"] = serializable["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return serializable.to_dict(orient="records")
