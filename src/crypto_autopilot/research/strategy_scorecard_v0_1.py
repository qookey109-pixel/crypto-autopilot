from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any, cast

from crypto_autopilot.strategy_library import get_strategy_family


_ALLOWED_STATES = {
    "REJECT",
    "INSUFFICIENT_GENERALIZATION_COVERAGE",
    "FAMILY_EVIDENCE_READY_FOR_HUMAN_REVIEW",
}


@dataclass(frozen=True, slots=True)
class StrategyResearchScorecardPolicy:
    receipt_coverage_weight: float = 0.20
    asset_breadth_weight: float = 0.25
    regime_breadth_weight: float = 0.20
    direction_breadth_weight: float = 0.10
    edge_consistency_weight: float = 0.25
    ready_state_multiplier: float = 1.0
    insufficient_state_multiplier: float = 0.65
    breadth_saturation_multiple: float = 2.0
    research_ranking_authorized: bool = True
    winner_selection_authorized: bool = False
    automatic_strategy_selection_authorized: bool = False
    position_sizing_authorized: bool = False
    paper_execution_authorized: bool = False
    real_money_order_authorized: bool = False
    live_real_trading_authorized: bool = False

    def __post_init__(self) -> None:
        weights = (
            self.receipt_coverage_weight,
            self.asset_breadth_weight,
            self.regime_breadth_weight,
            self.direction_breadth_weight,
            self.edge_consistency_weight,
        )
        multipliers = (
            self.ready_state_multiplier,
            self.insufficient_state_multiplier,
            self.breadth_saturation_multiple,
        )
        if any(isinstance(value, bool) for value in weights + multipliers):
            raise ValueError("scorecard numeric values cannot be booleans")
        if not all(math.isfinite(value) for value in weights + multipliers):
            raise ValueError("scorecard numeric values must be finite")
        if any(value < 0.0 for value in weights):
            raise ValueError("scorecard weights cannot be negative")
        if not math.isclose(sum(weights), 1.0, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError("scorecard weights must sum exactly to one")
        if not 0.0 < self.insufficient_state_multiplier <= self.ready_state_multiplier <= 1.0:
            raise ValueError("scorecard state multipliers are invalid")
        if self.breadth_saturation_multiple < 1.0:
            raise ValueError("breadth_saturation_multiple must be at least one")

        flags = (
            self.research_ranking_authorized,
            self.winner_selection_authorized,
            self.automatic_strategy_selection_authorized,
            self.position_sizing_authorized,
            self.paper_execution_authorized,
            self.real_money_order_authorized,
            self.live_real_trading_authorized,
        )
        if any(not isinstance(value, bool) for value in flags):
            raise ValueError("scorecard authority flags must be booleans")
        if not self.research_ranking_authorized:
            raise ValueError("Scorecard V0.1 requires research ranking authority")
        if any(flags[1:]):
            raise ValueError("Scorecard V0.1 cannot authorize selection or execution")


def _canonical(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _canonical(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    return value


def _sha256(value: object) -> str:
    encoded = json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _strict_nonnegative_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _strict_positive_int(value: object, label: str) -> int:
    parsed = _strict_nonnegative_int(value, label)
    if parsed < 1:
        raise ValueError(f"{label} must be positive")
    return parsed


def _unique_strings(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    parsed: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{label}[{index}] must be a non-empty string")
        parsed.append(item)
    if len(set(parsed)) != len(parsed):
        raise ValueError(f"{label} cannot contain duplicates")
    return tuple(parsed)


def _validate_authority(report: Mapping[str, object]) -> None:
    authority = report.get("authority")
    if not isinstance(authority, Mapping):
        raise ValueError("family validation authority object is required")
    if authority.get("research_evidence_only") is not True:
        raise ValueError("family validation must remain research evidence only")
    for key in (
        "family_registry_mutated",
        "strategy_edge_claimed",
        "provider_requests_performed",
        "r2_accessed",
        "holdout_accessed",
        "position_sizing_authorized",
        "paper_execution_authorized",
        "trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"family validation authority must remain closed: {key}")
    promotion = authority.get("promotion_authority")
    if not isinstance(promotion, int) or isinstance(promotion, bool) or promotion != 0:
        raise ValueError("family validation promotion_authority must equal zero")


def _validate_family_report(report: Mapping[str, object]) -> dict[str, object]:
    if report.get("schema") != "qookey-strategy-family-validation-report-v0.1":
        raise ValueError("unsupported strategy family validation report schema")
    family = report.get("family")
    state = report.get("state")
    if not isinstance(family, str) or not family.strip():
        raise ValueError("family validation report family is required")
    spec = get_strategy_family(family)
    if state not in _ALLOWED_STATES:
        raise ValueError("family validation report state is invalid")
    _validate_authority(report)

    coverage = report.get("coverage")
    policy = report.get("policy")
    lineage = report.get("lineage")
    if not isinstance(coverage, Mapping):
        raise ValueError("family validation coverage object is required")
    if not isinstance(policy, Mapping):
        raise ValueError("family validation policy object is required")
    if not isinstance(lineage, Mapping):
        raise ValueError("family validation lineage object is required")

    receipt_count = _strict_nonnegative_int(
        coverage.get("receipt_count"),
        "coverage.receipt_count",
    )
    assets = _unique_strings(coverage.get("distinct_assets"), "coverage.distinct_assets")
    regimes = _unique_strings(
        coverage.get("distinct_regimes"),
        "coverage.distinct_regimes",
    )
    directions = _unique_strings(
        coverage.get("directions_observed"),
        "coverage.directions_observed",
    )
    providers = _unique_strings(coverage.get("providers"), "coverage.providers")
    failed_count = _strict_nonnegative_int(
        coverage.get("failed_edge_report_count"),
        "coverage.failed_edge_report_count",
    )
    if failed_count > receipt_count:
        raise ValueError("failed edge report count cannot exceed receipt count")
    if any(direction not in spec.directions for direction in directions):
        raise ValueError("family validation contains unsupported observed direction")

    minimum_receipts = _strict_positive_int(
        policy.get("minimum_receipts"),
        "policy.minimum_receipts",
    )
    minimum_assets = _strict_positive_int(
        policy.get("minimum_distinct_assets"),
        "policy.minimum_distinct_assets",
    )
    minimum_regimes = _strict_positive_int(
        policy.get("minimum_distinct_regimes"),
        "policy.minimum_distinct_regimes",
    )
    for key in ("require_single_provider", "require_all_edge_pass"):
        if not isinstance(policy.get(key), bool):
            raise ValueError(f"policy.{key} must be a JSON boolean")

    report_hashes = _unique_strings(
        lineage.get("edge_report_sha256s"),
        "lineage.edge_report_sha256s",
    )
    fingerprints = _unique_strings(
        lineage.get("edge_input_fingerprints"),
        "lineage.edge_input_fingerprints",
    )
    if len(report_hashes) != receipt_count or len(fingerprints) != receipt_count:
        raise ValueError("family validation lineage count must equal receipt count")
    for label, values in (
        ("edge report sha", report_hashes),
        ("edge input fingerprint", fingerprints),
    ):
        if any(
            len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
            for value in values
        ):
            raise ValueError(f"{label} must be lowercase SHA-256 hex")

    if state == "FAMILY_EVIDENCE_READY_FOR_HUMAN_REVIEW":
        if receipt_count < minimum_receipts:
            raise ValueError("ready family has insufficient receipt count")
        if len(assets) < minimum_assets:
            raise ValueError("ready family has insufficient asset breadth")
        if len(regimes) < minimum_regimes:
            raise ValueError("ready family has insufficient regime breadth")
        if failed_count != 0:
            raise ValueError("ready family cannot contain failed edge reports")
        if policy.get("require_single_provider") is True and len(providers) != 1:
            raise ValueError("ready family violates single-provider policy")

    return {
        "family": family,
        "category": spec.category,
        "state": state,
        "receipt_count": receipt_count,
        "asset_count": len(assets),
        "regime_count": len(regimes),
        "direction_count": len(directions),
        "supported_direction_count": len(spec.directions),
        "provider_count": len(providers),
        "failed_count": failed_count,
        "minimum_receipts": minimum_receipts,
        "minimum_assets": minimum_assets,
        "minimum_regimes": minimum_regimes,
        "family_report_sha256": _sha256(report),
    }


def _breadth_score(observed: int, minimum: int, saturation_multiple: float) -> float:
    saturation = minimum * saturation_multiple
    return min(1.0, observed / saturation) if saturation > 0 else 0.0


def _score_one(
    report: Mapping[str, object],
    *,
    policy: StrategyResearchScorecardPolicy,
) -> dict[str, object]:
    parsed = _validate_family_report(report)
    state = cast(str, parsed["state"])
    receipt_count = cast(int, parsed["receipt_count"])
    failed_count = cast(int, parsed["failed_count"])

    dimensions = {
        "receipt_coverage": _breadth_score(
            receipt_count,
            cast(int, parsed["minimum_receipts"]),
            policy.breadth_saturation_multiple,
        ),
        "asset_breadth": _breadth_score(
            cast(int, parsed["asset_count"]),
            cast(int, parsed["minimum_assets"]),
            policy.breadth_saturation_multiple,
        ),
        "regime_breadth": _breadth_score(
            cast(int, parsed["regime_count"]),
            cast(int, parsed["minimum_regimes"]),
            policy.breadth_saturation_multiple,
        ),
        "direction_breadth": min(
            1.0,
            cast(int, parsed["direction_count"])
            / max(1, cast(int, parsed["supported_direction_count"])),
        ),
        "edge_consistency": (
            0.0
            if receipt_count == 0
            else max(0.0, 1.0 - failed_count / receipt_count)
        ),
    }
    raw = (
        dimensions["receipt_coverage"] * policy.receipt_coverage_weight
        + dimensions["asset_breadth"] * policy.asset_breadth_weight
        + dimensions["regime_breadth"] * policy.regime_breadth_weight
        + dimensions["direction_breadth"] * policy.direction_breadth_weight
        + dimensions["edge_consistency"] * policy.edge_consistency_weight
    )
    if state == "FAMILY_EVIDENCE_READY_FOR_HUMAN_REVIEW":
        multiplier = policy.ready_state_multiplier
        rankable = True
    elif state == "INSUFFICIENT_GENERALIZATION_COVERAGE":
        multiplier = policy.insufficient_state_multiplier
        rankable = True
    else:
        multiplier = 0.0
        rankable = False

    score = round(100.0 * raw * multiplier, 8)
    return {
        **parsed,
        "dimensions": {key: round(value, 8) for key, value in dimensions.items()},
        "state_multiplier": multiplier,
        "research_score": score,
        "rankable_for_research": rankable,
        "research_rank": None,
    }


def build_strategy_research_scorecard(
    family_reports: Sequence[Mapping[str, object]],
    *,
    policy: StrategyResearchScorecardPolicy = StrategyResearchScorecardPolicy(),
) -> dict[str, object]:
    """Rank family evidence for research-review priority only."""

    reports = tuple(family_reports)
    if not reports:
        raise ValueError("at least one family validation report is required")

    scored = [_score_one(report, policy=policy) for report in reports]
    families = [str(row["family"]) for row in scored]
    if len(set(families)) != len(families):
        raise ValueError("scorecard cannot contain duplicate strategy families")

    rankable = sorted(
        (row for row in scored if row["rankable_for_research"]),
        key=lambda row: (
            -cast(float, row["research_score"]),
            cast(str, row["family"]),
        ),
    )
    rank_by_family = {
        str(row["family"]): index + 1 for index, row in enumerate(rankable)
    }
    rows: list[dict[str, object]] = []
    for row in sorted(
        scored,
        key=lambda item: (
            item["research_rank"] is None,
            rank_by_family.get(str(item["family"]), 10**9),
            str(item["family"]),
        ),
    ):
        enriched = dict(row)
        enriched["research_rank"] = rank_by_family.get(str(row["family"]))
        rows.append(enriched)

    priority_order = [str(row["family"]) for row in rankable]
    rows_sha256 = _sha256(rows)
    scorecard_payload = {
        "schema": "qookey-strategy-research-scorecard-id-v0.1",
        "family_report_sha256s": sorted(
            str(row["family_report_sha256"]) for row in scored
        ),
        "policy": asdict(policy),
        "priority_order": priority_order,
        "rows_sha256": rows_sha256,
    }
    scorecard_id = f"strategy-research-scorecard-v0-1-{_sha256(scorecard_payload)}"
    return {
        "schema": "qookey-strategy-research-scorecard-report-v0.1",
        "scorecard_id": scorecard_id,
        "state": "RESEARCH_PRIORITY_RANKING_READY",
        "family_count": len(rows),
        "ranked_family_count": len(rankable),
        "research_priority_order": priority_order,
        "rows_sha256": rows_sha256,
        "rows": rows,
        "ranking_performed": True,
        "winner_selected": False,
        "execution_selection_performed": False,
        "policy": asdict(policy),
        "authority": {
            "research_evidence_only": True,
            "research_ranking_authorized": True,
            "ranking_is_trade_recommendation": False,
            "winner_selection_authorized": False,
            "automatic_strategy_selection_authorized": False,
            "strategy_registry_mutation_authorized": False,
            "position_sizing_authorized": False,
            "paper_execution_authorized": False,
            "private_exchange_api_authorized": False,
            "holdout_access_authorized": False,
            "real_money_order_authorized": False,
            "live_real_trading_authorized": False,
        },
        "limitations": [
            "Ranking orders research-review priority, not expected profitability.",
            "A research rank never selects a strategy for Paper Cycle or Live Paper execution.",
            "Family reports remain provider-separated and replacement holdout is not consumed.",
            "Historical evidence does not prove future profitability.",
        ],
    }


def verify_strategy_research_scorecard(
    payload: Mapping[str, object],
) -> str:
    if payload.get("schema") != "qookey-strategy-research-scorecard-report-v0.1":
        raise ValueError("unsupported strategy research scorecard report schema")
    if payload.get("state") != "RESEARCH_PRIORITY_RANKING_READY":
        raise ValueError("strategy research scorecard is not ready")
    rows = payload.get("rows")
    policy_payload = payload.get("policy")
    priority = payload.get("research_priority_order")
    if not isinstance(rows, list) or not rows:
        raise ValueError("strategy research scorecard rows are required")
    if not isinstance(policy_payload, Mapping):
        raise ValueError("strategy research scorecard policy is required")
    if not isinstance(priority, list):
        raise ValueError("strategy research priority order must be an array")
    policy = scorecard_policy_from_mapping(policy_payload)

    report_hashes: list[str] = []
    recomputed_priority: list[tuple[int, str]] = []
    families: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("strategy research scorecard row must be an object")
        family = row.get("family")
        report_hash = row.get("family_report_sha256")
        rank = row.get("research_rank")
        if not isinstance(family, str) or not family:
            raise ValueError("scorecard row family is required")
        if family in families:
            raise ValueError("scorecard row families must be unique")
        families.add(family)
        if (
            not isinstance(report_hash, str)
            or len(report_hash) != 64
            or any(character not in "0123456789abcdef" for character in report_hash)
        ):
            raise ValueError("scorecard row family report SHA is invalid")
        report_hashes.append(report_hash)
        if rank is not None:
            if not isinstance(rank, int) or isinstance(rank, bool) or rank < 1:
                raise ValueError("scorecard research_rank is invalid")
            recomputed_priority.append((rank, family))

    recomputed_priority.sort()
    if [family for _, family in recomputed_priority] != priority:
        raise ValueError("scorecard priority order does not match row ranks")
    if [rank for rank, _ in recomputed_priority] != list(
        range(1, len(recomputed_priority) + 1)
    ):
        raise ValueError("scorecard research ranks must be contiguous")

    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise ValueError("scorecard authority object is required")
    if authority.get("research_evidence_only") is not True:
        raise ValueError("scorecard must remain research evidence only")
    if authority.get("research_ranking_authorized") is not True:
        raise ValueError("scorecard research ranking authority is required")
    if authority.get("ranking_is_trade_recommendation") is not False:
        raise ValueError("scorecard ranking cannot be a trade recommendation")
    for key in (
        "winner_selection_authorized",
        "automatic_strategy_selection_authorized",
        "strategy_registry_mutation_authorized",
        "position_sizing_authorized",
        "paper_execution_authorized",
        "private_exchange_api_authorized",
        "holdout_access_authorized",
        "real_money_order_authorized",
        "live_real_trading_authorized",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"scorecard authority must remain closed: {key}")

    rows_sha256 = _sha256(rows)
    if payload.get("rows_sha256") != rows_sha256:
        raise ValueError("strategy research scorecard rows hash mismatch")
    payload_for_id = {
        "schema": "qookey-strategy-research-scorecard-id-v0.1",
        "family_report_sha256s": sorted(report_hashes),
        "policy": asdict(policy),
        "priority_order": list(priority),
        "rows_sha256": rows_sha256,
    }
    expected = f"strategy-research-scorecard-v0-1-{_sha256(payload_for_id)}"
    if payload.get("scorecard_id") != expected:
        raise ValueError("strategy research scorecard id mismatch")
    return expected


def scorecard_policy_from_mapping(
    payload: Mapping[str, object],
) -> StrategyResearchScorecardPolicy:
    numeric_keys = (
        "receipt_coverage_weight",
        "asset_breadth_weight",
        "regime_breadth_weight",
        "direction_breadth_weight",
        "edge_consistency_weight",
        "ready_state_multiplier",
        "insufficient_state_multiplier",
        "breadth_saturation_multiple",
    )
    numeric: dict[str, float] = {}
    for key in numeric_keys:
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{key} must be numeric")
        numeric[key] = float(value)
    bool_keys = (
        "research_ranking_authorized",
        "winner_selection_authorized",
        "automatic_strategy_selection_authorized",
        "position_sizing_authorized",
        "paper_execution_authorized",
        "real_money_order_authorized",
        "live_real_trading_authorized",
    )
    flags: dict[str, bool] = {}
    for key in bool_keys:
        value = payload.get(key)
        if not isinstance(value, bool):
            raise ValueError(f"{key} must be a JSON boolean")
        flags[key] = value
    return StrategyResearchScorecardPolicy(
        receipt_coverage_weight=numeric["receipt_coverage_weight"],
        asset_breadth_weight=numeric["asset_breadth_weight"],
        regime_breadth_weight=numeric["regime_breadth_weight"],
        direction_breadth_weight=numeric["direction_breadth_weight"],
        edge_consistency_weight=numeric["edge_consistency_weight"],
        ready_state_multiplier=numeric["ready_state_multiplier"],
        insufficient_state_multiplier=numeric["insufficient_state_multiplier"],
        breadth_saturation_multiple=numeric["breadth_saturation_multiple"],
        research_ranking_authorized=flags["research_ranking_authorized"],
        winner_selection_authorized=flags["winner_selection_authorized"],
        automatic_strategy_selection_authorized=flags[
            "automatic_strategy_selection_authorized"
        ],
        position_sizing_authorized=flags["position_sizing_authorized"],
        paper_execution_authorized=flags["paper_execution_authorized"],
        real_money_order_authorized=flags["real_money_order_authorized"],
        live_real_trading_authorized=flags["live_real_trading_authorized"],
    )


def scorecard_policy_from_config(
    payload: Mapping[str, object],
) -> StrategyResearchScorecardPolicy:
    if payload.get("schema") != "qookey-strategy-research-scorecard-v0.1":
        raise ValueError("unsupported strategy research scorecard config")
    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("strategy research scorecard policy object is required")
    return scorecard_policy_from_mapping(policy)


def scorecard_input_from_dict(
    payload: Mapping[str, Any],
) -> tuple[Mapping[str, object], ...]:
    if payload.get("schema") != "qookey-strategy-research-scorecard-input-v0.1":
        raise ValueError("unsupported strategy research scorecard input schema")
    reports = payload.get("family_reports")
    if not isinstance(reports, list):
        raise ValueError("family_reports must be a JSON array")
    parsed: list[Mapping[str, object]] = []
    for index, report in enumerate(reports):
        if not isinstance(report, Mapping):
            raise ValueError(f"family_reports[{index}] must be an object")
        parsed.append(report)
    return tuple(parsed)
