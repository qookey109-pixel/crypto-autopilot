from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from crypto_autopilot.historical import audit_candles
from crypto_autopilot.models import Candle
from crypto_autopilot.storage.layout import HistoricalObjectKey


class Binance2025PilotAuthorityError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Binance2025SymbolCoverage:
    symbol: str
    months: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.symbol.strip() or self.symbol != self.symbol.upper():
            raise ValueError("symbol must be a non-empty uppercase Binance symbol")
        if not self.months:
            raise ValueError("months cannot be empty")
        if tuple(sorted(set(self.months))) != self.months:
            raise ValueError("months must be sorted and unique")
        if any(month < 1 or month > 12 for month in self.months):
            raise ValueError("months must be between 1 and 12")


@dataclass(frozen=True, slots=True)
class Binance2025PartitionPlan:
    symbol: str
    interval: str
    year: int
    month: int | None
    source_months: tuple[int, ...]
    r2_key: str

    def __post_init__(self) -> None:
        if self.year != 2025:
            raise ValueError("V0.1 pilot is frozen to 2025")
        if self.interval not in {"15M", "60M", "4H"}:
            raise ValueError("unsupported pilot interval")
        if not self.source_months:
            raise ValueError("source_months cannot be empty")
        if self.interval == "15M":
            if self.month is None or self.source_months != (self.month,):
                raise ValueError("15M pilot partitions must be one monthly source archive")
        elif self.month is not None:
            raise ValueError("60M/4H pilot partitions are annual and cannot have month")
        if not self.r2_key.startswith("market-data/binance_usdm/"):
            raise ValueError("Binance pilot object must use the binance_usdm namespace")
        if "market-data/pionex/" in self.r2_key:
            raise ValueError("Binance pilot object cannot use a Pionex namespace")


def _month_number(period: str) -> int:
    try:
        year_text, month_text = period.split("-", 1)
        year = int(year_text)
        month = int(month_text)
    except (ValueError, AttributeError) as exc:
        raise Binance2025PilotAuthorityError(f"invalid coverage period: {period!r}") from exc
    if year != 2025 or month < 1 or month > 12:
        raise Binance2025PilotAuthorityError(f"coverage period outside frozen 2025 pilot: {period}")
    return month


def load_coverage_authority(path: str | Path) -> tuple[Binance2025SymbolCoverage, ...]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("status") != "PASS" or payload.get("stage") != "BINANCE_2025_COVERAGE_SCAN_PASS":
        raise Binance2025PilotAuthorityError("coverage authority must be BINANCE_2025_COVERAGE_SCAN_PASS")
    if payload.get("provider") != "binance_usdm" or payload.get("delivery") != "binance_vision":
        raise Binance2025PilotAuthorityError("coverage authority provider/delivery mismatch")
    if payload.get("native_to_execution_exchange") is not False:
        raise Binance2025PilotAuthorityError("coverage authority must remain non-native to Pionex")
    if payload.get("may_authorize_pionex_native_history") is not False:
        raise Binance2025PilotAuthorityError("coverage authority must not authorize Pionex-native history")
    if int(payload.get("year") or 0) != 2025 or int(payload.get("candidate_count") or 0) != 15:
        raise Binance2025PilotAuthorityError("coverage authority must freeze 15 candidates for 2025")

    full_symbols = tuple(payload.get("coverage_summary", {}).get("full_2025_trade_archive_presence_symbols") or ())
    if len(full_symbols) != 14 or len(set(full_symbols)) != 14:
        raise Binance2025PilotAuthorityError("coverage authority must contain exactly 14 full-year trade symbols")
    coverage: dict[str, tuple[int, ...]] = {str(symbol): tuple(range(1, 13)) for symbol in full_symbols}

    partial = payload.get("partial_coverage") or {}
    if set(partial) != {"HYPEUSDT"}:
        raise Binance2025PilotAuthorityError("V0.1 authority expects HYPEUSDT as the only partial symbol")
    hype_periods = partial["HYPEUSDT"].get("trade_15m_available_months") or []
    hype_months = tuple(_month_number(str(period)) for period in hype_periods)
    if hype_months != tuple(range(5, 13)):
        raise Binance2025PilotAuthorityError("HYPEUSDT V0.1 coverage must be 2025-05 through 2025-12")
    for field in ("trade_1h_available_months", "trade_4h_available_months"):
        months = tuple(_month_number(str(period)) for period in partial["HYPEUSDT"].get(field) or [])
        if months != hype_months:
            raise Binance2025PilotAuthorityError(f"HYPEUSDT coverage mismatch for {field}")
    coverage["HYPEUSDT"] = hype_months

    if len(coverage) != 15:
        raise Binance2025PilotAuthorityError("coverage authority did not resolve exactly 15 symbols")
    return tuple(
        Binance2025SymbolCoverage(symbol=symbol, months=months)
        for symbol, months in sorted(coverage.items())
    )


def build_partition_plan(
    coverage: tuple[Binance2025SymbolCoverage, ...],
) -> tuple[Binance2025PartitionPlan, ...]:
    plans: list[Binance2025PartitionPlan] = []
    for item in coverage:
        for month in item.months:
            key = HistoricalObjectKey(
                exchange="binance_usdm",
                market_type="perp",
                symbol=item.symbol,
                interval="15M",
                year=2025,
                month=month,
            ).build()
            plans.append(
                Binance2025PartitionPlan(
                    symbol=item.symbol,
                    interval="15M",
                    year=2025,
                    month=month,
                    source_months=(month,),
                    r2_key=key,
                )
            )
        for interval in ("60M", "4H"):
            key = HistoricalObjectKey(
                exchange="binance_usdm",
                market_type="perp",
                symbol=item.symbol,
                interval=interval,
                year=2025,
                month=None,
            ).build()
            plans.append(
                Binance2025PartitionPlan(
                    symbol=item.symbol,
                    interval=interval,
                    year=2025,
                    month=None,
                    source_months=item.months,
                    r2_key=key,
                )
            )
    plans.sort(key=lambda plan: (plan.symbol, plan.interval, plan.month or 0))
    if len(plans) != 206:
        raise Binance2025PilotAuthorityError(f"expected 206 pilot objects, got {len(plans)}")
    if len({plan.r2_key for plan in plans}) != len(plans):
        raise Binance2025PilotAuthorityError("pilot partition plan contains duplicate R2 keys")
    return tuple(plans)


def combine_and_audit_months(
    monthly_candles: tuple[tuple[Candle, ...], ...],
    *,
    interval: str,
) -> tuple[Candle, ...]:
    if interval not in {"60M", "4H"}:
        raise ValueError("annual aggregation is supported only for 60M and 4H")
    if not monthly_candles or any(not month for month in monthly_candles):
        raise Binance2025PilotAuthorityError("annual aggregation requires non-empty monthly candle sets")
    combined = tuple(candle for month in monthly_candles for candle in month)
    times = [candle.time_ms for candle in combined]
    if times != sorted(times) or len(times) != len(set(times)):
        raise Binance2025PilotAuthorityError("aggregated annual candles must be strictly increasing and unique")
    audit = audit_candles(combined, interval)
    if not audit.ok:
        raise Binance2025PilotAuthorityError(
            "aggregated annual candle audit failed for "
            f"{interval}: gaps={audit.gaps}, duplicates={audit.duplicate_timestamps}"
        )
    return combined


def source_archive_digest(items: tuple[tuple[str, str], ...]) -> str:
    """Digest ordered `(filename, sha256)` source authority for one R2 object."""

    normalized = tuple(sorted((str(filename), str(sha).lower()) for filename, sha in items))
    if not normalized:
        raise ValueError("source archive digest requires at least one item")
    for filename, sha in normalized:
        if not filename.strip() or len(sha) != 64 or any(char not in "0123456789abcdef" for char in sha):
            raise ValueError("invalid source archive digest item")
    payload = json.dumps(normalized, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
