"""Pionex-native historical reach discovery for the V0.3 simulation-readiness path.

This module never performs network access at import time and never persists candles.
It classifies how far the public Pionex kline API can be traversed before either
the provider's earliest returned candle or the documented 10,000-record cap.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import math
from typing import Protocol, Sequence

from ..historical import INTERVAL_MS, audit_candles
from ..models import Candle


class ReachRejected(RuntimeError):
    pass


class KlineClient(Protocol):
    def get_klines(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
        end_time_ms: int | None = None,
    ) -> list[Candle]: ...


@dataclass(frozen=True, slots=True)
class IntervalReach:
    interval: str
    classification: str
    records_observed: int
    data_pages: int
    requests: int
    earliest_time_ms: int
    latest_time_ms: int
    span_days: float
    continuity_verified: bool
    documented_record_cap: int

    def payload(self) -> dict[str, object]:
        value = asdict(self)
        value["earliest_utc"] = iso_utc(self.earliest_time_ms)
        value["latest_utc"] = iso_utc(self.latest_time_ms)
        return value


def stamp(text: str) -> int:
    return int(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp() * 1000)


def iso_utc(value_ms: int) -> str:
    return datetime.fromtimestamp(value_ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def require_execution_window(config: dict[str, object], clock=now_ms) -> None:
    current = clock()
    start = stamp(str(config["not_before_utc"]))
    stop = stamp(str(config["stop_exclusive_utc"]))
    if not start <= current < stop:
        raise ReachRejected("execution window closed")


def _require_fixed_scope(config: dict[str, object]) -> None:
    if config.get("provider") != "pionex_public_futures":
        raise ReachRejected("provider scope changed")
    if config.get("symbol") != "BTC_USDT_PERP":
        raise ReachRejected("symbol scope changed")
    if config.get("intervals") != ["15M", "60M", "4H"]:
        raise ReachRejected("interval scope changed")
    if config.get("cutoff_exclusive_utc") != "2026-08-28T00:00:00Z":
        raise ReachRejected("cutoff changed or protected holdout could be crossed")
    if config.get("page_limit") != 500:
        raise ReachRejected("page limit changed")
    if config.get("documented_max_records_per_interval") != 10_000:
        raise ReachRejected("documented record cap changed")
    if config.get("max_pages_per_interval") != 20:
        raise ReachRejected("page budget changed")
    if config.get("boundary_probe_limit") != 1:
        raise ReachRejected("boundary probe changed")
    if config.get("maximum_requests") != 63:
        raise ReachRejected("request budget changed")

    authority = config.get("authority")
    if not isinstance(authority, dict):
        raise ReachRejected("authority missing")
    required = {
        "public_pionex_reads": True,
        "workflow_dispatch": True,
        "automatic_schedule": False,
        "api_key_required": False,
        "private_account_reads": False,
        "r2_read": False,
        "r2_write": False,
        "holdout_access": False,
        "training": False,
        "formal_backtest_admission": False,
        "strategy_change": False,
        "source_switch": False,
        "binance_relabel_as_pionex": False,
        "trade_plan": False,
        "real_money_orders": False,
        "live_trading": False,
    }
    if authority != required:
        raise ReachRejected("authority widened or changed")

    output = config.get("output")
    if not isinstance(output, dict):
        raise ReachRejected("output policy missing")
    if output.get("persist_raw_provider_payloads") is not False:
        raise ReachRejected("raw payload persistence not allowed")
    if output.get("persist_candles") is not False:
        raise ReachRejected("candle persistence not allowed")
    if output.get("r2_read") is not False or output.get("r2_write") is not False:
        raise ReachRejected("R2 access not allowed")


def _validate_page(
    page: Sequence[Candle],
    *,
    interval: str,
    cursor: int,
    limit: int,
    seen: set[int],
) -> None:
    if len(page) > limit:
        raise ReachRejected("provider returned more rows than requested")
    if not page:
        return
    step = INTERVAL_MS[interval]
    if any(candle.time_ms > cursor for candle in page):
        raise ReachRejected("provider returned candle after discovery cursor")
    if any(candle.time_ms in seen for candle in page):
        raise ReachRejected("provider repeated candle across pages")
    audit = audit_candles(tuple(page), interval)
    if not audit.ok:
        raise ReachRejected("provider page is missing, duplicate, unordered, misaligned or invalid")
    if page[-1].time_ms != cursor:
        raise ReachRejected("provider page does not end at requested cursor")
    expected_first = cursor - (len(page) - 1) * step
    if page[0].time_ms != expected_first:
        raise ReachRejected("provider page endpoints are not contiguous")


def discover_interval(
    config: dict[str, object],
    client: KlineClient,
    interval: str,
    progress: dict[str, int],
) -> IntervalReach:
    _require_fixed_scope(config)
    if interval not in config["intervals"]:
        raise ReachRejected("interval not authorized")
    step = INTERVAL_MS[interval]
    cutoff = stamp(str(config["cutoff_exclusive_utc"]))
    cursor = cutoff - step
    page_limit = int(config["page_limit"])
    max_records = int(config["documented_max_records_per_interval"])
    max_pages = int(config["max_pages_per_interval"])
    maximum_requests = int(config["maximum_requests"])
    seen: set[int] = set()
    data_pages = 0
    interval_requests = 0
    classification: str | None = None

    while len(seen) < max_records and data_pages < max_pages:
        if progress["requests"] >= maximum_requests:
            raise ReachRejected("global request budget exhausted")
        remaining = max_records - len(seen)
        limit = min(page_limit, remaining)
        progress["requests"] += 1
        interval_requests += 1
        try:
            page = client.get_klines(
                str(config["symbol"]),
                interval,
                limit=limit,
                end_time_ms=cursor,
            )
        except Exception:
            raise ReachRejected("provider request failed; discovery is incomplete") from None

        if not page:
            if not seen:
                raise ReachRejected("provider returned no data at discovery cutoff")
            classification = str(config["classification"]["provider_earliest_reached"])
            break

        _validate_page(page, interval=interval, cursor=cursor, limit=limit, seen=seen)
        data_pages += 1
        seen.update(candle.time_ms for candle in page)

        if len(page) < limit:
            probe_cursor = page[0].time_ms - step
            if progress["requests"] >= maximum_requests:
                raise ReachRejected("boundary probe exceeds global request budget")
            progress["requests"] += 1
            interval_requests += 1
            try:
                probe = client.get_klines(
                    str(config["symbol"]),
                    interval,
                    limit=int(config["boundary_probe_limit"]),
                    end_time_ms=probe_cursor,
                )
            except Exception:
                raise ReachRejected("provider boundary probe failed") from None
            if probe:
                _validate_page(
                    probe,
                    interval=interval,
                    cursor=probe_cursor,
                    limit=int(config["boundary_probe_limit"]),
                    seen=seen,
                )
                raise ReachRejected("short page did not prove provider earliest boundary")
            classification = str(config["classification"]["provider_earliest_reached"])
            break

        if len(seen) == max_records:
            classification = str(config["classification"]["documented_record_cap_reached"])
            break

        cursor = page[0].time_ms - step

    if not seen:
        raise ReachRejected("no valid candles observed")
    if classification is None:
        if len(seen) == max_records:
            classification = str(config["classification"]["documented_record_cap_reached"])
        else:
            raise ReachRejected("discovery ended without a valid boundary classification")

    ordered = sorted(seen)
    earliest, latest = ordered[0], ordered[-1]
    expected_count = (latest - earliest) // step + 1
    if expected_count != len(ordered):
        raise ReachRejected("cross-page continuity failed")
    span_days = len(ordered) * step / 86_400_000
    if not math.isfinite(span_days) or span_days <= 0:
        raise ReachRejected("invalid reach span")

    return IntervalReach(
        interval=interval,
        classification=classification,
        records_observed=len(ordered),
        data_pages=data_pages,
        requests=interval_requests,
        earliest_time_ms=earliest,
        latest_time_ms=latest,
        span_days=span_days,
        continuity_verified=True,
        documented_record_cap=max_records,
    )


def discover_all(
    config: dict[str, object],
    client: KlineClient,
) -> dict[str, object]:
    _require_fixed_scope(config)
    progress = {"requests": 0}
    observations = [
        discover_interval(config, client, interval, progress)
        for interval in config["intervals"]
    ]
    return {
        "status": "PASS",
        "symbol": config["symbol"],
        "cutoff_exclusive_utc": config["cutoff_exclusive_utc"],
        "requests": progress["requests"],
        "intervals": [item.payload() for item in observations],
        "raw_provider_payloads_persisted": False,
        "candles_persisted": False,
        "r2_accessed": False,
        "holdout_accessed": False,
        "api_key_used": False,
        "full_history_complete": all(
            item.classification == config["classification"]["provider_earliest_reached"]
            for item in observations
        ),
        "materialization_authorized": False,
        "formal_backtest_admission_authorized": False,
        "live_trading_authorized": False,
    }
