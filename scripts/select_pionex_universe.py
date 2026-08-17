#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from crypto_autopilot.exchanges.pionex_public import PionexPublicClient
from crypto_autopilot.universe import rank_perpetual_universe


def main() -> int:
    parser = argparse.ArgumentParser(description="Select a liquid Pionex USDT perpetual universe.")
    parser.add_argument("--target-size", type=int, default=15)
    parser.add_argument("--min-size", type=int, default=10)
    parser.add_argument("--max-spread-bps", type=float, default=30.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if not 1 <= args.min_size <= args.target_size <= 20:
        parser.error("require 1 <= min-size <= target-size <= 20")

    client = PionexPublicClient()
    selected = rank_perpetual_universe(
        client.list_perpetual_symbols(),
        client.list_perpetual_tickers(),
        client.list_perpetual_book_tickers(),
        target_size=args.target_size,
        max_spread_bps=args.max_spread_bps,
    )
    payload = {
        "schema_version": 1,
        "source": "pionex_public_futures",
        "selection": {
            "quote_suffix": "_USDT_PERP",
            "target_size": args.target_size,
            "minimum_acceptable_size": args.min_size,
            "max_spread_bps": args.max_spread_bps,
            "ranking": "24h exchange-reported amount desc, spread asc, symbol asc",
        },
        "selected": [asdict(item) for item in selected],
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")

    return 0 if len(selected) >= args.min_size else 2


if __name__ == "__main__":
    raise SystemExit(main())
