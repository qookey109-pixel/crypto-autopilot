from __future__ import annotations

from dataclasses import dataclass

from .backtest import LongTradePlan
from .historical_universe import HistoricalUniverseIndex


@dataclass(frozen=True, slots=True)
class HistoricalPlanAdmission:
    plan_id: str
    symbol: str
    signal_time_ms: int
    admitted: bool
    reason: str
    authority_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HistoricalAdmissionBatch:
    admitted_plans: tuple[LongTradePlan, ...]
    rejected_plans: tuple[tuple[str, str], ...]
    decisions: tuple[HistoricalPlanAdmission, ...]


def _authority_refs_for_symbol(
    index: HistoricalUniverseIndex,
    *,
    symbol: str,
    timestamp_ms: int,
    provider: str,
    market_type: str,
    required_intervals: tuple[str, ...],
) -> tuple[str, ...]:
    required = set(required_intervals)
    refs = {
        record.source_ref
        for record in index.records
        if record.provider == provider
        and record.market_type == market_type
        and record.symbol == symbol
        and record.native
        and record.interval in required
        and record.contains(timestamp_ms)
    }
    return tuple(sorted(refs))


def admit_plans_by_historical_universe(
    plans: list[LongTradePlan] | tuple[LongTradePlan, ...],
    *,
    index: HistoricalUniverseIndex,
    provider: str,
    market_type: str = "perp",
    required_intervals: tuple[str, ...] = ("15M", "60M", "4H"),
) -> HistoricalAdmissionBatch:
    """Admit each plan only when its symbol was evidence-eligible at signal time.

    V0.1 is intentionally native-only. External proxy observations cannot make a
    Pionex-native backtest symbol eligible. Each plan is checked at its own
    `signal_time_ms`; the function never substitutes today's/current universe.
    """

    if not provider.strip() or not market_type.strip():
        raise ValueError("provider and market_type are required")
    if not required_intervals or any(not interval.strip() for interval in required_intervals):
        raise ValueError("required_intervals must contain non-empty interval names")

    source = tuple(plans)
    ids = tuple(plan.plan_id for plan in source)
    if len(set(ids)) != len(ids):
        raise ValueError("plan_id values must be unique before historical admission")

    required = tuple(dict.fromkeys(required_intervals))
    admitted: list[LongTradePlan] = []
    rejected: list[tuple[str, str]] = []
    decisions: list[HistoricalPlanAdmission] = []

    for plan in source:
        snapshot = index.snapshot(
            plan.signal_time_ms,
            provider=provider,
            market_type=market_type,
            required_intervals=required,
            native_only=True,
        )
        eligible = plan.symbol in set(snapshot.symbols)
        refs = (
            _authority_refs_for_symbol(
                index,
                symbol=plan.symbol,
                timestamp_ms=plan.signal_time_ms,
                provider=provider,
                market_type=market_type,
                required_intervals=required,
            )
            if eligible
            else ()
        )
        if eligible and not refs:
            raise RuntimeError(
                f"historically eligible symbol lacks admission authority refs: {plan.symbol}"
            )

        if eligible:
            reason = "historical_universe_eligible"
            admitted.append(plan)
        else:
            reason = "symbol_not_historically_eligible_at_signal_time"
            rejected.append((plan.plan_id, reason))

        decisions.append(
            HistoricalPlanAdmission(
                plan_id=plan.plan_id,
                symbol=plan.symbol,
                signal_time_ms=plan.signal_time_ms,
                admitted=eligible,
                reason=reason,
                authority_refs=refs,
            )
        )

    return HistoricalAdmissionBatch(
        admitted_plans=tuple(admitted),
        rejected_plans=tuple(rejected),
        decisions=tuple(decisions),
    )
