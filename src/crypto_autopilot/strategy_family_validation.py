from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .strategy_library import get_strategy_family


class StrategyFamilyValidationError(ValueError):
    """Raised when family-level evidence cannot satisfy the frozen contract."""


@dataclass(frozen=True, slots=True)
class StrategyFamilyValidationPolicy:
    """Coverage policy layered on top of existing Strategy Edge Validation."""

    minimum_receipts: int = 6
    minimum_distinct_assets: int = 3
    minimum_distinct_regimes: int = 2
    require_single_provider: bool = True
    require_all_edge_pass: bool = True

    def __post_init__(self) -> None:
        if self.minimum_receipts < 1:
            raise ValueError("minimum_receipts must be positive")
        if self.minimum_distinct_assets < 2:
            raise ValueError("minimum_distinct_assets must be at least 2")
        if self.minimum_distinct_regimes < 1:
            raise ValueError("minimum_distinct_regimes must be positive")


@dataclass(frozen=True, slots=True)
class FamilyEdgeReceipt:
    family: str
    symbol: str
    regime_state: str
    direction: str
    provider: str
    selected_candidate_id: str
    edge_input_fingerprint: str
    edge_report_sha256: str
    edge_verdict: str
    research_evidence_only: bool
    holdout_accessed: bool
    promotion_authority: int
    trade_plan_authorized: bool
    real_money_order_authorized: bool
    live_trading_authorized: bool

    def __post_init__(self) -> None:
        if not self.family.strip():
            raise StrategyFamilyValidationError("family is required")
        spec = get_strategy_family(self.family)
        if not self.symbol.strip():
            raise StrategyFamilyValidationError("symbol is required")
        if not self.regime_state.strip():
            raise StrategyFamilyValidationError("regime_state is required")
        if self.direction not in spec.directions:
            raise StrategyFamilyValidationError(
                f"{self.family} does not declare direction {self.direction}"
            )
        if not self.provider.strip():
            raise StrategyFamilyValidationError("provider is required")
        if not self.selected_candidate_id.strip():
            raise StrategyFamilyValidationError("selected_candidate_id is required")
        _require_sha256(self.edge_input_fingerprint, "edge input fingerprint")
        _require_sha256(self.edge_report_sha256, "edge report SHA-256")
        if self.edge_verdict not in {"PASS", "REJECT"}:
            raise StrategyFamilyValidationError("edge verdict must be PASS or REJECT")
        if self.research_evidence_only is not True:
            raise StrategyFamilyValidationError(
                "family receipts must preserve research-only edge authority"
            )
        if self.holdout_accessed:
            raise StrategyFamilyValidationError("family validation cannot consume holdout evidence")
        if self.promotion_authority != 0:
            raise StrategyFamilyValidationError("family validation cannot consume promotion authority")
        if (
            self.trade_plan_authorized
            or self.real_money_order_authorized
            or self.live_trading_authorized
        ):
            raise StrategyFamilyValidationError(
                "family validation cannot consume trading authority"
            )


def _require_sha256(value: str, label: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise StrategyFamilyValidationError(f"{label} must be lowercase hexadecimal")


def _strict_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise StrategyFamilyValidationError(f"{label} must be a JSON boolean")
    return value


def _canonical_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def family_edge_receipt_from_report(
    *,
    family: str,
    symbol: str,
    regime_state: str,
    direction: str,
    edge_report: Mapping[str, Any],
) -> FamilyEdgeReceipt:
    """Bind one existing Strategy Edge Validation report to family context.

    This function performs no statistical validation itself. The child report
    must already be a V0.1 Strategy Edge Validation report.
    """

    if edge_report.get("schema") != "qookey-strategy-edge-validation-report-v0.1":
        raise StrategyFamilyValidationError("unsupported strategy edge report schema")
    authority = edge_report.get("authority")
    if not isinstance(authority, Mapping):
        raise StrategyFamilyValidationError("edge report authority object is required")

    try:
        payload = dict(edge_report)
        return FamilyEdgeReceipt(
            family=family,
            symbol=symbol,
            regime_state=regime_state,
            direction=direction,
            provider=str(edge_report["provider"]),
            selected_candidate_id=str(edge_report["selected_candidate_id"]),
            edge_input_fingerprint=str(edge_report["input_fingerprint"]),
            edge_report_sha256=_canonical_sha256(payload),
            edge_verdict=str(edge_report["verdict"]),
            research_evidence_only=_strict_bool(
                authority["research_evidence_only"], "authority.research_evidence_only"
            ),
            holdout_accessed=_strict_bool(
                authority["holdout_accessed"], "authority.holdout_accessed"
            ),
            promotion_authority=int(authority["promotion_authority"]),
            trade_plan_authorized=_strict_bool(
                authority["trade_plan_authorized"], "authority.trade_plan_authorized"
            ),
            real_money_order_authorized=_strict_bool(
                authority["real_money_order_authorized"],
                "authority.real_money_order_authorized",
            ),
            live_trading_authorized=_strict_bool(
                authority["live_trading_authorized"], "authority.live_trading_authorized"
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, StrategyFamilyValidationError):
            raise
        raise StrategyFamilyValidationError(
            f"invalid strategy edge report: {error}"
        ) from error


def _receipt_key(receipt: FamilyEdgeReceipt) -> tuple[str, str, str, str]:
    return (
        receipt.symbol,
        receipt.regime_state,
        receipt.direction,
        receipt.edge_input_fingerprint,
    )


def validate_strategy_family(
    family: str,
    receipts: Sequence[FamilyEdgeReceipt],
    policy: StrategyFamilyValidationPolicy | None = None,
) -> dict[str, Any]:
    """Aggregate existing edge evidence into family-level generalization review.

    PASS-like family readiness is intentionally named REVIEW_READY rather than
    PASS because this layer does not prove live profitability or promote the
    registered family.
    """

    spec = get_strategy_family(family)
    active = policy or StrategyFamilyValidationPolicy()
    source = tuple(receipts)

    if any(receipt.family != family for receipt in source):
        raise StrategyFamilyValidationError("all receipts must belong to the requested family")
    keys = tuple(_receipt_key(receipt) for receipt in source)
    if len(set(keys)) != len(keys):
        raise StrategyFamilyValidationError("duplicate family evidence receipt detected")

    providers = tuple(sorted({receipt.provider for receipt in source}))
    assets = tuple(sorted({receipt.symbol for receipt in source}))
    regimes = tuple(sorted({receipt.regime_state for receipt in source}))
    directions = tuple(sorted({receipt.direction for receipt in source}))

    reasons: list[str] = []
    failed_edge_count = sum(receipt.edge_verdict != "PASS" for receipt in source)
    if active.require_all_edge_pass and failed_edge_count:
        reasons.append("one_or_more_strategy_edge_reports_rejected")
    if active.require_single_provider and len(providers) > 1:
        reasons.append("provider_provenance_mixed")
    if len(source) < active.minimum_receipts:
        reasons.append("family_receipts_below_minimum")
    if len(assets) < active.minimum_distinct_assets:
        reasons.append("distinct_assets_below_minimum")
    if len(regimes) < active.minimum_distinct_regimes:
        reasons.append("distinct_regimes_below_minimum")

    hard_reject = {
        "one_or_more_strategy_edge_reports_rejected",
        "provider_provenance_mixed",
    }
    if any(reason in hard_reject for reason in reasons):
        state = "REJECT"
    elif reasons:
        state = "INSUFFICIENT_GENERALIZATION_COVERAGE"
    else:
        state = "FAMILY_EVIDENCE_READY_FOR_HUMAN_REVIEW"

    return {
        "schema": "qookey-strategy-family-validation-report-v0.1",
        "family": family,
        "category": spec.category,
        "state": state,
        "reasons": reasons or ["all_family_generalization_gates_pass"],
        "coverage": {
            "receipt_count": len(source),
            "distinct_assets": list(assets),
            "distinct_regimes": list(regimes),
            "directions_observed": list(directions),
            "providers": list(providers),
            "failed_edge_report_count": failed_edge_count,
        },
        "policy": {
            "minimum_receipts": active.minimum_receipts,
            "minimum_distinct_assets": active.minimum_distinct_assets,
            "minimum_distinct_regimes": active.minimum_distinct_regimes,
            "require_single_provider": active.require_single_provider,
            "require_all_edge_pass": active.require_all_edge_pass,
        },
        "lineage": {
            "edge_report_sha256s": [receipt.edge_report_sha256 for receipt in source],
            "edge_input_fingerprints": [
                receipt.edge_input_fingerprint for receipt in source
            ],
        },
        "authority": {
            "research_evidence_only": True,
            "family_registry_mutated": False,
            "strategy_edge_claimed": False,
            "provider_requests_performed": False,
            "r2_accessed": False,
            "holdout_accessed": False,
            "promotion_authority": 0,
            "position_sizing_authorized": False,
            "paper_execution_authorized": False,
            "trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
        "limitations": [
            "Child Strategy Edge PASS is required evidence, not proof of future profitability.",
            "Generalization coverage is a review gate and never promotes the registered family.",
            "Cost, capacity, portfolio interaction and position sizing remain separate downstream gates.",
            "Replacement holdout evidence is not consumed by this layer.",
        ],
    }


def validate_strategy_library_evidence(
    receipts: Sequence[FamilyEdgeReceipt],
    policy: StrategyFamilyValidationPolicy | None = None,
) -> dict[str, Any]:
    """Produce a non-ranking multi-family research summary."""

    grouped: dict[str, list[FamilyEdgeReceipt]] = {}
    for receipt in receipts:
        grouped.setdefault(receipt.family, []).append(receipt)

    reports = {
        family: validate_strategy_family(family, family_receipts, policy)
        for family, family_receipts in sorted(grouped.items())
    }
    state_counts: dict[str, int] = {}
    for report in reports.values():
        state = str(report["state"])
        state_counts[state] = state_counts.get(state, 0) + 1

    return {
        "schema": "qookey-strategy-library-validation-report-v0.1",
        "families_evaluated": list(reports),
        "family_reports": reports,
        "state_counts": state_counts,
        "ranking_performed": False,
        "winner_selected": False,
        "authority": {
            "research_evidence_only": True,
            "strategy_promotion_authorized": False,
            "position_sizing_authorized": False,
            "paper_execution_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }


def policy_from_config(payload: Mapping[str, Any]) -> StrategyFamilyValidationPolicy:
    if payload.get("schema") != "qookey-strategy-family-validation-v0.1":
        raise StrategyFamilyValidationError("unsupported strategy family validation config")
    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise StrategyFamilyValidationError("policy object is required")
    try:
        return StrategyFamilyValidationPolicy(
            minimum_receipts=int(policy["minimum_receipts"]),
            minimum_distinct_assets=int(policy["minimum_distinct_assets"]),
            minimum_distinct_regimes=int(policy["minimum_distinct_regimes"]),
            require_single_provider=_strict_bool(
                policy["require_single_provider"], "policy.require_single_provider"
            ),
            require_all_edge_pass=_strict_bool(
                policy["require_all_edge_pass"], "policy.require_all_edge_pass"
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise StrategyFamilyValidationError(
            f"invalid strategy family validation policy: {error}"
        ) from error
