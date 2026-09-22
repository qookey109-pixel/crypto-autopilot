from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, cast


SCHEMA = "qookey-zec-strategy-v0-3-development-matrix-v0.1"
FROZEN_DEVELOPMENT_START = "2022-08-01T00:00:00Z"
FROZEN_DEVELOPMENT_END = "2026-08-01T00:00:00Z"
FROZEN_CONFIRMATION_START = "2026-08-01T00:00:00Z"
FROZEN_CONFIRMATION_END = "2026-09-16T00:00:00Z"
FROZEN_AXES: dict[str, list[object]] = {
    "macd": ["12/26/9", "12/30/7"],
    "trend_regime": ["TREND_STRICT", "TREND_BASIC"],
    "volatility_filter": ["ATR_FILTER_OFF", "ATR_ROLLING_EXTREME_GUARD"],
    "stop_model": ["VOL_STOP_2ATR_BB_HALF", "VOL_STOP_2_5ATR_BB_HALF"],
    "account_risk_fraction": [0.01, 0.025, 0.05, 0.1],
}
FROZEN_FOLDS = [
    (
        "dev-2022-08_to_2023-08",
        "2022-08-01T00:00:00Z",
        "2023-08-01T00:00:00Z",
    ),
    (
        "dev-2023-08_to_2024-08",
        "2023-08-01T00:00:00Z",
        "2024-08-01T00:00:00Z",
    ),
    (
        "dev-2024-08_to_2025-08",
        "2024-08-01T00:00:00Z",
        "2025-08-01T00:00:00Z",
    ),
    (
        "dev-2025-08_to_2026-08",
        "2025-08-01T00:00:00Z",
        "2026-08-01T00:00:00Z",
    ),
]


@dataclass(frozen=True, slots=True)
class ZecV03Candidate:
    candidate_id: str
    macd: str
    trend_regime: str
    volatility_filter: str
    stop_model: str
    account_risk_fraction: float


def _parse_utc(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{label} must be explicit UTC")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} must be valid ISO-8601 UTC") from exc


def build_zec_v0_3_candidate_grid(config: Mapping[str, Any]) -> tuple[ZecV03Candidate, ...]:
    axes = config.get("candidate_axes")
    if not isinstance(axes, Mapping):
        raise ValueError("candidate_axes must be an object")

    names = tuple(FROZEN_AXES)
    values: list[tuple[object, ...]] = []
    for name in names:
        axis = axes.get(name)
        if not isinstance(axis, list) or not axis:
            raise ValueError(f"candidate axis is missing or empty: {name}")
        if len({json.dumps(item, sort_keys=True) for item in axis}) != len(axis):
            raise ValueError(f"candidate axis contains duplicates: {name}")
        values.append(tuple(axis))

    candidates: list[ZecV03Candidate] = []
    for index, combination in enumerate(itertools.product(*values), start=1):
        macd, trend, volatility, stop, risk = combination
        if not all(
            isinstance(value, str) and value
            for value in (macd, trend, volatility, stop)
        ):
            raise ValueError("string candidate axes must contain non-empty strings")
        if (
            isinstance(risk, bool)
            or not isinstance(risk, (int, float))
            or not 0.0 < float(risk) <= 1.0
        ):
            raise ValueError("account_risk_fraction must be within (0, 1]")
        candidates.append(
            ZecV03Candidate(
                candidate_id=f"zec-v0-3-{index:02d}",
                macd=cast(str, macd),
                trend_regime=cast(str, trend),
                volatility_filter=cast(str, volatility),
                stop_model=cast(str, stop),
                account_risk_fraction=float(risk),
            )
        )
    return tuple(candidates)


def validate_zec_v0_3_development_contract(
    config: Mapping[str, Any],
) -> dict[str, object]:
    if config.get("schema") != SCHEMA:
        raise ValueError("unexpected ZEC V0.3 development contract schema")
    if config.get("status") != "PREPARED_OFFLINE_DEVELOPMENT_CONTRACT_ONLY":
        raise ValueError("unexpected ZEC V0.3 development contract status")
    if config.get("symbol") != "ZECUSDT" or config.get("direction") != "LONG_ONLY_RESEARCH":
        raise ValueError("unexpected ZEC V0.3 research identity")
    if (
        config.get("source_timeframe") != "15m"
        or config.get("signal_timeframe") != "30m"
        or config.get("context_timeframe") != "4h"
    ):
        raise ValueError("unexpected ZEC V0.3 timeframe contract")

    axes = config.get("candidate_axes")
    if not isinstance(axes, Mapping) or dict(axes) != FROZEN_AXES:
        raise ValueError("ZEC V0.3 candidate axes drifted from the frozen design")

    development = config.get("development_window")
    confirmation = config.get("fresh_confirmation_window")
    if not isinstance(development, Mapping) or not isinstance(confirmation, Mapping):
        raise ValueError("development and fresh-confirmation windows are required")
    if (
        development.get("start_utc") != FROZEN_DEVELOPMENT_START
        or development.get("end_exclusive_utc") != FROZEN_DEVELOPMENT_END
        or confirmation.get("start_utc") != FROZEN_CONFIRMATION_START
        or confirmation.get("end_exclusive_utc") != FROZEN_CONFIRMATION_END
    ):
        raise ValueError("ZEC V0.3 temporal boundaries drifted from the frozen design")

    development_start = _parse_utc(development.get("start_utc"), "development.start_utc")
    development_end = _parse_utc(
        development.get("end_exclusive_utc"),
        "development.end_exclusive_utc",
    )
    confirmation_start = _parse_utc(
        confirmation.get("start_utc"),
        "fresh_confirmation.start_utc",
    )
    confirmation_end = _parse_utc(
        confirmation.get("end_exclusive_utc"),
        "fresh_confirmation.end_exclusive_utc",
    )
    if not development_start < development_end <= confirmation_start < confirmation_end:
        raise ValueError("development/fresh-confirmation windows overlap or are unordered")
    if development.get("data_role") != "DEVELOPMENT_ONLY_ALREADY_SEEN":
        raise ValueError("development history must remain already-seen development evidence")
    if (
        confirmation.get("accessed") is not False
        or confirmation.get("access_authorized") is not False
    ):
        raise ValueError("fresh confirmation must remain unopened and unauthorized")

    folds = development.get("folds")
    if not isinstance(folds, list) or len(folds) != len(FROZEN_FOLDS):
        raise ValueError("exact frozen chronological development folds are required")
    actual_folds: list[tuple[str, str, str]] = []
    cursor = development_start
    for index, fold in enumerate(folds):
        if not isinstance(fold, Mapping):
            raise ValueError(f"development fold must be an object: {index}")
        fold_id = fold.get("fold_id")
        fold_start_raw = fold.get("start_utc")
        fold_end_raw = fold.get("end_exclusive_utc")
        if not all(isinstance(value, str) and value for value in (fold_id, fold_start_raw, fold_end_raw)):
            raise ValueError(f"development fold identity is invalid: {index}")
        fold_start = _parse_utc(fold_start_raw, f"fold[{index}].start_utc")
        fold_end = _parse_utc(fold_end_raw, f"fold[{index}].end_exclusive_utc")
        if fold_start != cursor or fold_end <= fold_start:
            raise ValueError("development folds must be contiguous, ordered and non-empty")
        cursor = fold_end
        actual_folds.append((cast(str, fold_id), cast(str, fold_start_raw), cast(str, fold_end_raw)))
    if cursor != development_end or actual_folds != FROZEN_FOLDS:
        raise ValueError("development folds drifted from the frozen design")

    candidates = build_zec_v0_3_candidate_grid(config)
    expected = config.get("expected_candidate_count")
    if expected != 64 or len(candidates) != expected:
        raise ValueError("ZEC V0.3 candidate matrix must contain exactly 64 candidates")

    protocol = config.get("development_protocol")
    required_protocol = {
        "complete_candidate_fold_matrix_required": True,
        "selective_omission_allowed": False,
        "robust_first_selection_required": True,
        "stable_neighbor_evidence_required": True,
        "exactly_one_champion_before_fresh_confirmation": True,
        "fresh_confirmation_can_reselect_candidate": False,
        "candidate_selection_from_fresh_confirmation_allowed": False,
    }
    if (
        not isinstance(protocol, Mapping)
        or any(protocol.get(key) is not value for key, value in required_protocol.items())
    ):
        raise ValueError("ZEC V0.3 development protocol boundary mismatch")

    authority = config.get("authority")
    if not isinstance(authority, Mapping):
        raise ValueError("ZEC V0.3 authority block is required")
    if authority.get("offline_contract_validation_authorized") is not True:
        raise ValueError("offline contract validation must be authorized")
    for key in (
        "offline_development_runner_authorized",
        "fresh_data_read_authorized",
        "provider_network_access_authorized",
        "r2_read_authorized",
        "r2_write_authorized",
        "formal_holdout_access_authorized",
        "source_switch_authorized",
        "model_promotion_authorized",
        "formal_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"unsafe ZEC V0.3 authority: {key}")

    payload = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return {
        "status": "PASS",
        "schema": SCHEMA,
        "candidate_count": len(candidates),
        "development_fold_count": len(folds),
        "development_matrix_cells": len(candidates) * len(folds),
        "candidate_ids": tuple(candidate.candidate_id for candidate in candidates),
        "fresh_confirmation_accessed": False,
        "fresh_confirmation_access_authorized": False,
        "contract_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "execution_authorized": False,
        "live_trading_authorized": False,
    }
