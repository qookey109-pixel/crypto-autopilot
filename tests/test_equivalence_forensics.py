from __future__ import annotations

import math

import pytest

from crypto_autopilot.equivalence_forensics import (
    FORENSIC_ABS_RETURN_BPS_BINS,
    analyze_direction_mismatches,
)
from crypto_autopilot.models import Candle


def candle(time_ms: int, close: float) -> Candle:
    return Candle(
        time_ms=time_ms,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1.0,
    )


def test_direction_forensics_reports_exact_sign_mismatches_without_regrading() -> None:
    left = (
        candle(0, 100.0),
        candle(1, 100.001),
        candle(2, 100.0),
        candle(3, 100.0),
    )
    right = (
        candle(0, 100.0),
        candle(1, 99.999),
        candle(2, 100.0),
        candle(3, 100.001),
    )

    result = analyze_direction_mismatches(left, right)

    assert result["comparison_count"] == 3
    assert result["direction_match_count"] == 0
    assert result["direction_mismatch_count"] == 3
    assert result["direction_agreement"] == 0.0
    assert result["mismatch_shape_counts"] == {
        "ONE_PROVIDER_FLAT": 1,
        "OPPOSITE_NONZERO_SIGNS": 2,
    }
    assert result["predeclared_descriptive_bins_bps"] == list(FORENSIC_ABS_RETURN_BPS_BINS)
    assert result["decision_boundary"] == {
        "descriptive_only": True,
        "v0_1_regraded": False,
        "new_deadband_applied": False,
        "new_threshold_proposed": False,
        "source_switch_authorized": False,
    }
    rows = result["mismatches"]
    assert len(rows) == 3
    assert all(float(row["max_abs_return_bps"]) < 0.11 for row in rows)
    assert result["both_abs_returns_cumulative_counts"]["both_abs_returns_le_0.1_bps"] == 3


def test_direction_forensics_matches_identical_returns() -> None:
    candles = (
        candle(0, 100.0),
        candle(1, 101.0),
        candle(2, 100.5),
    )
    result = analyze_direction_mismatches(candles, candles)
    assert result["direction_mismatch_count"] == 0
    assert result["direction_agreement"] == 1.0
    summary = result["mismatch_magnitude_summary_bps"]["max_of_providers_abs"]
    assert summary == {"median": None, "p95": None, "max": None}


def test_direction_forensics_requires_exact_ordered_timestamp_sets() -> None:
    left = (candle(0, 100.0), candle(1, 101.0))
    right = (candle(0, 100.0), candle(2, 101.0))
    with pytest.raises(ValueError, match="identical ordered timestamp sets"):
        analyze_direction_mismatches(left, right)


def test_direction_forensics_bps_are_finite() -> None:
    left = (candle(0, 10.0), candle(1, 10.1))
    right = (candle(0, 10.0), candle(1, 9.9))
    result = analyze_direction_mismatches(left, right)
    row = result["mismatches"][0]
    assert math.isfinite(float(row["pionex_return_bps"]))
    assert math.isfinite(float(row["binance_return_bps"]))
