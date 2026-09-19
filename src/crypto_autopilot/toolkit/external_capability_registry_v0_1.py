from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

EXPECTED_CAPABILITY_IDS: Final[frozenset[str]] = frozenset(
    {
        "crypto_market_data_mcp",
        "agentfeed",
        "tradingcalc_mcp",
        "tradingview_mcp",
        "depthy_mcp",
        "0xarchive_mcp",
        "telegram_mcp",
        "cloudflare_mcp",
        "github_official_mcp",
        "github_actions_mcp",
    }
)
ALLOWED_CATEGORIES: Final[frozenset[str]] = frozenset(
    {
        "MARKET_DATA",
        "MARKET_MICROSTRUCTURE",
        "RISK_CROSSCHECK",
        "RESEARCH_CHALLENGER",
        "HISTORICAL_MARKET_DATA",
        "NOTIFICATION",
        "INFRASTRUCTURE",
        "DEVELOPER_CI",
    }
)
ALLOWED_RISK_LEVELS: Final[frozenset[str]] = frozenset({"MEDIUM", "HIGH"})
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True, slots=True)
class ExternalCapabilityRegistryPolicy:
    automatic_install_authorized: bool = False
    runtime_execution_authorized: bool = False
    external_network_authorized: bool = False
    secret_access_authorized: bool = False
    wallet_payment_authorized: bool = False
    repository_mutation_authorized: bool = False
    workflow_mutation_authorized: bool = False
    cloud_infrastructure_mutation_authorized: bool = False
    telegram_write_authorized: bool = False
    strategy_router_integration_authorized: bool = False
    daily_opportunity_integration_authorized: bool = False
    r2_access_authorized: bool = False
    holdout_access_authorized: bool = False
    training_authorized: bool = False
    model_promotion_authorized: bool = False
    real_money_order_authorized: bool = False
    live_real_trading_authorized: bool = False

    def __post_init__(self) -> None:
        if any(
            (
                self.automatic_install_authorized,
                self.runtime_execution_authorized,
                self.external_network_authorized,
                self.secret_access_authorized,
                self.wallet_payment_authorized,
                self.repository_mutation_authorized,
                self.workflow_mutation_authorized,
                self.cloud_infrastructure_mutation_authorized,
                self.telegram_write_authorized,
                self.strategy_router_integration_authorized,
                self.daily_opportunity_integration_authorized,
                self.r2_access_authorized,
                self.holdout_access_authorized,
                self.training_authorized,
                self.model_promotion_authorized,
                self.real_money_order_authorized,
                self.live_real_trading_authorized,
            )
        ):
            raise ValueError(
                "External Capability Registry V0.1 is inventory-only and "
                "cannot grant install, runtime, network, secret, mutation, "
                "payment, training or trading authority"
            )


def _require_bool(mapping: Mapping[str, object], key: str) -> bool:
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a JSON boolean")
    return value


def _require_text(mapping: Mapping[str, object], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def validate_external_capability_registry(
    payload: Mapping[str, object],
) -> dict[str, object]:
    if payload.get("schema") != "qookey-external-capability-registry-v0.1":
        raise ValueError("unsupported external capability registry schema")
    if payload.get("status") != "CANDIDATE_REGISTRY_ONLY":
        raise ValueError("registry must remain candidate-only")

    policy_payload = payload.get("policy")
    rows = payload.get("capabilities")
    if not isinstance(policy_payload, Mapping):
        raise ValueError("registry policy object is required")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise ValueError("registry capabilities must be an array")

    policy_keys = (
        "automatic_install_authorized",
        "runtime_execution_authorized",
        "external_network_authorized",
        "secret_access_authorized",
        "wallet_payment_authorized",
        "repository_mutation_authorized",
        "workflow_mutation_authorized",
        "cloud_infrastructure_mutation_authorized",
        "telegram_write_authorized",
        "strategy_router_integration_authorized",
        "daily_opportunity_integration_authorized",
        "r2_access_authorized",
        "holdout_access_authorized",
        "training_authorized",
        "model_promotion_authorized",
        "real_money_order_authorized",
        "live_real_trading_authorized",
    )
    policy_values = {
        key: _require_bool(policy_payload, key)
        for key in policy_keys
    }
    policy = ExternalCapabilityRegistryPolicy(**policy_values)

    seen_ids: set[str] = set()
    seen_repositories: set[str] = set()
    category_counts: dict[str, int] = {}
    risk_counts: dict[str, int] = {}

    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("capability row must be an object")
        capability_id = _require_text(row, "capability_id")
        if capability_id in seen_ids:
            raise ValueError(f"duplicate capability_id: {capability_id}")
        seen_ids.add(capability_id)

        repository = _require_text(row, "repository")
        if repository in seen_repositories:
            raise ValueError(f"duplicate repository: {repository}")
        seen_repositories.add(repository)

        sha = _require_text(row, "commit_sha")
        if not _SHA_RE.fullmatch(sha):
            raise ValueError(f"invalid commit SHA for {capability_id}")

        category = _require_text(row, "category")
        if category not in ALLOWED_CATEGORIES:
            raise ValueError(f"unsupported category for {capability_id}: {category}")
        category_counts[category] = category_counts.get(category, 0) + 1

        if row.get("lifecycle_state") != "CANDIDATE":
            raise ValueError(f"{capability_id} must remain CANDIDATE")
        if row.get("decision") != "REVIEW_REQUIRED":
            raise ValueError(f"{capability_id} must remain REVIEW_REQUIRED")
        if _require_bool(row, "archived"):
            raise ValueError(f"{capability_id} points to an archived repository")
        if not _require_bool(row, "license_verified"):
            raise ValueError(f"{capability_id} license must be verified")
        _require_text(row, "license")

        if _require_bool(row, "production_eligible"):
            raise ValueError(f"{capability_id} cannot be production eligible in V0.1")
        if _require_bool(row, "adapter_authorized"):
            raise ValueError(f"{capability_id} adapter is not authorized")
        if _require_bool(row, "runtime_authorized"):
            raise ValueError(f"{capability_id} runtime is not authorized")

        requirements = row.get("requirements")
        risk = row.get("risk")
        capabilities = row.get("capability_summary")
        if not isinstance(requirements, Mapping) or not isinstance(risk, Mapping):
            raise ValueError(f"{capability_id} requirements/risk are required")
        if not isinstance(capabilities, Sequence) or isinstance(
            capabilities,
            (str, bytes),
        ) or not capabilities:
            raise ValueError(f"{capability_id} capability_summary is required")

        _require_text(requirements, "credential")
        _require_bool(requirements, "paid_runtime")
        if not _require_bool(requirements, "external_network"):
            raise ValueError(f"{capability_id} must declare external network use")

        risk_level = _require_text(risk, "level")
        if risk_level not in ALLOWED_RISK_LEVELS:
            raise ValueError(f"unsupported risk level for {capability_id}")
        risk_counts[risk_level] = risk_counts.get(risk_level, 0) + 1
        write_capable = _require_bool(risk, "upstream_write_capable")
        payment_capable = _require_bool(risk, "payment_capable")
        secret_bearing = _require_bool(risk, "secret_bearing")
        if (write_capable or payment_capable) and risk_level != "HIGH":
            raise ValueError(
                f"{capability_id} write/payment capability must be HIGH risk"
            )
        if payment_capable and not requirements.get("paid_runtime"):
            raise ValueError(f"{capability_id} payment capability must declare paid runtime")
        if secret_bearing and requirements.get("credential") in {"NONE", ""}:
            raise ValueError(f"{capability_id} secret-bearing risk lacks credential declaration")

    if seen_ids != EXPECTED_CAPABILITY_IDS:
        missing = sorted(EXPECTED_CAPABILITY_IDS - seen_ids)
        extra = sorted(seen_ids - EXPECTED_CAPABILITY_IDS)
        raise ValueError(f"capability registry mismatch missing={missing} extra={extra}")

    return {
        "schema": "qookey-external-capability-registry-validation-v0.1",
        "state": "PASS",
        "capability_count": len(rows),
        "category_counts": dict(sorted(category_counts.items())),
        "risk_counts": dict(sorted(risk_counts.items())),
        "authority": {
            "inventory_only": True,
            "automatic_install_authorized": policy.automatic_install_authorized,
            "runtime_execution_authorized": policy.runtime_execution_authorized,
            "external_network_authorized": policy.external_network_authorized,
            "secret_access_authorized": policy.secret_access_authorized,
            "wallet_payment_authorized": policy.wallet_payment_authorized,
            "repository_mutation_authorized": policy.repository_mutation_authorized,
            "workflow_mutation_authorized": policy.workflow_mutation_authorized,
            "cloud_infrastructure_mutation_authorized": (
                policy.cloud_infrastructure_mutation_authorized
            ),
            "telegram_write_authorized": policy.telegram_write_authorized,
            "strategy_router_integration_authorized": (
                policy.strategy_router_integration_authorized
            ),
            "daily_opportunity_integration_authorized": (
                policy.daily_opportunity_integration_authorized
            ),
            "r2_access_authorized": policy.r2_access_authorized,
            "holdout_access_authorized": policy.holdout_access_authorized,
            "training_authorized": policy.training_authorized,
            "model_promotion_authorized": policy.model_promotion_authorized,
            "real_money_order_authorized": policy.real_money_order_authorized,
            "live_real_trading_authorized": policy.live_real_trading_authorized,
        },
    }
