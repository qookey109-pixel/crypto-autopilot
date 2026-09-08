"""Offline reconciliation candidates. No download, persistence or execution authority."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from crypto_autopilot.binance.vision import (
    BinanceVisionArchiveKey, BinanceVisionEvidenceError, _csv_rows_from_archive,
    _parse_kline_row, _verify_archive_checksum, ingest_kline_archive,
)
from crypto_autopilot.binance_historical import BINANCE_INTERVAL_MS, BINANCE_TO_PROJECT_INTERVAL
from crypto_autopilot.historical import audit_candles
from crypto_autopilot.models import Candle


@dataclass(frozen=True)
class RepairCandidate:
    candles: tuple[Candle, ...]
    monthly_sha256: str
    daily_sha256: tuple[tuple[str, str], ...]
    inserted_rows: int
    overlapping_rows_verified: int
    status: str = "REPAIR_CANDIDATE_NOT_AUTHORIZED"
    provider: str = "binance_usdm"
    publication_authorized: bool = False


def reconcile_monthly_from_daily(
    key: BinanceVisionArchiveKey, monthly_bytes: bytes, monthly_checksum: bytes | str,
    daily_archives: list[tuple[BinanceVisionArchiveKey, bytes, bytes | str]],
    *, expected_monthly_sha256: str,
) -> RepairCandidate:
    """Fill only absent timestamps, using checksummed native same-provider daily rows.

    Callers must separately authorize acquiring input bytes and publishing a candidate.
    Every original OHLCV value is preserved; overlapping rows must compare exactly.
    """
    def reject(message):
        raise BinanceVisionEvidenceError(message)
    if key.dataset != "klines" or key.frequency != "monthly" or not "2022-08" <= key.period <= "2026-07":
        reject("repair candidate escaped historical monthly scope")
    if not 1 <= len(daily_archives) <= 31:
        reject("daily archive count outside bounded month")
    monthly_sha = _verify_archive_checksum(key, archive_bytes=monthly_bytes, checksum_payload=monthly_checksum)
    if monthly_sha != expected_monthly_sha256:
        reject("monthly revision requires separate review")
    rows = tuple(_parse_kline_row(r) for r in _csv_rows_from_archive(key, monthly_bytes))
    audit = audit_candles(rows, BINANCE_TO_PROJECT_INTERVAL[key.interval])
    if audit.duplicate_timestamps or audit.out_of_order_pairs or audit.misaligned_timestamps or audit.invalid_candle_timestamps:
        reject("only absent bars may be reconciled")
    start = datetime.fromisoformat(key.period + "-01").replace(tzinfo=timezone.utc)
    end = start.replace(year=start.year + 1, month=1) if start.month == 12 else start.replace(month=start.month + 1)
    lo, hi = int(start.timestamp() * 1000), int(end.timestamp() * 1000)
    step = BINANCE_INTERVAL_MS[key.interval]
    expected = set(range(lo, hi, step))
    original = {r.time_ms: r for r in rows}
    if not original or not set(original) <= expected:
        reject("monthly rows outside exact UTC month")
    missing = expected - set(original)
    if not missing:
        reject("monthly archive already complete")
    merged = dict(original)
    daily_shas = []
    seen_days = set()
    overlaps = 0
    for daily_key, data, checksum in daily_archives:
        if (daily_key.dataset, daily_key.frequency, daily_key.symbol, daily_key.interval) != (
                "klines", "daily", key.symbol, key.interval) or not daily_key.period.startswith(key.period + "-"):
            reject("daily archive identity mismatch")
        if daily_key.period in seen_days:
            reject("duplicate daily archive")
        seen_days.add(daily_key.period)
        archive = ingest_kline_archive(daily_key, archive_bytes=data, checksum_payload=checksum)
        day_start = int(datetime.fromisoformat(daily_key.period).replace(tzinfo=timezone.utc).timestamp() * 1000)
        day_times = set(range(day_start, day_start + 86400000, step))
        observed_times = [r.time_ms for r in archive.candles]
        if len(observed_times) != len(day_times) or set(observed_times) != day_times:
            reject("daily archive must cover its entire UTC day")
        for row in archive.candles:
            if row.time_ms not in expected:
                reject("daily row escaped monthly scope")
            if row.time_ms in original:
                if original[row.time_ms] != row:
                    reject("daily and monthly overlap conflict")
                overlaps += 1
            else:
                if row.time_ms in merged and merged[row.time_ms] != row:
                    reject("conflicting replacement row")
                merged[row.time_ms] = row
        daily_shas.append((daily_key.period, hashlib.sha256(data).hexdigest()))
    if set(merged) != expected:
        reject("official daily archives did not fill every missing timestamp")
    if overlaps == 0:
        reject("overlap evidence required; include adjacent complete daily archive")
    repaired = tuple(merged[t] for t in sorted(merged))
    if not audit_candles(repaired, BINANCE_TO_PROJECT_INTERVAL[key.interval]).ok:
        reject("reconciled candidate failed original candle audit")
    return RepairCandidate(repaired, monthly_sha, tuple(sorted(daily_shas)), len(missing), overlaps)
