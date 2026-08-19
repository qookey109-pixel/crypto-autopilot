from __future__ import annotations

import json
from pathlib import Path
from typing import Any


TRANSPORT_BLOCKER = Path(
    "research/receipts/2026-08-19-provider-equivalence-v0-2-transport-blocked.json"
)
EXPECTED_STAGE = "PROVIDER_EQUIVALENCE_V0_2_METADATA_TRANSPORT_BLOCKED_CAPTURE_SUSPENDED"


def load_transport_blocker() -> dict[str, Any]:
    payload = json.loads(TRANSPORT_BLOCKER.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("transport blocker authority must be an object")
    if payload.get("status") != "PASS" or payload.get("stage") != EXPECTED_STAGE:
        raise RuntimeError("transport blocker authority is not frozen PASS")

    fail_safe = payload.get("capture_fail_safe") or {}
    holdout = payload.get("holdout_state") or {}
    boundary = payload.get("authorization_boundary") or {}
    if not all(isinstance(value, dict) for value in (fail_safe, holdout, boundary)):
        raise RuntimeError("transport blocker authority shape changed")

    if fail_safe.get("scheduled_capture_started") is not False:
        raise RuntimeError("transport blocker no longer proves pre-window suspension")
    if fail_safe.get("complete_capture_receipts_written") != 0:
        raise RuntimeError("transport blocker capture receipt count changed")
    if fail_safe.get("scheduled_capture_suspended_before_window_start") is not True:
        raise RuntimeError("transport blocker suspension timing changed")
    if holdout.get("state") != "SUPERSEDED_UNOPENED_BEFORE_METADATA_CAPTURE_EVIDENCE":
        raise RuntimeError("blocked holdout state changed")
    if holdout.get("holdout_candles_accessed") is not False:
        raise RuntimeError("blocked holdout was unexpectedly accessed")
    if holdout.get("holdout_evaluated") is not False:
        raise RuntimeError("blocked holdout was unexpectedly evaluated")
    if holdout.get("replacement_holdout_frozen") is not False:
        raise RuntimeError("replacement holdout must not already be frozen")

    for key in (
        "metadata_capture_execution_authorized",
        "metadata_only_r2_writes_authorized",
        "holdout_candle_access_authorized",
        "holdout_evaluation_authorized",
        "source_switch_authorized",
        "provider_splicing_authorized",
        "staged_trade_kline_w1_materialization_authorized",
        "backtest_admission_authorized",
        "automatic_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if boundary.get(key) is not False:
            raise RuntimeError(f"transport blocker boundary changed: {key}")
    return payload


def suspended_execution_result(*, requested_mode: str) -> dict[str, Any]:
    if requested_mode not in {"connectivity-preflight", "capture"}:
        raise ValueError(f"unsupported requested mode: {requested_mode}")
    blocker = load_transport_blocker()
    return {
        "status": "SKIP",
        "stage": "PROVIDER_EQUIVALENCE_V0_2_METADATA_TRANSPORT_BLOCKED_CAPTURE_SUSPENDED",
        "requested_mode": requested_mode,
        "blocker_authority": str(TRANSPORT_BLOCKER),
        "next_required_stage": blocker["next_required_stage"],
        "provider_requests_performed": 0,
        "increment_values_emitted": False,
        "r2_client_constructed": False,
        "r2_writes_performed": False,
        "r2_deletes_performed": False,
        "holdout_candles_accessed": False,
        "holdout_evaluated": False,
        "source_switch_authorized": False,
        "provider_splicing_authorized": False,
        "w1_materialization_authorized": False,
        "live_trading_authorized": False,
    }
