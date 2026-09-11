from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scripts.run_pionex_asset_classification_execution_v0_1 import (
    ClassificationExecutionRejected,
    CONFIG_SHA256,
    load_authority,
    require_execution_window,
    validate_universe_report,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/pionex_asset_classification_execution_v0_1.json"
VERIFIER = ROOT / "config/pionex_asset_classification_verifier_v0_1.json"
ALT = ROOT / "config/pionex_alternative_assets_v0_1.json"


def test_execution_config_is_exact_and_closed() -> None:
    raw = CONFIG.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == CONFIG_SHA256
    config = json.loads(raw)
    assert config["status"] == (
        "AUTHORIZED_AFTER_PROTECTED_MAIN_MERGE_MANUAL_CLASSIFICATION_ONLY"
    )
    assert config["universe_source"] == {
        "workflow": "Pionex Research Universe 150+ V0.1",
        "run_id": 34563615657,
        "run_attempt": 1,
        "head_sha": "6a7aad2aa4c9d8445209d77b32a4c1698d9984ef",
        "artifact_id": 10185197916,
        "artifact_name": "pionex-research-universe-v0-1-34563615657-1",
        "artifact_digest_sha256": (
            "997c99f495e423673e8550da083b15dfc1a2f146833f64efc3d7da227bda8c47"
        ),
        "report_path_after_download": "classification-input/report.json",
        "report_sha256": (
            "0f0694d660c52858f02e9dbd06bb5f8ae94f2885279656c0dafd91a00785ee68"
        ),
        "expected_status": "PASS",
        "expected_selected_market_count": 197,
        "expected_crypto_core_count": 100,
    }
    assert config["execution"]["provider_request_count_exact"] == 1
    assert config["execution"]["automatic_retries"] == 0
    assert config["authority"]["public_coinpaprika_metadata_read"] is True
    assert config["authority"]["github_actions_artifact_read"] is True
    assert config["authority"]["workflow_dispatch"] is True
    for key in (
        "automatic_schedule",
        "private_account_reads",
        "r2_read",
        "r2_write",
        "universe_membership_change",
        "historical_materialization",
        "holdout_access",
        "training",
        "automatic_model_promotion",
        "strategy_change",
        "source_switch",
        "trade_plan",
        "real_money_orders",
        "live_trading",
    ):
        assert config["authority"][key] is False


def test_authority_receipt_binds_config() -> None:
    config, verifier_bytes, alt_bytes = load_authority(CONFIG, VERIFIER, ALT)
    assert config["provider"]["endpoint"] == "https://api.coinpaprika.com/v1/coins"
    assert hashlib.sha256(verifier_bytes).hexdigest() == config["verifier_contract"][
        "sha256"
    ]
    assert alt_bytes


def test_universe_report_rejects_wrong_bytes() -> None:
    config = json.loads(CONFIG.read_text())
    with pytest.raises(ClassificationExecutionRejected, match="SHA-256 mismatch"):
        validate_universe_report(config, b"{}")


def test_execution_window_rejects_outside_bounds() -> None:
    config = json.loads(CONFIG.read_text())
    with pytest.raises(ClassificationExecutionRejected, match="execution window closed"):
        require_execution_window(config, observed_at=datetime(2026, 9, 16, tzinfo=UTC))
