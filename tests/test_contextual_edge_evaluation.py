from __future__ import annotations

import pytest

from crypto_autopilot.contextual_edge import evaluate_contextual_breakout_edge
from crypto_autopilot.features.breakout import ACCEPTED, FAILED, PENDING, UP, BreakoutResearchEvent
from crypto_autopilot.features.regime import MarketRegimeSnapshot


def _event(
    event_id: str,
    breakout_available_at_ms: int,
    status: str,
    *,
    resolved_at_ms: int | None = None,
) -> BreakoutResearchEvent:
    return BreakoutResearchEvent(
        event_id=event_id,
        direction=UP,
        breakout_bar_time_ms=breakout_available_at_ms - 1,
        breakout_available_at_ms=breakout_available_at_ms,
        reference_level=100.0,
        breakout_close=101.0,
        status=status,
        resolved_at_ms=resolved_at_ms,
        bars_to_resolution=1 if resolved_at_ms is not None else None,
        resolution_close=102.0 if resolved_at_ms is not None else None,
    )


def _regime(available_at_ms: int, state: str) -> MarketRegimeSnapshot:
    return MarketRegimeSnapshot(
        bar_time_ms=available_at_ms - 1,
        available_at_ms=available_at_ms,
        btc_return=0.01,
        total3_return=0.02,
        eth_btc_return=0.01,
        btc_dominance_delta_pct_points=-0.1,
        alt_breadth_above_ema20=0.6,
        alt_breadth_positive_momentum=0.6,
        alt_expansion_votes=5,
        btc_concentration_votes=0,
        broad_risk_off_votes=0,
        state=state,
    )


def test_context_uses_latest_regime_available_at_breakout_time() -> None:
    events = (
        _event("e1", 15, ACCEPTED, resolved_at_ms=18),
        _event("e2", 25, FAILED, resolved_at_ms=28),
    )
    regimes = (
        _regime(10, "ALT_EXPANSION"),
        _regime(20, "BTC_CONCENTRATION"),
        _regime(30, "BROAD_RISK_OFF"),
    )

    report = evaluate_contextual_breakout_edge(events, regimes, minimum_decisive_events=1)

    assert [item.regime_state for item in report.observations] == [
        "ALT_EXPANSION",
        "BTC_CONCENTRATION",
    ]
    assert [item.regime_available_at_ms for item in report.observations] == [10, 20]
    assert report.matched_events == 2
    assert report.unmatched_events == 0


def test_as_of_masks_resolution_that_was_not_yet_available() -> None:
    event = _event("e1", 15, ACCEPTED, resolved_at_ms=30)

    report = evaluate_contextual_breakout_edge(
        (event,),
        (_regime(10, "ALT_EXPANSION"),),
        as_of_ms=20,
        minimum_decisive_events=1,
    )

    observation = report.observations[0]
    assert observation.status == PENDING
    assert observation.resolved_at_ms is None
    baseline = report.direction_baselines[0]
    assert baseline.pending_events == 1
    assert baseline.decisive_events == 0
    assert baseline.decisive_acceptance_rate is None


def test_slice_uplift_is_relative_to_same_direction_baseline() -> None:
    events = (
        _event("a1", 10, ACCEPTED, resolved_at_ms=12),
        _event("a2", 20, ACCEPTED, resolved_at_ms=22),
        _event("b1", 60, FAILED, resolved_at_ms=62),
        _event("b2", 70, FAILED, resolved_at_ms=72),
    )
    regimes = (
        _regime(5, "ALT_EXPANSION"),
        _regime(50, "BTC_CONCENTRATION"),
    )

    report = evaluate_contextual_breakout_edge(events, regimes, minimum_decisive_events=2)

    baseline = report.direction_baselines[0]
    assert baseline.decisive_events == 4
    assert baseline.decisive_acceptance_rate == pytest.approx(0.5)

    slices = {item.regime_state: item for item in report.slices}
    assert slices["ALT_EXPANSION"].decisive_acceptance_rate == pytest.approx(1.0)
    assert slices["ALT_EXPANSION"].decisive_acceptance_uplift_vs_direction == pytest.approx(0.5)
    assert slices["ALT_EXPANSION"].comparison_eligible is True
    assert slices["BTC_CONCENTRATION"].decisive_acceptance_rate == pytest.approx(0.0)
    assert slices["BTC_CONCENTRATION"].decisive_acceptance_uplift_vs_direction == pytest.approx(-0.5)


def test_small_or_insufficient_slice_never_emits_uplift() -> None:
    events = (
        _event("e1", 10, ACCEPTED, resolved_at_ms=12),
        _event("e2", 20, FAILED, resolved_at_ms=22),
    )
    report = evaluate_contextual_breakout_edge(
        events,
        (_regime(5, "INSUFFICIENT"),),
        minimum_decisive_events=2,
    )

    item = report.slices[0]
    assert item.regime_state == "INSUFFICIENT"
    assert item.comparison_eligible is False
    assert item.decisive_acceptance_uplift_vs_direction is None


def test_event_before_first_regime_is_preserved_as_unmatched_audit_evidence() -> None:
    report = evaluate_contextual_breakout_edge(
        (_event("e1", 5, ACCEPTED, resolved_at_ms=7),),
        (_regime(10, "ALT_EXPANSION"),),
        minimum_decisive_events=1,
    )

    assert report.matched_events == 0
    assert report.unmatched_events == 1
    assert report.observations[0].regime_state is None
    assert report.slices == ()


def test_invalid_resolution_timing_fails_closed() -> None:
    bad = _event("bad", 20, ACCEPTED, resolved_at_ms=19)

    with pytest.raises(ValueError, match="cannot precede"):
        evaluate_contextual_breakout_edge(
            (bad,),
            (_regime(10, "ALT_EXPANSION"),),
            minimum_decisive_events=1,
        )
