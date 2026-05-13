from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from backend.detectors.common import score_to_severity
from backend.detectors.loss_aversion import detect_loss_aversion
from backend.detectors.overtrading import detect_overtrading
from backend.detectors.revenge_trading import detect_revenge_trading
from backend.ml.features import extract_features, extract_windowed_features
from backend.ml.model import BiasMLClassifier

import logging

logger = logging.getLogger(__name__)

BIAS_TYPES = ["overtrading", "loss_aversion", "revenge_trading"]

MODE_RULES_ONLY = "rules_only"
MODE_ML_ONLY = "ml_only"
MODE_MIXED = "mixed"
VALID_MODES = {MODE_RULES_ONLY, MODE_ML_ONLY, MODE_MIXED}

_ML_WINDOW_SIZE = 50
_ML_STRIDE = 25
_ML_BIAS_THRESHOLD = 0.3


def _compute_ml_trade_flags(
    n_trades: int,
    window_predictions: list[dict[str, float]],
    window_size: int,
    stride: int,
) -> dict[int, set[str]]:
    """Map ML window predictions to per-trade bias tags.

    Each trade is assigned the averaged predictions of all windows that
    contain it.  Bias classes exceeding ``_ML_BIAS_THRESHOLD`` become tags.
    """
    if n_trades >= window_size:
        window_starts = list(range(0, n_trades - window_size + 1, stride))
    else:
        window_starts = [0]
        window_size = n_trades

    trade_to_windows: dict[int, list[int]] = defaultdict(list)
    for w_idx, start in enumerate(window_starts):
        for t in range(start, min(start + window_size, n_trades)):
            trade_to_windows[t].append(w_idx)

    # Assign uncovered trailing trades to the last window
    last_w = len(window_starts) - 1
    for t in range(n_trades):
        if t not in trade_to_windows:
            trade_to_windows[t].append(last_w)

    flag_map: dict[int, set[str]] = {}
    for t in range(n_trades):
        w_indices = trade_to_windows[t]
        tags: set[str] = set()
        for cls in BIAS_TYPES:
            avg_prob = float(np.mean([window_predictions[w][cls] for w in w_indices]))
            if avg_prob >= _ML_BIAS_THRESHOLD:
                tags.add(cls)
        flag_map[t] = tags

    return flag_map


def compute_feature_stats(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {
            "trade_count": 0,
            "date_range": [None, None],
            "pnl_total": 0.0,
            "pnl_volatility": 0.0,
            "avg_trade_size": 0.0,
        }

    trade_dates = df["timestamp"].dt.date

    return {
        "trade_count": int(len(df)),
        "date_range": [str(trade_dates.min()), str(trade_dates.max())],
        "pnl_total": round(float(df["pnl"].sum()), 4),
        "pnl_volatility": round(float(df["pnl"].std(ddof=0) or 0.0), 4),
        "avg_trade_size": round(float(df["quantity"].mean()), 4),
        "symbol_count": int(df["symbol"].nunique()),
    }


def _bias_reason(bias_name: str, row: pd.Series) -> str:
    if bias_name == "overtrading":
        return "High frequency, burst pattern, or rapid position switching detected."
    if bias_name == "loss_aversion":
        hold = row.get("hold_minutes", 0)
        pnl = row.get("pnl", 0)
        parts = []
        if hold > 0 and pnl < 0:
            parts.append(f"Losing trade held {hold:.0f} min, longer than winning baseline")
        if pnl < 0:
            parts.append(f"Loss of ${abs(pnl):.2f}")
        return "; ".join(parts) if parts else "Loss aversion pattern detected."
    return "Rapid re-entry after loss(es) with increased position size."


def _rationale_for_bias(bias: str, score: float, stats: dict[str, Any]) -> str:
    if bias == "overtrading":
        return (
            f"Avg trades/day={stats['avg_trades_per_day']}, max burst={stats['max_burst_trades']}, "
            f"position switches={stats.get('position_switches', 0)}."
        )
    if bias == "loss_aversion":
        return (
            f"Hold ratio={stats['loser_to_winner_hold_ratio']}, "
            f"avg loss=${stats.get('avg_loss_size', 0):.2f} vs avg win=${stats.get('avg_win_size', 0):.2f}, "
            f"R:R={stats.get('risk_reward_ratio', 0):.2f}."
        )
    return (
        f"Detected {stats['revenge_events']} rapid re-entries + "
        f"{stats.get('streak_events', 0)} streak-based events "
        f"(rate={stats['event_rate']})."
    )


def analyze_biases(df: pd.DataFrame, use_ml: bool = False, analysis_mode: str = MODE_MIXED) -> dict[str, Any]:
    if analysis_mode not in VALID_MODES:
        analysis_mode = MODE_MIXED

    overtrading = detect_overtrading(df)
    loss_aversion = detect_loss_aversion(df)
    revenge_trading = detect_revenge_trading(df)

    detector_output = {
        "overtrading": overtrading,
        "loss_aversion": loss_aversion,
        "revenge_trading": revenge_trading,
    }

    bias_scores: dict[str, dict[str, Any]] = {}
    bias_evidence: dict[str, list[dict[str, Any]]] = {}

    ml_probabilities: dict[str, float] = {}
    window_predictions: list[dict[str, float]] = []
    ml_active = False
    if analysis_mode in (MODE_ML_ONLY, MODE_MIXED):
        ml_model = BiasMLClassifier()
        if ml_model.is_loaded:
            try:
                # The model was trained on 50-trade windows.
                # Window the user's data the same way, predict each window,
                # and average the probabilities for a robust estimate.
                if len(df) >= _ML_WINDOW_SIZE:
                    windows = extract_windowed_features(df, window_size=_ML_WINDOW_SIZE, stride=_ML_STRIDE)
                else:
                    # Fewer trades than one window — use the whole batch
                    windows = [extract_features(df)]

                for feat in windows:
                    window_predictions.append(ml_model.predict_bias_probabilities(feat))

                labels = [str(c) for c in ml_model.classes]
                ml_probabilities = {
                    label: float(np.mean([p[label] for p in window_predictions]))
                    for label in labels
                }
                ml_active = True
                logger.info(
                    "XGBoost predictions (%d windows): %s",
                    len(windows),
                    {k: round(v, 3) for k, v in ml_probabilities.items()},
                )
            except Exception as exc:
                logger.warning("ML prediction failed, falling back to detectors: %s", exc)
        else:
            logger.info("No trained model found — using detector-only scoring.")

    for bias_name in BIAS_TYPES:
        detector_score = float(detector_output[bias_name]["score"])

        if analysis_mode == MODE_RULES_ONLY or not ml_active:
            final_score = round(detector_score, 2)
        elif analysis_mode == MODE_ML_ONLY:
            ml_score = float(ml_probabilities.get(bias_name, 0.0)) * 100
            final_score = round(ml_score, 2)
        else:  # MODE_MIXED
            ml_score = float(ml_probabilities.get(bias_name, 0.0)) * 100
            final_score = round((0.6 * detector_score) + (0.4 * ml_score), 2)

        rationale = _rationale_for_bias(bias_name, final_score, detector_output[bias_name]["stats"])
        if ml_active and analysis_mode != MODE_RULES_ONLY:
            ml_pct = ml_probabilities.get(bias_name, 0.0) * 100
            rationale += f" ML confidence: {ml_pct:.0f}%."

        bias_scores[bias_name] = {
            "score": final_score,
            "severity": score_to_severity(final_score),
            "rationale": rationale,
        }

        bias_evidence[bias_name] = detector_output[bias_name]["evidence"]

    # ── Per-trade flagging (mode-aware) ──
    rule_flag_map: dict[int, set[str]] = defaultdict(set)
    for bias_name in BIAS_TYPES:
        for idx in detector_output[bias_name]["flags"]:
            rule_flag_map[int(idx)].add(bias_name)

    if analysis_mode == MODE_RULES_ONLY or not ml_active:
        flag_map = rule_flag_map
    elif analysis_mode == MODE_ML_ONLY:
        flag_map = _compute_ml_trade_flags(
            len(df), window_predictions, _ML_WINDOW_SIZE, _ML_STRIDE,
        )
    else:
        # MIXED — intersection: only tag if both rules AND ML agree
        ml_flag_map = _compute_ml_trade_flags(
            len(df), window_predictions, _ML_WINDOW_SIZE, _ML_STRIDE,
        )
        flag_map = {}
        all_indices = set(rule_flag_map.keys()) | set(ml_flag_map.keys())
        for idx in all_indices:
            common = rule_flag_map.get(idx, set()) & ml_flag_map.get(idx, set())
            if common:
                flag_map[idx] = common

    flagged_trades: list[dict[str, Any]] = []
    for idx, tags in sorted(flag_map.items()):
        if idx >= len(df) or not tags:
            continue
        row = df.iloc[idx]
        tag_list = sorted(tags)
        reason = "; ".join([_bias_reason(tag, row) for tag in tag_list])

        timestamp = row["timestamp"]
        if isinstance(timestamp, datetime):
            normalized_timestamp = timestamp
        else:
            normalized_timestamp = pd.to_datetime(timestamp, utc=True).to_pydatetime()

        flagged_trades.append(
            {
                "trade_index": idx,
                "timestamp": normalized_timestamp,
                "symbol": str(row["symbol"]),
                "pnl": float(row["pnl"]),
                "tags": tag_list,
                "reason": reason,
            }
        )

    feature_stats = compute_feature_stats(df)
    feature_stats.update(
        {
            "avg_trades_per_day": overtrading["stats"]["avg_trades_per_day"],
            "max_burst_trades": overtrading["stats"]["max_burst_trades"],
            "position_switches": overtrading["stats"].get("position_switches", 0),
            "loser_to_winner_hold_ratio": loss_aversion["stats"]["loser_to_winner_hold_ratio"],
            "avg_loss_size": loss_aversion["stats"].get("avg_loss_size", 0),
            "avg_win_size": loss_aversion["stats"].get("avg_win_size", 0),
            "loss_to_win_ratio": loss_aversion["stats"].get("loss_to_win_ratio", 0),
            "risk_reward_ratio": loss_aversion["stats"].get("risk_reward_ratio", 0),
            "revenge_event_rate": revenge_trading["stats"]["event_rate"],
            "streak_events": revenge_trading["stats"].get("streak_events", 0),
            "ml_active": ml_active,
            "ml_probabilities": {k: round(v, 4) for k, v in ml_probabilities.items()} if ml_active else {},
            "analysis_mode": analysis_mode,
        }
    )

    # ── Calm classification ──
    # Calm score = inverse of the worst bias.  When ML is active, also
    # incorporate the model's "calm" probability for a richer signal.
    max_bias_score = max(bs["score"] for bs in bias_scores.values()) if bias_scores else 0.0
    rule_calm = round(max(0.0, 100.0 - max_bias_score), 2)

    if ml_active and analysis_mode != MODE_RULES_ONLY:
        ml_calm = float(ml_probabilities.get("calm", 0.0)) * 100
        if analysis_mode == MODE_ML_ONLY:
            calm_score = round(ml_calm, 2)
        else:  # mixed
            calm_score = round(0.6 * rule_calm + 0.4 * ml_calm, 2)
        calm_rationale = f"Composite discipline score. ML calm confidence: {ml_calm:.0f}%."
    else:
        calm_score = rule_calm
        calm_rationale = "Composite discipline score based on absence of bias signals."

    bias_scores["calm"] = {
        "score": calm_score,
        "severity": "low" if calm_score >= 60 else ("medium" if calm_score >= 30 else "high"),
        "rationale": calm_rationale,
    }
    bias_evidence["calm"] = []
    if ml_active and analysis_mode != MODE_RULES_ONLY:
        calm_prob = ml_probabilities.get("calm", 0.0)
        bias_evidence["calm"].append(
            {
                "metric": "ml_confidence",
                "value": round(calm_prob * 100, 1),
                "note": f"XGBoost calm confidence: {calm_prob*100:.1f}%",
            }
        )

    if ml_active and analysis_mode != MODE_RULES_ONLY:
        for bias_name in BIAS_TYPES:
            prob = ml_probabilities.get(bias_name, 0.0)
            bias_evidence[bias_name].append(
                {
                    "metric": "ml_confidence",
                    "value": round(prob * 100, 1),
                    "note": f"XGBoost model confidence: {prob*100:.1f}%",
                }
            )

    return {
        "bias_scores": bias_scores,
        "flagged_trades": flagged_trades,
        "bias_evidence": bias_evidence,
        "feature_stats": feature_stats,
    }
