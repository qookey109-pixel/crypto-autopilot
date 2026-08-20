from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "research/receipts/2026-08-20-provider-equivalence-v0-11-metadata-stability-evaluator-prepared.json"
CONFIG = ROOT / "config/provider_equivalence_v0_11_metadata_stability_evaluation_v0_1.json"
WORKFLOW = ROOT / ".github/workflows/validate-v0-11-metadata-stability-evaluator.yml"


def test_prepared_receipt_freezes_rules_without_claiming_production_evidence() -> None:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    config = json.loads(CONFIG.read_text(encoding="utf-8"))

    assert receipt["status"] == "PREPARED_EXECUTION_NOT_AUTHORIZED"
    assert receipt["stage"] == "PROVIDER_EQUIVALENCE_V0_11_METADATA_STABILITY_EVALUATOR_PREPARED_BEFORE_PRODUCTION_EVIDENCE"
    assert receipt["authority_type"] == "EVALUATOR_PROTOCOL_AND_IMPLEMENTATION_PREPARATION_ONLY"
    assert receipt["frozen_evaluation_contract"]["expected_hourly_slot_count"] == 194
    assert receipt["frozen_evaluation_contract"]["post_hoc_deadband_authorized"] is False
    assert receipt["frozen_evaluation_contract"]["post_hoc_symbol_scope_change_authorized"] is False
    assert receipt["frozen_evaluation_contract"]["post_hoc_provider_splicing_authorized"] is False
    assert receipt["preparation_execution"]["production_r2_listing_performed"] is False
    assert receipt["preparation_execution"]["production_r2_receipt_reads_performed"] == 0
    assert receipt["preparation_execution"]["provider_requests_performed"] == 0
    assert receipt["preparation_execution"]["render_requests_performed"] == 0
    assert receipt["preparation_execution"]["holdout_candles_accessed"] is False
    assert receipt["preparation_execution"]["holdout_evaluated"] is False
    assert receipt["preparation_execution"]["production_metadata_stability_result_known"] is False
    assert receipt["execution_boundary"]["v0_11_production_evaluation_authorized"] is False
    assert receipt["execution_boundary"]["r2_client_construction_authorized"] is False
    assert receipt["execution_boundary"]["r2_receipt_reads_authorized"] is False
    assert receipt["execution_boundary"]["holdout_candle_access_authorized"] is False
    assert receipt["execution_boundary"]["source_switch_authorized"] is False
    assert receipt["execution_boundary"]["live_trading_authorized"] is False
    assert receipt["interpretation"]["this_receipt_is_a_metadata_stability_pass"] is False
    assert receipt["interpretation"]["this_receipt_authorizes_holdout_access"] is False
    assert receipt["interpretation"]["replacement_holdout_state"] == "FROZEN_UNOPENED"
    assert receipt["interpretation"]["metadata_stability_state"] == "NOT_YET_RUN"

    assert config["status"] == "EVALUATOR_PROTOCOL_FROZEN_EXECUTION_NOT_AUTHORIZED"
    assert config["execution_boundary"]["r2_receipt_reads_authorized_by_this_protocol"] is False


def test_validation_workflow_has_no_schedule_and_no_production_secret_binding() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert not any(line == "  schedule:" for line in workflow.splitlines())
    assert "secrets.R2_ACCESS_KEY_ID" not in workflow
    assert "secrets.R2_SECRET_ACCESS_KEY" not in workflow
    assert "secrets.CLOUDFLARE_ACCOUNT_ID" not in workflow
    assert "secrets.R2_BUCKET_NAME" not in workflow
    assert "secrets.METADATA_RELAY_TOKEN" not in workflow
