from __future__ import annotations

import csv
import hashlib
import io
import math
import zipfile
from dataclasses import dataclass
from datetime import date
from io import BytesIO
from typing import Iterable

from .binance_vision import BINANCE_VISION_BASE_URL, parse_checksum, sha256_bytes


FUNDING_CADENCE_JITTER_TOLERANCE_MS = 10


class BinanceFundingEvidenceError(RuntimeError):
    pass


class BinanceFundingRevisionConflictError(BinanceFundingEvidenceError):
    pass


@dataclass(frozen=True, slots=True)
class BinanceFundingObservation:
    symbol: str
    funding_time_ms: int
    funding_interval_hours: int
    rate: float

    def __post_init__(self) -> None:
        if not self.symbol.strip() or self.symbol != self.symbol.upper():
            raise ValueError("symbol must be a non-empty uppercase Binance symbol")
        if self.funding_time_ms < 0:
            raise ValueError("funding_time_ms cannot be negative")
        if self.funding_interval_hours < 1 or self.funding_interval_hours > 24:
            raise ValueError("funding_interval_hours must be between 1 and 24")
        if not math.isfinite(self.rate):
            raise ValueError("funding rate must be finite")


@dataclass(frozen=True, slots=True)
class BinanceVisionFundingArchiveKey:
    symbol: str
    period: str

    def __post_init__(self) -> None:
        if not self.symbol.strip() or self.symbol != self.symbol.upper():
            raise ValueError("symbol must be a non-empty uppercase Binance symbol")
        try:
            parsed = date.fromisoformat(f"{self.period}-01")
        except ValueError as exc:
            raise ValueError("period must be YYYY-MM") from exc
        if parsed.strftime("%Y-%m") != self.period:
            raise ValueError("period must be YYYY-MM")

    @property
    def filename(self) -> str:
        return f"{self.symbol}-fundingRate-{self.period}.zip"

    @property
    def csv_filename(self) -> str:
        return self.filename.removesuffix(".zip") + ".csv"

    @property
    def path(self) -> str:
        return f"data/futures/um/monthly/fundingRate/{self.symbol}/{self.filename}"

    @property
    def url(self) -> str:
        return BINANCE_VISION_BASE_URL + self.path

    @property
    def checksum_url(self) -> str:
        return self.url + ".CHECKSUM"

    @property
    def identity(self) -> tuple[str, str]:
        return (self.symbol, self.period)


@dataclass(frozen=True, slots=True)
class BinanceFundingArchiveReceipt:
    symbol: str
    period: str
    source_url: str
    checksum_url: str
    archive_filename: str
    archive_sha256: str
    row_count: int
    first_time_ms: int
    last_time_ms: int
    interval_hours: tuple[int, ...]
    min_rate: float
    max_rate: float
    cadence_anomalies: int
    audit_ok: bool
    provider: str = "binance_usdm"
    delivery: str = "binance_vision"
    dataset: str = "fundingRate"
    native_to_pionex: bool = False
    may_authorize_pionex_native_history: bool = False

    @property
    def identity(self) -> tuple[str, str]:
        return (self.symbol, self.period)


@dataclass(frozen=True, slots=True)
class BinanceVisionFundingArchive:
    key: BinanceVisionFundingArchiveKey
    observations: tuple[BinanceFundingObservation, ...]
    receipt: BinanceFundingArchiveReceipt


@dataclass(frozen=True, slots=True)
class FundingParquetArtifact:
    payload: bytes
    rows: int
    sha256: str
    first_time_ms: int | None
    last_time_ms: int | None


def funding_r2_key(symbol: str, year: int) -> str:
    if not symbol.strip() or symbol != symbol.upper():
        raise ValueError("symbol must be a non-empty uppercase Binance symbol")
    if year < 2009 or year > 2100:
        raise ValueError("year outside supported range")
    return f"market-data/binance_usdm/perp/{symbol}/funding/year={year:04d}/funding.parquet"


def funding_partition_receipt_key(symbol: str, year: int) -> str:
    canonical = funding_r2_key(symbol, year)
    suffix = canonical.removeprefix("market-data/").removesuffix("/funding.parquet")
    return f"receipts/historical/funding/{suffix}/receipt.json"


def _verify_checksum(
    key: BinanceVisionFundingArchiveKey,
    *,
    archive_bytes: bytes,
    checksum_payload: bytes | str,
) -> str:
    expected_sha256, checksum_filename = parse_checksum(checksum_payload)
    if checksum_filename != key.filename:
        raise BinanceFundingEvidenceError(
            f"CHECKSUM filename mismatch: expected {key.filename}, got {checksum_filename}"
        )
    actual_sha256 = sha256_bytes(archive_bytes)
    if actual_sha256 != expected_sha256:
        raise BinanceFundingEvidenceError(
            f"Funding archive SHA-256 mismatch: expected {expected_sha256}, got {actual_sha256}"
        )
    return actual_sha256


def _rows_from_archive(key: BinanceVisionFundingArchiveKey, archive_bytes: bytes) -> list[list[str]]:
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes), mode="r") as archive:
            names = [name for name in archive.namelist() if not name.endswith("/")]
            if names != [key.csv_filename]:
                raise BinanceFundingEvidenceError(
                    f"archive must contain exactly {key.csv_filename}; got {names}"
                )
            payload = archive.read(names[0]).decode("utf-8-sig")
    except BinanceFundingEvidenceError:
        raise
    except (zipfile.BadZipFile, UnicodeDecodeError, KeyError) as exc:
        raise BinanceFundingEvidenceError("invalid Binance funding ZIP/CSV payload") from exc

    rows = [row for row in csv.reader(io.StringIO(payload)) if row and any(cell.strip() for cell in row)]
    if not rows:
        raise BinanceFundingEvidenceError("funding archive contains no rows")
    return rows


def _header_indexes(header: list[str]) -> tuple[int, int, int] | None:
    normalized = [cell.strip().lower() for cell in header]
    if "calc_time" not in normalized:
        return None

    def find_one(names: tuple[str, ...]) -> int:
        for name in names:
            if name in normalized:
                return normalized.index(name)
        raise BinanceFundingEvidenceError(f"funding header missing one of {names}")

    return (
        normalized.index("calc_time"),
        find_one(("funding_interval_hours", "funding_interval")),
        find_one(("last_funding_rate", "funding_rate", "fundingrate")),
    )


def _parse_observations(
    key: BinanceVisionFundingArchiveKey,
    rows: list[list[str]],
) -> tuple[BinanceFundingObservation, ...]:
    indexes = _header_indexes(rows[0])
    data_rows = rows[1:] if indexes is not None else rows
    if indexes is None:
        if any(len(row) != 3 for row in data_rows):
            raise BinanceFundingEvidenceError(
                "headerless funding archive must have exactly three columns: "
                "calc_time,funding_interval_hours,last_funding_rate"
            )
        indexes = (0, 1, 2)
    if not data_rows:
        raise BinanceFundingEvidenceError("funding archive contains no data rows")

    parsed: list[BinanceFundingObservation] = []
    time_idx, interval_idx, rate_idx = indexes
    for row in data_rows:
        if max(indexes) >= len(row):
            raise BinanceFundingEvidenceError("funding row has too few columns")
        try:
            parsed.append(
                BinanceFundingObservation(
                    symbol=key.symbol,
                    funding_time_ms=int(row[time_idx]),
                    funding_interval_hours=int(float(row[interval_idx])),
                    rate=float(row[rate_idx]),
                )
            )
        except (TypeError, ValueError) as exc:
            raise BinanceFundingEvidenceError("invalid funding row") from exc
    return tuple(parsed)


def _cadence_residual_ms(left: BinanceFundingObservation, right: BinanceFundingObservation) -> int:
    hour_ms = 60 * 60 * 1000
    delta = right.funding_time_ms - left.funding_time_ms
    expected = {
        left.funding_interval_hours * hour_ms,
        right.funding_interval_hours * hour_ms,
    }
    return min((delta - item for item in expected), key=abs)


def _cadence_anomalies(observations: tuple[BinanceFundingObservation, ...]) -> int:
    return sum(
        abs(_cadence_residual_ms(left, right)) > FUNDING_CADENCE_JITTER_TOLERANCE_MS
        for left, right in zip(observations, observations[1:])
    )


def ingest_funding_archive(
    key: BinanceVisionFundingArchiveKey,
    *,
    archive_bytes: bytes,
    checksum_payload: bytes | str,
) -> BinanceVisionFundingArchive:
    archive_sha256 = _verify_checksum(
        key,
        archive_bytes=archive_bytes,
        checksum_payload=checksum_payload,
    )
    observations = _parse_observations(key, _rows_from_archive(key, archive_bytes))
    times = [point.funding_time_ms for point in observations]
    if times != sorted(times) or len(times) != len(set(times)):
        raise BinanceFundingEvidenceError("funding timestamps must be strictly increasing and unique")
    anomalies = _cadence_anomalies(observations)
    if anomalies:
        raise BinanceFundingEvidenceError(f"unexplained funding cadence gaps: {anomalies}")
    rates = [point.rate for point in observations]
    intervals = tuple(sorted({point.funding_interval_hours for point in observations}))
    receipt = BinanceFundingArchiveReceipt(
        symbol=key.symbol,
        period=key.period,
        source_url=key.url,
        checksum_url=key.checksum_url,
        archive_filename=key.filename,
        archive_sha256=archive_sha256,
        row_count=len(observations),
        first_time_ms=times[0],
        last_time_ms=times[-1],
        interval_hours=intervals,
        min_rate=min(rates),
        max_rate=max(rates),
        cadence_anomalies=0,
        audit_ok=True,
    )
    return BinanceVisionFundingArchive(key=key, observations=observations, receipt=receipt)


def combine_funding_archives(
    archives: Iterable[BinanceVisionFundingArchive],
    *,
    symbol: str,
    year: int,
) -> tuple[BinanceFundingObservation, ...]:
    selected = sorted(archives, key=lambda item: item.key.period)
    if not selected:
        raise BinanceFundingEvidenceError("annual funding aggregation requires archives")
    for archive in selected:
        if archive.key.symbol != symbol or not archive.key.period.startswith(f"{year:04d}-"):
            raise BinanceFundingEvidenceError("funding archive escaped annual symbol scope")
        if not archive.receipt.audit_ok:
            raise BinanceFundingEvidenceError("funding archive receipt audit must pass")
    combined = tuple(point for archive in selected for point in archive.observations)
    times = [point.funding_time_ms for point in combined]
    if times != sorted(times) or len(times) != len(set(times)):
        raise BinanceFundingEvidenceError("annual funding timestamps must be strictly increasing and unique")
    anomalies = _cadence_anomalies(combined)
    if anomalies:
        raise BinanceFundingEvidenceError(f"annual funding cadence gaps: {anomalies}")
    return combined


def funding_to_parquet(observations: Iterable[BinanceFundingObservation]) -> FundingParquetArtifact:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("pyarrow is required for funding Parquet storage") from exc

    ordered = sorted(observations, key=lambda item: item.funding_time_ms)
    if ordered:
        times = [item.funding_time_ms for item in ordered]
        if len(times) != len(set(times)):
            raise BinanceFundingEvidenceError("cannot write duplicate funding timestamps")
    table = pa.table(
        {
            "symbol": [item.symbol for item in ordered],
            "funding_time_ms": [item.funding_time_ms for item in ordered],
            "funding_interval_hours": [item.funding_interval_hours for item in ordered],
            "funding_rate": [item.rate for item in ordered],
        }
    )
    buffer = BytesIO()
    pq.write_table(table, buffer, compression="zstd")
    payload = buffer.getvalue()
    return FundingParquetArtifact(
        payload=payload,
        rows=len(ordered),
        sha256=hashlib.sha256(payload).hexdigest(),
        first_time_ms=ordered[0].funding_time_ms if ordered else None,
        last_time_ms=ordered[-1].funding_time_ms if ordered else None,
    )


def parquet_to_funding(payload: bytes) -> list[BinanceFundingObservation]:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("pyarrow is required for funding Parquet storage") from exc
    table = pq.ParquetFile(BytesIO(payload)).read(use_threads=False)
    return [
        BinanceFundingObservation(
            symbol=str(row["symbol"]),
            funding_time_ms=int(row["funding_time_ms"]),
            funding_interval_hours=int(row["funding_interval_hours"]),
            rate=float(row["funding_rate"]),
        )
        for row in table.to_pylist()
    ]


def assert_no_funding_archive_revision(
    existing: BinanceFundingArchiveReceipt,
    observed: BinanceFundingArchiveReceipt,
) -> None:
    if existing.identity != observed.identity:
        raise ValueError("funding receipts must have the same logical identity")
    if existing.archive_sha256 != observed.archive_sha256:
        raise BinanceFundingRevisionConflictError(
            "Binance funding archive changed for an existing logical month; explicit revision review is required"
        )
    compared = (
        existing.row_count == observed.row_count
        and existing.first_time_ms == observed.first_time_ms
        and existing.last_time_ms == observed.last_time_ms
        and existing.interval_hours == observed.interval_hours
    )
    if not compared:
        raise BinanceFundingRevisionConflictError(
            "Binance funding archive metadata changed despite matching logical identity"
        )
