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
    "sk-proj-",
    "BEGIN PRIVATE KEY",
)

FORBIDDEN_RUNTIME_PHRASES = (
    "/api/order",
    "/api/orders/create",
    "placeOrder(",
    "submitOrder(",
    "liveTradingAuthorized: true",
    '"liveTradingAuthorized": true',
    '"tradePlanAuthorized": true',
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
            raise RuntimeError(f"dashboard contains forbidden live execution phrase: {phrase}")

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
    if "通過 · PASS" not in app_js or "未授權 · NOT_AUTHORIZED" not in app_js:
        raise RuntimeError("dashboard must preserve raw authority codes beside Chinese labels")

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
                "stage": "DASHBOARD_ZH_HANT_STATIC_SAFETY_PASS",
                "required_files": len(REQUIRED),
                "views": 8,
                "locale": "zh-Hant-TW",
                "authority_fixture": False,
                "paper_only": True,
                "live_execution_surface": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
