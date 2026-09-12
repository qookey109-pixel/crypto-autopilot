from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from crypto_autopilot.binance.lifecycle_gap_policy import POLICY_ID, match_lifecycle_gap
from crypto_autopilot.binance.vision import BinanceVisionArchiveKey
from crypto_autopilot.binance_historical import BINANCE_TO_PROJECT_INTERVAL
from crypto_autopilot.historical import audit_candles
from crypto_autopilot.models import Candle


STRICT_AUDIT_PASS = "STRICT_AUDIT_PASS"
LIFECYCLE_GAP_CLASSIFICATION = "USER_AUTHORIZED_LIFECYCLE_GAP"
VERIFIED_RECONCILIATION = "VERIFIED_MONTHLY_DAILY_RECONCILIATION"
_REPAIR_LINEAGE_SCHEMAS = {
    "bnx-archive-repair-lineage-v0.1",
    "bnx-archive-repair-lineage-v0.2",
    "bnx-archive-repair-lineage-v0.3",
}


class TrainingHistoryQualityError(ValueError):
    pass


def _identity(record: Mapping[str, Any]) -> tuple[str, str, str]:
    symbol = str(record.get("symbol") or "")
    interval = str(record.get("interval") or "")
    period = str(record.get("period") or "")
    if not symbol or interval not in BINANCE_TO_PROJECT_INTERVAL or not period:
        raise TrainingHistoryQualityError("training partition identity mismatch")
    return symbol, interval, period


def _audit(record: Mapping[str, Any], candles: Sequence[Candle]):
    _symbol, interval, _period = _identity(record)
    if len(candles) != int(record.get("source_rows") or -1):
        raise TrainingHistoryQualityError("training partition row count mismatch")
    return audit_candles(tuple(candles), BINANCE_TO_PROJECT_INTERVAL[interval])


def candidate_sha256(candles: Sequence[Candle]) -> str:
    normalized = json.dumps(
        [[c.time_ms, c.open, c.high, c.low, c.close, c.volume] for c in candles],
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    return hashlib.sha256(normalized).hexdigest()


def validate_training_partition(
    record: Mapping[str, Any], candles: Sequence[Candle]
) -> str:
    """Revalidate a materialized history partition before training can use it."""
    if record.get("provider") != "binance_usdm":
        raise TrainingHistoryQualityError("training partition provider mismatch")

    symbol, interval, period = _identity(record)
    audit = _audit(record, candles)
    delivery = record.get("delivery")

    if delivery == "binance_vision":
        if record.get("audit_ok") is True:
            if not audit.ok:
                raise TrainingHistoryQualityError("strict training partition audit failed")
            return STRICT_AUDIT_PASS
        if record.get("audit_ok") is not False:
            raise TrainingHistoryQualityError("training partition audit flag mismatch")
        source_sha = str(record.get("source_archive_sha256") or "")
        key = BinanceVisionArchiveKey("klines", "monthly", symbol, interval, period)
        if match_lifecycle_gap(key, archive_sha256=source_sha, audit=audit) != POLICY_ID:
            raise TrainingHistoryQualityError("unreviewed training partition gap")
        return LIFECYCLE_GAP_CLASSIFICATION

    if delivery == "binance_vision_monthly_daily_reconciliation":
        if record.get("audit_ok") is not True or not audit.ok:
            raise TrainingHistoryQualityError("reconciled training partition audit failed")
        lineage = record.get("repair_lineage")
        if not isinstance(lineage, Mapping):
            raise TrainingHistoryQualityError("reconciled training partition lineage missing")
        if lineage.get("schema") not in _REPAIR_LINEAGE_SCHEMAS:
            raise TrainingHistoryQualityError("reconciled training partition lineage schema mismatch")
        if lineage.get("provider") != "binance_usdm":
            raise TrainingHistoryQualityError("reconciled training partition lineage provider mismatch")
        if lineage.get("original_monthly_audit_ok") is not False:
            raise TrainingHistoryQualityError("reconciled source audit lineage mismatch")
        original_rows = lineage.get("original_monthly_rows")
        if type(original_rows) is not int or original_rows <= 0:
            raise TrainingHistoryQualityError("reconciled source row lineage mismatch")
        if lineage.get("original_monthly_archive_regraded") is not False:
            raise TrainingHistoryQualityError("reconciled source regrade mismatch")
        if int(lineage.get("candidate_rows") or -1) != len(candles):
            raise TrainingHistoryQualityError("reconciled candidate row mismatch")
        if str(lineage.get("monthly_sha256") or "") != str(
            record.get("source_archive_sha256") or ""
        ):
            raise TrainingHistoryQualityError("reconciled monthly SHA mismatch")
        if candidate_sha256(candles) != str(lineage.get("candidate_sha256") or ""):
            raise TrainingHistoryQualityError("reconciled candidate SHA mismatch")
        return VERIFIED_RECONCILIATION

    raise TrainingHistoryQualityError("training partition delivery mismatch")
