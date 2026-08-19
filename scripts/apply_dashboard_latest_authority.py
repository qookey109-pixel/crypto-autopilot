from __future__ import annotations

import argparse
import json
from pathlib import Path


MATERIALIZATION = Path(
    "research/receipts/2026-08-19-binance-funding-r2-v0-2-materialization.json"
)
R2_USAGE = Path("research/receipts/2026-08-19-r2-bucket-usage.json")
EXPECTED_SCOPE_SHA = "1e0ff54daeec8e5e47376fedb631c663687dd6fb6a4c297d269c33acdf99ad58"
EXPECTED_CHECKSUM_SHA = "881c14d3b3c780b8a0d56ca2f7fd57d2abff310fcd7cb4b13dc01f506b9b64f3"


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    dashboard = load(args.input)
    materialization = load(MATERIALIZATION)
    usage = load(R2_USAGE)

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
        }
    )
    dashboard["project"] = project
    dashboard["schema"] = "qookey-dashboard-authority-snapshot-v0.4"
    dashboard["snapshotLabel"] = "Repository 正式 Authority 狀態快照 · Funding V0.2 R2 PASS"

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
    dashboard["pipeline"] = normalized

    gates = dashboard.get("gates") or []
    if not isinstance(gates, list):
        raise RuntimeError("dashboard gates shape changed")
    for item in gates:
        if isinstance(item, dict) and item.get("name") == "R2 儲存預算":
            item["detail"] = "目前實際 R2 使用 22.120404 MB / 457 objects；仍遠低於既有 10 GB BLOCK guardrail。"
            item["status"] = "PASS"
            item["tone"] = "pass"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dashboard, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "PASS",
                "stage": "DASHBOARD_LATEST_AUTHORITY_OVERLAY_PASS",
                "funding_materialization_state": project["fundingMaterializationState"],
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
