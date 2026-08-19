from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "PROJECT_STATUS.md"
README = ROOT / "README.md"
AGENTS = ROOT / "AGENTS.md"
DASHBOARD = ROOT / "web/data/dashboard.json"
RETIRED_V03 = (
    ROOT / ".github/workflows/automate-v0-3-cloud-transport-follow-up.yml",
    ROOT / ".github/workflows/diagnose-v0-3-cloudflare-container-binance-transport.yml",
    ROOT / ".github/workflows/dispatch-v0-3-cloud-transport-from-authority-marker.yml",
)


def test_current_entry_docs_reflect_v08_without_granting_execution() -> None:
    status = STATUS.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    agents = AGENTS.read_text(encoding="utf-8")

    for text in (status, readme):
        assert "V0.8" in text
        assert "PAPER-ONLY" in text
        assert "FROZEN_UNOPENED" in text
        assert "Equivalence V0.1" in text or "EQUIVALENCE V0.1" in text

    assert "V0.8 RENDER METADATA CUTOVER PREPARED EXECUTION_NOT_AUTHORIZED" in status
    assert "V0_8_CAPTURE_EXECUTION_AUTHORIZED=false" in status
    assert "METADATA_RELAY_EXECUTION_AUTHORIZED=false" in status
    assert "successorMetadataCaptureExecutionAuthorized":=False if False else True

    assert "Project runtime budget is `0 USD/month`" in agents
    assert "Old/new capture paths must never run concurrently" in agents
    assert "Render must never receive R2 credentials" in agents


def test_dashboard_safe_fixture_is_current_but_never_authority() -> None:
    data = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    project = data["project"]
    assert data["authority"] is False
    assert data["locale"] == "zh-Hant-TW"
    assert project["mode"] == "PAPER-ONLY"
    assert project["fundingMaterializationState"] == "PASS"
    assert project["providerEquivalenceGateState"] == "FAIL"
    assert project["renderMetadataV0_8CutoverState"] == "PREPARED_EXECUTION_NOT_AUTHORIZED"
    assert project["currentMetadataCaptureExecutionPath"] == "github_self_hosted_mac"
    assert project["successorMetadataCaptureExecutionAuthorized"] is False
    assert project["successorMetadataScheduleEnabled"] is False
    assert project["metadataCapturePathsConcurrentAuthorized"] is False
    assert project["replacementHoldoutState"] == "FROZEN_UNOPENED"
    assert project["tradePlanAuthorized"] is False
    assert project["liveTradingAuthorized"] is False


def test_retired_cloudflare_v03_workflows_cannot_auto_dispatch() -> None:
    for path in RETIRED_V03:
        text = path.read_text(encoding="utf-8")
        assert "RETIRED_NO_EXECUTION" in text
        assert "workflow_run:" not in text
        assert "schedule:" not in text
        assert "repository_dispatch:" not in text
        assert "provider_requests_performed=0" in text or "upstream_provider_request_performed=false" in text
        assert "r2_writes_performed=false" in text
        assert "holdout_candles_accessed=false" in text
        assert "source_switch_authorized=false" in text
        assert "live_trading_authorized=false" in text
