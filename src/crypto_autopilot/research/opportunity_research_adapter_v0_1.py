from __future__ import annotations

from collections.abc import Mapping


def attach_research_sidecars(
    *,
    opportunity: Mapping[str, object],
    market_event_radar: Mapping[str, object] | None = None,
    technical_confluence: Mapping[str, object] | None = None,
    bounded_decision: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Attach research evidence without rewriting Daily Opportunity Engine V0.1."""

    if not isinstance(opportunity, Mapping):
        raise ValueError("opportunity must be an object")
    symbol = opportunity.get("symbol")
    score = opportunity.get("score")
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("opportunity.symbol is required")
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        raise ValueError("opportunity.score must be numeric")
    clean_symbol = symbol.strip().upper()

    sidecars: dict[str, object] = {}
    for name, payload in (
        ("market_event_radar", market_event_radar),
        ("technical_confluence", technical_confluence),
        ("bounded_decision", bounded_decision),
    ):
        if payload is None:
            continue
        if not isinstance(payload, Mapping):
            raise ValueError(f"{name} must be an object")
        sidecar_symbol = payload.get("symbol")
        if sidecar_symbol is not None and str(sidecar_symbol).strip().upper() != clean_symbol:
            raise ValueError(f"{name} belongs to another symbol")
        sidecars[name] = dict(payload)

    original = dict(opportunity)
    return {
        "schema": "qookey-opportunity-research-adapter-v0.1",
        "symbol": clean_symbol,
        "opportunity_v0_1": original,
        "original_score": float(score),
        "research_sidecars": sidecars,
        "invariants": {
            "opportunity_score_unchanged": True,
            "v0_1_thresholds_unchanged": True,
            "router_thresholds_unchanged": True,
        },
        "authority": {
            "research_evidence_only": True,
            "candidate_reranking_authorized": False,
            "strategy_routing_authorized": False,
            "risk_change_authorized": False,
            "portfolio_admission_authorized": False,
            "paper_submission_authorized": False,
            "live_trading_authorized": False,
        },
    }
