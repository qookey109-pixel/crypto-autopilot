from __future__ import annotations

import csv
import hashlib
import io
import re
import zipfile
from dataclasses import dataclass
from datetime import date

from .binance_historical import BINANCE_INTERVAL_MS, BINANCE_TO_PROJECT_INTERVAL
from .exchanges.binance_usdm_public import BinanceMarkPriceCandle
from .historical import audit_candles
from .models import Candle


BINANCE_VISION_BASE_URL = "https://data.binance.vision/"
_ALLOWED_DATASETS = {"klines", "markPriceKlines"}
_ALLOWED_FREQUENCIES = {"monthly", "daily"}
_CHECKSUM_RE = re.compile(r"^([0-9a-fA-F]{64})\s+\*?(.+?)\s*$")


class BinanceVisionEvidenceError(RuntimeError):
    pass


class BinanceVisionRevisionConflictError(BinanceVisionEvidenceError):
    pass


@dataclass(frozen=True, slots=True)
class BinanceVisionArchiveKey:
    dataset: str
    frequency: str
    symbol: str
    interval: str
    period: str

    def __post_init__(self) -> None:
        if self.dataset not in _ALLOWED_DATASETS:
            raise ValueError(f"unsupported Binance Vision dataset: {self.dataset}")
        if self.frequency not in _ALLOWED_FREQUENCIES:
            raise ValueError(f"unsupported Binance Vision frequency: {self.frequency}")
        if not self.symbol.strip() or self.symbol != self.symbol.upper():
            raise ValueError("symbol must be a non-empty uppercase Binance symbol")
        if self.interval not in BINANCE_INTERVAL_MS:
            raise ValueError("V0.1 Binance Vision supports 15m, 1h and 4h")
        try:
            if self.frequency == "monthly":
                parsed = date.fromisoformat(f"{self.period}-01")
                if parsed.strftime("%Y-%m") != self.period:
                    raise ValueError
            else:
                parsed = date.fromisoformat(self.period)
                if parsed.isoformat() != self.period:
                    raise ValueError
        except ValueError as exc:
            expected = "YYYY-MM" if self.frequency == "monthly" else "YYYY-MM-DD"
            raise ValueError(f"period must be {expected} for {self.frequency}") from exc

    @property
    def filename(self) -> str:
        return f"{self.symbol}-{self.interval}-{self.period}.zip"

    @property
    def csv_filename(self) -> str:
        return self.filename.removesuffix(".zip") + ".csv"

    @property
    def path(self) -> str:
        return (
            f"data/futures/um/{self.frequency}/{self.dataset}/"
            f"{self.symbol}/{self.interval}/{self.filename}"
        )

    @property
    def url(self) -> str:
        return BINANCE_VISION_BASE_URL + self.path

    @property
    def checksum_url(self) -> str:
        return self.url + ".CHECKSUM"

    @property
    def identity(self) -> tuple[str, str, str, str, str]:
        return (self.dataset, self.frequency, self.symbol, self.interval, self.period)


@dataclass(frozen=True, slots=True)
class BinanceVisionArchiveReceipt:
    dataset: str
    frequency: str
    symbol: str
    interval: str
    period: str
    source_url: str
    checksum_url: str
    archive_filename: str
    expected_sha256: str
    archive_sha256: str
    row_count: int
    first_time_ms: int | None
    last_time_ms: int | None
    audit_ok: bool
    provider: str = "binance_usdm"
    delivery: str = "binance_vision"
    native_to_pionex: bool = False
    may_authorize_pionex_native_history: bool = False

    @property
    def identity(self) -> tuple[str, str, str, str, str]:
        return (self.dataset, self.frequency, self.symbol, self.interval, self.period)


@dataclass(frozen=True, slots=True)
class BinanceVisionKlineArchive:
    key: BinanceVisionArchiveKey
    candles: tuple[Candle, ...]
    receipt: BinanceVisionArchiveReceipt


@dataclass(frozen=True, slots=True)
class BinanceVisionMarkPriceArchive:
    key: BinanceVisionArchiveKey
    candles: tuple[BinanceMarkPriceCandle, ...]
    receipt: BinanceVisionArchiveReceipt


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def parse_checksum(payload: bytes | str) -> tuple[str, str]:
    text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) != 1:
        raise BinanceVisionEvidenceError("Binance Vision CHECKSUM must contain exactly one non-empty line")
    match = _CHECKSUM_RE.fullmatch(lines[0])
    if match is None:
        raise BinanceVisionEvidenceError("invalid Binance Vision CHECKSUM format")
    return match.group(1).lower(), match.group(2).strip()


def _verify_archive_checksum(
    key: BinanceVisionArchiveKey,
    *,
    archive_bytes: bytes,
    checksum_payload: bytes | str,
) -> str:
    expected_sha256, checksum_filename = parse_checksum(checksum_payload)
    if checksum_filename != key.filename:
        raise BinanceVisionEvidenceError(
            f"CHECKSUM filename mismatch: expected {key.filename}, got {checksum_filename}"
        )
    actual_sha256 = sha256_bytes(archive_bytes)
    if actual_sha256 != expected_sha256:
        raise BinanceVisionEvidenceError(
            f"Binance Vision archive SHA-256 mismatch: expected {expected_sha256}, got {actual_sha256}"
        )
    return actual_sha256


def _csv_rows_from_archive(key: BinanceVisionArchiveKey, archive_bytes: bytes) -> list[list[str]]:
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes), mode="r") as archive:
            names = [name for name in archive.namelist() if not name.endswith("/")]
            if names != [key.csv_filename]:
                raise BinanceVisionEvidenceError(
                    f"archive must contain exactly {key.csv_filename}; got {names}"
                )
            payload = archive.read(names[0]).decode("utf-8-sig")
    except BinanceVisionEvidenceError:
        raise
    except (zipfile.BadZipFile, UnicodeDecodeError, KeyError) as exc:
        raise BinanceVisionEvidenceError("invalid Binance Vision ZIP/CSV payload") from exc

    parsed = list(csv.reader(io.StringIO(payload)))
    rows = [row for row in parsed if row and any(cell.strip() for cell in row)]
    if rows and rows[0] and not rows[0][0].strip().lstrip("-").isdigit():
        rows = rows[1:]
    if not rows:
        raise BinanceVisionEvidenceError("Binance Vision archive contains no data rows")
    return rows


def _parse_kline_row(row: list[str]) -> Candle:
    if len(row) < 7:
        raise BinanceVisionEvidenceError("Binance Vision kline row has too few columns")
    try:
        return Candle(
            time_ms=int(row[0]),
            open=float(row[1]),
            high=float(row[2]),
            low=float(row[3]),
            close=float(row[4]),
            volume=float(row[5]),
        )
    except (TypeError, ValueError) as exc:
        raise BinanceVisionEvidenceError("invalid Binance Vision kline row") from exc


def _parse_mark_row(key: BinanceVisionArchiveKey, row: list[str]) -> BinanceMarkPriceCandle:
    if len(row) < 7:
        raise BinanceVisionEvidenceError("Binance Vision mark-price row has too few columns")
    try:
        return BinanceMarkPriceCandle(
            symbol=key.symbol,
            interval=key.interval,
            open_time_ms=int(row[0]),
            open=float(row[1]),
            high=float(row[2]),
            low=float(row[3]),
            close=float(row[4]),
            close_time_ms=int(row[6]),
        )
    except (TypeError, ValueError) as exc:
        raise BinanceVisionEvidenceError("invalid Binance Vision mark-price row") from exc


def _receipt(
    key: BinanceVisionArchiveKey,
    *,
    archive_sha256: str,
    row_count: int,
    first_time_ms: int | None,
    last_time_ms: int | None,
    audit_ok: bool,
) -> BinanceVisionArchiveReceipt:
    return BinanceVisionArchiveReceipt(
        dataset=key.dataset,
        frequency=key.frequency,
        symbol=key.symbol,
        interval=key.interval,
        period=key.period,
        source_url=key.url,
        checksum_url=key.checksum_url,
        archive_filename=key.filename,
        expected_sha256=archive_sha256,
        archive_sha256=archive_sha256,
        row_count=row_count,
        first_time_ms=first_time_ms,
        last_time_ms=last_time_ms,
        audit_ok=audit_ok,
    )


def ingest_kline_archive(
    key: BinanceVisionArchiveKey,
    *,
    archive_bytes: bytes,
    checksum_payload: bytes | str,
) -> BinanceVisionKlineArchive:
    if key.dataset != "klines":
        raise ValueError("key.dataset must be klines")
    archive_sha256 = _verify_archive_checksum(
        key,
        archive_bytes=archive_bytes,
        checksum_payload=checksum_payload,
    )
    candles = tuple(_parse_kline_row(row) for row in _csv_rows_from_archive(key, archive_bytes))
    times = [candle.time_ms for candle in candles]
    if times != sorted(times) or len(times) != len(set(times)):
        raise BinanceVisionEvidenceError("Binance Vision klines must be strictly increasing and unique")
    audit = audit_candles(candles, BINANCE_TO_PROJECT_INTERVAL[key.interval])
    if not audit.ok:
        raise BinanceVisionEvidenceError("Binance Vision kline audit failed")
    return BinanceVisionKlineArchive(
        key=key,
        candles=candles,
        receipt=_receipt(
            key,
            archive_sha256=archive_sha256,
            row_count=len(candles),
            first_time_ms=times[0],
            last_time_ms=times[-1],
            audit_ok=True,
        ),
    )


def ingest_mark_price_archive(
    key: BinanceVisionArchiveKey,
    *,
    archive_bytes: bytes,
    checksum_payload: bytes | str,
) -> BinanceVisionMarkPriceArchive:
    if key.dataset != "markPriceKlines":
        raise ValueError("key.dataset must be markPriceKlines")
    archive_sha256 = _verify_archive_checksum(
        key,
        archive_bytes=archive_bytes,
        checksum_payload=checksum_payload,
    )
    candles = tuple(_parse_mark_row(key, row) for row in _csv_rows_from_archive(key, archive_bytes))
    times = [candle.open_time_ms for candle in candles]
    if times != sorted(times) or len(times) != len(set(times)):
        raise BinanceVisionEvidenceError("Binance Vision mark-price bars must be strictly increasing and unique")
    step = BINANCE_INTERVAL_MS[key.interval]
    for candle in candles:
        if candle.close_time_ms + 1 != candle.open_time_ms + step:
            raise BinanceVisionEvidenceError("mark-price bar has an unexpected close boundary")
    for left, right in zip(times, times[1:]):
        if right - left != step:
            raise BinanceVisionEvidenceError("gap in Binance Vision mark-price history")
    return BinanceVisionMarkPriceArchive(
        key=key,
        candles=candles,
        receipt=_receipt(
            key,
            archive_sha256=archive_sha256,
            row_count=len(candles),
            first_time_ms=times[0],
            last_time_ms=times[-1],
            audit_ok=True,
        ),
    )


def assert_no_archive_revision(
    existing: BinanceVisionArchiveReceipt,
    observed: BinanceVisionArchiveReceipt,
) -> None:
    if existing.identity != observed.identity:
        raise ValueError("archive receipts must have the same logical identity")
    if existing.archive_sha256 != observed.archive_sha256:
        raise BinanceVisionRevisionConflictError(
            "Binance Vision archive content changed for an existing logical archive; "
            "explicit revision review is required"
        )
    if existing.row_count != observed.row_count or existing.first_time_ms != observed.first_time_ms or existing.last_time_ms != observed.last_time_ms:
        raise BinanceVisionRevisionConflictError(
            "Binance Vision archive metadata changed despite matching logical identity"
        )
