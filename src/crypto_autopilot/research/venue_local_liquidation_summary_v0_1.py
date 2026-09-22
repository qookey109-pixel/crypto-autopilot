from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final, cast

INPUT_SCHEMA: Final[str] = "qookey-liquidation-quality-context-snapshot-v0.1"
ALLOWED_VENUES: Final[frozenset[str]] = frozenset({"bybit", "binance", "okx"})


@dataclass(frozen=True, slots=True)
class VenueLocalLiquidationSummaryPolicy:
    venue_local_summary_authorized: bool = True
    cross_venue_aggregation_authorized: bool = False
    coverage_weighting_authorized: bool = False
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
            self.venue_local_summary_authorized,
            self.cross_venue_aggregation_authorized,
            self.coverage_weighting_authorized,
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
            raise ValueError("venue-local summary policy flags must be booleans")
        if not self.venue_local_summary_authorized:
            raise ValueError("V0.1 requires venue-local summary authority")
        if any(values[1:]):
            raise ValueError(
                "Venue-local Liquidation Summary V0.1 cannot grant aggregation, "
                "signal, routing, network, storage, training or trading authority"
            )


def _finite_non_negative(value: object, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"{label} must be finite")
    if number < 0:
        raise ValueError(f"{label} cannot be negative")
    return number


def build_venue_local_liquidation_summary(
    *,
    snapshot: Mapping[str, object],
    venue: str,
    policy: VenueLocalLiquidationSummaryPolicy = VenueLocalLiquidationSummaryPolicy(),
) -> dict[str, object]:
    """Summarize one venue from a validated liquidation-quality snapshot."""

    if not policy.venue_local_summary_authorized:
        raise ValueError("venue-local liquidation summary is not authorized")
    if snapshot.get("schema") != INPUT_SCHEMA:
        raise ValueError("unsupported liquidation snapshot schema")
    if venue not in ALLOWED_VENUES:
        raise ValueError("unsupported liquidation venue")

    events = snapshot.get("events")
    if not isinstance(events, list):
        raise ValueError("liquidation snapshot events must be an array")

    selected: list[Mapping[str, object]] = []
    coverage_values: set[str] = set()
    long_notional = 0.0
    short_notional = 0.0
    max_event_notional = 0.0
    first_event_ms: int | None = None
    last_event_ms: int | None = None

    for row in events:
        if not isinstance(row, Mapping):
            raise ValueError("liquidation event must be an object")
        row_venue = row.get("exchange")
        if row_venue != venue:
            continue
        notional = _finite_non_negative(row.get("notional_usd"), "notional_usd")
        side = row.get("side_semantics")
        if side == "LONG_LIQUIDATED":
            long_notional += notional
        elif side == "SHORT_LIQUIDATED":
            short_notional += notional
        else:
            raise ValueError("unexpected liquidation side semantics")

        coverage = row.get("coverage_quality")
        if not isinstance(coverage, str) or not coverage:
            raise ValueError("coverage_quality is required")
        coverage_values.add(coverage)

        ts = row.get("event_timestamp_ms")
        if not isinstance(ts, int) or isinstance(ts, bool) or ts < 0:
            raise ValueError("event_timestamp_ms must be a non-negative integer")

        max_event_notional = max(max_event_notional, notional)
        first_event_ms = ts if first_event_ms is None else min(first_event_ms, ts)
        last_event_ms = ts if last_event_ms is None else max(last_event_ms, ts)
        selected.append(row)

    if len(coverage_values) > 1:
        raise ValueError(
            "one venue summary cannot mix multiple coverage-quality labels"
        )

    gross_notional = long_notional + short_notional
    side_imbalance = (
        0.0
        if gross_notional == 0.0
        else (long_notional - short_notional) / gross_notional
    )

    coverage_quality = next(iter(coverage_values), None)

    return {
        "schema": "qookey-venue-local-liquidation-summary-snapshot-v0.1",
        "symbol": snapshot.get("symbol"),
        "as_of_ms": snapshot.get("as_of_ms"),
        "input_class": snapshot.get("input_class"),
        "venue": venue,
        "coverage_quality": coverage_quality,
        "event_count": len(selected),
        "long_liquidated_notional_usd": long_notional,
        "short_liquidated_notional_usd": short_notional,
        "gross_liquidated_notional_usd": gross_notional,
        "side_imbalance": side_imbalance,
        "max_event_notional_usd": max_event_notional,
        "first_event_timestamp_ms": first_event_ms,
        "last_event_timestamp_ms": last_event_ms,
        "interpretation": "DESCRIPTIVE_VENUE_LOCAL_SUMMARY_ONLY",
        "authority": {
            "venue_local_summary_only": True,
            "cross_venue_aggregation_authorized": False,
            "coverage_weighting_authorized": False,
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


def venue_local_liquidation_summary_policy_from_config(
    payload: Mapping[str, object],
) -> VenueLocalLiquidationSummaryPolicy:
    if payload.get("schema") != "qookey-venue-local-liquidation-summary-v0.1":
        raise ValueError("unsupported venue-local liquidation summary config")
    if payload.get("input_schema") != INPUT_SCHEMA:
        raise ValueError("venue-local liquidation input schema mismatch")
    if set(cast(Any, payload.get("allowed_venues") or [])) != ALLOWED_VENUES:
        raise ValueError("venue-local liquidation venue registry mismatch")

    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("venue-local liquidation summary policy is required")

    keys = (
        "venue_local_summary_authorized",
        "cross_venue_aggregation_authorized",
        "coverage_weighting_authorized",
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

    return VenueLocalLiquidationSummaryPolicy(**values)
