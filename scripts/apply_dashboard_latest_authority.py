from __future__ import annotations

import argparse
import json
from pathlib import Path


MATERIALIZATION = Path(
    "research/receipts/2026-08-19-binance-funding-r2-v0-2-materialization.json"
)
R2_USAGE = Path("research/receipts/2026-08-19-r2-bucket-usage.json")
EQUIVALENCE = Path("research/receipts/2026-08-19-pionex-binance-equivalence-v0-1.json")
V05_RENDER_PASS = Path(
    "research/receipts/2026-08-19-provider-equivalence-v0-5-render-free-transport-pass.json"
)
V06_RENDER_TRANSITION = Path(
    "research/receipts/2026-08-19-provider-equivalence-v0-6-render-transport-authority-transition.json"
)
V07_RENDER_PROTOCOL = Path("config/provider_equivalence_v0_7_render_metadata_capture_protocol_v0_1.json")
V08_CUTOVER_PROTOCOL = Path("config/provider_equivalence_v0_8_render_metadata_execution_cutover_v0_1.json")
V08_CUTOVER_RECEIPT = Path(
    "research/receipts/2026-08-19-provider-equivalence-v0-8-render-metadata-cutover-prepared.json"
)
EXPECTED_SCOPE_SHA = "1e0ff54daeec8e5e47376fedb631c663687dd6fb6a4c297d269c33acdf99ad58"
EXPECTED_CHECKSUM_SHA = "881c14d3b3c780b8a0d56ca2f7fd57d2abff310fcd7cb4b13dc01f506b9b64f3"
EXPECTED_EQUIVALENCE_ARTIFACT_SHA = "16975dfcdc34c621b7abe8326cb3cdab0aebffcee27dce2720a8db7f28640af0"
EXPECTED_EQUIVALENCE_RESULT_SHA = "c4ddf68700b03c907fbf43101e9a8a39ead12fa80d395119aa53d3b52e527353"


def load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def replace_pipeline_item(
    items: list[dict[str, object]], name: str, detail: str, status: str
) -> None:
    for item in items:
        if item.get("name") == name:
            item["detail"] = detail
            item["status"] = status
            return
    items.append({"name": name, "detail": detail, "status": status})


def upsert_gate(
    items: list[dict[str, object]],
    name: str,
    detail: str,
    status: str,
    tone: str,
    critical: bool,
) -> None:
    for item in items:
        if item.get("name") == name:
            item.update(
                {
                    "detail": detail,
                    "status": status,
                    "tone": tone,
                    "critical": critical,
                }
            )
            return
    items.append(
        {
            "name": name,
            "detail": detail,
            "status": status,
            "tone": tone,
            "critical": critical,
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    dashboard = load(args.input)
    materialization = load(MATERIALIZATION)
    usage = load(R2_USAGE)
    equivalence = load(EQUIVALENCE)
    v05 = load(V05_RENDER_PASS)
    v06 = load(V06_RENDER_TRANSITION)
    v07 = load(V07_RENDER_PROTOCOL)
    v08 = load(V08_CUTOVER_PROTOCOL)
    v08_receipt = load(V08_CUTOVER_RECEIPT)

    if materialization.get("status") != "PASS":
        raise RuntimeError("Funding materialization authority is not PASS")
    if materialization.get("stage") != "BINANCE_FUNDING_R2_V0_2_MATERIALIZATION_PASS":
        raise RuntimeError("Funding materialization stage changed")
    exact_scope = materialization.get("exact_scope") or {}
    postwrite = materialization.get("postwrite_results") or {}
    blocked = materialization.get("explicitly_not_authorized") or {}
    if not isinstance(exact_scope, dict) or not isinstance(postwrite, dict) or not isinstance(blocked, dict):
        raise RuntimeError("Funding materialization authority shape changed")
    if exact_scope.get("canonical_scope_sha256") != EXPECTED_SCOPE_SHA:
        raise RuntimeError("Funding materialization scope SHA changed")
    if exact_scope.get("source_checksum_set_sha256") != EXPECTED_CHECKSUM_SHA:
        raise RuntimeError("Funding materialization checksum SHA changed")
    if exact_scope.get("source_archive_count") != 1003:
        raise RuntimeError("Funding materialization source count changed")
    if exact_scope.get("annual_canonical_object_count") != 94:
        raise RuntimeError("Funding materialization canonical object count changed")
    if exact_scope.get("authorized_object_identity_count") != 192:
        raise RuntimeError("Funding materialization identity count changed")
    if postwrite.get("actual_r2_materialization_completed") is not True:
        raise RuntimeError("Funding materialization is not complete")
    if postwrite.get("all_192_authorized_objects_verified_after_write") is not True:
        raise RuntimeError("Funding post-write object verification is not PASS")
    if postwrite.get("prewrite_exact_conflict_scan_pass") is not True:
        raise RuntimeError("Funding prewrite exact-conflict scan is not PASS")
    if blocked.get("live_trading_authorized") is not False:
        raise RuntimeError("live trading safety boundary changed")
    if blocked.get("source_switch_authorized") is not False:
        raise RuntimeError("source switch safety boundary changed")

    if usage.get("status") != "PASS" or usage.get("stage") != "R2_BUCKET_USAGE_READ_ONLY_INVENTORY_PASS":
        raise RuntimeError("R2 usage authority is not PASS")
    execution = usage.get("execution") or {}
    inventory = usage.get("inventory") or {}
    if not isinstance(execution, dict) or not isinstance(inventory, dict):
        raise RuntimeError("R2 usage authority shape changed")
    if execution.get("read_only") is not True:
        raise RuntimeError("R2 inventory was not read-only")
    if execution.get("writes_performed") is not False or execution.get("deletes_performed") is not False:
        raise RuntimeError("R2 inventory unexpectedly performed a mutation")
    if inventory.get("total_object_count") != 457 or inventory.get("total_bytes") != 22120404:
        raise RuntimeError("R2 inventory totals changed")

    if equivalence.get("status") != "FAIL":
        raise RuntimeError("Equivalence authority must preserve the frozen FAIL result")
    if equivalence.get("stage") != "PIONEX_BINANCE_EQUIVALENCE_GATE_FAIL":
        raise RuntimeError("Equivalence authority stage changed")
    eq_execution = equivalence.get("execution") or {}
    eq_aggregate = equivalence.get("aggregate") or {}
    eq_boundary = equivalence.get("authority_boundary") or {}
    if not all(isinstance(value, dict) for value in (eq_execution, eq_aggregate, eq_boundary)):
        raise RuntimeError("Equivalence authority shape changed")
    if eq_execution.get("workflow_run_id") != 32206479914:
        raise RuntimeError("Equivalence evidence run changed")
    if eq_execution.get("execution_status") != "PASS":
        raise RuntimeError("Equivalence evidence execution did not complete")
    if eq_execution.get("artifact_zip_sha256") != EXPECTED_EQUIVALENCE_ARTIFACT_SHA:
        raise RuntimeError("Equivalence artifact SHA changed")
    if eq_execution.get("result_json_sha256") != EXPECTED_EQUIVALENCE_RESULT_SHA:
        raise RuntimeError("Equivalence result SHA changed")
    if eq_aggregate.get("gate_status") != "FAIL":
        raise RuntimeError("Equivalence Gate is not frozen FAIL")
    if eq_aggregate.get("evaluated_pair_count") != 45:
        raise RuntimeError("Equivalence pair count changed")
    if (
        eq_aggregate.get("pass_count"),
        eq_aggregate.get("review_count"),
        eq_aggregate.get("fail_count"),
    ) != (18, 18, 9):
        raise RuntimeError("Equivalence aggregate counts changed")
    if eq_boundary.get("source_switch_authorized") is not False:
        raise RuntimeError("Equivalence FAIL must not authorize source switching")
    if eq_boundary.get("staged_trade_kline_w1_materialization_authorized") is not False:
        raise RuntimeError("Equivalence FAIL must keep W1 materialization blocked")
    if eq_boundary.get("live_trading_authorized") is not False:
        raise RuntimeError("Equivalence FAIL must keep live trading blocked")

    if v05.get("status") != "PASS" or v05.get("stage") != "PROVIDER_EQUIVALENCE_V0_5_RENDER_FREE_BINANCE_TRANSPORT_PASS":
        raise RuntimeError("V0.5 Render transport PASS authority changed")
    v05_execution = v05.get("execution_evidence") or {}
    v05_safety = v05.get("sanitization_and_safety") or {}
    if not isinstance(v05_execution, dict) or not isinstance(v05_safety, dict):
        raise RuntimeError("V0.5 authority shape changed")
    if (
        v05_execution.get("upstream_status"),
        v05_execution.get("json_ok"),
        v05_execution.get("symbols_array"),
        v05_execution.get("symbol_count"),
    ) != (200, True, True, 872):
        raise RuntimeError("V0.5 sanitized transport evidence changed")
    if any(v05_safety.get(key) is not False for key in (
        "api_key_used",
        "r2_writes_performed",
        "holdout_candles_accessed",
        "source_switch_performed",
        "live_trading_performed",
    )):
        raise RuntimeError("V0.5 safety boundary changed")

    if v06.get("status") != "PASS" or v06.get("stage") != "PROVIDER_EQUIVALENCE_V0_6_RENDER_TRANSPORT_AUTHORITY_TRANSITION_FROZEN":
        raise RuntimeError("V0.6 Render transition authority changed")
    v06_decision = v06.get("decision") or {}
    v06_boundary = v06.get("authorization_boundary") or {}
    if not isinstance(v06_decision, dict) or not isinstance(v06_boundary, dict):
        raise RuntimeError("V0.6 authority shape changed")
    if v06_decision.get("successor_public_metadata_transport_authority") != "render_free_web_service":
        raise RuntimeError("V0.6 successor transport changed")
    if v06_decision.get("render_metadata_capture_execution_authorized_by_this_receipt") is not False:
        raise RuntimeError("V0.6 must not authorize metadata capture")
    if v06_boundary.get("live_trading_authorized") is not False:
        raise RuntimeError("V0.6 live boundary changed")

    if v07.get("status") != "PROTOCOL_AND_RUNTIME_BOUNDARY_FROZEN_EXECUTION_NOT_AUTHORIZED":
        raise RuntimeError("V0.7 prepared protocol state changed")
    v07_holdout = v07.get("holdout") or {}
    v07_window = v07.get("metadata_capture_window") or {}
    v07_exec = v07.get("execution_boundary") or {}
    if not all(isinstance(value, dict) for value in (v07_holdout, v07_window, v07_exec)):
        raise RuntimeError("V0.7 authority shape changed")
    if v07_holdout.get("state") != "FROZEN_UNOPENED":
        raise RuntimeError("V0.7 replacement holdout state changed")
    if v07_window.get("hourly_slot_count") != 194 or v07_window.get("scheduled_minutes_utc") != [17, 47]:
        raise RuntimeError("V0.7 metadata window changed")
    if v07_exec.get("render_metadata_capture_execution_authorized") is not False:
        raise RuntimeError("V0.7 must remain execution-not-authorized")

    if v08.get("status") != "CUTOVER_CONTRACT_FROZEN_EXECUTION_NOT_AUTHORIZED":
        raise RuntimeError("V0.8 cutover protocol state changed")
    if v08_receipt.get("status") != "PASS" or v08_receipt.get("stage") != "PROVIDER_EQUIVALENCE_V0_8_RENDER_METADATA_CUTOVER_PREPARED_EXECUTION_NOT_AUTHORIZED":
        raise RuntimeError("V0.8 cutover preparation receipt changed")
    v08_current = v08.get("current_execution_path") or {}
    v08_successor = v08.get("successor_execution_path") or {}
    v08_cutover = v08.get("atomic_cutover_contract") or {}
    v08_boundary = v08.get("authorization_boundary") or {}
    if not all(isinstance(value, dict) for value in (v08_current, v08_successor, v08_cutover, v08_boundary)):
        raise RuntimeError("V0.8 authority shape changed")
    if v08_current.get("transport") != "github_self_hosted_mac":
        raise RuntimeError("V0.8 current execution path changed")
    if v08_successor.get("binance_transport") != "render_free_web_service":
        raise RuntimeError("V0.8 successor transport changed")
    if v08_successor.get("successor_schedule_enabled_now") is not False:
        raise RuntimeError("V0.8 successor schedule must remain disabled")
    if v08_cutover.get("atomic_activation_required") is not True:
        raise RuntimeError("V0.8 atomic activation requirement changed")
    if v08_cutover.get("concurrent_old_and_new_capture_paths_authorized") is not False:
        raise RuntimeError("V0.8 concurrent capture paths must remain forbidden")
    if v08_boundary.get("successor_scheduled_capture_activation_authorized") is not False:
        raise RuntimeError("V0.8 must not authorize successor schedule")
    if v08_boundary.get("metadata_only_r2_writes_authorized_by_this_protocol") is not False:
        raise RuntimeError("V0.8 preparation must not authorize metadata writes")
    if v08_boundary.get("holdout_candle_access_authorized") is not False:
        raise RuntimeError("V0.8 holdout must remain unopened")
    if v08_boundary.get("live_trading_authorized") is not False:
        raise RuntimeError("V0.8 live boundary changed")

    project = dashboard.get("project") or {}
    if not isinstance(project, dict):
        raise RuntimeError("dashboard project shape changed")
    if project.get("mode") != "PAPER-ONLY" or project.get("liveTradingAuthorized") is not False:
        raise RuntimeError("dashboard safety boundary changed")

    project.update(
        {
            "fundingMaterializationComplete": True,
            "fundingMaterializationState": "PASS",
            "fundingV0_2UploadedObjectCount": int(postwrite["uploaded_object_count"]),
            "fundingV0_2VerifiedExistingObjectCount": int(postwrite["verified_existing_object_count"]),
            "r2BucketObjectCount": int(inventory["total_object_count"]),
            "r2BucketBytes": int(inventory["total_bytes"]),
            "r2BucketMBDecimal": float(inventory["total_MB_decimal"]),
            "r2BucketMiBBinary": float(inventory["total_MiB_binary"]),
            "providerEquivalenceGateState": "FAIL",
            "providerEquivalencePassCount": int(eq_aggregate["pass_count"]),
            "providerEquivalenceReviewCount": int(eq_aggregate["review_count"]),
            "providerEquivalenceFailCount": int(eq_aggregate["fail_count"]),
            "sourceSwitchAuthorized": False,
            "tradeKlineW1MaterializationAuthorized": False,
            "renderTransportV0_5State": "PASS",
            "renderTransportV0_6AuthorityState": "PASS",
            "renderMetadataV0_7State": "PREPARED_EXECUTION_NOT_AUTHORIZED",
            "renderMetadataV0_8CutoverState": "PREPARED_EXECUTION_NOT_AUTHORIZED",
            "metadataStabilityState": "NOT_YET_RUN",
            "replacementHoldoutState": "FROZEN_UNOPENED",
            "currentMetadataCaptureExecutionPath": "github_self_hosted_mac",
            "successorMetadataCaptureTransport": "render_free_web_service",
            "successorMetadataCaptureExecutionAuthorized": False,
            "successorMetadataScheduleEnabled": False,
            "metadataCapturePathsConcurrentAuthorized": False,
            "cloudRuntimeMonthlyBudgetUsd": 0,
        }
    )
    dashboard["project"] = project
    dashboard["schema"] = "qookey-dashboard-authority-snapshot-v0.6"
    dashboard["snapshotLabel"] = (
        "Repository 正式 Authority 狀態快照 · Equivalence V0.1 FAIL / "
        "Funding V0.2 R2 PASS / Render V0.8 Cutover PREPARED"
    )

    pipeline = dashboard.get("pipeline") or []
    if not isinstance(pipeline, list):
        raise RuntimeError("dashboard pipeline shape changed")
    normalized: list[dict[str, object]] = []
    for item in pipeline:
        if not isinstance(item, dict):
            raise RuntimeError("dashboard pipeline row shape changed")
        normalized.append(item)
    replace_pipeline_item(
        normalized,
        "Funding V0.2 實際 R2 Materialization",
        "正式 run 32168151926 已完成：192/192 identities post-write 驗證 PASS；HYPEUSDT 2026 仍維持 deferred。",
        "PASS",
    )
    replace_pipeline_item(
        normalized,
        "R2 實際使用容量",
        "唯讀 inventory：457 objects / 22.120404 MB；檢查本身沒有寫入或刪除。",
        "PASS",
    )
    replace_pipeline_item(
        normalized,
        "Pionex ↔ Binance 等價性",
        "凍結 V0.1 已完成 45/45 pairs：18 PASS / 18 REVIEW / 9 FAIL。source switch 與 W1 materialization 維持未授權。",
        "FAIL",
    )
    replace_pipeline_item(
        normalized,
        "Render Free Binance Transport",
        "V0.5 Frankfurt transport PASS，V0.6 successor transport authority PASS；公開 exchangeInfo sanitized evidence symbol_count=872。",
        "PASS",
    )
    replace_pipeline_item(
        normalized,
        "Render Metadata V0.7 Protocol",
        "Successor relay/runtime boundary 已準備，但 execution gate 仍 hard-disabled，沒有 metadata capture 或 R2 write。",
        "PREPARED",
    )
    replace_pipeline_item(
        normalized,
        "Render Metadata V0.8 Cutover",
        "Atomic cutover contract 已準備；舊 V0.2 self-hosted path 仍是目前已授權 execution path，successor schedule 尚未啟用。",
        "PREPARED",
    )
    dashboard["pipeline"] = normalized

    gates = dashboard.get("gates") or []
    if not isinstance(gates, list):
        raise RuntimeError("dashboard gates shape changed")
    normalized_gates: list[dict[str, object]] = []
    for item in gates:
        if not isinstance(item, dict):
            raise RuntimeError("dashboard gate row shape changed")
        normalized_gates.append(item)
    upsert_gate(
        normalized_gates,
        "R2 儲存預算",
        "目前實際 R2 使用 22.120404 MB / 457 objects；V0.8 未授權任何 metadata write，未來寫入前仍須通過 FREE-ONLY 8 GB headroom gate。",
        "PASS",
        "pass",
        False,
    )
    upsert_gate(
        normalized_gates,
        "Provider 等價性",
        "V0.1 Gate 正式 FAIL：45 pairs 中 9 FAIL；不得降低 frozen thresholds，也不得以 Binance 取代 Pionex provenance。",
        "FAIL",
        "danger",
        True,
    )
    upsert_gate(
        normalized_gates,
        "Render Metadata Cutover",
        "V0.8 僅 PREPARED：shared relay secret 尚須 out-of-band provision，successor execution/schedule 未授權，且禁止與 V0.2 self-hosted path 同時 capture。",
        "NOT_AUTHORIZED",
        "blocked",
        True,
    )
    upsert_gate(
        normalized_gates,
        "Replacement Holdout",
        "2026-08-28 至 2026-09-03 維持 FROZEN_UNOPENED；metadata stability PASS 之前與獨立 holdout-access authority 之前不得讀取或評估。",
        "NOT_AUTHORIZED",
        "blocked",
        True,
    )
    dashboard["gates"] = normalized_gates

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(dashboard, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "stage": "DASHBOARD_LATEST_AUTHORITY_OVERLAY_V0_8_PASS",
                "funding_materialization_state": project["fundingMaterializationState"],
                "equivalence_gate_state": project["providerEquivalenceGateState"],
                "render_v0_5": project["renderTransportV0_5State"],
                "render_v0_6": project["renderTransportV0_6AuthorityState"],
                "render_v0_7": project["renderMetadataV0_7State"],
                "render_v0_8": project["renderMetadataV0_8CutoverState"],
                "current_capture_path": project["currentMetadataCaptureExecutionPath"],
                "successor_capture_authorized": project[
                    "successorMetadataCaptureExecutionAuthorized"
                ],
                "holdout_state": project["replacementHoldoutState"],
                "r2_objects": project["r2BucketObjectCount"],
                "r2_bytes": project["r2BucketBytes"],
                "paper_only": project["mode"] == "PAPER-ONLY",
                "live_trading": project["liveTradingAuthorized"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
