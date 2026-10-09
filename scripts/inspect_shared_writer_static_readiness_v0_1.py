"""Static, repository-only blocker for unproven shared Cloudflare R2 writer wiring.

This is not Cloudflare access or admission. It deliberately does not call
provider/R2/D1 endpoints and cannot promote any writer to a live status.
Changes in reviewed routes require a new reviewed successor contract.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = "config/cloudflare_shared_account_writer_registry_v0_1.json"

# Four exact, currently inventoried repo workflow-to-entrypoint routes.
# These are *not* authorizations or an assertion of account completeness.
REVIEWED_PATHS = {
    ".github/workflows/research-signal-layer-v0-2.yml": (
        "scripts/run_research_signal_layer_v0_2.py",
        "python scripts/run_research_signal_layer_v0_2.py",
        ("--publish-r2",),
        ("from crypto_autopilot.storage.r2 import R2Store", "store = R2Store("),
    ),
    ".github/workflows/binance-usdm-detailed-training-v0-1.yml": (
        "scripts/train_binance_detailed_history_models_v0_4.py",
        "scripts/train_binance_detailed_history_models_v0_4.py",
        ("R2_ACCESS_KEY_ID",),
        ("training_v02.build_examples_from_r2(", "r2_writes_performed"),
    ),
    ".github/workflows/live-paper-run-coordinator-v0-1.yml": (
        "scripts/run_live_paper_coordinator_v0_1.py",
        "scripts/run_live_paper_coordinator_v0_1.py",
        ("--store-backend r2",),
        ("from crypto_autopilot.storage.r2 import R2Store", "R2PaperRunStore("),
    ),
    ".github/workflows/live-paper-run-recovery-v0-1.yml": (
        "scripts/reconcile_live_paper_run_v0_1.py",
        "scripts/reconcile_live_paper_run_v0_1.py",
        ("--store-backend r2",),
        ("from crypto_autopilot.storage.r2 import R2Store", "R2PaperRunStore("),
    ),
}
_BANNED_SOURCE_MARKERS = ("SharedWriterR2Budget.admit(", "reserve_shared_writer_envelope(")


class SharedWiringReviewRequired(ValueError):
    """Repository evidence changed; do not grant shared-account authorization."""


def _require(predicate: bool, reason: str) -> None:
    if not predicate:
        raise SharedWiringReviewRequired(reason)


def inspect_unverified_shared_writers(
    registry: Mapping[str, object],
    workflow_source: Mapping[str, str],
    entrypoint_source: Mapping[str, str],
) -> dict[str, object]:
    """Validate known direct routes and keep all production claims *closed*.

    Source marker checks verify *unchanged reviewed code shapes*, not absence
    of every possible transitive wrapper or proof of any writer safety.
    """
    _require(
        registry.get("schema") == "qookey-cloudflare-shared-account-writer-registry-v0.1"
        and registry.get("status") == "PREPARED_REGISTRY_NOT_ACCOUNT_COMPLETE",
        "REGISTRY_SCHEMA_OR_STATUS_DRIFT",
    )
    rows = registry.get("repository_writers")
    _require(isinstance(rows, list), "REGISTERED_WRITERS_MISSING")
    _require(len(rows) == len(REVIEWED_PATHS), "REVIEWED_WRITER_COUNT_DRIFT")
    _require(
        set(workflow_source) == set(REVIEWED_PATHS),
        "REVIEWED_WORKFLOW_SOURCE_DRIFT",
    )
    expected_entrypoints = {route[0] for route in REVIEWED_PATHS.values()}
    _require(set(entrypoint_source) == expected_entrypoints, "REVIEWED_ENTRYPOINT_SOURCE_DRIFT")
    external = registry.get("external_writer_inventory")
    gate = registry.get("production_gate")
    _require(
        isinstance(external, Mapping)
        and external.get("state") == "UNCONFIRMED"
        and external.get("complete") is False
        and isinstance(gate, Mapping)
        and all(gate.get(field) is False for field in (
            "account_wide_coverage_proven",
            "shared_admission_integrated_for_all_repository_writers",
            "d1_provisioned",
            "activation_enabled",
            "legacy_existing_writes_claimed_globally_admitted",
        )),
        "ACCOUNT_COVERAGE_OR_GATE_UNEXPECTEDLY_OPEN",
    )
    reviewed: list[dict[str, object]] = []
    seen: set[str] = set()
    for row in rows:
        _require(isinstance(row, Mapping), "INVALID_WRITER_ENTRY")
        path = row.get("workflow")
        identity = row.get("writer_id")
        _require(
            isinstance(path, str)
            and path in REVIEWED_PATHS
            and isinstance(identity, str)
            and identity == f"crypto-autopilot:{path.removeprefix('.github/workflows/').removesuffix('.yml')}"
            and identity not in seen,
            "WRITER_IDENTITY_OR_WORKFLOW_DRIFT",
        )
        seen.add(identity)
        _require(
            row.get("resource") == "R2"
            and row.get("registration_state") == "DECLARED_SHARED_ADMISSION_NOT_VERIFIED",
            "UNSUPPORTED_WRITER_PROMOTION_WITHOUT_VERSIONED_PROOF",
        )
        script, command, workflow_markers, source_markers = REVIEWED_PATHS[path]
        workflow = workflow_source[path]
        source = entrypoint_source[script]
        _require(
            command in workflow
            and all(marker in workflow for marker in workflow_markers)
            and "R2_ACCESS_KEY_ID:" in workflow
            and "R2_SECRET_ACCESS_KEY:" in workflow,
            "WRITER_ROUTE_OR_SECRET_REFERENCE_DRIFT",
        )
        _require(
            all(marker in source for marker in source_markers),
            "R2_ENTRYPOINT_SHAPE_CHANGED_REVIEW_REQUIRED",
        )
        _require(
            all(marker not in source for marker in _BANNED_SOURCE_MARKERS),
            "SHARED_GATE_REFERENCE_CHANGED_REVIEW_BEFORE_PROMOTION",
        )
        reviewed.append({
            "writer_id": identity,
            "workflow": path,
            "entrypoint": script,
            "resource": "R2",
            "registry_state": "DECLARED_SHARED_ADMISSION_NOT_VERIFIED",
            "static_route_shape_matches_review": True,
            "shared_account_admission_verified": False,
            "runtime_query_meter_verified": False,
            "account_wide_writer_coverage_proven": False,
        })
    reviewed.sort(key=lambda x: str(x["workflow"]))
    return {
        "schema": "qookey-shared-writer-static-readiness-v0.1",
        "status": "REVIEW_REQUIRED_SHARED_ADMISSION_UNVERIFIED",
        "scope": "REPOSITORY_SOURCE_ONLY",
        "reviewed_writer_count": len(reviewed),
        "writer_reviews": reviewed,
        "account_inventory_complete_proven": False,
        "external_writer_inventory_verified": False,
        "production_query_meter_verified": False,
        "d1_account_usage_headroom_verified": False,
        "paper_activation_allowed": False,
        "live_trading_authorized": False,
        "cloudflare_access_performed": False,
        "this_result_grants_execution_authority": False,
        "note": (
            "Four exact known source routes are traceable; no demonstrated "
            "all-writer shared admission, account-wide proof, D1 provisioning "
            "or production query metering. Changing the workflow, entrypoint, "
            "or verified status requires a separately reviewed successor."
        ),
    }


def inspect_current_checkout() -> dict[str, object]:
    """Read only a GitHub Actions checkout, not network or user's computer."""
    registry = json.loads((ROOT / REGISTRY_PATH).read_text(encoding="utf-8"))
    workflows = {
        path: (ROOT / path).read_text(encoding="utf-8")
        for path in REVIEWED_PATHS
    }
    scripts = {
        route[0]: (ROOT / route[0]).read_text(encoding="utf-8")
        for route in REVIEWED_PATHS.values()
    }
    return inspect_unverified_shared_writers(registry, workflows, scripts)


if __name__ == "__main__":
    print(json.dumps(inspect_current_checkout(), sort_keys=True, indent=2))
