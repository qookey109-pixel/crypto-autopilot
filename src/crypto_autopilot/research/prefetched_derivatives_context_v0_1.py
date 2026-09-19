from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

SOURCE_CAPABILITY_ID: Final[str] = "crypto_market_data_mcp"
UPSTREAM_REPOSITORY: Final[str] = "eliasfire617/crypto-market-data-mcp"
UPSTREAM_COMMIT_SHA: Final[str] = "7720d7116e26e578037c519d6fdae0d9ba0e8a75"

ALLOWED_INPUT_CLASSES: Final[frozenset[str]] = frozenset(
    {"synthetic_fixture", "existing_non_holdout_fixture"}
)
METRIC_KINDS: Final[frozenset[str]] = frozenset(
    {"funding", "open_interest", "long_short_ratio"}
)
LONG_SHORT_PERIODS: Final[frozenset[str]] = frozenset(
    {"5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"}
)


@dataclass(frozen=True, slots=True)
class PrefetchedDerivativesContextPolicy:
    prefetched_evidence_ingestion_authorized: bool = True
    network_capture_authorized: bool = False
    mcp_runtime_authorized: bool = False
    provider_api_key_authorized: bool = False
    hosted_mcp_api_key_authorized: bool = False
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
            self.hosted_mcp_api_key_authorized,
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
            raise ValueError("derivatives-context policy flags must be booleans")
        if not self.prefetched_evidence_ingestion_authorized:
            raise ValueError("V0.1 requires prefetched evidence ingestion")
        if any(values[1:]):
            raise ValueError(
                "Prefetched Derivatives Context V0.1 cannot grant network, "
                "runtime, routing, storage, training or trading authority"
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
    if any(character.isspace() for character in exchange):
        raise ValueError("exchange cannot contain whitespace")
    return exchange


def _non_negative_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _finite_number(value: object, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"{label} must be finite")
    return number


def _non_negative_number(value: object, label: str) -> float:
    number = _finite_number(value, label)
    if number < 0:
        raise ValueError(f"{label} cannot be negative")
    return number


def _positive_number(value: object, label: str) -> float:
    number = _finite_number(value, label)
    if number <= 0:
        raise ValueError(f"{label} must be positive")
    return number


def _normalize_funding(payload: Mapping[str, object]) -> dict[str, object]:
    interval = _positive_number(
        payload.get("funding_interval_hours"),
        "funding_interval_hours",
    )
    if interval > 24.0:
        raise ValueError("funding_interval_hours cannot exceed 24")
    return {
        "funding_rate": _finite_number(payload.get("funding_rate"), "funding_rate"),
        "funding_interval_hours": interval,
    }


def _normalize_open_interest(payload: Mapping[str, object]) -> dict[str, object]:
    result: dict[str, object] = {}
    if payload.get("open_interest_amount") is not None:
        result["open_interest_amount"] = _non_negative_number(
            payload.get("open_interest_amount"),
            "open_interest_amount",
        )
    if payload.get("open_interest_value") is not None:
        result["open_interest_value"] = _non_negative_number(
            payload.get("open_interest_value"),
            "open_interest_value",
        )
    if not result:
        raise ValueError("open-interest payload requires amount or value")
    return result


def _normalize_long_short(
    payload: Mapping[str, object],
    exchange: str,
) -> dict[str, object]:
    if exchange != "binance":
        raise ValueError("long/short ratio V0.1 is Binance-only")
    period = payload.get("period")
    if not isinstance(period, str) or period not in LONG_SHORT_PERIODS:
        raise ValueError("unsupported Binance long/short period")

    ratio = _positive_number(payload.get("long_short_ratio"), "long_short_ratio")
    long_share = _finite_number(payload.get("long_pct"), "long_pct")
    short_share = _finite_number(payload.get("short_pct"), "short_pct")
    if not 0.0 <= long_share <= 1.0 or not 0.0 <= short_share <= 1.0:
        raise ValueError("long_pct and short_pct must be fractions within [0, 1]")
    if abs((long_share + short_share) - 1.0) > 1e-6:
        raise ValueError("long_pct and short_pct must sum to 1")
    if short_share <= 0.0:
        raise ValueError("short_pct must be positive for finite long/short ratio")
    expected_ratio = long_share / short_share
    tolerance = max(1e-6, abs(expected_ratio) * 1e-4)
    if abs(ratio - expected_ratio) > tolerance:
        raise ValueError("long_short_ratio is inconsistent with long_pct/short_pct")

    return {
        "period": period,
        "long_short_ratio": ratio,
        "long_pct": long_share,
        "short_pct": short_share,
    }


def _normalize_metric(
    kind: str,
    exchange: str,
    payload: Mapping[str, object],
) -> dict[str, object]:
    if kind == "funding":
        return _normalize_funding(payload)
    if kind == "open_interest":
        return _normalize_open_interest(payload)
    if kind == "long_short_ratio":
        return _normalize_long_short(payload, exchange)
    raise ValueError(f"unsupported derivatives metric kind: {kind}")


def build_prefetched_derivatives_context(
    *,
    symbol: str,
    as_of_ms: int,
    input_class: str,
    evidence: Sequence[Mapping[str, object]],
    policy: PrefetchedDerivativesContextPolicy = PrefetchedDerivativesContextPolicy(),
) -> dict[str, object]:
    """Normalize caller-supplied derivatives evidence without I/O."""

    if not policy.prefetched_evidence_ingestion_authorized:
        raise ValueError("prefetched derivatives evidence ingestion is not authorized")
    if input_class not in ALLOWED_INPUT_CLASSES:
        raise ValueError("V0.1 accepts only synthetic or existing non-holdout fixtures")
    clean_symbol = _clean_symbol(symbol)
    decision_time = _non_negative_int(as_of_ms, "as_of_ms")

    seen: set[tuple[str, str, str | None]] = set()
    normalized: dict[str, list[dict[str, object]]] = {
        "funding": [],
        "open_interest": [],
        "long_short_ratio": [],
    }

    for row in evidence:
        if not isinstance(row, Mapping):
            raise ValueError("derivatives evidence row must be an object")
        kind = row.get("kind")
        if not isinstance(kind, str) or kind not in METRIC_KINDS:
            raise ValueError("unsupported derivatives evidence kind")
        exchange = _clean_exchange(row.get("exchange"))
        evidence_symbol = _clean_symbol(row.get("symbol"))
        if evidence_symbol != clean_symbol:
            raise ValueError("derivatives evidence belongs to another symbol")

        observed_at_ms = _non_negative_int(row.get("observed_at_ms"), "observed_at_ms")
        available_at_ms = _non_negative_int(
            row.get("available_at_ms"),
            "available_at_ms",
        )
        if observed_at_ms > available_at_ms:
            raise ValueError("evidence cannot be available before observation")
        if available_at_ms > decision_time:
            raise ValueError("future derivatives evidence is not causally available")

        payload = row.get("payload")
        if not isinstance(payload, Mapping):
            raise ValueError("derivatives evidence payload must be an object")
        data = _normalize_metric(kind, exchange, payload)
        period = data.get("period") if kind == "long_short_ratio" else None
        dedup_key = (kind, exchange, period if isinstance(period, str) else None)
        if dedup_key in seen:
            raise ValueError(
                f"duplicate derivatives evidence: {kind}/{exchange}/{period or '-'}"
            )
        seen.add(dedup_key)

        normalized[kind].append(
            {
                "exchange": exchange,
                "observed_at_ms": observed_at_ms,
                "available_at_ms": available_at_ms,
                "data": data,
            }
        )

    for rows in normalized.values():
        rows.sort(
            key=lambda row: (
                str(row["exchange"]),
                int(row["observed_at_ms"]),
            )
        )

    return {
        "schema": "qookey-prefetched-derivatives-context-snapshot-v0.1",
        "symbol": clean_symbol,
        "as_of_ms": decision_time,
        "input_class": input_class,
        "source": {
            "capability_id": SOURCE_CAPABILITY_ID,
            "upstream_repository": UPSTREAM_REPOSITORY,
            "upstream_commit_sha": UPSTREAM_COMMIT_SHA,
        },
        "metrics_present": sorted(
            kind for kind, rows in normalized.items() if rows
        ),
        "metrics": normalized,
        "interpretation": "DESCRIPTIVE_RESEARCH_CONTEXT_ONLY",
        "authority": {
            "prefetched_evidence_ingestion_only": True,
            "network_capture_authorized": False,
            "mcp_runtime_authorized": False,
            "provider_api_key_authorized": False,
            "hosted_mcp_api_key_authorized": False,
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


def prefetched_derivatives_context_policy_from_config(
    payload: Mapping[str, object],
) -> PrefetchedDerivativesContextPolicy:
    if payload.get("schema") != "qookey-prefetched-derivatives-context-v0.1":
        raise ValueError("unsupported prefetched derivatives context config")
    source = payload.get("source")
    policy = payload.get("policy")
    allowed_inputs = payload.get("allowed_input_classes")
    metric_kinds = payload.get("metric_kinds")
    long_short = payload.get("long_short_ratio")
    if not isinstance(source, Mapping) or not isinstance(policy, Mapping):
        raise ValueError("derivatives context source/policy are required")
    if source.get("capability_id") != SOURCE_CAPABILITY_ID:
        raise ValueError("derivatives context capability id mismatch")
    if source.get("upstream_repository") != UPSTREAM_REPOSITORY:
        raise ValueError("derivatives context upstream repository mismatch")
    if source.get("upstream_commit_sha") != UPSTREAM_COMMIT_SHA:
        raise ValueError("derivatives context upstream commit pin mismatch")
    if set(allowed_inputs or []) != ALLOWED_INPUT_CLASSES:
        raise ValueError("derivatives context input-class registry mismatch")
    if set(metric_kinds or []) != METRIC_KINDS:
        raise ValueError("derivatives context metric registry mismatch")
    if not isinstance(long_short, Mapping):
        raise ValueError("long_short_ratio config is required")
    if long_short.get("provider") != "binance":
        raise ValueError("long/short provider must remain Binance in V0.1")
    if set(long_short.get("allowed_periods") or []) != LONG_SHORT_PERIODS:
        raise ValueError("long/short period registry mismatch")

    keys = (
        "prefetched_evidence_ingestion_authorized",
        "network_capture_authorized",
        "mcp_runtime_authorized",
        "provider_api_key_authorized",
        "hosted_mcp_api_key_authorized",
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
    return PrefetchedDerivativesContextPolicy(**values)
