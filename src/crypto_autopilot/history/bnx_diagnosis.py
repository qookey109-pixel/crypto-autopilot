"""Bounded public-archive diagnosis, with no R2 or production repair path."""
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

EXPECTED_SHA = "a3351bdf83dad7f503fb5732c88c85253101954c47b0cdb6791a11d61b131543"
CONFIG_SHA = "293187ce50a08a73efc233163b3b5d1aa8c5ed48ceaea942e12b39e644dcac63"
KEY = BinanceVisionArchiveKey("klines", "monthly", "BNXUSDT", "15m", "2022-08")
STEP = 900000
LIMIT = 8000000


class DiagnosisError(ValueError):
    pass


def clock_gate(now=None):
    now = now or datetime.now(timezone.utc)
    if not datetime(2026, 9, 8, tzinfo=timezone.utc) <= now < datetime(2026, 10, 1, tzinfo=timezone.utc):
        raise DiagnosisError("EXECUTION_WINDOW_CLOSED")


def load_authority(root, env=None, now=None):
    env = os.environ if env is None else env
    clock_gate(now)
    if (env.get("GITHUB_REPOSITORY"), env.get("GITHUB_REF"), env.get("GITHUB_EVENT_NAME"), env.get("GITHUB_RUN_ATTEMPT")) != (
            "qookey109-pixel/crypto-autopilot", "refs/heads/main", "workflow_dispatch", "1"):
        raise DiagnosisError("FRESH_MAIN_MANUAL_DISPATCH_REQUIRED")
    raw = (root / "config/bnx_archive_diagnosis_v0_1.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != CONFIG_SHA:
        raise DiagnosisError("CONFIG_SHA_MISMATCH")
    receipt = json.loads((root / "research/receipts/2026-09-08-bnx-archive-diagnosis-v0-1-authority.json").read_bytes())
    if receipt != {
        "schema": "bnx-archive-diagnosis-authority-v0.1",
        "status": "AUTHORIZED_ON_PROTECTED_MAIN_MERGE",
        "config": "config/bnx_archive_diagnosis_v0_1.json",
        "config_sha256": CONFIG_SHA,
        "public_archive_reads_authorized": True,
        "aggregate_github_artifact_authorized": True,
        "r2_access_authorized": False,
        "production_repair_authorized": False,
    }:
        raise DiagnosisError("RECEIPT_BINDING_MISMATCH")


def validate_zip(key, data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos = z.infolist()
        if len(infos) != 1 or infos[0].filename != key.csv_filename or infos[0].file_size > LIMIT:
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
        if key.symbol != KEY.symbol or key.interval != KEY.interval or key.dataset != "klines" or key.frequency != "daily" or not key.period.startswith("2022-08-"):
            raise DiagnosisError("DAY_SCOPE_MISMATCH")
        self.allowed.update((key.url, key.checksum_url))

    def __call__(self, url):
        clock_gate()
        if url not in self.allowed or self.requests >= 12:
            raise DiagnosisError("REQUEST_SCOPE_OR_COUNT_LIMIT")
        remaining = 20000000 - self.total_bytes
        if remaining <= 0:
            raise DiagnosisError("RESPONSE_BYTE_LIMIT")
        self.requests += 1
        limit = 1024 if url.endswith(".CHECKSUM") else LIMIT
        try:
            with self.opener.open(Request(url, headers={"User-Agent": "crypto-autopilot-bnx-diagnosis-v0.1"}), timeout=30) as response:
                data = response.read(min(limit + 1, remaining))
        except HTTPError as exc:
            if exc.code == 404:
                raise DiagnosisError("OFFICIAL_ARCHIVE_NOT_FOUND") from exc
            raise DiagnosisError("OFFICIAL_HTTP_REQUEST_FAILED") from exc
        except (URLError, TimeoutError) as exc:
            raise DiagnosisError("OFFICIAL_TRANSPORT_FAILED") from exc
        self.total_bytes += len(data)
        if len(data) > limit or self.total_bytes >= 20000000:
            raise DiagnosisError("RESPONSE_BYTE_LIMIT")
        return data


def diagnose(reader):
    monthly = reader(KEY.url)
    checksum = reader(KEY.checksum_url)
    observed_sha = _verify_archive_checksum(KEY, archive_bytes=monthly, checksum_payload=checksum)
    summary = {
        "provider": "binance_usdm", "symbol": "BNXUSDT", "interval": "15m", "period": "2022-08",
        "monthly_sha256": observed_sha, "r2_accessed": False, "production_repair_performed": False,
        "holdout_accessed": False, "raw_rows_emitted": False,
    }
    if observed_sha != EXPECTED_SHA:
        return dict(summary, status="SOURCE_REVISION_REVIEW_REQUIRED")
    validate_zip(KEY, monthly)
    candles = tuple(_parse_kline_row(r) for r in _csv_rows_from_archive(KEY, monthly))
    audit = audit_candles(candles, "15M")
    if (audit.count != 2688 or len(audit.gaps) != 1 or sum(g.missing_bars for g in audit.gaps) != 288 or
            audit.duplicate_timestamps or audit.out_of_order_pairs or audit.misaligned_timestamps or audit.invalid_candle_timestamps):
        raise DiagnosisError("OBSERVED_ARCHIVE_DOES_NOT_MATCH_FROZEN_INCIDENT")
    start = int(datetime(2022, 8, 1, tzinfo=timezone.utc).timestamp() * 1000)
    end = int(datetime(2022, 9, 1, tzinfo=timezone.utc).timestamp() * 1000)
    expected = set(range(start, end, STEP))
    present = {c.time_ms for c in candles}
    if not present <= expected or len(expected - present) != 288:
        raise DiagnosisError("MONTH_BOUNDARY_MISMATCH")
    missing = expected - present
    days = {datetime.fromtimestamp(t / 1000, timezone.utc).date().isoformat() for t in missing}
    # Also fetch a complete overlapping day to establish exact row agreement.
    overlap_days = [f"2022-08-{day:02d}" for day in range(1, 32) if f"2022-08-{day:02d}" not in days]
    days.add(overlap_days[0])
    if len(days) > 5:
        raise DiagnosisError("DAILY_ARCHIVE_BUDGET_EXCEEDED")
    daily = []
    for day in sorted(days):
        key = BinanceVisionArchiveKey("klines", "daily", "BNXUSDT", "15m", day)
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
    except BinanceVisionEvidenceError:
        return dict(summary, status="DAILY_RECONCILIATION_REJECTED")
    # Hash only the normalized candidate; no candles enter logs or artifacts.
    candidate_bytes = json.dumps([
        [c.time_ms, c.open, c.high, c.low, c.close, c.volume] for c in candidate.candles
    ], separators=(",", ":"), allow_nan=False).encode()
    return dict(summary, status="REPAIR_CANDIDATE_REQUIRES_PUBLICATION_AUTHORITY",
                inserted_rows=candidate.inserted_rows,
                overlapping_rows_verified=candidate.overlapping_rows_verified,
                candidate_sha256=hashlib.sha256(candidate_bytes).hexdigest(),
                candidate_row_count=len(candidate.candles),
                daily_sha256=list(candidate.daily_sha256))


def run(root, output):
    load_authority(root)  # Reject before creating any public reader.
    reader = PublicReader()
    try:
        report = diagnose(reader)
    except DiagnosisError as exc:
        report = {"status": str(exc), "r2_accessed": False, "production_repair_performed": False}
    except Exception:
        # Never copy arbitrary remote bodies, exception messages or raw rows to logs.
        report = {"status": "ARCHIVE_VALIDATION_FAILED", "r2_accessed": False, "production_repair_performed": False}
    report.update(public_requests=reader.requests, response_bytes=reader.total_bytes,
                  config_sha256=CONFIG_SHA)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "REPAIR_CANDIDATE_REQUIRES_PUBLICATION_AUTHORITY" else 1
