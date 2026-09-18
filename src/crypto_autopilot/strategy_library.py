from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StrategyFamilySpec:
    """Governed metadata for one reusable strategy family.

    A family registry entry is architecture metadata only. It does not claim
    statistical edge and does not authorize position sizing or execution.
    """

    family: str
    category: str
    attention_profiles: tuple[str, ...]
    directions: tuple[str, ...]
    requires_market_structure: bool
    validation_state: str
    reusable_scope: str
    generalization_required: bool
    strategy_edge_claimed: bool = False
    position_sizing_authorized: bool = False
    paper_execution_authorized: bool = False
    live_execution_authorized: bool = False


STRATEGY_LIBRARY_V0_1: tuple[StrategyFamilySpec, ...] = (
    StrategyFamilySpec(
        family="TREND_FOLLOWING",
        category="DIRECTIONAL",
        attention_profiles=("DIRECTIONAL",),
        directions=("LONG", "SHORT"),
        requires_market_structure=True,
        validation_state="ROUTING_RULE_PREPARED",
        reusable_scope="MULTI_ASSET_RESEARCH",
        generalization_required=True,
    ),
    StrategyFamilySpec(
        family="BREAKOUT",
        category="STRUCTURE",
        attention_profiles=("DIRECTIONAL",),
        directions=("LONG", "SHORT"),
        requires_market_structure=True,
        validation_state="ROUTING_RULE_PREPARED",
        reusable_scope="MULTI_ASSET_RESEARCH",
        generalization_required=True,
    ),
    StrategyFamilySpec(
        family="MOMENTUM",
        category="DIRECTIONAL",
        attention_profiles=("DIRECTIONAL",),
        directions=("LONG", "SHORT"),
        requires_market_structure=False,
        validation_state="ROUTING_RULE_PREPARED",
        reusable_scope="MULTI_ASSET_RESEARCH",
        generalization_required=True,
    ),
    StrategyFamilySpec(
        family="MEAN_REVERSION",
        category="RANGE",
        attention_profiles=("RANGE_EXTREMITY",),
        directions=("LONG", "SHORT"),
        requires_market_structure=True,
        validation_state="ROUTING_RULE_PREPARED",
        reusable_scope="MULTI_ASSET_RESEARCH",
        generalization_required=True,
    ),
    StrategyFamilySpec(
        family="HIGH_VOLATILITY_TREND",
        category="VOLATILITY_DIRECTIONAL",
        attention_profiles=("DIRECTIONAL",),
        directions=("LONG", "SHORT"),
        requires_market_structure=True,
        validation_state="ROUTING_RULE_PREPARED",
        reusable_scope="MULTI_ASSET_RESEARCH",
        generalization_required=True,
    ),
    StrategyFamilySpec(
        family="LOW_VOLATILITY_RANGE",
        category="VOLATILITY_RANGE",
        attention_profiles=("RANGE_EXTREMITY",),
        directions=("LONG", "SHORT"),
        requires_market_structure=True,
        validation_state="ROUTING_RULE_PREPARED",
        reusable_scope="MULTI_ASSET_RESEARCH",
        generalization_required=True,
    ),
)


def strategy_family_ids() -> tuple[str, ...]:
    return tuple(spec.family for spec in STRATEGY_LIBRARY_V0_1)


def strategy_family_registry() -> dict[str, StrategyFamilySpec]:
    return {spec.family: spec for spec in STRATEGY_LIBRARY_V0_1}


def get_strategy_family(family: str) -> StrategyFamilySpec:
    registry = strategy_family_registry()
    try:
        return registry[family]
    except KeyError as exc:
        raise ValueError(f"unregistered strategy family: {family}") from exc


def validate_strategy_library() -> None:
    """Fail closed if the V0.1 registry becomes internally inconsistent."""

    families = strategy_family_ids()
    if len(set(families)) != len(families):
        raise ValueError("strategy family identifiers must be unique")
    for spec in STRATEGY_LIBRARY_V0_1:
        if not spec.family:
            raise ValueError("strategy family identifier cannot be empty")
        if not spec.attention_profiles:
            raise ValueError(f"{spec.family} must declare attention profiles")
        if not set(spec.attention_profiles).issubset({"DIRECTIONAL", "RANGE_EXTREMITY"}):
            raise ValueError(f"{spec.family} declares an unsupported attention profile")
        if not spec.directions or not set(spec.directions).issubset({"LONG", "SHORT"}):
            raise ValueError(f"{spec.family} declares unsupported directions")
        if spec.strategy_edge_claimed:
            raise ValueError(f"{spec.family} cannot claim strategy edge in V0.1")
        if (
            spec.position_sizing_authorized
            or spec.paper_execution_authorized
            or spec.live_execution_authorized
        ):
            raise ValueError(f"{spec.family} cannot grant execution authority in V0.1")


validate_strategy_library()
