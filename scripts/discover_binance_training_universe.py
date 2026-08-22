from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

from crypto_autopilot.binance_training_catalog import (
    DEFAULT_QUOTES,
    catalog_payload,
    parse_exchange_info,
)


ENDPOINT = "https://api.binance.com/api/v3/exchangeInfo"


def fetch_exchange_info(timeout_seconds: float = 30.0) -> dict:
    request = Request(ENDPOINT, headers={"User-Agent": "qookey-crypto-autopilot-training-catalog/0.2"})
    with urlopen(request, timeout=timeout_seconds) as response:
        payload = json.loads(response.read())
    if not isinstance(payload, dict):
        raise RuntimeError("Binance exchangeInfo response must be an object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover Binance Spot markets for local training")
    parser.add_argument("--output", default="artifacts/binance-internal-training-v0-2/market-catalog.json")
    parser.add_argument("--quotes", nargs="+", default=list(DEFAULT_QUOTES))
    parser.add_argument("--all-quotes", action="store_true")
    args = parser.parse_args()

    markets = parse_exchange_info(
        fetch_exchange_info(), quotes=tuple(args.quotes), all_quotes=args.all_quotes
    )
    if not markets:
        raise RuntimeError("no eligible Binance Spot markets discovered")
    retrieved_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    payload = catalog_payload(
        markets,
        retrieved_at_utc=retrieved_at,
        quotes=[str(item).upper() for item in args.quotes],
        all_quotes=args.all_quotes,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    quote_counts = Counter(item.quote_asset for item in markets)
    class_counts = Counter(item.asset_class for item in markets)
    print(json.dumps({"status": "PASS", "markets": len(markets), "quotes": quote_counts, "asset_classes": class_counts}, default=dict, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
