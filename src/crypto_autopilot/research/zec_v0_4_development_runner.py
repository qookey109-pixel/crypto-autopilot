from __future__ import annotations

import bisect
import math
import statistics
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from crypto_autopilot.backtest import FundingPoint
from crypto_autopilot.models import Candle
from crypto_autopilot.risk import PositionSizingPolicy, plan_position_size
from crypto_autopilot.technical import TechnicalSnapshot, build_technical_series

from .bitget_macd import (
    THIRTY_MINUTES_MS,
    aggregate_15m_to_30m,
    macd_series,
)
from .zec_v0_3_development_runner import aggregate_15m_to_4h
from .zec_v0_3_selection_policy import ZecV03SelectionPolicy
from .zec_v0_4_development_contract import (
    FROZEN_AXES,
    ZecV04Candidate,
    build_zec_v0_4_candidate_grid,
    validate_zec_v0_4_development_contract,
)
from .zec_v0_4_development_execution_authority import (
    ZecV04DevelopmentExecutionAuthority,
)


FIFTEEN_MINUTES_MS = 15 * 60 * 1000
ATR_REFERENCE_BARS = 180
ATR_PERCENTILE = 0.90
FIXED_STOP_ATR_MULTIPLIER = 2.5
FIXED_RISK_FRACTION = 0.01
FIXED_MAX_LEVERAGE = 3.0


class ZecV04DevelopmentAuthorityError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ZecV04DevelopmentTrade:
    candidate_id: str
    fold_id: str
    signal_time_ms: int
    entry_time_ms: int
    exit_time_ms: int
    raw_entry_price: float
    entry_price: float
    raw_exit_price: float
    exit_price: float
    stop_price: float
    quantity: float
    target_risk_usd: float
    realized_risk_usd: float
    approved_notional_usd: float
    realized_leverage: float
    net_pnl_usd: float
    fees_usd: float
    funding_usd: float
    slippage_cost_usd: float
    exit_reason: str


@dataclass(frozen=True, slots=True)
class ZecV04FoldMetrics:
    trade_count: int
    win_count: int
    loss_count: int
    mean_net_pnl_usd: float
    return_pct: float
    max_drawdown_pct: float
    profit_factor: float | None
    total_fees_usd: float
    total_funding_usd: float
    total_slippage_cost_usd: float
    funding_status: str


@dataclass(frozen=True, slots=True)
class ZecV04CandidateFoldResult:
    candidate_id: str
    fold_id: str
    start_time_ms: int
    end_exclusive_time_ms: int
    initial_equity_usd: float
    final_equity_usd: float
    trades: tuple[ZecV04DevelopmentTrade, ...]
    metrics: ZecV04FoldMetrics
    paper_only: bool = True
    provider_requests_performed: int = 0
    r2_reads_performed: bool = False
    r2_writes_performed: bool = False
    formal_holdout_accessed: bool = False
    live_trading_authorized: bool = False


@dataclass(frozen=True, slots=True)
class ZecV04CandidateSummary:
    candidate_id: str
    profitable_folds: int
    worst_return_pct: float
    median_return_pct: float
    worst_drawdown_pct: float
    total_trades: int


@dataclass(frozen=True, slots=True)
class ZecV04DevelopmentRanking:
    ranked_candidate_ids: tuple[str, ...]
    diagnostic_leader_id: str
    leader_neighbor_ids: tuple[str, ...]
    selection_status: str = "DIAGNOSTIC_RANKING_ONLY"
    champion_frozen: bool = False
    fresh_confirmation_accessed: bool = False
    live_trading_authorized: bool = False


@dataclass(frozen=True, slots=True)
class ZecV04DevelopmentSelection:
    status: str
    selected_candidate_id: str | None
    stable_neighbor_ids: tuple[str, ...]
    ranked_eligible_candidate_ids: tuple[str, ...]
    policy_sha256: str
    selected_worst_return_pct: float | None
    selected_median_return_pct: float | None
    champion_frozen: bool
    fresh_confirmation_accessed: bool = False
    formal_holdout_accessed: bool = False
    live_trading_authorized: bool = False


def _r8(value: float) -> float:
    return round(float(value), 8)


def _crosses(
    macd: Sequence[float | None],
    signal: Sequence[float | None],
) -> tuple[tuple[bool, ...], tuple[bool, ...]]:
    up = [False] * len(macd)
    down = [False] * len(macd)
    for index in range(1, len(macd)):
        previous = (macd[index - 1], signal[index - 1])
        current = (macd[index], signal[index])
        if None in previous or None in current:
            continue
        previous_macd, previous_signal = previous
        current_macd, current_signal = current
        assert previous_macd is not None and previous_signal is not None
        assert current_macd is not None and current_signal is not None
        up[index] = previous_macd <= previous_signal and current_macd > current_signal
        down[index] = previous_macd >= previous_signal and current_macd < current_signal
    return tuple(up), tuple(down)


def _parse_macd(candidate: ZecV04Candidate) -> tuple[int, int, int]:
    try:
        fast, slow, signal = (int(value) for value in candidate.macd.split("/"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid MACD variant: {candidate.macd}") from exc
    if not 1 <= fast < slow or signal < 1:
        raise ValueError(f"invalid MACD variant: {candidate.macd}")
    return fast, slow, signal


def _context_ready(snapshot: TechnicalSnapshot) -> bool:
    return all(
        value is not None
        for value in (
            snapshot.ema20,
            snapshot.ema50,
            snapshot.ema200,
            snapshot.ema20_slope_atr,
            snapshot.atr14,
            snapshot.atr14_fraction,
            snapshot.bollinger_upper,
            snapshot.bollinger_lower,
            snapshot.rsi14,
            snapshot.macd_histogram,
        )
    )


def _activation_eligible(
    candidate: ZecV04Candidate,
    snapshot: TechnicalSnapshot,
) -> bool:
    if not _context_ready(snapshot):
        return False
    assert snapshot.ema20 is not None
    assert snapshot.ema50 is not None
    assert snapshot.ema200 is not None
    assert snapshot.ema20_slope_atr is not None
    assert snapshot.rsi14 is not None
    assert snapshot.macd_histogram is not None

    baseline = (
        snapshot.close > snapshot.ema200
        and snapshot.ema20 > snapshot.ema50
        and snapshot.ema20_slope_atr > 0.0
    )
    if candidate.activation_regime == "TREND_STRICT_BASELINE":
        return baseline

    stacked = baseline and snapshot.ema50 > snapshot.ema200
    if candidate.activation_regime == "TREND_STACKED":
        return stacked
    if candidate.activation_regime == "TREND_STACKED_MOMENTUM":
        return stacked and snapshot.rsi14 > 50.0 and snapshot.macd_histogram > 0.0
    raise ValueError(f"unsupported activation regime: {candidate.activation_regime}")


def _nearest_rank_percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    ordered = sorted(float(value) for value in values)
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def _volatility_eligible(
    *,
    context_index: int,
    contexts: Sequence[TechnicalSnapshot],
) -> bool:
    if context_index < ATR_REFERENCE_BARS:
        return False
    current = contexts[context_index].atr14_fraction
    prior = [
        item.atr14_fraction
        for item in contexts[context_index - ATR_REFERENCE_BARS : context_index]
    ]
    if current is None or any(value is None for value in prior):
        return False
    threshold = _nearest_rank_percentile(
        [float(value) for value in prior if value is not None],
        ATR_PERCENTILE,
    )
    return float(current) <= threshold


def _latest_context_index(
    available_at_ms: Sequence[int],
    decision_time_ms: int,
) -> int | None:
    index = bisect.bisect_right(available_at_ms, decision_time_ms) - 1
    return index if index >= 0 else None


def _fold_metrics(
    initial_equity: float,
    final_equity: float,
    trades: Sequence[ZecV04DevelopmentTrade],
    equity_curve: Sequence[float],
    *,
    funding_available: bool,
) -> ZecV04FoldMetrics:
    wins = [item for item in trades if item.net_pnl_usd > 0.0]
    losses = [item for item in trades if item.net_pnl_usd < 0.0]
    gross_profit = sum(item.net_pnl_usd for item in wins)
    gross_loss = -sum(item.net_pnl_usd for item in losses)
    peak = equity_curve[0]
    max_drawdown = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        if peak > 0.0:
            max_drawdown = max(max_drawdown, (peak - equity) / peak)
    return ZecV04FoldMetrics(
        trade_count=len(trades),
        win_count=len(wins),
        loss_count=len(losses),
        mean_net_pnl_usd=_r8(
            statistics.fmean(item.net_pnl_usd for item in trades) if trades else 0.0
        ),
        return_pct=_r8((final_equity / initial_equity - 1.0) * 100.0),
        max_drawdown_pct=_r8(max_drawdown * 100.0),
        profit_factor=None if gross_loss == 0.0 else _r8(gross_profit / gross_loss),
        total_fees_usd=_r8(sum(item.fees_usd for item in trades)),
        total_funding_usd=_r8(sum(item.funding_usd for item in trades)),
        total_slippage_cost_usd=_r8(sum(item.slippage_cost_usd for item in trades)),
        funding_status=(
            "EXPLICIT_POINT_IN_TIME_DATA_SUPPLIED"
            if funding_available
            else "UNAVAILABLE_NOT_FABRICATED"
        ),
    )


def evaluate_zec_v0_4_candidate_fold(
    *,
    candles_15m: Sequence[Candle],
    candidate: ZecV04Candidate,
    fold_id: str,
    fold_start_time_ms: int,
    fold_end_exclusive_time_ms: int,
    funding_points: Sequence[FundingPoint] | None = None,
    initial_equity_usd: float = 10_000.0,
    taker_fee_bps_per_side: float = 6.0,
    slippage_bps_per_side: float = 5.0,
) -> ZecV04CandidateFoldResult:
    """Evaluate one frozen V0.4 candidate on one development fold."""

    if not fold_id.strip():
        raise ValueError("fold_id is required")
    if fold_start_time_ms < 0 or fold_end_exclusive_time_ms <= fold_start_time_ms:
        raise ValueError("invalid fold window")
    if not math.isfinite(initial_equity_usd) or initial_equity_usd <= 0.0:
        raise ValueError("initial_equity_usd must be positive and finite")
    if min(taker_fee_bps_per_side, slippage_bps_per_side) < 0.0:
        raise ValueError("fee/slippage cannot be negative")

    candles_30m = aggregate_15m_to_30m(candles_15m)
    candles_4h = aggregate_15m_to_4h(candles_15m)
    contexts = build_technical_series(candles_4h, "4H")
    available_at = tuple(item.available_at_ms for item in contexts)

    fast, slow, signal_period = _parse_macd(candidate)
    macd, signal = macd_series(
        candles_30m,
        fast_period=fast,
        slow_period=slow,
        signal_period=signal_period,
    )
    cross_up, cross_down = _crosses(macd, signal)

    fold_indexes = [
        index
        for index, candle in enumerate(candles_30m)
        if fold_start_time_ms <= candle.time_ms < fold_end_exclusive_time_ms
    ]
    if not fold_indexes:
        raise ValueError("fold has no aligned 30m bars")
    fold_last_index = fold_indexes[-1]

    fee_rate = taker_fee_bps_per_side / 10_000.0
    slip_rate = slippage_bps_per_side / 10_000.0
    funding = (
        None
        if funding_points is None
        else tuple(sorted(funding_points, key=lambda item: item.time_ms))
    )
    funding_available = funding is not None

    equity = initial_equity_usd
    equity_curve = [equity]
    trades: list[ZecV04DevelopmentTrade] = []
    index = max(1, fold_indexes[0] - 1)

    while index < fold_last_index:
        signal_bar = candles_30m[index]
        decision_time_ms = signal_bar.time_ms + THIRTY_MINUTES_MS
        entry_index = index + 1
        entry_bar = candles_30m[entry_index]
        if entry_bar.time_ms < fold_start_time_ms:
            index += 1
            continue
        if entry_bar.time_ms >= fold_end_exclusive_time_ms:
            break
        if not cross_up[index]:
            index += 1
            continue

        context_index = _latest_context_index(available_at, decision_time_ms)
        if context_index is None:
            index += 1
            continue
        context = contexts[context_index]
        if not _activation_eligible(candidate, context):
            index += 1
            continue
        if not _volatility_eligible(
            context_index=context_index,
            contexts=contexts,
        ):
            index += 1
            continue

        assert context.atr14 is not None
        assert context.bollinger_upper is not None
        assert context.bollinger_lower is not None
        stop_distance = max(
            FIXED_STOP_ATR_MULTIPLIER * context.atr14,
            0.5 * (context.bollinger_upper - context.bollinger_lower),
        )
        raw_entry = entry_bar.open
        entry_price = raw_entry * (1.0 + slip_rate)
        stop_price = entry_price - stop_distance
        if stop_price <= 0.0 or stop_price >= entry_price:
            index += 1
            continue

        sizing = plan_position_size(
            direction="LONG",
            equity_usd=equity,
            entry_price=entry_price,
            stop_price=stop_price,
            policy=PositionSizingPolicy(
                risk_fraction_per_trade=FIXED_RISK_FRACTION,
                max_leverage=FIXED_MAX_LEVERAGE,
            ),
        )
        if sizing.status != "SIZING_READY" or sizing.approved_notional_usd <= 0.0:
            index += 1
            continue

        quantity = sizing.approved_notional_usd / entry_price
        exit_index = fold_last_index
        raw_exit = candles_30m[fold_last_index].close
        exit_reason = "fold_boundary_close"

        for scan in range(entry_index, fold_last_index + 1):
            candle = candles_30m[scan]
            if candle.open <= stop_price:
                exit_index = scan
                raw_exit = candle.open
                exit_reason = "stop_gap"
                break
            if candle.low <= stop_price:
                exit_index = scan
                raw_exit = stop_price
                exit_reason = "stop"
                break
            if cross_down[scan] and scan + 1 <= fold_last_index:
                exit_index = scan + 1
                raw_exit = candles_30m[exit_index].open
                exit_reason = "macd_death_cross_next_open"
                break

        exit_bar = candles_30m[exit_index]
        exit_price = raw_exit * (1.0 - slip_rate)
        gross_pnl = quantity * (exit_price - entry_price)
        fees = quantity * entry_price * fee_rate + quantity * exit_price * fee_rate
        funding_usd = 0.0
        if funding is not None:
            funding_usd = sum(
                sizing.approved_notional_usd * point.rate
                for point in funding
                if point.symbol == "ZECUSDT"
                and entry_bar.time_ms < point.time_ms <= exit_bar.time_ms
            )
        slippage_cost = quantity * (
            (entry_price - raw_entry) + (raw_exit - exit_price)
        )
        net_pnl = gross_pnl - fees - funding_usd
        trades.append(
            ZecV04DevelopmentTrade(
                candidate_id=candidate.candidate_id,
                fold_id=fold_id,
                signal_time_ms=signal_bar.time_ms,
                entry_time_ms=entry_bar.time_ms,
                exit_time_ms=exit_bar.time_ms,
                raw_entry_price=_r8(raw_entry),
                entry_price=_r8(entry_price),
                raw_exit_price=_r8(raw_exit),
                exit_price=_r8(exit_price),
                stop_price=_r8(stop_price),
                quantity=_r8(quantity),
                target_risk_usd=sizing.target_risk_usd,
                realized_risk_usd=sizing.realized_risk_usd,
                approved_notional_usd=sizing.approved_notional_usd,
                realized_leverage=sizing.realized_leverage,
                net_pnl_usd=_r8(net_pnl),
                fees_usd=_r8(fees),
                funding_usd=_r8(funding_usd),
                slippage_cost_usd=_r8(slippage_cost),
                exit_reason=exit_reason,
            )
        )
        equity = _r8(equity + net_pnl)
        equity_curve.append(equity)
        if equity <= 0.0:
            break
        index = max(exit_index, index + 1)

    metrics = _fold_metrics(
        initial_equity_usd,
        equity,
        trades,
        equity_curve,
        funding_available=funding_available,
    )
    return ZecV04CandidateFoldResult(
        candidate_id=candidate.candidate_id,
        fold_id=fold_id,
        start_time_ms=fold_start_time_ms,
        end_exclusive_time_ms=fold_end_exclusive_time_ms,
        initial_equity_usd=_r8(initial_equity_usd),
        final_equity_usd=_r8(equity),
        trades=tuple(trades),
        metrics=metrics,
    )


def _candidate_neighbors(
    candidates: Sequence[ZecV04Candidate],
    candidate_id: str,
) -> tuple[str, ...]:
    by_id = {item.candidate_id: item for item in candidates}
    current = by_id[candidate_id]
    fields = ("macd", "activation_regime")
    neighbors: list[str] = []
    for other in candidates:
        if other.candidate_id == candidate_id:
            continue
        differing = [
            field
            for field in fields
            if getattr(other, field) != getattr(current, field)
        ]
        if len(differing) != 1:
            continue
        field = differing[0]
        axis_values = FROZEN_AXES[field]
        if abs(
            axis_values.index(getattr(other, field))
            - axis_values.index(getattr(current, field))
        ) == 1:
            neighbors.append(other.candidate_id)
    return tuple(sorted(neighbors))


def rank_zec_v0_4_development_results(
    *,
    candidates: Sequence[ZecV04Candidate],
    fold_ids: Sequence[str],
    results: Sequence[ZecV04CandidateFoldResult],
) -> tuple[tuple[ZecV04CandidateSummary, ...], ZecV04DevelopmentRanking]:
    candidate_ids = {item.candidate_id for item in candidates}
    expected = {
        (candidate_id, fold_id)
        for candidate_id in candidate_ids
        for fold_id in fold_ids
    }
    seen: dict[tuple[str, str], ZecV04CandidateFoldResult] = {}
    for result in results:
        key = (result.candidate_id, result.fold_id)
        if result.candidate_id not in candidate_ids or result.fold_id not in fold_ids:
            raise ValueError("development matrix contains an unknown candidate/fold")
        if key in seen:
            raise ValueError("development matrix contains a duplicate candidate/fold")
        seen[key] = result
    if set(seen) != expected:
        raise ValueError(
            f"development matrix must be complete: expected={len(expected)} observed={len(seen)}"
        )

    summaries: list[ZecV04CandidateSummary] = []
    for candidate in candidates:
        rows = [seen[(candidate.candidate_id, fold_id)] for fold_id in fold_ids]
        returns = [row.metrics.return_pct for row in rows]
        summaries.append(
            ZecV04CandidateSummary(
                candidate_id=candidate.candidate_id,
                profitable_folds=sum(value > 0.0 for value in returns),
                worst_return_pct=min(returns),
                median_return_pct=float(statistics.median(returns)),
                worst_drawdown_pct=max(row.metrics.max_drawdown_pct for row in rows),
                total_trades=sum(row.metrics.trade_count for row in rows),
            )
        )

    ranked = tuple(
        sorted(
            summaries,
            key=lambda row: (
                -row.worst_return_pct,
                -row.median_return_pct,
                row.worst_drawdown_pct,
                -row.total_trades,
                row.candidate_id,
            ),
        )
    )
    leader = ranked[0]
    return ranked, ZecV04DevelopmentRanking(
        ranked_candidate_ids=tuple(item.candidate_id for item in ranked),
        diagnostic_leader_id=leader.candidate_id,
        leader_neighbor_ids=_candidate_neighbors(candidates, leader.candidate_id),
    )


def select_zec_v0_4_development_champion(
    *,
    candidates: Sequence[ZecV04Candidate],
    fold_ids: Sequence[str],
    results: Sequence[ZecV04CandidateFoldResult],
    policy: ZecV03SelectionPolicy,
    policy_sha256: str,
) -> ZecV04DevelopmentSelection:
    if len(policy_sha256) != 64:
        raise ValueError("selection policy SHA-256 is required")
    ranked, _ = rank_zec_v0_4_development_results(
        candidates=candidates,
        fold_ids=fold_ids,
        results=results,
    )
    by_summary = {item.candidate_id: item for item in ranked}
    by_result = {(item.candidate_id, item.fold_id): item for item in results}

    eligible_ids: list[str] = []
    for summary in ranked:
        per_fold = [by_result[(summary.candidate_id, fold_id)] for fold_id in fold_ids]
        enough_trades = all(
            item.metrics.trade_count >= policy.minimum_realized_trades_per_fold
            for item in per_fold
        )
        positive_worst_fold = (
            summary.worst_return_pct
            > policy.minimum_worst_fold_return_pct_exclusive
        )
        if enough_trades and positive_worst_fold:
            eligible_ids.append(summary.candidate_id)

    if not eligible_ids:
        return ZecV04DevelopmentSelection(
            status="NO_ELIGIBLE_DEVELOPMENT_CANDIDATE",
            selected_candidate_id=None,
            stable_neighbor_ids=(),
            ranked_eligible_candidate_ids=(),
            policy_sha256=policy_sha256,
            selected_worst_return_pct=None,
            selected_median_return_pct=None,
            champion_frozen=False,
        )

    selected_id = eligible_ids[0]
    selected = by_summary[selected_id]
    minimum_neighbor_return = (
        selected.worst_return_pct
        * policy.minimum_neighbor_worst_return_retention_fraction
    )
    eligible_set = set(eligible_ids)
    stable_neighbors = tuple(
        sorted(
            neighbor_id
            for neighbor_id in _candidate_neighbors(candidates, selected_id)
            if neighbor_id in eligible_set
            and by_summary[neighbor_id].worst_return_pct >= minimum_neighbor_return
        )
    )
    if len(stable_neighbors) < policy.minimum_stable_neighbors:
        return ZecV04DevelopmentSelection(
            status="ISOLATED_DEVELOPMENT_PEAK_REJECTED",
            selected_candidate_id=None,
            stable_neighbor_ids=stable_neighbors,
            ranked_eligible_candidate_ids=tuple(eligible_ids),
            policy_sha256=policy_sha256,
            selected_worst_return_pct=selected.worst_return_pct,
            selected_median_return_pct=selected.median_return_pct,
            champion_frozen=False,
        )

    return ZecV04DevelopmentSelection(
        status="DEVELOPMENT_CHAMPION_FROZEN",
        selected_candidate_id=selected_id,
        stable_neighbor_ids=stable_neighbors,
        ranked_eligible_candidate_ids=tuple(eligible_ids),
        policy_sha256=policy_sha256,
        selected_worst_return_pct=selected.worst_return_pct,
        selected_median_return_pct=selected.median_return_pct,
        champion_frozen=True,
    )


def run_zec_v0_4_development_matrix(
    *,
    candles_15m: Sequence[Candle],
    contract: Mapping[str, Any],
    selection_policy_payload: Mapping[str, Any],
    execution_authority: ZecV04DevelopmentExecutionAuthority | None = None,
    funding_points: Sequence[FundingPoint] | None = None,
    initial_equity_usd: float = 10_000.0,
) -> tuple[tuple[ZecV04CandidateFoldResult, ...], ZecV04DevelopmentRanking]:
    evidence = validate_zec_v0_4_development_contract(
        contract,
        selection_policy_payload=selection_policy_payload,
    )
    if (
        execution_authority is None
        or execution_authority.effective is not True
        or execution_authority.offline_development_execution_authorized is not True
    ):
        raise ZecV04DevelopmentAuthorityError(
            "offline ZEC V0.4 development execution is not authorized"
        )
    if evidence["fresh_confirmation_access_authorized"] is not False:
        raise ZecV04DevelopmentAuthorityError("fresh confirmation boundary is not closed")

    development = contract["development_window"]
    confirmation = contract["fresh_confirmation_window"]
    start_ms = _iso_to_ms(str(development["start_utc"]))
    end_ms = _iso_to_ms(str(development["end_exclusive_utc"]))
    confirmation_start_ms = _iso_to_ms(str(confirmation["start_utc"]))
    source = tuple(candles_15m)
    if not source:
        raise ValueError("development source candles are required")
    if source[0].time_ms != start_ms:
        raise ValueError("development source must begin at the frozen development start")
    if source[-1].time_ms + FIFTEEN_MINUTES_MS != end_ms:
        raise ValueError(
            "development source must end exactly at the frozen development boundary"
        )
    if any(item.time_ms >= confirmation_start_ms for item in source):
        raise ValueError("fresh confirmation candles are forbidden in development execution")

    candidates = build_zec_v0_4_candidate_grid(contract)
    fold_rows = tuple(development["folds"])
    results: list[ZecV04CandidateFoldResult] = []
    for candidate in candidates:
        for fold in fold_rows:
            results.append(
                evaluate_zec_v0_4_candidate_fold(
                    candles_15m=source,
                    candidate=candidate,
                    fold_id=str(fold["fold_id"]),
                    fold_start_time_ms=_iso_to_ms(str(fold["start_utc"])),
                    fold_end_exclusive_time_ms=_iso_to_ms(
                        str(fold["end_exclusive_utc"])
                    ),
                    funding_points=funding_points,
                    initial_equity_usd=initial_equity_usd,
                    slippage_bps_per_side=5.0,
                )
            )
    _, ranking = rank_zec_v0_4_development_results(
        candidates=candidates,
        fold_ids=tuple(str(fold["fold_id"]) for fold in fold_rows),
        results=results,
    )
    return tuple(results), ranking


def _iso_to_ms(value: str) -> int:
    from datetime import datetime

    return int(
        datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000
    )
