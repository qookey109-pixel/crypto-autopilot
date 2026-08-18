from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from crypto_autopilot.binance_vision import BinanceVisionArchiveKey, ingest_kline_archive
from crypto_autopilot.storage.layout import HistoricalObjectKey
from crypto_autopilot.storage.parquet import candles_to_parquet, parquet_to_candles
from crypto_autopilot.storage.r2 import R2ObjectReceipt, R2Store


DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
DEFAULT_PERIOD = "2025-01"
AUTHORITY_RECEIPT = Path("research/receipts/2026-08-18-binance-vision-live-proof.json")


def download(url: str, *, retries: int = 3, timeout_seconds: float = 30.0) -> bytes:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = Request(
                url,
                headers={"User-Agent": "qookey-crypto-autopilot-binance-r2-proof/0.1"},
            )
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - validated Vision URL
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if isinstance(exc, HTTPError) and exc.code == 404:
                raise RuntimeError(f"required Binance Vision archive is missing: {url}") from exc
            if attempt + 1 < retries:
                time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"failed to download {url}: {last_error}") from last_error


def load_authority() -> dict:
    payload = json.loads(AUTHORITY_RECEIPT.read_text(encoding="utf-8"))
    if payload.get("status") != "PASS" or payload.get("provider") != "binance_usdm":
        raise RuntimeError("Binance Vision live-proof authority must be PASS/provider=binance_usdm")
    if payload.get("native_to_execution_exchange") is not False:
        raise RuntimeError("Binance authority must remain non-native to Pionex")
    if payload.get("may_authorize_pionex_native_history") is not False:
        raise RuntimeError("Binance authority must not authorize Pionex-native history")
    return payload


def canonical_json_bytes(payload: dict) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def receipt_from_existing(store: R2Store, key: str, payload: bytes) -> R2ObjectReceipt:
    return R2ObjectReceipt(
        bucket=store.bucket,
        key=key,
        bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        etag=None,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", default=DEFAULT_PERIOD)
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS))
    parser.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID") or "local-binance-vision-r2-proof")
    parser.add_argument("--output-dir", default="artifacts/binance-vision-r2-proof")
    args = parser.parse_args()

    account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    bucket = os.environ["R2_BUCKET_NAME"]
    access_key = os.environ["R2_ACCESS_KEY_ID"]
    secret_key = os.environ["R2_SECRET_ACCESS_KEY"]
    store = R2Store(
        account_id=account_id,
        bucket=bucket,
        access_key_id=access_key,
        secret_access_key=secret_key,
    )

    authority = load_authority()
    authority_archive_sha = dict(authority.get("archive_sha256") or {})
    if args.period != authority.get("proof_scope", {}).get("period"):
        raise RuntimeError("R2 proof period must match frozen Binance Vision live-proof authority")

    object_records: list[dict[str, object]] = []
    total_rows = 0
    total_parquet_bytes = 0

    for raw_symbol in args.symbols:
        symbol = raw_symbol.upper()
        key = BinanceVisionArchiveKey("klines", "monthly", symbol, "15m", args.period)
        expected_source_sha = authority_archive_sha.get(key.filename)
        if not expected_source_sha:
            raise RuntimeError(f"frozen authority has no source SHA for {key.filename}")

        archive_bytes = download(key.url)
        checksum_bytes = download(key.checksum_url)
        source = ingest_kline_archive(
            key,
            archive_bytes=archive_bytes,
            checksum_payload=checksum_bytes,
        )
        if source.receipt.archive_sha256 != expected_source_sha:
            raise RuntimeError(
                f"Binance Vision source revision detected for {key.filename}: "
                f"frozen={expected_source_sha}, observed={source.receipt.archive_sha256}"
            )

        parquet = candles_to_parquet(source.candles)
        object_key = HistoricalObjectKey(
            exchange="binance_usdm",
            market_type="perp",
            symbol=symbol,
            interval="15M",
            year=2025,
            month=1,
        ).build()
        if not object_key.startswith("market-data/binance_usdm/"):
            raise RuntimeError(f"unsafe Binance R2 namespace: {object_key}")
        if "market-data/pionex/" in object_key:
            raise RuntimeError("Binance materialization attempted to enter the Pionex namespace")

        existing = store.get_bytes_if_exists(object_key)
        action = "uploaded"
        if existing is None:
            upload_receipt = store.put_bytes(
                object_key,
                parquet.payload,
                content_type="application/vnd.apache.parquet",
                metadata={
                    "provider": "binance_usdm",
                    "delivery": "binance_vision",
                    "source-sha256": source.receipt.archive_sha256,
                    "source-period": args.period,
                },
            )
        else:
            restored_existing = parquet_to_candles(existing)
            if restored_existing != list(source.candles):
                raise RuntimeError(
                    f"existing Binance canonical R2 object conflicts with frozen source candles: {object_key}"
                )
            upload_receipt = receipt_from_existing(store, object_key, existing)
            action = "verified_existing"

        restored_bytes = store.get_bytes_verified(object_key, expected_sha256=upload_receipt.sha256)
        restored_candles = parquet_to_candles(restored_bytes)
        if restored_candles != list(source.candles):
            raise RuntimeError(f"R2 Parquet exact-candle mismatch for {object_key}")

        total_rows += len(source.candles)
        total_parquet_bytes += len(restored_bytes)
        object_records.append(
            {
                "provider": "binance_usdm",
                "delivery": "binance_vision",
                "symbol": symbol,
                "interval": "15M",
                "period": args.period,
                "source_url": key.url,
                "source_sha256": source.receipt.archive_sha256,
                "source_rows": len(source.candles),
                "r2_key": object_key,
                "r2_sha256": upload_receipt.sha256,
                "r2_bytes": len(restored_bytes),
                "r2_action": action,
                "exact_candle_equality_verified": True,
            }
        )

    if total_rows != 3 * 2976 or len(object_records) != 3:
        raise RuntimeError(
            f"unexpected bounded proof totals: objects={len(object_records)}, rows={total_rows}"
        )

    created_at = datetime.now(timezone.utc)
    manifest = {
        "schema": "binance-vision-r2-manifest-v0.1",
        "status": "PASS",
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "execution_exchange": "pionex",
        "native_to_execution_exchange": False,
        "may_authorize_pionex_native_history": False,
        "source_authority": str(AUTHORITY_RECEIPT),
        "source_authority_artifact_id": authority.get("artifact", {}).get("id"),
        "period": args.period,
        "object_count": len(object_records),
        "total_rows": total_rows,
        "total_parquet_bytes": total_parquet_bytes,
        "objects": object_records,
        "generated_at_utc": created_at.isoformat(),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "github_sha": os.getenv("GITHUB_SHA"),
        "live_trading_authorized": False,
        "private_api_used": False,
    }
    manifest_bytes = canonical_json_bytes(manifest)
    manifest_key = (
        "manifests/historical/binance_usdm/"
        f"year={created_at.year:04d}/month={created_at.month:02d}/"
        f"binance-vision-r2-proof-{args.run_id}.json"
    )
    manifest_upload = store.put_bytes(manifest_key, manifest_bytes, content_type="application/json")
    store.get_bytes_verified(manifest_key, expected_sha256=manifest_upload.sha256)

    receipt = {
        "schema": "binance-vision-r2-proof-v0.1",
        "status": "PASS",
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "execution_exchange": "pionex",
        "native_to_execution_exchange": False,
        "may_authorize_pionex_native_history": False,
        "period": args.period,
        "symbols": sorted(record["symbol"] for record in object_records),
        "object_count": len(object_records),
        "total_rows": total_rows,
        "total_parquet_bytes": total_parquet_bytes,
        "manifest_key": manifest_key,
        "manifest_sha256": manifest_upload.sha256,
        "source_authority": str(AUTHORITY_RECEIPT),
        "source_authority_json_sha256": authority.get("artifact", {}).get("evidence_json_sha256"),
        "all_source_archive_sha_verified": True,
        "all_r2_sha_verified": True,
        "all_parquet_decoded": True,
        "exact_candle_equality_verified": True,
        "pionex_namespace_touched": False,
        "private_api_used": False,
        "live_trading_authorized": False,
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "github_sha": os.getenv("GITHUB_SHA"),
        "generated_at_utc": created_at.isoformat(),
        "objects": object_records,
    }
    receipt_bytes = canonical_json_bytes(receipt)
    receipt_key = f"receipts/historical/binance_usdm/binance-vision-r2-proof-{args.run_id}.json"
    receipt_upload = store.put_bytes(receipt_key, receipt_bytes, content_type="application/json")
    store.get_bytes_verified(receipt_key, expected_sha256=receipt_upload.sha256)
    receipt["r2_receipt_key"] = receipt_key
    receipt["r2_receipt_sha256"] = receipt_upload.sha256

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "binance-vision-r2-manifest.json"
    receipt_path = output_dir / "binance-vision-r2-receipt.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "PASS",
                "provider": "binance_usdm",
                "object_count": len(object_records),
                "total_rows": total_rows,
                "total_parquet_bytes": total_parquet_bytes,
                "manifest_key": manifest_key,
                "receipt_key": receipt_key,
                "output_dir": str(output_dir),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
