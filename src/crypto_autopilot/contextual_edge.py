from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

from crypto_autopilot.features.breakout import (
    ACCEPTED,
    EXPIRED,
    FAILED,
    PENDING,
    BreakoutResearchEvent,
    breakout_events_as_of,
)
from crypto_autopilot.features.regime import MarketRegimeSnapshot

_VALID_BREAKOUT_STATUSES = {PENDING, ACCEPTED, FAILED, EXPIRED}


@dataclass(frozen=True, slots=True)
class ContextualBreakoutObservation:
    """One breakout event joined to context known at breakout time only."""

    event_id: str
    direction: str
    breakout_available_at_ms: int
    status: str
    resolved_at_ms: int | None
    regime_state: str | None
    regime_available_at_ms: int | None

    @property
    def resolved(self) -> bool:
        return self.status != PENDING

    @property
    def decisive(self) -> bool:
        return self.status in {ACCEPTED, FAILED}


@dataclass(frozen=True, slots=True)
class ContextualEdgeSlice:
    """Descriptive outcome rates for one direction/context slice."""

    direction: str
    regime_state: str
    total_events: int
    resolved_events: int
    decisive_events: int
    accepted_events: int
    failed_events: int
    expired_events: int
    pending_events: int
    resolution_rate: float | None
    decisive_acceptance_rate: float | None
    expiry_rate_among_resolved: float | None
    decisive_acceptance_uplift_vs_direction: float | None
    comparison_eligible: bool
    interpretation: str = "DESCRIPTIVE_ONLY"


@dataclass(frozen=True, slots=True)
class DirectionBaseline:
    direction: str
    total_events: int
    resolved_events: int
    decisive_events: int
    accepted_events: int
    failed_events: int
    expired_events: int
    pending_events: int
    resolution_rate: float | None
    decisive_acceptance_rate: float | None
    expiry_rate_among_resolved: float | None


@dataclass(frozen=True, slots=True)
class ContextualEdgeReport:
    """Research-only breakout outcome slices; never a strategy gate."""

    as_of_ms: int | None
    minimum_decisive_events: int
    matched_events: int
    unmatched_events: int
    observations: tuple[ContextualBreakoutObservation, ...]
    direction_baselines: tuple[DirectionBaseline, ...]
    slices: tuple[ContextualEdgeSlice, ...]
    interpretation: str = "DESCRIPTIVE_ONLY"


def _validate_event(event: BreakoutResearchEvent) -> None:
    if event.status not in _VALID_BREAKOUT_STATUSES:
        raise ValueError(f"Unsupported breakout status: {event.status}")
    if event.breakout_available_at_ms < 0:
        raise ValueError("breakout_available_at_ms cannot be negative")
    if event.status == PENDING:
        if event.resolved_at_ms is not None:
            raise ValueError("PENDING breakout event cannot have resolved_at_ms")
    else:
        if event.resolved_at_ms is None:
            raise ValueError("Resolved breakout event must have resolved_at_ms")
        if event.resolved_at_ms < event.breakout_available_at_ms:
            raise ValueError("Breakout resolution cannot precede breakout availability")


def _validate_regimes(regimes: tuple[MarketRegimeSnapshot, ...]) -> None:
    previous_bar = None
    previous_available = None
    for item in regimes:
        if item.available_at_ms < item.bar_time_ms:
            raise ValueError("Regime availability cannot precede its bar time")
        if previous_bar is not None and item.bar_time_ms <= previous_bar:
            raise ValueError("Regime bar times must be strictly increasing")
        if previous_available is not None and item.available_at_ms < previous_available:
            raise ValueError("Regime availability timestamps must be nondecreasing")
        previous_bar = item.bar_time_ms
        previous_available = item.available_at_ms


def _rates(statuses: Sequence[str]) -> tuple[int, int, int, int, int, int, float | None, float | None, float | None]:
    total = len(statuses)
    accepted = sum(status == ACCEPTED for status in statuses)
    failed = sum(status == FAILED for status in statuses)
    expired = sum(status == EXPIRED for status in statuses)
    pending = sum(status == PENDING for status in statuses)
    resolved = accepted + failed + expired
    decisive = accepted + failed
    resolution_rate = resolved / total if total else None
    decisive_acceptance_rate = accepted / decisive if decisive else None
    expiry_rate = expired / resolved if resolved else None
    return (
        total,
        resolved,
        decisive,
        accepted,
        failed,
        expired,
        pending,
        resolution_rate,
        decisive_acceptance_rate,
        expiry_rate,
    )


def evaluate_contextual_breakout_edge(
    events: Sequence[BreakoutResearchEvent],
    regimes: Sequence[MarketRegimeSnapshot],
    *,
    as_of_ms: int | None = None,
    minimum_decisive_events: int = 30,
) -> ContextualEdgeReport:
    """Join breakout outcomes to the latest regime known when each breakout occurred.

    Context is selected using ``regime.available_at_ms <= breakout_available_at_ms``.
    This prevents later regime information from being attached to an earlier
    breakout. If ``as_of_ms`` is supplied, later breakout resolutions are masked
    back to PENDING using the breakout layer's existing causal projection.

    The report is descriptive only. It does not select parameters, modify a
    strategy score, authorize SHORT execution, promote a model or trade.
    """

    if minimum_decisive_events < 1:
        raise ValueError("minimum_decisive_events must be positive")
    if as_of_ms is not None and as_of_ms < 0:
        raise ValueError("as_of_ms cannot be negative")

    source_events = tuple(events)
    for event in source_events:
        _validate_event(event)
    visible_events = (
        breakout_events_as_of(source_events, as_of_ms)
        if as_of_ms is not None
        else source_events
    )

    regime_source = tuple(regimes)
    _validate_regimes(regime_source)
    regime_available_times = tuple(item.available_at_ms for item in regime_source)

    observations: list[ContextualBreakoutObservation] = []
    unmatched = 0
    for event in visible_events:
        regime_index = bisect_right(regime_available_times, event.breakout_available_at_ms) - 1
        if regime_index < 0:
            regime = None
            unmatched += 1
        else:
            regime = regime_source[regime_index]
        observations.append(
            ContextualBreakoutObservation(
                event_id=event.event_id,
                direction=event.direction,
                breakout_available_at_ms=event.breakout_available_at_ms,
                status=event.status,
                resolved_at_ms=event.resolved_at_ms,
                regime_state=regime.state if regime is not None else None,
                regime_available_at_ms=regime.available_at_ms if regime is not None else None,
            )
        )

    by_direction: dict[str, list[str]] = defaultdict(list)
    by_slice: dict[tuple[str, str], list[str]] = defaultdict(list)
    for item in observations:
        by_direction[item.direction].append(item.status)
        if item.regime_state is not None:
            by_slice[(item.direction, item.regime_state)].append(item.status)

    baselines: list[DirectionBaseline] = []
    baseline_acceptance: dict[str, tuple[int, float | None]] = {}
    for direction in sorted(by_direction):
        (
            total,
            resolved,
            decisive,
            accepted,
            failed,
            expired,
            pending,
            resolution_rate,
            acceptance_rate,
            expiry_rate,
        ) = _rates(by_direction[direction])
        baselines.append(
            DirectionBaseline(
                direction=direction,
                total_events=total,
                resolved_events=resolved,
                decisive_events=decisive,
                accepted_events=accepted,
                failed_events=failed,
                expired_events=expired,
                pending_events=pending,
                resolution_rate=resolution_rate,
                decisive_acceptance_rate=acceptance_rate,
                expiry_rate_among_resolved=expiry_rate,
            )
        )
        baseline_acceptance[direction] = (decisive, acceptance_rate)

    slices: list[ContextualEdgeSlice] = []
    for direction, regime_state in sorted(by_slice):
        (
            total,
            resolved,
            decisive,
            accepted,
            failed,
            expired,
            pending,
            resolution_rate,
            acceptance_rate,
            expiry_rate,
        ) = _rates(by_slice[(direction, regime_state)])
        baseline_decisive, baseline_rate = baseline_acceptance[direction]
        eligible = (
            regime_state != "INSUFFICIENT"
            and decisive >= minimum_decisive_events
            and baseline_decisive >= minimum_decisive_events
            and acceptance_rate is not None
            and baseline_rate is not None
        )
        uplift = acceptance_rate - baseline_rate if eligible else None
        slices.append(
            ContextualEdgeSlice(
                direction=direction,
                regime_state=regime_state,
                total_events=total,
                resolved_events=resolved,
                decisive_events=decisive,
                accepted_events=accepted,
                failed_events=failed,
                expired_events=expired,
                pending_events=pending,
                resolution_rate=resolution_rate,
                decisive_acceptance_rate=acceptance_rate,
                expiry_rate_among_resolved=expiry_rate,
                decisive_acceptance_uplift_vs_direction=uplift,
                comparison_eligible=eligible,
            )
        )

    return ContextualEdgeReport(
        as_of_ms=as_of_ms,
        minimum_decisive_events=minimum_decisive_events,
        matched_events=len(observations) - unmatched,
        unmatched_events=unmatched,
        observations=tuple(observations),
        direction_baselines=tuple(baselines),
        slices=tuple(slices),
    )
