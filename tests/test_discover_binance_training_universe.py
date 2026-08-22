from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from crypto_autopilot.binance_spot_history import ProviderReadDeadlineExceeded


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/discover_binance_training_universe.py"


def load_script():
    spec = importlib.util.spec_from_file_location(
        "discover_binance_training_universe",
        SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DiscoverBinanceTrainingUniverseTests(unittest.TestCase):
    def test_deadline_blocks_exchange_info_transport_at_exact_stop(self) -> None:
        module = load_script()
        calls: list[str] = []

        def transport(url: str, _timeout: float) -> bytes:
            calls.append(url)
            return json.dumps({"symbols": []}).encode()

        with self.assertRaises(ProviderReadDeadlineExceeded):
            module.fetch_exchange_info(
                provider_read_stop_ms=2_000_000,
                clock_fn=lambda: 2_000.0,
                transport=transport,
            )

        self.assertEqual(calls, [])

    def test_exchange_info_transport_runs_before_deadline(self) -> None:
        module = load_script()
        calls: list[tuple[str, float]] = []

        def transport(url: str, timeout_seconds: float) -> bytes:
            calls.append((url, timeout_seconds))
            return json.dumps({"symbols": []}).encode()

        payload = module.fetch_exchange_info(
            timeout_seconds=12.5,
            provider_read_stop_ms=2_000_000,
            clock_fn=lambda: 1_999.999,
            transport=transport,
        )

        self.assertEqual(payload, {"symbols": []})
        self.assertEqual(calls, [(module.ENDPOINT, 12.5)])

    def test_main_passes_authorized_config_deadline_to_discovery(self) -> None:
        module = load_script()
        exchange_info = {
            "symbols": [
                {
                    "symbol": "BTCUSDT",
                    "baseAsset": "BTC",
                    "quoteAsset": "USDT",
                    "status": "TRADING",
                    "isSpotTradingAllowed": True,
                }
            ]
        }
        with tempfile.TemporaryDirectory() as temporary_dir:
            output = Path(temporary_dir) / "catalog.json"
            argv = [str(SCRIPT), "--output", str(output), "--quotes", "USDT"]
            with (
                patch.object(sys, "argv", argv),
                patch.object(
                    module,
                    "fetch_exchange_info",
                    return_value=exchange_info,
                ) as fetch,
            ):
                self.assertEqual(module.main(), 0)

        self.assertEqual(
            fetch.call_args.kwargs["provider_read_stop_ms"],
            1_787_788_800_000,
        )

    def test_noncanonical_config_cannot_extend_provider_deadline(self) -> None:
        module = load_script()
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            config = json.loads(module.DEFAULT_CONFIG.read_text())
            config["schedule"]["provider_read_stop_utc"] = "2099-01-01T00:00:00Z"
            config_path = root / "altered-config.json"
            config_path.write_text(json.dumps(config) + "\n")
            output = root / "catalog.json"
            argv = [
                str(SCRIPT),
                "--config",
                str(config_path),
                "--output",
                str(output),
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(module, "fetch_exchange_info") as fetch,
                self.assertRaisesRegex(
                    ValueError, "canonical V0.5 config path"
                ),
            ):
                module.main()
            fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
