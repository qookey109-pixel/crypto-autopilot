from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

from crypto_autopilot.paper.cloud_budget_ledger_v0_1 import (
    D1UsageSnapshot,
    D1SharedRowsBudgetGuard,
)
from scripts.measure_cloud_paper_r2_protocol_profile_v0_1 import _MemoryS3Client
from crypto_autopilot.paper.cloud_candidate_adapter_v0_1 import CloudCandidateRegistryBlocked
from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked, R2UsageSnapshot
from crypto_autopilot.paper.cloud_pionex_client_v0_1 import CloudPaperPionexPublicClient
from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Store
from crypto_autopilot.paper.cloud_runtime_v0_1 import (
    CLOUD_PAPER_PREFIX,
    build_runtime_composition,
)

MODULE = "crypto_autopilot.paper.cloud_runtime_v0_1"
NOW = 1_790_864_820_000
ROOT = Path(__file__).resolve().parents[1]


def inputs():
    return {
        "r2_snapshot": R2UsageSnapshot(
            account_wide=True, reservation_coverage_complete=True,
            observed_at_ms=NOW, measured_through_ms=NOW, storage_bytes=0,
            class_a_month=0, class_b_month=0, class_a_31_days=0, class_b_31_days=0,
            class_a_day=0, class_b_day=0, provider_requests_day=0, new_bytes_day=0,
        ),
        "d1_snapshot": D1UsageSnapshot(
            account_wide=True, reservation_coverage_complete=True,
            observed_at_ms=NOW, measured_through_ms=NOW,
            rows_read_day=0, rows_written_day=0, storage_bytes=0,
        ),
        "strategy_registry": json.loads(
            (ROOT / "config/cloud_paper_strategy_registry_v0_1.json").read_text(),
        ),
        "allowed_base_assets": frozenset({"BTC"}),
        "clock_ms": lambda: NOW,
    }


class CloudPaperRuntimeAssemblyTests(unittest.TestCase):
    def test_default_off_before_environment_or_client_construction(self):
        with patch(f"{MODULE}.os.environ.get") as environment:
            with patch(f"{MODULE}.BudgetedR2Store.from_credentials") as r2:
                with patch(f"{MODULE}.CloudflareD1QueryClient.from_environment") as d1:
                    self.assertIsNone(build_runtime_composition(**inputs()))
        environment.assert_not_called()
        r2.assert_not_called()
        d1.assert_not_called()

    def test_incomplete_stale_or_hard_stop_evidence_prevents_construction(self):
        for key, changes, reason in (
            ("r2_snapshot", {"account_wide": False}, "EVIDENCE_INCOMPLETE"),
            ("r2_snapshot", {"measured_through_ms": NOW - 60_001}, "EVIDENCE_STALE"),
            ("r2_snapshot", {"storage_bytes": 8_000_000_000}, "STORAGE_HARD_STOP"),
            ("d1_snapshot", {"reservation_coverage_complete": False}, "EVIDENCE_INCOMPLETE"),
            ("d1_snapshot", {"measured_through_ms": NOW - 50_001}, "EVIDENCE_STALE"),
        ):
            with self.subTest(key=key, changes=changes):
                values = inputs()
                values[key] = replace(values[key], **changes)
                with patch(f"{MODULE}.os.environ.get") as environment:
                    with patch(f"{MODULE}.BudgetedR2Store.from_credentials") as r2:
                        with self.assertRaisesRegex(BudgetBlocked, reason):
                            build_runtime_composition(**values, construction_enabled=True)
                environment.assert_not_called()
                r2.assert_not_called()

    def test_all_adapters_share_guards_and_default_run_performs_no_io(self):
        sdk = Mock()
        query_client = Mock()
        captured = {}
        def r2_factory(**kwargs):
            captured.update(kwargs)
            return BudgetedR2Store(
                client=sdk, bucket="synthetic-only",
                budget_guard=kwargs["budget_guard"],
                freshness_check=kwargs["freshness_check"],
            )
        with patch(f"{MODULE}.BudgetedR2Store.from_credentials", side_effect=r2_factory):
            with patch(f"{MODULE}.CloudflareD1QueryClient.from_environment",
                       return_value=query_client) as d1:
                with patch(f"{MODULE}.os.environ.get", return_value="synthetic-only"):
                    runtime = build_runtime_composition(**inputs(), construction_enabled=True)
        self.assertIsInstance(runtime.client, CloudPaperPionexPublicClient)
        self.assertEqual(runtime.store.prefix, CLOUD_PAPER_PREFIX)
        self.assertIs(runtime.store.store.budget_guard, runtime.budget_guard)
        self.assertIs(runtime.reservation_ledger.client, query_client)
        self.assertIs(d1.call_args.kwargs["usage_guard"], runtime.d1_usage_guard)
        self.assertIsInstance(d1.call_args.kwargs["shared_rows_guard"], D1SharedRowsBudgetGuard)
        self.assertIs(captured["freshness_check"], runtime.before_external)
        result = runtime.run_slot(tick_ms=NOW, previous_slot=None)
        self.assertEqual(result["state"], "DISABLED")
        self.assertEqual(result["provider_requests_performed"], 0)
        sdk.assert_not_called()
        self.assertEqual(sdk.mock_calls, [])
        self.assertEqual(query_client.mock_calls, [])

    def test_send_boundary_uses_original_evidence_without_retimestamping(self):
        now = [NOW]
        values = inputs()
        values["clock_ms"] = lambda: now[0]
        captured = {}
        def factory(**kwargs):
            captured.update(kwargs)
            return BudgetedR2Store(
                client=Mock(), bucket="synthetic-only",
                budget_guard=kwargs["budget_guard"],
                freshness_check=kwargs["freshness_check"],
            )
        with patch(f"{MODULE}.BudgetedR2Store.from_credentials", side_effect=factory):
            with patch(f"{MODULE}.CloudflareD1QueryClient.from_environment"):
                with patch(f"{MODULE}.os.environ.get", return_value="synthetic-only"):
                    runtime = build_runtime_composition(**values, construction_enabled=True)
        self.assertIs(runtime.budget_guard.snapshot, values["r2_snapshot"])
        self.assertIs(runtime.d1_usage_guard.snapshot, values["d1_snapshot"])
        now[0] += 60_001
        with self.assertRaisesRegex(BudgetBlocked, "EVIDENCE_STALE"):
            runtime.client._before_send()
        self.assertEqual(runtime.budget_guard.snapshot.measured_through_ms, NOW)
        self.assertEqual(runtime.d1_usage_guard.snapshot.measured_through_ms, NOW)
        self.assertEqual(runtime.budget_guard.attempted_usage().provider_requests, 0)

    def test_invalid_activation_flag_or_registry_prevents_credentials(self):
        with self.assertRaises(ValueError):
            build_runtime_composition(**inputs(), construction_enabled=1)
        values = inputs()
        values["strategy_registry"]["automatic_promotion"] = True
        with patch(f"{MODULE}.os.environ.get") as environment:
            with self.assertRaisesRegex(CloudCandidateRegistryBlocked, "AUTHORITY_INVALID"):
                build_runtime_composition(**values, construction_enabled=True)
        environment.assert_not_called()


    def test_assembled_transport_and_r2_complete_a_no_trade_slot_without_network(self):
        # Reuse the established composition fixture; its market and ledger are
        # synthetic. Exercise real parsers, JSON store, budget hooks and writer.
        spec = importlib.util.spec_from_file_location(
            "runtime_assembly_fixture", ROOT / "tests/test_cloud_paper_composition_v0_1.py",
        )
        fixture = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = fixture
        spec.loader.exec_module(fixture)
        sdk = _MemoryS3Client()
        ledger = fixture.FakeReservationLedger()
        values = inputs()
        values["clock_ms"] = lambda: fixture.NOW
        for key in ("r2_snapshot", "d1_snapshot"):
            values[key] = replace(
                values[key], observed_at_ms=fixture.NOW, measured_through_ms=fixture.NOW,
            )
        def r2_factory(**kwargs):
            return BudgetedR2Store(
                client=sdk, bucket="synthetic-only",
                budget_guard=kwargs["budget_guard"],
                freshness_check=kwargs["freshness_check"],
            )
        responses = {
            "/api/v1/common/symbols": {"symbols": [{"symbol": "BTC_USDT_PERP"}]},
            "/api/v1/market/tickers": {"tickers": [{
                "symbol": "BTC_USDT_PERP", "close": 340, "volume": 1000,
                "amount": 1_000_000, "count": 100,
            }]},
            "/api/v1/market/bookTickers": {"tickers": [{
                "symbol": "BTC_USDT_PERP", "bidPrice": 340, "askPrice": 340.1,
                "bidSize": 10, "askSize": 10, "timestamp": fixture.NOW,
            }]},
            "/api/v1/market/klines": {"klines": [{
                "time": candle.time_ms, "open": candle.open, "high": candle.high,
                "low": candle.low, "close": candle.close, "volume": candle.volume,
            } for candle in fixture.bars()]},
        }
        from urllib.parse import urlparse
        from test_cloud_paper_pionex_transport_v0_1 import Response
        def send(request, **kwargs):
            data = responses[urlparse(request.full_url).path]
            return Response(json.dumps({"result": True, "data": data}).encode())
        opener = Mock()
        opener.open.side_effect = send
        with patch(f"{MODULE}.BudgetedR2Store.from_credentials", side_effect=r2_factory):
            with patch(f"{MODULE}.CloudflareD1QueryClient.from_environment"):
                with patch(f"{MODULE}.D1CloudBudgetLedger", return_value=ledger):
                    with patch(f"{MODULE}.os.environ.get", return_value="synthetic-only"):
                        runtime = build_runtime_composition(
                            **values, construction_enabled=True,
                        )
        with patch.object(runtime.client, "_pace"), patch(
            "crypto_autopilot.paper.cloud_pionex_client_v0_1.build_opener",
            return_value=opener,
        ):
            report = runtime.run_slot(
                tick_ms=fixture.NOW, previous_slot=None,
                run_id="synthetic-assembly", activation_enabled=True,
            )
            provider_calls = opener.open.call_count
            r2_calls = len(sdk.calls)
            with self.assertRaisesRegex(BudgetBlocked, "RESERVATION_REJECTED"):
                runtime.run_slot(
                    tick_ms=fixture.NOW, previous_slot=None,
                    run_id="synthetic-duplicate", activation_enabled=True,
                )
        self.assertEqual(report["state"], "NO_TRADE")
        self.assertEqual(report["account"]["initial_equity_usd"], 10_000)
        self.assertEqual(report["account"]["open_position_count"], 0)
        self.assertEqual(provider_calls, 0)
        self.assertEqual(opener.open.call_count, provider_calls)
        self.assertEqual(len(sdk.calls), r2_calls)
        self.assertTrue(sdk.objects)
        self.assertEqual(len(ledger.settlements), 1)
        usage = runtime.budget_guard.attempted_usage()
        self.assertEqual(usage.provider_requests, provider_calls)
        self.assertEqual(usage.class_a_requests, sum(
            call["operation"] in {"PUT", "LIST"} for call in sdk.calls
        ))
        self.assertEqual(usage.class_b_requests, sum(
            call["operation"] == "GET" for call in sdk.calls
        ))


if __name__ == "__main__":
    unittest.main()
