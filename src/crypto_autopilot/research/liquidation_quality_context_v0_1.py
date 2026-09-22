from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, cast

SOURCE_CAPABILITY_ID: Final[str] = "agentfeed"
UPSTREAM_REPOSITORY: Final[str] = "seekdaseek/agentfeed"
UPSTREAM_COMMIT_SHA: Final[str] = "0e1db87a65dc0cc0b890c2257e10e12cd3966cf7"

ALLOWED_INPUT_CLASSES: Final[frozenset[str]] = frozenset(
    {"synthetic_fixture", "existing_non_holdout_fixture"}
)
SIDE_SEMANTICS: Final[frozenset[str]] = frozenset(
    {"LONG_LIQUIDATED", "SHORT_LIQUIDATED"}
)
DEGRADED_COVERAGE: Final[str] = "DEGRADED_OR_UNKNOWN"
VENUE_COVERAGE_PROFILES: Final[dict[str, str]] = {
    "bybit": "UPSTREAM_DECLARED_COMPLETE_UNTHROTTLED",
    "binance": "UPSTREAM_DECLARED_THROTTLED_SNAPSHOT",
    "okx": "UPSTREAM_DECLARED_THROTTLED_UPDATE",
}


@dataclass(frozen=True, slots=True)
class LiquidationQualityContextPolicy:
    prefetched_evidence_ingestion_authorized: bool = True
    network_capture_authorized: bool = False
    mcp_runtime_authorized: bool = False
    provider_api_key_authorized: bool = False
    agentfeed_endpoint_authorized: bool = False
    wallet_creation_authorized: bool = False
    wallet_funding_authorized: bool = False
    private_key_access_authorized: bool = False
    x402_payment_authorized: bool = False
    cross_venue_aggregation_authorized: bool = False
    strategy_router_integration_authorized: bool = False
    daily_opportunity_integration_authorized: bool = False
    automatic_candidate_generation_authorized: bool = False
    automatic_strategy_selection_authorized: bool = False
    r2_write_authorized: bool = False
    holdout_access_authorized: bool = False
    training_authorized: bool = False
    model_promotion_authorized: bool = False
    formal_trade_plan_authorized: bool = False
    real_money_order_authorized: bool = False
    live_real_trading_authorized: bool = False

    def __post_init__(self) -> None:
        values = (
            self.prefetched_evidence_ingestion_authorized,
            self.network_capture_authorized,
            self.mcp_runtime_authorized,
            self.provider_api_key_authorized,
            self.agentfeed_endpoint_authorized,
            self.wallet_creation_authorized,
            self.wallet_funding_authorized,
            self.private_key_access_authorized,
            self.x402_payment_authorized,
            self.cross_venue_aggregation_authorized,
            self.strategy_router_integration_authorized,
            self.daily_opportunity_integration_authorized,
            self.automatic_candidate_generation_authorized,
            self.automatic_strategy_selection_authorized,
            self.r2_write_authorized,
            self.holdout_access_authorized,
            self.training_authorized,
            self.model_promotion_authorized,
            self.formal_trade_plan_authorized,
            self.real_money_order_authorized,
            self.live_real_trading_authorized,
        )
        if any(not isinstance(value, bool) for value in values):
            raise ValueError("liquidation-quality policy flags must be booleans")
        if not self.prefetched_evidence_ingestion_authorized:
            raise ValueError("V0.1 requires prefetched evidence ingestion")
        if any(values[1:]):
            raise ValueError(
                "Liquidation Quality Context V0.1 cannot grant network, payment, "
                "aggregation, routing, storage, training or trading authority"
            )


def _clean_symbol(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("symbol is required")
    symbol = value.strip().upper()
    if any(character.isspace() for character in symbol):
        raise ValueError("symbol cannot contain whitespace")
    return symbol


def _clean_exchange(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("exchange is required")
    exchange = value.strip().lower()
    if exchange not in VENUE_COVERAGE_PROFILES:
        raise ValueError("unsupported liquidation exchange")
    return exchange


def _non_negative_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _positive_number(value: object, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"{label} must be finite")
    if number <= 0:
        raise ValueError(f"{label} must be positive")
    return number


def _coverage_quality(exchange: str, value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("coverage_quality must be a string")
    expected = VENUE_COVERAGE_PROFILES[exchange]
    if value not in {expected, DEGRADED_COVERAGE}:
        raise ValueError(
            f"coverage_quality cannot upgrade or relabel {exchange} coverage"
        )
    return value


def _side_semantics(value: object) -> str:
    if not isinstance(value, str) or value not in SIDE_SEMANTICS:
        raise ValueError(
            "side_semantics must be LONG_LIQUIDATED or SHORT_LIQUIDATED"
        )
    return value


def _normalize_event(
    row: Mapping[str, object],
    *,
    clean_symbol: str,
    decision_time: int,
) -> dict[str, object]:
    exchange = _clean_exchange(row.get("exchange"))
    symbol = _clean_symbol(row.get("symbol"))
    if symbol != clean_symbol:
        raise ValueError("liquidation evidence belongs to another symbol")

    event_timestamp_ms = _non_negative_int(
        row.get("event_timestamp_ms"),
        "event_timestamp_ms",
    )
    observed_at_ms = _non_negative_int(
        row.get("observed_at_ms"),
        "observed_at_ms",
    )
    available_at_ms = _non_negative_int(
        row.get("available_at_ms"),
        "available_at_ms",
    )
    if event_timestamp_ms > observed_at_ms:
        raise ValueError("event cannot be observed before it occurs")
    if observed_at_ms > available_at_ms:
        raise ValueError("evidence cannot be available before observation")
    if available_at_ms > decision_time:
        raise ValueError("future liquidation evidence is not causally available")

    price = _positive_number(row.get("price"), "price")
    quantity = _positive_number(row.get("quantity"), "quantity")
    computed_notional = price * quantity

    supplied_notional = row.get("notional_usd")
    if supplied_notional is not None:
        supplied = _positive_number(supplied_notional, "notional_usd")
        tolerance = max(0.01, computed_notional * 1e-6)
        if abs(supplied - computed_notional) > tolerance:
            raise ValueError("notional_usd is inconsistent with price * quantity")

    return {
        "exchange": exchange,
        "symbol": symbol,
        "coverage_quality": _coverage_quality(
            exchange,
            row.get("coverage_quality"),
        ),
        "side_semantics": _side_semantics(row.get("side_semantics")),
        "event_timestamp_ms": event_timestamp_ms,
        "observed_at_ms": observed_at_ms,
        "available_at_ms": available_at_ms,
        "price": price,
        "quantity": quantity,
        "notional_usd": computed_notional,
    }


def build_liquidation_quality_context(
    *,
    symbol: str,
    as_of_ms: int,
    input_class: str,
    evidence: Sequence[Mapping[str, object]],
    policy: LiquidationQualityContextPolicy = LiquidationQualityContextPolicy(),
) -> dict[str, object]:
    """Normalize caller-supplied liquidation evidence without performing I/O."""

    if not policy.prefetched_evidence_ingestion_authorized:
        raise ValueError("prefetched liquidation evidence ingestion is not authorized")
    if input_class not in ALLOWED_INPUT_CLASSES:
        raise ValueError("V0.1 accepts only synthetic or existing non-holdout fixtures")

    clean_symbol = _clean_symbol(symbol)
    decision_time = _non_negative_int(as_of_ms, "as_of_ms")
    normalized: list[dict[str, object]] = []
    seen: set[tuple[object, ...]] = set()

    for row in evidence:
        if not isinstance(row, Mapping):
            raise ValueError("liquidation evidence row must be an object")
        event = _normalize_event(
            row,
            clean_symbol=clean_symbol,
            decision_time=decision_time,
        )
        duplicate_key = (
            event["exchange"],
            event["symbol"],
            event["side_semantics"],
            event["event_timestamp_ms"],
            event["price"],
            event["quantity"],
        )
        if duplicate_key in seen:
            raise ValueError("duplicate liquidation evidence row")
        seen.add(duplicate_key)
        normalized.append(event)

    normalized.sort(
        key=lambda row: (
            int(cast(int, row["event_timestamp_ms"])),
            str(row["exchange"]),
            str(row["side_semantics"]),
        )
    )

    venues_present = sorted({str(row["exchange"]) for row in normalized})
    return {
        "schema": "qookey-liquidation-quality-context-snapshot-v0.1",
        "symbol": clean_symbol,
        "as_of_ms": decision_time,
        "input_class": input_class,
        "source": {
            "capability_id": SOURCE_CAPABILITY_ID,
            "upstream_repository": UPSTREAM_REPOSITORY,
            "upstream_commit_sha": UPSTREAM_COMMIT_SHA,
        },
        "venues_present": venues_present,
        "venue_coverage_profiles": {
            venue: VENUE_COVERAGE_PROFILES[venue] for venue in venues_present
        },
        "event_count": len(normalized),
        "events": normalized,
        "interpretation": "DESCRIPTIVE_LIQUIDATION_CONTEXT_ONLY",
        "authority": {
            "prefetched_evidence_ingestion_only": True,
            "network_capture_authorized": False,
            "mcp_runtime_authorized": False,
            "provider_api_key_authorized": False,
            "agentfeed_endpoint_authorized": False,
            "wallet_creation_authorized": False,
            "wallet_funding_authorized": False,
            "private_key_access_authorized": False,
            "x402_payment_authorized": False,
            "cross_venue_aggregation_authorized": False,
            "strategy_router_integration_authorized": False,
            "daily_opportunity_integration_authorized": False,
            "automatic_candidate_generation_authorized": False,
            "automatic_strategy_selection_authorized": False,
            "r2_write_authorized": False,
            "holdout_access_authorized": False,
            "training_authorized": False,
            "model_promotion_authorized": False,
            "formal_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_real_trading_authorized": False,
        },
    }


def liquidation_quality_context_policy_from_config(
    payload: Mapping[str, object],
) -> LiquidationQualityContextPolicy:
    if payload.get("schema") != "qookey-liquidation-quality-context-v0.1":
        raise ValueError("unsupported liquidation quality context config")

    source = payload.get("source")
    policy = payload.get("policy")
    if not isinstance(source, Mapping) or not isinstance(policy, Mapping):
        raise ValueError("liquidation quality source/policy are required")
    if source.get("capability_id") != SOURCE_CAPABILITY_ID:
        raise ValueError("liquidation quality capability id mismatch")
    if source.get("upstream_repository") != UPSTREAM_REPOSITORY:
        raise ValueError("liquidation quality upstream repository mismatch")
    if source.get("upstream_commit_sha") != UPSTREAM_COMMIT_SHA:
        raise ValueError("liquidation quality upstream commit pin mismatch")

    if set(cast(Sequence[object], payload.get("allowed_input_classes") or [])) != ALLOWED_INPUT_CLASSES:
        raise ValueError("liquidation quality input-class registry mismatch")
    if set(cast(Sequence[object], payload.get("side_semantics") or [])) != SIDE_SEMANTICS:
        raise ValueError("liquidation side-semantics registry mismatch")
    if payload.get("venue_coverage_profiles") != VENUE_COVERAGE_PROFILES:
        raise ValueError("liquidation venue coverage profile mismatch")
    if payload.get("allowed_coverage_downgrade") != DEGRADED_COVERAGE:
        raise ValueError("liquidation coverage downgrade marker mismatch")

    keys = (
        "prefetched_evidence_ingestion_authorized",
        "network_capture_authorized",
        "mcp_runtime_authorized",
        "provider_api_key_authorized",
        "agentfeed_endpoint_authorized",
        "wallet_creation_authorized",
        "wallet_funding_authorized",
        "private_key_access_authorized",
        "x402_payment_authorized",
        "cross_venue_aggregation_authorized",
        "strategy_router_integration_authorized",
        "daily_opportunity_integration_authorized",
        "automatic_candidate_generation_authorized",
        "automatic_strategy_selection_authorized",
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

    return LiquidationQualityContextPolicy(**values)
