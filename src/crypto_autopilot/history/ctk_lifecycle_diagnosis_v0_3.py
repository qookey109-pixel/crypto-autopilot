"""Bounded CTKUSDT monthly lifecycle-shape diagnosis v0.3; no R2 or repair path."""
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
from crypto_autopilot.binance_historical import BINANCE_INTERVAL_MS, BINANCE_TO_PROJECT_INTERVAL
from crypto_autopilot.historical import audit_candles
from crypto_autopilot.history.bnx_diagnosis_v0_2 import (
    DiagnosisError,
    NoRedirect,
    SAFE_AUTHORITY,
    _utc_iso,
    validate_zip,
)

CONFIG = "config/ctk_lifecycle_diagnosis_v0_3.json"
CONFIG_SHA = "1cf6d90f8a1d666d2548c629fff5804e05146808599c057e829b19422025f51a"
RECEIPT = "research/receipts/2026-09-12-ctk-lifecycle-diagnosis-v0-3-authority.json"
INTERVALS = ("15m", "1h", "4h")
KEYS = {
    interval: BinanceVisionArchiveKey("klines", "monthly", "CTKUSDT", interval, "2025-04")
    for interval in INTERVALS
}
MAX_REQUESTS = 6
MAX_ARCHIVE_BYTES = 8_000_000
MAX_TOTAL_BYTES = 24_000_000
MONTH_START_MS = int(datetime(2025, 4, 1, tzinfo=timezone.utc).timestamp() * 1000)
MONTH_END_MS = int(datetime(2025, 5, 1, tzinfo=timezone.utc).timestamp() * 1000)


def clock_gate(now=None):
    now = now or datetime.now(timezone.utc)
    if not datetime(2026, 9, 12, 8, 0, tzinfo=timezone.utc) <= now < datetime(
        2026, 10, 1, tzinfo=timezone.utc
    ):
        raise DiagnosisError("EXECUTION_WINDOW_CLOSED")


def _expected_receipt():
    return {
        "schema": "ctk-lifecycle-diagnosis-authority-v0.3",
        "status": "AUTHORIZED_ON_PROTECTED_MAIN_MERGE",
        "config": CONFIG,
        "config_sha256": CONFIG_SHA,
        "source_v0_2_run_id": 34683490666,
        "source_v0_2_artifact_id": 10294243218,
        "source_v0_2_artifact_zip_sha256": "8df846b5e5291752e7468d8525021a10333464f01ecf625e50b4707d00b8b625",
        "source_v0_2_report_sha256": "dd86d17c7ff04b4ee765a1454d303c9cf163f396ef7654380ad2337d23b78332",
        "execution_performed_by_this_receipt": False,
        "public_archive_reads_authorized": True,
        "aggregate_github_artifact_authorized": True,
        "automatic_schedule_authorized": False,
        "r2_access_authorized": False,
        "production_repair_authorized": False,
        "lifecycle_publication_authorized": False,
        "training_cutoff_change_authorized": False,
        "source_switch_authorized": False,
        "pionex_native_relabel_authorized": False,
        "holdout_access_authorized": False,
        "trading_authorized": False,
        "automatic_model_promotion_authorized": False,
        "supersedes_future_diagnosis_execution": "ctk-archive-diagnosis-v0.2",
    }


def load_authority(root, env=None, now=None):
    env = os.environ if env is None else env
    clock_gate(now)
    actual_env = (
        env.get("GITHUB_REPOSITORY"),
        env.get("GITHUB_REF"),
        env.get("GITHUB_EVENT_NAME"),
        env.get("GITHUB_RUN_ATTEMPT"),
    )
    expected_env = (
        "qookey109-pixel/crypto-autopilot",
        "refs/heads/main",
        "workflow_dispatch",
        "1",
    )
    if actual_env != expected_env:
        raise DiagnosisError("FRESH_MAIN_MANUAL_DISPATCH_REQUIRED")
    raw = (root / CONFIG).read_bytes()
    if hashlib.sha256(raw).hexdigest() != CONFIG_SHA:
        raise DiagnosisError("CONFIG_SHA_MISMATCH")
    receipt = json.loads((root / RECEIPT).read_bytes())
    if receipt != _expected_receipt():
        raise DiagnosisError("RECEIPT_BINDING_MISMATCH")


class PublicReader:
    def __init__(self):
        self.requests = 0
        self.total_bytes = 0
        self.allowed = {
            url
            for key in KEYS.values()
            for url in (key.url, key.checksum_url)
        }
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

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
                Request(
                    url,
                    headers={"User-Agent": "crypto-autopilot-ctk-lifecycle-diagnosis-v0.3"},
                ),
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
        if len(data) > limit or self.total_bytes > MAX_TOTAL_BYTES:
            raise DiagnosisError("RESPONSE_BYTE_LIMIT")
        return data


def _missing_segments(present: set[int], step_ms: int) -> list[dict[str, object]]:
    if any(value < MONTH_START_MS or value >= MONTH_END_MS for value in present):
        raise DiagnosisError("ROW_ESCAPED_MONTH")
    expected = set(range(MONTH_START_MS, MONTH_END_MS, step_ms))
    missing = sorted(expected - present)
    if not missing:
        return []
    segments = []
    start = previous = missing[0]
    count = 1
    for value in missing[1:]:
        if value == previous + step_ms:
            previous = value
            count += 1
            continue
        segments.append(
            {
                "start_utc": _utc_iso(start),
                "end_exclusive_utc": _utc_iso(previous + step_ms),
                "missing_bars": count,
            }
        )
        start = previous = value
        count = 1
    segments.append(
        {
            "start_utc": _utc_iso(start),
            "end_exclusive_utc": _utc_iso(previous + step_ms),
            "missing_bars": count,
        }
    )
    return segments


def _diagnose_interval(reader, interval):
    key = KEYS[interval]
    archive = reader(key.url)
    checksum = reader(key.checksum_url)
    try:
        observed_sha = _verify_archive_checksum(
            key, archive_bytes=archive, checksum_payload=checksum
        )
        validate_zip(key, archive)
        candles = tuple(
            _parse_kline_row(row) for row in _csv_rows_from_archive(key, archive)
        )
    except BinanceVisionEvidenceError:
        raise DiagnosisError("MONTHLY_ARCHIVE_VALIDATION_FAILED") from None
    if not candles:
        raise DiagnosisError("EMPTY_MONTHLY_ARCHIVE")
    audit = audit_candles(candles, BINANCE_TO_PROJECT_INTERVAL[interval])
    step_ms = BINANCE_INTERVAL_MS[interval]
    present = {candle.time_ms for candle in candles}
    segments = _missing_segments(present, step_ms)
    return {
        "monthly_sha256": observed_sha,
        "row_count": len(candles),
        "expected_monthly_rows": (MONTH_END_MS - MONTH_START_MS) // step_ms,
        "first_timestamp_utc": _utc_iso(min(present)),
        "last_timestamp_utc": _utc_iso(max(present)),
        "missing_bars": sum(int(segment["missing_bars"]) for segment in segments),
        "missing_segments": segments,
        "internal_gap_count": len(audit.gaps),
        "internal_missing_bars": sum(gap.missing_bars for gap in audit.gaps),
        "duplicate_timestamps": len(audit.duplicate_timestamps),
        "out_of_order_pairs": len(audit.out_of_order_pairs),
        "misaligned_timestamps": len(audit.misaligned_timestamps),
        "invalid_candle_timestamps": len(audit.invalid_candle_timestamps),
    }


def diagnose(reader):
    intervals = {
        interval: _diagnose_interval(reader, interval) for interval in INTERVALS
    }
    return {
        "status": "LIFECYCLE_SHAPE_CHARACTERIZED",
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "symbol": "CTKUSDT",
        "period": "2025-04",
        "intervals": intervals,
        "source_v0_2_run_id": 34683490666,
        "source_v0_2_report_sha256": "dd86d17c7ff04b4ee765a1454d303c9cf163f396ef7654380ad2337d23b78332",
        **SAFE_AUTHORITY,
    }


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
    return 0 if report["status"] == "LIFECYCLE_SHAPE_CHARACTERIZED" else 1
