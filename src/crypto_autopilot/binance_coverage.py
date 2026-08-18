from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class CoverageSeriesSummary:
    symbol: str
    dataset: str
    interval: str
    scanned_months: tuple[str, ...]
    available_months: tuple[str, ...]
    no_data_months: tuple[str, ...]
    first_available_month: str | None
    last_available_month: str | None
    internal_gap_months: tuple[str, ...]
    leading_no_data_months: tuple[str, ...]
    trailing_no_data_months: tuple[str, ...]
    contiguous_between_first_last: bool


def month_periods(start_period: str, end_period: str) -> tuple[str, ...]:
    def parse(value: str) -> date:
        try:
            parsed = date.fromisoformat(value + "-01")
        except ValueError as exc:
            raise ValueError(f"invalid month period: {value}") from exc
        if parsed.strftime("%Y-%m") != value:
            raise ValueError(f"invalid month period: {value}")
        return parsed

    start = parse(start_period)
    end = parse(end_period)
    if start > end:
        raise ValueError("start_period must be <= end_period")
    output: list[str] = []
    current = start
    while current <= end:
        output.append(current.strftime("%Y-%m"))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    return tuple(output)


def summarize_presence(
    *,
    symbol: str,
    dataset: str,
    interval: str,
    scanned_months: tuple[str, ...],
    available_months: tuple[str, ...],
) -> CoverageSeriesSummary:
    if not symbol.strip() or not dataset.strip() or not interval.strip():
        raise ValueError("symbol, dataset and interval are required")
    if not scanned_months:
        raise ValueError("scanned_months cannot be empty")
    if tuple(sorted(set(scanned_months))) != scanned_months:
        raise ValueError("scanned_months must be sorted and unique")
    available = tuple(sorted(set(available_months)))
    scanned_set = set(scanned_months)
    if any(month not in scanned_set for month in available):
        raise ValueError("available_months must be within scanned_months")

    no_data = tuple(month for month in scanned_months if month not in set(available))
    if not available:
        return CoverageSeriesSummary(
            symbol=symbol,
            dataset=dataset,
            interval=interval,
            scanned_months=scanned_months,
            available_months=(),
            no_data_months=no_data,
            first_available_month=None,
            last_available_month=None,
            internal_gap_months=(),
            leading_no_data_months=no_data,
            trailing_no_data_months=(),
            contiguous_between_first_last=False,
        )

    first = available[0]
    last = available[-1]
    first_index = scanned_months.index(first)
    last_index = scanned_months.index(last)
    available_set = set(available)
    internal = tuple(
        month for month in scanned_months[first_index : last_index + 1] if month not in available_set
    )
    leading = tuple(scanned_months[:first_index])
    trailing = tuple(scanned_months[last_index + 1 :])
    return CoverageSeriesSummary(
        symbol=symbol,
        dataset=dataset,
        interval=interval,
        scanned_months=scanned_months,
        available_months=available,
        no_data_months=no_data,
        first_available_month=first,
        last_available_month=last,
        internal_gap_months=internal,
        leading_no_data_months=leading,
        trailing_no_data_months=trailing,
        contiguous_between_first_last=not internal,
    )
