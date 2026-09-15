from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

from crypto_autopilot.historical import audit_candles
from crypto_autopilot.models import Candle

from .core import run_paper_backtest
from .registry import SAFETY_BOUNDARY


_INTERVAL_ALIASES = {
    "15m": "15M",
    "15M": "15M",
    "1h": "60M",
    "1H": "60M",
    "60m": "60M",
    "60M": "60M",
    "4h": "4H",
    "4H": "4H",
    "8h": "8H",
    "8H": "8H",
    "1d": "1D",
    "1D": "1D",
    "1w": "1W",
    "1W": "1W",
}
_MAX_STRESS_SCENARIOS = 64
_ALLOWED_STRESS_OVERRIDES = {
    "taker_fee_bps",
    "slippage_bps",
    "conservative_same_bar_exit",
}


def _candle(item: dict[str, Any]) -> Candle:
    return Candle(
        time_ms=int(item["time_ms"]),
        open=float(item["open"]),
        high=float(item["high"]),
        low=float(item["low"]),
        close=float(item["close"]),
        volume=float(item["volume"]),
    )


def _interval(value: str) -> str:
    requested = value.strip()
    try:
        return _INTERVAL_ALIASES[requested]
    except KeyError as exc:
        supported = ", ".join(sorted(_INTERVAL_ALIASES))
        raise ValueError(f"unsupported toolkit interval {value!r}; expected one of: {supported}") from exc


def _finite_number(value: Any, *, name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def validate_candles(candles: list[dict[str, Any]], *, interval: str) -> dict[str, Any]:
    """Audit supplied OHLCV without filling, repairing, or interpolating any gap."""
    prepared = tuple(_candle(item) for item in candles)
    canonical_interval = _interval(interval)
    audit = audit_candles(prepared, canonical_interval)
    missing_bars = sum(gap.missing_bars for gap in audit.gaps)
    return {
        "schema": "qookey-crypto-toolkit-candle-validation-v0.2",
        "status": "PASS" if audit.ok else "FAIL",
        "requested_interval": interval,
        "canonical_interval": canonical_interval,
        "candle_count": audit.count,
        "duplicate_timestamps": list(audit.duplicate_timestamps),
        "duplicate_count": len(audit.duplicate_timestamps),
        "out_of_order_pairs": [list(pair) for pair in audit.out_of_order_pairs],
        "out_of_order_count": len(audit.out_of_order_pairs),
        "gaps": [
            {
                "previous_time_ms": gap.previous_time_ms,
                "next_time_ms": gap.next_time_ms,
                "missing_bars": gap.missing_bars,
            }
            for gap in audit.gaps
        ],
        "gap_count": len(audit.gaps),
        "missing_bars": missing_bars,
        "misaligned_timestamps": list(audit.misaligned_timestamps),
        "misaligned_count": len(audit.misaligned_timestamps),
        "invalid_candle_timestamps": list(audit.invalid_candle_timestamps),
        "invalid_candle_count": len(audit.invalid_candle_timestamps),
        "repair_performed": False,
        "interpolation_performed": False,
        "synthetic_candles_emitted": False,
        "authority": dict(SAFETY_BOUNDARY),
    }


def stress_paper_backtest(payload: dict[str, Any]) -> dict[str, Any]:
    """Re-run one paper backtest under bounded fee/slippage/execution scenarios."""
    backtest = payload.get("backtest")
    scenarios = payload.get("scenarios")
    if not isinstance(backtest, dict):
        raise ValueError("stress input requires a backtest object")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("stress input requires a non-empty scenarios list")
    if len(scenarios) > _MAX_STRESS_SCENARIOS:
        raise ValueError(f"stress scenario count exceeds {_MAX_STRESS_SCENARIOS}")

    names: set[str] = set()
    outputs: list[dict[str, Any]] = []
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise ValueError("each stress scenario must be an object")
        name = str(scenario.get("name") or "").strip()
        if not name:
            raise ValueError("each stress scenario requires a non-empty name")
        if name in names:
            raise ValueError(f"duplicate stress scenario name: {name}")
        names.add(name)

        overrides = set(scenario) - {"name"}
        unsupported = overrides - _ALLOWED_STRESS_OVERRIDES
        if unsupported:
            raise ValueError(
                "unsupported stress override(s): " + ", ".join(sorted(unsupported))
            )

        candidate = deepcopy(backtest)
        config = candidate.setdefault("config", {})
        if not isinstance(config, dict):
            raise ValueError("backtest config must be an object")
        if "taker_fee_bps" in scenario:
            fee = _finite_number(scenario["taker_fee_bps"], name="taker_fee_bps")
            if fee < 0:
                raise ValueError("taker_fee_bps cannot be negative")
            config["taker_fee_bps"] = fee
        if "slippage_bps" in scenario:
            slippage = _finite_number(scenario["slippage_bps"], name="slippage_bps")
            if slippage < 0:
                raise ValueError("slippage_bps cannot be negative")
            config["slippage_bps"] = slippage
        if "conservative_same_bar_exit" in scenario:
            value = scenario["conservative_same_bar_exit"]
            if type(value) is not bool:
                raise ValueError("conservative_same_bar_exit must be boolean")
            config["conservative_same_bar_exit"] = value

        result = run_paper_backtest(candidate)
        outputs.append(
            {
                "name": name,
                "overrides": {key: scenario[key] for key in sorted(overrides)},
                "metrics": result["result"]["metrics"],
                "final_equity_usd": result["result"]["final_equity_usd"],
                "rejected_plan_count": len(result["result"]["rejected_plans"]),
            }
        )

    highest_return = max(outputs, key=lambda item: item["metrics"]["return_pct"])
    lowest_return = min(outputs, key=lambda item: item["metrics"]["return_pct"])
    lowest_drawdown = min(outputs, key=lambda item: item["metrics"]["max_drawdown_pct"])
    highest_drawdown = max(outputs, key=lambda item: item["metrics"]["max_drawdown_pct"])
    return {
        "schema": "qookey-crypto-toolkit-stress-backtest-v0.2",
        "status": "PASS",
        "mode": "PAPER_ONLY",
        "scenario_count": len(outputs),
        "scenarios": outputs,
        "summary": {
            "highest_return_scenario": highest_return["name"],
            "lowest_return_scenario": lowest_return["name"],
            "lowest_drawdown_scenario": lowest_drawdown["name"],
            "highest_drawdown_scenario": highest_drawdown["name"],
            "return_range_pct": [
                lowest_return["metrics"]["return_pct"],
                highest_return["metrics"]["return_pct"],
            ],
            "drawdown_range_pct": [
                lowest_drawdown["metrics"]["max_drawdown_pct"],
                highest_drawdown["metrics"]["max_drawdown_pct"],
            ],
        },
        "automatic_strategy_mutation_performed": False,
        "authority": dict(SAFETY_BOUNDARY),
    }


def _paper_metrics(entry: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    label = str(entry.get("label") or "").strip()
    if not label:
        raise ValueError("each comparison result requires a non-empty label")
    result = entry.get("result")
    if not isinstance(result, dict):
        raise ValueError(f"comparison result {label!r} requires a result object")
    if result.get("schema") != "qookey-crypto-toolkit-paper-backtest-v0.1":
        raise ValueError(f"comparison result {label!r} has unsupported schema")
    if result.get("mode") != "PAPER_ONLY":
        raise ValueError(f"comparison result {label!r} is not PAPER_ONLY")
    authority = result.get("authority")
    if not isinstance(authority, dict) or any(authority.values()):
        raise ValueError(f"comparison result {label!r} has unexpected authority")
    nested = result.get("result")
    if not isinstance(nested, dict) or not isinstance(nested.get("metrics"), dict):
        raise ValueError(f"comparison result {label!r} is missing metrics")
    return label, nested["metrics"]


def compare_backtests(payload: dict[str, Any]) -> dict[str, Any]:
    """Compare already-produced research backtests without selecting a live strategy."""
    entries = payload.get("results")
    if not isinstance(entries, list) or len(entries) < 2:
        raise ValueError("comparison requires at least two results")
    if len(entries) > 64:
        raise ValueError("comparison supports at most 64 results")

    parsed = [_paper_metrics(entry) for entry in entries]
    labels = [label for label, _metrics in parsed]
    if len(set(labels)) != len(labels):
        raise ValueError("comparison labels must be unique")

    baseline_label, baseline = parsed[0]
    rows: list[dict[str, Any]] = []
    for label, metrics in parsed:
        rows.append(
            {
                "label": label,
                "metrics": metrics,
                "delta_vs_baseline": {
                    "return_pct": round(metrics["return_pct"] - baseline["return_pct"], 8),
                    "max_drawdown_pct": round(
                        metrics["max_drawdown_pct"] - baseline["max_drawdown_pct"], 8
                    ),
                    "win_rate": round(metrics["win_rate"] - baseline["win_rate"], 8),
                    "trade_count": metrics["trade_count"] - baseline["trade_count"],
                },
            }
        )

    highest_return = max(parsed, key=lambda item: item[1]["return_pct"])[0]
    lowest_drawdown = min(parsed, key=lambda item: item[1]["max_drawdown_pct"])[0]
    profit_factor_candidates = [
        item for item in parsed if item[1].get("profit_factor") is not None
    ]
    highest_profit_factor = (
        None
        if not profit_factor_candidates
        else max(profit_factor_candidates, key=lambda item: item[1]["profit_factor"])[0]
    )
    return {
        "schema": "qookey-crypto-toolkit-backtest-comparison-v0.2",
        "status": "PASS",
        "mode": "RESEARCH_ONLY",
        "baseline_label": baseline_label,
        "results": rows,
        "descriptive_extremes": {
            "highest_return": highest_return,
            "lowest_drawdown": lowest_drawdown,
            "highest_profit_factor": highest_profit_factor,
        },
        "selection_or_promotion_performed": False,
        "authority": dict(SAFETY_BOUNDARY),
    }


def build_research_report(payload: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic text summary from local Toolkit evidence."""
    title = str(payload.get("title") or "Qookey Crypto Research Report").strip()
    if not title:
        raise ValueError("report title cannot be empty")
    validation = payload.get("validation")
    stress = payload.get("stress")
    comparison = payload.get("comparison")
    if validation is None and stress is None and comparison is None:
        raise ValueError("report requires validation, stress, or comparison evidence")

    warnings: list[str] = []
    lines = [f"# {title}", "", "Status: RESEARCH_ONLY / PAPER_ONLY where applicable."]

    if validation is not None:
        if not isinstance(validation, dict) or validation.get("schema") != (
            "qookey-crypto-toolkit-candle-validation-v0.2"
        ):
            raise ValueError("unsupported validation evidence")
        lines.extend(
            [
                "",
                "## Candle validation",
                f"- Status: {validation.get('status')}",
                f"- Candles: {validation.get('candle_count')}",
                f"- Gaps: {validation.get('gap_count')} ({validation.get('missing_bars')} missing bars)",
                f"- Invalid candles: {validation.get('invalid_candle_count')}",
            ]
        )
        if validation.get("status") != "PASS":
            warnings.append("CANDLE_VALIDATION_FAILED")

    if stress is not None:
        if not isinstance(stress, dict) or stress.get("schema") != (
            "qookey-crypto-toolkit-stress-backtest-v0.2"
        ):
            raise ValueError("unsupported stress evidence")
        summary = stress.get("summary") or {}
        lines.extend(
            [
                "",
                "## Stress backtest",
                f"- Scenarios: {stress.get('scenario_count')}",
                f"- Return range (%): {summary.get('return_range_pct')}",
                f"- Drawdown range (%): {summary.get('drawdown_range_pct')}",
            ]
        )
        return_range = summary.get("return_range_pct")
        if isinstance(return_range, list) and return_range and return_range[0] < 0:
            warnings.append("NEGATIVE_RETURN_STRESS_SCENARIO")

    if comparison is not None:
        if not isinstance(comparison, dict) or comparison.get("schema") != (
            "qookey-crypto-toolkit-backtest-comparison-v0.2"
        ):
            raise ValueError("unsupported comparison evidence")
        extremes = comparison.get("descriptive_extremes") or {}
        lines.extend(
            [
                "",
                "## Backtest comparison",
                f"- Baseline: {comparison.get('baseline_label')}",
                f"- Highest historical return: {extremes.get('highest_return')}",
                f"- Lowest historical drawdown: {extremes.get('lowest_drawdown')}",
                f"- Highest historical profit factor: {extremes.get('highest_profit_factor')}",
            ]
        )

    lines.extend(
        [
            "",
            "## Safety",
            "This report is descriptive research evidence, not a live-trading recommendation,",
            "model promotion decision, or claim of future profitability.",
        ]
    )
    return {
        "schema": "qookey-crypto-toolkit-research-report-v0.2",
        "status": "RESEARCH_ONLY",
        "title": title,
        "warnings": warnings,
        "markdown": "\n".join(lines) + "\n",
        "authority": dict(SAFETY_BOUNDARY),
    }


__all__ = [
    "build_research_report",
    "compare_backtests",
    "stress_paper_backtest",
    "validate_candles",
]
