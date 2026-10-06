from __future__ import annotations

from collections.abc import Mapping
from typing import Final

BOUNDED_SCHEMA: Final[dict[str, tuple[str, ...]]] = {
    "market_regime": ("TREND", "RANGE", "BREAKOUT", "REVERSAL"),
    "direction": ("LONG", "SHORT", "NEUTRAL"),
    "flow_state": ("ACCUMULATION", "DISTRIBUTION", "NEUTRAL"),
    "event_importance": ("NOISE", "WATCH", "IMPORTANT", "CRITICAL"),
    "risk_regime": ("LOW", "NORMAL", "HIGH", "EXTREME"),
    "strategy_hint": ("TREND", "MOMENTUM", "MEAN_REVERSION", "NONE"),
}


def _finite_probability(value: object, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"{label} must be finite")
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"{label} must be within [0, 1]")
    return number


def build_bounded_decision_record(
    *,
    model_name: str,
    as_of_ms: int,
    probabilities: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    """Validate an offline bounded decision-model result.

    V0.1 performs no model/provider call. Probabilities are model classification
    outputs, not calibrated trading probabilities and not execution authority.
    """

    if not isinstance(model_name, str) or not model_name.strip():
        raise ValueError("model_name is required")
    if not isinstance(as_of_ms, int) or isinstance(as_of_ms, bool) or as_of_ms < 0:
        raise ValueError("as_of_ms must be a non-negative integer")
    if not isinstance(probabilities, Mapping):
        raise ValueError("probabilities must be an object")
    if set(probabilities) != set(BOUNDED_SCHEMA):
        raise ValueError("bounded decision axes must exactly match V0.1 schema")

    axes: dict[str, object] = {}
    for axis, labels in BOUNDED_SCHEMA.items():
        raw = probabilities[axis]
        if not isinstance(raw, Mapping) or set(raw) != set(labels):
            raise ValueError(f"{axis} labels must exactly match V0.1 schema")
        normalized = {
            label: _finite_probability(raw[label], f"{axis}.{label}") for label in labels
        }
        total = sum(normalized.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"{axis} probabilities must sum to 1")
        top = max(labels, key=lambda label: (normalized[label], -labels.index(label)))
        axes[axis] = {
            "selected": top,
            "probabilities": normalized,
        }

    return {
        "schema": "qookey-bounded-decision-record-v0.1",
        "model_name": model_name.strip(),
        "as_of_ms": as_of_ms,
        "axes": axes,
        "semantics": {
            "classification_probability_only": True,
            "calibrated_trading_probability": False,
        },
        "authority": {
            "offline_validation_only": True,
            "provider_call_authorized": False,
            "candidate_selection_authorized": False,
            "strategy_selection_authorized": False,
            "position_sizing_authorized": False,
            "portfolio_admission_authorized": False,
            "execution_authorized": False,
            "live_trading_authorized": False,
        },
    }
