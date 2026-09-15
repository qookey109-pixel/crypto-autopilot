from __future__ import annotations

import re
from typing import Any, Mapping


_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _resource_text(resource: Mapping[str, Any]) -> str:
    values: list[str] = [
        str(resource.get("id", "")),
        str(resource.get("name", "")),
        str(resource.get("summary", "")),
        str(resource.get("notes", "")),
    ]
    for key in ("categories", "tags", "use_cases"):
        raw = resource.get(key, [])
        if isinstance(raw, list):
            values.extend(str(item) for item in raw)
    return " ".join(values).lower()


def _matched_categories(
    resource: Mapping[str, Any], category_weights: Mapping[str, Any]
) -> list[dict[str, Any]]:
    categories = resource.get("categories", [])
    if not isinstance(categories, list):
        categories = []
    matched = [
        {"category": category, "weight": int(category_weights[category])}
        for category in categories
        if category in category_weights
    ]
    return sorted(matched, key=lambda item: (-item["weight"], item["category"]))


def _matched_signals(text: str, signal_weights: Mapping[str, Any]) -> list[dict[str, Any]]:
    matched = [
        {"signal": signal, "weight": int(weight)}
        for signal, weight in signal_weights.items()
        if signal.lower() in text
    ]
    return sorted(matched, key=lambda item: (-item["weight"], item["signal"]))


def _integration_type(text: str) -> str:
    if any(term in text for term in ("anti-scam", "反詐", "backtest", "strategy validation")):
        return "strategy_validation"
    if any(term in text for term in ("geopolit", "osint", "macro", "sentiment", "news")):
        return "market_intelligence"
    if any(term in text for term in ("time-series", "timeseries", "forecast")):
        return "forecasting_research"
    if any(term in text for term in ("trading", "crypto", "finance", "market", "portfolio")):
        return "trading_research"
    if any(term in text for term in ("analytics", "data analysis", "data / analytics")):
        return "data_analysis"
    return "research"


def _integration_risk(text: str) -> str:
    high_terms = (
        "live trading",
        "real-money",
        "real money",
        "order execution",
        "private key",
        "wallet",
    )
    if any(term in text for term in high_terms):
        return "high"

    medium_terms = (
        "api key",
        "api-key",
        "cookie",
        "scraping",
        "webhook",
        "automation",
        "mcp",
        "external api",
    )
    if any(term in text for term in medium_terms):
        return "medium"
    return "low"


def build_candidate_registry(
    catalog_payload: Mapping[str, Any],
    policy: Mapping[str, Any],
    *,
    source_commit: str,
) -> dict[str, Any]:
    """Build a read-only integration-candidate registry from the Resource Hub catalog.

    This function never performs network access, installs tools, executes tools, mutates strategy,
    or authorizes trading. Network retrieval and provenance binding belong to the caller.
    """

    if not _SHA_RE.fullmatch(source_commit):
        raise ValueError("source_commit must be a lowercase 40-character Git SHA")

    resources = catalog_payload.get("resources")
    if not isinstance(resources, list):
        raise ValueError("catalog resources must be a list")

    category_weights = policy.get("target_category_weights")
    signal_weights = policy.get("domain_signal_weights")
    weak_signals_raw = policy.get("weak_domain_signals", [])
    safety = policy.get("safety")
    source = policy.get("source")
    if not isinstance(category_weights, Mapping) or not category_weights:
        raise ValueError("policy target_category_weights must be a non-empty object")
    if not isinstance(signal_weights, Mapping) or not signal_weights:
        raise ValueError("policy domain_signal_weights must be a non-empty object")
    if not isinstance(weak_signals_raw, list) or not all(
        isinstance(item, str) and item for item in weak_signals_raw
    ):
        raise ValueError("policy weak_domain_signals must be a list of non-empty strings")
    if not isinstance(safety, Mapping):
        raise ValueError("policy safety must be an object")
    if not isinstance(source, Mapping):
        raise ValueError("policy source must be an object")

    weak_signals = {item.lower() for item in weak_signals_raw}
    unknown_weak_signals = weak_signals.difference(signal.lower() for signal in signal_weights)
    if unknown_weak_signals:
        raise ValueError(f"weak_domain_signals are missing weights: {sorted(unknown_weak_signals)}")

    minimum_strong_signals = int(policy.get("minimum_strong_signals_without_finance_category", 1))
    if minimum_strong_signals < 1:
        raise ValueError("minimum_strong_signals_without_finance_category must be >= 1")

    required_false = (
        "schedule_authorized",
        "automatic_install_authorized",
        "automatic_execution_authorized",
        "automatic_adapter_creation_authorized",
        "automatic_pull_request_authorized",
        "provider_access_authorized",
        "r2_access_authorized",
        "holdout_access_authorized",
        "source_switch_authorized",
        "automatic_strategy_mutation_authorized",
        "automatic_model_promotion_authorized",
        "formal_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    )
    enabled = [name for name in required_false if safety.get(name) is not False]
    if enabled:
        raise ValueError(f"read-only safety boundary failed: {enabled}")
    if safety.get("workflow_dispatch_only") is not True:
        raise ValueError("workflow_dispatch_only must remain true in V0.1")

    minimum_score = int(policy.get("minimum_score", 35))
    max_candidates = int(policy.get("max_candidates", 50))
    candidates: list[dict[str, Any]] = []
    eligible_count = 0

    for resource in resources:
        if not isinstance(resource, Mapping):
            continue
        matched_categories = _matched_categories(resource, category_weights)
        if not matched_categories:
            continue

        text = _resource_text(resource)
        matched_signals = _matched_signals(text, signal_weights)
        strong_matched_signals = [
            item for item in matched_signals if item["signal"].lower() not in weak_signals
        ]
        has_finance_category = any(
            item["category"] == "Finance / Crypto" for item in matched_categories
        )
        if not has_finance_category and len(strong_matched_signals) < minimum_strong_signals:
            continue

        eligible_count += 1
        score = min(
            100,
            sum(item["weight"] for item in matched_categories)
            + sum(item["weight"] for item in matched_signals),
        )
        if score < minimum_score:
            continue

        resource_id = str(resource.get("id", "")).strip()
        name = str(resource.get("name", "")).strip()
        url = str(resource.get("url", "")).strip()
        if not resource_id or not name or not url:
            continue

        candidates.append(
            {
                "resource_id": resource_id,
                "name": name,
                "url": url,
                "relevance_score": score,
                "matched_categories": [item["category"] for item in matched_categories],
                "matched_signals": [item["signal"] for item in matched_signals],
                "strong_matched_signals": [item["signal"] for item in strong_matched_signals],
                "integration_type": _integration_type(text),
                "integration_risk": _integration_risk(text),
                "license": resource.get("license"),
                "open_source": resource.get("open_source"),
                "pricing": resource.get("pricing"),
                "resource_status": resource.get("status"),
                "decision": "REVIEW_REQUIRED",
                "automatic_install_authorized": False,
                "automatic_execution_authorized": False,
                "adapter_creation_authorized": False,
                "live_trading_authorized": False,
            }
        )

    candidates.sort(key=lambda item: (-item["relevance_score"], item["resource_id"]))
    candidates = candidates[:max_candidates]

    return {
        "schema": "qookey-resource-hub-supply-chain-candidates-v0.1",
        "status": "RESEARCH_ONLY",
        "source": {
            "repository": source.get("repository"),
            "ref": source.get("ref"),
            "commit_sha": source_commit,
            "catalog_path": source.get("catalog_path"),
            "catalog_schema_version": catalog_payload.get("schema_version"),
            "catalog_updated_at": catalog_payload.get("updated_at"),
        },
        "policy": {
            "schema": policy.get("schema"),
            "minimum_score": minimum_score,
            "minimum_strong_signals_without_finance_category": minimum_strong_signals,
            "weak_domain_signals": sorted(weak_signals),
            "max_candidates": max_candidates,
        },
        "scanned_resource_count": len(resources),
        "eligible_resource_count": eligible_count,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "authority": dict(safety),
    }
