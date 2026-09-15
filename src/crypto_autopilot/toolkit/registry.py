from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    category: str
    description: str
    side_effects: str
    requires_network: bool
    requires_secrets: bool


_TOOL_SPECS = (
    ToolSpec(
        name="get_indicators",
        category="technical",
        description="Build deterministic EMA/RSI/MACD/Bollinger/ATR snapshots from supplied candles.",
        side_effects="none",
        requires_network=False,
        requires_secrets=False,
    ),
    ToolSpec(
        name="evaluate_strategy",
        category="strategy",
        description="Run the existing deterministic V0.1 research strategy gate.",
        side_effects="none",
        requires_network=False,
        requires_secrets=False,
    ),
    ToolSpec(
        name="size_long_trade",
        category="risk",
        description="Calculate paper-only LONG risk sizing under the existing risk caps.",
        side_effects="none",
        requires_network=False,
        requires_secrets=False,
    ),
    ToolSpec(
        name="run_paper_backtest",
        category="backtest",
        description="Run the existing deterministic paper-only LONG backtest engine.",
        side_effects="none",
        requires_network=False,
        requires_secrets=False,
    ),
)


SAFETY_BOUNDARY = {
    "provider_access_authorized": False,
    "r2_access_authorized": False,
    "holdout_access_authorized": False,
    "source_switch_authorized": False,
    "synthetic_candles_authorized": False,
    "interpolation_authorized": False,
    "automatic_strategy_mutation_authorized": False,
    "automatic_model_promotion_authorized": False,
    "formal_trade_plan_authorized": False,
    "real_money_order_authorized": False,
    "live_trading_authorized": False,
}


def list_capabilities() -> dict[str, object]:
    return {
        "schema": "qookey-crypto-toolkit-capabilities-v0.1",
        "status": "RESEARCH_ONLY",
        "tools": [asdict(spec) for spec in _TOOL_SPECS],
        "safety_boundary": dict(SAFETY_BOUNDARY),
    }
