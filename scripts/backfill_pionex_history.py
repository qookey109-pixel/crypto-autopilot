#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from crypto_autopilot.exchanges.pionex_public import PionexPublicClient
from crypto_autopilot.historical import backfill_klines, write_backfill_json


def parse_utc_ms(value: str) -> int:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.astimezone(timezone.utc).timestamp() * 1000)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill deterministic Pionex futures candles.")
    parser.add_argument("symbol", help="Example: BTC_USDT_PERP")
    parser.add_argument("interval", choices=("15M", "60M", "4H"))
    parser.add_argument("--start", required=True, help="ISO-8601 UTC boundary, e.g. 2026-01-01T00:00:00Z")
    parser.add_argument("--end", required=True, help="ISO-8601 UTC boundary, e.g. 2026-08-01T00:00:00Z")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--page-limit", type=int, default=500)
    args = parser.parse_args()

    result = backfill_klines(
        PionexPublicClient(),
        args.symbol,
        args.interval,
        start_time_ms=parse_utc_ms(args.start),
        end_time_ms=parse_utc_ms(args.end),
        page_limit=args.page_limit,
    )
    write_backfill_json(args.output, result)
    print(
        f"symbol={result.symbol} interval={result.interval} candles={len(result.candles)} "
        f"pages={result.pages_fetched} audit_ok={result.audit.ok} output={args.output}"
    )
    return 0 if result.audit.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
