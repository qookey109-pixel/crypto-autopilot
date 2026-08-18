from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from crypto_autopilot.models import Candle
from crypto_autopilot.storage.layout import HistoricalObjectKey, manifest_key, receipt_key
from crypto_autopilot.storage.parquet import candles_to_parquet, parquet_to_candles
from crypto_autopilot.storage.r2 import R2ObjectReceipt


class ByteStore(Protocol):
    def put_bytes(
        self,
        key: str,
        payload: bytes,
        *,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> R2ObjectReceipt: ...

    def get_bytes_verified(self, key: str, *, expected_sha256: str) -> bytes: ...


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _candle_from_dict(row: dict[str, Any]) -> Candle:
    return Candle(
        time_ms=int(row["time_ms"]),
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        volume=float(row["volume"]),
    )


def _partition_key(symbol: str, interval: str, candles: list[Candle]) -> str:
    if not candles:
        raise ValueError(f"No candles for {symbol} {interval}")

    first = datetime.fromtimestamp(candles[0].time_ms / 1000, tz=timezone.utc)
    last = datetime.fromtimestamp(candles[-1].time_ms / 1000, tz=timezone.utc)
    if interval == "15M":
        if (first.year, first.month) != (last.year, last.month):
            raise ValueError(f"15M bounded proof crosses a monthly partition: {symbol}")
        month: int | None = first.month
    else:
        if first.year != last.year:
            raise ValueError(f"Annual bounded proof crosses a year partition: {symbol} {interval}")
        month = None

    return HistoricalObjectKey(
        exchange="pionex",
        market_type="perp",
        symbol=symbol,
        interval=interval,
        year=first.year,
        month=month,
    ).build()


def _validate_authority(
    authority: dict[str, Any], source_receipt: dict[str, Any]
) -> tuple[list[str], list[str], int]:
    if authority.get("source") != "pionex_public_futures":
        raise ValueError("Authority receipt is not the Pionex public-futures M1A authority")
    if not authority.get("audit", {}).get("pass"):
        raise ValueError("Authority receipt audit did not pass")
    if not source_receipt.get("audit_pass"):
        raise ValueError("Downloaded M1A acquisition receipt audit did not pass")

    authority_intervals = list(authority.get("sample", {}).get("intervals", []))
    source_intervals = list(source_receipt.get("intervals", []))
    if authority_intervals != source_intervals:
        raise ValueError("Authority/source interval mismatch")

    authority_symbols = [item["symbol"] for item in authority.get("selected_universe", [])]
    source_symbols = sorted({item["symbol"] for item in source_receipt.get("results", [])})
    if sorted(authority_symbols) != source_symbols:
        raise ValueError("Authority/source symbol universe mismatch")

    total_rows = sum(int(item["candles"]) for item in source_receipt.get("results", []))
    expected_rows = int(authority.get("acquisition_summary", {}).get("total_candles", -1))
    if total_rows != expected_rows:
        raise ValueError(f"Authority/source row mismatch: expected {expected_rows}, got {total_rows}")

    expected_object_count = len(authority_symbols) * len(authority_intervals)
    if len(source_receipt.get("results", [])) != expected_object_count:
        raise ValueError("Authority/source object-count mismatch")

    return authority_symbols, authority_intervals, total_rows


def materialize_m1a_dataset(
    *,
    input_dir: Path,
    authority_receipt_path: Path,
    store: ByteStore,
    storage_run_id: str,
    created_at: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Materialize the authoritative bounded M1A evidence dataset into R2.

    The function verifies the downloaded acquisition artifact against the frozen
    M1A authority, converts all candle files to Zstandard Parquet, verifies every
    uploaded object by SHA-256 + decode + exact candle equality, and then writes
    a dataset manifest and receipt. It never interpolates or repairs source data.
    """

    input_dir = input_dir.resolve()
    authority_receipt_path = authority_receipt_path.resolve()
    source_receipt_path = input_dir / "receipt.json"
    if not source_receipt_path.exists():
        raise FileNotFoundError(f"Missing acquisition receipt: {source_receipt_path}")

    authority = _load_json(authority_receipt_path)
    source_receipt = _load_json(source_receipt_path)
    symbols, intervals, expected_total_rows = _validate_authority(authority, source_receipt)

    authority_meta = authority["authority"]
    source_artifact_sha256 = str(authority_meta["artifact_sha256"])
    source_run_id = int(authority_meta["github_actions_run_id"])
    source_commit = str(authority_meta["commit"])
    source_receipt_sha256 = hashlib.sha256(source_receipt_path.read_bytes()).hexdigest()

    now = created_at or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)

    object_receipts: list[dict[str, Any]] = []
    for result in sorted(source_receipt["results"], key=lambda item: (item["symbol"], item["interval"])):
        if not result.get("audit_ok"):
            raise ValueError(f"Source audit failed for {result['symbol']} {result['interval']}")

        source_path = input_dir / str(result["file"])
        source_payload = _load_json(source_path)
        symbol = str(result["symbol"])
        interval = str(result["interval"])
        if source_payload.get("symbol") != symbol or source_payload.get("interval") != interval:
            raise ValueError(f"Source metadata mismatch: {source_path}")
        if not source_payload.get("audit", {}).get("ok"):
            raise ValueError(f"Source candle audit not OK: {source_path}")

        candles = [_candle_from_dict(row) for row in source_payload.get("candles", [])]
        if len(candles) != int(result["candles"]):
            raise ValueError(f"Source row-count mismatch: {source_path}")
        times = [candle.time_ms for candle in candles]
        if times != sorted(times) or len(times) != len(set(times)):
            raise ValueError(f"Source timestamps are not strict/unique: {source_path}")

        key = _partition_key(symbol, interval, candles)
        parquet = candles_to_parquet(candles)
        receipt = store.put_bytes(
            key,
            parquet.payload,
            content_type="application/vnd.apache.parquet",
            metadata={
                "scope": "m1a-bounded-proof",
                "source": "pionex-public-futures",
                "symbol": symbol,
                "interval": interval,
                "rows": str(parquet.rows),
                "source-run-id": str(source_run_id),
                "audit-ok": "true",
            },
        )
        downloaded = store.get_bytes_verified(key, expected_sha256=receipt.sha256)
        restored = parquet_to_candles(downloaded)
        if restored != candles:
            raise RuntimeError(f"R2 Parquet round-trip candle mismatch: {key}")

        object_receipts.append(
            {
                "actual_first_ms": candles[0].time_ms,
                "actual_last_ms": candles[-1].time_ms,
                "audit_ok": True,
                "bytes": receipt.bytes,
                "etag": receipt.etag,
                "interval": interval,
                "key": key,
                "requested_end_ms": int(source_payload["requested_end_ms"]),
                "requested_start_ms": int(source_payload["requested_start_ms"]),
                "rows": parquet.rows,
                "sha256": receipt.sha256,
                "symbol": symbol,
            }
        )

    total_rows = sum(item["rows"] for item in object_receipts)
    if total_rows != expected_total_rows:
        raise RuntimeError(f"Materialized row total mismatch: expected {expected_total_rows}, got {total_rows}")

    manifest = {
        "audit_pass": True,
        "completeness": "bounded-m1a-evidence-window",
        "created_at": now.isoformat(),
        "dataset": "M1A_PIONEX_BOUNDED",
        "intervals": intervals,
        "object_count": len(object_receipts),
        "objects": object_receipts,
        "provenance": {
            "exchange": "pionex",
            "market_type": "perp",
            "source": "pionex_public_futures",
            "source_artifact_sha256": source_artifact_sha256,
            "source_commit": source_commit,
            "source_github_actions_run_id": source_run_id,
            "source_receipt_sha256": source_receipt_sha256,
        },
        "requested_end_ms": int(source_receipt["requested_end_ms"]),
        "requested_start_ms": int(source_receipt["requested_start_ms"]),
        "schema_version": 1,
        "storage_run_id": storage_run_id,
        "symbols": symbols,
        "total_parquet_bytes": sum(item["bytes"] for item in object_receipts),
        "total_rows": total_rows,
    }
    manifest_payload = _canonical_json(manifest)
    manifest_object = store.put_bytes(
        manifest_key(now),
        manifest_payload,
        content_type="application/json",
        metadata={"dataset": "m1a-pionex-bounded", "storage-run-id": storage_run_id},
    )
    store.get_bytes_verified(manifest_object.key, expected_sha256=manifest_object.sha256)

    dataset_receipt = {
        "created_at": now.isoformat(),
        "dataset": "M1A_PIONEX_BOUNDED",
        "manifest": {
            "bytes": manifest_object.bytes,
            "etag": manifest_object.etag,
            "key": manifest_object.key,
            "sha256": manifest_object.sha256,
        },
        "object_count": len(object_receipts),
        "schema_version": 1,
        "source_artifact_sha256": source_artifact_sha256,
        "source_github_actions_run_id": source_run_id,
        "status": "PASS",
        "storage_run_id": storage_run_id,
        "total_parquet_bytes": manifest["total_parquet_bytes"],
        "total_rows": total_rows,
    }
    receipt_payload = _canonical_json(dataset_receipt)
    receipt_object = store.put_bytes(
        receipt_key(storage_run_id),
        receipt_payload,
        content_type="application/json",
        metadata={"dataset": "m1a-pionex-bounded", "status": "pass"},
    )
    store.get_bytes_verified(receipt_object.key, expected_sha256=receipt_object.sha256)
    dataset_receipt["receipt"] = {
        "bytes": receipt_object.bytes,
        "etag": receipt_object.etag,
        "key": receipt_object.key,
        "sha256": receipt_object.sha256,
    }

    return manifest, dataset_receipt
