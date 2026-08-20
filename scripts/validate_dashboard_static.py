from __future__ import annotations

import json
from pathlib import Path


ROOT = Path("web")
REQUIRED = (
    ROOT / "index.html",
    ROOT / "styles.css",
    ROOT / "app.js",
    ROOT / "data" / "dashboard.json",
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
                "stage": "DASHBOARD_ZH_HANT_STATIC_SAFETY_V0_10_PASS",
                "required_files": len(REQUIRED),
                "views": 8,
                "locale": "zh-Hant-TW",
                "authority_fixture": False,
                "paper_only": True,
                "equivalence_v0_1": project["providerEquivalenceGateState"],
                "render_v0_10": project["renderMetadataV0_10CutoverState"],
                "metadata_capture_authorized": True,
                "metadata_stability": project["metadataStabilityState"],
                "holdout": project["replacementHoldoutState"],
                "live_execution_surface": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
