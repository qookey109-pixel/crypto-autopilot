from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from crypto_autopilot.backtest import BacktestMetrics, BacktestResult, BacktestTrade
from crypto_autopilot.strategy_edge_validation import (
    StrategyEdgeInput,
    TrialRegistryEvidence,
    input_fingerprint,
)
from crypto_autopilot.strategy_research_loop import (
    StrategyResearchLoopError,
    audit_paper_performance,
    build_candidate_registry,
    compose_research_evidence,
    paper_ledger_from_backtest_result,
    paper_ledger_from_dict,
    policy_from_config,
)


ROOT = Path(__file__).parents[1]
CONFIG_PATH = ROOT / "config/strategy_research_loop_v0_1.json"


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _ledger_payload(*, count: int = 40, concentrated: bool = False) -> dict[str, object]:
    registry = build_candidate_registry(_config())
    trades: list[dict[str, object]] = []
    for index in range(count):
        if concentrated and index == 0:
            net = 1_000.0
        else:
            net = 30.0 if index % 5 else -20.0
        fees = 1.0
        trades.append(
            {
                "trade_id": f"trade-{index:03d}",
                "symbol": "BTCUSDT" if index % 2 else "ETHUSDT",
                "side": "LONG" if index % 3 else "SHORT",
                "entry_time_ms": 1_700_000_000_000 + index * 86_400_000,
                "exit_time_ms": 1_700_000_000_000 + index * 86_400_000 + 43_200_000,
                "gross_pnl_usd": net + fees,
                "fees_usd": fees,
                "funding_usd": 0.0,
                "slippage_cost_usd": 0.5,
                "net_pnl_usd": net,
                "initial_risk_usd": 100.0,
            }
        )
    base = {
        "provider": "synthetic_fixture",
        "source_role": "SYNTHETIC_FIXTURE",
        "currency": "USD",
        "initial_equity_usd": 10_000.0,
        "candidate_id": registry.candidates[0].candidate_id,
        "registry_sha256": registry.registry_sha256,
        "edge_input_fingerprint": "a" * 64,
        "complete": True,
        "trades": trades,
    }
    return {
        "schema": "qookey-paper-performance-ledger-v0.1",
        **base,
        "ledger_sha256": _canonical_sha256(base),
        "authority": {
            "provider_data_fetched": False,
            "r2_accessed": False,
            "holdout_accessed": False,
            "trade_plan_authorized": False,
            "live_trading_authorized": False,
        },
    }


class CandidateRegistryTests(unittest.TestCase):
    def test_registry_is_deterministic_bounded_and_complete(self) -> None:
        first = build_candidate_registry(_config())
        second = build_candidate_registry(_config())
        self.assertEqual(first, second)
        self.assertEqual(len(first.candidates), 120)
        self.assertEqual(len({candidate.candidate_id for candidate in first.candidates}), 120)
        self.assertEqual(first.report()["status"], "PREPARED_NOT_EXECUTED")
        self.assertFalse(first.report()["authority"]["trade_plan_authorized"])

    def test_hard_cap_fails_closed(self) -> None:
        payload = _config()
        payload["candidate_search"]["hard_candidate_cap"] = 100
        with self.assertRaisesRegex(StrategyResearchLoopError, "hard cap"):
            build_candidate_registry(payload)

    def test_expected_candidate_count_fails_closed(self) -> None:
        payload = _config()
        payload["candidate_search"]["expected_candidate_count"] = 119
        with self.assertRaisesRegex(StrategyResearchLoopError, "frozen expectation"):
            build_candidate_registry(payload)

    def test_versioned_config_has_zero_authority(self) -> None:
        payload = _config()
        policy = policy_from_config(payload)
        self.assertEqual(payload["status"], "PREPARED_RESEARCH_ONLY")
        self.assertEqual(policy.minimum_trades, 30)
        self.assertFalse(payload["execution"]["production_dataset_execution_authorized"])
        self.assertFalse(payload["authority"]["replacement_holdout_access_authorized"])
        self.assertEqual(payload["authority"]["model_promotion_authority"], 0)


class PaperAuditTests(unittest.TestCase):
    def test_complete_cost_ledger_is_deterministic_and_acceptable(self) -> None:
        ledger = paper_ledger_from_dict(_ledger_payload())
        first = audit_paper_performance(ledger, policy_from_config(_config()))
        second = audit_paper_performance(ledger, policy_from_config(_config()))
        self.assertEqual(first, second)
        self.assertEqual(first["state"], "ACCEPTABLE_FOR_CONTINUED_PAPER_RESEARCH")
        self.assertGreater(first["metrics"]["expectancy_r"], 0)
        self.assertEqual(first["monte_carlo"]["samples"], 999)
        self.assertEqual(first["authority"]["model_promotion_authority"], 0)

    def test_small_ledger_is_insufficient_sample(self) -> None:
        ledger = paper_ledger_from_dict(_ledger_payload(count=10))
        report = audit_paper_performance(ledger, policy_from_config(_config()))
        self.assertEqual(report["state"], "INSUFFICIENT_SAMPLE")

    def test_winner_concentration_is_fragile(self) -> None:
        ledger = paper_ledger_from_dict(_ledger_payload(concentrated=True))
        report = audit_paper_performance(ledger, policy_from_config(_config()))
        self.assertEqual(report["state"], "FRAGILE_REVIEW_REQUIRED")
        self.assertIn("winner_concentration_above_maximum", report["reasons"])

    def test_non_synthetic_or_authorized_input_is_rejected(self) -> None:
        production = _ledger_payload()
        production["source_role"] = "PRODUCTION"
        with self.assertRaisesRegex(StrategyResearchLoopError, "SYNTHETIC_FIXTURE"):
            paper_ledger_from_dict(production)
        authorized = _ledger_payload()
        authorized["authority"]["r2_accessed"] = True
        with self.assertRaisesRegex(StrategyResearchLoopError, "zero data/trading authority"):
            paper_ledger_from_dict(authorized)

    def test_bad_accounting_or_hash_is_rejected(self) -> None:
        bad_accounting = _ledger_payload()
        bad_accounting["trades"][0]["net_pnl_usd"] += 1
        base = {key: value for key, value in bad_accounting.items() if key not in {"schema", "ledger_sha256", "authority"}}
        bad_accounting["ledger_sha256"] = _canonical_sha256(base)
        with self.assertRaisesRegex(StrategyResearchLoopError, "does not reconcile"):
            paper_ledger_from_dict(bad_accounting)
        bad_hash = _ledger_payload()
        bad_hash["ledger_sha256"] = "b" * 64
        with self.assertRaisesRegex(StrategyResearchLoopError, "SHA-256 mismatch"):
            paper_ledger_from_dict(bad_hash)

    def test_existing_backtest_is_adapted_without_second_broker(self) -> None:
        trade = BacktestTrade(
            plan_id="p-1",
            symbol="BTCUSDT",
            signal_time_ms=0,
            entry_time_ms=1,
            exit_time_ms=2,
            raw_entry_price=100.0,
            entry_price=100.1,
            raw_exit_price=103.0,
            exit_price=102.9,
            quantity=1.0,
            risk_usd=10.0,
            notional_usd=100.1,
            gross_pnl_usd=2.8,
            fees_usd=0.1,
            funding_usd=0.0,
            slippage_cost_usd=0.2,
            net_pnl_usd=2.7,
            r_multiple=0.27,
            exit_reason="target",
        )
        metrics = BacktestMetrics(1, 1, 0, 1.0, 2.7, 0.027, 0.0, None, None, 0.1, 0.0, 0.2)
        result = BacktestResult(10_000.0, 10_002.7, (trade,), (), (), (10_000.0, 10_002.7), metrics)
        registry = build_candidate_registry(_config())
        payload = paper_ledger_from_backtest_result(
            result,
            provider="synthetic_fixture",
            candidate_id=registry.candidates[0].candidate_id,
            registry_sha256=registry.registry_sha256,
            edge_input_fingerprint="a" * 64,
        )
        ledger = paper_ledger_from_dict(payload)
        self.assertEqual(ledger.trades[0].side, "LONG")
        self.assertEqual(payload["slippage_accounting"], "INCLUDED_IN_FILL_PRICES_AND_GROSS_PNL")


class CompositionTests(unittest.TestCase):
    def _evidence(self) -> tuple[object, StrategyEdgeInput, dict[str, object], dict[str, object]]:
        registry = build_candidate_registry(_config())
        ids = tuple(candidate.candidate_id for candidate in registry.candidates)
        edge_input = StrategyEdgeInput(
            provider="synthetic_fixture",
            selected_candidate_id=ids[0],
            candidate_ids=ids,
            update_returns_matrix=(tuple(0.001 for _ in ids),),
            update_benchmark_returns=(0.0,),
            validation_returns=(0.001,),
            validation_benchmark_returns=(0.0,),
            validation_market_returns=(0.001,),
            validation_positions=(1.0,),
            periods_per_year=365,
            trial_registry=TrialRegistryEvidence(True, ids, registry.registry_sha256),
            partition_integrity_passed=True,
            evaluation_integrity_sha256="c" * 64,
        )
        fingerprint = input_fingerprint(edge_input)
        ledger_payload = _ledger_payload()
        ledger_payload["edge_input_fingerprint"] = fingerprint
        base = {key: value for key, value in ledger_payload.items() if key not in {"schema", "ledger_sha256", "authority"}}
        ledger_payload["ledger_sha256"] = _canonical_sha256(base)
        audit = audit_paper_performance(
            paper_ledger_from_dict(ledger_payload), policy_from_config(_config())
        )
        edge_report = {
            "verdict": "PASS",
            "input_fingerprint": fingerprint,
            "provider": edge_input.provider,
            "selected_candidate_id": edge_input.selected_candidate_id,
        }
        return registry, edge_input, edge_report, audit

    def test_matching_edge_and_paper_evidence_reaches_human_review_only(self) -> None:
        registry, edge_input, edge_report, audit = self._evidence()
        report = compose_research_evidence(
            registry=registry,
            edge_input=edge_input,
            edge_report=edge_report,
            paper_audit=audit,
        )
        self.assertEqual(report["state"], "EVIDENCE_READY_FOR_HUMAN_REVIEW")
        self.assertEqual(report["authority"]["model_promotion_authority"], 0)
        self.assertFalse(report["authority"]["live_trading_authorized"])

    def test_lineage_mismatch_or_edge_failure_rejects(self) -> None:
        registry, edge_input, edge_report, audit = self._evidence()
        edge_report["verdict"] = "REJECT"
        report = compose_research_evidence(
            registry=registry,
            edge_input=edge_input,
            edge_report=edge_report,
            paper_audit=audit,
        )
        self.assertEqual(report["state"], "REJECT")
        self.assertIn("strategy_edge_verdict_not_pass", report["reasons"])


class ReceiptTests(unittest.TestCase):
    def test_preparation_receipt_binds_exact_artifact_bytes(self) -> None:
        receipt_path = ROOT / "research/receipts/2026-08-28-strategy-research-loop-v0-1-prepared.json"
        if not receipt_path.exists():
            self.skipTest("receipt is created after implementation hashes are frozen")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        for artifact in receipt["artifacts"].values():
            actual = hashlib.sha256(ROOT.joinpath(artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(actual, artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
