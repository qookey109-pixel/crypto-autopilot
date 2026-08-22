from __future__ import annotations

import importlib.util
import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from crypto_autopilot.binance_spot_history import (
    BinanceSpotCandle,
    BinanceSpotSeries,
    ProviderReadDeadlineExceeded,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/fetch_binance_internal_training.py"
DAY_MS = 86_400_000
START_MS = 1_577_923_200_000  # 2020-01-02T00:00:00Z


def load_script():
    spec = importlib.util.spec_from_file_location(
        "fetch_binance_internal_training",
        SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FetchBinanceInternalTrainingTests(unittest.TestCase):
    def test_cache_log_distinguishes_fetch_from_reuse(self) -> None:
        module = load_script()
        series = BinanceSpotSeries(
            symbol="BTCUSDT",
            interval="1d",
            requested_start_ms=START_MS,
            requested_end_ms=START_MS,
            pages_fetched=1,
            candles=(
                BinanceSpotCandle(
                    symbol="BTCUSDT",
                    open_time_ms=START_MS,
                    open=100.0,
                    high=103.0,
                    low=99.0,
                    close=101.0,
                    base_volume=12.5,
                    close_time_ms=START_MS + DAY_MS - 1,
                    quote_volume=1262.5,
                    trade_count=42,
                ),
            ),
        )

        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            catalog_path = root / "catalog.json"
            output_dir = root / "output"
            catalog_path.write_text(
                json.dumps(
                    {
                        "schema": "binance-internal-training-market-catalog-v0.2",
                        "authority": {
                            key: False for key in module.FORBIDDEN_AUTHORITY_KEYS
                        },
                        "markets": [
                            {
                                "symbol": "BTCUSDT",
                                "market_type": "spot",
                                "asset_class": "crypto",
                                "classification_method": "test-fixture",
                                "classification_confidence": "high",
                                "base_asset": "BTC",
                                "quote_asset": "USDT",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            argv = [
                str(SCRIPT),
                "--catalog",
                str(catalog_path),
                "--output-dir",
                str(output_dir),
                "--start-utc",
                "2020-01-02T00:00:00Z",
                "--now-ms",
                str(START_MS + DAY_MS),
            ]

            first_stdout = io.StringIO()
            with (
                patch.object(sys, "argv", argv),
                patch.object(module, "fetch_spot_history", return_value=series) as fetch,
                redirect_stdout(first_stdout),
            ):
                self.assertEqual(module.main(), 0)
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(
                fetch.call_args.kwargs["provider_read_stop_ms"],
                1_787_788_800_000,
            )
            self.assertTrue(first_stdout.getvalue().splitlines()[0].endswith(" / fetched"))
            receipt = json.loads((output_dir / "receipt.json").read_text(encoding="utf-8"))
            catalog_payload = catalog_path.read_bytes()
            self.assertEqual(receipt["catalog"]["bytes"], len(catalog_payload))
            self.assertEqual(
                receipt["catalog"]["sha256"], hashlib.sha256(catalog_payload).hexdigest()
            )
            self.assertEqual(
                receipt["market_audit_evidence"]["BTCUSDT"]["actual_last_open_time_ms"],
                START_MS,
            )
            self.assertTrue(receipt["market_audit_evidence"]["BTCUSDT"]["tail_complete"])

            second_stdout = io.StringIO()
            with (
                patch.object(sys, "argv", argv),
                patch.object(
                    module,
                    "fetch_spot_history",
                    side_effect=AssertionError("valid cache must avoid provider fetch"),
                ) as fetch,
                redirect_stdout(second_stdout),
            ):
                self.assertEqual(module.main(), 0)
            self.assertEqual(fetch.call_count, 0)
            self.assertTrue(second_stdout.getvalue().splitlines()[0].endswith(" / cached"))

    def test_deadline_failure_aborts_before_next_market(self) -> None:
        module = load_script()
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            catalog_path = root / "catalog.json"
            output_dir = root / "output"
            markets = []
            for symbol, base_asset in (("BTCUSDT", "BTC"), ("ETHUSDT", "ETH")):
                markets.append(
                    {
                        "symbol": symbol,
                        "market_type": "spot",
                        "asset_class": "crypto",
                        "classification_method": "test-fixture",
                        "classification_confidence": "high",
                        "base_asset": base_asset,
                        "quote_asset": "USDT",
                    }
                )
            catalog_path.write_text(
                json.dumps(
                    {
                        "schema": "binance-internal-training-market-catalog-v0.2",
                        "authority": {
                            key: False for key in module.FORBIDDEN_AUTHORITY_KEYS
                        },
                        "markets": markets,
                    }
                ),
                encoding="utf-8",
            )
            argv = [
                str(SCRIPT),
                "--catalog",
                str(catalog_path),
                "--output-dir",
                str(output_dir),
                "--start-utc",
                "2020-01-02T00:00:00Z",
                "--now-ms",
                str(START_MS + DAY_MS),
            ]

            with (
                patch.object(sys, "argv", argv),
                patch.object(
                    module,
                    "fetch_spot_history",
                    side_effect=ProviderReadDeadlineExceeded("fixture deadline"),
                ) as fetch,
            ):
                with self.assertRaises(ProviderReadDeadlineExceeded):
                    module.main()

            self.assertEqual(fetch.call_count, 1)


if __name__ == "__main__":
    unittest.main()
