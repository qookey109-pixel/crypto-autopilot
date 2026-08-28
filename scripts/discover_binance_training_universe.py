from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

from crypto_autopilot.binance.spot_history import (
    Clock,
    provider_read_stop_ms_from_v0_5_config,
    require_provider_request_before_deadline,
)
from crypto_autopilot.binance.training_catalog import (
    DEFAULT_QUOTES,
    catalog_payload,
    parse_exchange_info,
)
from crypto_autopilot.storage.ephemeral import require_ephemeral_output
from crypto_autopilot.training.quality import load_v0_5_authority_pair


ENDPOINT = "https://data-api.binance.vision/api/v3/exchangeInfo"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = (
    REPOSITORY_ROOT / "config/binance_spot_r2_training_governance_v0_5.json"
)
ExchangeInfoTransport = Callable[[str, float], bytes]


def public_exchange_info_transport(url: str, timeout_seconds: float) -> bytes:
    request = Request(
        url,
        headers={"User-Agent": "qookey-crypto-autopilot-training-catalog/0.2"},
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        return response.read()


def fetch_exchange_info(
    timeout_seconds: float = 30.0,
    *,
    provider_read_stop_ms: int | None = None,
    clock_fn: Clock = time.time,
    transport: ExchangeInfoTransport = public_exchange_info_transport,
) -> dict:
    require_provider_request_before_deadline(
        provider_read_stop_ms=provider_read_stop_ms,
        clock_fn=clock_fn,
    )
    payload = json.loads(transport(ENDPOINT, timeout_seconds))
    if not isinstance(payload, dict):
        raise RuntimeError("Binance exchangeInfo response must be an object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover Binance Spot markets for the R2 training pipeline")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output", required=True)
    parser.add_argument("--quotes", nargs="+", default=list(DEFAULT_QUOTES))
    parser.add_argument("--all-quotes", action="store_true")
    args = parser.parse_args()
    output = require_ephemeral_output(args.output)
    config_path = Path(args.config)
    config_payload = config_path.read_bytes()
    config = json.loads(config_payload)
    load_v0_5_authority_pair(
        config,
        config_path=config_path,
        config_payload=config_payload,
        repository_root=REPOSITORY_ROOT,
    )
    provider_read_stop_ms = provider_read_stop_ms_from_v0_5_config(config)

    markets = parse_exchange_info(
        fetch_exchange_info(
            provider_read_stop_ms=provider_read_stop_ms,
        ),
        quotes=tuple(args.quotes),
        all_quotes=args.all_quotes,
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
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    quote_counts = Counter(item.quote_asset for item in markets)
    class_counts = Counter(item.asset_class for item in markets)
    print(json.dumps({"status": "PASS", "markets": len(markets), "quotes": quote_counts, "asset_classes": class_counts}, default=dict, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
