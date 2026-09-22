from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, cast

from .zec_v0_3_selection_policy import validate_zec_v0_3_selection_policy


SCHEMA = "qookey-zec-strategy-v0-4-development-matrix-v0.1"
FROZEN_DEVELOPMENT_START = "2022-08-01T00:00:00Z"
FROZEN_DEVELOPMENT_END = "2026-08-01T00:00:00Z"
FROZEN_CONFIRMATION_START = "2026-08-01T00:00:00Z"
FROZEN_CONFIRMATION_END = "2026-09-16T00:00:00Z"
FROZEN_SELECTION_POLICY_SHA256 = (
    "6484f59ee6e71156c776bfe43cdf8c4716dae74f936a164e8702e175c731250d"
)
FROZEN_SELECTION_POLICY_PATH = "config/zec_strategy_v0_3_selection_policy_v0_1.json"
FROZEN_AXES: dict[str, list[str]] = {
    "macd": ["12/26/9", "12/30/7"],
    "activation_regime": [
        "TREND_STRICT_BASELINE",
        "TREND_STACKED",
        "TREND_STACKED_MOMENTUM",
    ],
}
FROZEN_REGIME_DEFINITIONS = {
    "TREND_STRICT_BASELINE": {
        "required_4h_conditions": [
            "close_gt_ema200",
            "ema20_gt_ema50",
            "ema20_slope_atr_gt_0",
        ]
    },
    "TREND_STACKED": {
        "required_4h_conditions": [
            "close_gt_ema200",
            "ema20_gt_ema50",
            "ema50_gt_ema200",
            "ema20_slope_atr_gt_0",
        ]
    },
    "TREND_STACKED_MOMENTUM": {
        "required_4h_conditions": [
            "close_gt_ema200",
            "ema20_gt_ema50",
            "ema50_gt_ema200",
            "ema20_slope_atr_gt_0",
            "rsi14_gt_50",
            "macd_histogram_gt_0",
        ]
    },
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
EXPECTED_FIXED_RULES = {
    "volatility_filter": "ATR_ROLLING_EXTREME_GUARD",
    "volatility_filter_definition": (
        "Reject entry when causal 4h ATR14/close is above the causal rolling 90th "
        "percentile of the prior 180 closed 4h bars; current bar excluded."
    ),
    "stop_model": "VOL_STOP_2_5ATR_BB_HALF",
    "account_risk_fraction": 0.01,
    "maximum_leverage": 3,
    "averaging_down": False,
    "martingale": False,
    "pyramiding": False,
    "funding_fabrication_allowed": False,
}


@dataclass(frozen=True, slots=True)
class ZecV04Candidate:
    candidate_id: str
    macd: str
    activation_regime: str


def _parse_utc(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{label} must be explicit UTC")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} must be valid ISO-8601 UTC") from exc


def build_zec_v0_4_candidate_grid(
    config: Mapping[str, Any],
) -> tuple[ZecV04Candidate, ...]:
    axes = config.get("candidate_axes")
    if not isinstance(axes, Mapping) or dict(axes) != FROZEN_AXES:
        raise ValueError("ZEC V0.4 candidate axes drifted from the frozen design")

    candidates: list[ZecV04Candidate] = []
    for index, (macd, activation_regime) in enumerate(
        itertools.product(
            FROZEN_AXES["macd"],
            FROZEN_AXES["activation_regime"],
        ),
        start=1,
    ):
        candidates.append(
            ZecV04Candidate(
                candidate_id=f"zec-v0-4-{index:02d}",
                macd=macd,
                activation_regime=activation_regime,
            )
        )
    return tuple(candidates)


def validate_zec_v0_4_development_contract(
    config: Mapping[str, Any],
    *,
    selection_policy_payload: Mapping[str, Any],
) -> dict[str, object]:
    if config.get("schema") != SCHEMA:
        raise ValueError("unexpected ZEC V0.4 development contract schema")
    if config.get("status") != "PREPARED_OFFLINE_DEVELOPMENT_CONTRACT_ONLY":
        raise ValueError("unexpected ZEC V0.4 development contract status")
    if config.get("symbol") != "ZECUSDT" or config.get("direction") != "LONG_ONLY_RESEARCH":
        raise ValueError("unexpected ZEC V0.4 research identity")
    if (
        config.get("source_timeframe") != "15m"
        or config.get("signal_timeframe") != "30m"
        or config.get("context_timeframe") != "4h"
    ):
        raise ValueError("unexpected ZEC V0.4 timeframe contract")

    lineage = config.get("lineage")
    if not isinstance(lineage, Mapping):
        raise ValueError("ZEC V0.4 lineage is required")
    if lineage.get("v0_3_completion") != (
        "research/receipts/2026-09-21-zec-v0-3-development-completion-v0-1.json"
    ):
        raise ValueError("ZEC V0.4 completion lineage drifted")
    if lineage.get("v0_3_diagnostic") != (
        "research/receipts/2026-09-21-zec-v0-3-development-diagnostic-v0-1.json"
    ):
        raise ValueError("ZEC V0.4 diagnostic lineage drifted")

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
        raise ValueError("ZEC V0.4 temporal boundaries drifted from the frozen design")
    if development.get("data_role") != "DEVELOPMENT_ONLY_ALREADY_SEEN":
        raise ValueError("V0.4 development history must remain already-seen development evidence")
    if (
        confirmation.get("accessed") is not False
        or confirmation.get("access_authorized") is not False
    ):
        raise ValueError("V0.4 fresh confirmation must remain unopened")

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
        raise ValueError("V0.4 development/fresh-confirmation windows overlap or are unordered")

    folds = development.get("folds")
    if not isinstance(folds, list) or len(folds) != len(FROZEN_FOLDS):
        raise ValueError("exact frozen V0.4 chronological folds are required")
    actual_folds: list[tuple[str, str, str]] = []
    cursor = development_start
    for index, fold in enumerate(folds):
        if not isinstance(fold, Mapping):
            raise ValueError(f"development fold must be an object: {index}")
        fold_id = fold.get("fold_id")
        fold_start_raw = fold.get("start_utc")
        fold_end_raw = fold.get("end_exclusive_utc")
        if not all(
            isinstance(value, str) and value
            for value in (fold_id, fold_start_raw, fold_end_raw)
        ):
            raise ValueError(f"development fold identity is invalid: {index}")
        fold_start = _parse_utc(fold_start_raw, f"fold[{index}].start_utc")
        fold_end = _parse_utc(fold_end_raw, f"fold[{index}].end_exclusive_utc")
        if fold_start != cursor or fold_end <= fold_start:
            raise ValueError("V0.4 development folds must be contiguous and ordered")
        cursor = fold_end
        actual_folds.append(
            cast(tuple[str, str, str], (fold_id, fold_start_raw, fold_end_raw))
        )
    if cursor != development_end or actual_folds != FROZEN_FOLDS:
        raise ValueError("V0.4 development folds drifted from the frozen design")

    base_signal = config.get("base_signal")
    expected_base_signal = {
        "trigger": "BULLISH_MACD_CROSSOVER_ON_CLOSED_30M_BAR",
        "execution": "NEXT_30M_OPEN",
        "macd_axis": ["12/26/9", "12/30/7"],
    }
    if not isinstance(base_signal, Mapping) or dict(base_signal) != expected_base_signal:
        raise ValueError("ZEC V0.4 base signal drifted")

    if config.get("activation_regime_axis") != FROZEN_AXES["activation_regime"]:
        raise ValueError("ZEC V0.4 activation regime axis drifted")
    if config.get("activation_regime_definitions") != FROZEN_REGIME_DEFINITIONS:
        raise ValueError("ZEC V0.4 regime definitions drifted")

    fixed_rules = config.get("fixed_rules")
    if not isinstance(fixed_rules, Mapping) or dict(fixed_rules) != EXPECTED_FIXED_RULES:
        raise ValueError("ZEC V0.4 fixed rules drifted")

    candidates = build_zec_v0_4_candidate_grid(config)
    if config.get("expected_candidate_count") != 6 or len(candidates) != 6:
        raise ValueError("ZEC V0.4 must contain exactly 6 candidates")
    if config.get("expected_development_matrix_cells") != 24:
        raise ValueError("ZEC V0.4 must contain exactly 24 development cells")

    policy_ref = config.get("selection_policy")
    if not isinstance(policy_ref, Mapping):
        raise ValueError("ZEC V0.4 selection policy reference is required")
    if policy_ref.get("path") != FROZEN_SELECTION_POLICY_PATH:
        raise ValueError("ZEC V0.4 selection policy path drifted")
    if policy_ref.get("canonical_sha256") != FROZEN_SELECTION_POLICY_SHA256:
        raise ValueError("ZEC V0.4 selection policy hash drifted")
    if policy_ref.get("reuse_without_threshold_change") is not True:
        raise ValueError("V0.4 must reuse the frozen selection thresholds")
    _, policy_sha256 = validate_zec_v0_3_selection_policy(selection_policy_payload)
    if policy_sha256 != FROZEN_SELECTION_POLICY_SHA256:
        raise ValueError("live selection policy bytes no longer match the frozen V0.4 reference")

    protocol = config.get("development_protocol")
    required_protocol = {
        "complete_candidate_fold_matrix_required": True,
        "selective_omission_allowed": False,
        "robust_first_selection_required": True,
        "stable_neighbor_evidence_required": True,
        "exactly_one_champion_before_fresh_confirmation": True,
        "fresh_confirmation_can_reselect_candidate": False,
        "candidate_selection_from_fresh_confirmation_allowed": False,
        "account_risk_sweep_allowed": False,
        "v0_3_selection_threshold_relaxation_allowed": False,
    }
    if not isinstance(protocol, Mapping) or dict(protocol) != required_protocol:
        raise ValueError("ZEC V0.4 development protocol drifted")

    authority = config.get("authority")
    if not isinstance(authority, Mapping):
        raise ValueError("ZEC V0.4 authority block is required")
    if authority.get("offline_contract_validation_authorized") is not True:
        raise ValueError("V0.4 offline contract validation must be authorized")
    for key in (
        "offline_development_runner_authorized",
        "new_data_access_authorized",
        "provider_network_access_authorized",
        "fresh_data_read_authorized",
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
            raise ValueError(f"unsafe ZEC V0.4 authority: {key}")

    payload = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return {
        "status": "PASS",
        "schema": SCHEMA,
        "candidate_count": len(candidates),
        "development_fold_count": len(folds),
        "development_matrix_cells": len(candidates) * len(folds),
        "candidate_ids": tuple(candidate.candidate_id for candidate in candidates),
        "selection_policy_sha256": policy_sha256,
        "fresh_confirmation_accessed": False,
        "fresh_confirmation_access_authorized": False,
        "execution_authorized": False,
        "live_trading_authorized": False,
        "contract_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    }
