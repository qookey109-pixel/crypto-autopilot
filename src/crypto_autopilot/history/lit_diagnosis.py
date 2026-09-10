"""Bounded LITUSDT public-archive diagnosis; no R2 or repair path."""
from __future__ import annotations

import hashlib
import io
import json
import os
import zipfile
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from crypto_autopilot.binance.vision import (
    BinanceVisionArchiveKey, BinanceVisionEvidenceError, _csv_rows_from_archive,
    _parse_kline_row, _verify_archive_checksum,
)
from crypto_autopilot.historical import audit_candles
from crypto_autopilot.history.archive_repair import reconcile_monthly_from_daily

CONFIG = "config/lit_archive_diagnosis_v0_1.json"
RECEIPT = "research/receipts/2026-09-09-lit-archive-diagnosis-v0-1-authority.json"
CONFIG_SHA = "8b4082c19711b513d18aa4ccc042ec80807a925eb0772d2ce1f28aa20a958004"
EXPECTED_SHA = "246dca9c1bcc046af274cc4d5b61fdd1fb818f243a2ae3c82a20471bdecdd160"
KEY = BinanceVisionArchiveKey("klines", "monthly", "LITUSDT", "15m", "2025-12")
STEP = 900000
MAX_RESPONSE_BYTES = 8_000_000
MAX_TOTAL_BYTES = 20_000_000
MAX_REQUESTS = 12
MAX_DAILY_ARCHIVES = 5

# Exact locally authored messages only; never emit arbitrary exception text.
RECONCILIATION_REASONS = {
    "daily and monthly overlap conflict": "OVERLAP_CONFLICT",
    "daily archive must cover its entire UTC day": "DAILY_INCOMPLETE",
    "official daily archives did not fill every missing timestamp": "MISSING_BARS_REMAIN",
    "daily archive identity mismatch": "DAILY_IDENTITY_MISMATCH",
    "duplicate daily archive": "DUPLICATE_DAILY_ARCHIVE",
    "conflicting replacement row": "REPLACEMENT_CONFLICT",
    "overlap evidence required; include adjacent complete daily archive": "NO_OVERLAP_EVIDENCE",
    "reconciled candidate failed original candle audit": "CANDIDATE_AUDIT_FAILED",
    "only absent bars may be reconciled": "MONTHLY_INVALID",
    "monthly rows outside exact UTC month": "MONTHLY_BOUNDARY_MISMATCH",
    "monthly revision requires separate review": "MONTHLY_REVISION",
}


class DiagnosisError(ValueError):
    pass


def rejection_reason(exc):
    message = str(exc)
    if message.startswith("Binance Vision kline audit failed: "):
        return "DAILY_CANDLE_AUDIT_FAILED"
    if message.startswith(("CHECKSUM filename mismatch:", "Binance Vision archive SHA-256 mismatch:")):
        return "CHECKSUM_VALIDATION_FAILED"
    return RECONCILIATION_REASONS.get(message, "ARCHIVE_VALIDATION_FAILED_UNCLASSIFIED")


def clock_gate(now=None):
    now = now or datetime.now(timezone.utc)
    if not datetime(2026, 9, 9, 11, 33, 46, tzinfo=timezone.utc) <= now < datetime(2026, 10, 1, tzinfo=timezone.utc):
        raise DiagnosisError("EXECUTION_WINDOW_CLOSED")


def load_authority(root, env=None, now=None):
    env = os.environ if env is None else env
    clock_gate(now)
    if (env.get("GITHUB_REPOSITORY"), env.get("GITHUB_REF"), env.get("GITHUB_EVENT_NAME"), env.get("GITHUB_RUN_ATTEMPT")) != (
            "qookey109-pixel/crypto-autopilot", "refs/heads/main", "workflow_dispatch", "1"):
        raise DiagnosisError("FRESH_MAIN_MANUAL_DISPATCH_REQUIRED")
    raw = (root / CONFIG).read_bytes()
    if hashlib.sha256(raw).hexdigest() != CONFIG_SHA:
        raise DiagnosisError("CONFIG_SHA_MISMATCH")
    receipt = json.loads((root / RECEIPT).read_bytes())
    if receipt != {
        "schema": "lit-archive-diagnosis-authority-v0.1",
        "status": "AUTHORIZED_ON_PROTECTED_MAIN_MERGE",
        "config": CONFIG,
        "config_sha256": CONFIG_SHA,
        "public_archive_reads_authorized": True,
        "aggregate_github_artifact_authorized": True,
        "r2_access_authorized": False,
        "production_repair_authorized": False,
    }:
        raise DiagnosisError("RECEIPT_BINDING_MISMATCH")


def validate_zip(key, data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos = archive.infolist()
        if len(infos) != 1 or infos[0].filename != key.csv_filename or infos[0].file_size > MAX_RESPONSE_BYTES:
            raise DiagnosisError("ZIP_STRUCTURE_OR_EXPANSION_LIMIT")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise DiagnosisError("REDIRECT_REJECTED")


class PublicReader:
    def __init__(self):
        self.requests = 0
        self.total_bytes = 0
        self.allowed = {KEY.url, KEY.checksum_url}
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def allow_day(self, key):
        if (key.symbol != KEY.symbol or key.interval != KEY.interval or key.dataset != "klines"
                or key.frequency != "daily" or not key.period.startswith("2025-12-")):
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
        limit = 1024 if url.endswith(".CHECKSUM") else MAX_RESPONSE_BYTES
        try:
            with self.opener.open(Request(url, headers={"User-Agent": "crypto-autopilot-lit-diagnosis-v0.1"}), timeout=30) as response:
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
    observed_sha = _verify_archive_checksum(KEY, archive_bytes=monthly, checksum_payload=checksum)
    summary = {
        "provider": "binance_usdm", "symbol": "LITUSDT", "interval": "15m", "period": "2025-12",
        "monthly_sha256": observed_sha, "r2_accessed": False, "production_repair_performed": False,
        "holdout_accessed": False, "raw_rows_emitted": False,
    }
    if observed_sha != EXPECTED_SHA:
        return dict(summary, status="SOURCE_REVISION_REVIEW_REQUIRED")
    validate_zip(KEY, monthly)
    candles = tuple(_parse_kline_row(row) for row in _csv_rows_from_archive(KEY, monthly))
    audit = audit_candles(candles, "15M")
    if (audit.count != 2906 or len(audit.gaps) != 1 or sum(gap.missing_bars for gap in audit.gaps) != 70
            or audit.duplicate_timestamps or audit.out_of_order_pairs or audit.misaligned_timestamps
            or audit.invalid_candle_timestamps):
        raise DiagnosisError("OBSERVED_ARCHIVE_DOES_NOT_MATCH_FROZEN_INCIDENT")
    start = int(datetime(2025, 12, 1, tzinfo=timezone.utc).timestamp() * 1000)
    end = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    expected = set(range(start, end, STEP))
    present = {candle.time_ms for candle in candles}
    if not present <= expected or len(expected - present) != 70:
        raise DiagnosisError("MONTH_BOUNDARY_MISMATCH")
    days = {datetime.fromtimestamp(value / 1000, timezone.utc).date().isoformat() for value in expected - present}
    overlap = next(f"2025-12-{day:02d}" for day in range(1, 32) if f"2025-12-{day:02d}" not in days)
    days.add(overlap)
    if len(days) > MAX_DAILY_ARCHIVES:
        raise DiagnosisError("DAILY_ARCHIVE_BUDGET_EXCEEDED")
    daily = []
    for day in sorted(days):
        key = BinanceVisionArchiveKey("klines", "daily", "LITUSDT", "15m", day)
        reader.allow_day(key)
        try:
            data, check = reader(key.url), reader(key.checksum_url)
        except DiagnosisError as exc:
            if str(exc) == "OFFICIAL_ARCHIVE_NOT_FOUND":
                return dict(summary, status="DAILY_ARCHIVE_UNAVAILABLE", unavailable_day=day)
            raise
        validate_zip(key, data)
        daily.append((key, data, check))
    try:
        candidate = reconcile_monthly_from_daily(KEY, monthly, checksum, daily, expected_monthly_sha256=EXPECTED_SHA)
    except BinanceVisionEvidenceError as exc:
        return dict(summary, status="DAILY_RECONCILIATION_REJECTED",
                    rejection_reason=rejection_reason(exc))
    normalized = json.dumps(
        [[c.time_ms, c.open, c.high, c.low, c.close, c.volume] for c in candidate.candles],
        separators=(",", ":"), allow_nan=False,
    ).encode()
    return dict(
        summary, status="REPAIR_CANDIDATE_REQUIRES_PUBLICATION_AUTHORITY",
        inserted_rows=candidate.inserted_rows,
        overlapping_rows_verified=candidate.overlapping_rows_verified,
        candidate_sha256=hashlib.sha256(normalized).hexdigest(),
        candidate_row_count=len(candidate.candles),
        daily_sha256=list(candidate.daily_sha256),
    )


def run(root, output):
    load_authority(root)
    reader = PublicReader()
    try:
        report = diagnose(reader)
    except DiagnosisError as exc:
        report = {"status": str(exc), "r2_accessed": False, "production_repair_performed": False}
    except Exception:
        report = {"status": "ARCHIVE_VALIDATION_FAILED", "r2_accessed": False, "production_repair_performed": False}
    report.update(public_requests=reader.requests, response_bytes=reader.total_bytes, config_sha256=CONFIG_SHA)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "REPAIR_CANDIDATE_REQUIRES_PUBLICATION_AUTHORITY" else 1
