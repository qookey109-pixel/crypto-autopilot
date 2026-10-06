from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence

DAY_MS = 24 * 60 * 60 * 1000
_HORIZONS = ("1H", "4H", "12H", "24H")


def _record_id(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _verify_record_id(record: Mapping[str, object], id_field: str) -> None:
    identifier = record.get(id_field)
    if not isinstance(identifier, str) or not identifier:
        raise ValueError(f"{id_field} is required")
    body = {key: value for key, value in record.items() if key != id_field}
    if _record_id(body) != identifier:
        raise ValueError(f"{id_field} integrity mismatch")


def _finite_number(value: object, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"{label} must be finite")
    return number


def _direction(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().upper()
    aliases = {
        "LONG": "LONG",
        "LONG_BIAS": "LONG",
        "SHORT": "SHORT",
        "SHORT_BIAS": "SHORT",
    }
    return aliases.get(normalized)


def _qookey_direction(signal: Mapping[str, object]) -> str | None:
    if signal.get("router_result") != "MATCH":
        return None
    candidate = signal.get("qookey_candidate")
    if not isinstance(candidate, Mapping):
        return None
    for field in ("direction", "bias"):
        resolved = _direction(candidate.get(field))
        if resolved is not None:
            return resolved
    return None


def _directional_return(raw_return: float, direction: str | None) -> float | None:
    if direction == "LONG":
        return raw_return
    if direction == "SHORT":
        return -raw_return
    return None


def _mean(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _expectancy(values: Sequence[float]) -> dict[str, object]:
    if not values:
        return {
            "sample_count": 0,
            "win_rate": None,
            "average_win": None,
            "average_loss": None,
            "expectancy": None,
        }
    wins = [value for value in values if value > 0.0]
    losses = [value for value in values if value <= 0.0]
    win_rate = len(wins) / len(values)
    loss_rate = len(losses) / len(values)
    average_win = _mean(wins)
    average_loss = _mean([-value for value in losses])
    expectancy = (
        win_rate * (average_win or 0.0)
        - loss_rate * (average_loss or 0.0)
    )
    return {
        "sample_count": len(values),
        "win_rate": win_rate,
        "average_win": average_win,
        "average_loss": average_loss,
        "expectancy": expectancy,
    }


def aggregate_shadow_records(
    records: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Aggregate frozen prospective shadow records without promotion semantics."""

    seen_signal_ids: set[str] = set()
    as_of_values: list[int] = []
    qookey_latencies: list[float] = []
    comparison_latencies: list[float] = []
    no_trade_counts = {"AVOIDED_LOSS": 0, "MISSED_GAIN": 0, "UNRESOLVED": 0}

    horizon_values: dict[str, dict[str, list[float]]] = {
        label: {
            "raw_return": [],
            "mfe": [],
            "mae": [],
            "qookey_directional_return": [],
            "comparison_directional_return": [],
        }
        for label in _HORIZONS
    }

    for index, pair in enumerate(records):
        if not isinstance(pair, Mapping):
            raise ValueError(f"record[{index}] must be an object")
        signal = pair.get("signal")
        outcome = pair.get("outcome")
        if not isinstance(signal, Mapping) or not isinstance(outcome, Mapping):
            raise ValueError(f"record[{index}] requires signal and outcome objects")
        if signal.get("schema") != "qookey-prospective-shadow-signal-v0.1":
            raise ValueError("unsupported shadow signal schema")
        if outcome.get("schema") != "qookey-prospective-shadow-outcome-v0.1":
            raise ValueError("unsupported shadow outcome schema")
        _verify_record_id(signal, "signal_id")
        _verify_record_id(outcome, "outcome_id")

        signal_id = str(signal["signal_id"])
        if signal_id in seen_signal_ids:
            raise ValueError("duplicate shadow signal_id")
        seen_signal_ids.add(signal_id)
        if outcome.get("signal_id") != signal_id:
            raise ValueError("shadow outcome belongs to another signal")
        if outcome.get("symbol") != signal.get("symbol"):
            raise ValueError("shadow signal/outcome symbol mismatch")

        as_of_ms = signal.get("as_of_ms")
        if not isinstance(as_of_ms, int) or isinstance(as_of_ms, bool) or as_of_ms < 0:
            raise ValueError("signal.as_of_ms must be a non-negative integer")
        as_of_values.append(as_of_ms)

        qookey_latency = signal.get("qookey_latency_ms")
        if qookey_latency is not None:
            qookey_latencies.append(_finite_number(qookey_latency, "qookey_latency_ms"))
        comparison_latency = signal.get("comparison_latency_ms")
        if comparison_latency is not None:
            comparison_latencies.append(
                _finite_number(comparison_latency, "comparison_latency_ms")
            )

        qookey_direction = _qookey_direction(signal)
        comparison_direction = _direction(signal.get("comparison_direction"))
        horizons = outcome.get("horizons")
        if not isinstance(horizons, Mapping):
            raise ValueError("shadow outcome horizons are required")

        for label in _HORIZONS:
            row = horizons.get(label)
            if not isinstance(row, Mapping) or row.get("status") != "OBSERVED":
                continue
            raw_return = _finite_number(row.get("return"), f"{label}.return")
            mfe = _finite_number(row.get("mfe"), f"{label}.mfe")
            mae = _finite_number(row.get("mae"), f"{label}.mae")
            horizon_values[label]["raw_return"].append(raw_return)
            horizon_values[label]["mfe"].append(mfe)
            horizon_values[label]["mae"].append(mae)

            qookey_value = _directional_return(raw_return, qookey_direction)
            if qookey_value is not None:
                horizon_values[label]["qookey_directional_return"].append(qookey_value)
            comparison_value = _directional_return(raw_return, comparison_direction)
            if comparison_value is not None:
                horizon_values[label]["comparison_directional_return"].append(
                    comparison_value
                )

        if signal.get("router_result") == "NO_TRADE":
            quality = outcome.get("no_trade_quality_24h")
            if quality in {"AVOIDED_LOSS", "MISSED_GAIN"}:
                no_trade_counts[str(quality)] += 1
            else:
                no_trade_counts["UNRESOLVED"] += 1

    span_days = 0.0
    if len(as_of_values) >= 2:
        span_days = (max(as_of_values) - min(as_of_values)) / DAY_MS
    if not as_of_values:
        collection_status = "NO_RECORDS"
    elif span_days < 30.0:
        collection_status = "COLLECTING"
    elif span_days <= 90.0:
        collection_status = "REVIEW_WINDOW"
    else:
        collection_status = "EXTENDED_WINDOW"

    horizon_summary: dict[str, object] = {}
    for label, values in horizon_values.items():
        horizon_summary[label] = {
            "observed_count": len(values["raw_return"]),
            "mean_raw_return": _mean(values["raw_return"]),
            "mean_mfe": _mean(values["mfe"]),
            "mean_mae": _mean(values["mae"]),
            "qookey": _expectancy(values["qookey_directional_return"]),
            "comparison": _expectancy(values["comparison_directional_return"]),
        }

    return {
        "schema": "qookey-prospective-shadow-analysis-v0.1",
        "record_count": len(records),
        "prospective_span_days": span_days,
        "collection_status": collection_status,
        "horizons": horizon_summary,
        "latency": {
            "qookey_observed_count": len(qookey_latencies),
            "qookey_mean_ms": _mean(qookey_latencies),
            "comparison_observed_count": len(comparison_latencies),
            "comparison_mean_ms": _mean(comparison_latencies),
        },
        "no_trade_quality_24h": no_trade_counts,
        "interpretation": {
            "automatic_winner_selection": False,
            "automatic_threshold_change": False,
            "automatic_router_change": False,
            "automatic_model_promotion": False,
            "requires_cross_asset_out_of_sample_review": True,
        },
        "authority": {
            "research_analysis_only": True,
            "candidate_reranking_authorized": False,
            "strategy_router_change_authorized": False,
            "risk_change_authorized": False,
            "paper_submission_authorized": False,
            "live_trading_authorized": False,
        },
    }
