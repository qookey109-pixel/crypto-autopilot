"""Pionex Validation Materialization V0.2 weekly construction contract.

V0.1 remains frozen. V0.2 does not teach the shared Pionex client that ``1W``
means ``1D``. Instead, a V0.2 materialization run reuses the exact native
Pionex ``1D`` partition for a symbol and deterministically constructs logical
Monday-UTC ``1W`` candles from complete seven-day groups.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ..historical import INTERVAL_ALIGNMENT_OFFSET_MS, INTERVAL_MS, audit_candles
from ..models import Candle
from .pionex_validation_materialization_v0_1 import (
    PartitionResult,
    ValidationMaterializationRejected,
    iso_utc,
    validate_config as validate_v0_1_config,
)

DAY_MS = INTERVAL_MS["1D"]
WEEK_MS = INTERVAL_MS["1W"]
WEEK_OFFSET_MS = INTERVAL_ALIGNMENT_OFFSET_MS["1W"]
EXPECTED_OVERLAY_SCHEMA = "pionex-validation-materialization-overlay-v0.2"
EXPECTED_OVERLAY_VERSION = "0.2.0"
EXPECTED_BASE_CONFIG_SHA256 = "83972be4bd6bd04d264a1f136283c5b95cb5e200c86cf22be4f02664d0035cbc"


@dataclass(frozen=True, slots=True)
class WeeklyAggregationResult:
    candles: tuple[Candle, ...]
    source_rows_total: int
    source_rows_used: int
    dropped_leading_rows: int
    dropped_trailing_rows: int

    def receipt_fields(self) -> dict[str, object]:
        return {
            "logical_interval": "1W",
            "physical_provider_interval": "1D",
            "weekly_alignment": "MONDAY_00_00_UTC",
            "source_rows_per_complete_week": 7,
            "source_rows_total": self.source_rows_total,
            "source_rows_used": self.source_rows_used,
            "dropped_leading_incomplete_week_rows": self.dropped_leading_rows,
            "dropped_trailing_incomplete_week_rows": self.dropped_trailing_rows,
            "weekly_rows": len(self.candles),
            "first_week_utc": iso_utc(self.candles[0].time_ms) if self.candles else None,
            "last_week_utc": iso_utc(self.candles[-1].time_ms) if self.candles else None,
            "provider_splicing_performed": False,
            "silent_interpolation_performed": False,
            "cross_provider_fallback_performed": False,
        }


@dataclass(frozen=True, slots=True)
class WeeklyPartitionResult:
    symbol: str
    coverage_status: str
    candles: tuple[Candle, ...]
    source_daily_result: PartitionResult
    aggregation: WeeklyAggregationResult

    @property
    def interval(self) -> str:
        return "1W"

    @property
    def requests(self) -> int:
        """No additional provider requests are charged to the logical 1W rowset."""
        return 0

    def receipt_fields(self) -> dict[str, object]:
        fields = self.aggregation.receipt_fields()
        fields.update(
            {
                "symbol": self.symbol,
                "interval": "1W",
                "coverage_status": self.coverage_status,
                "rows": len(self.candles),
                "first_time_ms": self.candles[0].time_ms if self.candles else None,
                "last_time_ms": self.candles[-1].time_ms if self.candles else None,
                "first_utc": iso_utc(self.candles[0].time_ms) if self.candles else None,
                "last_utc": iso_utc(self.candles[-1].time_ms) if self.candles else None,
                "requests": 0,
                "physical_provider_requests_reused": self.source_daily_result.requests,
                "physical_requests_reused_from_source_partition": True,
                "provider_error_type": self.source_daily_result.provider_error_type,
                "provider_http_status": self.source_daily_result.provider_http_status,
                "complete_provider_history_claimed": False,
            }
        )
        return fields


def validate_overlay(overlay: Mapping[str, Any]) -> None:
    if overlay.get("schema") != EXPECTED_OVERLAY_SCHEMA or overlay.get("version") != EXPECTED_OVERLAY_VERSION:
        raise ValidationMaterializationRejected("unexpected V0.2 overlay version")
    if overlay.get("status") != "IMPLEMENTED_REVIEW_REQUIRED_BEFORE_EXECUTION":
        raise ValidationMaterializationRejected("V0.2 execution authority changed")
    base = overlay.get("base_config")
    if not isinstance(base, Mapping):
        raise ValidationMaterializationRejected("V0.2 base config binding missing")
    if base.get("path") != "config/pionex_validation_dataset_v0_1.json":
        raise ValidationMaterializationRejected("V0.2 base config path changed")
    if base.get("sha256") != EXPECTED_BASE_CONFIG_SHA256 or base.get("frozen") is not True:
        raise ValidationMaterializationRejected("V0.2 frozen V0.1 binding changed")
    if overlay.get("provider") != "pionex_public_futures":
        raise ValidationMaterializationRejected("V0.2 provider changed")
    storage = overlay.get("storage")
    if not isinstance(storage, Mapping) or storage.get("namespace") != "market-data/pionex/validation-dataset-v0.2":
        raise ValidationMaterializationRejected("V0.2 namespace changed")
    expected_weekly = {
        "logical_interval": "1W",
        "physical_provider_interval": "1D",
        "alignment": "MONDAY_00_00_UTC",
        "source_rows_per_complete_week": 7,
        "open": "FIRST_DAILY_OPEN",
        "high": "MAX_DAILY_HIGH",
        "low": "MIN_DAILY_LOW",
        "close": "LAST_DAILY_CLOSE",
        "volume": "SUM_DAILY_VOLUME",
        "incomplete_week_policy": "DROP_AND_DO_NOT_EMIT",
        "duplicate_or_gap_policy": "FAIL_CLOSED",
        "provider_splicing_allowed": False,
        "silent_interpolation_allowed": False,
        "cross_provider_fallback_allowed": False,
        "reuse_materialized_native_1d_partition": True,
        "physical_request_accounting": "CHARGED_TO_NATIVE_1D_SOURCE_PARTITION",
        "lineage": "WEEKLY_RECEIPT_REFERENCES_EXACT_NATIVE_1D_DATA_KEY_AND_SHA256",
    }
    if overlay.get("weekly_materialization") != expected_weekly:
        raise ValidationMaterializationRejected("V0.2 weekly construction contract changed")
    expected_authority = {
        "execution_authorized": False,
        "holdout_access": False,
        "model_promotion": False,
        "source_switch": False,
        "training": False,
        "trade_plan": False,
        "real_money_orders": False,
        "live_trading": False,
    }
    if overlay.get("authority") != expected_authority:
        raise ValidationMaterializationRejected("V0.2 authority widened")


def _week_start(time_ms: int) -> int:
    return WEEK_OFFSET_MS + ((time_ms - WEEK_OFFSET_MS) // WEEK_MS) * WEEK_MS


def aggregate_complete_weeks(source_daily: Sequence[Candle]) -> WeeklyAggregationResult:
    """Construct logical 1W candles from contiguous Pionex-native 1D rows.

    Partial edge weeks are omitted. Any duplicate, gap, out-of-order row,
    invalid OHLCV value, or daily misalignment fails closed before aggregation.
    """
    source = tuple(source_daily)
    if not source:
        raise ValidationMaterializationRejected("weekly aggregation source contains no native 1D rows")
    if not audit_candles(source, "1D").ok:
        raise ValidationMaterializationRejected("weekly aggregation source 1D rows are not contiguous and valid")

    buckets: dict[int, list[Candle]] = {}
    for row in source:
        buckets.setdefault(_week_start(row.time_ms), []).append(row)

    weekly: list[Candle] = []
    used = 0
    dropped_leading = 0
    dropped_trailing = 0
    ordered_starts = sorted(buckets)
    for index, week_start in enumerate(ordered_starts):
        rows = buckets[week_start]
        expected = [week_start + day * DAY_MS for day in range(7)]
        actual = [row.time_ms for row in rows]
        if actual != expected:
            if index == 0:
                dropped_leading += len(rows)
                continue
            if index == len(ordered_starts) - 1:
                dropped_trailing += len(rows)
                continue
            raise ValidationMaterializationRejected("incomplete interior UTC week in native 1D source")
        weekly.append(
            Candle(
                time_ms=week_start,
                open=rows[0].open,
                high=max(row.high for row in rows),
                low=min(row.low for row in rows),
                close=rows[-1].close,
                volume=sum(row.volume for row in rows),
            )
        )
        used += 7

    if not weekly:
        raise ValidationMaterializationRejected("native 1D source contains no complete Monday-Sunday UTC week")
    if not audit_candles(tuple(weekly), "1W").ok:
        raise ValidationMaterializationRejected("constructed logical 1W candles failed continuity audit")
    if used + dropped_leading + dropped_trailing != len(source):
        raise ValidationMaterializationRejected("weekly source accounting mismatch")
    return WeeklyAggregationResult(
        candles=tuple(weekly),
        source_rows_total=len(source),
        source_rows_used=used,
        dropped_leading_rows=dropped_leading,
        dropped_trailing_rows=dropped_trailing,
    )


def weekly_from_native_daily(
    base_config: Mapping[str, Any],
    *,
    symbol: str,
    source_daily_result: PartitionResult,
) -> WeeklyPartitionResult:
    """Create one V0.2 logical weekly partition without another provider read."""
    validate_v0_1_config(base_config)
    if source_daily_result.symbol != symbol or source_daily_result.interval != "1D":
        raise ValidationMaterializationRejected("weekly lineage must use the same symbol's native 1D partition")
    aggregation = aggregate_complete_weeks(source_daily_result.candles)
    coverage = f"AGGREGATED_COMPLETE_WEEKS_FROM_{source_daily_result.coverage_status}"
    return WeeklyPartitionResult(
        symbol=symbol,
        coverage_status=coverage,
        candles=aggregation.candles,
        source_daily_result=source_daily_result,
        aggregation=aggregation,
    )
