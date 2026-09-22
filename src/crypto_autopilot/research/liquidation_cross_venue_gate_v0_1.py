from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final, cast

INPUT_SCHEMA: Final[str] = (
    "qookey-venue-local-liquidation-summary-snapshot-v0.1"
)
VENUE_LOCAL_ONLY: Final[str] = "VENUE_LOCAL_ONLY"
CROSS_VENUE_BLOCKED: Final[str] = (
    "CROSS_VENUE_AGGREGATION_BLOCKED_UNCALIBRATED_COVERAGE"
)


@dataclass(frozen=True, slots=True)
class LiquidationCrossVenueGatePolicy:
    comparability_gate_authorized: bool = True
    cross_venue_aggregation_authorized: bool = False
    coverage_weighting_authorized: bool = False
    missingness_calibration_authorized: bool = False
    signal_generation_authorized: bool = False
    strategy_router_integration_authorized: bool = False
    daily_opportunity_integration_authorized: bool = False
    automatic_candidate_generation_authorized: bool = False
    automatic_strategy_selection_authorized: bool = False
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
            self.comparability_gate_authorized,
            self.cross_venue_aggregation_authorized,
            self.coverage_weighting_authorized,
            self.missingness_calibration_authorized,
            self.signal_generation_authorized,
            self.strategy_router_integration_authorized,
            self.daily_opportunity_integration_authorized,
            self.automatic_candidate_generation_authorized,
            self.automatic_strategy_selection_authorized,
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
            raise ValueError("cross-venue gate policy flags must be booleans")
        if not self.comparability_gate_authorized:
            raise ValueError("V0.1 requires comparability-gate authority")
        if any(values[1:]):
            raise ValueError(
                "Liquidation Cross-Venue Gate V0.1 cannot grant aggregation, "
                "weighting, calibration, signal, routing, storage, training "
                "or trading authority"
            )


def _non_negative_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def assess_liquidation_cross_venue_gate(
    *,
    summaries: Sequence[Mapping[str, object]],
    policy: LiquidationCrossVenueGatePolicy = LiquidationCrossVenueGatePolicy(),
) -> dict[str, object]:
    """Assess whether venue-local summaries may be directly aggregated.

    V0.1 is intentionally a blocking gate. It never computes a cross-venue
    liquidation total or coverage weight.
    """

    if not policy.comparability_gate_authorized:
        raise ValueError("liquidation comparability gate is not authorized")
    if not summaries:
        raise ValueError("at least one venue-local summary is required")

    symbol: object | None = None
    as_of_ms: object | None = None
    input_class: object | None = None
    seen_venues: set[str] = set()
    venue_metadata: list[dict[str, object]] = []

    for summary in summaries:
        if not isinstance(summary, Mapping):
            raise ValueError("venue-local summary must be an object")
        if summary.get("schema") != INPUT_SCHEMA:
            raise ValueError("unsupported venue-local liquidation summary schema")

        current_symbol = summary.get("symbol")
        current_as_of = summary.get("as_of_ms")
        current_input_class = summary.get("input_class")
        venue = summary.get("venue")
        coverage_quality = summary.get("coverage_quality")
        event_count = _non_negative_int(summary.get("event_count"), "event_count")

        if not isinstance(current_symbol, str) or not current_symbol:
            raise ValueError("summary symbol is required")
        if not isinstance(current_as_of, int) or isinstance(current_as_of, bool):
            raise ValueError("summary as_of_ms must be an integer")
        if current_as_of < 0:
            raise ValueError("summary as_of_ms cannot be negative")
        if not isinstance(current_input_class, str) or not current_input_class:
            raise ValueError("summary input_class is required")
        if not isinstance(venue, str) or not venue:
            raise ValueError("summary venue is required")
        if coverage_quality is not None and (
            not isinstance(coverage_quality, str) or not coverage_quality
        ):
            raise ValueError("coverage_quality must be null or a non-empty string")

        if venue in seen_venues:
            raise ValueError("duplicate venue-local summary")
        seen_venues.add(venue)

        if symbol is None:
            symbol = current_symbol
            as_of_ms = current_as_of
            input_class = current_input_class
        elif (
            current_symbol != symbol
            or current_as_of != as_of_ms
            or current_input_class != input_class
        ):
            raise ValueError(
                "venue-local summaries must share symbol, as_of_ms and input_class"
            )

        venue_metadata.append(
            {
                "venue": venue,
                "coverage_quality": coverage_quality,
                "event_count": event_count,
            }
        )

    venue_metadata.sort(key=lambda item: str(item["venue"]))
    is_cross_venue = len(venue_metadata) > 1
    decision = CROSS_VENUE_BLOCKED if is_cross_venue else VENUE_LOCAL_ONLY

    return {
        "schema": "qookey-liquidation-cross-venue-gate-result-v0.1",
        "symbol": symbol,
        "as_of_ms": as_of_ms,
        "input_class": input_class,
        "venue_count": len(venue_metadata),
        "venues": venue_metadata,
        "cross_venue_requested": is_cross_venue,
        "decision": decision,
        "cross_venue_aggregation_permitted": False,
        "reason": (
            "Coverage missingness and venue weighting are not calibrated."
            if is_cross_venue
            else "Single-venue descriptive summary only."
        ),
        "interpretation": "GOVERNANCE_BLOCKING_GATE_ONLY",
        "authority": {
            "comparability_gate_only": True,
            "cross_venue_aggregation_authorized": False,
            "coverage_weighting_authorized": False,
            "missingness_calibration_authorized": False,
            "signal_generation_authorized": False,
            "strategy_router_integration_authorized": False,
            "daily_opportunity_integration_authorized": False,
            "automatic_candidate_generation_authorized": False,
            "automatic_strategy_selection_authorized": False,
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


def liquidation_cross_venue_gate_policy_from_config(
    payload: Mapping[str, object],
) -> LiquidationCrossVenueGatePolicy:
    if payload.get("schema") != "qookey-liquidation-cross-venue-gate-v0.1":
        raise ValueError("unsupported liquidation cross-venue gate config")
    if payload.get("input_schema") != INPUT_SCHEMA:
        raise ValueError("liquidation cross-venue input schema mismatch")
    if set(cast(Any, payload.get("decisions") or [])) != {
        VENUE_LOCAL_ONLY,
        CROSS_VENUE_BLOCKED,
    }:
        raise ValueError("liquidation cross-venue decision registry mismatch")

    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("liquidation cross-venue gate policy is required")

    keys = (
        "comparability_gate_authorized",
        "cross_venue_aggregation_authorized",
        "coverage_weighting_authorized",
        "missingness_calibration_authorized",
        "signal_generation_authorized",
        "strategy_router_integration_authorized",
        "daily_opportunity_integration_authorized",
        "automatic_candidate_generation_authorized",
        "automatic_strategy_selection_authorized",
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

    return LiquidationCrossVenueGatePolicy(**values)
