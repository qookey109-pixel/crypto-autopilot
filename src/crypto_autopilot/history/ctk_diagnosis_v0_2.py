"""Bounded CTKUSDT 15m public-archive diagnosis v0.2; no R2 or repair path."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

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
    SAFE_AUTHORITY,
    _raw_rows_by_time,
    _utc_iso,
    _verify_raw_overlap,
    validate_zip,
)
from crypto_autopilot.history.ctk_diagnosis_v0_1 import (
    EXPECTED_GAPS,
    EXPECTED_MISSING,
    EXPECTED_ROWS,
    EXPECTED_SHA,
    KEY,
    MAX_DAILY_ARCHIVES,
    OBSERVED_ROWS,
    PublicReader,
    STEP,
)

CONFIG = "config/ctk_archive_diagnosis_v0_2.json"
CONFIG_SHA = "dacd10a6efff73a3aa43f78ea6f40ac9373f05f6f5a9b70f34bf980310043099"
RECEIPT = "research/receipts/2026-09-12-ctk-archive-diagnosis-v0-2-authority.json"

REASON_MAP = {
    "daily archive must cover its entire UTC day": "DAILY_NOT_FULL_UTC_DAY",
    "daily and monthly overlap conflict": "MONTHLY_DAILY_OVERLAP_CONFLICT",
    "official daily archives did not fill every missing timestamp": "MISSING_NOT_FULLY_FILLED",
    "overlap evidence required; include adjacent complete daily archive": "OVERLAP_EVIDENCE_MISSING",
    "reconciled candidate failed original candle audit": "RECONCILED_CANDIDATE_AUDIT_FAILED",
    "conflicting replacement row": "CONFLICTING_REPLACEMENT_ROW",
    "daily archive identity mismatch": "DAILY_IDENTITY_MISMATCH",
    "duplicate daily archive": "DUPLICATE_DAILY_ARCHIVE",
    "daily row escaped monthly scope": "DAILY_ROW_ESCAPED_MONTH",
    "only absent bars may be reconciled": "MONTHLY_NON_ABSENCE_DEFECT",
}
REASON_ALLOWLIST = frozenset(
    set(REASON_MAP.values())
    | {
        "DAILY_ARCHIVE_VALIDATION_REJECTED",
        "RECONCILIATION_REJECTED_UNKNOWN",
    }
)


def clock_gate(now=None):
    now = now or datetime.now(timezone.utc)
    if not datetime(2026, 9, 12, 8, 0, 6, tzinfo=timezone.utc) <= now < datetime(
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
    authority = json.loads((root / RECEIPT).read_bytes())
    if authority != {'schema': 'ctk-archive-diagnosis-authority-v0.2', 'status': 'AUTHORIZED_ON_PROTECTED_MAIN_MERGE', 'config': 'config/ctk_archive_diagnosis_v0_2.json', 'config_sha256': 'dacd10a6efff73a3aa43f78ea6f40ac9373f05f6f5a9b70f34bf980310043099', 'source_failure_run_id': 34682130869, 'source_failure_report_sha256': 'c972f754c8e03bba606f7392e2ac46c2822aade7d8287cf631315b073d6c63ad', 'execution_performed_by_this_receipt': False, 'public_archive_reads_authorized': True, 'aggregate_github_artifact_authorized': True, 'allowlisted_reconciliation_reason_authorized': True, 'automatic_schedule_authorized': False, 'r2_access_authorized': False, 'production_repair_authorized': False, 'source_switch_authorized': False, 'pionex_native_relabel_authorized': False, 'holdout_access_authorized': False, 'trading_authorized': False, 'automatic_model_promotion_authorized': False, 'supersedes_future_diagnosis_execution': 'ctk-archive-diagnosis-v0.1'}:
        raise DiagnosisError("RECEIPT_BINDING_MISMATCH")


def _safe_reconcile_reason(exc):
    message = str(exc)
    if message in REASON_MAP:
        return REASON_MAP[message]
    if "daily archive" in message:
        return "DAILY_ARCHIVE_VALIDATION_REJECTED"
    return "RECONCILIATION_REJECTED_UNKNOWN"


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
        "symbol": "CTKUSDT",
        "interval": "15m",
        "period": "2025-04",
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

    start = int(datetime(2025, 4, 1, tzinfo=timezone.utc).timestamp() * 1000)
    end = int(datetime(2025, 5, 1, tzinfo=timezone.utc).timestamp() * 1000)
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
        f"2025-04-{day:02d}"
        for day in range(1, 31)
        if f"2025-04-{day:02d}" not in missing_dates
    ]
    if not complete_days:
        raise DiagnosisError("NO_COMPLETE_OVERLAP_DAY")
    requested_days = sorted(set(missing_dates) | {complete_days[0]})
    if len(requested_days) > MAX_DAILY_ARCHIVES:
        raise DiagnosisError("DAILY_ARCHIVE_BUDGET_EXCEEDED")

    daily = []
    raw_overlap_rows_verified = 0
    overlap_day = complete_days[0]
    for day in requested_days:
        key = BinanceVisionArchiveKey("klines", "daily", "CTKUSDT", "15m", day)
        reader.allow_day(key)
        try:
            data = reader(key.url)
            check = reader(key.checksum_url)
        except DiagnosisError as exc:
            if str(exc) == "OFFICIAL_ARCHIVE_NOT_FOUND":
                return dict(
                    summary,
                    status="DAILY_ARCHIVE_UNAVAILABLE",
                    unavailable_day=day,
                    missing_start_utc=_utc_iso(missing[0]),
                    missing_end_open_utc=_utc_iso(missing[-1]),
                    missing_end_exclusive_utc=_utc_iso(missing[-1] + STEP),
                    missing_dates=missing_dates,
                )
            raise
        validate_zip(key, data)
        try:
            _verify_archive_checksum(key, archive_bytes=data, checksum_payload=check)
        except BinanceVisionEvidenceError:
            raise DiagnosisError("DAILY_CHECKSUM_VALIDATION_FAILED") from None
        if day == overlap_day:
            raw_overlap_rows_verified = _verify_raw_overlap(monthly_raw, key, data)
        daily.append((key, data, check))

    diagnostics = {
        "observed_monthly_rows": len(candles),
        "expected_monthly_rows": EXPECTED_ROWS,
        "missing_bars": len(missing),
        "gap_count": EXPECTED_GAPS,
        "missing_start_utc": _utc_iso(missing[0]),
        "missing_end_open_utc": _utc_iso(missing[-1]),
        "missing_end_exclusive_utc": _utc_iso(missing[-1] + STEP),
        "missing_dates": missing_dates,
        "overlap_day": overlap_day,
        "raw_overlap_rows_verified": raw_overlap_rows_verified,
    }

    try:
        candidate = reconcile_monthly_from_daily(
            KEY,
            monthly,
            checksum,
            daily,
            expected_monthly_sha256=EXPECTED_SHA,
        )
    except BinanceVisionEvidenceError as exc:
        reason = _safe_reconcile_reason(exc)
        if reason not in REASON_ALLOWLIST:
            raise DiagnosisError("RECONCILIATION_REASON_NOT_ALLOWLISTED")
        return dict(
            summary,
            status="RECONCILIATION_REJECTION_CHARACTERIZED",
            reconciliation_rejection_reason=reason,
            **diagnostics,
        )

    candidate_bytes = json.dumps(
        [[c.time_ms, c.open, c.high, c.low, c.close, c.volume] for c in candidate.candles],
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    return dict(
        summary,
        status="REPAIR_CANDIDATE_REQUIRES_PUBLICATION_AUTHORITY",
        inserted_rows=candidate.inserted_rows,
        overlapping_rows_verified=candidate.overlapping_rows_verified,
        candidate_sha256=hashlib.sha256(candidate_bytes).hexdigest(),
        candidate_row_count=len(candidate.candles),
        daily_sha256=list(candidate.daily_sha256),
        **diagnostics,
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
    return 0 if report["status"] in {
        "REPAIR_CANDIDATE_REQUIRES_PUBLICATION_AUTHORITY",
        "RECONCILIATION_REJECTION_CHARACTERIZED",
    } else 1
