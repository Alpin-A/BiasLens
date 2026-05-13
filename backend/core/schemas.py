from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class ColumnMapping(BaseModel):
    timestamp: str = "timestamp"
    side: str = "side"
    symbol: str = "symbol"
    price: str = "price"
    quantity: str = "quantity"
    pnl: str = "pnl"
    hold_minutes: str | None = None


class TradeInput(BaseModel):
    timestamp: datetime
    side: str
    symbol: str
    price: float
    quantity: float
    pnl: float
    hold_minutes: float | None = None

    @field_validator("side")
    @classmethod
    def normalize_side(cls, value: str) -> str:
        normalized = value.strip().lower()
        aliases = {
            "b": "buy",
            "long": "buy",
            "s": "sell",
            "short": "sell",
        }
        return aliases.get(normalized, normalized)


class AnalyzeRequest(BaseModel):
    csv_content: str | None = None
    trades: list[TradeInput] | None = None
    mapping: ColumnMapping = Field(default_factory=ColumnMapping)
    analysis_mode: str = "mixed"


class BiasScore(BaseModel):
    score: float = Field(..., ge=0, le=100)
    severity: Literal["low", "medium", "high"]
    rationale: str


class BiasFlag(BaseModel):
    trade_index: int
    timestamp: datetime
    symbol: str
    pnl: float
    tags: list[Literal["overtrading", "loss_aversion", "revenge_trading", "calm"]]
    reason: str


class EvidenceItem(BaseModel):
    metric: str
    value: float | int | str
    note: str


class AnalyzeResponse(BaseModel):
    bias_scores: dict[str, BiasScore]
    flagged_trades: list[BiasFlag]
    bias_evidence: dict[str, list[EvidenceItem]]
    feature_stats: dict[str, Any]
    normalized_trades: list[dict[str, Any]]


class CounterfactualRules(BaseModel):
    cooldown_minutes_after_loss: int | None = Field(default=30, ge=0, le=480)
    max_trades_per_day: int | None = Field(default=20, ge=1, le=500)
    cap_size_after_loss: float | None = Field(default=1.0, ge=0.1, le=5.0)


class CounterfactualRequest(BaseModel):
    trades: list[TradeInput]
    rules: CounterfactualRules


class CounterfactualTrade(BaseModel):
    trade_index: int
    timestamp: datetime
    symbol: str
    side: str
    quantity: float
    pnl: float
    status: Literal["kept", "removed", "modified"]
    reason: str | None = None


class CounterfactualResponse(BaseModel):
    original_pnl: float
    counterfactual_pnl: float
    pnl_delta: float
    kept_trades: int
    removed_trades: int
    modified_trades: int
    modified_trade_list: list[CounterfactualTrade]


class BiasEvent(BaseModel):
    bias_type: str
    date: date
    trader_behavior: str
    headlines: list[str] = Field(default_factory=list)


class ReportRequest(BaseModel):
    analysis: dict[str, Any]
    bias_event: BiasEvent | None = None
    include_headlines: bool = True


class ReportResponse(BaseModel):
    report_markdown: str
    coaching_plan: list[str]


class NewsItem(BaseModel):
    title: str
    source: str
    published_at: datetime
    url: str
    symbol: str | None = None


class NewsResponse(BaseModel):
    date: date
    headlines: list[NewsItem]
    context: str | None = None
    symbols: list[str] = Field(default_factory=list)


# ── Trade Insights (per-flagged-trade Gemini analysis with news) ──


class TradeInsight(BaseModel):
    trade_index: int
    timestamp: datetime
    symbol: str
    side: str
    pnl: float
    tags: list[str]
    reason: str
    market_context: str
    gemini_explanation: str
    related_headlines: list[str] = Field(default_factory=list)


class TradeInsightsRequest(BaseModel):
    flagged_trades: list[BiasFlag]
    bias_scores: dict[str, BiasScore]
    normalized_trades: list[dict[str, Any]]
    symbols: list[str] = Field(default_factory=list)
    date_range: list[str] = Field(default_factory=list)


class TradeInsightsResponse(BaseModel):
    insights: list[TradeInsight]
    summary: str
    market_context: str


# ── SHAP Explainability ──


class ShapWindowData(BaseModel):
    window_index: int
    trade_range: list[int]
    feature_values: list[float]
    predictions: dict[str, float]
    shap_values: dict[str, list[float]]


class ShapExplainResponse(BaseModel):
    feature_names: list[str]
    classes: list[str]
    n_windows: int
    base_values: dict[str, float]
    windows: list[ShapWindowData]


ANALYZE_RESPONSE_EXAMPLE = {
    "bias_scores": {
        "overtrading": {
            "score": 78.5,
            "severity": "high",
            "rationale": "Trade frequency and burst activity exceeded thresholds on multiple days.",
        },
        "loss_aversion": {
            "score": 61.3,
            "severity": "medium",
            "rationale": "Average hold time for losing trades was 1.9x winners.",
        },
        "revenge_trading": {
            "score": 55.0,
            "severity": "medium",
            "rationale": "Several rapid re-entries after losses with larger size were detected.",
        },
    },
    "flagged_trades": [
        {
            "trade_index": 42,
            "timestamp": "2023-03-14T10:06:00Z",
            "symbol": "BTCUSD",
            "pnl": -520.0,
            "tags": ["revenge_trading"],
            "reason": "Re-entered 5 minutes after loss with 1.7x size.",
        }
    ],
    "bias_evidence": {
        "overtrading": [
            {
                "metric": "avg_trades_per_day",
                "value": 26.4,
                "note": "Above threshold of 15 trades/day.",
            }
        ],
        "loss_aversion": [
            {
                "metric": "loser_to_winner_hold_ratio",
                "value": 1.9,
                "note": "Losers held significantly longer than winners.",
            }
        ],
        "revenge_trading": [
            {
                "metric": "revenge_events",
                "value": 4,
                "note": "Rapid larger re-entry events detected after losses.",
            }
        ],
    },
    "feature_stats": {
        "trade_count": 350,
        "date_range": ["2023-01-01", "2023-03-31"],
        "pnl_total": 2410.5,
        "pnl_volatility": 312.4,
    },
    "normalized_trades": [],
}
