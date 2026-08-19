from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V0_1 = ROOT / "config" / "provider_equivalence_v0_1.json"
V0_2 = ROOT / "config" / "provider_equivalence_v0_2_draft.json"
CAPTURE = ROOT / "config" / "provider_equivalence_v0_2_metadata_capture_v0_1.json"
CAPTURE_AUTHORITY = ROOT / "research" / "receipts" / "2026-08-19-provider-equivalence-v0-2-forward-metadata-capture-authority.json"


def load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


class ProviderEquivalenceV02DraftTests(unittest.TestCase):
    def test_v0_1_remains_frozen_fail(self) -> None:
        draft = load(V0_2)
        boundary = draft["v0_1_boundary"]
        self.assertEqual(boundary["frozen_gate_status"], "FAIL")
        self.assertIs(boundary["v0_1_thresholds_changed"], False)
        self.assertIs(boundary["v0_1_scope_changed"], False)
        self.assertIs(boundary["v0_1_regraded"], False)

    def test_old_holdout_is_superseded_unopened(self) -> None:
        draft = load(V0_2)
        old = draft["superseded_candidate_holdout"]
        self.assertEqual(old["state"], "SUPERSEDED_UNOPENED_BEFORE_ANY_EVIDENCE")
        self.assertEqual(old["start_utc"], "2026-08-03T08:00:00Z")
        self.assertEqual(old["end_utc"], "2026-08-10T07:59:59.999Z")
        self.assertIs(old["holdout_data_accessed"], False)
        self.assertIs(old["holdout_evaluated"], False)
        self.assertIs(old["holdout_result_known"], False)

    def test_new_forward_holdout_is_frozen_but_candles_forbidden(self) -> None:
        draft = load(V0_2)
        holdout = draft["candidate_holdout"]
        self.assertEqual(holdout["state"], "FROZEN_UNOPENED_FORWARD_CANDIDATE")
        self.assertEqual(holdout["start_utc"], "2026-08-21T00:00:00Z")
        self.assertEqual(holdout["end_utc"], "2026-08-27T23:59:59.999Z")
        self.assertEqual(holdout["candidate_symbol_count"], 15)
        self.assertEqual(holdout["mapped_pair_count"], 45)
        self.assertEqual(holdout["intervals"], ["15M", "60M", "4H"])
        self.assertIs(holdout["holdout_data_access_authorized"], False)
        self.assertIs(holdout["holdout_evaluation_authorized"], False)
        self.assertIs(holdout["holdout_result_known"], False)

    def test_v0_1_price_and_setup_thresholds_remain_unchanged(self) -> None:
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

    def test_capture_protocol_is_frozen_metadata_only(self) -> None:
        protocol = load(CAPTURE)
        self.assertEqual(protocol["status"], "PROTOCOL_FROZEN_BEFORE_METADATA_EVIDENCE")
        window = protocol["metadata_capture_window"]
        self.assertEqual(window["start_utc"], "2026-08-20T00:00:00Z")
        self.assertEqual(window["end_utc"], "2026-08-28T01:59:59.999Z")
        self.assertEqual(window["hourly_slot_count"], 194)
        self.assertEqual(window["scheduled_minutes_utc"], [17, 47])
        self.assertEqual(window["nominal_capture_attempts"], 388)
        storage = protocol["storage"]
        self.assertEqual(storage["projected_max_new_object_count"], 1164)
        self.assertLess(
            storage["current_bucket_usage_reference_bytes"] + storage["projected_metadata_storage_cap_bytes"],
            storage["existing_project_storage_block_guardrail_bytes"],
        )
        boundary = protocol["authorization_boundary"]
        self.assertIs(boundary["metadata_capture_authorized"], True)
        self.assertIs(boundary["metadata_only_r2_writes_authorized"], True)
        self.assertIs(boundary["holdout_candle_access_authorized"], False)
        self.assertIs(boundary["holdout_evaluation_authorized"], False)
        self.assertIs(boundary["source_switch_authorized"], False)
        self.assertIs(boundary["live_trading_authorized"], False)

    def test_capture_authority_does_not_authorize_holdout_or_w1(self) -> None:
        authority = load(CAPTURE_AUTHORITY)
        self.assertEqual(authority["status"], "PASS")
        self.assertEqual(
            authority["stage"],
            "PROVIDER_EQUIVALENCE_V0_2_FORWARD_METADATA_CAPTURE_AUTHORIZED_HOLDOUT_CANDLES_FORBIDDEN",
        )
        old = authority["supersession"]
        self.assertIs(old["old_holdout_candles_accessed"], False)
        new = authority["new_frozen_candidate_holdout"]
        self.assertIs(new["candles_accessed"], False)
        blocked = authority["explicitly_not_authorized"]
        self.assertIs(blocked["holdout_candle_access_authorized"], False)
        self.assertIs(blocked["holdout_evaluation_authorized"], False)
        self.assertIs(blocked["staged_trade_kline_w1_materialization_authorized"], False)
        self.assertIs(blocked["source_switch_authorized"], False)
        self.assertIs(blocked["live_trading_authorized"], False)

    def test_indeterminate_floor_is_not_tuned_on_v0_1_results(self) -> None:
        metric = load(V0_2)["direction_metric_design"]["indeterminate_fraction_metric"]
        self.assertEqual(metric["minimum_comparable_comparisons"], {"15M": 599, "60M": 149, "4H": 39})
        self.assertEqual(metric["derived_max_indeterminate_count"], {"15M": 72, "60M": 18, "4H": 2})
        self.assertIs(metric["derivation_uses_v0_1_mismatch_results"], False)


if __name__ == "__main__":
    unittest.main()
