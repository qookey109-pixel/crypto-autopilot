from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from crypto_autopilot.models import Candle
from crypto_autopilot.storage.layout import HistoricalObjectKey
from crypto_autopilot.storage.parquet import candles_to_parquet, parquet_to_candles
from crypto_autopilot.storage.r2 import R2Store


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main() -> int:
    candles = [
        Candle(time_ms=1786939200000, open=100.0, high=102.0, low=99.0, close=101.0, volume=10.0),
        Candle(time_ms=1786940100000, open=101.0, high=103.0, low=100.0, close=102.0, volume=12.0),
        Candle(time_ms=1786941000000, open=102.0, high=104.0, low=101.0, close=103.0, volume=11.0),
    ]
    artifact = candles_to_parquet(candles)
    key = HistoricalObjectKey(
        exchange="pionex",
        market_type="perp",
        symbol="R2_PROOF_USDT_PERP",
        interval="15M",
        year=2026,
        month=8,
    ).build()

    store = R2Store(
        account_id=required("CLOUDFLARE_ACCOUNT_ID"),
        bucket=required("R2_BUCKET_NAME"),
        access_key_id=required("R2_ACCESS_KEY_ID"),
        secret_access_key=required("R2_SECRET_ACCESS_KEY"),
    )
    receipt = store.put_bytes(
        key,
        artifact.payload,
        content_type="application/vnd.apache.parquet",
        metadata={"rows": str(artifact.rows), "proof": "m1b"},
    )
    downloaded = store.get_bytes_verified(key, expected_sha256=receipt.sha256)
    restored = parquet_to_candles(downloaded)
    if len(restored) != artifact.rows:
        raise RuntimeError("R2 round-trip row-count mismatch")

    print(
        json.dumps(
            {
                "proof": "M1B_R2_ROUND_TRIP",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "bucket": receipt.bucket,
                "key": receipt.key,
                "bytes": receipt.bytes,
                "rows": artifact.rows,
                "sha256": receipt.sha256,
                "etag": receipt.etag,
                "status": "PASS",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
