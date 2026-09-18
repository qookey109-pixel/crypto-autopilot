from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from ..models import Candle


EXPECTED_SYMBOL = "ZECUSDT"
EXPECTED_INTERVAL = "15m"
EXPECTED_START_PERIOD = "2022-08"
EXPECTED_END_PERIOD = "2026-07"
EXPECTED_DATASET_FINGERPRINT = (
    "91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876"
)


class BitgetMacdRealHistoryError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RealHistorySelection:
    symbol: str
    interval: str
    start_period: str
    end_period: str
    records: tuple[dict[str, Any], ...]
    record_fingerprint: str

    @property
    def partition_count(self) -> int:
        return len(self.records)

    @property
    def source_rows(self) -> int:
        return sum(int(item["source_rows"]) for item in self.records)


def _period_ordinal(period: str) -> int:
    try:
        year_text, month_text = period.split("-", 1)
        year = int(year_text)
        month = int(month_text)
    except (AttributeError, TypeError, ValueError) as exc:
        raise BitgetMacdRealHistoryError(f"invalid monthly period: {period!r}") from exc
    if year < 2000 or not 1 <= month <= 12:
        raise BitgetMacdRealHistoryError(f"invalid monthly period: {period!r}")
    return year * 12 + month - 1


def expected_monthly_periods(
    start_period: str = EXPECTED_START_PERIOD,
    end_period: str = EXPECTED_END_PERIOD,
) -> tuple[str, ...]:
    start = _period_ordinal(start_period)
    end = _period_ordinal(end_period)
    if end < start:
        raise BitgetMacdRealHistoryError("end period cannot precede start period")
    output = []
    for ordinal in range(start, end + 1):
        year, month_zero = divmod(ordinal, 12)
        output.append(f"{year:04d}-{month_zero + 1:02d}")
    return tuple(output)


def _catalog_market(catalog: Mapping[str, Any], symbol: str) -> Mapping[str, Any]:
    markets = catalog.get("markets")
    if not isinstance(markets, list):
        raise BitgetMacdRealHistoryError("Core100 catalog markets are missing")
    matches = [item for item in markets if isinstance(item, Mapping) and item.get("symbol") == symbol]
    if len(matches) != 1:
        raise BitgetMacdRealHistoryError(
            f"{symbol} must appear exactly once in the governed Core100 catalog"
        )
    market = matches[0]
    if market.get("asset_class") != "crypto":
        raise BitgetMacdRealHistoryError(f"{symbol} is not classified as crypto")
    return market


def select_governed_zec_15m_records(
    *,
    catalog: Mapping[str, Any],
    object_records: Iterable[Mapping[str, Any]],
    symbol: str = EXPECTED_SYMBOL,
    interval: str = EXPECTED_INTERVAL,
    start_period: str = EXPECTED_START_PERIOD,
    end_period: str = EXPECTED_END_PERIOD,
) -> RealHistorySelection:
    _catalog_market(catalog, symbol)
    expected = expected_monthly_periods(start_period, end_period)
    selected: list[dict[str, Any]] = []
    by_period: dict[str, dict[str, Any]] = {}

    for raw in object_records:
        if raw.get("symbol") != symbol or raw.get("interval") != interval:
            continue
        if raw.get("provider") != "binance_usdm":
            raise BitgetMacdRealHistoryError("ZEC partition provider mismatch")
        if raw.get("delivery") not in {
            "binance_vision",
            "binance_vision_monthly_daily_reconciliation",
        }:
            raise BitgetMacdRealHistoryError("ZEC partition delivery mismatch")
        period = str(raw.get("period") or "")
        if period not in expected:
            continue
        if period in by_period:
            raise BitgetMacdRealHistoryError(f"duplicate ZEC partition for {period}")
        if not str(raw.get("r2_key") or "").strip():
            raise BitgetMacdRealHistoryError("ZEC partition R2 key is missing")
        sha = str(raw.get("r2_sha256") or "")
        if len(sha) != 64:
            raise BitgetMacdRealHistoryError("ZEC partition SHA-256 is invalid")
        source_rows = raw.get("source_rows")
        if type(source_rows) is not int or source_rows <= 0:
            raise BitgetMacdRealHistoryError("ZEC partition row count is invalid")
        row = dict(raw)
        by_period[period] = row

    missing = [period for period in expected if period not in by_period]
    if missing:
        raise BitgetMacdRealHistoryError(
            "ZEC 15m governed history is incomplete: missing " + ",".join(missing)
        )

    selected = [by_period[period] for period in expected]
    binding = [
        {
            "period": item["period"],
            "r2_key": item["r2_key"],
            "r2_sha256": item["r2_sha256"],
            "source_rows": item["source_rows"],
            "delivery": item["delivery"],
        }
        for item in selected
    ]
    fingerprint = hashlib.sha256(
        json.dumps(binding, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return RealHistorySelection(
        symbol=symbol,
        interval=interval,
        start_period=start_period,
        end_period=end_period,
        records=tuple(selected),
        record_fingerprint=fingerprint,
    )


def validate_contiguous_15m_history(candles: Sequence[Candle]) -> None:
    if not candles:
        raise BitgetMacdRealHistoryError("ZEC 15m history is empty")
    interval_ms = 15 * 60 * 1000
    previous = candles[0]
    if previous.time_ms % interval_ms:
        raise BitgetMacdRealHistoryError("first ZEC candle is not 15m UTC aligned")
    for candle in candles[1:]:
        if candle.time_ms <= previous.time_ms:
            raise BitgetMacdRealHistoryError("ZEC candles are not strictly ordered")
        if candle.time_ms - previous.time_ms != interval_ms:
            raise BitgetMacdRealHistoryError(
                f"ZEC 15m history has a gap after {previous.time_ms}"
            )
        previous = candle


def validate_dataset_fingerprint(value: str) -> None:
    if value != EXPECTED_DATASET_FINGERPRINT:
        raise BitgetMacdRealHistoryError(
            "Core100 dataset fingerprint does not match the completed training dataset"
        )
