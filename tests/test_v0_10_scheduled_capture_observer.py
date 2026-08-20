from pathlib import Path


WORKFLOW = Path('.github/workflows/observe-v0-10-scheduled-capture.yml')


def test_observer_is_read_only_and_schedule_scoped() -> None:
    text = WORKFLOW.read_text(encoding='utf-8')

    assert 'Provider Equivalence V0.10 Render Metadata Capture' in text
    assert "github.event.workflow_run.event == 'schedule'" in text
    assert 'actions: read' in text
    assert 'contents: read' in text
    assert 'issues: write' not in text
    assert 'contents: write' not in text
    assert 'secrets.' not in text
    assert 'workflow_dispatch:' not in text


def test_observer_reads_only_github_execution_metadata() -> None:
    text = WORKFLOW.read_text(encoding='utf-8')

    assert '/actions/runs/{run_id}/jobs?per_page=100' in text
    assert 'capture_artifact_read' in text
    assert "'capture_artifact_read': False" in text
    assert "'provider_data_read': False" in text
    assert "'r2_client_constructed': False" in text
    assert "'r2_reads_performed': False" in text
    assert "'r2_writes_performed': False" in text
    assert "'holdout_accessed': False" in text
    assert "'v0_11_evaluation_performed': False" in text
    assert "'source_switch_performed': False" in text
    assert "'live_trading_performed': False" in text


def test_observer_requires_the_expected_pipeline_steps() -> None:
    text = WORKFLOW.read_text(encoding='utf-8')

    assert 'validate-atomic-cutover' in text
    assert 'window-gate' in text
    assert "'capture'" in text
    assert 'Reject stale scheduled runs before provider or R2 access' in text
    assert 'Capture frozen provider metadata through V0.10 successor path' in text
    assert 'Assert V0.10 capture boundary' in text
    assert 'V0_10_SCHEDULED_PIPELINE_EXECUTION_HEALTH_PASS' in text
    assert 'capture_evidence_interpreted' in text
    assert "'capture_evidence_interpreted': False" in text


def test_observer_preserves_exact_frozen_window() -> None:
    text = WORKFLOW.read_text(encoding='utf-8')

    assert '2026-08-27T00:00:00+00:00' in text
    assert '2026-09-04T01:59:59.999000+00:00' in text
