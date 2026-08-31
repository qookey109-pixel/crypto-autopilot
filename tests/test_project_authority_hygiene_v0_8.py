from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "PROJECT_STATUS.md"
README = ROOT / "README.md"
AGENTS = ROOT / "AGENTS.md"
DASHBOARD = ROOT / "web/data/dashboard.json"
V08_CONFIG = ROOT / "config/provider_equivalence_v0_8_render_metadata_execution_cutover_v0_1.json"
V10_CONFIG = ROOT / "config/provider_equivalence_v0_10_final_atomic_cutover_v0_1.json"
V10_AUTHORITY = (
    ROOT
    / "research/receipts/2026-08-20-provider-equivalence-v0-10-final-atomic-cutover-authority.json"
)
OLD_WORKFLOW = ROOT / ".github/workflows/provider-equivalence-v0-2-metadata-capture.yml"
V10_WORKFLOW = ROOT / ".github/workflows/provider-equivalence-v0-10-render-metadata-capture.yml"
RETIRED_V03 = (
    ROOT / ".github/workflows/automate-v0-3-cloud-transport-follow-up.yml",
    ROOT / ".github/workflows/diagnose-v0-3-cloudflare-container-binance-transport.yml",
    ROOT / ".github/workflows/dispatch-v0-3-cloud-transport-from-authority-marker.yml",
)


def _load(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_current_entry_docs_preserve_v08_history_and_reflect_v10_effective_state() -> None:
    status = STATUS.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    agents = AGENTS.read_text(encoding="utf-8")

    for text in (status, readme):
        assert "V0.8" in text
        assert "V0.10" in text
        assert "PAPER-ONLY" in text
        assert "FROZEN_UNOPENED" in text
        assert "Equivalence V0.1" in text or "EQUIVALENCE V0.1" in text

    # V0.8 remains immutable historical preparation evidence; it must not be
    # rewritten to look like the effective V0.10 execution authority.
    v08 = _load(V08_CONFIG)
    assert v08["status"] == "CUTOVER_CONTRACT_FROZEN_EXECUTION_NOT_AUTHORIZED"
    assert v08["authorization_boundary"]["render_metadata_relay_enablement_authorized"] is False
    assert v08["authorization_boundary"]["successor_scheduled_capture_activation_authorized"] is False

    assert "V0.10 FINAL ATOMIC METADATA CAPTURE CUTOVER EFFECTIVE" in status
    assert "V0.2 SELF-HOSTED SCHEDULE RETIRED" in status
    assert "V0.10 GITHUB-HOSTED SCHEDULE CURRENT" in status
    assert "V0.8" in status and "HISTORICAL" in status

    assert "Project runtime budget is `0 USD/month`" in agents
    assert "Do not create a second concurrent capture path" in agents
    assert "Render must never receive R2 credentials" in agents
    assert "V0.10 final atomic metadata-capture cutover is **effective**" in agents


def test_v10_is_unique_current_metadata_execution_owner_without_rewriting_v08() -> None:
    v10 = _load(V10_CONFIG)
    authority = _load(V10_AUTHORITY)
    old_lines = OLD_WORKFLOW.read_text(encoding="utf-8").splitlines()
    new_lines = V10_WORKFLOW.read_text(encoding="utf-8").splitlines()

    assert v10["status"] == "FINAL_ATOMIC_CUTOVER_AUTHORIZED_ON_MAIN_MERGE"
    assert authority["status"] == "PASS"
    assert authority["post_merge_authorization"]["metadata_capture_execution_authorized"] is True
    assert authority["post_merge_authorization"]["old_v0_2_scheduled_execution_authorized"] is False
    assert authority["post_merge_authorization"]["concurrent_old_new_capture_authorized"] is False
    assert not any(line == "  schedule:" for line in old_lines)
    assert any(line == "  schedule:" for line in new_lines)


def test_dashboard_safe_fixture_reflects_v10_but_never_becomes_authority() -> None:
    data = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    project = data["project"]
    assert data["authority"] is False
    assert data["locale"] == "zh-Hant-TW"
    assert project["mode"] == "PAPER-ONLY"
    assert project["fundingMaterializationState"] == "PASS"
    assert project["providerEquivalenceGateState"] == "FAIL"
    assert project["renderMetadataV0_8CutoverState"] == (
        "HISTORICAL_PREPARED_EXECUTION_NOT_AUTHORIZED"
    )
    assert project["renderMetadataV0_9SmokeState"] == "PASS_FROZEN"
    assert project["renderMetadataV0_10CutoverState"] == "EFFECTIVE_AUTHORIZED"
    assert project["v0_10CaptureOperationalState"] == (
        "FAIL_CLOSED_PIONEX_SCHEMA_MISMATCH"
    )
    assert project["v0_10CaptureObservedFailedRunCount"] == 5
    assert project["metadataStabilityEligibilityState"] == (
        "KNOWN_BLOCKED_BY_MISSING_VALID_SLOTS"
    )
    assert project["currentMetadataCaptureExecutionPath"] == "github_hosted_ubuntu_v0_10"
    assert project["oldV0_2ScheduledExecutionAuthorized"] is False
    assert project["successorMetadataCaptureExecutionAuthorized"] is True
    assert project["successorMetadataScheduleEnabled"] is True
    assert project["metadataCapturePathsConcurrentAuthorized"] is False
    assert project["metadataStabilityState"] == "NOT_YET_RUN"
    assert project["replacementHoldoutState"] == "FROZEN_UNOPENED"
    assert project["sourceSwitchAuthorized"] is False
    assert project["tradePlanAuthorized"] is False
    assert project["liveTradingAuthorized"] is False


def test_retired_cloudflare_v03_workflows_cannot_auto_dispatch() -> None:
    for path in RETIRED_V03:
        text = path.read_text(encoding="utf-8")
        assert "RETIRED_NO_EXECUTION" in text
        assert "workflow_run:" not in text
        assert "schedule:" not in text
        assert "repository_dispatch:" not in text
        assert (
            "provider_requests_performed=0" in text
            or "upstream_provider_request_performed=false" in text
        )
        assert "r2_writes_performed=false" in text
        assert "holdout_candles_accessed=false" in text
        assert "source_switch_authorized=false" in text
        assert "live_trading_authorized=false" in text
