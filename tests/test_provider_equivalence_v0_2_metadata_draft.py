from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "config" / "provider_equivalence_v0_2_metadata_draft.json"
V0_2 = ROOT / "config" / "provider_equivalence_v0_2_draft.json"


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
        for key in (
            "metadata_protocol_frozen",
            "metadata_acquisition_authorized",
            "metadata_values_known",
            "holdout_data_access_authorized",
            "holdout_evaluation_authorized",
            "source_switch_authorized",
            "staged_trade_kline_w1_materialization_authorized",
            "backtest_admission_authorized",
            "trade_plan_authorized",
            "live_trading_authorized",
        ):
            self.assertIs(boundary[key], False, key)

    def test_binance_candidate_field_has_explicit_price_step_semantics(self) -> None:
        payload = load(METADATA)
        binance = payload["official_documentation_basis"]["binance_usdm"]
        self.assertEqual(binance["documented_filter"], "PRICE_FILTER")
        self.assertEqual(
            binance["price_increment_field"],
            "symbols[].filters[filterType=PRICE_FILTER].tickSize",
        )
        self.assertEqual(
            binance["field_semantics_status"],
            "OFFICIALLY_DEFINED_AS_PRICE_STEP_INTERVAL",
        )
        self.assertIs(
            binance["field_may_be_used_as_candidate_v0_2_increment_authority_after_RAW_RECEIPT"],
            True,
        )

    def test_pionex_quotestep_is_explicitly_blocked_until_semantics_are_proven(self) -> None:
        payload = load(METADATA)
        pionex = payload["official_documentation_basis"]["pionex"]
        self.assertEqual(pionex["candidate_price_increment_field"], "data.symbols[].quoteStep")
        self.assertEqual(
            pionex["candidate_field_semantics_status"],
            "FIELD_PRESENT_IN_OFFICIAL_SCHEMA_BUT_PRICE_INCREMENT_SEMANTICS_NOT_EXPLICITLY_DEFINED",
        )
        self.assertIs(pionex["candidate_field_may_be_used_as_v0_2_increment_authority"], False)
        resolution = payload["pionex_semantic_resolution"]
        self.assertEqual(resolution["state"], "BLOCKING_BEFORE_METADATA_AUTHORITY")
        self.assertIs(resolution["quoteStep_name_alone_is_sufficient_proof"], False)
        self.assertIs(resolution["observed_v0_1_price_deltas_may_define_increment"], False)
        self.assertIs(resolution["holdout_data_may_be_used_to_resolve_semantics_before_freeze"], False)

    def test_current_snapshot_does_not_prove_historical_holdout_applicability(self) -> None:
        payload = load(METADATA)
        applicability = payload["historical_applicability"]
        self.assertEqual(applicability["state"], "BLOCKING_BEFORE_V0_2_FREEZE")
        self.assertIs(applicability["current_metadata_snapshot_alone_proves_historical_effective_value"], False)
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
            "RESOLVE_PIONEX_QUOTESTEP_SEMANTICS_AND_HOLDOUT_APPLICABILITY_WITHOUT_OPENING_HOLDOUT",
        )


if __name__ == "__main__":
    unittest.main()
