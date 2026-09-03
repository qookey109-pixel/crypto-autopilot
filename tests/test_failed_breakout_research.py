from __future__ import annotations

from crypto_autopilot.features.breakout import (
    ACCEPTED,
    DOWN,
    EXPIRED,
    FAILED,
    PENDING,
    UP,
    breakout_events_as_of,
    build_breakout_research_events,
)
from crypto_autopilot.features.structure import MarketStructureSnapshot
from crypto_autopilot.models import Candle

STEP = 15 * 60 * 1000


def _candle(index: int, close: float) -> Candle:
    return Candle(
        time_ms=index * STEP,
        open=close,
        high=close + 1.0,
        low=max(0.01, close - 1.0),
        close=close,
        volume=100.0,
    )


def _structure(
    index: int,
    *,
    breakout: bool = False,
    breakdown: bool = False,
    previous_high: float = 100.0,
    previous_low: float = 90.0,
) -> MarketStructureSnapshot:
    return MarketStructureSnapshot(
        bar_time_ms=index * STEP,
        available_at_ms=(index + 1) * STEP,
        rolling_previous_high=previous_high,
        rolling_previous_low=previous_low,
        breakout_above_previous_range=breakout,
        breakdown_below_previous_range=breakdown,
        distance_to_previous_high_atr=None,
        distance_to_previous_low_atr=None,
        confirmed_swing_high=False,
        confirmed_swing_low=False,
        most_recent_confirmed_swing_high=None,
        most_recent_confirmed_swing_low=None,
        market_structure_state="RANGE",
    )


def test_upside_breakout_is_accepted_after_two_confirming_closes() -> None:
    candles = tuple(_candle(i, close) for i, close in enumerate((99.0, 101.0, 102.0, 103.0)))
    structures = (
        _structure(0),
        _structure(1, breakout=True),
        _structure(2, breakout=True),
        _structure(3),
    )

    events = build_breakout_research_events(candles, structures, "15M")

    assert len(events) == 1
    event = events[0]
    assert event.direction == UP
    assert event.status == ACCEPTED
    assert event.bars_to_resolution == 1
    assert event.resolved_at_ms == 3 * STEP
    assert event.resolution_close == 102.0


def test_upside_breakout_is_failed_after_reentry() -> None:
    candles = tuple(_candle(i, close) for i, close in enumerate((99.0, 101.0, 99.0, 100.0)))
    structures = (
        _structure(0),
        _structure(1, breakout=True),
        _structure(2),
        _structure(3),
    )

    event = build_breakout_research_events(candles, structures, "15M")[0]

    assert event.direction == UP
    assert event.status == FAILED
    assert event.bars_to_resolution == 1
    assert event.resolution_close == 99.0


def test_downside_breakout_uses_symmetric_research_label() -> None:
    candles = tuple(_candle(i, close) for i, close in enumerate((91.0, 89.0, 88.0, 87.0)))
    structures = (
        _structure(0),
        _structure(1, breakdown=True),
        _structure(2, breakdown=True),
        _structure(3),
    )

    event = build_breakout_research_events(candles, structures, "15M")[0]

    assert event.direction == DOWN
    assert event.status == ACCEPTED
    assert event.bars_to_resolution == 1


def test_neutral_zone_expires_after_full_resolution_window() -> None:
    candles = tuple(
        _candle(i, close)
        for i, close in enumerate((99.0, 100.02, 100.01, 100.00, 100.02, 99.0))
    )
    structures = (
        _structure(0),
        _structure(1, breakout=True),
        _structure(2),
        _structure(3),
        _structure(4),
        _structure(5),
    )

    event = build_breakout_research_events(candles, structures, "15M")[0]

    assert event.status == EXPIRED
    assert event.bars_to_resolution == 3
    assert event.resolution_close == 100.02


def test_as_of_projection_masks_future_resolution() -> None:
    candles = tuple(_candle(i, close) for i, close in enumerate((99.0, 101.0, 102.0, 103.0)))
    structures = (
        _structure(0),
        _structure(1, breakout=True),
        _structure(2, breakout=True),
        _structure(3),
    )
    events = build_breakout_research_events(candles, structures, "15M")

    at_breakout = breakout_events_as_of(events, 2 * STEP)
    after_resolution = breakout_events_as_of(events, 3 * STEP)

    assert len(at_breakout) == 1
    assert at_breakout[0].status == PENDING
    assert at_breakout[0].resolved_at_ms is None
    assert at_breakout[0].resolution_close is None
    assert after_resolution[0].status == ACCEPTED


def test_candidate_near_data_end_remains_pending() -> None:
    candles = tuple(_candle(i, close) for i, close in enumerate((99.0, 101.0)))
    structures = (_structure(0), _structure(1, breakout=True))

    event = build_breakout_research_events(candles, structures, "15M")[0]

    assert event.status == PENDING
    assert event.resolved_at_ms is None
