"""Pure availability/coverage review for existing prospective Shadow reports.

This is caller-supplied normalized research data, NOT original ZIP authentication,
provider verification, strategy selection, a backtest or a paper execution.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from crypto_autopilot.research.prospective_shadow_continuity_v0_1 import (
    ContinuityReviewRequired,
    HOUR_MS,
    inspect_shadow_batch_continuity,
)

# Paths are preregistered existing collector output fields, not new indicators.
# "NONE", False and numerical zero are observable values, not missing values.
_FEATURES: tuple[tuple[str, str], ...] = (
    ("technical", "ema20"),
    ("technical", "ema50"),
    ("technical", "atr14"),
    ("technical", "volume_ratio"),
    ("technical", "macd_histogram"),
    ("structure", "rolling_previous_high"),
    ("structure", "rolling_previous_low"),
    ("structure", "market_structure_state"),
    ("patterns", "liquidity_event"),
    ("patterns", "fvg_bias"),
    ("patterns", "order_block_bias"),
    ("patterns", "macd_divergence"),
    ("market_event_radar", "relative_volume"),
    ("market_event_radar", "oi_change_pct"),
    ("market_event_radar", "liquidation_imbalance"),
)


def _time(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _attested_snapshot(
    row: Mapping[str, object],
    family: str,
    candle_start: int,
    capture: int,
) -> bool:
    snapshot = row[family]
    if not isinstance(snapshot, Mapping):
        raise ContinuityReviewRequired("FEATURE_FAMILY_INVALID")
    available = _time(snapshot.get("available_at_ms"))
    if snapshot.get("available_at_ms") is not None and available is None:
        raise ContinuityReviewRequired("FEATURE_AVAILABILITY_TIME_INVALID")
    if available is not None and (
        available > capture or available < candle_start + HOUR_MS
    ):
        raise ContinuityReviewRequired("FEATURE_LOOKAHEAD_OR_PREMATURE_AVAILABILITY")

    # The radar uses its source bar's observed time; other snapshots use bar_time_ms.
    reference_key = "observed_at_ms" if family == "market_event_radar" else "bar_time_ms"
    observed = _time(snapshot.get(reference_key))
    if snapshot.get(reference_key) is not None and observed is None:
        raise ContinuityReviewRequired("FEATURE_SOURCE_BAR_TIME_INVALID")
    if observed is not None and observed > capture:
        raise ContinuityReviewRequired("FEATURE_SOURCE_BAR_IN_FUTURE")
    if observed is not None and observed != candle_start:
        raise ContinuityReviewRequired("FEATURE_SOURCE_BAR_MISMATCH")

    # Availability/lineage missing means UNKNOWN, not a usable feature.
    return available is not None and observed == candle_start


def _value(snapshot: Mapping[str, object], family: str, field: str) -> tuple[str, object]:
    source: object = snapshot.get("features") if family == "market_event_radar" else snapshot
    if not isinstance(source, Mapping) or field not in source:
        return "missing", None
    value = source[field]
    if value is None:
        return "explicit_null", None
    if isinstance(value, bool) or isinstance(value, str) and bool(value):
        return "available", value
    if isinstance(value, (float, int)) and not isinstance(value, bool):
        if math.isfinite(float(value)):
            return "available", value
    raise ContinuityReviewRequired("FEATURE_VALUE_INVALID")


def inspect_shadow_feature_coverage(
    reports: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Review causal source/feature coverage with no network or mutable effects.

    Existing normalized-run hash, authority, candle integrity and cross-batch
    checks run first. Original ZIP digests and GitHub identities must be
    authenticated separately: this function *always* reports those as false.
    """

    continuity = inspect_shadow_batch_continuity(reports)
    counts: dict[str, dict[str, int]] = {
        f"{family}.{field}": {
            "available": 0,
            "explicit_null": 0,
            "missing": 0,
            "unattested_time": 0,
        }
        for family, field in _FEATURES
    }
    unique_closed_candles: set[tuple[str, int]] = set()
    market_observations = 0
    attested_snapshot_family_rows = 0
    for report in reports:
        collection = report["collection"]
        capture = collection["capture_timestamp_ms"]
        for row in collection["market_evidence"]:
            market_observations += 1
            candle_start = row["candles_60m"][-1]["time_ms"]
            for candle in row["candles_60m"]:
                unique_closed_candles.add((row["symbol"], candle["time_ms"]))
            attested_by_family = {
                family: _attested_snapshot(row, family, candle_start, capture)
                for family, _ in _FEATURES
            }
            attested_snapshot_family_rows += sum(attested_by_family.values())
            for family, field in _FEATURES:
                record = counts[f"{family}.{field}"]
                if not attested_by_family[family]:
                    record["unattested_time"] += 1
                    continue
                result, _ = _value(row[family], family, field)
                record[result] += 1

    features: dict[str, dict[str, object]] = {}
    for key, count in counts.items():
        known = market_observations - count["unattested_time"]
        features[key] = {
            **count,
            "observations": market_observations,
            "point_in_time_coverage_fraction": (
                count["available"] / market_observations
                if count["unattested_time"] == 0 and count["missing"] == 0
                else None
            ),
            "attested_snapshots": known,
            "complete_coverage_proven": (
                count["available"] == market_observations and market_observations > 0
            ),
        }

    return {
        "schema": "qookey-shadow-feature-coverage-v0.1",
        "status": (
            "REVIEW_REQUIRED" if continuity["status"] == "REVIEW_REQUIRED"
            else "PARTIAL_RESEARCH_ONLY"
        ),
        "mode": "CALLER_SUPPLIED_REPORTS_PURE_VALIDATION",
        "source_archive_digests_authenticated": False,
        "github_run_metadata_authenticated": False,
        "production_eligibility_proven": False,
        "no_lookahead_verified_for_attested_feature_snapshots": (
            attested_snapshot_family_rows > 0
        ),
        "attested_snapshot_family_rows": attested_snapshot_family_rows,
        "no_lookahead_proven_for_unattested_snapshots": False,
        "observed_report_count": continuity["report_count"],
        "market_snapshot_rows": market_observations,
        "closed_60m_input_rows_including_overlap": market_observations * 240,
        "unique_closed_60m_symbol_time_pairs": len(unique_closed_candles),
        "timeframes": {
            "60M": "PARTIAL_SOURCE_OBSERVATIONS",
            "15M": "NOT_COLLECTED_IN_THIS_REPORT",
            "4H": "NOT_COLLECTED_IN_THIS_REPORT",
        },
        "features": features,
        "costs": {
            "fees_bps": None,
            "slippage_bps": None,
            "funding_bps": None,
            "estimated_net_return": None,
            "status": "UNKNOWN_NOT_MEASURED",
        },
        "temporal_continuity": {
            "status": continuity["status"],
            "observed_gap_count": continuity["observed_gap_count"],
            "maximum_source_lag_minutes": continuity["maximum_source_lag_minutes"],
            "full_schedule_coverage_proven": False,
        },
        "authority": {
            "research_only": True,
            "candidate_reranking": False,
            "strategy_qualification": False,
            "model_promotion": False,
            "paper_submission": False,
            "holdout_access": False,
            "source_switch": False,
            "live_trading": False,
        },
    }
