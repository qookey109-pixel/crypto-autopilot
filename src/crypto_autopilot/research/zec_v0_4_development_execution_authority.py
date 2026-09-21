from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


SCHEMA = "qookey-zec-v0-4-development-one-shot-authority-v0.1"
STATUS = "PROPOSED_EFFECTIVE_ONLY_ON_EXPLICIT_PROTECTED_MAIN_PR_MERGE"
AUTHORITY_ID = "zec-v0-4-development-20260921-v0-1"

EXPECTED_SOURCE = {
    "provider": "binance_usdm",
    "delivery": "binance_vision_public_monthly",
    "dataset": "klines",
    "frequency": "monthly",
    "symbol": "ZECUSDT",
    "interval": "15m",
    "source_month_start": "2022-08",
    "source_month_end": "2026-07",
    "development_start_utc": "2022-08-01T00:00:00Z",
    "development_end_exclusive_utc": "2026-08-01T00:00:00Z",
    "archive_count": 48,
    "row_count": 140256,
    "maximum_provider_requests": 96,
    "raw_candles_persisted": False,
    "memory_only": True,
}
EXPECTED_EXECUTION = {
    "trigger": "workflow_dispatch",
    "one_shot": True,
    "maximum_runs": 1,
    "maximum_run_attempts": 1,
    "candidate_count": 6,
    "development_fold_count": 4,
    "development_matrix_cells": 24,
    "complete_matrix_required": True,
    "selective_omission_allowed": False,
    "primary_slippage_bps_per_side": 5.0,
    "funding_fabrication_allowed": False,
    "aggregate_report_artifact_authorized": True,
    "raw_candle_artifact_authorized": False,
    "raw_trade_artifact_authorized": False,
}
EXPECTED_SAFETY_BOUNDARY = {
    "fresh_confirmation_access_authorized": False,
    "fresh_data_read_authorized": False,
    "r2_read_authorized": False,
    "r2_write_authorized": False,
    "formal_holdout_access_authorized": False,
    "source_switch_authorized": False,
    "model_promotion_authorized": False,
    "formal_trade_plan_authorized": False,
    "real_money_order_authorized": False,
    "live_trading_authorized": False,
}


@dataclass(frozen=True, slots=True)
class ZecV04DevelopmentExecutionAuthority:
    authority_id: str
    authority_pr_number: int
    public_binance_vision_read_authorized: bool
    offline_development_execution_authorized: bool
    aggregate_report_artifact_authorized: bool
    effective: bool


def validate_zec_v0_4_development_execution_authority(
    payload: Mapping[str, Any],
    *,
    authority_pr_merged: bool,
    observed_blob_shas: Mapping[str, str] | None = None,
) -> ZecV04DevelopmentExecutionAuthority:
    if payload.get("schema") != SCHEMA:
        raise ValueError("unexpected ZEC V0.4 development authority schema")
    if payload.get("status") != STATUS:
        raise ValueError("unexpected ZEC V0.4 development authority status")
    if payload.get("authority_id") != AUTHORITY_ID:
        raise ValueError("unexpected ZEC V0.4 development authority id")

    pr_number = payload.get("authority_pr_number")
    if isinstance(pr_number, bool) or not isinstance(pr_number, int) or pr_number < 1:
        raise ValueError("authority PR number must be a positive integer")

    if payload.get("source_scope") != EXPECTED_SOURCE:
        raise ValueError("ZEC V0.4 one-shot source scope drifted")
    if payload.get("execution_scope") != EXPECTED_EXECUTION:
        raise ValueError("ZEC V0.4 one-shot execution scope drifted")
    if payload.get("safety_boundary") != EXPECTED_SAFETY_BOUNDARY:
        raise ValueError("ZEC V0.4 one-shot safety boundary drifted")

    conditional = payload.get("conditional_authority")
    if not isinstance(conditional, Mapping):
        raise ValueError("conditional authority block is required")
    expected_conditional = {
        "effective_condition": "AUTHORITY_PR_MERGED_ON_PROTECTED_MAIN",
        "public_binance_vision_read_authorized_after_effective_condition": True,
        "offline_development_execution_authorized_after_effective_condition": True,
        "aggregate_report_artifact_authorized_after_effective_condition": True,
        "provider_private_api_authorized": False,
    }
    if dict(conditional) != expected_conditional:
        raise ValueError("conditional authority boundary drifted")

    bindings = payload.get("bound_git_blobs")
    if not isinstance(bindings, Mapping) or not bindings:
        raise ValueError("authority must bind reviewed Git blobs")
    for path, expected_sha in bindings.items():
        if not isinstance(path, str) or not path:
            raise ValueError("authority blob path is invalid")
        if (
            not isinstance(expected_sha, str)
            or len(expected_sha) != 40
            or any(ch not in "0123456789abcdef" for ch in expected_sha)
        ):
            raise ValueError(f"authority Git blob SHA is invalid: {path}")
    if observed_blob_shas is not None and dict(bindings) != dict(observed_blob_shas):
        raise ValueError("reviewed Git blob bindings do not match execution checkout")

    effective = bool(authority_pr_merged)
    return ZecV04DevelopmentExecutionAuthority(
        authority_id=AUTHORITY_ID,
        authority_pr_number=pr_number,
        public_binance_vision_read_authorized=effective,
        offline_development_execution_authorized=effective,
        aggregate_report_artifact_authorized=effective,
        effective=effective,
    )
