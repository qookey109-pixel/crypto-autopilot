from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Iterable

from crypto_autopilot.binance.vision import BinanceVisionArchiveKey


SERIES: tuple[tuple[str, str], ...] = (
    ("klines", "15m"),
    ("klines", "1h"),
    ("klines", "4h"),
    ("markPriceKlines", "1h"),
)


def _parse_month(period: str) -> date:
    try:
        parsed = date.fromisoformat(f"{period}-01")
    except ValueError as exc:
        raise ValueError("month period must be YYYY-MM") from exc
    if parsed.strftime("%Y-%m") != period:
        raise ValueError("month period must be YYYY-MM")
    return parsed


def month_periods(start_month: str, end_month: str) -> tuple[str, ...]:
    start = _parse_month(start_month)
    end = _parse_month(end_month)
    if end < start:
        raise ValueError("end_month must not be before start_month")

    periods: list[str] = []
    year = start.year
    month = start.month
    while (year, month) <= (end.year, end.month):
        periods.append(f"{year:04d}-{month:02d}")
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
    return tuple(periods)


def daily_periods(start: date, end: date) -> tuple[str, ...]:
    if end < start:
        return ()
    periods: list[str] = []
    current = start
    while current <= end:
        periods.append(current.isoformat())
        current = date.fromordinal(current.toordinal() + 1)
    return tuple(periods)


def build_archive_keys(
    symbols: Iterable[str],
    *,
    frequency: str,
    periods: Iterable[str],
) -> tuple[BinanceVisionArchiveKey, ...]:
    keys: list[BinanceVisionArchiveKey] = []
    for symbol in symbols:
        for period in periods:
            for dataset, interval in SERIES:
                keys.append(
                    BinanceVisionArchiveKey(
                        dataset=dataset,
                        frequency=frequency,
                        symbol=symbol,
                        interval=interval,
                        period=period,
                    )
                )
    return tuple(keys)


def summarize_presence(
    records: Iterable[dict[str, object]],
    *,
    symbol: str,
    dataset: str,
    interval: str,
    ordered_periods: tuple[str, ...],
) -> dict[str, object]:
    selected = [
        record
        for record in records
        if record.get("symbol") == symbol
        and record.get("dataset") == dataset
        and record.get("interval") == interval
    ]
    by_period = {str(record["period"]): record for record in selected}
    if set(by_period) != set(ordered_periods):
        missing = sorted(set(ordered_periods) - set(by_period))
        extra = sorted(set(by_period) - set(ordered_periods))
        raise RuntimeError(
            f"coverage record period mismatch for {symbol} {dataset} {interval}: "
            f"missing={missing} extra={extra}"
        )
    statuses = {str(record.get("status")) for record in selected}
    if not statuses.issubset({"AVAILABLE", "NO_DATA"}):
        raise RuntimeError(
            f"unsupported coverage status for {symbol} {dataset} {interval}: {statuses}"
        )

    available_periods = [
        period for period in ordered_periods if by_period[period]["status"] == "AVAILABLE"
    ]
    no_data_periods = [
        period for period in ordered_periods if by_period[period]["status"] == "NO_DATA"
    ]
    if available_periods:
        first_index = ordered_periods.index(available_periods[0])
        last_index = ordered_periods.index(available_periods[-1])
        observed_span = ordered_periods[first_index : last_index + 1]
        missing_within_span = [
            period for period in observed_span if by_period[period]["status"] == "NO_DATA"
        ]
    else:
        missing_within_span = []

    return {
        "symbol": symbol,
        "dataset": dataset,
        "interval": interval,
        "available_periods": available_periods,
        "no_data_periods": no_data_periods,
        "available_count": len(available_periods),
        "no_data_count": len(no_data_periods),
        "first_available_period": available_periods[0] if available_periods else None,
        "last_available_period": available_periods[-1] if available_periods else None,
        "missing_periods_within_observed_span": missing_within_span,
        "continuous_archive_presence_within_observed_span": not missing_within_span,
    }


def ms_to_iso(value: int | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()


def attach_audited_boundaries(
    summary: dict[str, object],
    *,
    first_receipt: dict[str, object] | None,
    last_receipt: dict[str, object] | None,
    latest_daily_receipt: dict[str, object] | None = None,
) -> dict[str, object]:
    result = dict(summary)
    if first_receipt is None and last_receipt is None and latest_daily_receipt is None:
        result.update(
            {
                "earliest_candle_time_ms": None,
                "earliest_candle_time_utc": None,
                "latest_candle_time_ms": None,
                "latest_candle_time_utc": None,
                "audited_first_archive": None,
                "audited_last_monthly_archive": None,
                "audited_latest_daily_archive": None,
            }
        )
        return result

    first_candidates = [
        receipt
        for receipt in (first_receipt, latest_daily_receipt)
        if receipt is not None and receipt.get("first_time_ms") is not None
    ]
    last_candidates = [
        receipt
        for receipt in (last_receipt, latest_daily_receipt)
        if receipt is not None and receipt.get("last_time_ms") is not None
    ]
    earliest = min(int(receipt["first_time_ms"]) for receipt in first_candidates)
    latest = max(int(receipt["last_time_ms"]) for receipt in last_candidates)
    result.update(
        {
            "earliest_candle_time_ms": earliest,
            "earliest_candle_time_utc": ms_to_iso(earliest),
            "latest_candle_time_ms": latest,
            "latest_candle_time_utc": ms_to_iso(latest),
            "audited_first_archive": first_receipt,
            "audited_last_monthly_archive": last_receipt,
            "audited_latest_daily_archive": latest_daily_receipt,
        }
    )
    return result


def summarize_symbol_boundaries(
    symbol: str,
    series_summaries: Iterable[dict[str, object]],
) -> dict[str, object]:
    own = [summary for summary in series_summaries if summary.get("symbol") == symbol]
    by_series = {
        (str(summary["dataset"]), str(summary["interval"])): summary for summary in own
    }
    expected = set(SERIES)
    if set(by_series) != expected:
        raise RuntimeError(
            f"missing coverage series for {symbol}: expected={sorted(expected)} "
            f"observed={sorted(by_series)}"
        )

    trade = [by_series[("klines", interval)] for interval in ("15m", "1h", "4h")]
    trade_earliest = [summary.get("earliest_candle_time_ms") for summary in trade]
    trade_latest = [summary.get("latest_candle_time_ms") for summary in trade]
    if all(value is not None for value in trade_earliest + trade_latest):
        trade_common_earliest = max(int(value) for value in trade_earliest)
        trade_common_latest = min(int(value) for value in trade_latest)
        trade_common_available = trade_common_earliest <= trade_common_latest
    else:
        trade_common_earliest = None
        trade_common_latest = None
        trade_common_available = False

    mark = by_series[("markPriceKlines", "1h")]
    mark_earliest = mark.get("earliest_candle_time_ms")
    mark_latest = mark.get("latest_candle_time_ms")
    all_earliest = trade_earliest + [mark_earliest]
    all_latest = trade_latest + [mark_latest]
    if all(value is not None for value in all_earliest + all_latest):
        strategy_common_earliest = max(int(value) for value in all_earliest)
        strategy_common_latest = min(int(value) for value in all_latest)
        strategy_common_available = strategy_common_earliest <= strategy_common_latest
    else:
        strategy_common_earliest = None
        strategy_common_latest = None
        strategy_common_available = False

    return {
        "binance_symbol": symbol,
        "series": [
            by_series[("klines", "15m")],
            by_series[("klines", "1h")],
            by_series[("klines", "4h")],
            by_series[("markPriceKlines", "1h")],
        ],
        "trade_common_window": {
            "available": trade_common_available,
            "earliest_candle_time_ms": trade_common_earliest,
            "earliest_candle_time_utc": ms_to_iso(trade_common_earliest),
            "latest_candle_time_ms": trade_common_latest,
            "latest_candle_time_utc": ms_to_iso(trade_common_latest),
        },
        "strategy_price_common_window": {
            "includes_mark_price_1h": True,
            "available": strategy_common_available,
            "earliest_candle_time_ms": strategy_common_earliest,
            "earliest_candle_time_utc": ms_to_iso(strategy_common_earliest),
            "latest_candle_time_ms": strategy_common_latest,
            "latest_candle_time_utc": ms_to_iso(strategy_common_latest),
        },
        "has_internal_monthly_presence_gap": any(
            bool(summary["missing_periods_within_observed_span"]) for summary in own
        ),
    }
