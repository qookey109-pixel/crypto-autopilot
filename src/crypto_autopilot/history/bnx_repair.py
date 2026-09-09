"""SHA-pinned BNX reconstruction appendix; execution stays in the existing writer."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from types import SimpleNamespace

from crypto_autopilot.binance.vision import BinanceVisionArchiveKey, _verify_archive_checksum
from crypto_autopilot.history.archive_repair import reconcile_monthly_from_daily
from crypto_autopilot.history.bnx_diagnosis import PublicReader, validate_zip

CONFIG_SHA = "08721e700471fa2a66b686733d21e531ee9216d5607d4a5080d9c2846e985cdd"
BASE_SHA = "fc4e42b855229ecb62e12e681778080c2aa749112036a6e8b3af9e9da98b716a"
TARGET = ("BNXUSDT", "15m", "2022-08")
DESTINATION = "market-data/binance_usdm/crypto-core-v0.1/perp/BNXUSDT/15m/year=2022/month=08/candles.parquet"


class RepairAuthorityError(ValueError):
    pass


def require_clock(now=None):
    now = now or datetime.now(timezone.utc)
    if not datetime(2026, 9, 8, 14, 54, 34, tzinfo=timezone.utc) <= now < datetime(2026, 10, 1, tzinfo=timezone.utc):
        raise RepairAuthorityError("BNX_REPAIR_WINDOW_CLOSED")


def load_contract(config_path, receipt_path, base_bytes, now=None, env=None):
    require_clock(now)
    env = os.environ if env is None else env
    if (env.get("GITHUB_REPOSITORY") != "qookey109-pixel/crypto-autopilot" or
            env.get("GITHUB_REF") != "refs/heads/main" or
            env.get("GITHUB_EVENT_NAME") not in {"schedule", "workflow_dispatch"} or
            env.get("GITHUB_RUN_ATTEMPT") != "1"):
        raise RepairAuthorityError("BNX_REPAIR_MAIN_FRESH_RUN_REQUIRED")
    raw = config_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != CONFIG_SHA or hashlib.sha256(base_bytes).hexdigest() != BASE_SHA:
        raise RepairAuthorityError("BNX_REPAIR_CONFIG_BINDING_MISMATCH")
    receipt = json.loads(receipt_path.read_bytes())
    if receipt != {
        "schema": "bnx-archive-repair-authority-v0.1",
        "status": "AUTHORIZED_ON_PROTECTED_MAIN_MERGE",
        "config": "config/bnx_archive_repair_v0_1.json",
        "config_sha256": CONFIG_SHA,
        "diagnosis_run_id": 34241295251,
        "missing_partition_creation_authorized": True,
        "existing_partition_overwrite_authorized": False,
        "original_authorities_mutated": False,
    }:
        raise RepairAuthorityError("BNX_REPAIR_RECEIPT_BINDING_MISMATCH")
    return json.loads(raw)


def matches(partition):
    return (partition.symbol, partition.interval, partition.period) == TARGET


def reconstruct(partition, contract, reader_factory=PublicReader):
    require_clock()
    if not matches(partition) or partition.r2_key != DESTINATION:
        raise RepairAuthorityError("BNX_REPAIR_TARGET_MISMATCH")
    key = BinanceVisionArchiveKey("klines", "monthly", *TARGET)
    reader = reader_factory()

    def read(url):
        require_clock()
        return reader(url)

    monthly, checksum = read(key.url), read(key.checksum_url)
    if _verify_archive_checksum(key, archive_bytes=monthly, checksum_payload=checksum) != contract["monthly_sha256"]:
        raise RepairAuthorityError("BNX_REPAIR_MONTHLY_REVISION")
    validate_zip(key, monthly)
    daily = []
    for day, sha in contract["daily_sha256"]:
        daily_key = BinanceVisionArchiveKey("klines", "daily", "BNXUSDT", "15m", day)
        reader.allow_day(daily_key)
        data, check = read(daily_key.url), read(daily_key.checksum_url)
        if _verify_archive_checksum(daily_key, archive_bytes=data, checksum_payload=check) != sha:
            raise RepairAuthorityError("BNX_REPAIR_DAILY_REVISION")
        validate_zip(daily_key, data)
        daily.append((daily_key, data, check))
    candidate = reconcile_monthly_from_daily(
        key, monthly, checksum, daily, expected_monthly_sha256=contract["monthly_sha256"]
    )
    rows = candidate.candles
    normalized = json.dumps([
        [c.time_ms, c.open, c.high, c.low, c.close, c.volume] for c in rows
    ], separators=(",", ":"), allow_nan=False).encode()
    digest = hashlib.sha256(normalized).hexdigest()
    if (digest != contract["candidate_sha256"] or len(rows) != 2976 or
            candidate.inserted_rows != 288 or candidate.overlapping_rows_verified != 96):
        raise RepairAuthorityError("BNX_REPAIR_CANDIDATE_MISMATCH")
    lineage = {
        "schema": "bnx-archive-repair-lineage-v0.1",
        "config_sha256": CONFIG_SHA,
        "diagnosis_run_id": 34241295251,
        "monthly_sha256": candidate.monthly_sha256,
        "original_monthly_rows": 2688,
        "original_monthly_audit_ok": False,
        "daily_sha256": list(candidate.daily_sha256),
        "candidate_sha256": digest,
        "candidate_rows": len(rows),
        "inserted_rows": candidate.inserted_rows,
        "overlapping_rows_verified": candidate.overlapping_rows_verified,
        "provider": "binance_usdm",
        "original_monthly_archive_regraded": False,
    }
    # Internal writer adapter, not a fabricated Binance monthly archive receipt.
    result = SimpleNamespace(key=key, candles=rows, receipt=SimpleNamespace(
        archive_sha256=candidate.monthly_sha256, row_count=len(rows),
        first_time_ms=rows[0].time_ms, last_time_ms=rows[-1].time_ms, audit_ok=True,
    ))
    return result, lineage
