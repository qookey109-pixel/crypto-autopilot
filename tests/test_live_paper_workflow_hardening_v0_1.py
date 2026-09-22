from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.run_live_paper_coordinator_v0_1 import (
    _OperationJournal,
    _TrackedFeed,
    _TrackedStore,
    _failure_report,
)


ROOT = Path(__file__).resolve().parents[1]


class _Frame:
    provider_request_count = 2


class _SuccessFeed:
    def fetch_frame(self, symbol: str, *, tick_time_ms: int, since_ms: int):
        return _Frame()


class _FailingFeed:
    def fetch_frame(self, symbol: str, *, tick_time_ms: int, since_ms: int):
        raise RuntimeError("provider leaked detail must not reach report")


class _SuccessStore:
    def put_json(self, kind: str, object_id: str, payload):
        return SimpleNamespace(replayed=False)

    def get_json(self, kind: str, object_id: str):
        return None

    def put_json_if_absent(self, kind: str, object_id: str, payload):
        return SimpleNamespace(replayed=False)


class _FailingStore:
    def put_json(self, kind: str, object_id: str, payload):
        raise OSError("storage leaked detail must not reach report")

    def get_json(self, kind: str, object_id: str):
        return None

    def put_json_if_absent(self, kind: str, object_id: str, payload):
        raise OSError("storage leaked detail must not reach report")


def test_tracked_feed_counts_known_provider_requests() -> None:
    journal = _OperationJournal()
    frame = _TrackedFeed(_SuccessFeed(), journal).fetch_frame(
        "BTC_USDT_PERP",
        tick_time_ms=2,
        since_ms=1,
    )
    assert frame.provider_request_count == 2
    assert journal.provider_requests_known == 2
    assert journal.provider_status == "KNOWN"


def test_tracked_feed_marks_failed_call_unknown_or_partial() -> None:
    journal = _OperationJournal()
    with pytest.raises(RuntimeError):
        _TrackedFeed(_FailingFeed(), journal).fetch_frame(
            "BTC_USDT_PERP",
            tick_time_ms=2,
            since_ms=1,
        )
    assert journal.provider_requests_known == 0
    assert journal.provider_status == "UNKNOWN_OR_PARTIAL"


def test_tracked_store_records_known_create_and_unknown_failed_write() -> None:
    journal = _OperationJournal()
    receipt = _TrackedStore(_SuccessStore(), journal).put_json(
        "live-state",
        "state-1",
        {"value": 1},
    )
    assert receipt.replayed is False
    assert journal.store_write_attempts == 1
    assert journal.store_objects_created_known == 1
    assert journal.store_status == "KNOWN"

    failing_journal = _OperationJournal()
    with pytest.raises(OSError):
        _TrackedStore(_FailingStore(), failing_journal).put_json(
            "live-state",
            "state-1",
            {"value": 1},
        )
    assert failing_journal.store_write_attempts == 1
    assert failing_journal.store_objects_created_known == 0
    assert failing_journal.store_status == "UNKNOWN_OR_PARTIAL"


def test_failure_report_never_claims_zero_when_side_effects_are_uncertain() -> None:
    journal = _OperationJournal(
        provider_status="UNKNOWN_OR_PARTIAL",
        store_write_attempts=1,
        store_status="UNKNOWN_OR_PARTIAL",
    )
    report = _failure_report(
        stage="COORDINATE_RUN_STEP",
        error=RuntimeError("secret-ish raw provider response"),
        journal=journal,
        claim_required=True,
    )
    assert report["provider_requests_performed"] is None
    assert report["persistent_objects_created"] is None
    assert report["provider_requests_status"] == "UNKNOWN_OR_PARTIAL"
    assert report["persistent_writes_status"] == "UNKNOWN_OR_PARTIAL"
    assert report["reason"] == "coordinate_run_step_failed"
    assert report["error_type"] == "RuntimeError"
    assert report["authority"]["paper_run_slot_claim_authorized"] is True
    assert report["authority"]["claim_conflict_auto_retry_authorized"] is False
    assert "secret-ish" not in str(report)


def test_workflows_use_constrained_installs_main_guard_and_shared_lock() -> None:
    coordinator = (
        ROOT / ".github/workflows/live-paper-run-coordinator-v0-1.yml"
    ).read_text(encoding="utf-8")
    recovery = (
        ROOT / ".github/workflows/live-paper-run-recovery-v0-1.yml"
    ).read_text(encoding="utf-8")

    for workflow in (coordinator, recovery):
        assert "requirements/ci-constraints.txt" in workflow
        assert 'test "${GITHUB_REF}" = "refs/heads/main"' in workflow
        assert "group: live-paper-persistence-v0-1" in workflow

    assert '--input "${{ inputs.input_path }}"' not in coordinator
    assert "research/inputs/live-paper" in coordinator
    assert 'INPUT_PATH: ${{ inputs.input_path }}' in coordinator

    assert '--run-id "${{ inputs.run_id }}"' not in recovery
    assert 'RUN_ID_INPUT: ${{ inputs.run_id }}' in recovery
    assert '--run-id "${SAFE_RUN_ID}"' in recovery
    assert "live-paper-run-v0-1-[0-9a-f]{64}" in recovery

    assert "id: coordinator" in coordinator
    assert "exit_code=$?" in coordinator
    assert 'echo "report_safe=true" >> "$GITHUB_OUTPUT"' in coordinator
    assert "always() && steps.coordinator.outputs.report_safe == 'true'" in coordinator
    assert "--coordinator-config config/live_paper_run_coordinator_v0_2.json" in coordinator
    assert "--claim-config config/live_paper_run_claim_v0_1.json" in coordinator
    assert 'authority["paper_run_slot_claim_authorized"] is True' in coordinator
    assert "Coordinator failed after producing a validated safe report." in coordinator
