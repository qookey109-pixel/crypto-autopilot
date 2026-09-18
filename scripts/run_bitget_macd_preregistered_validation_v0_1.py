#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.models import Candle
from crypto_autopilot.research.bitget_macd_validation import (
    BitgetMacdValidationPlan,
    plan_payload,
    plan_sha256,
    run_preregistered_validation,
    validation_summary,
)


def _load_candles(path: Path) -> list[Candle]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("candles") if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not rows:
        raise ValueError("input must be a non-empty candle list or {'candles': [...]} object")
    return [
        Candle(
            time_ms=int(row["time_ms"]),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume"]),
        )
        for row in rows
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("candles", type=Path, nargs="?")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--initial-equity", type=float, default=10_000.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    plan = BitgetMacdValidationPlan()
    if args.plan_only:
        payload = {"plan": plan_payload(plan), "plan_sha256": plan_sha256(plan)}
    else:
        if args.candles is None:
            raise ValueError("candles path is required unless --plan-only is used")
        result = run_preregistered_validation(
            candles_15m=_load_candles(args.candles),
            plan=plan,
            initial_equity_usd=args.initial_equity,
        )
        payload = validation_summary(result)

    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
