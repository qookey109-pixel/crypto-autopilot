"""V0.2-only handling for Pionex history that stops before the frozen cutoff.

V0.1 remains frozen.  This module preserves all V0.1 validation and request
budget semantics, but permits one narrowly-defined V0.2 condition: the first
successful provider page may end before the requested frozen-cutoff cursor.
That condition is recorded as explicit partial coverage and collection then
continues backward from the provider's actual latest observed candle.

No rows are fabricated, interpolated, or sourced from another provider.
Any later page/cross-page discontinuity remains fail-closed.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

from ..historical import INTERVAL_MS, audit_candles
from ..models import Candle
from .pionex_validation_materialization_v0_1 import (
    PartitionResult,
    ValidationMaterializationRejected,
    _last_aligned_candle_before,
    _safe_error,
    _validate_page,
    profile_for_symbol,
    require_execution_window,
    stamp,
    validate_config,
)
from .pionex_validation_materialization_v0_2 import ZERO_HISTORY_COVERAGE_STATUS

TRAILING_HISTORY_COVERAGE_PREFIX = "PARTIAL_PROVIDER_LATEST_BEFORE_CUTOFF"


def _validate_initial_page(
    page: Sequence[Candle],
    *,
    interval: str,
    cursor: int,
    limit: int,
) -> bool:
    """Validate the first page and return whether its latest row trails cursor.

    Exact-at-cursor pages are delegated to the frozen V0.1 validator.  A page
    ending before cursor is accepted only when the returned rows themselves are
    ordered, aligned, valid, and contiguous.  This exception is intentionally
    first-page-only; later page endpoint mismatches still fail closed through
    the V0.1 validator.
    """
    if len(page) > limit:
        raise ValidationMaterializationRejected("provider returned more rows than requested")
    if not page:
        return False
    if any(candle.time_ms > cursor for candle in page):
        raise ValidationMaterializationRejected("provider returned candle after requested cursor")
    if page[-1].time_ms == cursor:
        _validate_page(page, interval=interval, cursor=cursor, limit=limit, seen=set())
        return False

    audit = audit_candles(tuple(page), interval)
    if not audit.ok:
        raise ValidationMaterializationRejected(
            "provider first page before cutoff is missing, duplicate, unordered, misaligned or invalid"
        )
    step = INTERVAL_MS[interval]
    expected_first = page[-1].time_ms - (len(page) - 1) * step
    if page[0].time_ms != expected_first:
        raise ValidationMaterializationRejected("provider first-page endpoints are not contiguous")
    return True


def _with_trailing_coverage(status: str) -> str:
    return f"{TRAILING_HISTORY_COVERAGE_PREFIX}__{status}"


def collect_partition_v0_2_with_trailing_coverage(
    config: Mapping[str, Any],
    client: Any,
    *,
    symbol: str,
    interval: str,
    progress: dict[str, int],
    clock: Callable[[], int],
) -> PartitionResult:
    """Collect one V0.2 partition with explicit zero/tail-history coverage.

    This mirrors the frozen V0.1 bounded collector except for two already
    reviewed V0.2 outcomes:

    * a successful empty first response is explicit zero history; and
    * a clean first page ending before the cutoff is explicit trailing absence.

    Once the actual latest provider candle is established, all older pages use
    the exact V0.1 endpoint/continuity validator.  Provider errors, protected
    range reads, internal gaps, duplicates, invalid candles, and later endpoint
    mismatches remain fail-closed or retain the existing V0.1 partial-boundary
    semantics.
    """
    validate_config(config)
    profile = profile_for_symbol(config, symbol)
    if interval not in config["history_profiles"][profile]["intervals"]:
        raise ValidationMaterializationRejected("interval outside symbol history profile")
    require_execution_window(config, now_ms=clock())

    cutoff = stamp(str(config["cutoff_exclusive_utc"]))
    step = INTERVAL_MS[interval]
    frozen_cursor = _last_aligned_candle_before(cutoff, interval)
    cursor = frozen_cursor
    page_limit = int(config["materialization"]["page_limit"])
    max_records = int(config["materialization"]["maximum_records_per_symbol_interval"])
    max_requests = int(config["materialization"]["maximum_provider_requests"])
    seen: dict[int, Candle] = {}
    partition_requests = 0
    coverage_status: str | None = None
    error_type: str | None = None
    error_status: int | None = None
    provider_latest_before_cutoff: int | None = None
    first_page = True

    while len(seen) < max_records:
        require_execution_window(config, now_ms=clock())
        if progress["requests"] >= max_requests:
            raise ValidationMaterializationRejected("global provider request budget exhausted")
        limit = min(page_limit, max_records - len(seen))
        progress["requests"] += 1
        partition_requests += 1
        try:
            page = client.get_klines(symbol, interval, limit=limit, end_time_ms=cursor)
        except Exception as exc:
            if not seen:
                raise ValidationMaterializationRejected(
                    "provider request failed before any valid rows",
                    diagnostics={
                        "symbol": symbol,
                        "interval": interval,
                        "stage": "page",
                        "error_type": type(exc).__name__,
                    },
                ) from None
            coverage_status = "PARTIAL_PROVIDER_REQUEST_BOUNDARY"
            error_type, error_status = _safe_error(exc)
            break

        if any(candle.time_ms >= cutoff for candle in page):
            progress["protected_range_violation"] = 1
            raise ValidationMaterializationRejected(
                "provider returned candle at or beyond protected cutoff",
                diagnostics={"symbol": symbol, "interval": interval},
            )

        if first_page:
            trailing = _validate_initial_page(
                page,
                interval=interval,
                cursor=cursor,
                limit=limit,
            )
            if trailing and page:
                provider_latest_before_cutoff = page[-1].time_ms
        else:
            _validate_page(page, interval=interval, cursor=cursor, limit=limit, seen=set(seen))

        if not page:
            if not seen:
                return PartitionResult(
                    symbol=symbol,
                    interval=interval,
                    coverage_status=ZERO_HISTORY_COVERAGE_STATUS,
                    candles=(),
                    requests=partition_requests,
                )
            coverage_status = "PROVIDER_EARLIEST_REACHED"
            break

        first_page = False
        for candle in page:
            seen[candle.time_ms] = candle

        if len(page) < limit:
            probe_cursor = page[0].time_ms - step
            require_execution_window(config, now_ms=clock())
            if progress["requests"] >= max_requests:
                raise ValidationMaterializationRejected(
                    "global provider request budget exhausted before boundary probe"
                )
            progress["requests"] += 1
            partition_requests += 1
            try:
                probe = client.get_klines(
                    symbol,
                    interval,
                    limit=int(config["materialization"]["boundary_probe_limit"]),
                    end_time_ms=probe_cursor,
                )
            except Exception as exc:
                coverage_status = "PARTIAL_PROVIDER_BOUNDARY_PROBE_FAILED"
                error_type, error_status = _safe_error(exc)
                break
            if any(candle.time_ms >= cutoff for candle in probe):
                progress["protected_range_violation"] = 1
                raise ValidationMaterializationRejected(
                    "provider boundary probe returned protected-range candle",
                    diagnostics={"symbol": symbol, "interval": interval},
                )
            _validate_page(probe, interval=interval, cursor=probe_cursor, limit=1, seen=set(seen))
            if not probe:
                coverage_status = "PROVIDER_EARLIEST_REACHED"
                break
            for candle in probe:
                seen[candle.time_ms] = candle
            cursor = probe[0].time_ms - step
            continue

        if len(seen) >= max_records:
            coverage_status = "BOUNDED_RECORD_CAP_REACHED"
            break
        cursor = page[0].time_ms - step

    candles = tuple(seen[key] for key in sorted(seen))
    if not candles:
        raise ValidationMaterializationRejected("partition contains no valid candles")
    if not audit_candles(candles, interval).ok:
        raise ValidationMaterializationRejected("cross-page partition continuity failed")

    if provider_latest_before_cutoff is None:
        if candles[-1].time_ms != frozen_cursor:
            raise ValidationMaterializationRejected("partition does not end at frozen validation cutoff")
    else:
        if not candles[-1].time_ms < frozen_cursor:
            raise ValidationMaterializationRejected("trailing-history classification is inconsistent with cutoff")
        if candles[-1].time_ms != provider_latest_before_cutoff:
            raise ValidationMaterializationRejected("trailing-history latest-row accounting mismatch")

    if coverage_status is None:
        coverage_status = (
            "BOUNDED_RECORD_CAP_REACHED" if len(candles) >= max_records else "PARTIAL_UNCLASSIFIED"
        )
    if provider_latest_before_cutoff is not None:
        coverage_status = _with_trailing_coverage(coverage_status)

    return PartitionResult(
        symbol=symbol,
        interval=interval,
        coverage_status=coverage_status,
        candles=candles,
        requests=partition_requests,
        provider_error_type=error_type,
        provider_http_status=error_status,
    )
