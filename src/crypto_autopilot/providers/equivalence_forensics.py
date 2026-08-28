from __future__ import annotations

import math
from typing import Iterable

from crypto_autopilot.models import Candle


# Descriptive bins frozen before the forensic evidence run. They are NOT Gate
# thresholds and must not be interpreted as source-switch authorization.
FORENSIC_ABS_RETURN_BPS_BINS: tuple[float, ...] = (0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
# Numerical-comparison tolerance only. This is many orders of magnitude below
# any descriptive bin and does not alter return signs or V0.1 Gate grading.
FORENSIC_FLOAT_EPSILON_BPS = 1e-12


def _direction(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    if not 0 <= fraction <= 1:
        raise ValueError("fraction must be between 0 and 1")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _summary(values: list[float]) -> dict[str, float | None]:
    return {
        "median": _percentile(values, 0.50),
        "p95": _percentile(values, 0.95),
        "max": max(values) if values else None,
    }


def _le_descriptive_boundary(value: float, boundary: float) -> bool:
    return value <= boundary + FORENSIC_FLOAT_EPSILON_BPS


def _bucket_label(value: float) -> str:
    previous = 0.0
    for upper in FORENSIC_ABS_RETURN_BPS_BINS:
        if _le_descriptive_boundary(value, upper):
            if previous == 0.0:
                return f"<= {upper:g} bps"
            return f"({previous:g}, {upper:g}] bps"
        previous = upper
    return f"> {FORENSIC_ABS_RETURN_BPS_BINS[-1]:g} bps"


def analyze_direction_mismatches(
    pionex_candles: Iterable[Candle],
    binance_candles: Iterable[Candle],
) -> dict[str, object]:
    """Describe exact-sign close-to-close disagreements without changing V0.1.

    V0.1 deliberately grades raw return sign with no deadband. This helper only
    measures the magnitude and shape of the disagreements already produced by
    that frozen rule. It does not grade, re-grade, or authorize a provider.
    """

    left = tuple(pionex_candles)
    right = tuple(binance_candles)
    if len(left) != len(right):
        raise ValueError("forensics requires equal candle counts")
    if len(left) < 2:
        raise ValueError("forensics requires at least two candles")
    if [item.time_ms for item in left] != [item.time_ms for item in right]:
        raise ValueError("forensics requires identical ordered timestamp sets")

    mismatch_rows: list[dict[str, object]] = []
    matches = 0
    for index in range(1, len(left)):
        left_previous = left[index - 1]
        left_current = left[index]
        right_previous = right[index - 1]
        right_current = right[index]
        if left_previous.close <= 0 or right_previous.close <= 0:
            raise ValueError("close prices must be positive")

        left_delta = left_current.close - left_previous.close
        right_delta = right_current.close - right_previous.close
        left_bps = left_delta / left_previous.close * 10_000.0
        right_bps = right_delta / right_previous.close * 10_000.0
        left_direction = _direction(left_delta)
        right_direction = _direction(right_delta)
        if left_direction == right_direction:
            matches += 1
            continue

        max_abs_bps = max(abs(left_bps), abs(right_bps))
        min_abs_bps = min(abs(left_bps), abs(right_bps))
        mismatch_rows.append(
            {
                "previous_time_ms": left_previous.time_ms,
                "time_ms": left_current.time_ms,
                "pionex_previous_close": left_previous.close,
                "pionex_close": left_current.close,
                "binance_previous_close": right_previous.close,
                "binance_close": right_current.close,
                "pionex_return_bps": left_bps,
                "binance_return_bps": right_bps,
                "pionex_direction": left_direction,
                "binance_direction": right_direction,
                "shape": (
                    "ONE_PROVIDER_FLAT"
                    if left_direction == 0 or right_direction == 0
                    else "OPPOSITE_NONZERO_SIGNS"
                ),
                "max_abs_return_bps": max_abs_bps,
                "min_abs_return_bps": min_abs_bps,
                "descriptive_max_abs_bin": _bucket_label(max_abs_bps),
            }
        )

    comparisons = len(left) - 1
    mismatches = len(mismatch_rows)
    if matches + mismatches != comparisons:
        raise RuntimeError("direction forensic accounting mismatch")

    max_abs_values = [float(row["max_abs_return_bps"]) for row in mismatch_rows]
    min_abs_values = [float(row["min_abs_return_bps"]) for row in mismatch_rows]
    left_abs_values = [abs(float(row["pionex_return_bps"])) for row in mismatch_rows]
    right_abs_values = [abs(float(row["binance_return_bps"])) for row in mismatch_rows]

    bin_counts: dict[str, int] = {}
    for row in mismatch_rows:
        label = str(row["descriptive_max_abs_bin"])
        bin_counts[label] = bin_counts.get(label, 0) + 1

    cumulative_counts = {
        f"both_abs_returns_le_{threshold:g}_bps": sum(
            _le_descriptive_boundary(abs(float(row["pionex_return_bps"])), threshold)
            and _le_descriptive_boundary(abs(float(row["binance_return_bps"])), threshold)
            for row in mismatch_rows
        )
        for threshold in FORENSIC_ABS_RETURN_BPS_BINS
    }

    return {
        "comparison_count": comparisons,
        "direction_match_count": matches,
        "direction_mismatch_count": mismatches,
        "direction_agreement": matches / comparisons,
        "mismatch_fraction": mismatches / comparisons,
        "mismatch_shape_counts": {
            "ONE_PROVIDER_FLAT": sum(row["shape"] == "ONE_PROVIDER_FLAT" for row in mismatch_rows),
            "OPPOSITE_NONZERO_SIGNS": sum(
                row["shape"] == "OPPOSITE_NONZERO_SIGNS" for row in mismatch_rows
            ),
        },
        "predeclared_descriptive_bins_bps": list(FORENSIC_ABS_RETURN_BPS_BINS),
        "floating_comparison_epsilon_bps": FORENSIC_FLOAT_EPSILON_BPS,
        "max_abs_return_bps_bin_counts": bin_counts,
        "both_abs_returns_cumulative_counts": cumulative_counts,
        "mismatch_magnitude_summary_bps": {
            "pionex_abs": _summary(left_abs_values),
            "binance_abs": _summary(right_abs_values),
            "max_of_providers_abs": _summary(max_abs_values),
            "min_of_providers_abs": _summary(min_abs_values),
        },
        "mismatches": mismatch_rows,
        "decision_boundary": {
            "descriptive_only": True,
            "v0_1_regraded": False,
            "new_deadband_applied": False,
            "new_threshold_proposed": False,
            "source_switch_authorized": False,
        },
    }
