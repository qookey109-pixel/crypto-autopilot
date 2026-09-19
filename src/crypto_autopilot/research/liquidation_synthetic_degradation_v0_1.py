from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

INPUT_SCHEMA: Final[str] = "qookey-liquidation-quality-context-snapshot-v0.1"
ALLOWED_INPUT_CLASS: Final[str] = "synthetic_fixture"
DEGRADED_COVERAGE: Final[str] = "DEGRADED_OR_UNKNOWN"


@dataclass(frozen=True, slots=True)
class LiquidationSyntheticDegradationPolicy:
    synthetic_degradation_authorized: bool = True
    real_missingness_estimation_authorized: bool = False
    random_sampling_authorized: bool = False
    coverage_weighting_authorized: bool = False
    cross_venue_aggregation_authorized: bool = False
    signal_generation_authorized: bool = False
    strategy_router_integration_authorized: bool = False
    daily_opportunity_integration_authorized: bool = False
    network_capture_authorized: bool = False
    mcp_runtime_authorized: bool = False
    r2_write_authorized: bool = False
    holdout_access_authorized: bool = False
    training_authorized: bool = False
    model_promotion_authorized: bool = False
    formal_trade_plan_authorized: bool = False
    real_money_order_authorized: bool = False
    live_real_trading_authorized: bool = False

    def __post_init__(self) -> None:
        values = (
            self.synthetic_degradation_authorized,
            self.real_missingness_estimation_authorized,
            self.random_sampling_authorized,
            self.coverage_weighting_authorized,
            self.cross_venue_aggregation_authorized,
            self.signal_generation_authorized,
            self.strategy_router_integration_authorized,
            self.daily_opportunity_integration_authorized,
            self.network_capture_authorized,
            self.mcp_runtime_authorized,
            self.r2_write_authorized,
            self.holdout_access_authorized,
            self.training_authorized,
            self.model_promotion_authorized,
            self.formal_trade_plan_authorized,
            self.real_money_order_authorized,
            self.live_real_trading_authorized,
        )
        if any(not isinstance(value, bool) for value in values):
            raise ValueError("synthetic-degradation policy flags must be booleans")
        if not self.synthetic_degradation_authorized:
            raise ValueError("V0.1 requires synthetic degradation authority")
        if any(values[1:]):
            raise ValueError(
                "Liquidation Synthetic Degradation V0.1 cannot grant real "
                "missingness estimation, random sampling, weighting, aggregation, "
                "signals, routing, storage, training or trading authority"
            )


def _validate_drop_indices(
    drop_event_indices: Sequence[int],
    *,
    event_count: int,
) -> tuple[int, ...]:
    if isinstance(drop_event_indices, (str, bytes)):
        raise ValueError("drop_event_indices must be an integer sequence")

    normalized: list[int] = []
    seen: set[int] = set()
    for value in drop_event_indices:
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError("drop_event_indices must contain non-negative integers")
        if value >= event_count:
            raise ValueError("drop_event_indices contains an out-of-range index")
        if value in seen:
            raise ValueError("drop_event_indices cannot contain duplicates")
        seen.add(value)
        normalized.append(value)

    if not normalized:
        raise ValueError("at least one synthetic event must be dropped")

    return tuple(sorted(normalized))


def degrade_liquidation_snapshot(
    *,
    snapshot: Mapping[str, object],
    venue: str,
    drop_event_indices: Sequence[int],
    policy: LiquidationSyntheticDegradationPolicy = (
        LiquidationSyntheticDegradationPolicy()
    ),
) -> dict[str, object]:
    """Create a deterministic one-venue degraded synthetic snapshot.

    Indices are relative to the selected venue's event order in the validated
    input snapshot. No randomness, I/O, missingness estimate or correction
    weight is used.
    """

    if not policy.synthetic_degradation_authorized:
        raise ValueError("synthetic liquidation degradation is not authorized")
    if snapshot.get("schema") != INPUT_SCHEMA:
        raise ValueError("unsupported liquidation quality snapshot schema")
    if snapshot.get("input_class") != ALLOWED_INPUT_CLASS:
        raise ValueError("V0.1 accepts synthetic_fixture input only")
    if not isinstance(venue, str) or not venue.strip():
        raise ValueError("venue is required")
    clean_venue = venue.strip().lower()

    events = snapshot.get("events")
    if not isinstance(events, list):
        raise ValueError("liquidation snapshot events must be an array")

    selected: list[dict[str, object]] = []
    for row in events:
        if not isinstance(row, Mapping):
            raise ValueError("liquidation event must be an object")
        if row.get("exchange") == clean_venue:
            selected.append(dict(row))

    if not selected:
        raise ValueError("selected venue has no synthetic events to degrade")

    drop_indices = _validate_drop_indices(
        drop_event_indices,
        event_count=len(selected),
    )
    drop_set = set(drop_indices)

    retained: list[dict[str, object]] = []
    for index, row in enumerate(selected):
        if index in drop_set:
            continue
        degraded = dict(row)
        degraded["coverage_quality"] = DEGRADED_COVERAGE
        retained.append(degraded)

    source = snapshot.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("liquidation snapshot source metadata is required")

    authority = snapshot.get("authority")
    if not isinstance(authority, Mapping):
        raise ValueError("liquidation snapshot authority metadata is required")

    return {
        "schema": INPUT_SCHEMA,
        "symbol": snapshot.get("symbol"),
        "as_of_ms": snapshot.get("as_of_ms"),
        "input_class": ALLOWED_INPUT_CLASS,
        "source": dict(source),
        "venues_present": [clean_venue] if retained else [],
        "venue_coverage_profiles": (
            {clean_venue: DEGRADED_COVERAGE} if retained else {}
        ),
        "event_count": len(retained),
        "events": retained,
        "interpretation": "SYNTHETIC_DEGRADED_LIQUIDATION_CONTEXT_ONLY",
        "synthetic_degradation": {
            "venue": clean_venue,
            "original_event_count": len(selected),
            "retained_event_count": len(retained),
            "dropped_event_count": len(drop_indices),
            "drop_event_indices": list(drop_indices),
            "scenario_id": "drop_indices:" + ",".join(
                str(index) for index in drop_indices
            ),
            "real_missingness_rate_estimate": None,
            "correction_weight": None,
            "random_sampling_used": False,
        },
        "authority": {
            **dict(authority),
            "synthetic_degradation_only": True,
            "real_missingness_estimation_authorized": False,
            "random_sampling_authorized": False,
            "coverage_weighting_authorized": False,
            "cross_venue_aggregation_authorized": False,
            "signal_generation_authorized": False,
            "strategy_router_integration_authorized": False,
            "daily_opportunity_integration_authorized": False,
            "network_capture_authorized": False,
            "mcp_runtime_authorized": False,
            "r2_write_authorized": False,
            "holdout_access_authorized": False,
            "training_authorized": False,
            "model_promotion_authorized": False,
            "formal_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_real_trading_authorized": False,
        },
    }


def liquidation_synthetic_degradation_policy_from_config(
    payload: Mapping[str, object],
) -> LiquidationSyntheticDegradationPolicy:
    if payload.get("schema") != "qookey-liquidation-synthetic-degradation-v0.1":
        raise ValueError("unsupported liquidation synthetic degradation config")
    if payload.get("input_schema") != INPUT_SCHEMA:
        raise ValueError("synthetic degradation input schema mismatch")
    if payload.get("allowed_input_class") != ALLOWED_INPUT_CLASS:
        raise ValueError("synthetic degradation input class mismatch")
    if payload.get("degraded_coverage_quality") != DEGRADED_COVERAGE:
        raise ValueError("synthetic degradation coverage marker mismatch")

    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("synthetic degradation policy is required")

    keys = (
        "synthetic_degradation_authorized",
        "real_missingness_estimation_authorized",
        "random_sampling_authorized",
        "coverage_weighting_authorized",
        "cross_venue_aggregation_authorized",
        "signal_generation_authorized",
        "strategy_router_integration_authorized",
        "daily_opportunity_integration_authorized",
        "network_capture_authorized",
        "mcp_runtime_authorized",
        "r2_write_authorized",
        "holdout_access_authorized",
        "training_authorized",
        "model_promotion_authorized",
        "formal_trade_plan_authorized",
        "real_money_order_authorized",
        "live_real_trading_authorized",
    )
    values: dict[str, bool] = {}
    for key in keys:
        value = policy.get(key)
        if not isinstance(value, bool):
            raise ValueError(f"policy.{key} must be a JSON boolean")
        values[key] = value

    return LiquidationSyntheticDegradationPolicy(**values)
