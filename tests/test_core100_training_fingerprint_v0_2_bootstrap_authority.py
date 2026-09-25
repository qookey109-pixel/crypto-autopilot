import json
from pathlib import Path


def test_core100_v02_bootstrap_authority_is_exact_and_not_yet_active():
    config = json.loads(
        Path("config/core100_training_fingerprint_v0_2_bootstrap_authority_v0_1.json").read_text()
    )
    receipt = json.loads(
        Path("research/receipts/2026-09-25-core100-training-fingerprint-v0-2-bootstrap-authority.json").read_text()
    )
    assert config["status"] == "AUTHORIZED_NOT_ACTIVE"
    assert receipt["status"] == "AUTHORIZED_NOT_ACTIVE"
    assert config["user_authorization"]["decision"] == "AUTHORIZED"
    assert config["authorized_execution"]["one_time_bootstrap"] is True
    assert config["authorized_execution"]["required_input"] == {
        "name": "bootstrap_v0_2",
        "value": "true",
    }
    assert config["authorized_execution"]["github_run_attempt"] == 1
    assert config["authorized_execution"]["one_dispatch_guard"]["permission_scope"].startswith("actions:read only;")
    assert config["proposed_r2_access"]["writes_authorized_by_this_authority"] is True
    assert config["proposed_r2_access"]["headroom_gate_bytes"] == 8_000_000_000
    assert config["boundaries"]["provider_requests_authorized"] is False
    assert config["boundaries"]["replacement_holdout_access_authorized"] is False
    assert config["boundaries"]["source_switch_authorized"] is False
    assert config["boundaries"]["automatic_model_promotion_authorized"] is False
    assert config["boundaries"]["live_trading_authorized"] is False
    assert config["boundaries"]["local_files_or_local_runtime_authorized"] is False
    assert receipt["activation_gate"]["workflow_implementation_merged_to_main_required"] is True
    assert receipt["effects"]["r2_access_performed"] is False
