from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Mapping

from crypto_autopilot.toolkit.external_capability_registry_v0_1 import (
    validate_external_capability_registry,
)


POLICY = Path("config/automation_schedule_projection_v0_1.json")
RESOURCE_HUB = Path("config/resource_hub_supply_chain_v0_2.json")
CAPABILITY_REGISTRY = Path("config/external_capability_registry_v0_1.json")
CURRENT_OPERATIONS = Path("research/status/current-operations-v0-3.json")
ZEC_MATRIX = Path("config/zec_strategy_v0_3_development_matrix_v0_1.json")
CORE100_RETIREMENT = Path("config/core100_history_retirement_v0_1.json")
CORE100_TRAINING_FINGERPRINT = Path("config/core100_training_fingerprint_v0_1.json")


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def _crons(path: Path) -> list[str]:
    if not path.is_file():
        raise RuntimeError(f"workflow missing: {path}")
    return re.findall(
        r'^\s*-\s*cron:\s*"([^"]+)"\s*$',
        path.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )


def _normalize_generated_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise RuntimeError("generated_at_utc must be UTC")
    return parsed.isoformat(timespec="seconds").replace("+00:00", "Z")


def build_projection(
    *,
    generated_at_utc: str | None = None,
    checked_in_fixture: bool = False,
) -> dict[str, object]:
    policy = _load(POLICY)
    if policy.get("schema") != "qookey-automation-schedule-projection-policy-v0.1":
        raise RuntimeError("automation schedule projection policy schema changed")
    if policy.get("status") != "PROJECTION_ONLY":
        raise RuntimeError("automation schedule projection must remain projection-only")
    policy_authority = policy.get("authority")
    if not isinstance(policy_authority, Mapping):
        raise RuntimeError("automation schedule projection authority missing")
    if policy_authority.get("projection_only") is not True:
        raise RuntimeError("automation schedule projection_only must remain true")
    for key, value in policy_authority.items():
        if key != "projection_only" and value is not False:
            raise RuntimeError(f"automation schedule projection gained authority: {key}")

    rows = policy.get("jobs")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("automation schedule jobs are required")

    projected_rows: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError("automation schedule job must be an object")
        workflow = row.get("workflow")
        expected = row.get("expected_crons")
        if not isinstance(expected, list) or not all(isinstance(item, str) for item in expected):
            raise RuntimeError(f"expected_crons invalid for {row.get('id')}")
        if workflow is not None:
            if not isinstance(workflow, str) or not workflow.startswith(".github/workflows/"):
                raise RuntimeError(f"workflow path invalid for {row.get('id')}")
            actual = _crons(Path(workflow))
            if actual != expected:
                raise RuntimeError(
                    f"workflow cron drift for {row.get('id')}: expected={expected} actual={actual}"
                )
        elif expected:
            raise RuntimeError(f"planned job cannot declare live cron: {row.get('id')}")
        projected_rows.append(dict(row))

    current = _load(CURRENT_OPERATIONS)
    core100 = current.get("core100")
    if not isinstance(core100, Mapping):
        raise RuntimeError("current operations Core100 state missing")
    if core100.get("history_status") != "COMPLETE":
        raise RuntimeError("automation projection expected Core100 History COMPLETE")
    if core100.get("history_complete_shards") != 10:
        raise RuntimeError("automation projection expected 10 Core100 shards")
    if core100.get("history_reacquisition_required") is not False:
        raise RuntimeError("automation projection cannot require completed history reacquisition")

    retirement = _load(CORE100_RETIREMENT)
    if (
        retirement.get("schema") != "qookey-core100-history-retirement-v0.1"
        or retirement.get("status") != "EFFECTIVE_ON_PROTECTED_MAIN_MERGE"
    ):
        raise RuntimeError("Core100 History retirement authority missing")
    retired_execution = retirement.get("retired_execution")
    retirement_authority = retirement.get("authority")
    if not isinstance(retired_execution, Mapping) or not isinstance(
        retirement_authority, Mapping
    ):
        raise RuntimeError("Core100 History retirement contract incomplete")
    if (
        retired_execution.get("schedule_trigger_retired") is not True
        or retired_execution.get("generic_auto_discover_backfill_retired") is not True
        or retired_execution.get("automatic_resume") is not False
    ):
        raise RuntimeError("Core100 History retirement contract drifted")
    if any(value is not False for value in retirement_authority.values()):
        raise RuntimeError("Core100 History retirement gained authority")

    training_fingerprint = _load(CORE100_TRAINING_FINGERPRINT)
    if (
        training_fingerprint.get("schema")
        != "qookey-core100-training-fingerprint-v0.1"
        or training_fingerprint.get("status") != "EFFECTIVE_ON_PROTECTED_MAIN_MERGE"
    ):
        raise RuntimeError("Core100 Training fingerprint policy missing")
    reuse = training_fingerprint.get("reuse_policy")
    fingerprint_authority = training_fingerprint.get("authority")
    baseline_training = training_fingerprint.get("baseline")
    if (
        not isinstance(reuse, Mapping)
        or not isinstance(fingerprint_authority, Mapping)
        or not isinstance(baseline_training, Mapping)
    ):
        raise RuntimeError("Core100 Training fingerprint contract incomplete")
    if (
        reuse.get("same_dataset_and_experiment_returns") != "NO_CHANGE"
        or reuse.get("no_training_on_no_change") is not True
        or reuse.get("no_r2_write_on_no_change") is not True
    ):
        raise RuntimeError("Core100 Training fingerprint reuse policy drifted")
    if any(value is not False for value in fingerprint_authority.values()):
        raise RuntimeError("Core100 Training fingerprint gained authority")

    resource = _load(RESOURCE_HUB)
    if resource.get("schema") != "qookey-resource-hub-supply-chain-policy-v0.2":
        raise RuntimeError("Resource Hub v0.2 policy missing")
    safety = resource.get("safety")
    baseline = resource.get("baseline")
    if not isinstance(safety, Mapping) or not isinstance(baseline, Mapping):
        raise RuntimeError("Resource Hub v0.2 policy is incomplete")
    if safety.get("schedule_authorized") is not True:
        raise RuntimeError("Resource Hub scheduled read watch is not authorized")
    for key in (
        "automatic_install_authorized",
        "automatic_execution_authorized",
        "automatic_adapter_creation_authorized",
        "automatic_pull_request_authorized",
        "provider_access_authorized",
        "r2_access_authorized",
        "holdout_access_authorized",
        "source_switch_authorized",
        "automatic_strategy_mutation_authorized",
        "automatic_model_promotion_authorized",
        "formal_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if safety.get(key) is not False:
            raise RuntimeError(f"Resource Hub v0.2 unsafe authority enabled: {key}")

    registry = _load(CAPABILITY_REGISTRY)
    registry_validation = validate_external_capability_registry(registry)
    if registry_validation.get("state") != "PASS":
        raise RuntimeError("external capability registry validation failed")

    zec = _load(ZEC_MATRIX)
    if zec.get("status") != "PREPARED_OFFLINE_DEVELOPMENT_CONTRACT_ONLY":
        raise RuntimeError("ZEC V0.3 development contract state changed")
    zec_authority = zec.get("authority")
    development = zec.get("development_window")
    if not isinstance(zec_authority, Mapping) or not isinstance(development, Mapping):
        raise RuntimeError("ZEC V0.3 development contract incomplete")
    if zec_authority.get("offline_development_runner_authorized") is not False:
        raise RuntimeError("ZEC V0.3 development execution unexpectedly opened")
    candidates = int(zec.get("expected_candidate_count") or 0)
    folds = development.get("folds")
    if candidates != 64 or not isinstance(folds, list) or len(folds) != 4:
        raise RuntimeError("ZEC V0.3 64 x 4 matrix contract changed")
    expected_cells = candidates * len(folds)

    statuses = [str(row.get("status") or "") for row in projected_rows]
    scheduled_count = sum(
        1
        for row in projected_rows
        if isinstance(row.get("workflow"), str) and bool(row.get("expected_crons"))
    )
    waiting_count = sum("WAITING" in status for status in statuses)
    planned_count = sum(status == "PLANNED_NOT_SCHEDULED" for status in statuses)

    generated = None if checked_in_fixture else _normalize_generated_at(generated_at_utc)
    return {
        "schema": "qookey-automation-schedule-projection-v0.1",
        "authority": False,
        "timezone": str(policy.get("timezone") or "Asia/Taipei"),
        "projectionGeneratedAtUtc": generated,
        "summary": {
            "scheduledJobCount": scheduled_count,
            "waitingAuthorityCount": waiting_count,
            "plannedNotScheduledCount": planned_count,
            "core100HistoryStatus": "COMPLETE",
            "core100HistoryRetirementPending": False,
            "core100HistoryScheduleRetired": True,
            "core100TrainingDedupeState": "ACTIVE_FINGERPRINT_NO_CHANGE",
            "zecDevelopmentExpectedCells": expected_cells,
            "zecDevelopmentCompletedCells": 0,
        },
        "sourceStatus": {
            "resourceHub": {
                "state": "SCHEDULED_READ_ONLY_CHANGE_WATCH",
                "baselineCommit": baseline.get("source_commit"),
                "catalogUpdatedAt": baseline.get("catalog_updated_at"),
                "automaticPullRequestAuthorized": False,
                "automaticExecutionAuthorized": False,
            },
            "externalCapabilityRegistry": {
                "state": "CANDIDATE_REGISTRY_ONLY",
                "candidateCount": registry_validation.get("capability_count"),
                "runtimeExecutionAuthorized": False,
                "automaticInstallAuthorized": False,
            },
            "core100": {
                "historyState": "COMPLETE_SCHEDULE_RETIRED",
                "historyGenericBackfillRetired": True,
                "trainingState": "FINGERPRINT_DEDUP_ACTIVE",
                "trainingBaselineRunId": baseline_training.get("source_workflow_run_id"),
                "trainingBaselineExperimentFingerprint": baseline_training.get(
                    "experiment_fingerprint"
                ),
                "trainingNoChangeWritesR2": False,
            },
            "zecV0_3": {
                "state": "WAITING_EXECUTION_AUTHORITY",
                "candidateCount": candidates,
                "foldCount": len(folds),
                "expectedCells": expected_cells,
                "completedCells": 0,
                "freshConfirmationAccessAuthorized": False,
            },
        },
        "items": projected_rows,
        "sourceAuthorities": [
            str(POLICY),
            str(RESOURCE_HUB),
            str(CAPABILITY_REGISTRY),
            str(CURRENT_OPERATIONS),
            str(CORE100_RETIREMENT),
            str(CORE100_TRAINING_FINGERPRINT),
            str(ZEC_MATRIX),
        ],
        "safetyBoundary": {
            "automaticActivationAuthorized": False,
            "providerAccessAuthorized": False,
            "r2ReadAuthorized": False,
            "r2WriteAuthorized": False,
            "holdoutAccessAuthorized": False,
            "sourceSwitchAuthorized": False,
            "automaticModelPromotionAuthorized": False,
            "formalTradePlanAuthorized": False,
            "realMoneyOrderAuthorized": False,
            "liveTradingAuthorized": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--generated-at-utc")
    args = parser.parse_args()

    projection = build_projection(generated_at_utc=args.generated_at_utc)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(projection, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
