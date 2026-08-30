from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config/v0_10_critical_path_freeze_v0_1.json"
WORKFLOW = ROOT / ".github/workflows/v0-10-critical-path-freeze-guard.yml"
BASELINE = "4a805b30183b23e29ea36689dfaa2ba0a4e4533f"


def test_v0_10_critical_path_manifest_is_fail_closed() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert payload["schema"] == "v0_10_critical_path_freeze_v0_1"
    assert payload["status"] == "FROZEN_PRE_WINDOW"
    assert payload["baseline_main_sha"] == BASELINE
    assert payload["frozen_window_start_utc"] == "2026-08-27T00:00:00Z"
    assert payload["frozen_window_end_utc"] == "2026-09-04T01:59:59.999Z"

    paths = payload["critical_paths"]
    assert len(paths) == len(set(paths))
    required_paths = {
        ".github/workflows/provider-equivalence-v0-10-render-metadata-capture.yml",
        ".github/workflows/provider-equivalence-v0-2-metadata-capture.yml",
        "config/provider_equivalence_v0_10_final_atomic_cutover_v0_1.json",
        "config/provider_equivalence_v0_2_metadata_capture_v0_2.json",
        "src/crypto_autopilot/provider_metadata_capture_v0_10.py",
        "src/crypto_autopilot/provider_metadata_capture_v0_8_successor.py",
        "src/crypto_autopilot/provider_metadata_capture_v0_2.py",
        "src/crypto_autopilot/storage/r2.py",
        "scripts/capture_provider_equivalence_v0_10_metadata.py",
        "infra/render/binance-transport-free/server.py",
        "requirements/ci-constraints.txt",
    }
    assert required_paths.issubset(set(paths))
    assert all((ROOT / path).is_file() for path in paths)

    boundary = payload["guard_boundary"]
    assert boundary["advisory_path_scoped_check_only"] is True
    assert boundary["global_required_check"] is False
    assert boundary["provider_requests_performed"] == 0
    assert boundary["render_requests_performed"] == 0
    assert boundary["r2_client_constructed"] is False
    assert boundary["r2_reads_performed"] is False
    assert boundary["r2_writes_performed"] is False
    assert boundary["holdout_accessed"] is False
    assert boundary["v0_11_production_evaluation_performed"] is False
    assert boundary["manual_v0_10_capture_authorized"] is False
    assert boundary["render_deploy_authorized"] is False
    assert boundary["source_switch_authorized"] is False
    assert boundary["live_trading_authorized"] is False


def test_v0_10_critical_path_guard_is_read_only_and_not_scheduled() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "name: V0.10 Critical Path Freeze Guard" in text
    assert "workflow_dispatch:" not in text
    assert "schedule:" not in text
    assert "permissions:\n  contents: read" in text
    assert "secrets." not in text
    assert "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803" in text
    assert "persist-credentials: false" in text
    assert "fetch-depth: 0" in text
    assert "V0_10_CRITICAL_PATH_DRIFT_DETECTED" in text
    assert "V0_10_CRITICAL_PATH_FREEZE_GUARD_PASS" in text
    assert "V0_10_AUTHORIZED_EMERGENCY_SCHEDULE_REREGISTRATION_REVIEW_PASS" in text
    assert "V0_10_AUTHORIZED_EMERGENCY_PIONEX_PERP_QUERY_REVIEW_PASS" in text
    assert "v0_10_mid_window_emergency_schedule_reactivation_v0_1.json" in text
    assert "v0_10_mid_window_emergency_pionex_perp_query_v0_1.json" in text
    assert "protected_main_pr_number" in text
    assert "a56fcff85e65a051b3848a0362edfa7a6e9019f6" in text
    assert "operational_changed != [" in text
    assert "'query_value': 'PERP'" in text
    assert "changed not in (schedule_expected_changed, pionex_expected_changed)" not in text
    assert "not recognized_change or not required_authorities_present" in text
    assert "replacement_attempts != original_attempts" in text
    assert "len(replacement_attempts) != 388" in text
    assert "prior_missing_attempts_remain_failures': True" in text
    assert "provider_requests_performed': 0" in text
    assert "r2_reads_performed': False" in text
    assert "r2_writes_performed': False" in text
    assert "holdout_accessed': False" in text
    assert "source_switch_authorized': False" in text
    assert "live_trading_authorized': False" in text
