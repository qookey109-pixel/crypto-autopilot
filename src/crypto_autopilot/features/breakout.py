from __future__ import annotations

from dataclasses import dataclass, replace

from crypto_autopilot.features.structure import MarketStructureSnapshot
from crypto_autopilot.historical import INTERVAL_MS, audit_candles
from crypto_autopilot.models import Candle
from crypto_autopilot.technical import TechnicalDataError

UP = "UP"
DOWN = "DOWN"
PENDING = "PENDING"
ACCEPTED = "ACCEPTED"
FAILED = "FAILED"
EXPIRED = "EXPIRED"


@dataclass(frozen=True, slots=True)
class BreakoutResearchEvent:
    """Research-only breakout outcome with explicit causal availability."""

    event_id: str
    direction: str
    breakout_bar_time_ms: int
    breakout_available_at_ms: int
    reference_level: float
    breakout_close: float
    status: str
    resolved_at_ms: int | None
    bars_to_resolution: int | None
    resolution_close: float | None

    @property
    def resolved(self) -> bool:
        return self.status != PENDING


def _thresholds(
    direction: str,
    reference_level: float,
    *,
    acceptance_buffer_bps: float,
    failure_reentry_buffer_bps: float,
) -> tuple[float, float]:
    if direction == UP:
        return (
            reference_level * (1.0 + acceptance_buffer_bps / 10_000.0),
            reference_level * (1.0 - failure_reentry_buffer_bps / 10_000.0),
        )
    return (
        reference_level * (1.0 - acceptance_buffer_bps / 10_000.0),
        reference_level * (1.0 + failure_reentry_buffer_bps / 10_000.0),
    )


def _in_acceptance_zone(direction: str, close: float, threshold: float) -> bool:
    return close >= threshold if direction == UP else close <= threshold


def _in_failure_zone(direction: str, close: float, threshold: float) -> bool:
    return close <= threshold if direction == UP else close >= threshold


def _candidate(
    current: MarketStructureSnapshot,
    previous: MarketStructureSnapshot | None,
) -> tuple[str, float] | None:
    previous_up = bool(previous and previous.breakout_above_previous_range)
    previous_down = bool(previous and previous.breakdown_below_previous_range)

    if current.breakout_above_previous_range and not previous_up:
        if current.rolling_previous_high is None:
            raise ValueError("upside breakout is missing its reference high")
        return UP, current.rolling_previous_high
    if current.breakdown_below_previous_range and not previous_down:
        if current.rolling_previous_low is None:
            raise ValueError("downside breakout is missing its reference low")
        return DOWN, current.rolling_previous_low
    return None


def build_breakout_research_events(
    candles: list[Candle] | tuple[Candle, ...],
    structures: list[MarketStructureSnapshot] | tuple[MarketStructureSnapshot, ...],
    interval: str,
    *,
    resolution_bars: int = 3,
    acceptance_closes: int = 2,
    acceptance_buffer_bps: float = 5.0,
    failure_reentry_buffer_bps: float = 5.0,
) -> tuple[BreakoutResearchEvent, ...]:
    """Label range breakouts as accepted, failed, expired, or still pending.

    A candidate is edge-triggered when a closed bar first closes beyond the
    trailing range. Outcomes are determined only by that bar and later closed
    bars. Consumers that evaluate historical events as-of an earlier timestamp
    must use :func:`breakout_events_as_of`, which masks outcomes that were not
    yet causally available.

    The labels are research evidence only. They do not create entries, SHORT
    permission, position sizes, trade plans, or any execution authority.
    """

    if interval not in INTERVAL_MS:
        raise ValueError(f"Unsupported breakout interval: {interval}")
    if resolution_bars < 1:
        raise ValueError("resolution_bars must be positive")
    if acceptance_closes < 1:
        raise ValueError("acceptance_closes must be positive")
    if acceptance_closes > resolution_bars + 1:
        raise ValueError("acceptance_closes cannot exceed candidate plus resolution window")
    if acceptance_buffer_bps < 0 or failure_reentry_buffer_bps < 0:
        raise ValueError("breakout buffers cannot be negative")

    source = tuple(candles)
    structure_source = tuple(structures)
    if len(source) != len(structure_source):
        raise ValueError("structures must align one-to-one with candles")

    audit = audit_candles(source, interval)
    if not audit.ok:
        raise TechnicalDataError(f"Candle audit failed: {audit}")

    step_ms = INTERVAL_MS[interval]
    for candle, structure in zip(source, structure_source, strict=True):
        if candle.time_ms != structure.bar_time_ms:
            raise ValueError("structure bar times must align with candles")
        if structure.available_at_ms != candle.time_ms + step_ms:
            raise ValueError("structure availability must equal the closed-bar availability")

    events: list[BreakoutResearchEvent] = []
    for index, candle in enumerate(source):
        previous = structure_source[index - 1] if index > 0 else None
        candidate = _candidate(structure_source[index], previous)
        if candidate is None:
            continue

        direction, reference_level = candidate
        if reference_level <= 0:
            raise ValueError("breakout reference level must be positive")

        accept_threshold, fail_threshold = _thresholds(
            direction,
            reference_level,
            acceptance_buffer_bps=acceptance_buffer_bps,
            failure_reentry_buffer_bps=failure_reentry_buffer_bps,
        )
        acceptance_streak = int(_in_acceptance_zone(direction, candle.close, accept_threshold))
        status = PENDING
        resolved_at_ms: int | None = None
        bars_to_resolution: int | None = None
        resolution_close: float | None = None

        if acceptance_streak >= acceptance_closes:
            status = ACCEPTED
            resolved_at_ms = structure_source[index].available_at_ms
            bars_to_resolution = 0
            resolution_close = candle.close
        else:
            last_followup = min(len(source) - 1, index + resolution_bars)
            for follow_index in range(index + 1, last_followup + 1):
                follow_close = source[follow_index].close
                if _in_failure_zone(direction, follow_close, fail_threshold):
                    status = FAILED
                    resolved_at_ms = structure_source[follow_index].available_at_ms
                    bars_to_resolution = follow_index - index
                    resolution_close = follow_close
                    break
                if _in_acceptance_zone(direction, follow_close, accept_threshold):
                    acceptance_streak += 1
                else:
                    acceptance_streak = 0
                if acceptance_streak >= acceptance_closes:
                    status = ACCEPTED
                    resolved_at_ms = structure_source[follow_index].available_at_ms
                    bars_to_resolution = follow_index - index
                    resolution_close = follow_close
                    break

            if status == PENDING and index + resolution_bars < len(source):
                expiry_index = index + resolution_bars
                status = EXPIRED
                resolved_at_ms = structure_source[expiry_index].available_at_ms
                bars_to_resolution = resolution_bars
                resolution_close = source[expiry_index].close

        events.append(
            BreakoutResearchEvent(
                event_id=f"{direction}:{candle.time_ms}",
                direction=direction,
                breakout_bar_time_ms=candle.time_ms,
                breakout_available_at_ms=structure_source[index].available_at_ms,
                reference_level=reference_level,
                breakout_close=candle.close,
                status=status,
                resolved_at_ms=resolved_at_ms,
                bars_to_resolution=bars_to_resolution,
                resolution_close=resolution_close,
            )
        )

    return tuple(events)


def breakout_events_as_of(
    events: list[BreakoutResearchEvent] | tuple[BreakoutResearchEvent, ...],
    as_of_ms: int,
) -> tuple[BreakoutResearchEvent, ...]:
    """Return only causally visible event state at ``as_of_ms``.

    A historically resolved event is intentionally projected back to PENDING
    when its resolution had not yet become available at the requested time.
    This prevents outcome labels from leaking backward into model features.
    """

    if as_of_ms < 0:
        raise ValueError("as_of_ms cannot be negative")

    visible: list[BreakoutResearchEvent] = []
    for event in events:
        if event.breakout_available_at_ms > as_of_ms:
            continue
        if event.resolved_at_ms is not None and event.resolved_at_ms > as_of_ms:
            visible.append(
                replace(
                    event,
                    status=PENDING,
                    resolved_at_ms=None,
                    bars_to_resolution=None,
                    resolution_close=None,
                )
            )
        else:
            visible.append(event)
    return tuple(visible)
