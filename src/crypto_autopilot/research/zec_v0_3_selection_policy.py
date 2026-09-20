from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Mapping


SCHEMA = "qookey-zec-strategy-v0-3-development-selection-policy-v0.1"


@dataclass(frozen=True, slots=True)
class ZecV03SelectionPolicy:
    minimum_realized_trades_per_fold: int
    minimum_worst_fold_return_pct_exclusive: float
    minimum_stable_neighbors: int
    minimum_neighbor_worst_return_retention_fraction: float
    primary_metric: str = "worst_fold_return_pct"


def validate_zec_v0_3_selection_policy(
    payload: Mapping[str, Any],
) -> tuple[ZecV03SelectionPolicy, str]:
    if payload.get("schema") != SCHEMA:
        raise ValueError("unexpected ZEC V0.3 selection policy schema")
    if payload.get("status") != "FROZEN_BEFORE_DEVELOPMENT_EXECUTION":
        raise ValueError("selection policy must be frozen before development execution")
    if payload.get("primary_metric") != "worst_fold_return_pct":
        raise ValueError("unexpected ZEC V0.3 selection primary metric")
    if payload.get("complete_matrix_required") is not True:
        raise ValueError("complete development matrix must be required")
    if payload.get("selective_omission_allowed") is not False:
        raise ValueError("selective omission must remain forbidden")
    if payload.get("fresh_confirmation_used_for_selection") is not False:
        raise ValueError("fresh confirmation cannot be used for development selection")

    eligibility = payload.get("eligibility")
    stable = payload.get("stable_neighbor")
    if not isinstance(eligibility, Mapping) or not isinstance(stable, Mapping):
        raise ValueError("selection eligibility and stable-neighbor policy are required")

    minimum_trades = eligibility.get("minimum_realized_trades_per_fold")
    minimum_return = eligibility.get("minimum_worst_fold_return_pct_exclusive")
    minimum_neighbors = stable.get("minimum_count")
    retention = stable.get("minimum_worst_return_retention_fraction")
    if minimum_trades != 30:
        raise ValueError("minimum realized trades per fold must remain frozen at 30")
    if minimum_return != 0.0:
        raise ValueError("minimum worst-fold return boundary must remain frozen at 0.0")
    if minimum_neighbors != 2:
        raise ValueError("minimum stable-neighbor count must remain frozen at 2")
    if retention != 0.75:
        raise ValueError("stable-neighbor retention fraction must remain frozen at 0.75")
    if stable.get("definition") != "ONE_ADJACENT_VALUE_ON_EXACTLY_ONE_FROZEN_AXIS":
        raise ValueError("unexpected stable-neighbor definition")
    if stable.get("neighbor_must_be_eligible") is not True:
        raise ValueError("stable neighbors must independently satisfy eligibility")

    ranking = payload.get("ranking_order")
    expected_ranking = [
        "highest_worst_fold_return_pct",
        "highest_median_fold_return_pct",
        "lowest_worst_fold_drawdown_pct",
        "highest_total_realized_trades",
        "deterministic_candidate_id",
    ]
    if ranking != expected_ranking:
        raise ValueError("ZEC V0.3 development ranking order drifted")

    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise ValueError("selection policy authority block is required")
    if authority.get("selection_policy_frozen") is not True:
        raise ValueError("selection policy must be frozen")
    for key in (
        "offline_development_runner_authorized",
        "fresh_data_read_authorized",
        "fresh_confirmation_access_authorized",
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
            raise ValueError(f"unsafe ZEC V0.3 selection authority: {key}")

    if not isinstance(minimum_trades, int) or minimum_trades < 1:
        raise ValueError("minimum realized trades per fold must be positive")
    if not isinstance(minimum_neighbors, int) or minimum_neighbors < 1:
        raise ValueError("minimum stable-neighbor count must be positive")
    if not isinstance(minimum_return, (int, float)) or not math.isfinite(float(minimum_return)):
        raise ValueError("minimum worst-fold return must be finite")
    if (
        not isinstance(retention, (int, float))
        or not math.isfinite(float(retention))
        or not 0.0 < float(retention) <= 1.0
    ):
        raise ValueError("stable-neighbor retention fraction must be within (0, 1]")

    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return (
        ZecV03SelectionPolicy(
            minimum_realized_trades_per_fold=minimum_trades,
            minimum_worst_fold_return_pct_exclusive=float(minimum_return),
            minimum_stable_neighbors=minimum_neighbors,
            minimum_neighbor_worst_return_retention_fraction=float(retention),
        ),
        hashlib.sha256(encoded).hexdigest(),
    )
