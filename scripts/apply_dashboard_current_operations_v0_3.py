from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


CURRENT_OPERATIONS = Path("research/status/current-operations-v0-3.json")


def _require_dict(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError(f"expected object: {label}")
    return value


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return _require_dict(payload, str(path))


def _upsert_status_item(
    items: list[dict[str, Any]],
    *,
    name: str,
    detail: str,
    status: str,
    tone: str | None = None,
    critical: bool | None = None,
) -> None:
    item: dict[str, Any] | None = None
    for row in items:
        if row.get("name") == name:
            item = row
            break
    if item is None:
        item = {"name": name}
        items.append(item)
    item["detail"] = detail
    item["status"] = status
    if tone is not None:
        item["tone"] = tone
    if critical is not None:
        item["critical"] = critical


def validate_current_operations(current: dict[str, Any]) -> None:
    if current.get("schema") != "qookey-current-operations-v0.3":
        raise RuntimeError("unexpected current-operations schema")
    if current.get("repository_authority") != "RESOLVE_MAIN_LIVE_AT_READ_TIME":
        raise RuntimeError("repository authority semantics changed")
    if current.get("mode") != "PAPER_ONLY":
        raise RuntimeError("current operations must remain PAPER_ONLY")

    basis = _require_dict(current.get("evidence_basis"), "evidence basis")
    if basis.get("semantics") != "REPOSITORY_MAIN_REVIEWED_BEFORE_THIS_STATUS_VERSION":
        raise RuntimeError("evidence-basis semantics changed")
    if basis.get("is_latest_main_claim") is not False:
        raise RuntimeError("current status must not self-claim latest main")

    core100 = _require_dict(current.get("core100"), "core100")
    if core100.get("history_status") != "COMPLETE":
        raise RuntimeError("Core100 history is not complete")
    if (core100.get("history_complete_shards"), core100.get("history_total_shards")) != (10, 10):
        raise RuntimeError("Core100 governed shard count changed")
    if core100.get("training_workflow_conclusion") != "success":
        raise RuntimeError("Core100 training workflow is not successful")
    if core100.get("training_report_status") != "PASS":
        raise RuntimeError("Core100 training report is not PASS")

    quality = _require_dict(core100.get("model_quality_gate"), "model quality")
    if quality.get("status") != "REJECT":
        raise RuntimeError("Core100 model-quality state changed")
    if quality.get("automatic_promotion") is not False:
        raise RuntimeError("Core100 rejection cannot authorize promotion")

    replay = _require_dict(core100.get("threshold_replay"), "threshold replay")
    if replay.get("workflow_conclusion") != "success":
        raise RuntimeError("threshold replay is not complete")
    if replay.get("supported_thresholds") != []:
        raise RuntimeError("current replay unexpectedly supports a threshold")
    if replay.get("threshold_change_supported") is not False:
        raise RuntimeError("threshold change unexpectedly became supported")
    if replay.get("configured_threshold_changed") is not False:
        raise RuntimeError("configured threshold changed")

    pionex = _require_dict(current.get("pionex_validation"), "pionex validation")
    if pionex.get("repository_materialization_status") != "PENDING_MANUAL_DISPATCH":
        raise RuntimeError("Pionex repository validation state changed")
    authority = _require_dict(pionex.get("authority"), "Pionex authority")
    if authority.get("public_pionex_kline_reads") is not True:
        raise RuntimeError("Pionex public validation reads unexpectedly disabled")
    if authority.get("r2_validation_dataset_writes") is not True:
        raise RuntimeError("Pionex validation R2 writes unexpectedly disabled")
    for key in (
        "private_api",
        "account_data",
        "replacement_holdout_access",
        "training",
        "source_switch",
        "automatic_model_promotion",
        "formal_trade_plan",
        "real_money_orders",
        "live_trading",
    ):
        if authority.get(key) is not False:
            raise RuntimeError(f"Pionex validation boundary changed: {key}")

    gates = _require_dict(current.get("gates"), "gates")
    if gates.get("holdout") != "FROZEN_UNOPENED":
        raise RuntimeError("replacement holdout state changed")
    if gates.get("live_trading") != "CLOSED":
        raise RuntimeError("live-trading gate changed")
    if gates.get("source_switch_authorized") is not False:
        raise RuntimeError("source-switch boundary changed")

    control = _require_dict(current.get("control_plane"), "control plane")
    if control.get("self_referential_latest_main_sha_allowed") is not False:
        raise RuntimeError("control plane re-enabled self-referential main claims")


def overlay_current_operations(
    dashboard: dict[str, Any], current: dict[str, Any]
) -> dict[str, Any]:
    validate_current_operations(current)

    if dashboard.get("authority") is not False:
        raise RuntimeError("dashboard must remain a non-authoritative projection")
    if dashboard.get("locale") != "zh-Hant-TW":
        raise RuntimeError("dashboard locale changed")

    basis = _require_dict(current["evidence_basis"], "evidence basis")
    core100 = _require_dict(current["core100"], "core100")
    quality = _require_dict(core100["model_quality_gate"], "model quality")
    replay = _require_dict(core100["threshold_replay"], "threshold replay")
    pionex = _require_dict(current["pionex_validation"], "pionex validation")
    pionex_authority = _require_dict(pionex["authority"], "Pionex authority")

    project = _require_dict(dashboard.get("project"), "dashboard project")
    schedule_registration_present = bool(project.get("successorMetadataScheduleEnabled", False))
    project.update(
        {
            "currentOperationsEvidenceBasisSha": str(basis["parent_main_sha"]),
            "currentOperationsEvidenceBasisSemantics": str(basis["semantics"]),
            "currentOperationsEvidenceBasisIsLatestMainClaim": False,
            "currentOperationsUpdatedDate": str(current["updated_date"]),
            "core100HistoryState": "COMPLETE_10_OF_10",
            "core100TrainingState": "COMPLETED_PASS",
            "core100TrainingRunId": int(core100["training_run_id"]),
            "core100ModelQualityState": str(quality["status"]),
            "core100ThresholdReplayState": "COMPLETED_NO_SUPPORTED_THRESHOLD_CHANGE",
            "core100ThresholdReplayRunId": int(replay["run_id"]),
            "core100ThresholdChangeSupported": False,
            "pionexValidationMaterializationState": str(
                pionex["repository_materialization_status"]
            ),
            "pionexValidationPreviousRunId": int(pionex["previous_run_id"]),
            "pionexValidationBoundaryFixPr": int(pionex["boundary_fix_merged_pr"]),
            "pionexValidationManualDispatchOnly": True,
            "currentMetadataCaptureExecutionPath": "NONE_V0_12_WINDOW_ENDED",
            "v0_12SuccessorWindowState": "HISTORICAL_WINDOW_ENDED",
            "v0_12CurrentWindowActive": False,
            "v0_12ScheduleRegistrationPresent": schedule_registration_present,
            "successorMetadataCaptureExecutionAuthorized": False,
            "successorMetadataScheduleEnabled": False,
            "replacementHoldoutState": "FROZEN_UNOPENED",
            "sourceSwitchAuthorized": False,
            "tradePlanAuthorized": False,
            "liveTradingAuthorized": False,
        }
    )
    dashboard["project"] = project

    pipeline_raw = dashboard.get("pipeline") or []
    if not isinstance(pipeline_raw, list):
        raise RuntimeError("dashboard pipeline shape changed")
    pipeline = [_require_dict(row, "pipeline row") for row in pipeline_raw]
    _upsert_status_item(
        pipeline,
        name="Core100 History",
        detail="10/10 governed shards complete；model-quality REJECT 不會自動重啟歷史資料取得。",
        status="COMPLETE",
    )
    _upsert_status_item(
        pipeline,
        name="Core100 Training",
        detail=(
            f"Run {core100['training_run_id']} completed：100 symbols / "
            "18,235,427 rows / 249,228 examples。"
        ),
        status="COMPLETED",
    )
    _upsert_status_item(
        pipeline,
        name="Core100 Threshold Replay",
        detail=(
            f"Run {replay['run_id']} completed；0.50-0.55 無 supported threshold change，"
            "configured threshold 保持不變。"
        ),
        status="COMPLETED_NO_CHANGE",
    )
    _upsert_status_item(
        pipeline,
        name="Pionex Validation Dataset V0.1",
        detail=(
            "PR #321 boundary fix 已進 Repository；新的 materialization 仍等待手動 dispatch。"
            "僅 public K-lines + validation R2，沒有 holdout/training/source-switch/trading authority。"
        ),
        status="PENDING_MANUAL_DISPATCH",
    )
    _upsert_status_item(
        pipeline,
        name="V0.12 Successor Metadata Window",
        detail=(
            "2026-09-04 02:00Z 至 2026-09-12 03:59:59.999Z 的 bounded metadata window 已結束；"
            "保留歷史 lineage，不是目前 active capture path。"
        ),
        status="HISTORICAL",
    )
    dashboard["pipeline"] = pipeline

    gates_raw = dashboard.get("gates") or []
    if not isinstance(gates_raw, list):
        raise RuntimeError("dashboard gates shape changed")
    gates = [_require_dict(row, "gate row") for row in gates_raw]
    _upsert_status_item(
        gates,
        name="Core100 Model Quality",
        detail="Training pipeline PASS 與 model-quality acceptance 分離；目前 quality gate 維持 REJECT。",
        status="REJECT",
        tone="danger",
        critical=True,
    )
    _upsert_status_item(
        gates,
        name="V0.12 Metadata Capture",
        detail="Successor bounded window 已結束；frozen authority 與歷史 evidence 保留，但不再呈現為 current active path。",
        status="HISTORICAL",
        tone="pending",
        critical=False,
    )
    _upsert_status_item(
        gates,
        name="Pionex Repository Validation",
        detail="新的 validation materialization 尚待 manual dispatch；未完成前不得宣稱 Repository-current validation complete。",
        status="PENDING_MANUAL_DISPATCH",
        tone="pending",
        critical=True,
    )
    _upsert_status_item(
        gates,
        name="Replacement Holdout",
        detail="2026-08-28 至 2026-09-03 維持 FROZEN_UNOPENED；Pionex validation 不授權 holdout access。",
        status="NOT_AUTHORIZED",
        tone="blocked",
        critical=True,
    )
    dashboard["gates"] = gates

    security = _require_dict(dashboard.get("securityBoundary"), "security boundary")
    security.update(
        {
            "containsSecrets": False,
            "containsPrivateExchangeResponses": False,
            "authorizesMetadataCapture": False,
            "authorizesPionexValidationMaterialization": True,
            "authorizesPionexPrivateApi": False,
            "authorizesHoldoutAccess": False,
            "authorizesSourceSwitch": False,
            "authorizesPionexNativeRelabeling": False,
            "authorizesTradePlans": False,
            "authorizesLiveTrading": False,
        }
    )
    dashboard["securityBoundary"] = security

    source_authorities = dashboard.get("sourceAuthorities") or []
    if not isinstance(source_authorities, list):
        raise RuntimeError("dashboard sourceAuthorities shape changed")
    current_path = str(CURRENT_OPERATIONS)
    if current_path not in source_authorities:
        source_authorities.append(current_path)
    dashboard["sourceAuthorities"] = source_authorities

    dashboard["schema"] = "qookey-dashboard-authority-snapshot-v0.13"
    dashboard["snapshotLabel"] = (
        "Repository Current Operations 投影 · Core100 History/Training COMPLETE / "
        "Model Quality REJECT / Threshold Replay NO CHANGE / "
        "V0.12 HISTORICAL / Pionex repository validation PENDING"
    )
    dashboard["currentOperationsProjection"] = {
        "authority": False,
        "source": current_path,
        "evidence_basis_parent_main_sha": str(basis["parent_main_sha"]),
        "evidence_basis_semantics": str(basis["semantics"]),
        "is_latest_main_claim": False,
        "updated_date": str(current["updated_date"]),
    }

    if pionex_authority["private_api"] is not False:
        raise RuntimeError("private Pionex API cannot be projected as authorized")
    return dashboard


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--current", type=Path, default=CURRENT_OPERATIONS)
    args = parser.parse_args()

    dashboard = _load(args.input)
    current = _load(args.current)
    result = overlay_current_operations(dashboard, current)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "stage": "DASHBOARD_CURRENT_OPERATIONS_V0_3_OVERLAY_PASS",
                "schema": result["schema"],
                "evidence_basis_parent_main_sha": basis_sha(current),
                "core100_history": result["project"]["core100HistoryState"],
                "core100_training": result["project"]["core100TrainingState"],
                "model_quality": result["project"]["core100ModelQualityState"],
                "pionex_validation": result["project"][
                    "pionexValidationMaterializationState"
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def basis_sha(current: dict[str, Any]) -> str:
    basis = _require_dict(current["evidence_basis"], "evidence basis")
    return str(basis["parent_main_sha"])


if __name__ == "__main__":
    raise SystemExit(main())
