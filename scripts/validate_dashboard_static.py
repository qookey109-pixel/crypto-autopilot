from __future__ import annotations

import json
from pathlib import Path


ROOT = Path("web")
OPERATIONAL_STATUS = ROOT / "data" / "operational-status.json"
REQUIRED = (
    ROOT / "index.html",
    ROOT / "styles.css",
    ROOT / "app.js",
    ROOT / "data" / "dashboard.json",
    OPERATIONAL_STATUS,
    ROOT / "data" / "paper-training.json",
    ROOT / "_headers",
)

FORBIDDEN_TEXT = (
    "R2_SECRET_ACCESS_KEY",
    "R2_ACCESS_KEY_ID",
    "CLOUDFLARE_ACCOUNT_ID",
    "PIONEX_API_SECRET",
    "PIONEX_SECRET",
    "METADATA_RELAY_TOKEN=",
    "sk-proj-",
    "BEGIN PRIVATE KEY",
)

# Metadata-capture authorization is now legitimate under V0.10. Keep the
# dashboard safety validator focused on trading/live execution and secret
# exposure rather than treating metadata execution as a live-order surface.
FORBIDDEN_RUNTIME_PHRASES = (
    "/api/order",
    "/api/orders/create",
    "placeOrder(",
    "submitOrder(",
    "liveTradingAuthorized: true",
    '"liveTradingAuthorized": true',
    '"tradePlanAuthorized": true',
    '"metadataCapturePathsConcurrentAuthorized": true',
)

REQUIRED_ZH_HANT_LABELS = (
    "總覽",
    "資料健康度",
    "交易訊號",
    "模擬持倉",
    "模擬交易",
    "績效中心",
    "回測",
    "風險與閘門",
    "真實交易目前停用",
)


def main() -> int:
    missing = [str(path) for path in REQUIRED if not path.is_file()]
    if missing:
        raise RuntimeError(f"dashboard required files missing: {missing}")

    combined = "\n".join(path.read_text(encoding="utf-8") for path in REQUIRED)
    for token in FORBIDDEN_TEXT:
        if token in combined:
            raise RuntimeError(f"dashboard contains forbidden secret identifier/material: {token}")
    for phrase in FORBIDDEN_RUNTIME_PHRASES:
        if phrase in combined:
            raise RuntimeError(f"dashboard contains forbidden live/concurrent execution phrase: {phrase}")

    data = json.loads((ROOT / "data" / "dashboard.json").read_text(encoding="utf-8"))
    if data.get("authority") is not False:
        raise RuntimeError("dashboard fixture must explicitly declare authority=false")
    if data.get("locale") != "zh-Hant-TW":
        raise RuntimeError("dashboard fixture must declare locale=zh-Hant-TW")

    project = data.get("project") or {}
    if project.get("mode") != "PAPER-ONLY":
        raise RuntimeError("dashboard must remain PAPER-ONLY")
    if project.get("tradePlanAuthorized") is not False:
        raise RuntimeError("dashboard fixture must keep tradePlanAuthorized=false")
    if project.get("liveTradingAuthorized") is not False:
        raise RuntimeError("dashboard fixture must keep liveTradingAuthorized=false")
    if project.get("providerEquivalenceGateState") != "FAIL":
        raise RuntimeError("dashboard fixture must reflect frozen Equivalence V0.1 FAIL")
    if project.get("fundingMaterializationState") != "PASS":
        raise RuntimeError("dashboard fixture must reflect Funding V0.2 materialization PASS")

    # Historical V0.8 preparation remains frozen evidence; current execution
    # ownership must come from the merged V0.10 authority.
    if project.get("renderMetadataV0_8CutoverState") != (
        "HISTORICAL_PREPARED_EXECUTION_NOT_AUTHORIZED"
    ):
        raise RuntimeError("dashboard fixture must preserve V0.8 historical prepared state")
    if project.get("renderMetadataV0_9SmokeState") != "PASS_FROZEN":
        raise RuntimeError("dashboard fixture must reflect frozen V0.9 smoke PASS")
    if project.get("renderMetadataV0_10CutoverState") != "EFFECTIVE_AUTHORIZED":
        raise RuntimeError("dashboard fixture must reflect effective V0.10 cutover")
    if project.get("currentMetadataCaptureExecutionPath") != "github_hosted_ubuntu_v0_10":
        raise RuntimeError("dashboard fixture must reflect V0.10 current capture path")
    if project.get("oldV0_2ScheduledExecutionAuthorized") is not False:
        raise RuntimeError("dashboard fixture must keep V0.2 scheduled execution retired")
    if project.get("successorMetadataCaptureExecutionAuthorized") is not True:
        raise RuntimeError("dashboard fixture must reflect V0.10 metadata capture authority")
    if project.get("successorMetadataScheduleEnabled") is not True:
        raise RuntimeError("dashboard fixture must reflect V0.10 schedule enablement")
    if project.get("metadataCapturePathsConcurrentAuthorized") is not False:
        raise RuntimeError("dashboard fixture must forbid concurrent capture paths")
    if project.get("metadataStabilityState") != "NOT_YET_RUN":
        raise RuntimeError("dashboard fixture must keep metadata stability pending")
    if project.get("replacementHoldoutState") != "FROZEN_UNOPENED":
        raise RuntimeError("dashboard fixture must keep replacement holdout unopened")
    if project.get("sourceSwitchAuthorized") is not False:
        raise RuntimeError("dashboard fixture must keep source switching forbidden")

    operational = json.loads(OPERATIONAL_STATUS.read_text(encoding="utf-8"))
    if operational.get("schema") != "qookey-dashboard-operational-status-v0.1":
        raise RuntimeError("dashboard operational status schema changed")
    if operational.get("authority") is not False:
        raise RuntimeError("dashboard operational status must declare authority=false")
    if operational.get("locale") != "zh-Hant-TW":
        raise RuntimeError("dashboard operational status locale changed")
    op_project = operational.get("project") or {}
    if op_project.get("preWindowReadinessState") != "PASS":
        raise RuntimeError("dashboard must reflect pre-window readiness PASS")
    if op_project.get("v0_10ScheduledObserverState") != "PREPARED":
        raise RuntimeError("dashboard must reflect V0.10 observer PREPARED")
    if op_project.get("v0_10CriticalPathFreezeGuardState") != "PASS_FROZEN":
        raise RuntimeError("dashboard must reflect frozen V0.10 critical-path guard")
    if op_project.get("v0_10CaptureWindowOperationsState") != "PREPARED":
        raise RuntimeError("dashboard must reflect V0.10 capture-window operations PREPARED")
    if op_project.get("v0_10MidWindowEmergencyTemplateState") != "PREPARED_NOT_AUTHORITY":
        raise RuntimeError("dashboard must reflect emergency template as prepared but not authority")
    if op_project.get("v0_10ScheduledAttemptCount") != 388:
        raise RuntimeError("dashboard V0.10 scheduled attempt count changed")
    if op_project.get("manualCaptureBackfillAuthorized") is not False:
        raise RuntimeError("dashboard must keep manual capture backfill unauthorized")
    if op_project.get("retroactiveSlotBackfillAuthorized") is not False:
        raise RuntimeError("dashboard must keep retroactive slot backfill unauthorized")
    if op_project.get("midWindowCriticalMutationDefaultAuthorized") is not False:
        raise RuntimeError("dashboard must keep mid-window critical mutation unauthorized by default")
    if op_project.get("emergencyCriticalPathChangeRequiresVersionedAuthority") is not True:
        raise RuntimeError("dashboard emergency change must require separate versioned authority")
    if op_project.get("emergencyCriticalPathChangeRequiresProtectedMainPr") is not True:
        raise RuntimeError("dashboard emergency change must require protected-main PR")
    if op_project.get("v0_11SyntheticFailureRehearsalState") != "PASS":
        raise RuntimeError("dashboard must reflect V0.11 synthetic rehearsal PASS")
    if op_project.get("v0_11SyntheticScenarioCount") != 12:
        raise RuntimeError("dashboard V0.11 synthetic scenario count changed")
    if op_project.get("v0_11PostWindowExecutionPackageState") != "PREPARED":
        raise RuntimeError("dashboard must reflect V0.11 post-window package PREPARED")
    if op_project.get("v0_11ProductionR2EvaluationState") != "NOT_AUTHORIZED":
        raise RuntimeError("dashboard must keep V0.11 production R2 evaluation unauthorized")
    if op_project.get("metadataStabilityState") != "NOT_YET_RUN":
        raise RuntimeError("dashboard operational metadata stability must remain not-run")
    if op_project.get("replacementHoldoutState") != "FROZEN_UNOPENED":
        raise RuntimeError("dashboard operational holdout must remain unopened")
    if op_project.get("metadataCaptureHourlySlotCount") != 194:
        raise RuntimeError("dashboard operational V0.10 slot count changed")
    if op_project.get("metadataCaptureScheduledMinutesUtc") != [17, 47]:
        raise RuntimeError("dashboard operational scheduled minutes changed")
    for key in (
        "sourceSwitchAuthorized",
        "tradeKlineW1MaterializationAuthorized",
        "realMoneyOrderAuthorized",
        "liveTradingAuthorized",
    ):
        if op_project.get(key) is not False:
            raise RuntimeError(f"dashboard operational safety boundary changed: {key}")
    op_security = operational.get("securityBoundary") or {}
    for key, value in op_security.items():
        if value is not False:
            raise RuntimeError(f"dashboard operational security boundary changed: {key}")

    source_authorities = operational.get("sourceAuthorities") or []
    if "config/v0_10_mid_window_emergency_change_template_v0_1.json" not in source_authorities:
        raise RuntimeError("dashboard emergency-template lineage missing")

    html = (ROOT / "index.html").read_text(encoding="utf-8")
    if '<html lang="zh-Hant-TW">' not in html:
        raise RuntimeError("dashboard HTML must declare zh-Hant-TW")
    for label in REQUIRED_ZH_HANT_LABELS:
        if label not in html:
            raise RuntimeError(f"dashboard Traditional Chinese label missing: {label}")
    for view in (
        "overview",
        "data-health",
        "signals",
        "positions",
        "trades",
        "performance",
        "backtests",
        "gates",
    ):
        if f'id="view-{view}"' not in html:
            raise RuntimeError(f"dashboard view missing: {view}")

    app_js = (ROOT / "app.js").read_text(encoding="utf-8")
    for label in (
        "通過 · PASS",
        "已授權 · AUTHORIZED",
        "已準備 · PREPARED",
        "未授權 · NOT_AUTHORIZED",
        "失敗 · FAIL",
    ):
        if label not in app_js:
            raise RuntimeError(f"dashboard status label missing: {label}")
    for token in (
        "./data/operational-status.json",
        "./data/paper-training.json",
        "mergeOperationalStatus",
        "renderPaperTraining",
        "operational.pipelineItems",
        "operational.gateItems",
    ):
        if token not in app_js:
            raise RuntimeError(f"dashboard operational merge logic missing: {token}")

    paper = json.loads((ROOT / "data" / "paper-training.json").read_text(encoding="utf-8"))
    if paper.get("schema") != "pionex-public-paper-training-run-v0.1":
        raise RuntimeError("dashboard paper-training schema changed")
    if paper.get("mode") != "PAPER_TRAINING_ONLY":
        raise RuntimeError("dashboard paper-training fixture must remain paper-only")
    paper_authority = paper.get("authority") or {}
    for key in (
        "formalTradePlanAuthorized",
        "pionexDemoAutomationAuthorized",
        "privateApiUsed",
        "r2ReadsPerformed",
        "r2WritesPerformed",
        "holdoutAccessed",
        "sourceSwitchAuthorized",
        "realMoneyOrderAuthorized",
        "liveTradingAuthorized",
    ):
        if paper_authority.get(key) is not False:
            raise RuntimeError(f"dashboard paper-training safety boundary changed: {key}")

    headers = (ROOT / "_headers").read_text(encoding="utf-8")
    for header in (
        "Content-Security-Policy",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Permissions-Policy",
    ):
        if header not in headers:
            raise RuntimeError(f"dashboard security header missing: {header}")

    print(
        json.dumps(
            {
                "status": "PASS",
                "stage": "DASHBOARD_ZH_HANT_STATIC_SAFETY_V0_11_OPERATIONAL_PASS",
                "required_files": len(REQUIRED),
                "views": 8,
                "locale": "zh-Hant-TW",
                "authority_fixture": False,
                "operational_authority": False,
                "paper_only": True,
                "equivalence_v0_1": project["providerEquivalenceGateState"],
                "render_v0_10": project["renderMetadataV0_10CutoverState"],
                "metadata_capture_authorized": True,
                "capture_window_operations": op_project["v0_10CaptureWindowOperationsState"],
                "mid_window_emergency_template": op_project["v0_10MidWindowEmergencyTemplateState"],
                "metadata_stability": op_project["metadataStabilityState"],
                "v0_11_synthetic_rehearsal": op_project["v0_11SyntheticFailureRehearsalState"],
                "v0_11_production_r2_evaluation": op_project["v0_11ProductionR2EvaluationState"],
                "holdout": op_project["replacementHoldoutState"],
                "live_execution_surface": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
