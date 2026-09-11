from datetime import datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest import mock
from urllib.request import Request
import zipfile

from crypto_autopilot.backtest import BacktestMetrics, BacktestResult
from test_simulation_funding_v0_1 import encoded_kline_sample, funding_report

SPEC = importlib.util.spec_from_file_location(
    "btc_execution", Path(__file__).resolve().parents[1] / "scripts/run_simulation_btc_v0_1.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class BtcExecutionTests(unittest.TestCase):
    def setUp(self):
        self.config, self.receipt = module.load_authority()
        self.env = {"GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": module.REPOSITORY,
                    "GITHUB_REF": "refs/heads/main", "GITHUB_RUN_ATTEMPT": "1",
                    "GITHUB_EVENT_NAME": "workflow_run", "GITHUB_SHA": "a" * 40,
                    "GITHUB_RUN_NUMBER": "1", "GITHUB_RUN_ID": "123"}
        self.event = {"workflow_run": {"name": "CI", "event": "push",
                      "status": "completed", "conclusion": "success", "head_branch": "main",
                      "head_repository": {"full_name": module.REPOSITORY}, "head_sha": "a" * 40}}
        self.now = datetime(2026, 9, 12, tzinfo=timezone.utc)

    def sample_reader(self):
        payloads, receipt = encoded_kline_sample()
        by_key = {row["key"]: payloads[row["interval"]] for row in receipt["intervals"]}
        calls = []

        def read(key, size):
            calls.append(key)
            return by_key[key]

        return receipt, read, calls

    def test_context_requires_fresh_current_main_ci_within_budget_and_window(self):
        module.require_context(self.config, self.env, self.event, self.now)
        for key, value in [("GITHUB_RUN_ATTEMPT", "2"), ("GITHUB_RUN_NUMBER", "21"),
                           ("GITHUB_REF", "refs/heads/feature"), ("GITHUB_SHA", "b" * 40)]:
            with self.assertRaises(ValueError):
                module.require_context(self.config, {**self.env, key: value}, self.event, self.now)
        with self.assertRaises(ValueError):
            module.require_context(self.config, self.env, self.event,
                                   datetime(2026, 9, 16, tzinfo=timezone.utc))
        self.event["workflow_run"]["event"] = "pull_request"
        with self.assertRaises(ValueError):
            module.require_context(self.config, self.env, self.event, self.now)

    def test_funding_archive_hash_and_run_identity_are_verified(self):
        report = funding_report()
        report["observations"] = report["observations"][::32]
        report["observation_count"] = len(report["observations"])
        report["last_time_ms"] = report["observations"][-1]["funding_time_ms"]
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("report.json", json.dumps(report))
        payload = stream.getvalue()
        config = {**self.config, "funding_zip_sha256": module.digest(payload),
                  "funding_run_id": report["run_id"]}
        self.assertEqual(module.funding_from_zip(payload, config), report)
        with self.assertRaises(ValueError):
            module.funding_from_zip(payload + b"changed", config)
        with self.assertRaises(ValueError):
            module.funding_from_zip(payload, {**config, "funding_run_id": "wrong"})

    def test_redirect_drops_token_and_rejects_plain_http(self):
        redirect = module.ArtifactRedirect()
        request = Request("https://api.github.com/archive", headers={"Authorization": "Bearer TEST"})
        result = redirect.redirect_request(request, None, 302, "", {}, "https://storage.example/archive")
        self.assertIsNone(result.get_header("Authorization"))
        with self.assertRaises(ValueError):
            redirect.redirect_request(request, None, 302, "", {}, "http://storage.example/archive")

    def test_exact_three_reads_then_canonical_simulation_never_claims_full_universe(self):
        receipt, read, calls = self.sample_reader()
        result = module.simulate(self.config, receipt, funding_report(), read)
        self.assertEqual(len(calls), 3)
        self.assertEqual(result["status"], "READY")
        self.assertFalse(result["full_universe_ready"])
        self.assertGreater(result["executed_trade_count"], 0)
        self.assertNotIn("production_simulation_data_admission_not_authorized", result["blockers"])
        self.assertEqual(result["outcome"]["state"], "TRADES_EXECUTED")
        self.assertTrue(result["outcome"]["simulation_result_available"])

        controls = result["controls"]
        self.assertFalse(controls["kill_switch"]["configured"])
        self.assertIsNone(controls["kill_switch"]["time_ms"])
        self.assertIsInstance(controls["kill_switch"]["triggered"], bool)
        self.assertTrue(controls["max_holding"]["configured"])
        self.assertEqual(controls["max_holding"]["minutes"], 720)
        self.assertIsInstance(controls["max_holding"]["triggered"], bool)

        summary = result["financial_summary"]
        self.assertTrue(summary["available"])
        expected_gross = round(
            sum(trade["gross_pnl_usd"] for trade in result["result"]["trades"]), 8
        )
        self.assertEqual(summary["gross_pnl_usd"], expected_gross)
        self.assertEqual(summary["net_pnl_usd"], result["result"]["metrics"]["net_pnl_usd"])
        self.assertEqual(
            summary["max_drawdown_pct"], result["result"]["metrics"]["max_drawdown_pct"]
        )

    def test_no_signal_uses_explicit_unavailable_financial_schema(self):
        receipt, read, _ = self.sample_reader()
        no_signal = {
            "status": "FUNDING_PIPELINE_NOT_EXERCISED_NO_SIGNAL",
            "data_ready": True,
            "funding_data_ready": True,
            "pipeline_exercised": False,
            "full_simulation_ready": False,
            "generated_plan_count": 0,
            "executed_trade_count": 0,
            "funding_observation_count": 81,
            "blockers": [
                "no_candle_derived_strategy_signal",
                "production_simulation_data_admission_not_authorized",
            ],
        }
        with mock.patch.object(module, "run_readiness_with_verified_funding", return_value=no_signal):
            result = module.simulate(self.config, receipt, funding_report(), read)
        self.assertEqual(result["status"], "NOT_READY")
        self.assertEqual(result["outcome"]["state"], "NO_SIGNAL")
        self.assertFalse(result["outcome"]["simulation_result_available"])
        self.assertEqual(result["outcome"]["generated_plan_count"], 0)
        self.assertEqual(result["outcome"]["executed_trade_count"], 0)
        self.assertEqual(result["outcome"]["rejected_plan_count"], 0)
        self.assertFalse(result["financial_summary"]["available"])
        self.assertIsNone(result["financial_summary"]["gross_pnl_usd"])
        self.assertIsNone(result["financial_summary"]["net_pnl_usd"])
        self.assertIsNone(result["controls"]["kill_switch"]["triggered"])
        self.assertIsNone(result["controls"]["max_holding"]["triggered"])

    def test_no_trade_zeroes_are_measured_not_missing(self):
        receipt, read, _ = self.sample_reader()
        metrics = BacktestMetrics(
            trade_count=0,
            win_count=0,
            loss_count=0,
            win_rate=0.0,
            net_pnl_usd=0.0,
            return_pct=0.0,
            max_drawdown_pct=0.0,
            profit_factor=None,
            trade_sharpe=None,
            total_fees_usd=0.0,
            total_funding_usd=0.0,
            total_slippage_cost_usd=0.0,
        )
        measured_empty = BacktestResult(
            initial_equity_usd=100.0,
            final_equity_usd=100.0,
            trades=(),
            events=(),
            rejected_plans=(("plan-1", "daily_entry_limit"),),
            equity_curve=(100.0,),
            metrics=metrics,
        )
        bridge = {
            "status": "FUNDING_PIPELINE_NOT_EXERCISED",
            "data_ready": True,
            "funding_data_ready": True,
            "pipeline_exercised": False,
            "full_simulation_ready": False,
            "generated_plan_count": 1,
            "executed_trade_count": 0,
            "rejected_plan_count": 1,
            "funding_observation_count": 81,
            "blockers": ["production_simulation_data_admission_not_authorized"],
            "result": measured_empty,
        }
        with mock.patch.object(module, "run_readiness_with_verified_funding", return_value=bridge):
            result = module.simulate(self.config, receipt, funding_report(), read)
        self.assertEqual(result["outcome"]["state"], "NO_TRADE")
        self.assertTrue(result["outcome"]["simulation_result_available"])
        self.assertTrue(result["financial_summary"]["available"])
        self.assertEqual(result["financial_summary"]["gross_pnl_usd"], 0.0)
        self.assertEqual(result["financial_summary"]["net_pnl_usd"], 0.0)

    def test_execution_failure_schema_uses_nulls_not_fake_zeroes(self):
        report = module.base_report()
        failure = "execution_failed_ValueError"
        report["blockers"] = [failure]
        report["outcome"] = module.outcome_summary("EXECUTION_FAILED", reason=failure)
        report["controls"] = module.controls_summary(None)
        report["financial_summary"] = module.financial_summary(None)

        self.assertEqual(report["outcome"]["state"], "EXECUTION_FAILED")
        self.assertFalse(report["outcome"]["simulation_result_available"])
        self.assertIsNone(report["outcome"]["generated_plan_count"])
        self.assertIsNone(report["outcome"]["executed_trade_count"])
        self.assertIsNone(report["outcome"]["rejected_plan_count"])
        self.assertFalse(report["financial_summary"]["available"])
        for key, value in report["financial_summary"].items():
            if key != "available":
                self.assertIsNone(value, key)

    def test_corrupt_sample_stops_before_later_objects(self):
        calls = []

        def read(key, size):
            calls.append(key)
            return b"wrong"

        with self.assertRaises(ValueError):
            module.simulate(self.config, self.receipt, funding_report(), read)
        self.assertEqual(len(calls), 1)
