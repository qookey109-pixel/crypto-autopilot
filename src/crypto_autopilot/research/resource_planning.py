"""Bounded resource-aware ordering for offline research proposals."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from crypto_autopilot.lineage import assert_no_secret_fields, assert_sha256, sha256_json


class ResourcePlanningError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ResearchProposal:
    proposal_id: str
    config: Mapping[str, Any]
    utility_score: float
    proposal_seed: int

    def __post_init__(self) -> None:
        if not self.proposal_id.strip():
            raise ResourcePlanningError("proposal_id is required")
        if not math.isfinite(self.utility_score) or not 0.0 <= self.utility_score <= 1.0:
            raise ResourcePlanningError("utility_score must be within [0, 1]")
        assert_no_secret_fields(self.config)

    @property
    def config_sha256(self) -> str:
        return sha256_json(self.config)


@dataclass(frozen=True, slots=True)
class ResourceEstimate:
    proposal_id: str
    resource_profile_sha256: str
    wall_clock_seconds: float
    environment_steps: int
    r2_bytes: int = 0
    source_data_role: str = "resource-accounting-estimate"
    holdout_accessed: bool = False
    validation_score_consumed: bool = False
    promotion_outcome_consumed: bool = False
    deployment_outcome_consumed: bool = False

    def __post_init__(self) -> None:
        if not self.proposal_id.strip():
            raise ResourcePlanningError("estimate proposal_id is required")
        assert_sha256(self.resource_profile_sha256, "resource_profile_sha256")
        if not math.isfinite(self.wall_clock_seconds) or self.wall_clock_seconds < 0:
            raise ResourcePlanningError("wall_clock_seconds must be finite and >= 0")
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in (self.environment_steps, self.r2_bytes)
        ):
            raise ResourcePlanningError("resource counters must be non-negative integers")
        if self.source_data_role != "resource-accounting-estimate":
            raise ResourcePlanningError("resource estimates have a fixed data role")
        if any((self.holdout_accessed, self.validation_score_consumed, self.promotion_outcome_consumed, self.deployment_outcome_consumed)):
            raise ResourcePlanningError("resource estimates cannot consume quality or deployment outcomes")


@dataclass(frozen=True, slots=True)
class ResourcePlanningPolicy:
    configured_cost_weight: float = 0.30
    minimum_adaptive_utility_weight: float = 0.65
    max_proposals: int = 256
    promotion_authority: int = 0
    trade_plan_authorized: bool = False
    holdout_access_authorized: bool = False

    def __post_init__(self) -> None:
        if not math.isfinite(self.configured_cost_weight) or not 0.0 <= self.configured_cost_weight <= 0.35:
            raise ResourcePlanningError("configured_cost_weight must be within [0, 0.35]")
        if not math.isfinite(self.minimum_adaptive_utility_weight) or not 0.65 <= self.minimum_adaptive_utility_weight <= 1.0:
            raise ResourcePlanningError("minimum_adaptive_utility_weight must be within [0.65, 1]")
        if 1.0 - self.configured_cost_weight < self.minimum_adaptive_utility_weight:
            raise ResourcePlanningError("adaptive utility must remain dominant")
        if not 1 <= self.max_proposals <= 4096:
            raise ResourcePlanningError("max_proposals must be within [1, 4096]")
        if int(self.promotion_authority) != 0 or self.trade_plan_authorized or self.holdout_access_authorized:
            raise ResourcePlanningError("resource planning has no promotion, trade or holdout authority")


@dataclass(frozen=True, slots=True)
class ResourceRanking:
    proposal_id: str
    config_sha256: str
    utility_score: float
    normalized_resource_cost: float
    acquisition_score: float
    estimate_available: bool


@dataclass(frozen=True, slots=True)
class ResourcePlanReceipt:
    contract_version: str
    rankings: tuple[ResourceRanking, ...]
    resource_profile_sha256: str | None
    estimate_coverage_fraction: float
    effective_adaptive_utility_weight: float
    effective_cost_weight: float
    holdout_accessed: bool = False
    promotion_authority: int = 0
    trade_plan_authorized: bool = False

    def evidence(self) -> dict[str, Any]:
        return {
            "contractVersion": self.contract_version,
            "rankings": [
                {
                    "proposalId": ranking.proposal_id,
                    "configSha256": ranking.config_sha256,
                    "utilityScore": ranking.utility_score,
                    "normalizedResourceCost": ranking.normalized_resource_cost,
                    "acquisitionScore": ranking.acquisition_score,
                    "estimateAvailable": ranking.estimate_available,
                }
                for ranking in self.rankings
            ],
            "resourceProfileSha256": self.resource_profile_sha256,
            "estimateCoverageFraction": self.estimate_coverage_fraction,
            "effectiveAdaptiveUtilityWeight": self.effective_adaptive_utility_weight,
            "effectiveCostWeight": self.effective_cost_weight,
            "holdoutAccessed": False,
            "promotionAuthority": 0,
            "tradePlanAuthorized": False,
        }


def rank_research_proposals(
    proposals: Iterable[ResearchProposal],
    estimates: Iterable[ResourceEstimate] = (),
    *,
    policy: ResourcePlanningPolicy = ResourcePlanningPolicy(),
) -> ResourcePlanReceipt:
    rows = tuple(proposals)
    if not rows:
        raise ResourcePlanningError("at least one proposal is required")
    if len(rows) > policy.max_proposals:
        raise ResourcePlanningError("proposal count exceeds bounded planner limit")
    if len({row.proposal_id for row in rows}) != len(rows):
        raise ResourcePlanningError("proposal ids must be unique")
    estimate_rows = tuple(estimates)
    by_id: dict[str, ResourceEstimate] = {}
    proposal_ids = {row.proposal_id for row in rows}
    for row in estimate_rows:
        if row.proposal_id not in proposal_ids:
            raise ResourcePlanningError("resource estimate references an unknown proposal")
        if row.proposal_id in by_id:
            raise ResourcePlanningError("duplicate resource estimate")
        by_id[row.proposal_id] = row
    profiles = {row.resource_profile_sha256 for row in estimate_rows}
    if len(profiles) > 1:
        raise ResourcePlanningError("resource estimates must share one profile fingerprint")

    costs = {
        row.proposal_id: float(row.wall_clock_seconds) + float(row.environment_steps) / 100_000.0 + float(row.r2_bytes) / 1_000_000_000.0
        for row in estimate_rows
    }
    if costs:
        low, high = min(costs.values()), max(costs.values())
        normalized = {key: 0.5 if abs(high - low) <= 1e-12 else (value - low) / (high - low) for key, value in costs.items()}
    else:
        normalized = {}
    cost_weight = float(policy.configured_cost_weight)
    utility_weight = 1.0 - cost_weight
    rankings = []
    for proposal in rows:
        cost = normalized.get(proposal.proposal_id, 0.5)
        score = utility_weight * proposal.utility_score + cost_weight * (1.0 - cost)
        rankings.append(ResourceRanking(proposal.proposal_id, proposal.config_sha256, proposal.utility_score, cost, score, proposal.proposal_id in normalized))
    rankings.sort(key=lambda row: (-row.acquisition_score, row.proposal_id))
    return ResourcePlanReceipt(
        contract_version="0.1.0",
        rankings=tuple(rankings),
        resource_profile_sha256=next(iter(profiles), None),
        estimate_coverage_fraction=len(normalized) / len(rows),
        effective_adaptive_utility_weight=utility_weight,
        effective_cost_weight=cost_weight,
    )
