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
        self.assertIs(boundary["metadata_field_semantics_frozen"], True)
        for key in (
            "protocol_frozen",
            "historical_metadata_values_authorized",
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

    def test_direction_design_requires_verified_increment_and_derived_evidence_floor(self) -> None:
        draft = load(V0_2)
        metric = draft["direction_metric_design"]
        self.assertEqual(metric["proposed_agreement_pass_min"], 0.98)
        self.assertEqual(metric["proposed_agreement_review_min"], 0.95)
        increment_rule = metric["verified_increment_rule"]
        self.assertIn("frozen price increment", increment_rule)
        self.assertIn("never infer", increment_rule)

        cap = metric["indeterminate_fraction_metric"]
        self.assertEqual(cap["state"], "RESOLVED_BY_UNCHANGED_V0_1_MINIMUM_ROW_REQUIREMENTS")
        self.assertIs(cap["separate_pass_review_thresholds_added"], False)
        self.assertIs(cap["derivation_uses_v0_1_mismatch_results"], False)
        self.assertEqual(
            cap["expected_candle_rows_in_exact_7d_holdout"],
            {"15M": 672, "60M": 168, "4H": 42},
        )
        self.assertEqual(
            cap["expected_adjacent_comparisons"],
            {"15M": 671, "60M": 167, "4H": 41},
        )
        self.assertEqual(
            cap["minimum_comparable_comparisons"],
            {"15M": 599, "60M": 149, "4H": 39},
        )
        self.assertEqual(
            cap["derived_max_indeterminate_count"],
            {"15M": 72, "60M": 18, "4H": 2},
        )
        for interval in ("15M", "60M", "4H"):
            expected = cap["expected_adjacent_comparisons"][interval]
            minimum = cap["minimum_comparable_comparisons"][interval]
            maximum = cap["derived_max_indeterminate_count"][interval]
            self.assertEqual(expected - minimum, maximum)

        prerequisite = draft["microstructure_metadata_prerequisite"]
        self.assertEqual(
            prerequisite["state"],
            "FIELD_SEMANTICS_PASS_HISTORICAL_VALUES_NOT_READY",
        )
        self.assertEqual(
            prerequisite["design_protocol"],
            "config/provider_equivalence_v0_2_metadata_draft.json",
        )
        self.assertEqual(
            prerequisite["semantic_authority"],
            "research/receipts/2026-08-19-provider-equivalence-v0-2-price-increment-semantics.json",
        )
        self.assertIs(prerequisite["pionex_price_increment_semantics_resolved"], True)
        self.assertIs(prerequisite["binance_price_increment_semantics_resolved"], True)
        self.assertIs(prerequisite["historical_increment_values_required"], True)
        self.assertIs(prerequisite["raw_payload_sha256_receipts_required"], True)

    def test_v0_2_remains_blocked_only_on_historical_increment_values(self) -> None:
        draft = load(V0_2)
        self.assertEqual(
            draft["aggregate_design"]["state"],
            "DRAFT_BLOCKED_ON_HISTORICAL_PRICE_INCREMENT_VALUES",
        )
        self.assertEqual(
            draft["next_required_stage"],
            "HISTORICAL_PRICE_INCREMENT_VALUE_APPLICABILITY_DESIGN_WITHOUT_OPENING_HOLDOUT",
        )
        self.assertIs(draft["hard_requirements"]["verified_price_increment_metadata_required"], True)
        self.assertIs(
            draft["hard_requirements"]["all_thresholds_and_metadata_contracts_must_be_frozen_before_holdout_access"],
            True,
        )

    def test_v0_1_is_never_regraded(self) -> None:
        draft = load(V0_2)
        boundary = draft["v0_1_boundary"]
        self.assertEqual(boundary["frozen_gate_status"], "FAIL")
        self.assertIs(boundary["v0_1_thresholds_changed"], False)
        self.assertIs(boundary["v0_1_scope_changed"], False)
        self.assertIs(boundary["v0_1_regraded"], False)


if __name__ == "__main__":
    unittest.main()
