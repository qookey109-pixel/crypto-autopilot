#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from crypto_autopilot.binance_vision import BinanceVisionArchiveKey, ingest_kline_archive
from crypto_autopilot.detailed_history import (
    DetailedHistoryAuthorityError,
    DetailedMarketCoverage,
    build_catalog,
    build_market_coverage,
    build_shard_plan,
    canonical_json_bytes,
    load_authority_pair,
    month_range,
    months_from_interval_keys,
    parse_bucket_listing,
    require_execution_window,
    sha256_bytes,
    symbols_from_root_prefixes,
    validate_catalog,
)
from crypto_autopilot.ephemeral_storage import require_ephemeral_output
from crypto_autopilot.online_r2_training import current_bucket_bytes
from crypto_autopilot.storage.parquet import candles_to_parquet, parquet_to_candles
from crypto_autopilot.storage.r2 import R2Store


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config/binance_usdm_detailed_history_v0_1_1.json"
DEFAULT_AUTHORITY = (
    ROOT
    / "research/receipts/2026-08-24-binance-usdm-detailed-history-v0-1-1-bounded-authority.json"
)
BUCKET_LIST_URL = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
OBJECT_BASE_URL = "https://data.binance.vision/"
SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9._-]{1,96}$")


def required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"required GitHub Actions R2 secret is missing: {name}")
    return value


def create_store() -> R2Store:
    return R2Store(
        account_id=required("CLOUDFLARE_ACCOUNT_ID"),
        bucket=required("R2_BUCKET_NAME"),
        access_key_id=required("R2_ACCESS_KEY_ID"),
        secret_access_key=required("R2_SECRET_ACCESS_KEY"),
    )


def download(
    url: str,
    *,
    timeout_seconds: float,
    retries: int,
    user_agent: str = "qookey-crypto-autopilot-detailed-history/0.1",
) -> bytes:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = Request(url, headers={"User-Agent": user_agent})
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
                return response.read()
        except HTTPError as exc:
            last_error = exc
            if exc.code not in {408, 425, 429, 500, 502, 503, 504}:
                break
        except (URLError, TimeoutError) as exc:
            last_error = exc
        if attempt + 1 < retries:
            time.sleep(float(attempt + 1))
    raise RuntimeError(f"public Binance Vision download failed for {url}: {last_error}") from last_error


def list_bucket_keys(
    prefix: str,
    *,
    delimiter: str | None,
    timeout_seconds: float,
    retries: int,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    marker: str | None = None
    prefixes: list[str] = []
    keys: list[str] = []
    while True:
        params = {"prefix": prefix}
        if delimiter is not None:
            params["delimiter"] = delimiter
        if marker is not None:
            params["marker"] = marker
        payload = download(
            f"{BUCKET_LIST_URL}?{urlencode(params)}",
            timeout_seconds=timeout_seconds,
            retries=retries,
        )
        listing = parse_bucket_listing(payload, expected_prefix=prefix)
        prefixes.extend(listing.common_prefixes)
        keys.extend(listing.keys)
        if not listing.is_truncated:
            break
        marker = listing.next_marker
    return tuple(sorted(set(prefixes))), tuple(sorted(set(keys)))


def discover_one_symbol(
    symbol: str,
    *,
    requested_months: tuple[str, ...],
    tokenized_stock_roots: tuple[str, ...],
    other_roots: tuple[str, ...],
    timeout_seconds: float,
    retries: int,
) -> DetailedMarketCoverage | None:
    months_by_interval: dict[str, tuple[str, ...]] = {}
    for interval in ("15m", "1h", "4h"):
        prefix = f"data/futures/um/monthly/klines/{symbol}/{interval}/"
        _prefixes, keys = list_bucket_keys(
            prefix,
            delimiter=None,
            timeout_seconds=timeout_seconds,
            retries=retries,
        )
        months_by_interval[interval] = months_from_interval_keys(
            keys, symbol=symbol, interval=interval
        )
    return build_market_coverage(
        symbol=symbol,
        months_by_interval=months_by_interval,
        requested_months=requested_months,
        tokenized_stock_roots=tokenized_stock_roots,
        other_roots=other_roots,
    )


def discover_universe(config: dict[str, Any], *, retrieved_at_utc: str) -> dict[str, Any]:
    execution = config["execution"]
    selection = config["selection"]
    scope = config["scope"]
    root = "data/futures/um/monthly/klines/"
    prefixes, _keys = list_bucket_keys(
        root,
        delimiter="/",
        timeout_seconds=float(execution["timeout_seconds"]),
        retries=int(execution["download_retries"]),
    )
    symbols = symbols_from_root_prefixes(prefixes)
    if len(symbols) < int(scope["target_market_count"]):
        raise DetailedHistoryAuthorityError(
            f"Binance Vision root listed only {len(symbols)} eligible USDT symbols"
        )
    requested_months = month_range(scope["source_month_start"], scope["source_month_end"])
    records: list[DetailedMarketCoverage] = []
    with ThreadPoolExecutor(max_workers=int(execution["directory_workers"])) as executor:
        futures = {
            executor.submit(
                discover_one_symbol,
                symbol,
                requested_months=requested_months,
                tokenized_stock_roots=tuple(selection["tokenized_stock_roots"]),
                other_roots=tuple(selection["other_roots"]),
                timeout_seconds=float(execution["timeout_seconds"]),
                retries=int(execution["download_retries"]),
            ): symbol
            for symbol in symbols
        }
        for future in as_completed(futures):
            record = future.result()
            if record is not None:
                records.append(record)
    records.sort(key=lambda item: item.symbol)
    return build_catalog(records, config=config, retrieved_at_utc=retrieved_at_utc)


def _ensure_reservation_headroom(store: R2Store, config: dict[str, Any], *, planned: int) -> int:
    current = current_bucket_bytes(store)
    hard_stop = int(config["storage"]["free_only_hard_stop_bytes"])
    if current + planned > hard_stop:
        raise DetailedHistoryAuthorityError(
            "R2 FREE-ONLY headroom gate blocked before provider access"
        )
    return current


def _put_immutable(
    store: R2Store,
    *,
    key: str,
    payload: bytes,
    content_type: str,
    metadata: dict[str, str],
) -> dict[str, Any]:
    existing = store.get_bytes_if_exists(key)
    if existing is not None and existing != payload:
        raise DetailedHistoryAuthorityError(f"immutable detailed-history object conflict: {key}")
    if existing is None:
        receipt = store.put_bytes(
            key,
            payload,
            content_type=content_type,
            metadata=metadata,
        )
        action = "UPLOAD"
        record = asdict(receipt)
    else:
        action = "VERIFY_EXISTING"
        record = {
            "bucket": store.bucket,
            "key": key,
            "bytes": len(existing),
            "sha256": hashlib.sha256(existing).hexdigest(),
            "etag": None,
        }
    restored = store.get_bytes_verified(key, expected_sha256=str(record["sha256"]))
    if restored != payload:
        raise DetailedHistoryAuthorityError(f"R2 exact-byte round trip mismatch: {key}")
    return {"action": action, **record}


def publish_catalog(
    store: R2Store,
    *,
    config: dict[str, Any],
    catalog: dict[str, Any],
    run_id: str,
    generated_at_utc: str,
) -> dict[str, Any]:
    catalog_payload = canonical_json_bytes(catalog)
    storage = config["storage"]
    catalog_key = f"{storage['catalog_runs_namespace'].rstrip('/')}/run={run_id}/catalog.json"
    manifest = {
        "schema": "binance-usdm-detailed-history-catalog-manifest-v0.1",
        "status": "PASS",
        "provider": "binance_usdm",
        "run_id": run_id,
        "generated_at_utc": generated_at_utc,
        "catalog_key": catalog_key,
        "catalog_sha256": sha256_bytes(catalog_payload),
        "catalog_bytes": len(catalog_payload),
        "selected_market_count": catalog["selected_market_count"],
        "holdout_accessed": False,
    }
    manifest_payload = canonical_json_bytes(manifest)
    manifest_key = f"{storage['catalog_runs_namespace'].rstrip('/')}/run={run_id}/manifest.json"
    latest = {
        "schema": "binance-usdm-detailed-history-catalog-latest-v0.1",
        "provider": "binance_usdm",
        "run_id": run_id,
        "generated_at_utc": generated_at_utc,
        "catalog_key": catalog_key,
        "catalog_sha256": sha256_bytes(catalog_payload),
        "manifest_key": manifest_key,
        "manifest_sha256": sha256_bytes(manifest_payload),
    }
    latest_payload = canonical_json_bytes(latest)
    current = current_bucket_bytes(store)
    planned = len(catalog_payload) + len(manifest_payload) + len(latest_payload)
    if current + planned > int(storage["free_only_hard_stop_bytes"]):
        raise DetailedHistoryAuthorityError("R2 headroom blocked catalog publication")
    objects = [
        _put_immutable(
            store,
            key=catalog_key,
            payload=catalog_payload,
            content_type="application/json",
            metadata={"provider": "binance_usdm", "role": "detailed-catalog", "version": "v0.1"},
        ),
        _put_immutable(
            store,
            key=manifest_key,
            payload=manifest_payload,
            content_type="application/json",
            metadata={"provider": "binance_usdm", "role": "detailed-catalog-manifest", "version": "v0.1"},
        ),
    ]
    pointer = store.put_bytes(
        storage["catalog_latest_pointer_key"],
        latest_payload,
        content_type="application/json",
        metadata={"provider": "binance_usdm", "role": "detailed-catalog-latest", "version": "v0.1"},
    )
    restored = store.get_bytes_verified(
        storage["catalog_latest_pointer_key"], expected_sha256=pointer.sha256
    )
    if restored != latest_payload:
        raise DetailedHistoryAuthorityError("catalog latest pointer round trip mismatch")
    return {
        "status": "PASS",
        "stage": "BINANCE_USDM_DETAILED_HISTORY_CATALOG_PUBLISHED_V0_1",
        "catalog_key": catalog_key,
        "catalog_sha256": sha256_bytes(catalog_payload),
        "selected_market_count": catalog["selected_market_count"],
        "objects": objects,
        "latest_pointer_written_last": True,
    }


def load_published_catalog(
    store: R2Store, config: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    key = config["storage"]["catalog_latest_pointer_key"]
    latest_payload = store.get_bytes_if_exists(key)
    if latest_payload is None:
        return None
    latest = json.loads(latest_payload)
    if (
        latest.get("schema") != "binance-usdm-detailed-history-catalog-latest-v0.1"
        or latest.get("provider") != "binance_usdm"
    ):
        raise DetailedHistoryAuthorityError("catalog latest pointer identity mismatch")
    catalog_key = str(latest.get("catalog_key") or "")
    expected_prefix = config["storage"]["catalog_runs_namespace"].rstrip("/") + "/run="
    if not catalog_key.startswith(expected_prefix):
        raise DetailedHistoryAuthorityError("catalog key escaped its versioned namespace")
    catalog_payload = store.get_bytes_verified(
        catalog_key, expected_sha256=str(latest["catalog_sha256"])
    )
    catalog = json.loads(catalog_payload)
    validate_catalog(catalog, config=config)
    return latest, catalog


def _initial_state(latest: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "binance-usdm-detailed-history-backfill-state-v0.1",
        "status": "IN_PROGRESS",
        "provider": "binance_usdm",
        "catalog_key": latest["catalog_key"],
        "catalog_sha256": latest["catalog_sha256"],
        "shard_count": catalog["shard_count"],
        "completed_shards": [],
        "total_rows": 0,
        "total_parquet_bytes": 0,
        "total_partition_objects": 0,
        "contains_secrets": False,
        "holdout_accessed": False,
    }


def load_state(
    store: R2Store,
    *,
    config: dict[str, Any],
    latest: dict[str, Any],
    catalog: dict[str, Any],
) -> dict[str, Any]:
    key = config["storage"]["backfill_state_key"]
    payload = store.get_bytes_if_exists(key)
    if payload is None:
        return _initial_state(latest, catalog)
    state = json.loads(payload)
    if (
        state.get("schema") != "binance-usdm-detailed-history-backfill-state-v0.1"
        or state.get("provider") != "binance_usdm"
        or state.get("catalog_key") != latest["catalog_key"]
        or state.get("catalog_sha256") != latest["catalog_sha256"]
        or int(state.get("shard_count") or 0) != int(catalog["shard_count"])
        or state.get("contains_secrets") is not False
        or state.get("holdout_accessed") is not False
    ):
        raise DetailedHistoryAuthorityError("backfill state contract mismatch")
    completed = state.get("completed_shards")
    if not isinstance(completed, list):
        raise DetailedHistoryAuthorityError("backfill state completed shards are missing")
    indexes = [int(item["shard_index"]) for item in completed if isinstance(item, dict)]
    if len(indexes) != len(set(indexes)):
        raise DetailedHistoryAuthorityError("backfill state contains duplicate completed shards")
    return state


def fetch_partition(partition: Any, *, timeout_seconds: float, retries: int) -> dict[str, Any]:
    key = BinanceVisionArchiveKey(
        "klines",
        "monthly",
        partition.symbol,
        partition.interval,
        partition.period,
    )
    archive_bytes = download(
        key.url, timeout_seconds=timeout_seconds, retries=retries
    )
    checksum = download(
        key.checksum_url, timeout_seconds=timeout_seconds, retries=retries
    )
    archive = ingest_kline_archive(
        key, archive_bytes=archive_bytes, checksum_payload=checksum
    )
    parquet = candles_to_parquet(archive.candles)
    return {
        "partition": partition,
        "archive": archive,
        "parquet": parquet,
    }


def materialize_shard(
    store: R2Store,
    *,
    config: dict[str, Any],
    latest: dict[str, Any],
    catalog: dict[str, Any],
    state: dict[str, Any],
    shard_index: int,
    run_id: str,
    generated_at_utc: str,
) -> dict[str, Any]:
    completed_indexes = {
        int(item["shard_index"])
        for item in state["completed_shards"]
        if isinstance(item, dict)
    }
    if shard_index in completed_indexes:
        return {
            "status": "SKIPPED",
            "stage": "DETAILED_HISTORY_SHARD_ALREADY_COMPLETE",
            "shard_index": shard_index,
        }
    storage = config["storage"]
    _ensure_reservation_headroom(
        store, config, planned=int(storage["maximum_planned_shard_bytes"])
    )
    plans = build_shard_plan(catalog, shard_index=shard_index)
    materialized: list[dict[str, Any]] = []
    execution = config["execution"]
    with ThreadPoolExecutor(max_workers=int(execution["download_workers"])) as executor:
        futures = {
            executor.submit(
                fetch_partition,
                plan,
                timeout_seconds=float(execution["timeout_seconds"]),
                retries=int(execution["download_retries"]),
            ): plan
            for plan in plans
        }
        for future in as_completed(futures):
            materialized.append(future.result())
    materialized.sort(
        key=lambda item: (
            item["partition"].symbol,
            item["partition"].interval,
            item["partition"].period,
        )
    )

    planned_missing_bytes = 0
    object_records: list[dict[str, Any]] = []
    for item in materialized:
        partition = item["partition"]
        archive = item["archive"]
        parquet = item["parquet"]
        existing = store.get_bytes_if_exists(partition.r2_key)
        if existing is not None:
            if parquet_to_candles(existing) != list(archive.candles):
                raise DetailedHistoryAuthorityError(
                    f"existing detailed-history candles conflict: {partition.r2_key}"
                )
            action = "VERIFY_EXISTING"
            existing_sha = hashlib.sha256(existing).hexdigest()
            existing_bytes = len(existing)
        else:
            action = "UPLOAD"
            existing_sha = parquet.sha256
            existing_bytes = len(parquet.payload)
            planned_missing_bytes += len(parquet.payload)
        object_records.append(
            {
                "provider": "binance_usdm",
                "delivery": "binance_vision",
                "symbol": partition.symbol,
                "asset_class": partition.asset_class,
                "interval": partition.interval,
                "period": partition.period,
                "source_url": archive.key.url,
                "source_archive_sha256": archive.receipt.archive_sha256,
                "source_rows": archive.receipt.row_count,
                "first_time_ms": archive.receipt.first_time_ms,
                "last_time_ms": archive.receipt.last_time_ms,
                "audit_ok": archive.receipt.audit_ok,
                "r2_key": partition.r2_key,
                "r2_bytes": existing_bytes,
                "r2_sha256": existing_sha,
                "r2_action": action,
            }
        )

    current = current_bucket_bytes(store)
    if current + planned_missing_bytes + 5_000_000 > int(storage["free_only_hard_stop_bytes"]):
        raise DetailedHistoryAuthorityError("R2 exact shard headroom gate blocked before write")

    for item, record in zip(materialized, object_records):
        if record["r2_action"] == "VERIFY_EXISTING":
            restored = store.get_bytes_verified(
                record["r2_key"], expected_sha256=record["r2_sha256"]
            )
            if parquet_to_candles(restored) != list(item["archive"].candles):
                raise DetailedHistoryAuthorityError("existing R2 candle equality verification failed")
            continue
        uploaded = store.put_bytes(
            record["r2_key"],
            item["parquet"].payload,
            content_type="application/vnd.apache.parquet",
            metadata={
                "provider": "binance_usdm",
                "delivery": "binance_vision",
                "version": "detailed-v0.1",
                "source-sha256": record["source_archive_sha256"],
            },
        )
        if uploaded.sha256 != record["r2_sha256"]:
            raise DetailedHistoryAuthorityError("uploaded detailed-history SHA mismatch")
        restored = store.get_bytes_verified(
            record["r2_key"], expected_sha256=uploaded.sha256
        )
        if restored != item["parquet"].payload:
            raise DetailedHistoryAuthorityError("uploaded detailed-history round trip mismatch")

    receipt = {
        "schema": "binance-usdm-detailed-history-shard-receipt-v0.1",
        "status": "PASS",
        "stage": "BINANCE_USDM_DETAILED_HISTORY_SHARD_PUBLISHED_V0_1",
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "run_id": run_id,
        "generated_at_utc": generated_at_utc,
        "catalog_key": latest["catalog_key"],
        "catalog_sha256": latest["catalog_sha256"],
        "shard_index": shard_index,
        "partition_object_count": len(object_records),
        "row_count": sum(int(item["source_rows"]) for item in object_records),
        "parquet_bytes": sum(int(item["r2_bytes"]) for item in object_records),
        "uploaded_object_count": sum(item["r2_action"] == "UPLOAD" for item in object_records),
        "verified_existing_object_count": sum(
            item["r2_action"] == "VERIFY_EXISTING" for item in object_records
        ),
        "objects": object_records,
        "authority": {
            "holdout_accessed": False,
            "historical_universe_membership_authorized": False,
            "pionex_native_relabel_authorized": False,
            "source_switch_authorized": False,
            "automatic_model_promotion_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }
    receipt_payload = canonical_json_bytes(receipt)
    receipt_key = (
        f"{storage['shard_receipt_namespace'].rstrip('/')}/"
        f"shard={shard_index:03d}/run={run_id}/receipt.json"
    )
    receipt_record = _put_immutable(
        store,
        key=receipt_key,
        payload=receipt_payload,
        content_type="application/json",
        metadata={"provider": "binance_usdm", "role": "detailed-shard-receipt", "version": "v0.1"},
    )

    next_state = dict(state)
    completed = list(state["completed_shards"])
    completed.append(
        {
            "shard_index": shard_index,
            "receipt_key": receipt_key,
            "receipt_sha256": sha256_bytes(receipt_payload),
            "partition_object_count": receipt["partition_object_count"],
            "row_count": receipt["row_count"],
            "parquet_bytes": receipt["parquet_bytes"],
        }
    )
    completed.sort(key=lambda item: int(item["shard_index"]))
    next_state["completed_shards"] = completed
    next_state["total_rows"] = sum(int(item["row_count"]) for item in completed)
    next_state["total_parquet_bytes"] = sum(int(item["parquet_bytes"]) for item in completed)
    next_state["total_partition_objects"] = sum(
        int(item["partition_object_count"]) for item in completed
    )
    next_state["updated_at_utc"] = generated_at_utc
    next_state["status"] = (
        "COMPLETE" if len(completed) == int(state["shard_count"]) else "IN_PROGRESS"
    )
    state_payload = canonical_json_bytes(next_state)
    state_receipt = store.put_bytes(
        storage["backfill_state_key"],
        state_payload,
        content_type="application/json",
        metadata={"provider": "binance_usdm", "role": "detailed-backfill-state", "version": "v0.1"},
    )
    restored_state = store.get_bytes_verified(
        storage["backfill_state_key"], expected_sha256=state_receipt.sha256
    )
    if restored_state != state_payload:
        raise DetailedHistoryAuthorityError("backfill state round trip mismatch")
    return {
        "status": "PASS",
        "stage": receipt["stage"],
        "shard_index": shard_index,
        "shards_complete": len(completed),
        "shard_count": state["shard_count"],
        "dataset_status": next_state["status"],
        "partition_object_count": receipt["partition_object_count"],
        "row_count": receipt["row_count"],
        "parquet_bytes": receipt["parquet_bytes"],
        "receipt": receipt_record,
        "state_pointer_written_last": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Discover and resumably materialize the governed Binance USD-M detailed history."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument("--mode", choices=("auto", "discover", "backfill"), default="auto")
    parser.add_argument("--shard-index", type=int)
    parser.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID") or "local")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--now-utc")
    args = parser.parse_args()
    output = require_ephemeral_output(args.output)
    if not SAFE_RUN_ID.fullmatch(args.run_id):
        raise ValueError("run id must be a safe 1-96 character object-key component")
    config, _authority, _config_bytes = load_authority_pair(args.config, args.authority)
    observed = (
        datetime.fromisoformat(args.now_utc.replace("Z", "+00:00"))
        if args.now_utc
        else datetime.now(UTC)
    )
    generated_at = observed.astimezone(UTC).isoformat().replace("+00:00", "Z")
    try:
        require_execution_window(config, observed_at=observed, operation="backfill")
    except DetailedHistoryAuthorityError as exc:
        reason = str(exc)
        if not any(
            marker in reason
            for marker in (
                "blocked until the V0.10 window has ended",
                "backfill authority expired before provider or R2 access",
            )
        ):
            raise
        report = {
            "status": "SKIPPED",
            "stage": (
                "DETAILED_HISTORY_AUTHORITY_EXPIRED"
                if "expired" in reason
                else "DETAILED_HISTORY_NOT_BEFORE_GUARD"
            ),
            "mode": args.mode,
            "observed_at_utc": generated_at,
            "reason": reason,
            "provider_requests_performed": 0,
            "r2_access_performed": False,
            "authority": {
                "holdout_accessed": False,
                "pionex_native_relabel_authorized": False,
                "source_switch_authorized": False,
                "automatic_model_promotion_authorized": False,
                "real_money_order_authorized": False,
                "live_trading_authorized": False,
            },
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(canonical_json_bytes(report))
        print(json.dumps(report, sort_keys=True))
        return 0

    store = create_store()
    published = load_published_catalog(store, config)
    mode = args.mode
    if mode == "auto":
        mode = "discover" if published is None else "backfill"

    if mode == "discover":
        if published is not None:
            result = {
                "status": "SKIPPED",
                "stage": "DETAILED_HISTORY_CATALOG_ALREADY_PUBLISHED",
                "catalog_key": published[0]["catalog_key"],
            }
        else:
            _ensure_reservation_headroom(
                store,
                config,
                planned=int(config["storage"]["maximum_projected_dataset_bytes"]),
            )
            catalog = discover_universe(config, retrieved_at_utc=generated_at)
            result = publish_catalog(
                store,
                config=config,
                catalog=catalog,
                run_id=args.run_id,
                generated_at_utc=generated_at,
            )
    else:
        if published is None:
            raise DetailedHistoryAuthorityError("publish a governed catalog before backfill")
        latest, catalog = published
        state = load_state(
            store, config=config, latest=latest, catalog=catalog
        )
        if state["status"] == "COMPLETE":
            result = {
                "status": "SKIPPED",
                "stage": "DETAILED_HISTORY_DATASET_ALREADY_COMPLETE",
                "shards_complete": len(state["completed_shards"]),
                "shard_count": state["shard_count"],
            }
        else:
            completed = {
                int(item["shard_index"])
                for item in state["completed_shards"]
                if isinstance(item, dict)
            }
            shard_index = (
                args.shard_index
                if args.shard_index is not None
                else next(index for index in range(int(state["shard_count"])) if index not in completed)
            )
            result = materialize_shard(
                store,
                config=config,
                latest=latest,
                catalog=catalog,
                state=state,
                shard_index=shard_index,
                run_id=args.run_id,
                generated_at_utc=generated_at,
            )

    report = {
        **result,
        "mode": mode,
        "observed_at_utc": generated_at,
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "authority": {
            "holdout_accessed": False,
            "pionex_native_relabel_authorized": False,
            "source_switch_authorized": False,
            "automatic_model_promotion_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes(report))
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
