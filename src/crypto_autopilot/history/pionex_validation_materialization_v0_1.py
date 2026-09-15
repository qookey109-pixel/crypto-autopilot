"""Bounded Pionex-native validation dataset materialization V0.1.

The module is provider-native and fail-closed. It does not perform network or R2
I/O at import time. Binance data is never used to fill Pionex gaps.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Callable, Mapping, Protocol, Sequence

from ..historical import INTERVAL_ALIGNMENT_OFFSET_MS, INTERVAL_MS, audit_candles
from ..models import Candle


class ValidationMaterializationRejected(RuntimeError):
    def __init__(self, message: str, *, diagnostics: dict[str, object] | None = None):
        super().__init__(message)
        self.diagnostics = diagnostics or {}


class KlineClient(Protocol):
    def get_klines(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
        end_time_ms: int | None = None,
    ) -> list[Candle]: ...


_RUN_ID_RE = re.compile(r"^github-[0-9]+-1$")
_SAFE_SYMBOL_RE = re.compile(r"^[A-Z0-9]+_USDT_PERP$")
_EXPECTED_CLASSES = {
    "crypto",
    "equity_linked_token",
    "etf_or_fund_linked_token",
    "company_reference_perpetual",
    "energy_commodity_reference",
    "industrial_metal_reference",
    "precious_metal_reference",
    "tokenized_precious_metal",
}
_EXPECTED_PROFILE_INTERVALS = {
    "FULL_INTRADAY": ["15M", "60M", "4H", "1D", "1W"],
    "MULTISCALE_RESEARCH": ["60M", "4H", "1D", "1W"],
    "BREADTH_BACKGROUND": ["1D", "1W"],
}


def stamp(text: str) -> int:
    return int(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp() * 1000)


def iso_utc(value_ms: int) -> str:
    return datetime.fromtimestamp(value_ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def validate_config(config: Mapping[str, Any]) -> None:
    if config.get("schema") != "pionex-validation-dataset-v0.1" or config.get("version") != "0.1.0":
        raise ValidationMaterializationRejected("unexpected validation-dataset config version")
    if config.get("status") != "AUTHORIZED_AFTER_REVIEWED_MAIN_MERGE_MANUAL_ONLY":
        raise ValidationMaterializationRejected("validation dataset authority status changed")
    if config.get("provider") != "pionex_public_futures":
        raise ValidationMaterializationRejected("provider changed")
    if config.get("cutoff_exclusive_utc") != "2026-08-28T00:00:00Z":
        raise ValidationMaterializationRejected("protected cutoff changed")

    architecture = config.get("architecture")
    if architecture != {
        "binance_role": "LARGE_SCALE_LEARNING_DATABASE",
        "pionex_is_core100_training_input": False,
        "pionex_role": "FINAL_CALIBRATION_AND_REAL_TRADING_ENVIRONMENT",
    }:
        raise ValidationMaterializationRejected("Binance/Pionex architecture contract changed")

    source = config.get("source_universe")
    if not isinstance(source, Mapping):
        raise ValidationMaterializationRejected("source universe missing")
    if source.get("workflow_run_id") != 34563615657 or source.get("artifact_id") != 10185197916:
        raise ValidationMaterializationRejected("source universe evidence changed")
    if source.get("artifact_digest") != "sha256:997c99f495e423673e8550da083b15dfc1a2f146833f64efc3d7da227bda8c47":
        raise ValidationMaterializationRejected("source universe artifact digest changed")
    if source.get("selected_market_count") != 197 or source.get("historical_snapshot_regraded") is not False:
        raise ValidationMaterializationRejected("source universe semantics changed")

    profiles = config.get("history_profiles")
    if not isinstance(profiles, Mapping) or set(profiles) != set(_EXPECTED_PROFILE_INTERVALS):
        raise ValidationMaterializationRejected("history profiles changed")
    all_symbols: list[str] = []
    expected_counts = {"FULL_INTRADAY": 30, "MULTISCALE_RESEARCH": 99, "BREADTH_BACKGROUND": 68}
    for profile, intervals in _EXPECTED_PROFILE_INTERVALS.items():
        value = profiles.get(profile)
        if not isinstance(value, Mapping) or value.get("intervals") != intervals:
            raise ValidationMaterializationRejected(f"{profile} intervals changed")
        symbols = value.get("symbols")
        if not isinstance(symbols, list) or len(symbols) != expected_counts[profile]:
            raise ValidationMaterializationRejected(f"{profile} symbol count changed")
        if symbols != sorted(symbols) or len(symbols) != len(set(symbols)):
            raise ValidationMaterializationRejected(f"{profile} symbols must be unique and sorted")
        if any(not _SAFE_SYMBOL_RE.fullmatch(str(symbol)) for symbol in symbols):
            raise ValidationMaterializationRejected(f"{profile} contains unsafe symbol")
        all_symbols.extend(str(symbol) for symbol in symbols)
    if len(all_symbols) != 197 or len(set(all_symbols)) != 197:
        raise ValidationMaterializationRejected("history profile symbols must partition exactly 197 markets")

    overlay = config.get("classification_overlay")
    if not isinstance(overlay, Mapping) or overlay.get("default_class") != "crypto":
        raise ValidationMaterializationRejected("classification overlay missing")
    explicit = overlay.get("explicit_classes")
    counts = overlay.get("class_counts")
    if not isinstance(explicit, Mapping) or not isinstance(counts, Mapping):
        raise ValidationMaterializationRejected("classification map/counts missing")
    if set(explicit) != _EXPECTED_CLASSES - {"crypto"} or set(counts) != _EXPECTED_CLASSES:
        raise ValidationMaterializationRejected("classification classes changed")
    explicit_symbols: set[str] = set()
    for asset_class, values in explicit.items():
        if not isinstance(values, list) or values != sorted(values) or len(values) != len(set(values)):
            raise ValidationMaterializationRejected(f"classification {asset_class} is not deterministic")
        for symbol in values:
            if symbol not in set(all_symbols) or symbol in explicit_symbols:
                raise ValidationMaterializationRejected("classification overlay has unknown or duplicate symbol")
            explicit_symbols.add(str(symbol))
    derived_counts = {asset_class: 0 for asset_class in _EXPECTED_CLASSES}
    for symbol in all_symbols:
        derived_counts[asset_class_for_symbol(config, symbol)] += 1
    if dict(counts) != derived_counts or sum(derived_counts.values()) != 197:
        raise ValidationMaterializationRejected("classification counts do not match 197-market overlay")
    if overlay.get("preserve_source_history_profile") is not True or overlay.get("preserve_source_selection_evidence") is not True:
        raise ValidationMaterializationRejected("historical source evidence preservation weakened")

    materialization = config.get("materialization")
    if not isinstance(materialization, Mapping):
        raise ValidationMaterializationRejected("materialization contract missing")
    exact = {
        "maximum_records_per_symbol_interval": 9000,
        "page_limit": 500,
        "boundary_probe_limit": 1,
        "requests_per_second": 3.0,
        "request_timeout_seconds": 15.0,
        "maximum_provider_requests": 15000,
        "manual_main_workflow_dispatch_only": True,
        "automatic_schedule": False,
        "partial_partition_may_be_stored": True,
        "partial_partition_is_complete_history": False,
        "silent_interpolation_allowed": False,
        "provider_splicing_allowed": False,
    }
    for key, expected in exact.items():
        if materialization.get(key) != expected:
            raise ValidationMaterializationRejected(f"materialization.{key} changed")
    if materialization.get("missing_history_policy") != "STORE_CONTIGUOUS_OBSERVED_PIONEX_ROWS_WITH_EXPLICIT_COVERAGE_STATUS":
        raise ValidationMaterializationRejected("missing-history policy changed")
    if stamp(str(materialization.get("not_before_utc"))) >= stamp(str(materialization.get("stop_exclusive_utc"))):
        raise ValidationMaterializationRejected("execution window is empty")

    storage = config.get("storage")
    if not isinstance(storage, Mapping):
        raise ValidationMaterializationRejected("storage contract missing")
    if storage.get("namespace") != "market-data/pionex/validation-dataset-v0.1":
        raise ValidationMaterializationRejected("storage namespace changed")
    if storage.get("format") != "PARQUET_PLUS_JSON_RECEIPT_PER_SYMBOL_INTERVAL":
        raise ValidationMaterializationRejected("storage format changed")
    if storage.get("free_only_hard_stop_bytes") != 8_000_000_000:
        raise ValidationMaterializationRejected("FREE-ONLY hard stop changed")
    if storage.get("maximum_planned_run_bytes") != 2_147_483_648:
        raise ValidationMaterializationRejected("planned run bytes changed")
    if storage.get("raw_provider_payloads_persisted") is not False or storage.get("pages_projection") is not False:
        raise ValidationMaterializationRejected("raw/provider projection boundary widened")
    if storage.get("sha256_readback_required") is not True:
        raise ValidationMaterializationRejected("SHA-256 readback requirement weakened")

    expected_authority = {
        "account_data": False,
        "binance_relabel_as_pionex": False,
        "core100_pionex_training": False,
        "formal_backtest_admission": False,
        "live_trading": False,
        "model_promotion": False,
        "private_api": False,
        "public_pionex_kline_reads": True,
        "r2_headroom_reads": True,
        "r2_validation_dataset_writes": True,
        "real_money_orders": False,
        "replacement_holdout_access": False,
        "source_switch": False,
        "trade_plan": False,
        "training": False,
    }
    if config.get("authority") != expected_authority:
        raise ValidationMaterializationRejected("authority widened or changed")


def require_execution_window(config: Mapping[str, Any], *, now_ms: int) -> None:
    materialization = config["materialization"]
    if not stamp(str(materialization["not_before_utc"])) <= now_ms < stamp(str(materialization["stop_exclusive_utc"])):
        raise ValidationMaterializationRejected("execution window closed")


def asset_class_for_symbol(config: Mapping[str, Any], symbol: str) -> str:
    explicit = config["classification_overlay"]["explicit_classes"]
    for asset_class, symbols in explicit.items():
        if symbol in symbols:
            return str(asset_class)
    return str(config["classification_overlay"]["default_class"])


def profile_for_symbol(config: Mapping[str, Any], symbol: str) -> str:
    for profile in ("FULL_INTRADAY", "MULTISCALE_RESEARCH", "BREADTH_BACKGROUND"):
        if symbol in config["history_profiles"][profile]["symbols"]:
            return profile
    raise ValidationMaterializationRejected(f"symbol outside frozen 197-market universe: {symbol}")


def _last_aligned_candle_before(cutoff: int, interval: str) -> int:
    step = INTERVAL_MS[interval]
    offset = INTERVAL_ALIGNMENT_OFFSET_MS.get(interval, 0)
    if cutoff <= offset:
        raise ValidationMaterializationRejected("cutoff precedes interval alignment origin")
    return offset + ((cutoff - step - offset) // step) * step


def _validate_page(
    page: Sequence[Candle], *, interval: str, cursor: int, limit: int, seen: set[int]
) -> None:
    if len(page) > limit:
        raise ValidationMaterializationRejected("provider returned more rows than requested")
    if not page:
        return
    step = INTERVAL_MS[interval]
    if any(candle.time_ms > cursor for candle in page):
        raise ValidationMaterializationRejected("provider returned candle after requested cursor")
    if any(candle.time_ms in seen for candle in page):
        raise ValidationMaterializationRejected("provider repeated candle across pages")
    audit = audit_candles(tuple(page), interval)
    if not audit.ok:
        raise ValidationMaterializationRejected("provider page is missing, duplicate, unordered, misaligned or invalid")
    if page[-1].time_ms != cursor:
        raise ValidationMaterializationRejected("provider page does not end at requested cursor")
    expected_first = cursor - (len(page) - 1) * step
    if page[0].time_ms != expected_first:
        raise ValidationMaterializationRejected("provider page endpoints are not contiguous")


@dataclass(frozen=True, slots=True)
class PartitionResult:
    symbol: str
    interval: str
    coverage_status: str
    candles: tuple[Candle, ...]
    requests: int
    provider_error_type: str | None = None
    provider_http_status: int | None = None

    def receipt_fields(self) -> dict[str, object]:
        candles = self.candles
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "coverage_status": self.coverage_status,
            "rows": len(candles),
            "first_time_ms": candles[0].time_ms if candles else None,
            "last_time_ms": candles[-1].time_ms if candles else None,
            "first_utc": iso_utc(candles[0].time_ms) if candles else None,
            "last_utc": iso_utc(candles[-1].time_ms) if candles else None,
            "requests": self.requests,
            "provider_error_type": self.provider_error_type,
            "provider_http_status": self.provider_http_status,
            "complete_provider_history_claimed": self.coverage_status == "PROVIDER_EARLIEST_REACHED",
        }


def _safe_error(exc: Exception) -> tuple[str, int | None]:
    from urllib.error import HTTPError
    return type(exc).__name__, exc.code if isinstance(exc, HTTPError) else None


def collect_partition(
    config: Mapping[str, Any],
    client: KlineClient,
    *,
    symbol: str,
    interval: str,
    progress: dict[str, int],
    clock: Callable[[], int],
) -> PartitionResult:
    validate_config(config)
    profile = profile_for_symbol(config, symbol)
    if interval not in config["history_profiles"][profile]["intervals"]:
        raise ValidationMaterializationRejected("interval outside symbol history profile")
    require_execution_window(config, now_ms=clock())

    cutoff = stamp(str(config["cutoff_exclusive_utc"]))
    step = INTERVAL_MS[interval]
    cursor = _last_aligned_candle_before(cutoff, interval)
    page_limit = int(config["materialization"]["page_limit"])
    max_records = int(config["materialization"]["maximum_records_per_symbol_interval"])
    max_requests = int(config["materialization"]["maximum_provider_requests"])
    seen: dict[int, Candle] = {}
    partition_requests = 0
    coverage_status: str | None = None
    error_type: str | None = None
    error_status: int | None = None

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
                    diagnostics={"symbol": symbol, "interval": interval, "stage": "page", "error_type": type(exc).__name__},
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
        _validate_page(page, interval=interval, cursor=cursor, limit=limit, seen=set(seen))
        if not page:
            if not seen:
                raise ValidationMaterializationRejected("provider returned no data at validation cutoff")
            coverage_status = "PROVIDER_EARLIEST_REACHED"
            break
        for candle in page:
            seen[candle.time_ms] = candle

        if len(page) < limit:
            probe_cursor = page[0].time_ms - step
            require_execution_window(config, now_ms=clock())
            if progress["requests"] >= max_requests:
                raise ValidationMaterializationRejected("global provider request budget exhausted before boundary probe")
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
    if candles[-1].time_ms != _last_aligned_candle_before(cutoff, interval):
        raise ValidationMaterializationRejected("partition does not end at frozen validation cutoff")
    if coverage_status is None:
        coverage_status = "BOUNDED_RECORD_CAP_REACHED" if len(candles) >= max_records else "PARTIAL_UNCLASSIFIED"
    return PartitionResult(
        symbol=symbol,
        interval=interval,
        coverage_status=coverage_status,
        candles=candles,
        requests=partition_requests,
        provider_error_type=error_type,
        provider_http_status=error_status,
    )


def iter_partitions(config: Mapping[str, Any]):
    validate_config(config)
    for profile in ("FULL_INTRADAY", "MULTISCALE_RESEARCH", "BREADTH_BACKGROUND"):
        for symbol in config["history_profiles"][profile]["symbols"]:
            for interval in config["history_profiles"][profile]["intervals"]:
                yield profile, symbol, interval


def partition_count(config: Mapping[str, Any]) -> int:
    return sum(1 for _ in iter_partitions(config))


def validate_run_id(run_id: str) -> None:
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValidationMaterializationRejected("fresh GitHub main run attempt 1 id required")
