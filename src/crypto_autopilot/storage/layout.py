from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


INTERVAL_FOLDERS = {"15M": "15m", "60M": "1h", "4H": "4h"}


@dataclass(frozen=True, slots=True)
class HistoricalObjectKey:
    exchange: str
    market_type: str
    symbol: str
    interval: str
    year: int
    month: int | None = None

    def build(self) -> str:
        if self.interval not in INTERVAL_FOLDERS:
            raise ValueError(f"Unsupported interval for historical layout: {self.interval}")
        if self.year < 2009 or self.year > 2100:
            raise ValueError("year outside supported range")
        if self.month is not None and not 1 <= self.month <= 12:
            raise ValueError("month must be between 1 and 12")

        tf = INTERVAL_FOLDERS[self.interval]
        prefix = (
            f"market-data/{self.exchange}/{self.market_type}/"
            f"{self.symbol}/{tf}/year={self.year:04d}"
        )
        if self.month is None:
            return f"{prefix}/candles.parquet"
        return f"{prefix}/month={self.month:02d}/candles.parquet"


def _historical_partition_suffix(
    *,
    exchange: str,
    market_type: str,
    symbol: str,
    interval: str,
    year: int,
    month: int | None,
) -> str:
    canonical = HistoricalObjectKey(
        exchange=exchange,
        market_type=market_type,
        symbol=symbol,
        interval=interval,
        year=year,
        month=month,
    ).build()
    return canonical.removeprefix("market-data/").removesuffix("/candles.parquet")


def historical_checkpoint_key(
    *,
    exchange: str,
    market_type: str,
    symbol: str,
    interval: str,
    year: int,
    month: int | None = None,
) -> str:
    suffix = _historical_partition_suffix(
        exchange=exchange,
        market_type=market_type,
        symbol=symbol,
        interval=interval,
        year=year,
        month=month,
    )
    return f"checkpoints/historical/{suffix}/checkpoint.json"


def historical_staging_key(
    *,
    exchange: str,
    market_type: str,
    symbol: str,
    interval: str,
    year: int,
    month: int | None = None,
) -> str:
    suffix = _historical_partition_suffix(
        exchange=exchange,
        market_type=market_type,
        symbol=symbol,
        interval=interval,
        year=year,
        month=month,
    )
    return f"staging/historical/{suffix}/candles.parquet"


def historical_partition_receipt_key(
    *,
    exchange: str,
    market_type: str,
    symbol: str,
    interval: str,
    year: int,
    month: int | None = None,
) -> str:
    suffix = _historical_partition_suffix(
        exchange=exchange,
        market_type=market_type,
        symbol=symbol,
        interval=interval,
        year=year,
        month=month,
    )
    return f"receipts/historical/partitions/{suffix}/receipt.json"


def receipt_key(run_id: str) -> str:
    clean = run_id.strip().replace("/", "-")
    if not clean:
        raise ValueError("run_id is required")
    return f"receipts/historical/{clean}.json"


def manifest_key(created_at: datetime) -> str:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    created_at = created_at.astimezone(timezone.utc)
    return (
        "manifests/historical/"
        f"year={created_at.year:04d}/month={created_at.month:02d}/"
        f"manifest-{created_at.strftime('%Y%m%dT%H%M%SZ')}.json"
    )
