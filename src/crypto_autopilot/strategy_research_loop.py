from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import statistics
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .backtest import BacktestResult
from .strategy_edge_validation import StrategyEdgeInput, input_fingerprint


class StrategyResearchLoopError(ValueError):
    """Raised when research evidence violates the frozen V0.1 contract."""


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _require_sha256(value: str, label: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise StrategyResearchLoopError(f"{label} must be lowercase hexadecimal SHA-256")


def _strict_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise StrategyResearchLoopError(f"{label} must be a JSON boolean")
    return value


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise StrategyResearchLoopError(f"{label} must be finite numeric data")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise StrategyResearchLoopError(f"{label} must be finite numeric data") from error
    if not math.isfinite(number):
        raise StrategyResearchLoopError(f"{label} must be finite numeric data")
    return number


@dataclass(frozen=True, slots=True)
class StrategyCandidate:
    candidate_id: str
    family: str
    horizon: str
    parameters: tuple[tuple[str, int | float | str], ...]
    hypothesis_sha256: str

    def payload(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "family": self.family,
            "horizon": self.horizon,
            "parameters": dict(self.parameters),
            "hypothesis_sha256": self.hypothesis_sha256,
        }


@dataclass(frozen=True, slots=True)
class CandidateRegistry:
    candidates: tuple[StrategyCandidate, ...]
    registry_sha256: str

    def report(self) -> dict[str, Any]:
        return {
            "schema": "qookey-strategy-candidate-registry-v0.1",
            "status": "PREPARED_NOT_EXECUTED",
            "candidate_count": len(self.candidates),
            "candidate_ids": [candidate.candidate_id for candidate in self.candidates],
            "registry_sha256": self.registry_sha256,
            "candidates": [candidate.payload() for candidate in self.candidates],
            "authority": _zero_authority(),
        }


@dataclass(frozen=True, slots=True)
class PaperTrade:
    trade_id: str
    symbol: str
    side: str
    entry_time_ms: int
    exit_time_ms: int
    gross_pnl_usd: float
    fees_usd: float
    funding_usd: float
    slippage_cost_usd: float
    net_pnl_usd: float
    initial_risk_usd: float

    @property
    def r_multiple(self) -> float:
        return self.net_pnl_usd / self.initial_risk_usd


@dataclass(frozen=True, slots=True)
class PaperLedger:
    provider: str
    source_role: str
    currency: str
    initial_equity_usd: float
    trades: tuple[PaperTrade, ...]
    complete: bool
    candidate_id: str
    registry_sha256: str
    edge_input_fingerprint: str
    ledger_sha256: str
    provider_data_fetched: bool = False
    r2_accessed: bool = False
    holdout_accessed: bool = False
    trade_plan_authorized: bool = False
    live_trading_authorized: bool = False


@dataclass(frozen=True, slots=True)
class PaperAuditPolicy:
    minimum_trades: int = 30
    minimum_expectancy_r: float = 0.0
    minimum_profit_factor: float = 1.0
    maximum_largest_winner_share: float = 0.35
    maximum_actual_drawdown_fraction: float = 0.50
    monte_carlo_samples: int = 999
    monte_carlo_mean_block_length: float = 5.0
    monte_carlo_ruin_drawdown_fraction: float = 0.50
    maximum_monte_carlo_ruin_probability: float = 0.10
    deterministic_seed: int = 20260828

    def __post_init__(self) -> None:
        if self.minimum_trades < 1:
            raise StrategyResearchLoopError("minimum_trades must be positive")
        if self.minimum_profit_factor < 0 or self.minimum_expectancy_r < -1:
            raise StrategyResearchLoopError("invalid performance thresholds")
        fractions = (
            self.maximum_largest_winner_share,
            self.maximum_actual_drawdown_fraction,
            self.monte_carlo_ruin_drawdown_fraction,
            self.maximum_monte_carlo_ruin_probability,
        )
        if any(not 0 <= value <= 1 for value in fractions):
            raise StrategyResearchLoopError("audit fractions must be within [0, 1]")
        if self.monte_carlo_samples < 99 or self.monte_carlo_mean_block_length <= 0:
            raise StrategyResearchLoopError("invalid Monte Carlo policy")


def _zero_authority() -> dict[str, Any]:
    return {
        "research_evidence_only": True,
        "provider_requests_performed": False,
        "r2_accessed": False,
        "holdout_accessed": False,
        "model_promotion_authority": 0,
        "trade_plan_authorized": False,
        "real_money_order_authorized": False,
        "live_trading_authorized": False,
        "sstate_core_mutated": False,
        "v0_10_production_critical_path_mutated": False,
    }


def _grid(parameter_grid: Mapping[str, Sequence[object]]) -> Iterable[dict[str, object]]:
    names = tuple(sorted(parameter_grid))
    values = tuple(parameter_grid[name] for name in names)
    for combination in itertools.product(*values):
        yield dict(zip(names, combination))


def build_candidate_registry(payload: Mapping[str, Any]) -> CandidateRegistry:
    if payload.get("schema_version") != "strategy_research_loop_v0_1":
        raise StrategyResearchLoopError("unsupported strategy research loop config")
    search = payload.get("candidate_search")
    if not isinstance(search, Mapping):
        raise StrategyResearchLoopError("candidate_search object is required")
    hard_cap = int(search.get("hard_candidate_cap", 0))
    if hard_cap < 1 or hard_cap > 4096:
        raise StrategyResearchLoopError("hard candidate cap must be within [1, 4096]")
    families = search.get("families")
    if not isinstance(families, list) or not families:
        raise StrategyResearchLoopError("candidate families are required")

    candidates: list[StrategyCandidate] = []
    for family in families:
        if not isinstance(family, Mapping):
            raise StrategyResearchLoopError("candidate family must be an object")
        family_id = str(family.get("id", "")).strip()
        horizons = family.get("horizons")
        parameter_grid = family.get("parameter_grid")
        if not family_id or not isinstance(horizons, list) or not horizons:
            raise StrategyResearchLoopError("candidate family id and horizons are required")
        if not isinstance(parameter_grid, Mapping) or not parameter_grid:
            raise StrategyResearchLoopError("candidate parameter_grid is required")
        for key, values in parameter_grid.items():
            if not isinstance(key, str) or not isinstance(values, list) or not values:
                raise StrategyResearchLoopError("every parameter must have a non-empty list")
        for horizon in horizons:
            normalized_horizon = str(horizon).strip().upper()
            if normalized_horizon not in {"INTRADAY", "MULTIDAY", "SWING"}:
                raise StrategyResearchLoopError("unsupported candidate horizon")
            for parameters in _grid(parameter_grid):
                hypothesis = {
                    "family": family_id,
                    "horizon": normalized_horizon,
                    "parameters": parameters,
                }
                digest = _canonical_sha256(hypothesis)
                candidate_id = f"sr-v0-1-{len(candidates) + 1:04d}-{digest[:12]}"
                candidates.append(
                    StrategyCandidate(
                        candidate_id=candidate_id,
                        family=family_id,
                        horizon=normalized_horizon,
                        parameters=tuple(sorted(parameters.items())),
                        hypothesis_sha256=digest,
                    )
                )
                if len(candidates) > hard_cap:
                    raise StrategyResearchLoopError("candidate family exceeds frozen hard cap")
    if len({candidate.candidate_id for candidate in candidates}) != len(candidates):
        raise StrategyResearchLoopError("candidate IDs must be unique")
    expected_count = int(search.get("expected_candidate_count", 0))
    if expected_count < 1 or len(candidates) != expected_count:
        raise StrategyResearchLoopError("candidate count does not match frozen expectation")
    registry_payload = [candidate.payload() for candidate in candidates]
    return CandidateRegistry(tuple(candidates), _canonical_sha256(registry_payload))


def _trade_payload(trade: PaperTrade) -> dict[str, Any]:
    return {
        "trade_id": trade.trade_id,
        "symbol": trade.symbol,
        "side": trade.side,
        "entry_time_ms": trade.entry_time_ms,
        "exit_time_ms": trade.exit_time_ms,
        "gross_pnl_usd": trade.gross_pnl_usd,
        "fees_usd": trade.fees_usd,
        "funding_usd": trade.funding_usd,
        "slippage_cost_usd": trade.slippage_cost_usd,
        "net_pnl_usd": trade.net_pnl_usd,
        "initial_risk_usd": trade.initial_risk_usd,
    }


def _ledger_hash_payload(ledger: PaperLedger) -> dict[str, Any]:
    return {
        "provider": ledger.provider,
        "source_role": ledger.source_role,
        "currency": ledger.currency,
        "initial_equity_usd": ledger.initial_equity_usd,
        "candidate_id": ledger.candidate_id,
        "registry_sha256": ledger.registry_sha256,
        "edge_input_fingerprint": ledger.edge_input_fingerprint,
        "complete": ledger.complete,
        "trades": [_trade_payload(trade) for trade in ledger.trades],
    }


def paper_ledger_from_dict(payload: Mapping[str, Any]) -> PaperLedger:
    if payload.get("schema") != "qookey-paper-performance-ledger-v0.1":
        raise StrategyResearchLoopError("unsupported paper ledger schema")
    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise StrategyResearchLoopError("paper ledger authority object is required")
    try:
        trades = tuple(
            PaperTrade(
                trade_id=str(item["trade_id"]),
                symbol=str(item["symbol"]),
                side=str(item["side"]).upper(),
                entry_time_ms=int(item["entry_time_ms"]),
                exit_time_ms=int(item["exit_time_ms"]),
                gross_pnl_usd=_finite(item["gross_pnl_usd"], "gross_pnl_usd"),
                fees_usd=_finite(item["fees_usd"], "fees_usd"),
                funding_usd=_finite(item["funding_usd"], "funding_usd"),
                slippage_cost_usd=_finite(item["slippage_cost_usd"], "slippage_cost_usd"),
                net_pnl_usd=_finite(item["net_pnl_usd"], "net_pnl_usd"),
                initial_risk_usd=_finite(item["initial_risk_usd"], "initial_risk_usd"),
            )
            for item in payload["trades"]
        )
        ledger = PaperLedger(
            provider=str(payload["provider"]),
            source_role=str(payload["source_role"]),
            currency=str(payload["currency"]).upper(),
            initial_equity_usd=_finite(payload["initial_equity_usd"], "initial_equity_usd"),
            trades=trades,
            complete=_strict_bool(payload["complete"], "complete"),
            candidate_id=str(payload["candidate_id"]),
            registry_sha256=str(payload["registry_sha256"]),
            edge_input_fingerprint=str(payload["edge_input_fingerprint"]),
            ledger_sha256=str(payload["ledger_sha256"]),
            provider_data_fetched=_strict_bool(
                authority.get("provider_data_fetched", False), "authority.provider_data_fetched"
            ),
            r2_accessed=_strict_bool(authority.get("r2_accessed", False), "authority.r2_accessed"),
            holdout_accessed=_strict_bool(
                authority.get("holdout_accessed", False), "authority.holdout_accessed"
            ),
            trade_plan_authorized=_strict_bool(
                authority.get("trade_plan_authorized", False), "authority.trade_plan_authorized"
            ),
            live_trading_authorized=_strict_bool(
                authority.get("live_trading_authorized", False), "authority.live_trading_authorized"
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, StrategyResearchLoopError):
            raise
        raise StrategyResearchLoopError(f"invalid paper ledger: {error}") from error
    _validate_ledger(ledger)
    return ledger


def _validate_ledger(ledger: PaperLedger) -> None:
    if ledger.source_role != "SYNTHETIC_FIXTURE":
        raise StrategyResearchLoopError("V0.1 accepts SYNTHETIC_FIXTURE ledgers only")
    if ledger.currency != "USD" or ledger.initial_equity_usd <= 0:
        raise StrategyResearchLoopError("paper ledger must use positive USD equity")
    if not ledger.provider or not ledger.candidate_id or not ledger.complete:
        raise StrategyResearchLoopError("paper ledger must be complete and identified")
    _require_sha256(ledger.registry_sha256, "registry_sha256")
    _require_sha256(ledger.edge_input_fingerprint, "edge_input_fingerprint")
    _require_sha256(ledger.ledger_sha256, "ledger_sha256")
    authority_flags = (
        ledger.provider_data_fetched,
        ledger.r2_accessed,
        ledger.holdout_accessed,
        ledger.trade_plan_authorized,
        ledger.live_trading_authorized,
    )
    if any(authority_flags):
        raise StrategyResearchLoopError("paper performance audit has zero data/trading authority")
    if len({trade.trade_id for trade in ledger.trades}) != len(ledger.trades):
        raise StrategyResearchLoopError("paper trade IDs must be unique")
    previous_entry = -1
    for trade in ledger.trades:
        if not trade.trade_id.strip() or not trade.symbol.strip() or trade.side not in {"LONG", "SHORT"}:
            raise StrategyResearchLoopError("paper trades must be identified LONG/SHORT records")
        if trade.entry_time_ms < previous_entry or trade.exit_time_ms < trade.entry_time_ms:
            raise StrategyResearchLoopError("paper trades must be ordered and have valid times")
        previous_entry = trade.entry_time_ms
        if trade.initial_risk_usd <= 0 or min(trade.fees_usd, trade.slippage_cost_usd) < 0:
            raise StrategyResearchLoopError("paper risk and explicit costs must be valid")
        # Repository backtests include slippage in fill prices/gross PnL. The
        # explicit slippage amount is retained for audit, never subtracted twice.
        expected_net = trade.gross_pnl_usd - trade.fees_usd - trade.funding_usd
        if not math.isclose(expected_net, trade.net_pnl_usd, abs_tol=1e-6):
            raise StrategyResearchLoopError("paper ledger net PnL accounting does not reconcile")
    if _canonical_sha256(_ledger_hash_payload(ledger)) != ledger.ledger_sha256:
        raise StrategyResearchLoopError("paper ledger SHA-256 mismatch")


def paper_ledger_from_backtest_result(
    result: BacktestResult,
    *,
    provider: str,
    candidate_id: str,
    registry_sha256: str,
    edge_input_fingerprint: str,
) -> dict[str, Any]:
    """Adapt the existing synthetic Repository backtest without creating a broker."""

    trades = [
        {
            "trade_id": trade.plan_id,
            "symbol": trade.symbol,
            "side": "LONG",
            "entry_time_ms": trade.entry_time_ms,
            "exit_time_ms": trade.exit_time_ms,
            "gross_pnl_usd": trade.gross_pnl_usd,
            "fees_usd": trade.fees_usd,
            "funding_usd": trade.funding_usd,
            "slippage_cost_usd": trade.slippage_cost_usd,
            "net_pnl_usd": trade.net_pnl_usd,
            "initial_risk_usd": trade.risk_usd,
        }
        for trade in result.trades
    ]
    base = {
        "provider": provider,
        "source_role": "SYNTHETIC_FIXTURE",
        "currency": "USD",
        "initial_equity_usd": result.initial_equity_usd,
        "candidate_id": candidate_id,
        "registry_sha256": registry_sha256,
        "edge_input_fingerprint": edge_input_fingerprint,
        "complete": True,
        "trades": trades,
    }
    return {
        "schema": "qookey-paper-performance-ledger-v0.1",
        **base,
        "ledger_sha256": _canonical_sha256(base),
        "slippage_accounting": "INCLUDED_IN_FILL_PRICES_AND_GROSS_PNL",
        "authority": {
            "provider_data_fetched": False,
            "r2_accessed": False,
            "holdout_accessed": False,
            "trade_plan_authorized": False,
            "live_trading_authorized": False,
        },
    }


def _maximum_drawdown(equity_curve: Sequence[float]) -> float:
    peak = equity_curve[0]
    maximum = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        if peak > 0:
            maximum = max(maximum, (peak - equity) / peak)
    return maximum


def _stationary_resample(values: Sequence[float], *, mean_block: float, rng: random.Random) -> list[float]:
    restart_probability = 1.0 / mean_block
    current = rng.randrange(len(values))
    sample: list[float] = []
    for index in range(len(values)):
        if index and rng.random() < restart_probability:
            current = rng.randrange(len(values))
        elif index:
            current = (current + 1) % len(values)
        sample.append(values[current])
    return sample


def _percentile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - index) + ordered[upper] * (index - lower)


def _monte_carlo(ledger: PaperLedger, policy: PaperAuditPolicy) -> dict[str, Any]:
    r_values = [trade.r_multiple for trade in ledger.trades]
    if not r_values:
        return {
            "samples": 0,
            "ruin_probability": 1.0,
            "final_equity_p05_usd": ledger.initial_equity_usd,
            "final_equity_median_usd": ledger.initial_equity_usd,
            "maximum_drawdown_p95": 1.0,
        }
    risk_fractions = [trade.initial_risk_usd / ledger.initial_equity_usd for trade in ledger.trades]
    risk_fraction = statistics.median(risk_fractions)
    rng = random.Random(policy.deterministic_seed)
    finals: list[float] = []
    drawdowns: list[float] = []
    ruins = 0
    for _ in range(policy.monte_carlo_samples):
        equity = ledger.initial_equity_usd
        curve = [equity]
        for r_multiple in _stationary_resample(
            r_values, mean_block=policy.monte_carlo_mean_block_length, rng=rng
        ):
            equity = max(0.0, equity * (1.0 + risk_fraction * r_multiple))
            curve.append(equity)
        drawdown = _maximum_drawdown(curve)
        finals.append(equity)
        drawdowns.append(drawdown)
        ruins += drawdown >= policy.monte_carlo_ruin_drawdown_fraction
    return {
        "method": "deterministic_stationary_bootstrap_r_multiple_paths",
        "samples": policy.monte_carlo_samples,
        "mean_block_length": policy.monte_carlo_mean_block_length,
        "median_realized_risk_fraction": risk_fraction,
        "ruin_drawdown_fraction": policy.monte_carlo_ruin_drawdown_fraction,
        "ruin_probability": ruins / policy.monte_carlo_samples,
        "final_equity_p05_usd": _percentile(finals, 0.05),
        "final_equity_median_usd": _percentile(finals, 0.50),
        "maximum_drawdown_p95": _percentile(drawdowns, 0.95),
    }


def audit_paper_performance(
    ledger: PaperLedger, policy: PaperAuditPolicy | None = None
) -> dict[str, Any]:
    _validate_ledger(ledger)
    active = policy or PaperAuditPolicy()
    trades = ledger.trades
    r_values = [trade.r_multiple for trade in trades]
    net_values = [trade.net_pnl_usd for trade in trades]
    wins = [value for value in net_values if value > 0]
    losses = [-value for value in net_values if value < 0]
    expectancy_r = statistics.fmean(r_values) if r_values else 0.0
    profit_factor = math.inf if not losses and wins else (sum(wins) / sum(losses) if losses else 0.0)
    payoff_ratio = (statistics.fmean(wins) / statistics.fmean(losses)) if wins and losses else None
    sharpe_r = None
    sortino_r = None
    if len(r_values) >= 2 and statistics.stdev(r_values) > 0:
        sharpe_r = statistics.fmean(r_values) / statistics.stdev(r_values)
    downside = [min(value, 0.0) for value in r_values]
    if len(downside) >= 2 and statistics.stdev(downside) > 0:
        sortino_r = statistics.fmean(r_values) / statistics.stdev(downside)
    equity_curve = [ledger.initial_equity_usd]
    for value in net_values:
        equity_curve.append(equity_curve[-1] + value)
    actual_drawdown = _maximum_drawdown(equity_curve)
    largest_winner_share = max(wins) / sum(wins) if wins else 1.0
    consecutive = maximum_consecutive = 0
    for value in net_values:
        consecutive = consecutive + 1 if value < 0 else 0
        maximum_consecutive = max(maximum_consecutive, consecutive)
    monte_carlo = _monte_carlo(ledger, active)
    metrics = {
        "trade_count": len(trades),
        "win_rate": len(wins) / len(trades) if trades else 0.0,
        "expectancy_usd": statistics.fmean(net_values) if trades else 0.0,
        "expectancy_r": expectancy_r,
        "payoff_ratio": payoff_ratio,
        "profit_factor": profit_factor,
        "trade_sharpe_r": sharpe_r,
        "trade_sortino_r": sortino_r,
        "actual_maximum_drawdown_fraction": actual_drawdown,
        "maximum_consecutive_losses": maximum_consecutive,
        "largest_winner_share_of_gross_profit": largest_winner_share,
        "average_holding_hours": (
            statistics.fmean((trade.exit_time_ms - trade.entry_time_ms) / 3_600_000 for trade in trades)
            if trades
            else 0.0
        ),
        "intraday_trade_fraction": (
            sum(trade.exit_time_ms - trade.entry_time_ms < 86_400_000 for trade in trades) / len(trades)
            if trades
            else 0.0
        ),
        "total_fees_usd": sum(trade.fees_usd for trade in trades),
        "total_funding_usd": sum(trade.funding_usd for trade in trades),
        "total_slippage_cost_usd": sum(trade.slippage_cost_usd for trade in trades),
        "final_equity_usd": equity_curve[-1],
    }
    reasons: list[str] = []
    if len(trades) < active.minimum_trades:
        state = "INSUFFICIENT_SAMPLE"
        reasons.append("trade_count_below_frozen_minimum")
    else:
        if expectancy_r <= active.minimum_expectancy_r:
            reasons.append("expectancy_r_not_positive")
        if profit_factor < active.minimum_profit_factor:
            reasons.append("profit_factor_below_minimum")
        if largest_winner_share > active.maximum_largest_winner_share:
            reasons.append("winner_concentration_above_maximum")
        if actual_drawdown > active.maximum_actual_drawdown_fraction:
            reasons.append("actual_drawdown_above_maximum")
        if monte_carlo["ruin_probability"] > active.maximum_monte_carlo_ruin_probability:
            reasons.append("monte_carlo_ruin_probability_above_maximum")
        state = "FRAGILE_REVIEW_REQUIRED" if reasons else "ACCEPTABLE_FOR_CONTINUED_PAPER_RESEARCH"
    return {
        "schema": "qookey-paper-performance-audit-v0.1",
        "state": state,
        "reasons": reasons or ["all_frozen_paper_research_gates_pass"],
        "candidate_id": ledger.candidate_id,
        "registry_sha256": ledger.registry_sha256,
        "edge_input_fingerprint": ledger.edge_input_fingerprint,
        "ledger_sha256": ledger.ledger_sha256,
        "provider": ledger.provider,
        "metrics": metrics,
        "monte_carlo": monte_carlo,
        "authority": _zero_authority(),
    }


def compose_research_evidence(
    *,
    registry: CandidateRegistry,
    edge_input: StrategyEdgeInput,
    edge_report: Mapping[str, Any],
    paper_audit: Mapping[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    candidate_ids = tuple(candidate.candidate_id for candidate in registry.candidates)
    if edge_input.candidate_ids != candidate_ids:
        reasons.append("edge_candidate_order_does_not_match_registry")
    if edge_input.trial_registry.registry_sha256 != registry.registry_sha256:
        reasons.append("edge_registry_sha256_mismatch")
    expected_fingerprint = input_fingerprint(edge_input)
    if edge_report.get("input_fingerprint") != expected_fingerprint:
        reasons.append("edge_report_input_fingerprint_mismatch")
    if edge_report.get("provider") != edge_input.provider:
        reasons.append("edge_report_provider_mismatch")
    if edge_report.get("selected_candidate_id") != edge_input.selected_candidate_id:
        reasons.append("edge_report_candidate_mismatch")
    if paper_audit.get("candidate_id") != edge_input.selected_candidate_id:
        reasons.append("paper_audit_candidate_mismatch")
    if paper_audit.get("registry_sha256") != registry.registry_sha256:
        reasons.append("paper_audit_registry_sha256_mismatch")
    if paper_audit.get("edge_input_fingerprint") != expected_fingerprint:
        reasons.append("paper_audit_edge_fingerprint_mismatch")
    if paper_audit.get("provider") != edge_input.provider:
        reasons.append("paper_audit_provider_mismatch")
    if edge_report.get("verdict") != "PASS":
        reasons.append("strategy_edge_verdict_not_pass")

    if reasons:
        state = "REJECT"
    elif paper_audit.get("state") != "ACCEPTABLE_FOR_CONTINUED_PAPER_RESEARCH":
        state = "RESEARCH_REVIEW_REQUIRED"
        reasons.append("paper_performance_not_acceptable_for_continued_research")
    else:
        state = "EVIDENCE_READY_FOR_HUMAN_REVIEW"
        reasons.append("edge_and_paper_evidence_pass_with_matching_lineage")
    return {
        "schema": "qookey-strategy-research-loop-report-v0.1",
        "state": state,
        "reasons": reasons,
        "registry_sha256": registry.registry_sha256,
        "candidate_count": len(registry.candidates),
        "selected_candidate_id": edge_input.selected_candidate_id,
        "edge_input_fingerprint": expected_fingerprint,
        "paper_ledger_sha256": paper_audit.get("ledger_sha256"),
        "authority": _zero_authority(),
        "limitations": [
            "Human-review readiness never promotes a model or authorizes trading.",
            "V0.1 accepts synthetic fixtures only and does not execute candidate returns.",
            "Historical evidence does not prove future profitability.",
        ],
    }


def policy_from_config(payload: Mapping[str, Any]) -> PaperAuditPolicy:
    policy = payload.get("paper_performance_audit")
    if payload.get("schema_version") != "strategy_research_loop_v0_1" or not isinstance(policy, Mapping):
        raise StrategyResearchLoopError("unsupported paper performance policy")
    try:
        return PaperAuditPolicy(
            minimum_trades=int(policy["minimum_trades"]),
            minimum_expectancy_r=float(policy["minimum_expectancy_r"]),
            minimum_profit_factor=float(policy["minimum_profit_factor"]),
            maximum_largest_winner_share=float(policy["maximum_largest_winner_share"]),
            maximum_actual_drawdown_fraction=float(policy["maximum_actual_drawdown_fraction"]),
            monte_carlo_samples=int(policy["monte_carlo_samples"]),
            monte_carlo_mean_block_length=float(policy["monte_carlo_mean_block_length"]),
            monte_carlo_ruin_drawdown_fraction=float(policy["monte_carlo_ruin_drawdown_fraction"]),
            maximum_monte_carlo_ruin_probability=float(policy["maximum_monte_carlo_ruin_probability"]),
            deterministic_seed=int(policy["deterministic_seed"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, StrategyResearchLoopError):
            raise
        raise StrategyResearchLoopError(f"invalid paper audit policy: {error}") from error
