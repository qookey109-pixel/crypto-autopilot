from __future__ import annotations

import json
import sys

from crypto_autopilot.exchanges.pionex_public import PionexPublicClient


def main() -> int:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "BTC_USDT_PERP"
    interval = sys.argv[2] if len(sys.argv) > 2 else "15M"
    client = PionexPublicClient()
    candles = client.get_klines(symbol, interval, limit=10)
    rows = [
        {
            "time_ms": candle.time_ms,
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
        }
        for candle in candles
    ]
    print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
