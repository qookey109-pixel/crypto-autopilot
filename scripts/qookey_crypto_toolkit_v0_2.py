#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from crypto_autopilot.toolkit import (
    build_research_report,
    compare_backtests,
    evaluate_strategy,
    get_indicators,
    list_capabilities_v0_2,
    run_paper_backtest,
    size_long_trade_tool,
    stress_paper_backtest,
    validate_candles,
)


def _read_json(path: str) -> dict[str, Any]:
    payload = json.load(sys.stdin) if path == "-" else json.loads(Path(path).read_text())
    if not isinstance(payload, dict):
        raise ValueError("toolkit input must be a JSON object")
    return payload


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description="Qookey Crypto Toolkit V0.2 cloud/repository runner")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("capabilities", help="List research Toolkit capabilities")

    indicators = subparsers.add_parser("indicators", help="Calculate technical indicators")
    indicators.add_argument("--input", required=True)
    indicators.add_argument("--interval", required=True)
    indicators.add_argument("--include-series", action="store_true")

    validate = subparsers.add_parser("validate", help="Audit supplied candles without repair")
    validate.add_argument("--input", required=True)
    validate.add_argument("--interval", required=True)

    for command, help_text in (
        ("strategy", "Evaluate the deterministic strategy gate"),
        ("risk", "Calculate paper-only risk sizing"),
        ("backtest", "Run the deterministic paper-only backtest"),
        ("stress", "Stress a paper backtest across bounded execution-cost scenarios"),
        ("compare", "Compare paper-backtest evidence"),
        ("report", "Build a deterministic research report"),
    ):
        command_parser = subparsers.add_parser(command, help=help_text)
        command_parser.add_argument("--input", required=True)

    args = parser.parse_args()
    if args.command == "capabilities":
        _emit(list_capabilities_v0_2())
        return 0

    payload = _read_json(args.input)
    if args.command == "indicators":
        candles = payload.get("candles")
        if not isinstance(candles, list):
            raise ValueError("indicator input requires a candles list")
        _emit(get_indicators(candles, interval=args.interval, include_series=args.include_series))
    elif args.command == "validate":
        candles = payload.get("candles")
        if not isinstance(candles, list):
            raise ValueError("validation input requires a candles list")
        _emit(validate_candles(candles, interval=args.interval))
    elif args.command == "strategy":
        _emit(evaluate_strategy(payload))
    elif args.command == "risk":
        _emit(size_long_trade_tool(payload))
    elif args.command == "backtest":
        _emit(run_paper_backtest(payload))
    elif args.command == "stress":
        _emit(stress_paper_backtest(payload))
    elif args.command == "compare":
        _emit(compare_backtests(payload))
    elif args.command == "report":
        _emit(build_research_report(payload))
    else:
        raise AssertionError(f"unhandled command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
