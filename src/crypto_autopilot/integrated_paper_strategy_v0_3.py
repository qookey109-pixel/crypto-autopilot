"""Separated evidence lanes and diagnostics for Integrated Paper V0.3.

V0.3 keeps the V0.2 candidate and execution semantics, but separates an
executable one-position portfolio replay from overlapping independent signal
samples.  The exploration lane cannot be interpreted as portfolio PnL.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import asdict
from statistics import median
from typing import Any, Mapping, Sequence

from .backtest import FundingPoint
from .integrated_paper_strategy_v0_2 import (
    IntegratedCandidate,
    IntegratedPaperTrade,
    _simulate_integrated_plan,
    _validate_candles,
    run_integrated_paper_replay,
)
from .models import Candle


def _r8(value: float) -> float:
    return round(float(value), 8)


def _quantile(values: Sequence[float], quantile: float) -> float | None:
    if not values:
        return None
    if not 0 <= quantile <= 1:
        raise ValueError("quantile must be between zero and one")
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return _r8(ordered[lower])
    weight = position - lower
    return _r8(ordered[lower] * (1.0 - weight) + ordered[upper] * weight)


def _distribution(
    values: Sequence[float],
    *,
    quantiles: Sequence[float],
) -> dict[str, Any]:
    prepared = [float(value) for value in values if math.isfinite(float(value))]
    result: dict[str, Any] = {
        "count": len(prepared),
        "minimum": _r8(min(prepared)) if prepared else None,
        "mean": _r8(sum(prepared) / len(prepared)) if prepared else None,
        "maximum": _r8(max(prepared)) if prepared else None,
    }
    for quantile in quantiles:
        result[f"p{round(float(quantile) * 100):02d}"] = _quantile(prepared, quantile)
    return result


def _planned_reward_risk(
    candidate: IntegratedCandidate,
    trade: Mapping[str, Any],
) -> float | None:
    entry = float(trade["entry_price"])
    stop = float(trade["initial_stop_price"])
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    reward = abs(float(candidate.directional.plan.target_price) - entry)
    return reward / risk


def _trade_groups(
    candidates_by_id: Mapping[str, IntegratedCandidate],
    trades: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[tuple[Mapping[str, Any], float | None]]] = defaultdict(list)
    for trade in trades:
        candidate = candidates_by_id[str(trade["plan_id"])]
        grouped[candidate.stop_source].append(
            (trade, _planned_reward_risk(candidate, trade))
        )
    output: dict[str, dict[str, Any]] = {}
    for source, rows in sorted(grouped.items()):
        reward_risk = [value for _, value in rows if value is not None]
        output[source] = {
            "trade_count": len(rows),
            "win_rate": _r8(
                sum(float(trade["net_pnl_usd"]) > 0 for trade, _ in rows) / len(rows)
            ),
            "average_realized_r": _r8(
                sum(float(trade["r_multiple"]) for trade, _ in rows) / len(rows)
            ),
            "average_planned_reward_risk": _r8(
                sum(reward_risk) / len(reward_risk)
            )
            if reward_risk
            else None,
        }
    return output


def build_reward_risk_diagnostics(
    *,
    candidates: Sequence[IntegratedCandidate],
    replay_result: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Derive predeclared stop, R:R and leverage-rejection diagnostics."""

    diagnostic_config = config["diagnostics"]
    quantiles = tuple(float(value) for value in diagnostic_config["stop_distance_atr_quantiles"])
    thresholds = tuple(
        float(value) for value in diagnostic_config["planned_reward_risk_thresholds"]
    )
    candidates_by_id = {
        candidate.directional.plan.plan_id: candidate for candidate in candidates
    }
    trades = tuple(replay_result.get("paperTrades", ()))
    executed_candidates = [
        candidates_by_id[str(trade["plan_id"])]
        for trade in trades
        if str(trade["plan_id"]) in candidates_by_id
    ]
    reward_risk = [
        value
        for trade in trades
        if str(trade["plan_id"]) in candidates_by_id
        for value in [_planned_reward_risk(candidates_by_id[str(trade["plan_id"])], trade)]
        if value is not None
    ]
    leverage_rejected_ids = {
        str(row[0])
        for row in replay_result.get("rejectedPlans", ())
        if len(row) >= 2 and row[1] == "required_leverage_exceeds_cap"
    }
    leverage_rejected = [
        candidates_by_id[plan_id]
        for plan_id in sorted(leverage_rejected_ids)
        if plan_id in candidates_by_id
    ]
    fixed_target_breakeven = [1.0 / (1.0 + value) for value in reward_risk if value > 0]
    return {
        "stopDistanceAtr": {
            "eligibleCandidates": _distribution(
                [candidate.stop_distance_atr for candidate in candidates if candidate.eligible],
                quantiles=quantiles,
            ),
            "executedTrades": _distribution(
                [candidate.stop_distance_atr for candidate in executed_candidates],
                quantiles=quantiles,
            ),
        },
        "plannedRewardRisk": {
            "distribution": _distribution(reward_risk, quantiles=quantiles),
            "fractionBelow": {
                f"{threshold:.2f}": _r8(
                    sum(value < threshold for value in reward_risk) / len(reward_risk)
                )
                if reward_risk
                else 0.0
                for threshold in thresholds
            },
            "approximateFixedTargetBreakevenWinRate": _distribution(
                fixed_target_breakeven,
                quantiles=quantiles,
            ),
            "interpretation": (
                "Breakeven estimates ignore partial, trailing, fees, slippage and funding; "
                "realized R remains the decision evidence."
            ),
        },
        "byStopSource": _trade_groups(candidates_by_id, trades),
        "leverageRejectedCandidateQuality": {
            "count": len(leverage_rejected),
            "averageTechnicalScore": _r8(
                sum(candidate.directional.score for candidate in leverage_rejected)
                / len(leverage_rejected)
            )
            if leverage_rejected
            else None,
            "stopDistanceAtr": _distribution(
                [candidate.stop_distance_atr for candidate in leverage_rejected],
                quantiles=quantiles,
            ),
            "bySide": dict(
                Counter(candidate.directional.plan.side for candidate in leverage_rejected)
            ),
            "byRegime": dict(Counter(candidate.regime for candidate in leverage_rejected)),
            "byStopSource": dict(
                Counter(candidate.stop_source for candidate in leverage_rejected)
            ),
        },
    }


def run_integrated_portfolio_replay_v0_3(
    *,
    candidates: Sequence[IntegratedCandidate],
    candles_by_symbol: Mapping[str, Sequence[Candle]],
    funding_points: Sequence[FundingPoint] = (),
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Run the single-position portfolio lane and append V0.3 diagnostics."""

    result = run_integrated_paper_replay(
        candidates=candidates,
        candles_by_symbol=candles_by_symbol,
        funding_points=funding_points,
        config=config,
    )
    result["schema"] = "integrated-paper-strategy-portfolio-replay-v0.3"
    result["mode"] = "PORTFOLIO_PAPER_EVIDENCE"
    result["portfolioPerformanceValid"] = True
    result["rewardRiskDiagnostics"] = build_reward_risk_diagnostics(
        candidates=candidates,
        replay_result=result,
        config=config,
    )
    return result


def _independent_sample_metrics(trades: Sequence[IntegratedPaperTrade]) -> dict[str, Any]:
    by_side: dict[str, dict[str, Any]] = {}
    for side in ("LONG", "SHORT"):
        selected = [trade for trade in trades if trade.side == side]
        by_side[side] = {
            "sample_count": len(selected),
            "average_r": _r8(sum(trade.r_multiple for trade in selected) / len(selected))
            if selected
            else 0.0,
        }
    return {
        "sample_count": len(trades),
        "win_rate": _r8(sum(trade.net_pnl_usd > 0 for trade in trades) / len(trades))
        if trades
        else 0.0,
        "average_r": _r8(sum(trade.r_multiple for trade in trades) / len(trades))
        if trades
        else 0.0,
        "median_r": _r8(median(trade.r_multiple for trade in trades)) if trades else 0.0,
        "mean_net_pnl_per_fixed_risk_sample_usd": _r8(
            sum(trade.net_pnl_usd for trade in trades) / len(trades)
        )
        if trades
        else 0.0,
        "by_side": by_side,
        "by_regime": dict(Counter(trade.regime for trade in trades)),
        "by_asset_class": dict(Counter(trade.asset_class for trade in trades)),
        "by_exit_reason": dict(Counter(trade.exit_reason for trade in trades)),
    }


def run_integrated_signal_exploration_v0_3(
    *,
    candidates: Sequence[IntegratedCandidate],
    candles_by_symbol: Mapping[str, Sequence[Candle]],
    funding_points: Sequence[FundingPoint] = (),
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay every eligible signal independently on fixed reference equity."""

    plan_ids = [candidate.directional.plan.plan_id for candidate in candidates]
    if len(plan_ids) != len(set(plan_ids)):
        raise ValueError("integrated candidate plan_id values must be unique")
    reference_equity = float(config["portfolio_risk"]["initial_equity_usd"])
    trades: list[IntegratedPaperTrade] = []
    rejected_candidates: list[list[str]] = []
    rejected_plans: list[list[str]] = []
    for candidate in sorted(
        candidates,
        key=lambda item: (
            item.directional.plan.signal_time_ms,
            item.market.symbol,
            item.directional.plan.side,
            item.directional.plan.plan_id,
        ),
    ):
        plan = candidate.plan
        if plan is None:
            rejected_candidates.append(
                [candidate.directional.plan.plan_id, *candidate.reasons]
            )
            continue
        candles = _validate_candles(candles_by_symbol.get(plan.symbol, ()), plan.symbol)
        trade, reason, _ = _simulate_integrated_plan(
            candidate=candidate,
            candles=candles,
            funding_points=funding_points,
            equity_usd=reference_equity,
            config=config,
        )
        if trade is None:
            rejected_plans.append([plan.plan_id, reason or "no_trade"])
            continue
        trades.append(trade)

    replay_shape = {
        "paperTrades": [asdict(trade) for trade in trades],
        "rejectedPlans": rejected_plans,
    }
    return {
        "schema": "integrated-paper-strategy-independent-signal-exploration-v0.3",
        "status": "PASS",
        "mode": "INDEPENDENT_SIGNAL_EVIDENCE_ONLY",
        "candidateCount": len(candidates),
        "eligibleCandidateCount": sum(candidate.eligible for candidate in candidates),
        "normalizedReferenceEquityUsd": _r8(reference_equity),
        "independentSamples": [asdict(trade) for trade in trades],
        "rejectedCandidates": rejected_candidates,
        "rejectedPlans": rejected_plans,
        "sampleMetrics": _independent_sample_metrics(trades),
        "rewardRiskDiagnostics": build_reward_risk_diagnostics(
            candidates=candidates,
            replay_result=replay_shape,
            config=config,
        ),
        "portfolioPerformanceValid": False,
        "aggregatePnlMayBeReportedAsPortfolioPnl": False,
        "interpretation": {
            "overlapping_samples_allowed": True,
            "each_sample_uses_fixed_reference_equity": True,
            "sample_statistics_are_calibration_evidence_only": True,
            "results_are_not_an_executable_portfolio_equity_curve": True,
        },
        "authority": dict(config["authority"]),
    }


def run_integrated_evidence_lanes_v0_3(
    *,
    candidates: Sequence[IntegratedCandidate],
    candles_by_symbol: Mapping[str, Sequence[Candle]],
    funding_points: Sequence[FundingPoint] = (),
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Return portfolio and independent samples without blending their metrics."""

    return {
        "schema": "integrated-paper-strategy-evidence-lanes-v0.3",
        "status": "PASS",
        "portfolio": run_integrated_portfolio_replay_v0_3(
            candidates=candidates,
            candles_by_symbol=candles_by_symbol,
            funding_points=funding_points,
            config=config,
        ),
        "independentSignalExploration": run_integrated_signal_exploration_v0_3(
            candidates=candidates,
            candles_by_symbol=candles_by_symbol,
            funding_points=funding_points,
            config=config,
        ),
        "metricsMayBeCombined": False,
        "authority": dict(config["authority"]),
    }
