"""Tests for bias detectors and data loading pipeline."""
from __future__ import annotations

import pandas as pd
import pytest

from backend.utils.data_loader import csv_to_dataframe
from backend.core.schemas import ColumnMapping
from backend.core.analysis_engine import analyze_biases
from backend.detectors.overtrading import detect_overtrading
from backend.detectors.loss_aversion import detect_loss_aversion
from backend.detectors.revenge_trading import detect_revenge_trading


SAMPLE_CSV = """timestamp,side,symbol,quantity,price,pnl
2025-01-10 09:30:00,buy,AAPL,100,150.0,200
2025-01-10 09:31:00,sell,AAPL,100,149.0,-100
2025-01-10 09:32:00,buy,AAPL,200,148.0,-150
2025-01-10 09:33:00,sell,AAPL,200,149.5,300
2025-01-10 09:34:00,buy,TSLA,50,220.0,-50
2025-01-10 09:35:00,sell,TSLA,50,219.0,-50
2025-01-10 09:36:00,buy,TSLA,150,218.0,100
"""


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return csv_to_dataframe(SAMPLE_CSV, ColumnMapping())


def test_csv_to_dataframe(sample_df: pd.DataFrame):
    assert len(sample_df) == 7
    assert "timestamp" in sample_df.columns
    assert "pnl" in sample_df.columns
    assert "hold_minutes" in sample_df.columns
    assert sample_df["symbol"].iloc[0] == "AAPL"


def test_overtrading_detector(sample_df: pd.DataFrame):
    result = detect_overtrading(sample_df)
    assert "score" in result
    assert 0 <= result["score"] <= 100
    assert "flags" in result
    assert "evidence" in result
    assert "position_switches" in result["stats"]


def test_loss_aversion_detector(sample_df: pd.DataFrame):
    result = detect_loss_aversion(sample_df)
    assert "score" in result
    assert 0 <= result["score"] <= 100
    assert "stats" in result
    assert "avg_loss_size" in result["stats"]
    assert "avg_win_size" in result["stats"]
    assert "loss_to_win_ratio" in result["stats"]
    assert "risk_reward_ratio" in result["stats"]


def test_revenge_trading_detector(sample_df: pd.DataFrame):
    result = detect_revenge_trading(sample_df)
    assert "score" in result
    assert 0 <= result["score"] <= 100
    assert "stats" in result
    assert "streak_events" in result["stats"]


def test_analyze_biases_integration(sample_df: pd.DataFrame):
    result = analyze_biases(sample_df, analysis_mode="rules_only")
    assert "bias_scores" in result
    assert "overtrading" in result["bias_scores"]
    assert "loss_aversion" in result["bias_scores"]
    assert "revenge_trading" in result["bias_scores"]
    assert "calm" in result["bias_scores"]
    assert "flagged_trades" in result
    assert "bias_evidence" in result
    assert "feature_stats" in result
    assert result["feature_stats"]["analysis_mode"] == "rules_only"


def test_empty_dataframe():
    empty_df = pd.DataFrame(columns=["timestamp", "side", "symbol", "quantity", "price", "pnl", "hold_minutes"])
    ot = detect_overtrading(empty_df)
    la = detect_loss_aversion(empty_df)
    rt = detect_revenge_trading(empty_df)
    assert ot["score"] == 0.0
    assert la["score"] == 0.0
    assert rt["score"] == 0.0
