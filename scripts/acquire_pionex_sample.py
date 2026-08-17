#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from crypto_autopilot.exchanges.pionex_public import PionexPublicClient
from crypto_autopilot.historical import INTERVAL_MS, backfill_klines, write_backfill_json

DAY_MS = 24 * 60 * 60 * 1000
FOUR_HOURS_MS = INTERVAL_MS["4H"]


def closed_boundary_ms(now_ms: int) -> int:
    """Return the last millisecond before the current UTC 4H bucket."""
    return (now_ms // FOUR_HOURS_MS) * FOUR_HOURS_MS - 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Acquire a bounded Pionex research sample.")
    parser.add_argument("--universe", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--minimum-symbols", type=int, default=10)
    parser.add_argument("--end-ms", type=int, help="Optional frozen acquisition end boundary for replay")
    args = parser.parse_args()

    if args.days < 1:
        parser.error("days must be positive")
    if args.minimum_symbols < 1:
        parser.error("minimum-symbols must be positive")

    universe = json.loads(args.universe.read_text(encoding="utf-8"))
    symbols = [str(item["symbol"]) for item in universe.get("selected", [])]
    if len(symbols) < args.minimum_symbols:
        raise SystemExit(
            f"universe has {len(symbols)} symbols; requires at least {args.minimum_symbols}"
        )

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    end_ms = args.end_ms if args.end_ms is not None else closed_boundary_ms(now_ms)
    start_ms = end_ms + 1 - args.days * DAY_MS

    args.output_dir.mkdir(parents=True, exist_ok=True)
    client = PionexPublicClient()
    results = []
    all_ok = True
    total_pages = 0
    total_candles = 0

    for symbol in symbols:
        for interval in ("15M", "60M", "4H"):
            result = backfill_klines(
                client,
                symbol,
                interval,
                start_time_ms=start_ms,
                end_time_ms=end_ms,
                page_limit=500,
            )
            relative = Path("candles") / symbol / f"{interval}.json"
            write_backfill_json(args.output_dir / relative, result)
            total_pages += result.pages_fetched
            total_candles += len(result.candles)
            all_ok = all_ok and result.audit.ok
            results.append(
                {
                    "symbol": symbol,
                    "interval": interval,
                    "file": str(relative),
                    "candles": len(result.candles),
                    "pages": result.pages_fetched,
                    "audit_ok": result.audit.ok,
                    "gap_count": len(result.audit.gaps),
                    "duplicate_count": len(result.audit.duplicate_timestamps),
                    "invalid_count": len(result.audit.invalid_candle_timestamps),
                }
            )

    receipt = {
        "schema_version": 1,
        "stage": "M1A_LIVE_PIONEX_ACQUISITION_RECEIPT",
        "source": "pionex_public_futures",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_days": args.days,
        "requested_start_ms": start_ms,
        "requested_end_ms": end_ms,
        "symbols": symbols,
        "symbol_count": len(symbols),
        "intervals": ["15M", "60M", "4H"],
        "total_pages": total_pages,
        "total_candles": total_candles,
        "audit_pass": all_ok,
        "results": results,
    }
    (args.output_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"symbols={len(symbols)} total_pages={total_pages} total_candles={total_candles} "
        f"audit_pass={all_ok} receipt={args.output_dir / 'receipt.json'}"
    )
    return 0 if all_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
