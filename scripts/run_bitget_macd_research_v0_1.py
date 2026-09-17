#!/usr/bin/env python3
"""Run paper-only Bitget-style 30m MACD research from a local candle JSON file."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.models import Candle
from crypto_autopilot.research.bitget_macd import (
    BitgetMacdResearchConfig,
    default_bitget_macd_candidate_grid,
    rank_candidates,
    result_summary,
    run_bitget_macd_long_30m_research,
    run_candidate_grid,
)


def _load_candles(path: Path) -> list[Candle]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("candles") if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not rows:
        raise ValueError("input must be a non-empty candle list or {'candles': [...]} object")
    candles = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("each candle must be a JSON object")
        candles.append(
            Candle(
                time_ms=int(row["time_ms"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            )
        )
    return candles


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("candles", type=Path, help="Local contiguous 15m OHLCV JSON")
    parser.add_argument("--initial-equity", type=float, default=10_000.0)
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--max-candidates", type=int)
    parser.add_argument("--baseline-only", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.top < 1:
        raise ValueError("--top must be positive")
    if args.max_candidates is not None and args.max_candidates < 1:
        raise ValueError("--max-candidates must be positive")

    candles = _load_candles(args.candles)
    if args.baseline_only:
        result = run_bitget_macd_long_30m_research(
            candles_15m=candles,
            config=BitgetMacdResearchConfig(),
            initial_equity_usd=args.initial_equity,
        )
        payload = {
            "schema": "qookey-bitget-macd-long-30m-research-v0.1",
            "mode": "BASELINE_ONLY",
            "result": result_summary(result),
            "data_source": "LOCAL_FILE_ONLY",
            "provider_requests_performed": 0,
            "r2_reads_performed": False,
            "r2_writes_performed": False,
            "live_trading_authorized": False,
        }
    else:
        configs = default_bitget_macd_candidate_grid()
        if args.max_candidates is not None:
            configs = configs[: args.max_candidates]
        results = run_candidate_grid(
            candles_15m=candles,
            configs=configs,
            initial_equity_usd=args.initial_equity,
        )
        ranked = rank_candidates(results)
        payload = {
            "schema": "qookey-bitget-macd-long-30m-research-v0.1",
            "mode": "CURATED_SENSITIVITY_GRID",
            "candidate_count": len(results),
            "top_results": [result_summary(result) for result in ranked[: args.top]],
            "data_source": "LOCAL_FILE_ONLY",
            "provider_requests_performed": 0,
            "r2_reads_performed": False,
            "r2_writes_performed": False,
            "bitget_fluctuation_formula_verified": False,
            "live_trading_authorized": False,
        }

    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
