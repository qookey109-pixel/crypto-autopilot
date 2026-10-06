from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

_FEATURES: Final[tuple[str, ...]] = (
    "relative_volume",
    "volume_zscore",
    "oi_change_pct",
    "oi_acceleration",
    "funding_rate",
    "liquidation_imbalance",
    "vwap_zscore",
    "volatility_compression_ratio",
    "volatility_expansion_ratio",
    "market_breadth",
)


@dataclass(frozen=True, slots=True)
class MarketEventRadarPolicy:
    prefetched_feature_ingestion_authorized: bool = True
    network_capture_authorized: bool = False
    opportunity_score_change_authorized: bool = False
    strategy_router_change_authorized: bool = False
    automatic_candidate_generation_authorized: bool = False
    provider_access_authorized: bool = False
    storage_write_authorized: bool = False
    training_authorized: bool = False
    holdout_access_authorized: bool = False
    live_trading_authorized: bool = False

    def __post_init__(self) -> None:
        values = (
            self.prefetched_feature_ingestion_authorized,
            self.network_capture_authorized,
            self.opportunity_score_change_authorized,
            self.strategy_router_change_authorized,
            self.automatic_candidate_generation_authorized,
            self.provider_access_authorized,
            self.storage_write_authorized,
            self.training_authorized,
            self.holdout_access_authorized,
            self.live_trading_authorized,
        )
        if any(not isinstance(value, bool) for value in values):
            raise ValueError("market event radar policy flags must be booleans")
        if not self.prefetched_feature_ingestion_authorized:
            raise ValueError("V0.1 requires prefetched feature ingestion")
        if any(values[1:]):
            raise ValueError("Market Event Radar V0.1 cannot grant runtime or trading authority")


def _clean_symbol(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("symbol is required")
    symbol = value.strip().upper()
    if any(character.isspace() for character in symbol):
        raise ValueError("symbol cannot contain whitespace")
    return symbol


def _non_negative_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _finite(value: object, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"{label} must be finite")
    return number


def _bounded(value: object, label: str, lower: float, upper: float) -> float:
    number = _finite(value, label)
    if not lower <= number <= upper:
        raise ValueError(f"{label} must be within [{lower}, {upper}]")
    return number


def build_market_event_radar_snapshot(
    *,
    symbol: str,
    as_of_ms: int,
    observed_at_ms: int,
    available_at_ms: int,
    features: Mapping[str, object],
    policy: MarketEventRadarPolicy = MarketEventRadarPolicy(),
) -> dict[str, object]:
    """Normalize deterministic point-in-time market-event features.

    This function performs no network I/O and emits descriptive event tags only.
    Event tags are not an opportunity score, strategy route, or trade instruction.
    """

    if not policy.prefetched_feature_ingestion_authorized:
        raise ValueError("prefetched feature ingestion is not authorized")
    clean_symbol = _clean_symbol(symbol)
    decision_time = _non_negative_int(as_of_ms, "as_of_ms")
    observed = _non_negative_int(observed_at_ms, "observed_at_ms")
    available = _non_negative_int(available_at_ms, "available_at_ms")
    if observed > available:
        raise ValueError("features cannot be available before observation")
    if available > decision_time:
        raise ValueError("future market-event features are not causally available")
    if not isinstance(features, Mapping):
        raise ValueError("features must be an object")

    normalized: dict[str, float] = {}
    for field in _FEATURES:
        if field not in features or features[field] is None:
            continue
        if field in {"relative_volume", "volatility_compression_ratio", "volatility_expansion_ratio"}:
            value = _finite(features[field], field)
            if value < 0.0:
                raise ValueError(f"{field} cannot be negative")
        elif field in {"liquidation_imbalance", "market_breadth"}:
            value = _bounded(features[field], field, -1.0, 1.0)
        else:
            value = _finite(features[field], field)
        normalized[field] = value
    if not normalized:
        raise ValueError("at least one supported market-event feature is required")

    events: list[str] = []
    if normalized.get("relative_volume", 0.0) >= 1.0:
        events.append("RVOL_AT_OR_ABOVE_BASELINE")
    if "volume_zscore" in normalized:
        events.append("VOLUME_Z_POSITIVE" if normalized["volume_zscore"] > 0.0 else "VOLUME_Z_NON_POSITIVE")
    if "oi_change_pct" in normalized:
        events.append("OI_RISING" if normalized["oi_change_pct"] > 0.0 else "OI_NOT_RISING")
    if "oi_acceleration" in normalized:
        events.append("OI_ACCELERATING" if normalized["oi_acceleration"] > 0.0 else "OI_NOT_ACCELERATING")
    if "funding_rate" in normalized:
        if normalized["funding_rate"] > 0.0:
            events.append("FUNDING_POSITIVE")
        elif normalized["funding_rate"] < 0.0:
            events.append("FUNDING_NEGATIVE")
        else:
            events.append("FUNDING_FLAT")
    if "liquidation_imbalance" in normalized:
        if normalized["liquidation_imbalance"] > 0.0:
            events.append("LIQUIDATION_BUY_IMBALANCE")
        elif normalized["liquidation_imbalance"] < 0.0:
            events.append("LIQUIDATION_SELL_IMBALANCE")
        else:
            events.append("LIQUIDATION_BALANCED")
    if "vwap_zscore" in normalized:
        if normalized["vwap_zscore"] > 0.0:
            events.append("ABOVE_VWAP")
        elif normalized["vwap_zscore"] < 0.0:
            events.append("BELOW_VWAP")
        else:
            events.append("AT_VWAP")
    if {
        "volatility_compression_ratio",
        "volatility_expansion_ratio",
    }.issubset(normalized):
        events.append(
            "VOLATILITY_EXPANDING"
            if normalized["volatility_expansion_ratio"] > normalized["volatility_compression_ratio"]
            else "VOLATILITY_NOT_EXPANDING"
        )
    if "market_breadth" in normalized:
        if normalized["market_breadth"] > 0.0:
            events.append("BREADTH_POSITIVE")
        elif normalized["market_breadth"] < 0.0:
            events.append("BREADTH_NEGATIVE")
        else:
            events.append("BREADTH_NEUTRAL")

    return {
        "schema": "qookey-market-event-radar-snapshot-v0.1",
        "symbol": clean_symbol,
        "as_of_ms": decision_time,
        "observed_at_ms": observed,
        "available_at_ms": available,
        "features": normalized,
        "events": events,
        "authority": {
            "research_only": True,
            "network_capture_authorized": False,
            "opportunity_score_change_authorized": False,
            "strategy_router_change_authorized": False,
            "automatic_candidate_generation_authorized": False,
            "provider_access_authorized": False,
            "storage_write_authorized": False,
            "training_authorized": False,
            "holdout_access_authorized": False,
            "live_trading_authorized": False,
        },
    }
