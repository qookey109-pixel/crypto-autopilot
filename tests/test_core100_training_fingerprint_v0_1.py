from __future__ import annotations

import json
from pathlib import Path

from scripts import train_binance_detailed_history_models_v0_3 as trainer


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/core100_training_fingerprint_v0_1.json"
WORKFLOW = ROOT / ".github/workflows/binance-usdm-detailed-training-v0-1.yml"
BASELINE_DATASET = "91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876"
BASELINE_EXPERIMENT = "25b3178ce0d13052684d20b35a0e1f6949f0d97a5ac0c5b9e8f0a52d4d12f9c8"


def _config() -> dict[str, object]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_current_model_inputs_match_verified_successful_baseline() -> None:
    config = _config()
    trainer.validate_fingerprint_config(config)
    fingerprint, blobs = trainer.build_experiment_identity(
        dataset_fingerprint=BASELINE_DATASET,
        fingerprint_config=config,
    )
    assert fingerprint == BASELINE_EXPERIMENT
    assert blobs == config["baseline"]["model_affecting_git_blobs"]


def test_legacy_successful_latest_pointer_reuses_without_retraining() -> None:
    config = _config()
    latest = {
        "schema": "binance-usdm-intraday-research-training-latest-v0.1",
        "provider": "binance_usdm",
        "run_id": "github-34918219864-1",
        "dataset_fingerprint": BASELINE_DATASET,
    }
    decision = trainer.decide_training_reuse(
        latest=latest,
        dataset_fingerprint=BASELINE_DATASET,
        experiment_fingerprint=BASELINE_EXPERIMENT,
        fingerprint_config=config,
    )
    assert decision["reuse"] is True
    assert decision["reason"] == "VERIFIED_LEGACY_BASELINE_MATCH"


def test_changed_dataset_or_model_input_requires_training() -> None:
    config = _config()
    latest = {
        "schema": "binance-usdm-intraday-research-training-latest-v0.1",
        "provider": "binance_usdm",
        "run_id": "github-34918219864-1",
        "dataset_fingerprint": BASELINE_DATASET,
    }
    for dataset, experiment in (
        ("f" * 64, BASELINE_EXPERIMENT),
        (BASELINE_DATASET, "e" * 64),
    ):
        decision = trainer.decide_training_reuse(
            latest=latest,
            dataset_fingerprint=dataset,
            experiment_fingerprint=experiment,
            fingerprint_config=config,
        )
        assert decision["reuse"] is False
        assert decision["reason"] == "DATASET_OR_MODEL_INPUT_CHANGED"


def test_v0_2_latest_pointer_reuses_exact_experiment() -> None:
    config = _config()
    latest = {
        "schema": "binance-usdm-intraday-research-training-latest-v0.2",
        "provider": "binance_usdm",
        "run_id": "github-future-1",
        "dataset_fingerprint": BASELINE_DATASET,
        "experiment_fingerprint": BASELINE_EXPERIMENT,
    }
    decision = trainer.decide_training_reuse(
        latest=latest,
        dataset_fingerprint=BASELINE_DATASET,
        experiment_fingerprint=BASELINE_EXPERIMENT,
        fingerprint_config=config,
    )
    assert decision["reuse"] is True
    assert decision["reason"] == "EXACT_EXPERIMENT_FINGERPRINT_MATCH"


def test_training_workflow_uses_dedupe_runner_and_keeps_weekly_schedule() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert 'cron: "37 4 * * 0"' in text
    assert "train_binance_detailed_history_models_v0_3.py" in text
    assert "--fingerprint-config config/core100_training_fingerprint_v0_1.json" in text
    assert '"PASS", "NO_CHANGE"' in text
    assert 'report["r2_writes_performed"] is False' in text


def test_fingerprint_policy_grants_no_new_authority() -> None:
    config = _config()
    assert config["reuse_policy"]["same_dataset_and_experiment_returns"] == "NO_CHANGE"
    assert config["reuse_policy"]["no_training_on_no_change"] is True
    assert config["reuse_policy"]["no_r2_write_on_no_change"] is True
    assert all(value is False for value in config["authority"].values())
