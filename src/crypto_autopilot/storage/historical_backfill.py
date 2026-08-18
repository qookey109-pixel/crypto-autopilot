from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

from crypto_autopilot.historical import KlineClient, audit_candles, backfill_klines
from crypto_autopilot.models import Candle
from crypto_autopilot.storage.layout import (
    HistoricalObjectKey,
    historical_checkpoint_key,
    historical_partition_receipt_key,
    historical_staging_key,
)
from crypto_autopilot.storage.parquet import candles_to_parquet, parquet_to_candles
from crypto_autopilot.storage.r2 import R2ObjectReceipt


class BackfillByteStore(Protocol):
    def put_bytes(
        self,
        key: str,
        payload: bytes,
        *,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> R2ObjectReceipt: ...

    def get_bytes_verified(self, key: str, *, expected_sha256: str) -> bytes: ...

    def get_bytes_if_exists(self, key: str) -> bytes | None: ...


class PlannedInterruption(RuntimeError):
    def __init__(self, message: str, *, summary: dict[str, Any]) -> None:
        super().__init__(message)
        self.summary = summary


class CanonicalConflictError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class HistoricalPartition:
    symbol: str
    interval: str
    year: int
    month: int | None
    requested_start_ms: int
    requested_end_ms: int

    @property
    def canonical_key(self) -> str:
        return HistoricalObjectKey(
            exchange="pionex",
            market_type="perp",
            symbol=self.symbol,
            interval=self.interval,
            year=self.year,
            month=self.month,
        ).build()

    @property
    def checkpoint_key(self) -> str:
        return historical_checkpoint_key(
            exchange="pionex",
            market_type="perp",
            symbol=self.symbol,
            interval=self.interval,
            year=self.year,
            month=self.month,
        )

    @property
    def staging_key(self) -> str:
        return historical_staging_key(
            exchange="pionex",
            market_type="perp",
            symbol=self.symbol,
            interval=self.interval,
            year=self.year,
            month=self.month,
        )

    @property
    def receipt_key(self) -> str:
        return historical_partition_receipt_key(
            exchange="pionex",
            market_type="perp",
            symbol=self.symbol,
            interval=self.interval,
            year=self.year,
            month=self.month,
        )

    @property
    def identity(self) -> str:
        partition = f"{self.year:04d}-{self.month:02d}" if self.month else f"{self.year:04d}"
        return f"pionex:perp:{self.symbol}:{self.interval}:{partition}"


def _to_ms(value: datetime) -> int:
    return int(value.astimezone(timezone.utc).timestamp() * 1000)


def partition_specs_for_year(
    symbols: list[str] | tuple[str, ...],
    year: int,
    *,
    intervals: tuple[str, ...] = ("15M", "60M", "4H"),
) -> tuple[HistoricalPartition, ...]:
    if year < 2009 or year > 2100:
        raise ValueError("year outside supported range")
    unsupported = set(intervals) - {"15M", "60M", "4H"}
    if unsupported:
        raise ValueError(f"Unsupported pilot intervals: {sorted(unsupported)}")

    partitions: list[HistoricalPartition] = []
    for symbol in symbols:
        clean_symbol = symbol.strip()
        if not clean_symbol:
            raise ValueError("symbol cannot be empty")
        for interval in intervals:
            if interval == "15M":
                for month in range(1, 13):
                    start = datetime(year, month, 1, tzinfo=timezone.utc)
                    if month == 12:
                        next_start = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
                    else:
                        next_start = datetime(year, month + 1, 1, tzinfo=timezone.utc)
                    partitions.append(
                        HistoricalPartition(
                            symbol=clean_symbol,
                            interval=interval,
                            year=year,
                            month=month,
                            requested_start_ms=_to_ms(start),
                            requested_end_ms=_to_ms(next_start) - 1,
                        )
                    )
            else:
                start = datetime(year, 1, 1, tzinfo=timezone.utc)
                next_start = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
                partitions.append(
                    HistoricalPartition(
                        symbol=clean_symbol,
                        interval=interval,
                        year=year,
                        month=None,
                        requested_start_ms=_to_ms(start),
                        requested_end_ms=_to_ms(next_start) - 1,
                    )
                )
    return tuple(partitions)


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _read_json_optional(store: BackfillByteStore, key: str) -> dict[str, Any] | None:
    payload = store.get_bytes_if_exists(key)
    if payload is None:
        return None
    decoded = json.loads(payload.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError(f"Expected JSON object at {key}")
    return decoded


def _put_json(
    store: BackfillByteStore,
    key: str,
    payload: dict[str, Any],
    *,
    metadata: dict[str, str] | None = None,
) -> R2ObjectReceipt:
    return store.put_bytes(
        key,
        _canonical_json(payload),
        content_type="application/json",
        metadata=metadata,
    )


def _now_iso(now_fn: Callable[[], datetime]) -> str:
    now = now_fn()
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc).isoformat()


def _checkpoint_payload(
    partition: HistoricalPartition,
    *,
    status: str,
    storage_run_id: str,
    now_fn: Callable[[], datetime],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "provider": "pionex",
        "market_type": "perp",
        "identity": partition.identity,
        "symbol": partition.symbol,
        "interval": partition.interval,
        "year": partition.year,
        "month": partition.month,
        "requested_start_ms": partition.requested_start_ms,
        "requested_end_ms": partition.requested_end_ms,
        "status": status,
        "storage_run_id": storage_run_id,
        "updated_at": _now_iso(now_fn),
    }
    if extra:
        payload.update(extra)
    return payload


def _write_checkpoint(
    store: BackfillByteStore,
    partition: HistoricalPartition,
    *,
    status: str,
    storage_run_id: str,
    now_fn: Callable[[], datetime],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _checkpoint_payload(
        partition,
        status=status,
        storage_run_id=storage_run_id,
        now_fn=now_fn,
        extra=extra,
    )
    _put_json(
        store,
        partition.checkpoint_key,
        payload,
        metadata={"state": status.lower(), "identity": partition.identity},
    )
    return payload


def _verify_parquet_payload(
    payload: bytes,
    *,
    interval: str,
    expected_candles: tuple[Candle, ...] | None = None,
) -> tuple[Candle, ...]:
    restored = tuple(parquet_to_candles(payload))
    audit = audit_candles(restored, interval)
    if not audit.ok:
        raise RuntimeError(f"Parquet audit failed for interval {interval}")
    if expected_candles is not None and restored != expected_candles:
        raise RuntimeError("Parquet round-trip candle equality failed")
    return restored


def _verify_finalized_checkpoint(
    store: BackfillByteStore,
    partition: HistoricalPartition,
    checkpoint: dict[str, Any],
) -> None:
    if checkpoint.get("no_data"):
        receipt = checkpoint.get("receipt") or {}
        if receipt.get("key") and receipt.get("sha256"):
            store.get_bytes_verified(str(receipt["key"]), expected_sha256=str(receipt["sha256"]))
        return

    canonical = checkpoint.get("canonical") or {}
    key = str(canonical.get("key") or "")
    sha256 = str(canonical.get("sha256") or "")
    if key != partition.canonical_key or not sha256:
        raise ValueError(f"Invalid FINALIZED checkpoint for {partition.identity}")
    payload = store.get_bytes_verified(key, expected_sha256=sha256)
    restored = _verify_parquet_payload(payload, interval=partition.interval)
    expected_rows = int(canonical.get("rows", -1))
    if len(restored) != expected_rows:
        raise ValueError(f"FINALIZED row-count mismatch for {partition.identity}")

    receipt = checkpoint.get("receipt") or {}
    if receipt.get("key") and receipt.get("sha256"):
        store.get_bytes_verified(str(receipt["key"]), expected_sha256=str(receipt["sha256"]))


def _finalize_from_staged(
    *,
    store: BackfillByteStore,
    partition: HistoricalPartition,
    checkpoint: dict[str, Any],
    storage_run_id: str,
    now_fn: Callable[[], datetime],
) -> tuple[int, int]:
    staging = checkpoint.get("staging") or {}
    staging_key = str(staging.get("key") or "")
    staging_sha256 = str(staging.get("sha256") or "")
    if staging_key != partition.staging_key or not staging_sha256:
        raise ValueError(f"Invalid STAGED checkpoint for {partition.identity}")

    staging_payload = store.get_bytes_verified(staging_key, expected_sha256=staging_sha256)
    candles = _verify_parquet_payload(staging_payload, interval=partition.interval)
    if len(candles) != int(staging.get("rows", -1)):
        raise ValueError(f"STAGED row-count mismatch for {partition.identity}")

    existing_canonical = store.get_bytes_if_exists(partition.canonical_key)
    if existing_canonical is not None:
        existing_sha256 = hashlib.sha256(existing_canonical).hexdigest()
        if existing_sha256 != staging_sha256:
            raise CanonicalConflictError(
                f"Refusing to overwrite existing canonical object for {partition.identity}: "
                f"existing={existing_sha256} staged={staging_sha256}"
            )
        canonical_receipt = R2ObjectReceipt(
            bucket="existing",
            key=partition.canonical_key,
            bytes=len(existing_canonical),
            sha256=existing_sha256,
            etag=None,
        )
    else:
        canonical_receipt = store.put_bytes(
            partition.canonical_key,
            staging_payload,
            content_type="application/vnd.apache.parquet",
            metadata={
                "source": "pionex-public-futures",
                "symbol": partition.symbol,
                "interval": partition.interval,
                "rows": str(len(candles)),
                "audit-ok": "true",
            },
        )

    canonical_payload = store.get_bytes_verified(
        partition.canonical_key,
        expected_sha256=canonical_receipt.sha256,
    )
    _verify_parquet_payload(
        canonical_payload,
        interval=partition.interval,
        expected_candles=candles,
    )

    source = checkpoint.get("source") or {}
    receipt_payload: dict[str, Any] = {
        "schema_version": 1,
        "status": "PASS",
        "provider": "pionex",
        "market_type": "perp",
        "identity": partition.identity,
        "symbol": partition.symbol,
        "interval": partition.interval,
        "year": partition.year,
        "month": partition.month,
        "requested_start_ms": partition.requested_start_ms,
        "requested_end_ms": partition.requested_end_ms,
        "actual_first_ms": candles[0].time_ms,
        "actual_last_ms": candles[-1].time_ms,
        "rows": len(candles),
        "pages_fetched": int(source.get("pages_fetched", 0)),
        "audit_ok": True,
        "storage_run_id": storage_run_id,
        "staging": {
            "key": staging_key,
            "sha256": staging_sha256,
            "bytes": len(staging_payload),
        },
        "canonical": {
            "key": partition.canonical_key,
            "sha256": canonical_receipt.sha256,
            "bytes": canonical_receipt.bytes,
        },
        "finalized_at": _now_iso(now_fn),
    }
    receipt_object = _put_json(
        store,
        partition.receipt_key,
        receipt_payload,
        metadata={"status": "pass", "identity": partition.identity},
    )
    store.get_bytes_verified(partition.receipt_key, expected_sha256=receipt_object.sha256)

    verified_extra = {
        "source": source,
        "staging": staging,
        "canonical": {
            "key": partition.canonical_key,
            "sha256": canonical_receipt.sha256,
            "bytes": canonical_receipt.bytes,
            "rows": len(candles),
        },
        "receipt": {
            "key": partition.receipt_key,
            "sha256": receipt_object.sha256,
            "bytes": receipt_object.bytes,
        },
        "no_data": False,
    }
    _write_checkpoint(
        store,
        partition,
        status="VERIFIED",
        storage_run_id=storage_run_id,
        now_fn=now_fn,
        extra=verified_extra,
    )
    _write_checkpoint(
        store,
        partition,
        status="FINALIZED",
        storage_run_id=storage_run_id,
        now_fn=now_fn,
        extra=verified_extra,
    )
    return len(candles), int(source.get("pages_fetched", 0))


def _finalize_no_data(
    *,
    store: BackfillByteStore,
    partition: HistoricalPartition,
    pages_fetched: int,
    storage_run_id: str,
    now_fn: Callable[[], datetime],
) -> None:
    receipt_payload: dict[str, Any] = {
        "schema_version": 1,
        "status": "NO_DATA",
        "provider": "pionex",
        "market_type": "perp",
        "identity": partition.identity,
        "symbol": partition.symbol,
        "interval": partition.interval,
        "year": partition.year,
        "month": partition.month,
        "requested_start_ms": partition.requested_start_ms,
        "requested_end_ms": partition.requested_end_ms,
        "rows": 0,
        "pages_fetched": pages_fetched,
        "storage_run_id": storage_run_id,
        "finalized_at": _now_iso(now_fn),
    }
    receipt_object = _put_json(
        store,
        partition.receipt_key,
        receipt_payload,
        metadata={"status": "no-data", "identity": partition.identity},
    )
    store.get_bytes_verified(partition.receipt_key, expected_sha256=receipt_object.sha256)
    _write_checkpoint(
        store,
        partition,
        status="FINALIZED",
        storage_run_id=storage_run_id,
        now_fn=now_fn,
        extra={
            "source": {"pages_fetched": pages_fetched, "rows": 0},
            "receipt": {
                "key": partition.receipt_key,
                "sha256": receipt_object.sha256,
                "bytes": receipt_object.bytes,
            },
            "canonical": None,
            "staging": None,
            "no_data": True,
        },
    )


def run_historical_backfill_pilot(
    *,
    client: KlineClient,
    store: BackfillByteStore,
    symbols: list[str] | tuple[str, ...],
    year: int,
    storage_run_id: str,
    page_limit: int = 500,
    planned_stop_after_staged: int | None = None,
    now_fn: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> dict[str, Any]:
    if not storage_run_id.strip():
        raise ValueError("storage_run_id is required")
    if planned_stop_after_staged is not None and planned_stop_after_staged < 1:
        raise ValueError("planned_stop_after_staged must be positive")

    partitions = partition_specs_for_year(symbols, year)
    summary: dict[str, Any] = {
        "schema_version": 1,
        "status": "RUNNING",
        "year": year,
        "symbols": list(symbols),
        "intervals": ["15M", "60M", "4H"],
        "storage_run_id": storage_run_id,
        "work_items_total": len(partitions),
        "finalized_new": 0,
        "skipped_finalized": 0,
        "resumed_from_staged": 0,
        "resumed_from_verified": 0,
        "no_data": 0,
        "pages_fetched": 0,
        "rows_fetched": 0,
        "planned_interruptions": 0,
    }
    staged_this_run = 0

    for partition in partitions:
        checkpoint = _read_json_optional(store, partition.checkpoint_key)
        if checkpoint is not None and checkpoint.get("identity") != partition.identity:
            raise ValueError(f"Checkpoint identity mismatch: {partition.checkpoint_key}")

        if checkpoint is not None and checkpoint.get("status") == "FINALIZED":
            _verify_finalized_checkpoint(store, partition, checkpoint)
            summary["skipped_finalized"] += 1
            if checkpoint.get("no_data"):
                summary["no_data"] += 1
            continue

        if checkpoint is not None and checkpoint.get("status") == "VERIFIED":
            _verify_finalized_checkpoint(store, partition, {**checkpoint, "status": "FINALIZED"})
            final_extra = {key: checkpoint.get(key) for key in ("source", "staging", "canonical", "receipt", "no_data")}
            _write_checkpoint(
                store,
                partition,
                status="FINALIZED",
                storage_run_id=storage_run_id,
                now_fn=now_fn,
                extra=final_extra,
            )
            summary["resumed_from_verified"] += 1
            summary["finalized_new"] += 1
            continue

        if checkpoint is not None and checkpoint.get("status") == "STAGED":
            rows, _ = _finalize_from_staged(
                store=store,
                partition=partition,
                checkpoint=checkpoint,
                storage_run_id=storage_run_id,
                now_fn=now_fn,
            )
            summary["resumed_from_staged"] += 1
            summary["finalized_new"] += 1
            summary["rows_fetched"] += rows
            continue

        if checkpoint is not None and checkpoint.get("status") not in {"PENDING", "ACQUIRING"}:
            raise ValueError(
                f"Unsupported checkpoint state {checkpoint.get('status')} for {partition.identity}"
            )

        existing_canonical = store.get_bytes_if_exists(partition.canonical_key)
        if existing_canonical is not None:
            raise CanonicalConflictError(
                f"Canonical object exists without FINALIZED authority for {partition.identity}; "
                "refusing overwrite"
            )

        if checkpoint is None:
            _write_checkpoint(
                store,
                partition,
                status="PENDING",
                storage_run_id=storage_run_id,
                now_fn=now_fn,
            )
        _write_checkpoint(
            store,
            partition,
            status="ACQUIRING",
            storage_run_id=storage_run_id,
            now_fn=now_fn,
        )

        result = backfill_klines(
            client,
            partition.symbol,
            partition.interval,
            start_time_ms=partition.requested_start_ms,
            end_time_ms=partition.requested_end_ms,
            page_limit=page_limit,
        )
        summary["pages_fetched"] += result.pages_fetched
        summary["rows_fetched"] += len(result.candles)
        if not result.audit.ok:
            raise RuntimeError(f"Historical audit failed for {partition.identity}: {asdict(result.audit)}")

        if not result.candles:
            _finalize_no_data(
                store=store,
                partition=partition,
                pages_fetched=result.pages_fetched,
                storage_run_id=storage_run_id,
                now_fn=now_fn,
            )
            summary["no_data"] += 1
            summary["finalized_new"] += 1
            continue

        parquet = candles_to_parquet(list(result.candles))
        staging_receipt = store.put_bytes(
            partition.staging_key,
            parquet.payload,
            content_type="application/vnd.apache.parquet",
            metadata={
                "state": "staged",
                "source": "pionex-public-futures",
                "symbol": partition.symbol,
                "interval": partition.interval,
                "rows": str(parquet.rows),
            },
        )
        staging_payload = store.get_bytes_verified(
            partition.staging_key,
            expected_sha256=staging_receipt.sha256,
        )
        _verify_parquet_payload(
            staging_payload,
            interval=partition.interval,
            expected_candles=result.candles,
        )

        checkpoint = _write_checkpoint(
            store,
            partition,
            status="STAGED",
            storage_run_id=storage_run_id,
            now_fn=now_fn,
            extra={
                "source": {
                    "pages_fetched": result.pages_fetched,
                    "rows": len(result.candles),
                    "actual_first_ms": result.candles[0].time_ms,
                    "actual_last_ms": result.candles[-1].time_ms,
                    "audit_ok": True,
                },
                "staging": {
                    "key": partition.staging_key,
                    "sha256": staging_receipt.sha256,
                    "bytes": staging_receipt.bytes,
                    "rows": parquet.rows,
                },
                "no_data": False,
            },
        )
        staged_this_run += 1
        if (
            planned_stop_after_staged is not None
            and staged_this_run >= planned_stop_after_staged
        ):
            summary["status"] = "PLANNED_STOP"
            summary["planned_interruptions"] += 1
            summary["planned_stop_identity"] = partition.identity
            raise PlannedInterruption(
                f"Planned interruption after staging {partition.identity}",
                summary=summary,
            )

        rows, _ = _finalize_from_staged(
            store=store,
            partition=partition,
            checkpoint=checkpoint,
            storage_run_id=storage_run_id,
            now_fn=now_fn,
        )
        if rows != len(result.candles):
            raise RuntimeError(f"Finalized row mismatch for {partition.identity}")
        summary["finalized_new"] += 1

    summary["status"] = "PASS"
    summary["completed_at"] = _now_iso(now_fn)
    return summary
