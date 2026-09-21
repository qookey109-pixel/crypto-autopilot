from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.resource_hub_change_watch_v0_2 import build_change_watch
from crypto_autopilot.toolkit.resource_hub_supply_chain import build_candidate_registry


POLICY = json.loads(
    Path("config/resource_hub_supply_chain_v0_2.json").read_text(encoding="utf-8")
)
BASELINE = POLICY["baseline"]["source_commit"]
WORKFLOW = Path(".github/workflows/resource-hub-supply-chain-v0-2.yml")


def _catalog() -> dict[str, object]:
    return {
        "schema_version": "0.1",
        "updated_at": "2026-09-19",
        "resources": [
            {
                "id": "market-research",
                "name": "Market Research",
                "url": "https://example.com/market",
                "categories": ["Finance / Crypto"],
                "tags": ["crypto", "market data"],
                "summary": "Read-only crypto market data research.",
                "use_cases": ["market research"],
                "pricing": "free",
                "open_source": True,
                "license": "MIT",
                "status": "active",
            }
        ],
    }


def _previous(
    commit: str = BASELINE,
    fingerprint: str | None = None,
    count: int | None = None,
) -> dict[str, object]:
    return {
        "schema": "qookey-resource-hub-change-watch-state-v0.2",
        "source": {"current_commit": commit},
        "evaluation": {
            "candidate_fingerprint": fingerprint,
            "candidate_count": count,
        },
    }


def test_v0_2_candidate_registry_allows_only_scheduled_public_catalog_read() -> None:
    result = build_candidate_registry(_catalog(), POLICY, source_commit="b" * 40)
    authority = result["authority"]
    assert authority["workflow_dispatch_only"] is False
    assert authority["schedule_authorized"] is True
    assert authority["public_catalog_read_authorized"] is True
    for key, value in authority.items():
        if key in {"schedule_authorized", "public_catalog_read_authorized"}:
            assert value is True
        elif key == "workflow_dispatch_only":
            assert value is False
        else:
            assert value is False, key


def test_no_change_skips_candidate_evaluation() -> None:
    state, registry = build_change_watch(
        catalog=_catalog(),
        policy=POLICY,
        source_commit=BASELINE,
        previous_state=_previous(),
    )
    assert state["status"] == "NO_CHANGE"
    assert state["decision"] == "NO_CHANGE"
    assert state["source"]["source_changed"] is False
    assert state["evaluation"]["candidate_evaluation_performed"] is False
    assert registry is None


def test_changed_source_builds_review_only_candidates() -> None:
    state, registry = build_change_watch(
        catalog=_catalog(),
        policy=POLICY,
        source_commit="c" * 40,
        previous_state=_previous(),
    )
    assert state["status"] == "SOURCE_CHANGED_REVIEW_REQUIRED"
    assert state["decision"] == "REVIEW_REQUIRED"
    assert state["evaluation"]["candidate_evaluation_performed"] is True
    assert state["evaluation"]["automatic_pull_request_created"] is False
    assert registry is not None
    assert registry["status"] == "RESEARCH_ONLY"
    assert registry["candidate_count"] == 1


def test_same_candidate_fingerprint_does_not_request_duplicate_review() -> None:
    first_state, first_registry = build_change_watch(
        catalog=_catalog(),
        policy=POLICY,
        source_commit="c" * 40,
        previous_state=_previous(),
    )
    assert first_registry is not None
    fingerprint = first_state["evaluation"]["candidate_fingerprint"]

    second_state, second_registry = build_change_watch(
        catalog=_catalog(),
        policy=POLICY,
        source_commit="d" * 40,
        previous_state=_previous("c" * 40, fingerprint, 1),
    )
    assert second_registry is not None
    assert second_state["status"] == "SOURCE_CHANGED_CANDIDATES_UNCHANGED"
    assert second_state["decision"] == "NO_CHANGE"
    assert second_state["evaluation"]["candidate_changed_vs_previous"] is False


def test_v0_2_fails_closed_if_runtime_or_auto_pr_is_enabled() -> None:
    for key in ("automatic_execution_authorized", "automatic_pull_request_authorized"):
        unsafe = deepcopy(POLICY)
        unsafe["safety"][key] = True
        with pytest.raises(ValueError):
            build_change_watch(
                catalog=_catalog(),
                policy=unsafe,
                source_commit=BASELINE,
                previous_state=_previous(),
            )


def test_workflow_expands_variables_and_never_silently_loses_dedupe_state() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "\\${" not in text
    assert "GITHUB_TOKEN: ${{ github.token }}" in text
    assert 'Bearer ${GITHUB_TOKEN}' in text
    assert 'hub_sha=${HUB_SHA}' in text
    assert '/${HUB_SHA}/data/resources.json' in text
    assert '"${args[@]}"' in text
    assert "|| true" not in text

    assert "FIRST_RUN_BASELINE" in text
    assert "PREVIOUS_STATE_LOOKUP_FAILED" in text
    assert "PREVIOUS_STATE_EXPIRED" in text
    assert "PREVIOUS_STATE_MISSING" in text
    assert "PREVIOUS_STATE_RESTORE_FAILED" in text
    assert "PREVIOUS_STATE_INVALID" in text

    assert (
        "name: resource-hub-source-state-v0-2\n"
        "          path: resource-hub-output/state.json\n"
        "          retention-days: 30"
    ) in text
