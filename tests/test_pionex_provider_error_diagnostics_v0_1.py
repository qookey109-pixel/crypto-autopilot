from __future__ import annotations

import json
from pathlib import Path
import unittest

from crypto_autopilot.exchanges.pionex_public import PionexAPIError
from crypto_autopilot.history import pionex_validation_materialization_v0_1 as materialization
from crypto_autopilot.history.pionex_provider_error_diagnostics_v0_1 import (
    ProviderErrorDiagnosticKlineClient,
    install_provider_error_diagnostics,
    pionex_api_error_diagnostics,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/pionex_validation_dataset_v0_1.json"


class FailingPionexClient:
    def get_klines(self, symbol, interval, *, limit=500, end_time_ms=None):
        raise PionexAPIError(
            "Pionex request failed: 429 Too many requests "
            "https://api.pionex.com/internal token=super-secret"
        )


class GenericFailingClient:
    def get_klines(self, symbol, interval, *, limit=500, end_time_ms=None):
        raise RuntimeError("ordinary failure")


class PionexProviderErrorDiagnosticsTests(unittest.TestCase):
    def test_pionex_error_is_structured_bounded_and_redacted(self) -> None:
        exc = PionexAPIError(
            "Pionex request failed: 10012 provider rejected "
            "https://example.invalid/path api_key=abc123 " + ("x" * 400)
        )
        diagnostics = pionex_api_error_diagnostics(exc)
        self.assertEqual(diagnostics["provider_error_code"], "10012")
        message = str(diagnostics["provider_error_message"])
        self.assertIn("[redacted-url]", message)
        self.assertIn("api_key=[redacted]", message)
        self.assertNotIn("abc123", message)
        self.assertNotIn("example.invalid", message)
        self.assertLessEqual(len(message), 256)

    def test_adapter_does_not_capture_generic_exception_text(self) -> None:
        client = ProviderErrorDiagnosticKlineClient(GenericFailingClient())
        with self.assertRaisesRegex(RuntimeError, "ordinary failure"):
            client.get_klines("BTC_USDT_PERP", "60M")
        self.assertEqual(client.provider_error_diagnostics, {})

    def test_materialization_failure_adds_only_safe_provider_fields(self) -> None:
        config = json.loads(CONFIG_PATH.read_text())
        install_provider_error_diagnostics()
        client = ProviderErrorDiagnosticKlineClient(FailingPionexClient())
        progress = {"requests": 0, "protected_range_violation": 0}
        now_ms = materialization.stamp(str(config["materialization"]["not_before_utc"])) + 1

        with self.assertRaises(materialization.ValidationMaterializationRejected) as caught:
            materialization.collect_partition(
                config,
                client,
                symbol="AAVE_USDT_PERP",
                interval="1W",
                progress=progress,
                clock=lambda: now_ms,
            )

        exc = caught.exception
        self.assertEqual(str(exc), "provider request failed before any valid rows")
        self.assertEqual(exc.diagnostics["error_type"], "PionexAPIError")
        self.assertEqual(exc.diagnostics["provider_error_code"], "429")
        self.assertEqual(
            exc.diagnostics["provider_error_message"],
            "Too many requests [redacted-url] token=[redacted]",
        )
        serialized = json.dumps(exc.diagnostics, sort_keys=True)
        self.assertNotIn("super-secret", serialized)
        self.assertNotIn("api.pionex.com", serialized)
        self.assertNotIn("payload", serialized.lower())
        self.assertEqual(progress["requests"], 1)


if __name__ == "__main__":
    unittest.main()
