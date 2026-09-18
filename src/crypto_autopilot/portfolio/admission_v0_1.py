from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass

from crypto_autopilot.risk import PositionSizingPlan
from crypto_autopilot.strategy_library import get_strategy_family, strategy_family_ids


FAMILY_REVIEW_READY = "FAMILY_EVIDENCE_READY_FOR_HUMAN_REVIEW"

OVERLAP_GROUPS: dict[str, str] = {
    "TREND_FOLLOWING": "DIRECTIONAL",
    "BREAKOUT": "DIRECTIONAL",
    "MOMENTUM": "DIRECTIONAL",
    "HIGH_VOLATILITY_TREND": "DIRECTIONAL",
    "MEAN_REVERSION": "RANGE",
    "LOW_VOLATILITY_RANGE": "RANGE",
}


def _validate_overlap_registry() -> None:
    if set(OVERLAP_GROUPS) != set(strategy_family_ids()):
        raise ValueError(
            "portfolio overlap groups must cover the complete strategy library"
        )


_validate_overlap_registry()


@dataclass(frozen=True, slots=True)
class PortfolioPolicy:
    """Fail-closed basket admission policy; not a strategy ranking model."""

    maximum_total_realized_risk_fraction: float = 0.03
    maximum_symbol_realized_risk_fraction: float = 0.015
    maximum_overlap_group_realized_risk_fraction: float = 0.02
    maximum_gross_notional_fraction: float = 3.0
    maximum_symbol_notional_fraction: float = 1.5
    maximum_routes_per_symbol: int = 2
    opposing_directions_same_symbol_allowed: bool = False
    automatic_subset_selection_authorized: bool = False

    def __post_init__(self) -> None:
        numeric = (
            self.maximum_total_realized_risk_fraction,
            self.maximum_symbol_realized_risk_fraction,
            self.maximum_overlap_group_realized_risk_fraction,
            self.maximum_gross_notional_fraction,
            self.maximum_symbol_notional_fraction,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in numeric):
            raise ValueError("portfolio policy numeric limits must be finite and positive")
        if self.maximum_symbol_realized_risk_fraction > (
            self.maximum_total_realized_risk_fraction
        ):
            raise ValueError("symbol risk cap cannot exceed total risk cap")
        if self.maximum_overlap_group_realized_risk_fraction > (
            self.maximum_total_realized_risk_fraction
        ):
            raise ValueError("overlap-group risk cap cannot exceed total risk cap")
        if self.maximum_symbol_notional_fraction > self.maximum_gross_notional_fraction:
            raise ValueError("symbol notional cap cannot exceed gross notional cap")
        if self.maximum_routes_per_symbol < 1:
            raise ValueError("maximum_routes_per_symbol must be positive")
        if not isinstance(self.opposing_directions_same_symbol_allowed, bool):
            raise ValueError("opposing_directions_same_symbol_allowed must be boolean")
        if not isinstance(self.automatic_subset_selection_authorized, bool):
            raise ValueError("automatic_subset_selection_authorized must be boolean")
        if self.automatic_subset_selection_authorized:
            raise ValueError("automatic subset selection is not authorized in V0.1")


@dataclass(frozen=True, slots=True)
class PortfolioExposure:
    """Existing open research/paper exposure counted before new proposals."""

    exposure_id: str
    symbol: str
    strategy_family: str
    direction: str
    notional_usd: float
    realized_risk_usd: float

    def __post_init__(self) -> None:
        if not self.exposure_id.strip() or not self.symbol.strip():
            raise ValueError("exposure_id and symbol are required")
        family = get_strategy_family(self.strategy_family)
        if self.direction not in family.directions:
            raise ValueError("existing exposure direction is not supported by family")
        values = (self.notional_usd, self.realized_risk_usd)
        if not all(math.isfinite(value) and value >= 0.0 for value in values):
            raise ValueError("existing exposure values must be finite and non-negative")
        if self.notional_usd <= 0.0 or self.realized_risk_usd <= 0.0:
            raise ValueError("existing exposure notional and risk must be positive")


@dataclass(frozen=True, slots=True)
class PortfolioProposal:
    proposal_id: str
    symbol: str
    strategy_family: str
    overlap_group: str
    direction: str
    as_of_ms: int
    family_validation_report_sha256: str
    sizing_equity_usd: float
    entry_price: float
    stop_price: float
    approved_notional_usd: float
    realized_risk_usd: float
    target_risk_usd: float
    risk_utilization_fraction: float


def _canonical_sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(
        dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _validate_family_report(
    strategy_family: str,
    family_validation_report: Mapping[str, object],
) -> str:
    if family_validation_report.get("schema") != (
        "qookey-strategy-family-validation-report-v0.1"
    ):
        raise ValueError("invalid family validation schema")
    if family_validation_report.get("family") != strategy_family:
        raise ValueError("family validation report does not match strategy family")
    if family_validation_report.get("state") != FAMILY_REVIEW_READY:
        raise ValueError("family validation report is not review-ready")

    authority = family_validation_report.get("authority")
    if not isinstance(authority, Mapping):
        raise ValueError("family validation authority object is required")
    if authority.get("research_evidence_only") is not True:
        raise ValueError("family validation must remain research-only")
    if authority.get("promotion_authority") != 0:
        raise ValueError("family validation promotion authority must remain zero")
    for key in (
        "position_sizing_authorized",
        "paper_execution_authorized",
        "trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"family validation authority must remain closed: {key}")
    return _canonical_sha256(family_validation_report)


def build_portfolio_proposal(
    *,
    symbol: str,
    strategy_family: str,
    family_validation_report: Mapping[str, object],
    as_of_ms: int,
    sizing_plan: PositionSizingPlan,
) -> PortfolioProposal:
    """Bind validated family evidence and one ready sizing plan into a proposal."""

    if not symbol.strip():
        raise ValueError("symbol is required")
    if as_of_ms < 0:
        raise ValueError("as_of_ms cannot be negative")
    family = get_strategy_family(strategy_family)
    if strategy_family not in OVERLAP_GROUPS:
        raise ValueError("strategy family has no governed overlap group")
    report_sha = _validate_family_report(strategy_family, family_validation_report)
    if sizing_plan.status != "SIZING_READY":
        raise ValueError("position sizing plan is not ready")
    if sizing_plan.direction not in family.directions:
        raise ValueError("sizing direction is not supported by strategy family")
    values = (
        sizing_plan.equity_usd,
        sizing_plan.entry_price,
        sizing_plan.stop_price,
        sizing_plan.approved_notional_usd,
        sizing_plan.realized_risk_usd,
        sizing_plan.target_risk_usd,
        sizing_plan.risk_utilization_fraction,
    )
    if not all(math.isfinite(value) and value > 0.0 for value in values):
        raise ValueError("portfolio proposal sizing values must be finite and positive")

    payload: dict[str, object] = {
        "schema": "qookey-portfolio-proposal-v0.1",
        "symbol": symbol,
        "strategy_family": strategy_family,
        "overlap_group": OVERLAP_GROUPS[strategy_family],
        "direction": sizing_plan.direction,
        "as_of_ms": as_of_ms,
        "family_validation_report_sha256": report_sha,
        "sizing_equity_usd": sizing_plan.equity_usd,
        "entry_price": sizing_plan.entry_price,
        "stop_price": sizing_plan.stop_price,
        "approved_notional_usd": sizing_plan.approved_notional_usd,
        "realized_risk_usd": sizing_plan.realized_risk_usd,
        "target_risk_usd": sizing_plan.target_risk_usd,
        "risk_utilization_fraction": sizing_plan.risk_utilization_fraction,
    }
    proposal_id = f"portfolio-v0-1-{_canonical_sha256(payload)}"
    return PortfolioProposal(
        proposal_id=proposal_id,
        symbol=symbol,
        strategy_family=strategy_family,
        overlap_group=OVERLAP_GROUPS[strategy_family],
        direction=sizing_plan.direction,
        as_of_ms=as_of_ms,
        family_validation_report_sha256=report_sha,
        sizing_equity_usd=sizing_plan.equity_usd,
        entry_price=sizing_plan.entry_price,
        stop_price=sizing_plan.stop_price,
        approved_notional_usd=sizing_plan.approved_notional_usd,
        realized_risk_usd=sizing_plan.realized_risk_usd,
        target_risk_usd=sizing_plan.target_risk_usd,
        risk_utilization_fraction=sizing_plan.risk_utilization_fraction,
    )


def _accumulate(
    exposures: Sequence[PortfolioExposure],
    proposals: Sequence[PortfolioProposal],
) -> tuple[
    float,
    float,
    dict[str, float],
    dict[str, float],
    dict[str, float],
    dict[str, int],
    dict[str, set[str]],
]:
    total_risk = sum(item.realized_risk_usd for item in exposures)
    gross_notional = sum(item.notional_usd for item in exposures)
    symbol_risk: dict[str, float] = defaultdict(float)
    symbol_notional: dict[str, float] = defaultdict(float)
    overlap_risk: dict[str, float] = defaultdict(float)
    route_count: dict[str, int] = defaultdict(int)
    directions: dict[str, set[str]] = defaultdict(set)

    for item in exposures:
        family_group = OVERLAP_GROUPS.get(item.strategy_family)
        if family_group is None:
            raise ValueError("existing exposure has ungoverned strategy overlap group")
        symbol_risk[item.symbol] += item.realized_risk_usd
        symbol_notional[item.symbol] += item.notional_usd
        overlap_risk[family_group] += item.realized_risk_usd
        route_count[item.symbol] += 1
        directions[item.symbol].add(item.direction)

    for item in proposals:
        total_risk += item.realized_risk_usd
        gross_notional += item.approved_notional_usd
        symbol_risk[item.symbol] += item.realized_risk_usd
        symbol_notional[item.symbol] += item.approved_notional_usd
        overlap_risk[item.overlap_group] += item.realized_risk_usd
        route_count[item.symbol] += 1
        directions[item.symbol].add(item.direction)

    return (
        total_risk,
        gross_notional,
        dict(symbol_risk),
        dict(symbol_notional),
        dict(overlap_risk),
        dict(route_count),
        dict(directions),
    )


def admit_portfolio(
    *,
    equity_usd: float,
    proposals: Sequence[PortfolioProposal],
    existing_exposures: Sequence[PortfolioExposure] = (),
    policy: PortfolioPolicy = PortfolioPolicy(),
) -> dict[str, object]:
    """Evaluate one explicit basket without ranking or subset optimization."""

    if not math.isfinite(equity_usd) or equity_usd <= 0.0:
        raise ValueError("equity_usd must be finite and positive")
    proposal_tuple = tuple(proposals)
    existing_tuple = tuple(existing_exposures)
    if not proposal_tuple:
        return {
            "schema": "qookey-portfolio-admission-report-v0.1",
            "state": "NO_PROPOSALS",
            "reasons": ["proposal_set_empty"],
            "admitted_proposal_ids": [],
            "rejected_proposal_ids": [],
            "ranking_performed": False,
            "subset_selection_performed": False,
            "authority": _authority(),
        }

    proposal_ids = tuple(item.proposal_id for item in proposal_tuple)
    if len(set(proposal_ids)) != len(proposal_ids):
        raise ValueError("portfolio proposal ids must be unique")

    if any(
        not math.isclose(
            item.sizing_equity_usd,
            equity_usd,
            rel_tol=0.0,
            abs_tol=1e-8,
        )
        for item in proposal_tuple
    ):
        raise ValueError("all portfolio proposals must use the portfolio equity basis")

    (
        total_risk,
        gross_notional,
        symbol_risk,
        symbol_notional,
        overlap_risk,
        route_count,
        directions,
    ) = _accumulate(existing_tuple, proposal_tuple)

    reasons: list[str] = []
    total_risk_fraction = total_risk / equity_usd
    gross_notional_fraction = gross_notional / equity_usd
    if total_risk_fraction > policy.maximum_total_realized_risk_fraction:
        reasons.append("total_realized_risk_above_cap")
    if gross_notional_fraction > policy.maximum_gross_notional_fraction:
        reasons.append("gross_notional_above_cap")

    for symbol, risk_usd in sorted(symbol_risk.items()):
        if risk_usd / equity_usd > policy.maximum_symbol_realized_risk_fraction:
            reasons.append(f"symbol_realized_risk_above_cap:{symbol}")
    for symbol, notional_usd in sorted(symbol_notional.items()):
        if notional_usd / equity_usd > policy.maximum_symbol_notional_fraction:
            reasons.append(f"symbol_notional_above_cap:{symbol}")
    for group, risk_usd in sorted(overlap_risk.items()):
        if risk_usd / equity_usd > policy.maximum_overlap_group_realized_risk_fraction:
            reasons.append(f"overlap_group_risk_above_cap:{group}")
    for symbol, count in sorted(route_count.items()):
        if count > policy.maximum_routes_per_symbol:
            reasons.append(f"routes_per_symbol_above_cap:{symbol}")
    if not policy.opposing_directions_same_symbol_allowed:
        for symbol, values in sorted(directions.items()):
            if len(values) > 1:
                reasons.append(f"opposing_directions_same_symbol:{symbol}")

    state = "PORTFOLIO_REVIEW_REQUIRED" if reasons else "PORTFOLIO_ADMITTED"
    admitted_ids = list(proposal_ids) if not reasons else []
    rejected_ids = list(proposal_ids) if reasons else []

    return {
        "schema": "qookey-portfolio-admission-report-v0.1",
        "state": state,
        "reasons": reasons or ["all_portfolio_admission_gates_pass"],
        "equity_usd": round(equity_usd, 8),
        "admitted_proposal_ids": admitted_ids,
        "rejected_proposal_ids": rejected_ids,
        "proposal_count": len(proposal_tuple),
        "existing_exposure_count": len(existing_tuple),
        "metrics": {
            "total_realized_risk_usd": round(total_risk, 8),
            "total_realized_risk_fraction": round(total_risk_fraction, 8),
            "gross_notional_usd": round(gross_notional, 8),
            "gross_notional_fraction": round(gross_notional_fraction, 8),
            "symbol_realized_risk_usd": {
                key: round(value, 8) for key, value in sorted(symbol_risk.items())
            },
            "symbol_notional_usd": {
                key: round(value, 8) for key, value in sorted(symbol_notional.items())
            },
            "overlap_group_realized_risk_usd": {
                key: round(value, 8) for key, value in sorted(overlap_risk.items())
            },
            "routes_per_symbol": dict(sorted(route_count.items())),
        },
        "policy": asdict(policy),
        "ranking_performed": False,
        "subset_selection_performed": False,
        "authority": _authority(),
        "limitations": [
            "V0.1 evaluates an explicit basket and does not rank strategy families.",
            "V0.1 does not optimize a subset when the proposed basket breaches a cap.",
            "Correlation is approximated only through governed strategy-overlap groups.",
            "Portfolio admission is paper/research evidence, not live-trading authority.",
        ],
    }


def _authority() -> dict[str, object]:
    return {
        "research_paper_admission_only": True,
        "provider_requests_performed": False,
        "r2_accessed": False,
        "holdout_accessed": False,
        "strategy_ranking_authorized": False,
        "automatic_subset_selection_authorized": False,
        "paper_execution_authorized": False,
        "short_paper_execution_authorized": False,
        "real_money_order_authorized": False,
        "live_trading_authorized": False,
    }


def position_sizing_plan_from_mapping(
    payload: Mapping[str, object],
) -> PositionSizingPlan:
    numeric_keys = (
        "equity_usd",
        "entry_price",
        "stop_price",
        "stop_distance_fraction",
        "target_risk_usd",
        "realized_risk_usd",
        "target_notional_usd",
        "approved_notional_usd",
        "required_leverage",
        "realized_leverage",
        "risk_utilization_fraction",
    )
    if any(isinstance(payload.get(key), bool) for key in numeric_keys):
        raise ValueError("position sizing numeric fields cannot be booleans")
    if not isinstance(payload.get("stop_preserved"), bool):
        raise ValueError("position sizing stop_preserved must be a JSON boolean")
    clipped_by = payload.get("clipped_by")
    if not isinstance(clipped_by, list) or any(
        not isinstance(item, str) for item in clipped_by
    ):
        raise ValueError("position sizing clipped_by must be an array of strings")
    try:
        return PositionSizingPlan(
            status=str(payload["status"]),
            reason=str(payload["reason"]),
            direction=str(payload["direction"]),
            equity_usd=float(payload["equity_usd"]),
            entry_price=float(payload["entry_price"]),
            stop_price=float(payload["stop_price"]),
            stop_distance_fraction=float(payload["stop_distance_fraction"]),
            target_risk_usd=float(payload["target_risk_usd"]),
            realized_risk_usd=float(payload["realized_risk_usd"]),
            target_notional_usd=float(payload["target_notional_usd"]),
            approved_notional_usd=float(payload["approved_notional_usd"]),
            required_leverage=float(payload["required_leverage"]),
            realized_leverage=float(payload["realized_leverage"]),
            risk_utilization_fraction=float(payload["risk_utilization_fraction"]),
            clipped_by=tuple(clipped_by),
            stop_preserved=bool(payload["stop_preserved"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"invalid position sizing plan: {error}") from error


def portfolio_admission_input_from_dict(
    payload: Mapping[str, object],
) -> tuple[float, tuple[PortfolioProposal, ...], tuple[PortfolioExposure, ...]]:
    if payload.get("schema") != "qookey-portfolio-admission-input-v0.1":
        raise ValueError("unsupported portfolio admission input schema")
    if isinstance(payload.get("equity_usd"), bool):
        raise ValueError("equity_usd cannot be boolean")
    try:
        equity_usd = float(payload["equity_usd"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"invalid equity_usd: {error}") from error

    proposal_items = payload.get("proposals")
    existing_items = payload.get("existing_exposures", [])
    if not isinstance(proposal_items, list):
        raise ValueError("proposals must be a JSON array")
    if not isinstance(existing_items, list):
        raise ValueError("existing_exposures must be a JSON array")

    proposals: list[PortfolioProposal] = []
    for index, item in enumerate(proposal_items):
        if not isinstance(item, Mapping):
            raise ValueError(f"proposals[{index}] must be a JSON object")
        family_report = item.get("family_validation_report")
        sizing_payload = item.get("position_sizing_plan")
        if not isinstance(family_report, Mapping):
            raise ValueError(
                f"proposals[{index}].family_validation_report must be an object"
            )
        if not isinstance(sizing_payload, Mapping):
            raise ValueError(
                f"proposals[{index}].position_sizing_plan must be an object"
            )
        if not isinstance(item.get("as_of_ms"), int) or isinstance(item.get("as_of_ms"), bool):
            raise ValueError(f"proposals[{index}].as_of_ms must be a JSON integer")
        try:
            proposals.append(
                build_portfolio_proposal(
                    symbol=str(item["symbol"]),
                    strategy_family=str(item["strategy_family"]),
                    family_validation_report=family_report,
                    as_of_ms=item["as_of_ms"],
                    sizing_plan=position_sizing_plan_from_mapping(sizing_payload),
                )
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"invalid proposals[{index}]: {error}") from error

    existing: list[PortfolioExposure] = []
    for index, item in enumerate(existing_items):
        if not isinstance(item, Mapping):
            raise ValueError(f"existing_exposures[{index}] must be a JSON object")
        if any(
            isinstance(item.get(key), bool)
            for key in ("notional_usd", "realized_risk_usd")
        ):
            raise ValueError(
                f"existing_exposures[{index}] numeric fields cannot be booleans"
            )
        try:
            existing.append(
                PortfolioExposure(
                    exposure_id=str(item["exposure_id"]),
                    symbol=str(item["symbol"]),
                    strategy_family=str(item["strategy_family"]),
                    direction=str(item["direction"]),
                    notional_usd=float(item["notional_usd"]),
                    realized_risk_usd=float(item["realized_risk_usd"]),
                )
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(
                f"invalid existing_exposures[{index}]: {error}"
            ) from error

    return equity_usd, tuple(proposals), tuple(existing)


def portfolio_policy_from_config(payload: Mapping[str, object]) -> PortfolioPolicy:
    if payload.get("schema") != "qookey-portfolio-admission-v0.1":
        raise ValueError("unsupported portfolio admission config")
    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("policy object is required")

    overlap_groups = payload.get("overlap_groups")
    if not isinstance(overlap_groups, Mapping):
        raise ValueError("overlap_groups object is required")
    expected_groups: dict[str, list[str]] = defaultdict(list)
    for family, group in OVERLAP_GROUPS.items():
        expected_groups[group].append(family)
    normalized_expected = {
        group: sorted(families) for group, families in sorted(expected_groups.items())
    }
    normalized_config: dict[str, list[str]] = {}
    for group, families in overlap_groups.items():
        if not isinstance(group, str) or not isinstance(families, list):
            raise ValueError("overlap_groups must map strings to arrays")
        normalized_config[group] = sorted(str(family) for family in families)
    if normalized_config != normalized_expected:
        raise ValueError("configured strategy overlap groups do not match code registry")

    numeric_keys = (
        "maximum_total_realized_risk_fraction",
        "maximum_symbol_realized_risk_fraction",
        "maximum_overlap_group_realized_risk_fraction",
        "maximum_gross_notional_fraction",
        "maximum_symbol_notional_fraction",
        "maximum_routes_per_symbol",
    )
    if any(isinstance(policy.get(key), bool) for key in numeric_keys):
        raise ValueError("portfolio numeric policy fields cannot be booleans")
    if not isinstance(policy.get("maximum_routes_per_symbol"), int):
        raise ValueError("policy.maximum_routes_per_symbol must be a JSON integer")
    for key in (
        "opposing_directions_same_symbol_allowed",
        "automatic_subset_selection_authorized",
    ):
        if not isinstance(policy.get(key), bool):
            raise ValueError(f"policy.{key} must be a JSON boolean")

    try:
        return PortfolioPolicy(
            maximum_total_realized_risk_fraction=float(
                policy["maximum_total_realized_risk_fraction"]
            ),
            maximum_symbol_realized_risk_fraction=float(
                policy["maximum_symbol_realized_risk_fraction"]
            ),
            maximum_overlap_group_realized_risk_fraction=float(
                policy["maximum_overlap_group_realized_risk_fraction"]
            ),
            maximum_gross_notional_fraction=float(
                policy["maximum_gross_notional_fraction"]
            ),
            maximum_symbol_notional_fraction=float(
                policy["maximum_symbol_notional_fraction"]
            ),
            maximum_routes_per_symbol=int(policy["maximum_routes_per_symbol"]),
            opposing_directions_same_symbol_allowed=bool(
                policy["opposing_directions_same_symbol_allowed"]
            ),
            automatic_subset_selection_authorized=bool(
                policy["automatic_subset_selection_authorized"]
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"invalid portfolio admission config: {error}") from error
