from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence

from crypto_autopilot.historical import INTERVAL_MS, audit_candles
from crypto_autopilot.models import Candle
from crypto_autopilot.technical import TechnicalDataError

_HORIZONS_MS = {
    "1H": 60 * 60 * 1000,
    "4H": 4 * 60 * 60 * 1000,
    "12H": 12 * 60 * 60 * 1000,
    "24H": 24 * 60 * 60 * 1000,
}


def _clean_symbol(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("symbol is required")
    return value.strip().upper()


def _finite_positive(value: object, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")) or number <= 0:
        raise ValueError(f"{label} must be finite and positive")
    return number


def _non_negative_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _record_id(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_shadow_signal_record(
    *,
    symbol: str,
    as_of_ms: int,
    reference_price: float,
    qookey_candidate: Mapping[str, object],
    router_result: str,
    qookey_detected_at_ms: int | None = None,
    event_observed_at_ms: int | None = None,
    comparison_signal: str | None = None,
    comparison_direction: str | None = None,
    comparison_detected_at_ms: int | None = None,
) -> dict[str, object]:
    """Freeze a prospective signal snapshot before any future outcome is known."""

    clean_symbol = _clean_symbol(symbol)
    decision_time = _non_negative_int(as_of_ms, "as_of_ms")
    price = _finite_positive(reference_price, "reference_price")
    if not isinstance(qookey_candidate, Mapping):
        raise ValueError("qookey_candidate must be an object")
    if not isinstance(router_result, str) or router_result not in {"MATCH", "NO_TRADE"}:
        raise ValueError("router_result must be MATCH or NO_TRADE")

    detected = decision_time if qookey_detected_at_ms is None else _non_negative_int(
        qookey_detected_at_ms,
        "qookey_detected_at_ms",
    )
    if detected > decision_time:
        raise ValueError("qookey detection cannot be in the future")

    event_time = None
    qookey_latency_ms = None
    if event_observed_at_ms is not None:
        event_time = _non_negative_int(event_observed_at_ms, "event_observed_at_ms")
        if event_time > detected:
            raise ValueError("event cannot be observed after qookey detection")
        qookey_latency_ms = detected - event_time

    comparison_latency_ms = None
    if comparison_detected_at_ms is not None:
        comparison_detected_at_ms = _non_negative_int(
            comparison_detected_at_ms,
            "comparison_detected_at_ms",
        )
        if comparison_detected_at_ms > decision_time:
            raise ValueError("comparison detection cannot be in the future")
        if event_time is not None:
            if comparison_detected_at_ms < event_time:
                raise ValueError("comparison detection cannot predate observed event")
            comparison_latency_ms = comparison_detected_at_ms - event_time

    direction = None
    if comparison_direction is not None:
        direction = comparison_direction.strip().upper()
        if direction not in {"LONG", "SHORT", "NEUTRAL"}:
            raise ValueError("comparison_direction must be LONG, SHORT or NEUTRAL")

    body = {
        "schema": "qookey-prospective-shadow-signal-v0.1",
        "symbol": clean_symbol,
        "as_of_ms": decision_time,
        "reference_price": price,
        "qookey_candidate": dict(qookey_candidate),
        "router_result": router_result,
        "qookey_detected_at_ms": detected,
        "event_observed_at_ms": event_time,
        "qookey_latency_ms": qookey_latency_ms,
        "comparison_signal": comparison_signal,
        "comparison_direction": direction,
        "comparison_detected_at_ms": comparison_detected_at_ms,
        "comparison_latency_ms": comparison_latency_ms,
        "horizons_ms": dict(_HORIZONS_MS),
        "authority": {
            "prospective_research_only": True,
            "candidate_reranking_authorized": False,
            "strategy_change_authorized": False,
            "risk_change_authorized": False,
            "execution_authorized": False,
            "live_trading_authorized": False,
        },
    }
    return {**body, "signal_id": _record_id(body)}


def evaluate_shadow_outcomes(
    *,
    signal: Mapping[str, object],
    candles: Sequence[Candle],
    interval: str,
    evaluated_at_ms: int,
) -> dict[str, object]:
    """Evaluate fixed future windows without modifying the frozen signal record."""

    if signal.get("schema") != "qookey-prospective-shadow-signal-v0.1":
        raise ValueError("unsupported shadow signal schema")
    if interval not in INTERVAL_MS:
        raise ValueError(f"unsupported outcome interval: {interval}")
    source = tuple(candles)
    audit = audit_candles(source, interval)
    if not audit.ok:
        raise TechnicalDataError(f"Candle audit failed: {audit}")

    as_of_ms = _non_negative_int(signal.get("as_of_ms"), "signal.as_of_ms")
    reference_price = _finite_positive(signal.get("reference_price"), "signal.reference_price")
    evaluated_at = _non_negative_int(evaluated_at_ms, "evaluated_at_ms")
    if evaluated_at < as_of_ms:
        raise ValueError("evaluation cannot predate the signal")

    step_ms = INTERVAL_MS[interval]
    horizons: dict[str, object] = {}
    for label, horizon_ms in _HORIZONS_MS.items():
        target_ms = as_of_ms + horizon_ms
        if evaluated_at < target_ms:
            horizons[label] = {"status": "NOT_YET_AVAILABLE", "target_ms": target_ms}
            continue

        available = [
            candle
            for candle in source
            if as_of_ms < candle.time_ms + step_ms <= target_ms
        ]
        if not available or available[-1].time_ms + step_ms != target_ms:
            horizons[label] = {
                "status": "MISSING_EXACT_HORIZON",
                "target_ms": target_ms,
            }
            continue

        terminal = available[-1]
        raw_return = terminal.close / reference_price - 1.0
        mfe = max(item.high for item in available) / reference_price - 1.0
        mae = min(item.low for item in available) / reference_price - 1.0
        horizons[label] = {
            "status": "OBSERVED",
            "target_ms": target_ms,
            "terminal_close": terminal.close,
            "return": raw_return,
            "mfe": mfe,
            "mae": mae,
        }

    no_trade_quality = None
    if signal.get("router_result") == "NO_TRADE":
        direction = signal.get("comparison_direction")
        terminal = horizons["24H"]
        if (
            isinstance(terminal, Mapping)
            and terminal.get("status") == "OBSERVED"
            and direction in {"LONG", "SHORT"}
        ):
            raw_return = float(terminal["return"])
            directional_return = raw_return if direction == "LONG" else -raw_return
            no_trade_quality = (
                "AVOIDED_LOSS" if directional_return <= 0.0 else "MISSED_GAIN"
            )

    body = {
        "schema": "qookey-prospective-shadow-outcome-v0.1",
        "signal_id": signal.get("signal_id"),
        "symbol": signal.get("symbol"),
        "evaluated_at_ms": evaluated_at,
        "interval": interval,
        "horizons": horizons,
        "no_trade_quality_24h": no_trade_quality,
        "authority": {
            "research_evaluation_only": True,
            "production_score_change_authorized": False,
            "router_change_authorized": False,
            "execution_authorized": False,
            "live_trading_authorized": False,
        },
    }
    return {**body, "outcome_id": _record_id(body)}
