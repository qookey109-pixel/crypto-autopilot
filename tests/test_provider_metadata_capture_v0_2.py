from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from crypto_autopilot.provider_metadata_capture_suspension_v0_2 import load_transport_blocker
from crypto_autopilot.provider_metadata_capture_v0_2 import (
    capture_slot,
    load_and_validate_authority,
    parse_binance_exchange_info,
    parse_pionex_symbols,
)


TRANSPORT_PASS = Path(
    "research/receipts/2026-08-19-provider-equivalence-v0-2-self-hosted-mac-transport-pass.json"
)
FORWARD_AUTHORITY = Path(
    "research/receipts/2026-08-19-provider-equivalence-v0-2-forward-metadata-capture-authority-v0-2.json"
)
V0_1_RESULT = Path("research/receipts/2026-08-19-pionex-binance-equivalence-v0-1.json")
CAPTURE_CLI = Path("scripts/capture_provider_equivalence_v0_2_metadata.py")


def _load(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"expected object: {path}")
    return payload


class ProviderMetadataCaptureV02Tests(unittest.TestCase):
    def test_replacement_capture_protocol_is_frozen_and_metadata_only(self) -> None:
        protocol, pionex, binance = load_and_validate_authority()
        self.assertEqual(len(pionex), 15)
        self.assertEqual(len(binance), 15)
        self.assertEqual(protocol["version"], "0.2.0")
        self.assertEqual(protocol["metadata_capture_window"]["hourly_slot_count"], 194)
        self.assertEqual(
            protocol["capture_execution"]["required_runner_labels"],
            ["self-hosted", "macOS", "ARM64"],
        )
        self.assertIs(protocol["capture_execution"]["connectivity_preflight_already_completed"], True)
        self.assertIs(protocol["capture_execution"]["connectivity_preflight_rerun_authorized"], False)
        self.assertIs(protocol["authorization_boundary"]["metadata_capture_authorized"], True)
        self.assertIs(protocol["authorization_boundary"]["metadata_only_r2_writes_authorized"], True)
        self.assertIs(protocol["authorization_boundary"]["holdout_candle_access_authorized"], False)
        self.assertIs(protocol["authorization_boundary"]["backtest_admission_authorized"], False)
        self.assertIs(protocol["authorization_boundary"]["live_trading_authorized"], False)

    def test_historical_transport_blocker_remains_immutable_lineage(self) -> None:
        blocker = load_transport_blocker()
        self.assertEqual(blocker["status"], "PASS")
        self.assertEqual(
            blocker["stage"],
            "PROVIDER_EQUIVALENCE_V0_2_METADATA_TRANSPORT_BLOCKED_CAPTURE_SUSPENDED",
        )
        self.assertEqual(
            blocker["holdout_state"]["state"],
            "SUPERSEDED_UNOPENED_BEFORE_METADATA_CAPTURE_EVIDENCE",
        )
        self.assertIs(blocker["holdout_state"]["holdout_candles_accessed"], False)
        self.assertIs(blocker["holdout_state"]["holdout_evaluated"], False)
        self.assertIs(blocker["holdout_state"]["replacement_holdout_frozen"], False)
        boundary = blocker["authorization_boundary"]
        self.assertIs(boundary["metadata_capture_execution_authorized"], False)
        self.assertIs(boundary["metadata_only_r2_writes_authorized"], False)
        self.assertIs(boundary["holdout_candle_access_authorized"], False)
        self.assertIs(boundary["source_switch_authorized"], False)
        self.assertIs(boundary["live_trading_authorized"], False)

    def test_self_hosted_transport_pass_is_sanitized_only(self) -> None:
        transport = _load(TRANSPORT_PASS)
        self.assertEqual(transport["status"], "PASS")
        self.assertEqual(
            transport["stage"],
            "PROVIDER_EQUIVALENCE_V0_2_SELF_HOSTED_MAC_BINANCE_TRANSPORT_PASS",
        )
        evidence = transport["execution_evidence"]
        self.assertEqual(evidence["transport"], "github_self_hosted_mac")
        self.assertEqual(evidence["runner_os"], "Darwin")
        self.assertEqual(evidence["runner_machine"], "arm64")
        self.assertEqual(evidence["http_status"], 200)
        self.assertIs(evidence["json_ok"], True)
        self.assertIs(evidence["symbols_array"], True)
        self.assertGreater(evidence["symbol_count"], 0)
        safety = transport["sanitization_and_safety"]
        self.assertIs(safety["increment_values_emitted"], False)
        self.assertIs(safety["r2_client_constructed"], False)
        self.assertIs(safety["r2_writes_performed"], False)
        self.assertIs(safety["holdout_candles_accessed"], False)
        self.assertIs(safety["source_switch_authorized"], False)
        self.assertIs(safety["live_trading_authorized"], False)

    def test_replacement_holdout_is_disjoint_and_unopened(self) -> None:
        authority = _load(FORWARD_AUTHORITY)
        old_holdout = authority["superseded_holdout"]
        new_holdout = authority["new_frozen_candidate_holdout"]
        old_end = datetime.fromisoformat(old_holdout["end_utc"].replace("Z", "+00:00"))
        new_start = datetime.fromisoformat(new_holdout["start_utc"].replace("Z", "+00:00"))
        self.assertGreater(new_start, old_end)
        self.assertIs(old_holdout["reactivation_authorized"], False)
        self.assertEqual(new_holdout["state"], "FROZEN_UNOPENED")
        self.assertIs(new_holdout["candles_accessed"], False)
        self.assertIs(new_holdout["candles_evaluated"], False)
        self.assertIs(new_holdout["result_known"], False)
        self.assertIs(new_holdout["disjoint_from_superseded_holdout"], True)

    def test_v0_1_definitive_fail_is_unchanged(self) -> None:
        result = _load(V0_1_RESULT)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["aggregate"]["gate_status"], "FAIL")
        self.assertEqual(result["aggregate"]["evaluated_pair_count"], 45)
        self.assertEqual(result["aggregate"]["pass_count"], 18)
        self.assertEqual(result["aggregate"]["review_count"], 18)
        self.assertEqual(result["aggregate"]["fail_count"], 9)
        self.assertIs(result["aggregate"]["source_switch_authorized"], False)

    def test_capture_cli_does_not_offer_transport_preflight_rerun(self) -> None:
        source = CAPTURE_CLI.read_text(encoding="utf-8")
        self.assertNotIn("connectivity-preflight", source)
        self.assertIn('choices=("capture",)', source)

    def test_parse_pionex_requires_exact_expected_symbols_and_positive_steps(self) -> None:
        raw = json.dumps(
            {
                "data": {
                    "symbols": [
                        {
                            "symbol": "BTC_USDT_PERP",
                            "quoteStep": "0.1",
                            "status": "TRADING",
                            "contractType": "PERP",
                        },
                        {
                            "symbol": "ETH_USDT_PERP",
                            "quoteStep": "0.01",
                            "status": "TRADING",
                            "contractType": "PERP",
                        },
                    ]
                }
            }
        ).encode()
        rows = parse_pionex_symbols(raw, ("BTC_USDT_PERP", "ETH_USDT_PERP"))
        self.assertEqual([row["symbol"] for row in rows], ["BTC_USDT_PERP", "ETH_USDT_PERP"])
        self.assertEqual(rows[0]["price_increment"], "0.1")
        self.assertEqual(rows[1]["price_increment"], "0.01")
        self.assertTrue(all(row["source_field"] == "data.symbols[].quoteStep" for row in rows))

    def test_parse_pionex_missing_symbol_fails_closed(self) -> None:
        raw = json.dumps(
            {
                "data": {
                    "symbols": [
                        {
                            "symbol": "BTC_USDT_PERP",
                            "quoteStep": "0.1",
                            "status": "TRADING",
                            "contractType": "PERP",
                        }
                    ]
                }
            }
        ).encode()
        with self.assertRaisesRegex(RuntimeError, "missing frozen symbols"):
            parse_pionex_symbols(raw, ("BTC_USDT_PERP", "ETH_USDT_PERP"))

    def test_parse_binance_requires_price_filter(self) -> None:
        raw = json.dumps(
            {
                "symbols": [
                    {
                        "symbol": "BTCUSDT",
                        "status": "TRADING",
                        "contractType": "PERPETUAL",
                        "filters": [
                            {"filterType": "PRICE_FILTER", "tickSize": "0.10"},
                            {"filterType": "LOT_SIZE", "stepSize": "0.001"},
                        ],
                    }
                ]
            }
        ).encode()
        rows = parse_binance_exchange_info(raw, ("BTCUSDT",))
        self.assertEqual(rows[0]["price_increment"], "0.10")
        self.assertEqual(
            rows[0]["source_field"],
            "symbols[].filters[filterType=PRICE_FILTER].tickSize",
        )

    def test_nonpositive_increment_fails_closed(self) -> None:
        raw = json.dumps(
            {
                "symbols": [
                    {
                        "symbol": "BTCUSDT",
                        "status": "TRADING",
                        "contractType": "PERPETUAL",
                        "filters": [{"filterType": "PRICE_FILTER", "tickSize": "0"}],
                    }
                ]
            }
        ).encode()
        with self.assertRaisesRegex(RuntimeError, "finite and positive"):
            parse_binance_exchange_info(raw, ("BTCUSDT",))

    def test_replacement_capture_slot_math(self) -> None:
        protocol, _, _ = load_and_validate_authority()
        inside = datetime(2026, 8, 28, 3, 47, 12, tzinfo=timezone.utc)
        self.assertEqual(
            capture_slot(inside, protocol),
            datetime(2026, 8, 28, 3, 0, 0, tzinfo=timezone.utc),
        )
        before = datetime(2026, 8, 26, 23, 59, 59, tzinfo=timezone.utc)
        after = datetime(2026, 9, 4, 2, 0, 0, tzinfo=timezone.utc)
        self.assertIsNone(capture_slot(before, protocol))
        self.assertIsNone(capture_slot(after, protocol))


if __name__ == "__main__":
    unittest.main()
