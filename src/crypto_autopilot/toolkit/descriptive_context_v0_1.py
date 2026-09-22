from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse


class DescriptiveContextError(ValueError):
    """Raised when the research-only descriptive-context contract is violated."""


_ALLOWED_INPUT_CLASSES = {"synthetic_fixture"}
_ALLOWED_CONTEXT_TYPES = {
    "geopolitical_event",
    "supply_chain_disruption",
    "sanctions_context",
    "energy_context",
    "cyber_context",
    "disaster_context",
    "market_stress_context",
}
_ALLOWED_SEVERITY_LABELS = {
    "unknown",
    "low",
    "moderate",
    "elevated",
    "high",
    "critical",
}
_REQUIRED_PAYLOAD_KEYS = {
    "source",
    "context_type",
    "observed_at",
    "cached_at",
    "stale",
    "summary",
    "severity",
    "provenance",
}
_REQUIRED_PROVENANCE_KEYS = {"source_name", "source_url"}
_INTERPRETATION_KEYS = {
    "directional_signal",
    "strategy_input",
    "formal_edge_gate",
    "promotion_signal",
    "formal_backtest_admission",
    "trade_plan_generation",
    "live_trading_signal",
    "source_equivalence_claimed",
}
_AUTHORITY_KEYS = {
    "automatic_schedule_authorized",
    "worldmonitor_network_call_authorized",
    "worldmonitor_api_key_authorized",
    "worldmonitor_oauth_authorized",
    "provider_access_authorized",
    "r2_access_authorized",
    "holdout_access_authorized",
    "source_switch_authorized",
    "strategy_parameter_change_authorized",
    "automatic_strategy_mutation_authorized",
    "model_promotion_authorized",
    "formal_backtest_admission_authorized",
    "formal_trade_plan_authorized",
    "real_money_order_authorized",
    "live_trading_authorized",
}
_FORBIDDEN_DIRECTIONAL_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bgo\s+long\b",
        r"\bgo\s+short\b",
        r"\bbuy\b",
        r"\bsell\b",
        r"\bbullish\b",
        r"\bbearish\b",
        r"\bentry\b",
        r"\bstop[- ]loss\b",
        r"\btake[- ]profit\b",
        r"\bprice\s+target\b",
        r"\btarget\s+return\b",
        r"\bposition\s+size\b",
        r"\bleverage\b",
        r"\btrade\s+plan\b",
        r"\brisk[-_ ]on\b",
        r"\brisk[-_ ]off\b",
    )
)


def _parse_timestamp(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise DescriptiveContextError(f"{label} must be a non-empty ISO-8601 string")
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise DescriptiveContextError(f"{label} must be valid ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise DescriptiveContextError(f"{label} must include a timezone offset")
    return parsed.astimezone(UTC)


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _positive_int(mapping: Mapping[str, Any], key: str) -> int:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise DescriptiveContextError(f"{key} must be a positive integer")
    return value


def _require_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DescriptiveContextError(f"{label} policy must be an object")
    return value


def _validate_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    if policy.get("schema") != "resource-hub-descriptive-context-policy-v0.1":
        raise DescriptiveContextError("unexpected descriptive-context policy schema")
    if policy.get("status") != "PREPARED_RESEARCH_ONLY":
        raise DescriptiveContextError("descriptive-context policy must remain research only")

    allowed_inputs = policy.get("allowed_input_classes")
    allowed_contexts = policy.get("allowed_context_types")
    allowed_severity = policy.get("allowed_severity_labels")
    if not isinstance(allowed_inputs, list) or set(allowed_inputs) != _ALLOWED_INPUT_CLASSES:
        raise DescriptiveContextError("allowed input classes must remain the frozen safe set")
    if not isinstance(allowed_contexts, list) or set(allowed_contexts) != _ALLOWED_CONTEXT_TYPES:
        raise DescriptiveContextError("allowed context types must remain the frozen descriptive set")
    if not isinstance(allowed_severity, list) or set(allowed_severity) != _ALLOWED_SEVERITY_LABELS:
        raise DescriptiveContextError("allowed severity labels must remain the frozen descriptive set")

    freshness = _require_mapping(policy.get("freshness"), "freshness")
    provenance_policy = _require_mapping(policy.get("provenance"), "provenance")
    content_policy = _require_mapping(policy.get("content"), "content")
    interpretation = _require_mapping(policy.get("interpretation"), "interpretation")
    authority = _require_mapping(policy.get("authority"), "authority")

    if set(interpretation) != _INTERPRETATION_KEYS:
        raise DescriptiveContextError("interpretation policy keys must remain frozen")
    if any(value is not False for value in interpretation.values()):
        raise DescriptiveContextError("all interpretation flags must remain false")
    if set(authority) != _AUTHORITY_KEYS:
        raise DescriptiveContextError("authority policy keys must remain frozen")
    if any(value is not False for value in authority.values()):
        raise DescriptiveContextError("all descriptive-context authority flags must remain false")

    max_cache_age = _positive_int(freshness, "max_cache_age_seconds")
    max_observation_age = _positive_int(freshness, "max_observation_age_seconds")
    max_clock_skew = _positive_int(freshness, "max_clock_skew_seconds")
    minimum_sources = _positive_int(provenance_policy, "minimum_sources")
    maximum_sources = _positive_int(provenance_policy, "maximum_sources")
    maximum_summary = _positive_int(content_policy, "maximum_summary_characters")
    if minimum_sources > maximum_sources:
        raise DescriptiveContextError("minimum provenance sources cannot exceed maximum")
    if provenance_policy.get("require_https_url") is not True:
        raise DescriptiveContextError("provenance HTTPS requirement must remain enabled")
    if content_policy.get("reject_directional_or_trade_language") is not True:
        raise DescriptiveContextError("directional/trade-language rejection must remain enabled")

    return {
        "max_cache_age_seconds": max_cache_age,
        "max_observation_age_seconds": max_observation_age,
        "max_clock_skew_seconds": max_clock_skew,
        "minimum_sources": minimum_sources,
        "maximum_sources": maximum_sources,
        "maximum_summary_characters": maximum_summary,
        "authority": dict(authority),
    }


def _validate_summary(summary: object, maximum_characters: int) -> str:
    if not isinstance(summary, str) or not summary.strip():
        raise DescriptiveContextError("summary must be a non-empty string")
    normalized = " ".join(summary.split())
    if len(normalized) > maximum_characters:
        raise DescriptiveContextError("summary exceeds the bounded descriptive-context size")
    if any(pattern.search(normalized) for pattern in _FORBIDDEN_DIRECTIONAL_PATTERNS):
        raise DescriptiveContextError("summary contains directional or trade-plan language")
    return normalized


def _validate_provenance(
    value: object,
    *,
    minimum_sources: int,
    maximum_sources: int,
) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise DescriptiveContextError("provenance must be a list")
    if not minimum_sources <= len(value) <= maximum_sources:
        raise DescriptiveContextError("provenance source count is outside the frozen bounds")

    normalized: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for item in value:
        if not isinstance(item, Mapping) or set(item) != _REQUIRED_PROVENANCE_KEYS:
            raise DescriptiveContextError("each provenance item must use the frozen schema")
        source_name = item.get("source_name")
        source_url = item.get("source_url")
        if not isinstance(source_name, str) or not source_name.strip():
            raise DescriptiveContextError("provenance source_name must be non-empty")
        if not isinstance(source_url, str):
            raise DescriptiveContextError("provenance source_url must be a string")
        parsed = urlparse(source_url.strip())
        if parsed.scheme.lower() != "https" or not parsed.netloc:
            raise DescriptiveContextError("provenance source_url must use HTTPS")
        canonical_url = source_url.strip()
        if canonical_url in seen_urls:
            raise DescriptiveContextError("duplicate provenance URLs are not allowed")
        seen_urls.add(canonical_url)
        normalized.append(
            {
                "source_name": source_name.strip(),
                "source_url": canonical_url,
            }
        )
    return normalized


def build_descriptive_context_envelope(
    payload: Mapping[str, Any],
    policy: Mapping[str, Any],
    *,
    input_class: str,
    as_of: str,
) -> dict[str, Any]:
    """Normalize synthetic context into a non-directional research-only envelope.

    V0.1 deliberately has no transport layer. It cannot call World Monitor or any market
    provider and cannot grant strategy, backtest, promotion, trade-plan, or live authority.
    """

    limits = _validate_policy(policy)
    if input_class not in _ALLOWED_INPUT_CLASSES:
        raise DescriptiveContextError("input class is not authorized for descriptive context")
    if set(payload) != _REQUIRED_PAYLOAD_KEYS:
        raise DescriptiveContextError("payload keys must exactly match the frozen schema")

    source = payload.get("source")
    context_type = payload.get("context_type")
    severity = payload.get("severity")
    stale = payload.get("stale")
    if not isinstance(source, str) or not source.strip() or len(source.strip()) > 120:
        raise DescriptiveContextError("source must be a bounded non-empty string")
    if context_type not in _ALLOWED_CONTEXT_TYPES:
        raise DescriptiveContextError("context type is not in the frozen descriptive set")
    if severity not in _ALLOWED_SEVERITY_LABELS:
        raise DescriptiveContextError("severity must be a frozen descriptive label")
    if stale is not False:
        raise DescriptiveContextError("stale context is rejected")

    as_of_dt = _parse_timestamp(as_of, "as_of")
    observed_at = _parse_timestamp(payload.get("observed_at"), "observed_at")
    cached_at = _parse_timestamp(payload.get("cached_at"), "cached_at")
    max_clock_skew = limits["max_clock_skew_seconds"]
    if observed_at > cached_at:
        raise DescriptiveContextError("observed_at cannot be later than cached_at")
    if (observed_at - as_of_dt).total_seconds() > max_clock_skew:
        raise DescriptiveContextError("observed_at is too far in the future")
    if (cached_at - as_of_dt).total_seconds() > max_clock_skew:
        raise DescriptiveContextError("cached_at is too far in the future")

    cache_age_seconds = max(0, int((as_of_dt - cached_at).total_seconds()))
    observation_age_seconds = max(0, int((as_of_dt - observed_at).total_seconds()))
    if cache_age_seconds > limits["max_cache_age_seconds"]:
        raise DescriptiveContextError("cached context exceeds the freshness budget")
    if observation_age_seconds > limits["max_observation_age_seconds"]:
        raise DescriptiveContextError("observed context exceeds the age budget")

    summary = _validate_summary(
        payload.get("summary"),
        limits["maximum_summary_characters"],
    )
    provenance = _validate_provenance(
        payload.get("provenance"),
        minimum_sources=limits["minimum_sources"],
        maximum_sources=limits["maximum_sources"],
    )

    return {
        "schema": "resource-hub-descriptive-context-envelope-v0.1",
        "status": "RESEARCH_ONLY",
        "decision": "DESCRIPTIVE_CONTEXT_ONLY",
        "input_class": input_class,
        "source": source.strip(),
        "context_type": context_type,
        "severity": severity,
        "observed_at": _format_timestamp(observed_at),
        "cached_at": _format_timestamp(cached_at),
        "as_of": _format_timestamp(as_of_dt),
        "stale": False,
        "freshness": {
            "cache_age_seconds": cache_age_seconds,
            "observation_age_seconds": observation_age_seconds,
        },
        "summary": summary,
        "provenance": provenance,
        "directional_signal": None,
        "strategy_eligible": False,
        "formal_backtest_eligible": False,
        "trade_plan_eligible": False,
        "limitations": [
            "Synthetic V0.1 contract validation only; no World Monitor transport is implemented.",
            "Severity and context type are descriptive labels, not calibrated crypto predictors.",
            "The envelope cannot replace exchange-native market data or provider provenance.",
            "The envelope cannot authorize strategy changes, promotion, backtests, orders, or trading.",
        ],
        "authority": limits["authority"],
    }
