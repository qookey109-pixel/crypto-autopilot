from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Final

_TIMEFRAMES: Final[frozenset[str]] = frozenset({"1D", "4H", "1H", "15M", "5M"})
_STRUCTURE_STATES: Final[frozenset[str]] = frozenset({"UP", "DOWN", "RANGE", "INDETERMINATE"})
_LIQUIDITY_EVENTS: Final[frozenset[str]] = frozenset(
    {"HIGH_SWEEP_RECLAIM", "LOW_SWEEP_RECLAIM", "NONE"}
)
_BIASES: Final[frozenset[str]] = frozenset({"BULLISH", "BEARISH", "NONE"})


def _clean_symbol(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("symbol is required")
    symbol = value.strip().upper()
    if any(character.isspace() for character in symbol):
        raise ValueError("symbol cannot contain whitespace")
    return symbol


def _non_negative_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _enum(value: object, label: str, allowed: frozenset[str]) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    normalized = value.strip().upper()
    if normalized not in allowed:
        raise ValueError(f"unsupported {label}: {value}")
    return normalized


def build_technical_confluence_snapshot(
    *,
    symbol: str,
    as_of_ms: int,
    timeframes: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Aggregate already-deterministic structure/location/momentum evidence.

    The function intentionally does not infer an entry, score, stop, position size,
    or strategy route. It only preserves causal evidence and descriptive confluence.
    """

    clean_symbol = _clean_symbol(symbol)
    decision_time = _non_negative_int(as_of_ms, "as_of_ms")
    if not isinstance(timeframes, Sequence) or isinstance(timeframes, (str, bytes)):
        raise ValueError("timeframes must be an array")
    if not timeframes:
        raise ValueError("at least one timeframe row is required")

    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    bullish = 0
    bearish = 0

    for raw in timeframes:
        if not isinstance(raw, Mapping):
            raise ValueError("timeframe row must be an object")
        timeframe = _enum(raw.get("timeframe"), "timeframe", _TIMEFRAMES)
        if timeframe in seen:
            raise ValueError(f"duplicate timeframe: {timeframe}")
        seen.add(timeframe)

        available_at_ms = _non_negative_int(raw.get("available_at_ms"), "available_at_ms")
        if available_at_ms > decision_time:
            raise ValueError("future technical evidence is not causally available")

        structure = _enum(raw.get("structure_state"), "structure_state", _STRUCTURE_STATES)
        liquidity = _enum(raw.get("liquidity_event"), "liquidity_event", _LIQUIDITY_EVENTS)
        fvg = _enum(raw.get("fvg_bias"), "fvg_bias", _BIASES)
        order_block = _enum(raw.get("order_block_bias"), "order_block_bias", _BIASES)
        harmonic = _enum(raw.get("harmonic_prz"), "harmonic_prz", _BIASES)
        macd = _enum(raw.get("macd_divergence"), "macd_divergence", _BIASES)

        evidence = (
            "BULLISH" if structure == "UP" else "BEARISH" if structure == "DOWN" else "NONE",
            "BEARISH" if liquidity == "HIGH_SWEEP_RECLAIM" else (
                "BULLISH" if liquidity == "LOW_SWEEP_RECLAIM" else "NONE"
            ),
            fvg,
            order_block,
            harmonic,
            macd,
        )
        bullish_count = sum(value == "BULLISH" for value in evidence)
        bearish_count = sum(value == "BEARISH" for value in evidence)
        bullish += bullish_count
        bearish += bearish_count

        rows.append(
            {
                "timeframe": timeframe,
                "available_at_ms": available_at_ms,
                "structure_state": structure,
                "liquidity_event": liquidity,
                "fvg_bias": fvg,
                "order_block_bias": order_block,
                "harmonic_prz": harmonic,
                "macd_divergence": macd,
                "bullish_evidence_count": bullish_count,
                "bearish_evidence_count": bearish_count,
            }
        )

    confluence = "NEUTRAL"
    if bullish > bearish:
        confluence = "BULLISH"
    elif bearish > bullish:
        confluence = "BEARISH"

    return {
        "schema": "qookey-technical-confluence-snapshot-v0.1",
        "symbol": clean_symbol,
        "as_of_ms": decision_time,
        "timeframes": rows,
        "aggregate": {
            "bullish_evidence_count": bullish,
            "bearish_evidence_count": bearish,
            "descriptive_confluence": confluence,
        },
        "authority": {
            "research_only": True,
            "entry_signal_authorized": False,
            "opportunity_score_change_authorized": False,
            "strategy_router_change_authorized": False,
            "risk_change_authorized": False,
            "automatic_execution_authorized": False,
            "live_trading_authorized": False,
        },
    }
