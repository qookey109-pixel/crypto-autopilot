from __future__ import annotations

import hashlib
import json
import math
import statistics
from dataclasses import asdict, dataclass, replace
from typing import Iterable, Sequence

from ..models import Candle
from .bitget_macd import (
    THIRTY_MINUTES_MS,
    BitgetMacdResearchConfig,
    BitgetMacdResearchResult,
    aggregate_15m_to_30m,
    default_bitget_macd_candidate_grid,
    result_summary,
    run_bitget_macd_long_30m_research,
)


@dataclass(frozen=True, slots=True)
class BitgetMacdValidationPlan:
    """Pre-registered temporal validation policy for local, authorized data only."""

    development_fraction: float = 0.70
    development_folds: int = 4
    top_k: int = 24
    min_trades_per_development_window: int = 5
    min_30m_bars_per_window: int = 120
    selection_slippage_bps_per_side: float = 2.0
    confirmation_slippage_stress_bps_per_side: tuple[float, ...] = (2.0, 5.0, 10.0)
    confirmation_can_change_parameters: bool = False
    formal_project_holdout_accessed: bool = False

    def __post_init__(self) -> None:
        if not math.isfinite(self.development_fraction) or not 0.5 <= self.development_fraction < 0.9:
            raise ValueError("development_fraction must be within [0.5, 0.9)")
        if self.development_folds < 2:
            raise ValueError("development_folds must be at least 2")
        if self.top_k < 1:
            raise ValueError("top_k must be positive")
        if self.min_trades_per_development_window < 1:
            raise ValueError("min_trades_per_development_window must be positive")
        if self.min_30m_bars_per_window < 50:
            raise ValueError("min_30m_bars_per_window must be at least 50")
        stresses = self.confirmation_slippage_stress_bps_per_side
        if not stresses or tuple(sorted(set(stresses))) != stresses:
            raise ValueError("confirmation slippage stresses must be unique and ascending")
        if not all(math.isfinite(value) and value >= 0 for value in stresses):
            raise ValueError("confirmation slippage stresses must be finite and non-negative")
        if self.selection_slippage_bps_per_side not in stresses:
            raise ValueError("selection slippage must be included in confirmation stresses")
        if self.confirmation_can_change_parameters:
            raise ValueError("confirmation is read-only with respect to parameter selection")
        if self.formal_project_holdout_accessed:
            raise ValueError("formal project holdout access is forbidden for this plan")


@dataclass(frozen=True, slots=True)
class TemporalWindow:
    name: str
    phase: str
    start_time_ms: int
    end_time_ms: int
    bar_count_30m: int

    def __post_init__(self) -> None:
        if self.phase not in {"DEVELOPMENT", "CONFIRMATION"}:
            raise ValueError("invalid temporal window phase")
        if self.start_time_ms >= self.end_time_ms:
            raise ValueError("temporal window must have positive duration")
        if self.bar_count_30m < 1:
            raise ValueError("temporal window must contain bars")


@dataclass(frozen=True, slots=True)
class DevelopmentCandidateSummary:
    config: BitgetMacdResearchConfig
    window_results: tuple[BitgetMacdResearchResult, ...]
    qualified_windows: int
    profitable_windows: int
    worst_return_pct: float
    median_return_pct: float
    median_profit_factor: float
    max_drawdown_pct: float
    total_trades: int


@dataclass(frozen=True, slots=True)
class ConfirmationStressResult:
    config: BitgetMacdResearchConfig
    slippage_bps_per_side: float
    result: BitgetMacdResearchResult


@dataclass(frozen=True, slots=True)
class PreregisteredValidationResult:
    plan_hash: str
    development_windows: tuple[TemporalWindow, ...]
    confirmation_window: TemporalWindow
    candidate_count: int
    selected_development_candidates: tuple[DevelopmentCandidateSummary, ...]
    confirmation_results: tuple[ConfirmationStressResult, ...]
    confirmation_used_for_selection: bool = False
    formal_project_holdout_accessed: bool = False
    paper_only: bool = True


def plan_payload(plan: BitgetMacdValidationPlan = BitgetMacdValidationPlan()) -> dict[str, object]:
    return {
        "schema": "qookey-bitget-macd-preregistered-validation-plan-v0.1",
        "development_fraction": plan.development_fraction,
        "development_folds": plan.development_folds,
        "top_k": plan.top_k,
        "min_trades_per_development_window": plan.min_trades_per_development_window,
        "min_30m_bars_per_window": plan.min_30m_bars_per_window,
        "selection_slippage_bps_per_side": plan.selection_slippage_bps_per_side,
        "confirmation_slippage_stress_bps_per_side": list(
            plan.confirmation_slippage_stress_bps_per_side
        ),
        "confirmation_can_change_parameters": plan.confirmation_can_change_parameters,
        "formal_project_holdout_accessed": plan.formal_project_holdout_accessed,
        "candidate_grid_count": len(default_bitget_macd_candidate_grid()),
        "selection_uses_confirmation": False,
        "data_access": "LOCAL_AUTHORIZED_FILE_ONLY",
    }


def plan_sha256(plan: BitgetMacdValidationPlan = BitgetMacdValidationPlan()) -> str:
    encoded = json.dumps(plan_payload(plan), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_preregistered_windows(
    candles_15m: Sequence[Candle],
    *,
    plan: BitgetMacdValidationPlan = BitgetMacdValidationPlan(),
) -> tuple[tuple[TemporalWindow, ...], TemporalWindow]:
    bars = aggregate_15m_to_30m(candles_15m)
    minimum_total = plan.min_30m_bars_per_window * (plan.development_folds + 1)
    if len(bars) < minimum_total:
        raise ValueError(
            f"need at least {minimum_total} aligned 30m bars for preregistered validation"
        )

    development_count = int(len(bars) * plan.development_fraction)
    confirmation_count = len(bars) - development_count
    if confirmation_count < plan.min_30m_bars_per_window:
        raise ValueError("confirmation window is too small")
    if development_count < plan.development_folds * plan.min_30m_bars_per_window:
        raise ValueError("development windows are too small")

    base = development_count // plan.development_folds
    remainder = development_count % plan.development_folds
    development: list[TemporalWindow] = []
    cursor = 0
    for fold in range(plan.development_folds):
        count = base + (1 if fold < remainder else 0)
        start_index = cursor
        end_index = cursor + count
        development.append(
            TemporalWindow(
                name=f"development-{fold + 1}",
                phase="DEVELOPMENT",
                start_time_ms=bars[start_index].time_ms,
                end_time_ms=bars[end_index].time_ms,
                bar_count_30m=count,
            )
        )
        cursor = end_index

    confirmation = TemporalWindow(
        name="confirmation",
        phase="CONFIRMATION",
        start_time_ms=bars[development_count].time_ms,
        end_time_ms=bars[-1].time_ms + THIRTY_MINUTES_MS,
        bar_count_30m=confirmation_count,
    )
    return tuple(development), confirmation


def _slice_window(candles_15m: Sequence[Candle], window: TemporalWindow) -> tuple[Candle, ...]:
    sliced = tuple(
        candle
        for candle in candles_15m
        if window.start_time_ms <= candle.time_ms < window.end_time_ms
    )
    if not sliced:
        raise ValueError(f"window {window.name} has no source candles")
    return sliced


def _development_summary(
    *,
    config: BitgetMacdResearchConfig,
    window_results: Sequence[BitgetMacdResearchResult],
    min_trades: int,
) -> DevelopmentCandidateSummary:
    results = tuple(window_results)
    returns = [result.metrics.return_pct for result in results]
    profit_factors = [
        result.metrics.profit_factor if result.metrics.profit_factor is not None else 0.0
        for result in results
    ]
    qualified = sum(result.metrics.trade_count >= min_trades for result in results)
    profitable = sum(result.metrics.return_pct > 0 for result in results)
    return DevelopmentCandidateSummary(
        config=config,
        window_results=results,
        qualified_windows=qualified,
        profitable_windows=profitable,
        worst_return_pct=min(returns),
        median_return_pct=float(statistics.median(returns)),
        median_profit_factor=float(statistics.median(profit_factors)),
        max_drawdown_pct=max(result.metrics.max_drawdown_pct for result in results),
        total_trades=sum(result.metrics.trade_count for result in results),
    )


def _selection_key(summary: DevelopmentCandidateSummary) -> tuple[float, ...]:
    return (
        float(summary.qualified_windows),
        float(summary.profitable_windows),
        summary.worst_return_pct,
        summary.median_return_pct,
        summary.median_profit_factor,
        -summary.max_drawdown_pct,
        float(summary.total_trades),
    )


def run_preregistered_validation(
    *,
    candles_15m: Sequence[Candle],
    configs: Iterable[BitgetMacdResearchConfig] | None = None,
    plan: BitgetMacdValidationPlan = BitgetMacdValidationPlan(),
    initial_equity_usd: float = 10_000.0,
) -> PreregisteredValidationResult:
    """Run development selection then read-only confirmation on local candles.

    Confirmation results never feed back into parameter selection. This function
    performs no provider requests, no R2 access, no holdout access, and no live
    trading actions.
    """

    development_windows, confirmation_window = build_preregistered_windows(
        candles_15m, plan=plan
    )
    candidates = tuple(configs) if configs is not None else default_bitget_macd_candidate_grid()
    if not candidates:
        raise ValueError("at least one candidate config is required")

    development_summaries: list[DevelopmentCandidateSummary] = []
    for config in candidates:
        selection_config = replace(
            config, slippage_bps_per_side=plan.selection_slippage_bps_per_side
        )
        fold_results = tuple(
            run_bitget_macd_long_30m_research(
                candles_15m=_slice_window(candles_15m, window),
                config=selection_config,
                initial_equity_usd=initial_equity_usd,
            )
            for window in development_windows
        )
        development_summaries.append(
            _development_summary(
                config=selection_config,
                window_results=fold_results,
                min_trades=plan.min_trades_per_development_window,
            )
        )

    ranked = tuple(sorted(development_summaries, key=_selection_key, reverse=True))
    selected = ranked[: min(plan.top_k, len(ranked))]
    confirmation_candles = _slice_window(candles_15m, confirmation_window)

    confirmation: list[ConfirmationStressResult] = []
    for summary in selected:
        for slippage in plan.confirmation_slippage_stress_bps_per_side:
            stress_config = replace(summary.config, slippage_bps_per_side=slippage)
            result = run_bitget_macd_long_30m_research(
                candles_15m=confirmation_candles,
                config=stress_config,
                initial_equity_usd=initial_equity_usd,
            )
            confirmation.append(
                ConfirmationStressResult(
                    config=stress_config,
                    slippage_bps_per_side=slippage,
                    result=result,
                )
            )

    return PreregisteredValidationResult(
        plan_hash=plan_sha256(plan),
        development_windows=development_windows,
        confirmation_window=confirmation_window,
        candidate_count=len(candidates),
        selected_development_candidates=selected,
        confirmation_results=tuple(confirmation),
    )


def validation_summary(result: PreregisteredValidationResult) -> dict[str, object]:
    selected = []
    for summary in result.selected_development_candidates:
        selected.append(
            {
                "config": asdict(summary.config),
                "qualified_windows": summary.qualified_windows,
                "profitable_windows": summary.profitable_windows,
                "worst_return_pct": summary.worst_return_pct,
                "median_return_pct": summary.median_return_pct,
                "median_profit_factor": summary.median_profit_factor,
                "max_drawdown_pct": summary.max_drawdown_pct,
                "total_trades": summary.total_trades,
                "window_results": [result_summary(item) for item in summary.window_results],
            }
        )

    confirmation = [
        {
            "config": asdict(item.config),
            "slippage_bps_per_side": item.slippage_bps_per_side,
            "result": result_summary(item.result),
        }
        for item in result.confirmation_results
    ]
    return {
        "schema": "qookey-bitget-macd-preregistered-validation-result-v0.1",
        "plan_hash": result.plan_hash,
        "candidate_count": result.candidate_count,
        "development_windows": [asdict(window) for window in result.development_windows],
        "confirmation_window": asdict(result.confirmation_window),
        "selected_development_candidates": selected,
        "confirmation_results": confirmation,
        "confirmation_used_for_selection": result.confirmation_used_for_selection,
        "formal_project_holdout_accessed": result.formal_project_holdout_accessed,
        "paper_only": result.paper_only,
        "provider_requests_performed": 0,
        "r2_reads_performed": False,
        "r2_writes_performed": False,
        "live_trading_authorized": False,
    }
