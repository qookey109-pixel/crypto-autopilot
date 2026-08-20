from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone

from crypto_autopilot import provider_metadata_capture_v0_2 as v02
from crypto_autopilot import provider_metadata_stability_v0_11 as v11


def _vector(symbols: tuple[str, ...], *, increment: str = "0.01") -> list[dict[str, str]]:
    return [
        {
            "symbol": symbol,
            "price_increment": increment,
            "status": "TRADING",
            "contract_type": "PERPETUAL",
            "source_field": "fixture",
        }
        for symbol in sorted(symbols)
    ]


def _vector_sha(vector: list[dict[str, str]]) -> str:
    payload = json.dumps(vector, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _receipt(slot: str, run_id: int, *, pionex_increment: str = "0.01", binance_increment: str = "0.01") -> tuple[str, dict[str, object]]:
    config, _, pionex_symbols, binance_symbols = v11.validate_v0_11_protocol()
    namespace = str(config["input_contract"]["metadata_namespace"]).rstrip("/")
    slot_dt = datetime.fromisoformat(slot.replace("Z", "+00:00")).astimezone(timezone.utc)
    slot_id = slot_dt.strftime("%Y%m%dT%H0000Z")
    prefix = f"{namespace}/capture/slot={slot_id}/run={run_id}"
    pionex = _vector(pionex_symbols, increment=pionex_increment)
    binance = _vector(binance_symbols, increment=binance_increment)
    key = f"{prefix}/receipt.json"
    receipt: dict[str, object] = {
        "schema": v11.V0_10_RECEIPT_SCHEMA,
        "status": "PASS",
        "stage": v11.V0_10_CAPTURE_PASS_STAGE,
        "activation_authority": "provider_equivalence_v0_10_final_atomic_cutover_v0_1",
        "capture_execution_version": "v0_10",
        "slot_utc": slot,
        "observed_at_utc": slot_dt.replace(minute=17).isoformat(),
        "github_run_id": run_id,
        "github_sha": "fixture-v011",
        "transport": {
            "pionex": "github_hosted_direct_public_https",
            "binance_usdm": "render_free_web_service_v0_10_raw_relay",
            "render_region": "frankfurt",
            "render_plan": "free",
            "render_relay_path": "/metadata/v0-10/binance-exchange-info",
        },
        "providers": {
            "pionex": {
                "raw_key": f"{prefix}/pionex-symbols.json.gz",
                "normalized_vector_sha256": _vector_sha(pionex),
                "normalized_vector": pionex,
            },
            "binance_usdm": {
                "raw_key": f"{prefix}/binance-usdm-exchange-info.json.gz",
                "normalized_vector_sha256": _vector_sha(binance),
                "normalized_vector": binance,
            },
        },
        "authorization_boundary": {
            "metadata_only": True,
            "holdout_candle_access_authorized": False,
            "holdout_evaluation_authorized": False,
            "source_switch_authorized": False,
            "provider_splicing_authorized": False,
            "pionex_native_relabel_authorized": False,
            "w1_materialization_authorized": False,
            "automatic_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }
    return key, receipt


def _full_window() -> dict[str, dict[str, object]]:
    receipts: dict[str, dict[str, object]] = {}
    for index, slot in enumerate(v11.expected_slot_strings(), start=1):
        key, receipt = _receipt(slot, 700_000 + index)
        receipts[key] = receipt
    return receipts


def test_protocol_is_frozen_before_evidence_and_production_execution_is_disabled() -> None:
    config, _, pionex_symbols, binance_symbols = v11.validate_v0_11_protocol()
    assert config["status"] == "EVALUATOR_PROTOCOL_FROZEN_EXECUTION_NOT_AUTHORIZED"
    assert config["frozen_scope"]["expected_hourly_slot_count"] == 194
    assert config["frozen_scope"]["replacement_holdout_state"] == "FROZEN_UNOPENED"
    assert config["input_contract"]["raw_provider_objects_may_be_read_by_evaluator"] is False
    assert config["input_contract"]["holdout_objects_may_be_listed_or_read_by_evaluator"] is False
    assert config["execution_boundary"]["r2_receipt_reads_authorized_by_this_protocol"] is False
    assert config["execution_boundary"]["holdout_candle_access_authorized"] is False
    assert config["execution_boundary"]["live_trading_authorized"] is False
    assert v11.V0_11_R2_EVALUATION_EXECUTION_AUTHORIZED is False
    assert len(pionex_symbols) == 15
    assert len(binance_symbols) == 15


def test_expected_slots_are_exactly_the_frozen_194_hour_window() -> None:
    slots = v11.expected_slot_strings()
    assert len(slots) == 194
    assert slots[0] == "2026-08-27T00:00:00Z"
    assert slots[-1] == "2026-09-04T01:00:00Z"
    parsed = [datetime.fromisoformat(slot.replace("Z", "+00:00")) for slot in slots]
    assert all(right - left == timedelta(hours=1) for left, right in zip(parsed, parsed[1:]))


def test_complete_194_slot_exactly_stable_receipts_pass_without_emitting_values() -> None:
    result = v11.evaluate_receipt_set(_full_window())
    assert result["status"] == "PASS"
    assert result["stage"] == v11.V0_11_PASS_STAGE
    assert result["expected_slot_count"] == 194
    assert result["covered_slot_count"] == 194
    assert result["complete_valid_receipt_count"] == 194
    assert result["invalid_receipt_count"] == 0
    assert result["missing_slot_count"] == 0
    assert result["intra_slot_disagreement_count"] == 0
    assert result["cross_window_vector_drift_providers"] == []
    assert result["stable_provider_vector_sha256"]["pionex"]
    assert result["stable_provider_vector_sha256"]["binance_usdm"]
    assert result["increment_values_emitted"] is False
    assert result["raw_provider_responses_emitted"] is False
    assert result["holdout_candles_accessed"] is False
    assert result["holdout_evaluated"] is False
    assert result["holdout_access_authorized"] is False
    assert result["source_switch_authorized"] is False
    assert result["live_trading_authorized"] is False


def test_same_slot_duplicate_with_identical_vectors_is_allowed() -> None:
    receipts = _full_window()
    slot = v11.expected_slot_strings()[10]
    key, receipt = _receipt(slot, 999_001)
    receipts[key] = receipt
    result = v11.evaluate_receipt_set(receipts)
    assert result["status"] == "PASS"
    assert result["covered_slot_count"] == 194
    assert result["complete_valid_receipt_count"] == 195
    assert result["intra_slot_disagreement_count"] == 0


def test_missing_hour_fails_closed_and_never_authorizes_holdout() -> None:
    receipts = _full_window()
    missing_slot = v11.expected_slot_strings()[25]
    key_to_remove = next(key for key, value in receipts.items() if value["slot_utc"] == missing_slot)
    receipts.pop(key_to_remove)
    result = v11.evaluate_receipt_set(receipts)
    assert result["status"] == "FAIL"
    assert result["stage"] == v11.V0_11_FAIL_STAGE
    assert result["covered_slot_count"] == 193
    assert result["missing_slot_count"] == 1
    assert result["missing_slot_ids"] == [missing_slot]
    assert result["holdout_access_authorized"] is False


def test_cross_window_vector_drift_fails_closed() -> None:
    receipts = _full_window()
    drift_slot = v11.expected_slot_strings()[100]
    drift_key = next(key for key, value in receipts.items() if value["slot_utc"] == drift_slot)
    _, drifted = _receipt(drift_slot, int(receipts[drift_key]["github_run_id"]), pionex_increment="0.02")
    receipts[drift_key] = drifted
    result = v11.evaluate_receipt_set(receipts)
    assert result["status"] == "FAIL"
    assert result["cross_window_vector_drift_providers"] == ["pionex"]
    assert result["holdout_access_authorized"] is False


def test_same_slot_vector_disagreement_fails_closed() -> None:
    receipts = _full_window()
    slot = v11.expected_slot_strings()[50]
    key, receipt = _receipt(slot, 999_002, binance_increment="0.02")
    receipts[key] = receipt
    result = v11.evaluate_receipt_set(receipts)
    assert result["status"] == "FAIL"
    assert f"{slot}:binance_usdm" in result["intra_slot_disagreements"]
    assert "binance_usdm" in result["cross_window_vector_drift_providers"]
    assert result["holdout_access_authorized"] is False


def test_corrupt_vector_sha_is_invalid_receipt_and_fails_closed() -> None:
    receipts = _full_window()
    key = sorted(receipts)[0]
    corrupt = copy.deepcopy(receipts[key])
    corrupt["providers"]["pionex"]["normalized_vector_sha256"] = "0" * 64
    receipts[key] = corrupt
    result = v11.evaluate_receipt_set(receipts)
    assert result["status"] == "FAIL"
    assert result["invalid_receipt_count"] == 1
    assert result["missing_slot_count"] == 1
    assert key in result["invalid_receipt_keys"]


def test_receipt_claiming_holdout_access_is_invalid_and_fails_closed() -> None:
    receipts = _full_window()
    key = sorted(receipts)[1]
    invalid = copy.deepcopy(receipts[key])
    invalid["authorization_boundary"]["holdout_candle_access_authorized"] = True
    receipts[key] = invalid
    result = v11.evaluate_receipt_set(receipts)
    assert result["status"] == "FAIL"
    assert key in result["invalid_receipt_keys"]
    assert result["holdout_access_authorized"] is False


def test_wrong_namespace_receipt_key_is_invalid_and_cannot_pass() -> None:
    receipts = _full_window()
    original_key = sorted(receipts)[2]
    receipt = receipts.pop(original_key)
    wrong_key = original_key.replace("metadata/provider-equivalence/v0_7/", "holdout/provider-equivalence/")
    receipts[wrong_key] = receipt
    result = v11.evaluate_receipt_set(receipts)
    assert result["status"] == "FAIL"
    assert wrong_key in result["invalid_receipt_keys"]
    assert result["holdout_candles_accessed"] is False


def test_production_entrypoint_stops_before_r2_client_construction() -> None:
    store_called = False

    def forbidden_store():
        nonlocal store_called
        store_called = True
        raise AssertionError("V0.11 prepared evaluator constructed R2 before execution authority")

    result = v11.run_v0_11_r2_evaluation(store_factory=forbidden_store)
    assert result["status"] == "SKIP"
    assert result["stage"] == v11.V0_11_DISABLED_STAGE
    assert result["r2_client_constructed"] is False
    assert result["r2_receipt_reads_performed"] == 0
    assert result["r2_writes_performed"] is False
    assert result["provider_requests_performed"] == 0
    assert result["render_requests_performed"] == 0
    assert result["holdout_candles_accessed"] is False
    assert result["holdout_evaluated"] is False
    assert result["source_switch_authorized"] is False
    assert result["live_trading_authorized"] is False
    assert store_called is False


def test_v02_frozen_stability_semantics_are_not_rewritten() -> None:
    protocol, _, _ = v02.load_and_validate_authority()
    window = protocol["metadata_capture_window"]
    assert window["hourly_slot_count"] == 194
    assert window["required_coverage"] == "AT_LEAST_ONE_COMPLETE_VALID_CAPTURE_PER_UTC_HOURLY_SLOT"
    assert window["duplicate_capture_policy"] == "ALLOWED_ONLY_IF_NORMALIZED_15_SYMBOL_VECTORS_AGREE_WITHIN_SLOT"
    assert window["stability_policy"] == "ALL_COMPLETE_CAPTURE_VECTORS_ACROSS_THE_FULL_CAPTURE_WINDOW_MUST_MATCH_EXACTLY_PER_PROVIDER"
    assert window["missing_hour_policy"] == "METADATA_APPLICABILITY_INVALID_NO_HOLDOUT_EVALUATION"
    assert window["changed_vector_policy"] == "METADATA_APPLICABILITY_INVALID_NO_HOLDOUT_EVALUATION"
