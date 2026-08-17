from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from io import BytesIO
from typing import Iterable

from ..models import Candle


@dataclass(frozen=True, slots=True)
class ParquetArtifact:
    payload: bytes
    rows: int
    sha256: str
    first_time_ms: int | None
    last_time_ms: int | None


def candles_to_parquet(candles: Iterable[Candle]) -> ParquetArtifact:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError("pyarrow is required for Parquet storage") from exc

    ordered = sorted(candles, key=lambda candle: candle.time_ms)
    table = pa.table(
        {
            "time_ms": [c.time_ms for c in ordered],
            "open": [c.open for c in ordered],
            "high": [c.high for c in ordered],
            "low": [c.low for c in ordered],
            "close": [c.close for c in ordered],
            "volume": [c.volume for c in ordered],
        }
    )
    buffer = BytesIO()
    pq.write_table(table, buffer, compression="zstd")
    payload = buffer.getvalue()
    return ParquetArtifact(
        payload=payload,
        rows=len(ordered),
        sha256=hashlib.sha256(payload).hexdigest(),
        first_time_ms=ordered[0].time_ms if ordered else None,
        last_time_ms=ordered[-1].time_ms if ordered else None,
    )


def parquet_to_candles(payload: bytes) -> list[Candle]:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError("pyarrow is required for Parquet storage") from exc

    table = pq.read_table(BytesIO(payload))
    rows = table.to_pylist()
    return [
        Candle(
            time_ms=int(row["time_ms"]),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume"]),
        )
        for row in rows
    ]
