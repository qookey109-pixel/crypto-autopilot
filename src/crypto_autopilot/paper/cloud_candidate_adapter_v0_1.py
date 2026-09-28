"""Fail-closed adapter from versioned qualified strategy outputs to Paper inputs.

This module does not implement or select a strategy. It validates outputs already
produced by an explicitly paper-qualified registry entry and binds them to the
current Pionex market evidence and Strategy Router match.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

REGISTRY_SCHEMA = "qookey-cloud-paper-strategy-registry-v0.1"
MARKET_SCHEMA = "qookey-cloud-paper-market-report-v0.1"
ELIGIBLE_REGISTRY_STATUS = "QUALIFIED_PAPER_STRATEGIES_AVAILABLE"
EMPTY_REGISTRY_STATUS = "EMPTY_NO_ELIGIBLE_STRATEGIES"
ELIGIBLE_QUALIFICATION_STATE = "PAPER_ELIGIBLE"
MAX_CANDIDATES = 5
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CloudCandidateRegistryBlocked(ValueError):
    """The versioned registry cannot authorize candidate execution."""


@dataclass(frozen=True, slots=True)
class CandidateSelection:
    status: str
    candidates: tuple[Mapping[str, object], ...]
    reasons: tuple[str, ...]


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _positive_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) > 0.0
    )


def _false_authority(qualification: Mapping[str, object]) -> bool:
    return all(
        qualification.get(key) is False
        for key in (
            "holdout_accessed",
            "source_switch_authorized",
            "model_promotion_authorized",
            "real_money_order_authorized",
            "live_trading_authorized",
        )
    )


def validate_strategy_registry(
    registry: Mapping[str, object],
) -> dict[str, Mapping[str, object]]:
    """Validate every production registration before provider or R2 access."""
    if registry.get("schema") != REGISTRY_SCHEMA:
        raise CloudCandidateRegistryBlocked("STRATEGY_REGISTRY_SCHEMA_INVALID")
    strategies = registry.get("strategies")
    if not isinstance(strategies, list):
        raise CloudCandidateRegistryBlocked("STRATEGY_REGISTRY_ENTRIES_INVALID")
    if (
        registry.get("production_fixture_admission") is not False
        or registry.get("automatic_promotion") is not False
    ):
        raise CloudCandidateRegistryBlocked("STRATEGY_REGISTRY_AUTHORITY_INVALID")
    status = registry.get("status")
    if status == EMPTY_REGISTRY_STATUS:
        if strategies:
            raise CloudCandidateRegistryBlocked("EMPTY_REGISTRY_CONTAINS_STRATEGIES")
        return {}
    if status != ELIGIBLE_REGISTRY_STATUS or not strategies:
        raise CloudCandidateRegistryBlocked("STRATEGY_REGISTRY_NOT_PAPER_QUALIFIED")

    registrations: dict[str, Mapping[str, object]] = {}
    for raw in strategies:
        if not isinstance(raw, Mapping):
            raise CloudCandidateRegistryBlocked("STRATEGY_REGISTRATION_INVALID")
        strategy_id = raw.get("strategy_id")
        family = raw.get("strategy_family")
        provider = raw.get("provider")
        symbols = raw.get("symbols")
        regimes = raw.get("regimes")
        implementation_sha = raw.get("implementation_sha256")
        model_dependency = raw.get("model_dependency")
        qualification = raw.get("qualification")
        if (
            not isinstance(strategy_id, str) or not strategy_id
            or strategy_id in registrations
            or not isinstance(family, str) or not family
            or provider != "PIONEX_PUBLIC"
            or not isinstance(symbols, list) or not symbols
            or any(not isinstance(x, str) or not x for x in symbols)
            or len(set(symbols)) != len(symbols)
            or not isinstance(regimes, list) or not regimes
            or any(not isinstance(x, str) or not x for x in regimes)
            or len(set(regimes)) != len(regimes)
            or not _is_sha256(implementation_sha)
            or model_dependency not in {"NONE", "CORE100"}
            or not isinstance(qualification, Mapping)
        ):
            raise CloudCandidateRegistryBlocked("STRATEGY_REGISTRATION_INVALID")
        receipt_path = qualification.get("receipt_path")
        receipt_sha = qualification.get("receipt_sha256")
        if (
            qualification.get("state") != ELIGIBLE_QUALIFICATION_STATE
            or qualification.get("paper_execution_authorized") is not True
            or not _false_authority(qualification)
            or not isinstance(receipt_path, str)
            or not receipt_path.startswith("research/receipts/")
            or not _is_sha256(receipt_sha)
            or qualification.get("implementation_sha256") != implementation_sha
            or not _is_sha256(qualification.get("family_validation_report_sha256"))
        ):
            raise CloudCandidateRegistryBlocked("STRATEGY_QUALIFICATION_NOT_AUTHORIZED")
        if (
            model_dependency == "CORE100"
            and registry.get("model_quality") != "PASS"
        ):
            raise CloudCandidateRegistryBlocked("MODEL_QUALITY_GATE_NOT_PASSED")
        registrations[strategy_id] = raw
    if len(registrations) > MAX_CANDIDATES:
        raise CloudCandidateRegistryBlocked("STRATEGY_REGISTRY_EXCEEDS_LIMIT")
    return registrations


def _route_match(
    route: Mapping[str, object],
    *,
    family: str,
    direction: str,
    regime: str,
) -> bool:
    matches = route.get("matches")
    if not isinstance(matches, list):
        return False
    return any(
        isinstance(match, Mapping)
        and match.get("family") == family
        and match.get("direction") == direction
        and match.get("regime_state") == regime
        for match in matches
    )


def select_qualified_candidates(
    market: Mapping[str, object],
    state: Mapping[str, object],
    registry: Mapping[str, object],
    *,
    allowed_base_assets: frozenset[str],
) -> CandidateSelection:
    """Bind ready strategy outputs to same-slot market evidence and route.

    The builder accepts no partial basket: one invalid candidate makes the
    complete selection REVIEW_REQUIRED. It never derives or modifies entry,
    stop, target, strategy, or risk parameters.
    """
    try:
        registrations = validate_strategy_registry(registry)
    except CloudCandidateRegistryBlocked as exc:
        return CandidateSelection("REVIEW_REQUIRED", (), (str(exc),))

    if market.get("schema") != MARKET_SCHEMA:
        return CandidateSelection("REVIEW_REQUIRED", (), ("MARKET_REPORT_SCHEMA_INVALID",))
    raw_specs = market.get("candidate_specs")
    if not isinstance(raw_specs, list):
        return CandidateSelection("REVIEW_REQUIRED", (), ("CANDIDATE_OUTPUTS_INVALID",))
    if not registrations:
        if raw_specs:
            return CandidateSelection(
                "REVIEW_REQUIRED", (), ("EMPTY_REGISTRY_HAS_CANDIDATE_OUTPUTS",),
            )
        return CandidateSelection("NO_CANDIDATES", (), ("NO_ELIGIBLE_STRATEGY",))
    if (
        market.get("provider") != "PIONEX_PUBLIC"
        or market.get("market_status") != "CAPTURED"
        or market.get("context_status") != "AVAILABLE"
    ):
        return CandidateSelection(
            "REVIEW_REQUIRED", (), ("MARKET_OR_CONTEXT_NOT_EXECUTION_READY",),
        )
    as_of_ms = market.get("as_of_ms")
    evidence = market.get("market_evidence")
    routes = market.get("routes")
    if (
        not isinstance(as_of_ms, int) or isinstance(as_of_ms, bool)
        or not isinstance(evidence, Mapping)
        or not isinstance(routes, list)
    ):
        return CandidateSelection("REVIEW_REQUIRED", (), ("MARKET_EVIDENCE_INVALID",))
    if not raw_specs:
        return CandidateSelection(
            "NO_CANDIDATES", (), ("NO_QUALIFIED_STRATEGY_OUTPUT",),
        )
    if len(raw_specs) > MAX_CANDIDATES:
        return CandidateSelection("REVIEW_REQUIRED", (), ("TOO_MANY_CANDIDATES",))

    routes_by_symbol = {
        str(route.get("symbol")): route
        for route in routes if isinstance(route, Mapping)
        and isinstance(route.get("symbol"), str)
    }
    selected: list[Mapping[str, object]] = []
    identities: set[tuple[str, str, int]] = set()
    for raw in raw_specs:
        if not isinstance(raw, Mapping):
            return CandidateSelection("REVIEW_REQUIRED", (), ("CANDIDATE_OUTPUT_INVALID",))
        candidate = raw.get("candidate")
        target_price = raw.get("target_price")
        if not isinstance(candidate, Mapping):
            return CandidateSelection("REVIEW_REQUIRED", (), ("CANDIDATE_PAYLOAD_INVALID",))
        strategy_id = candidate.get("strategy_id")
        registration = registrations.get(strategy_id) if isinstance(strategy_id, str) else None
        symbol = candidate.get("symbol")
        family = candidate.get("strategy_family")
        direction = candidate.get("direction")
        candidate_as_of = candidate.get("as_of_ms")
        regime = candidate.get("regime_state")
        if (
            registration is None
            or not isinstance(symbol, str)
            or not isinstance(family, str)
            or direction != "LONG"
            or not isinstance(candidate_as_of, int)
            or isinstance(candidate_as_of, bool)
            or candidate_as_of != as_of_ms
            or not isinstance(regime, str)
            or registration.get("strategy_family") != family
            or registration.get("provider") != "PIONEX_PUBLIC"
            or symbol not in registration.get("symbols", [])
            or regime not in registration.get("regimes", [])
            or candidate.get("provider") != "PIONEX_PUBLIC"
        ):
            return CandidateSelection("REVIEW_REQUIRED", (), ("CANDIDATE_AUTHORITY_MISMATCH",))
        base_asset = symbol.split("_", 1)[0]
        if base_asset not in allowed_base_assets:
            return CandidateSelection("REVIEW_REQUIRED", (), ("CANDIDATE_ASSET_NOT_GOVERNED",))
        source = evidence.get(symbol)
        route = routes_by_symbol.get(symbol)
        qualification = registration.get("qualification")
        family_report = candidate.get("family_validation_report")
        sizing = candidate.get("position_sizing_plan")
        if (
            not isinstance(source, Mapping)
            or not isinstance(route, Mapping)
            or not isinstance(qualification, Mapping)
            or not isinstance(family_report, Mapping)
            or not isinstance(sizing, Mapping)
        ):
            return CandidateSelection("REVIEW_REQUIRED", (), ("CANDIDATE_LINEAGE_MISSING",))
        if (
            source.get("provider") != "PIONEX_PUBLIC"
            or not _is_sha256(source.get("sha256"))
            or candidate.get("market_evidence_sha256") != source.get("sha256")
            or candidate.get("strategy_route_sha256") != _canonical_sha256(route)
            or candidate.get("qualification_receipt_sha256")
                != qualification.get("receipt_sha256")
            or candidate.get("strategy_implementation_sha256")
                != registration.get("implementation_sha256")
            or family_report.get("schema")
                != "qookey-strategy-family-validation-report-v0.1"
            or family_report.get("family") != family
            or _canonical_sha256(family_report)
                != qualification.get("family_validation_report_sha256")
        ):
            return CandidateSelection("REVIEW_REQUIRED", (), ("CANDIDATE_LINEAGE_MISMATCH",))
        if not _route_match(route, family=family, direction=direction, regime=regime):
            return CandidateSelection("REVIEW_REQUIRED", (), ("STRATEGY_ROUTE_NOT_MATCHED",))
        checkpoint = state.get("checkpoint_report")
        account = checkpoint.get("account_snapshot") if isinstance(checkpoint, Mapping) else None
        equity = account.get("equity_usd") if isinstance(account, Mapping) else None
        entry = candidate.get("entry_price")
        stop = candidate.get("stop_price")
        if (
            not _positive_number(equity)
            or not _positive_number(entry)
            or not _positive_number(stop)
            or not _positive_number(target_price)
            or not float(stop) < float(entry) < float(target_price)
            or sizing.get("status") != "SIZING_READY"
            or sizing.get("direction") != direction
            or sizing.get("equity_usd") != equity
            or sizing.get("entry_price") != entry
            or sizing.get("stop_price") != stop
            or not _positive_number(sizing.get("approved_notional_usd"))
        ):
            return CandidateSelection("REVIEW_REQUIRED", (), ("CANDIDATE_RISK_OUTPUT_INVALID",))
        identity = (symbol, family, candidate_as_of)
        if identity in identities:
            return CandidateSelection("REVIEW_REQUIRED", (), ("CANDIDATE_IDENTITY_DUPLICATE",))
        identities.add(identity)
        selected.append(raw)
    return CandidateSelection("READY", tuple(selected), ("QUALIFIED_CANDIDATES",))
