from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "config" / "provider_equivalence_v0_2_metadata_draft.json"
V0_2 = ROOT / "config" / "provider_equivalence_v0_2_draft.json"
SEMANTICS = ROOT / "research" / "receipts" / "2026-08-19-provider-equivalence-v0-2-price-increment-semantics.json"


def load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


class ProviderEquivalenceV02MetadataDraftTests(unittest.TestCase):
    def test_field_semantics_remain_frozen(self) -> None:
        payload = load(METADATA)
        self.assertIs(payload["authorization_boundary"]["field_semantics_authority_frozen"], True)
        pionex = payload["official_documentation_basis"]["pionex"]
        self.assertEqual(pionex["official_field_description"], "Price step size (quote asset)")
        self.assertIs(pionex["field_semantics_authorized"], True)
        binance = payload["official_documentation_basis"]["binance_usdm"]
        self.assertEqual(binance["documented_filter"], "PRICE_FILTER")
        self.assertIs(binance["field_semantics_authorized"], True)
        receipt = load(SEMANTICS)
        self.assertEqual(receipt["status"], "PASS")

    def test_old_historical_value_attempt_is_superseded_without_candle_access(self) -> None:
        payload = load(METADATA)
        old = payload["superseded_historical_applicability_attempt"]
        self.assertEqual(old["state"], "SUPERSEDED_UNOPENED")
        self.assertIs(old["current_snapshot_backfill_forbidden"], True)
        self.assertIs(old["m1a_artifact_contains_raw_symbols_response"], False)
        self.assertIs(old["holdout_candles_accessed"], False)

    def test_forward_capture_window_matches_new_candidate_holdout(self) -> None:
        payload = load(METADATA)
        forward = payload["forward_applicability"]
        holdout = load(V0_2)["candidate_holdout"]
        self.assertEqual(forward["state"], "CAPTURE_PROTOCOL_FROZEN_VALUES_PENDING")
        self.assertEqual(forward["candidate_holdout_start_utc"], holdout["start_utc"])
        self.assertEqual(forward["candidate_holdout_end_utc"], holdout["end_utc"])
        self.assertEqual(forward["capture_start_utc"], "2026-08-20T00:00:00Z")
        self.assertEqual(forward["capture_end_utc"], "2026-08-28T01:59:59.999Z")
        self.assertEqual(forward["hourly_slot_count"], 194)
        self.assertIs(forward["invalid_result_authorizes_holdout_candles"], False)
        self.assertIs(forward["pass_result_authorizes_holdout_candles"], False)
        self.assertIs(forward["separate_holdout_access_authority_required_after_pass"], True)

    def test_capture_contract_is_public_fail_closed_and_candle_independent(self) -> None:
        contract = load(METADATA)["capture_contract"]
        self.assertIs(contract["public_endpoints_only"], True)
        self.assertIs(contract["private_provider_api_keys_forbidden"], True)
        self.assertIs(contract["raw_response_bytes_retained"], True)
        self.assertIs(contract["raw_payload_sha256_required"], True)
        self.assertIs(contract["all_15_symbols_required"], True)
        self.assertIs(contract["missing_symbol_fails_closed"], True)
        self.assertIs(contract["nonpositive_increment_fails_closed"], True)
        self.assertIs(contract["provider_splicing_forbidden"], True)
        self.assertIs(contract["value_interpolation_forbidden"], True)
        self.assertIs(contract["candle_inference_forbidden"], True)

    def test_capture_authority_does_not_open_holdout(self) -> None:
        boundary = load(METADATA)["authorization_boundary"]
        self.assertIs(boundary["metadata_capture_protocol_frozen"], True)
        self.assertIs(boundary["metadata_capture_authorized"], True)
        self.assertIs(boundary["metadata_only_r2_writes_authorized"], True)
        self.assertIs(boundary["metadata_values_complete"], False)
        self.assertIs(boundary["metadata_applicability_pass"], False)
        self.assertIs(boundary["holdout_data_access_authorized"], False)
        self.assertIs(boundary["holdout_evaluation_authorized"], False)
        self.assertIs(boundary["source_switch_authorized"], False)
        self.assertIs(boundary["staged_trade_kline_w1_materialization_authorized"], False)
        self.assertIs(boundary["live_trading_authorized"], False)


if __name__ == "__main__":
    unittest.main()
