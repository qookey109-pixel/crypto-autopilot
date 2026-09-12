"""Bounded BNXUSDT 4h public-archive diagnosis; no R2 or repair path."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from crypto_autopilot.binance.vision import (
    BinanceVisionArchiveKey,
    BinanceVisionEvidenceError,
    _csv_rows_from_archive,
    _parse_kline_row,
    _verify_archive_checksum,
)
from crypto_autopilot.binance_historical import BINANCE_TO_PROJECT_INTERVAL
from crypto_autopilot.historical import audit_candles
from crypto_autopilot.history.archive_repair import reconcile_monthly_from_daily
from crypto_autopilot.history.bnx_diagnosis_v0_2 import (
    DiagnosisError,
    NoRedirect,
    SAFE_AUTHORITY,
    _raw_rows_by_time,
    _utc_iso,
    _verify_raw_overlap,
    validate_zip,
)

EXPECTED_SHA = "1da5c171a2d1ec9913fd4ace2ec35bc6ebe3aeff32a153df9164a876a8a71995"
CONFIG = "config/bnx_archive_diagnosis_v0_3.json"
CONFIG_SHA = "43e68e8412e308feabb7850d3e0015236bc13e384e7b98a7c083be2635386999"
RECEIPT = "research/receipts/2026-09-12-bnx-archive-diagnosis-v0-3-authority.json"
KEY = BinanceVisionArchiveKey("klines", "monthly", "BNXUSDT", "4h", "2022-08")
STEP = 14_400_000
EXPECTED_ROWS = 186
OBSERVED_ROWS = 168
EXPECTED_MISSING = 18
EXPECTED_GAPS = 1
MAX_ARCHIVE_BYTES = 8_000_000
MAX_TOTAL_BYTES = 20_000_000
MAX_REQUESTS = 12


def clock_gate(now=None):
    now = now or datetime.now(timezone.utc)
    if not datetime(2026, 9, 12, 3, 4, 11, tzinfo=timezone.utc) <= now < datetime(
        2026, 10, 1, tzinfo=timezone.utc
    ):
        raise DiagnosisError("EXECUTION_WINDOW_CLOSED")


def load_authority(root, env=None, now=None):
    env = os.environ if env is None else env
    clock_gate(now)
    expected_env = (
        "qookey109-pixel/crypto-autopilot",
        "refs/heads/main",
        "workflow_dispatch",
        "1",
    )
    actual_env = (
        env.get("GITHUB_REPOSITORY"),
        env.get("GITHUB_REF"),
        env.get("GITHUB_EVENT_NAME"),
        env.get("GITHUB_RUN_ATTEMPT"),
    )
    if actual_env != expected_env:
        raise DiagnosisError("FRESH_MAIN_MANUAL_DISPATCH_REQUIRED")
    raw = (root / CONFIG).read_bytes()
    if hashlib.sha256(raw).hexdigest() != CONFIG_SHA:
        raise DiagnosisError("CONFIG_SHA_MISMATCH")
    receipt = json.loads((root / RECEIPT).read_bytes())
    if receipt != {
        "schema": "bnx-archive-diagnosis-authority-v0.3",
        "status": "AUTHORIZED_ON_PROTECTED_MAIN_MERGE",
        "config": CONFIG,
        "config_sha256": CONFIG_SHA,
        "execution_performed_by_this_receipt": False,
        "public_archive_reads_authorized": True,
        "aggregate_github_artifact_authorized": True,
        "automatic_schedule_authorized": False,
        "r2_access_authorized": False,
        "production_repair_authorized": False,
        "source_switch_authorized": False,
        "pionex_native_relabel_authorized": False,
        "holdout_access_authorized": False,
        "trading_authorized": False,
        "automatic_model_promotion_authorized": False,
    }:
        raise DiagnosisError("RECEIPT_BINDING_MISMATCH")


class PublicReader:
    def __init__(self):
        self.requests = 0
        self.total_bytes = 0
        self.allowed = {KEY.url, KEY.checksum_url}
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def allow_day(self, key):
        if (
            key.symbol != KEY.symbol
            or key.interval != KEY.interval
            or key.dataset != "klines"
            or key.frequency != "daily"
            or not key.period.startswith("2022-08-")
        ):
            raise DiagnosisError("DAY_SCOPE_MISMATCH")
        self.allowed.update((key.url, key.checksum_url))

    def __call__(self, url):
        clock_gate()
        if url not in self.allowed or self.requests >= MAX_REQUESTS:
            raise DiagnosisError("REQUEST_SCOPE_OR_COUNT_LIMIT")
        remaining = MAX_TOTAL_BYTES - self.total_bytes
        if remaining <= 0:
            raise DiagnosisError("RESPONSE_BYTE_LIMIT")
        self.requests += 1
        limit = 1024 if url.endswith(".CHECKSUM") else MAX_ARCHIVE_BYTES
        try:
            with self.opener.open(
                Request(url, headers={"User-Agent": "crypto-autopilot-bnx-diagnosis-v0.3"}),
                timeout=30,
            ) as response:
                data = response.read(min(limit + 1, remaining))
        except HTTPError as exc:
            if exc.code == 404:
                raise DiagnosisError("OFFICIAL_ARCHIVE_NOT_FOUND") from exc
            raise DiagnosisError("OFFICIAL_HTTP_REQUEST_FAILED") from exc
        except (URLError, TimeoutError) as exc:
            raise DiagnosisError("OFFICIAL_TRANSPORT_FAILED") from exc
        self.total_bytes += len(data)
        if len(data) > limit or self.total_bytes >= MAX_TOTAL_BYTES:
            raise DiagnosisError("RESPONSE_BYTE_LIMIT")
        return data


def diagnose(reader):
    monthly = reader(KEY.url)
    checksum = reader(KEY.checksum_url)
    try:
        observed_sha = _verify_archive_checksum(
            KEY, archive_bytes=monthly, checksum_payload=checksum
        )
    except BinanceVisionEvidenceError:
        raise DiagnosisError("MONTHLY_CHECKSUM_VALIDATION_FAILED") from None
    summary = {
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "symbol": "BNXUSDT",
        "interval": "4h",
        "period": "2022-08",
        "monthly_sha256": observed_sha,
        **SAFE_AUTHORITY,
    }
    if observed_sha != EXPECTED_SHA:
        return dict(summary, status="SOURCE_REVISION_REVIEW_REQUIRED")

    validate_zip(KEY, monthly)
    try:
        monthly_raw = _raw_rows_by_time(KEY, monthly)
        candles = tuple(_parse_kline_row(row) for row in _csv_rows_from_archive(KEY, monthly))
    except BinanceVisionEvidenceError:
        raise DiagnosisError("MONTHLY_ARCHIVE_VALIDATION_FAILED") from None

    audit = audit_candles(candles, BINANCE_TO_PROJECT_INTERVAL[KEY.interval])
    if (
        audit.count != OBSERVED_ROWS
        or len(audit.gaps) != EXPECTED_GAPS
        or sum(gap.missing_bars for gap in audit.gaps) != EXPECTED_MISSING
        or audit.duplicate_timestamps
        or audit.out_of_order_pairs
        or audit.misaligned_timestamps
        or audit.invalid_candle_timestamps
    ):
        raise DiagnosisError("OBSERVED_ARCHIVE_DOES_NOT_MATCH_FROZEN_INCIDENT")

    start = int(datetime(2022, 8, 1, tzinfo=timezone.utc).timestamp() * 1000)
    end = int(datetime(2022, 9, 1, tzinfo=timezone.utc).timestamp() * 1000)
    expected = set(range(start, end, STEP))
    present = {candle.time_ms for candle in candles}
    missing = sorted(expected - present)
    if (
        len(expected) != EXPECTED_ROWS
        or not present <= expected
        or len(missing) != EXPECTED_MISSING
        or any(b - a != STEP for a, b in zip(missing, missing[1:]))
    ):
        raise DiagnosisError("MONTH_BOUNDARY_OR_GAP_SHAPE_MISMATCH")

    missing_dates = sorted({
        datetime.fromtimestamp(time_ms / 1000, timezone.utc).date().isoformat()
        for time_ms in missing
    })
    complete_days = [
        f"2022-08-{day:02d}"
        for day in range(1, 32)
        if f"2022-08-{day:02d}" not in missing_dates
    ]
    if not complete_days:
        raise DiagnosisError("NO_COMPLETE_OVERLAP_DAY")
    requested_days = sorted(set(missing_dates) | {complete_days[0]})
    if len(requested_days) > 5:
        raise DiagnosisError("DAILY_ARCHIVE_BUDGET_EXCEEDED")

    daily = []
    raw_overlap_rows_verified = 0
    overlap_day = complete_days[0]
    for day in requested_days:
        key = BinanceVisionArchiveKey("klines", "daily", "BNXUSDT", "4h", day)
        reader.allow_day(key)
        try:
            data = reader(key.url)
            check = reader(key.checksum_url)
        except DiagnosisError as exc:
            if str(exc) == "OFFICIAL_ARCHIVE_NOT_FOUND":
                return dict(summary, status="DAILY_ARCHIVE_UNAVAILABLE", unavailable_day=day)
            raise
        validate_zip(key, data)
        try:
            _verify_archive_checksum(key, archive_bytes=data, checksum_payload=check)
        except BinanceVisionEvidenceError:
            raise DiagnosisError("DAILY_CHECKSUM_VALIDATION_FAILED") from None
        if day == overlap_day:
            raw_overlap_rows_verified = _verify_raw_overlap(monthly_raw, key, data)
        daily.append((key, data, check))

    try:
        candidate = reconcile_monthly_from_daily(
            KEY,
            monthly,
            checksum,
            daily,
            expected_monthly_sha256=EXPECTED_SHA,
        )
    except BinanceVisionEvidenceError:
        return dict(summary, status="DAILY_RECONCILIATION_REJECTED")

    candidate_bytes = json.dumps(
        [[c.time_ms, c.open, c.high, c.low, c.close, c.volume] for c in candidate.candles],
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    return dict(
        summary,
        status="REPAIR_CANDIDATE_REQUIRES_PUBLICATION_AUTHORITY",
        observed_monthly_rows=len(candles),
        expected_monthly_rows=EXPECTED_ROWS,
        missing_bars=len(missing),
        gap_count=EXPECTED_GAPS,
        missing_start_utc=_utc_iso(missing[0]),
        missing_end_open_utc=_utc_iso(missing[-1]),
        missing_end_exclusive_utc=_utc_iso(missing[-1] + STEP),
        missing_dates=missing_dates,
        overlap_day=overlap_day,
        raw_overlap_rows_verified=raw_overlap_rows_verified,
        inserted_rows=candidate.inserted_rows,
        overlapping_rows_verified=candidate.overlapping_rows_verified,
        candidate_sha256=hashlib.sha256(candidate_bytes).hexdigest(),
        candidate_row_count=len(candidate.candles),
        daily_sha256=list(candidate.daily_sha256),
    )


def run(root, output):
    load_authority(root)
    reader = PublicReader()
    try:
        report = diagnose(reader)
    except DiagnosisError as exc:
        report = dict(SAFE_AUTHORITY, status=str(exc))
    except Exception:
        report = dict(SAFE_AUTHORITY, status="ARCHIVE_VALIDATION_FAILED")
    report.update(
        public_requests=reader.requests,
        response_bytes=reader.total_bytes,
        config_sha256=CONFIG_SHA,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "REPAIR_CANDIDATE_REQUIRES_PUBLICATION_AUTHORITY" else 1
