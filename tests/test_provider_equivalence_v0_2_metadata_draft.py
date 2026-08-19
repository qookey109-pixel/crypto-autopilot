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
    def test_metadata_protocol_is_design_only_and_cannot_open_holdout(self) -> None:
        payload = load(METADATA)
        self.assertEqual(payload["status"], "METADATA_PROTOCOL_DRAFT_NOT_AUTHORIZED")
        boundary = payload["authorization_boundary"]
        self.assertIs(boundary["field_semantics_authority_frozen"], True)
        for key in (
            "metadata_protocol_frozen",
            "metadata_acquisition_authorized",
            "metadata_values_known",
            "historical_metadata_values_authorized",
            "holdout_data_access_authorized",
            "holdout_evaluation_authorized",
            "source_switch_authorized",
            "staged_trade_kline_w1_materialization_authorized",
            "backtest_admission_authorized",
            "trade_plan_authorized",
            "live_trading_authorized",
        ):
            self.assertIs(boundary[key], False, key)

    def test_binance_field_semantics_are_resolved_but_value_authority_is_not(self) -> None:
        payload = load(METADATA)
        binance = payload["official_documentation_basis"]["binance_usdm"]
        self.assertEqual(binance["documented_filter"], "PRICE_FILTER")
        self.assertEqual(
            binance["price_increment_field"],
            "symbols[].filters[filterType=PRICE_FILTER].tickSize",
        )
        self.assertEqual(binance["field_semantics_status"], "PASS_EXPLICIT_PRICE_STEP_INTERVAL")
        self.assertIs(binance["field_semantics_authorized"], True)
        self.assertIs(binance["historical_field_value_authorized"], False)

    def test_pionex_quotestep_semantics_are_frozen_from_pre_holdout_official_openapi(self) -> None:
        payload = load(METADATA)
        pionex = payload["official_documentation_basis"]["pionex"]
        self.assertEqual(pionex["official_repository"], "pionex-official/pionex-open-api")
        self.assertEqual(pionex["official_file"], "openapi_futures.yaml")
        self.assertEqual(
            pionex["pre_holdout_commit"],
            "b8c63d29ed9b49d967b75b75b0c2ef057e45cc77",
        )
        self.assertEqual(
            pionex["pre_holdout_git_blob_sha1"],
            "46f9b20d5ab7946dcb11663913987a511ac5be10",
        )
        self.assertEqual(pionex["price_increment_field"], "data.symbols[].quoteStep")
        self.assertEqual(pionex["official_field_description"], "Price step size (quote asset)")
        self.assertEqual(
            pionex["field_semantics_status"],
            "PASS_EXPLICIT_PRICE_STEP_SIZE_IN_PRE_HOLDOUT_OFFICIAL_OPENAPI",
        )
        self.assertIs(pionex["field_semantics_authorized"], True)
        self.assertIs(pionex["historical_field_value_authorized"], False)

        resolution = payload["pionex_semantic_resolution"]
        self.assertEqual(resolution["state"], "PASS_FROZEN_SEMANTIC_AUTHORITY")
        self.assertIs(resolution["quoteStep_name_alone_is_sufficient_proof"], False)
        self.assertIs(resolution["pre_holdout_official_openapi_description_used"], True)
        self.assertIs(resolution["current_market_price_lattice_observation_used_as_authority"], False)
        self.assertIs(resolution["observed_v0_1_price_deltas_used_as_authority"], False)
        self.assertIs(resolution["holdout_data_used_to_resolve_semantics"], False)

    def test_semantics_receipt_preserves_v0_1_and_holdout_boundaries(self) -> None:
        receipt = load(SEMANTICS)
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(
            receipt["stage"],
            "PROVIDER_EQUIVALENCE_V0_2_PRICE_INCREMENT_SEMANTICS_PASS_VALUES_NOT_READY",
        )
        self.assertEqual(receipt["v0_1_boundary"]["frozen_gate_status"], "FAIL")
        self.assertIs(receipt["candidate_holdout_boundary"]["holdout_data_accessed"], False)
        self.assertIs(receipt["candidate_holdout_boundary"]["holdout_evaluated"], False)
        self.assertIs(receipt["candidate_holdout_boundary"]["holdout_result_known"], False)
        self.assertIs(receipt["semantic_result"]["pionex_quote_step_semantics_resolved"], True)
        self.assertIs(receipt["semantic_result"]["historical_value_applicability_ready"], False)

    def test_only_remaining_metadata_blocker_is_historical_value_applicability(self) -> None:
        payload = load(METADATA)
        applicability = payload["historical_applicability"]
        self.assertEqual(
            applicability["state"],
            "ONLY_REMAINING_BLOCKER_BEFORE_METADATA_VALUE_AUTHORITY",
        )
        self.assertIs(applicability["current_metadata_snapshot_alone_proves_historical_effective_value"], False)
        self.assertIs(applicability["m1a_artifact_contains_raw_symbols_response"], False)
        self.assertIs(applicability["holdout_candles_must_remain_unopened_during_resolution"], True)
        draft = load(V0_2)
        holdout = draft["candidate_holdout"]
        self.assertEqual(applicability["candidate_holdout_start_utc"], holdout["start_utc"])
        self.assertEqual(applicability["candidate_holdout_end_utc"], holdout["end_utc"])

    def test_future_acquisition_contract_is_fail_closed_and_public_only(self) -> None:
        payload = load(METADATA)
        contract = payload["future_acquisition_contract"]
        self.assertEqual(contract["state"], "DESIGN_ONLY_NOT_AUTHORIZED")
        self.assertIs(contract["public_endpoints_only"], True)
        self.assertIs(contract["private_api_key_forbidden"], True)
        self.assertIs(contract["raw_response_bytes_must_be_retained"], True)
        self.assertIs(contract["raw_payload_sha256_required"], True)
        self.assertIs(contract["all_15_symbols_required"], True)
        self.assertIs(contract["missing_symbol_fails_closed"], True)
        self.assertIs(contract["nonpositive_increment_fails_closed"], True)
        self.assertIs(contract["provider_splicing_forbidden"], True)
        self.assertIs(contract["value_interpolation_forbidden"], True)

    def test_next_stage_cannot_be_holdout_evaluation(self) -> None:
        payload = load(METADATA)
        self.assertEqual(
            payload["next_required_stage"],
            "RESOLVE_HISTORICAL_PRICE_INCREMENT_VALUE_APPLICABILITY_WITHOUT_OPENING_HOLDOUT",
        )


if __name__ == "__main__":
    unittest.main()
