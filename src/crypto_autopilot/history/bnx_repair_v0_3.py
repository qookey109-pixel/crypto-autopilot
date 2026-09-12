"""SHA-pinned BNXUSDT 4h reconstruction appendix; manual publication only."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from crypto_autopilot.binance.vision import BinanceVisionArchiveKey, _verify_archive_checksum
from crypto_autopilot.history.archive_repair import reconcile_monthly_from_daily
from crypto_autopilot.history.bnx_diagnosis_v0_2 import validate_zip
from crypto_autopilot.history.bnx_diagnosis_v0_3 import PublicReader

CONFIG_SHA = "283f26de59acd5a978ad54c7781a6fae1db95cecfc8b3cca9c7552ba8ef67987"
BASE_SHA = "fc4e42b855229ecb62e12e681778080c2aa749112036a6e8b3af9e9da98b716a"
EVIDENCE_SHA = "011be2ea56b4c5788418f12ad86fdaa55d0d6a7fe4258089f088bc469922fc4d"
EVIDENCE = "research/receipts/2026-09-12-bnx-archive-diagnosis-v0-3-run-34671635162-report.json"
TARGET = ("BNXUSDT", "4h", "2022-08")
SHARD_INDEX = 3
DESTINATION = "market-data/binance_usdm/crypto-core-v0.1/perp/BNXUSDT/4h/year=2022/month=08/candles.parquet"


class RepairAuthorityError(ValueError):
    pass


def require_clock(now=None):
    now = now or datetime.now(timezone.utc)
    if not datetime(2026, 9, 12, 4, 10, 42, tzinfo=timezone.utc) <= now < datetime(2026, 10, 1, tzinfo=timezone.utc):
        raise RepairAuthorityError("BNX_4H_REPAIR_WINDOW_CLOSED")


def _root_from_config(config_path: Path) -> Path:
    path = Path(config_path).resolve()
    if path.name != "bnx_archive_repair_v0_3.json" or path.parent.name != "config":
        raise RepairAuthorityError("BNX_4H_REPAIR_CONFIG_PATH_MISMATCH")
    return path.parent.parent


def load_contract(config_path, receipt_path, base_bytes, now=None, env=None):
    require_clock(now)
    env = os.environ if env is None else env
    if (
        env.get("GITHUB_REPOSITORY") != "qookey109-pixel/crypto-autopilot"
        or env.get("GITHUB_REF") != "refs/heads/main"
        or env.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
        or env.get("GITHUB_RUN_ATTEMPT") != "1"
    ):
        raise RepairAuthorityError("BNX_4H_REPAIR_FRESH_MAIN_MANUAL_REQUIRED")

    raw = Path(config_path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != CONFIG_SHA:
        raise RepairAuthorityError("BNX_4H_REPAIR_CONFIG_BINDING_MISMATCH")
    if hashlib.sha256(base_bytes).hexdigest() != BASE_SHA:
        raise RepairAuthorityError("BNX_4H_REPAIR_BASE_BINDING_MISMATCH")

    root = _root_from_config(Path(config_path))
    evidence = (root / EVIDENCE).read_bytes()
    if hashlib.sha256(evidence).hexdigest() != EVIDENCE_SHA:
        raise RepairAuthorityError("BNX_4H_REPAIR_EVIDENCE_BINDING_MISMATCH")
    observed = json.loads(evidence)
    if (
        observed.get("status") != "REPAIR_CANDIDATE_REQUIRES_PUBLICATION_AUTHORITY"
        or observed.get("provider") != "binance_usdm"
        or observed.get("symbol") != "BNXUSDT"
        or observed.get("interval") != "4h"
        or observed.get("period") != "2022-08"
        or observed.get("candidate_sha256") != "1580aca66432a28267b72ea32385650cde5b0898b399e4459aeef3c990eeb534"
        or observed.get("candidate_row_count") != 186
        or observed.get("inserted_rows") != 18
        or observed.get("overlapping_rows_verified") != 6
        or observed.get("missing_dates") != ["2022-08-10", "2022-08-11", "2022-08-12"]
    ):
        raise RepairAuthorityError("BNX_4H_REPAIR_EVIDENCE_IDENTITY_MISMATCH")

    receipt = json.loads(Path(receipt_path).read_bytes())
    expected_receipt = {
        "schema": "bnx-archive-repair-authority-v0.3",
        "status": "AUTHORIZED_ON_PROTECTED_MAIN_MERGE",
        "config": "config/bnx_archive_repair_v0_3.json",
        "config_sha256": "283f26de59acd5a978ad54c7781a6fae1db95cecfc8b3cca9c7552ba8ef67987",
        "diagnosis_run_id": 34671635162,
        "diagnosis_report": "research/receipts/2026-09-12-bnx-archive-diagnosis-v0-3-run-34671635162-report.json",
        "diagnosis_report_sha256": "011be2ea56b4c5788418f12ad86fdaa55d0d6a7fe4258089f088bc469922fc4d",
        "shard_index": 3,
        "manual_only": True,
        "missing_partition_creation_authorized": True,
        "existing_partition_overwrite_authorized": False,
        "new_schedule_authorized": False,
        "original_authorities_mutated": False,
    }
    if receipt != expected_receipt:
        raise RepairAuthorityError("BNX_4H_REPAIR_RECEIPT_BINDING_MISMATCH")

    contract = json.loads(raw)
    if (
        contract.get("shard_index") != SHARD_INDEX
        or contract.get("destination_key") != DESTINATION
        or contract.get("existing_partition_overwrite_authorized") is not False
        or contract.get("missing_partition_creation_authorized") is not True
        or contract.get("new_schedule_authorized") is not False
    ):
        raise RepairAuthorityError("BNX_4H_REPAIR_SCOPE_MISMATCH")
    return contract


def matches(partition):
    return (partition.symbol, partition.interval, partition.period) == TARGET


def reconstruct(partition, contract, reader_factory=PublicReader):
    require_clock()
    if not matches(partition) or partition.r2_key != DESTINATION:
        raise RepairAuthorityError("BNX_4H_REPAIR_TARGET_MISMATCH")
    key = BinanceVisionArchiveKey("klines", "monthly", *TARGET)
    reader = reader_factory()

    def read(url):
        require_clock()
        return reader(url)

    monthly, checksum = read(key.url), read(key.checksum_url)
    if _verify_archive_checksum(key, archive_bytes=monthly, checksum_payload=checksum) != contract["monthly_sha256"]:
        raise RepairAuthorityError("BNX_4H_REPAIR_MONTHLY_REVISION")
    validate_zip(key, monthly)

    daily = []
    for day, sha in contract["daily_sha256"]:
        daily_key = BinanceVisionArchiveKey("klines", "daily", "BNXUSDT", "4h", day)
        reader.allow_day(daily_key)
        data, check = read(daily_key.url), read(daily_key.checksum_url)
        if _verify_archive_checksum(daily_key, archive_bytes=data, checksum_payload=check) != sha:
            raise RepairAuthorityError("BNX_4H_REPAIR_DAILY_REVISION")
        validate_zip(daily_key, data)
        daily.append((daily_key, data, check))

    candidate = reconcile_monthly_from_daily(
        key, monthly, checksum, daily, expected_monthly_sha256=contract["monthly_sha256"]
    )
    rows = candidate.candles
    normalized = json.dumps(
        [[c.time_ms, c.open, c.high, c.low, c.close, c.volume] for c in rows],
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    digest = hashlib.sha256(normalized).hexdigest()
    if (
        digest != contract["candidate_sha256"]
        or len(rows) != 186
        or candidate.inserted_rows != 18
        or candidate.overlapping_rows_verified != 6
    ):
        raise RepairAuthorityError("BNX_4H_REPAIR_CANDIDATE_MISMATCH")

    lineage = {
        "schema": "bnx-archive-repair-lineage-v0.3",
        "config_sha256": CONFIG_SHA,
        "diagnosis_run_id": 34671635162,
        "diagnosis_report_sha256": EVIDENCE_SHA,
        "monthly_sha256": candidate.monthly_sha256,
        "original_monthly_rows": 168,
        "original_monthly_audit_ok": False,
        "daily_sha256": list(candidate.daily_sha256),
        "candidate_sha256": digest,
        "candidate_rows": len(rows),
        "inserted_rows": candidate.inserted_rows,
        "overlapping_rows_verified": candidate.overlapping_rows_verified,
        "provider": "binance_usdm",
        "original_monthly_archive_regraded": False,
    }
    result = SimpleNamespace(
        key=key,
        candles=rows,
        receipt=SimpleNamespace(
            archive_sha256=candidate.monthly_sha256,
            row_count=len(rows),
            first_time_ms=rows[0].time_ms,
            last_time_ms=rows[-1].time_ms,
            audit_ok=True,
        ),
    )
    return result, lineage
