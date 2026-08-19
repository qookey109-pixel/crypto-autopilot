from __future__ import annotations

import json
import unittest
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V0_1 = ROOT / "config" / "provider_equivalence_v0_1.json"
V0_2 = ROOT / "config" / "provider_equivalence_v0_2_draft.json"


def load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class ProviderEquivalenceV02DraftTests(unittest.TestCase):
    def test_draft_is_not_executable_or_authoritative(self) -> None:
        draft = load(V0_2)
        self.assertEqual(draft["status"], "PROTOCOL_DRAFT_NOT_AUTHORIZED")
        boundary = draft["authorization_boundary"]
        for key in (
            "protocol_frozen",
            "metadata_acquisition_authorized",
            "holdout_data_access_authorized",
            "holdout_evaluation_authorized",
            "source_switch_authorized",
            "provider_splicing_authorized",
            "staged_trade_kline_w1_materialization_authorized",
            "historical_universe_membership_authorized",
            "backtest_admission_authorized",
            "automatic_trade_plan_authorized",
            "real_money_order_authorized",
            "live_trading_authorized",
        ):
            self.assertIs(boundary[key], False, key)

    def test_candidate_holdout_is_predeclared_and_does_not_overlap_v0_1(self) -> None:
        v0_1 = load(V0_1)
        draft = load(V0_2)
        holdout = draft["candidate_holdout"]
        old_window = v0_1["overlap_window"]
        self.assertEqual(holdout["state"], "PREDECLARED_BUT_NOT_AUTHORIZED_FOR_ACCESS")
        self.assertIs(holdout["holdout_data_access_authorized"], False)
        self.assertIs(holdout["holdout_evaluation_authorized"], False)
        self.assertIs(holdout["holdout_result_known"], False)
        self.assertLess(utc(holdout["end_utc"]), utc(old_window["start_utc"]))
        self.assertEqual(holdout["candidate_symbol_count"], 15)
        self.assertEqual(holdout["mapped_pair_count"], 45)
        self.assertEqual(holdout["intervals"], ["15M", "60M", "4H"])

    def test_price_and_setup_thresholds_are_carried_from_v0_1_without_relaxation(self) -> None:
        v0_1 = load(V0_1)
        draft = load(V0_2)
        old_price = v0_1["price_metrics_bps"]
        new_price = draft["price_metrics_bps"]
        for metric in ("median_ohlc", "p95_open_close", "p95_high_low"):
            self.assertEqual(new_price[metric]["proposed_pass_max"], old_price[metric]["pass_max"])
            self.assertEqual(new_price[metric]["proposed_review_max"], old_price[metric]["review_max"])
        old_setup = v0_1["behavior_metrics"]["setup_60m_agreement"]
        new_setup = draft["setup_60m_metric"]
        self.assertEqual(new_setup["proposed_pass_min"], old_setup["pass_min"])
        self.assertEqual(new_setup["proposed_review_min"], old_setup["review_min"])
        self.assertEqual(new_setup["minimum_ready_bars"], old_setup["minimum_ready_bars"])
        self.assertEqual(new_setup["state"], old_setup["state"])

    def test_direction_design_requires_verified_increment_and_unresolved_cap_before_freeze(self) -> None:
        draft = load(V0_2)
        metric = draft["direction_metric_design"]
        self.assertEqual(metric["proposed_agreement_pass_min"], 0.98)
        self.assertEqual(metric["proposed_agreement_review_min"], 0.95)
        increment_rule = metric["verified_increment_rule"]
        self.assertIn("frozen price increment", increment_rule)
        self.assertIn("never infer", increment_rule)
        cap = metric["indeterminate_fraction_metric"]
        self.assertIsNone(cap["pass_max"])
        self.assertIsNone(cap["review_max"])
        self.assertEqual(cap["state"], "UNRESOLVED_MUST_FREEZE_BEFORE_HOLDOUT_ACCESS")
        prerequisite = draft["microstructure_metadata_prerequisite"]
        self.assertEqual(prerequisite["state"], "REQUIRED_BEFORE_PROTOCOL_FREEZE")
        self.assertIs(prerequisite["pionex_price_increment_authority_required"], True)
        self.assertIs(prerequisite["binance_price_increment_authority_required"], True)
        self.assertIs(prerequisite["raw_payload_sha256_receipts_required"], True)

    def test_v0_1_is_never_regraded(self) -> None:
        draft = load(V0_2)
        boundary = draft["v0_1_boundary"]
        self.assertEqual(boundary["frozen_gate_status"], "FAIL")
        self.assertIs(boundary["v0_1_thresholds_changed"], False)
        self.assertIs(boundary["v0_1_scope_changed"], False)
        self.assertIs(boundary["v0_1_regraded"], False)


if __name__ == "__main__":
    unittest.main()
