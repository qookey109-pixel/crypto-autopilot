from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TypedDict


ROOT = Path("web")
APP_JS = ROOT / "assets" / "js" / "app.js"
STYLES = ROOT / "assets" / "css" / "styles.css"
ACTIVE_IMAGE = ROOT / "assets" / "images" / "cloud-garden-v4.jpg"
OPERATIONAL_STATUS = ROOT / "data" / "operational-status.json"
RESEARCH_CALENDAR = ROOT / "data" / "research-calendar.json"
OPERATIONS_SCHEDULE = ROOT / "data" / "operations-schedule.json"
RESEARCH_EVIDENCE = ROOT / "data" / "research-evidence.json"
RESEARCH_EVIDENCE_SCHEMA = ROOT / "data" / "research-evidence.schema.json"
ALTERNATIVE_ASSETS = ROOT / "data" / "alternative-assets.json"
HISTORY_PROGRESS = ROOT / "data" / "history-progress.json"
CLOUD_RUNS = ROOT / "data" / "cloud-runs.json"
CLOUD_PAPER_LOOP = ROOT / "data" / "cloud-paper-loop.json"
ZEC_COMPLETION_RECEIPT = Path("research/receipts/2026-09-21-zec-v0-3-development-completion-v0-1.json")
REQUIRED = (
    ROOT / "index.html",
    STYLES,
    ROOT / "assets" / "css" / "variables.css",
    APP_JS,
    ROOT / "data" / "dashboard.json",
    OPERATIONAL_STATUS,
    ROOT / "data" / "paper-training.json",
    ROOT / "data" / "strategy.json",
    RESEARCH_CALENDAR,
    OPERATIONS_SCHEDULE,
    RESEARCH_EVIDENCE,
    RESEARCH_EVIDENCE_SCHEMA,
    ALTERNATIVE_ASSETS,
    HISTORY_PROGRESS,
    CLOUD_RUNS,
    CLOUD_PAPER_LOOP,
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
    "進場時間",
    "出場時間",
    "策略",
    "模擬持倉",
    "模擬交易",
    "績效中心",
    "回測",
    "風險與閘門",
    "真實交易目前停用",
    "研究時程與授權狀態",
    "自動化排程與來源狀態",
    "SState 是 4H 市場狀態與背景准入閘門",
    "投影建立：尚未提供",
    "Paper 觀測：尚未完成",
    "未提供資料時不推算持倉",
    "研究結果不等於正式准入",
    "股票代幣、ETF 與金屬資料池",
    "網站只顯示安全摘要",
    "最近一次逐市場決策軌跡",
    "尚無正式循環報告",
)


class CloudPaperUsageContract(TypedDict):
    version: str
    budget_state: str
    d1_state: str
    fields: dict[str, object]


def validate_cloud_paper_usage_evidence(budget: dict[str, object]) -> str:
    """Validate reviewed partial evidence; this never grants runtime authority."""
    contracts: dict[str, CloudPaperUsageContract] = {
        "cloud_paper_usage_audit_v0_2": {
            "version": "V0.2",
            "budget_state": "REVIEW_REQUIRED_V0_2_DATASET_COVERAGE_INCOMPLETE",
            "d1_state": "UNKNOWN_EMPTY_UNVERIFIED",
            "fields": {
                "authority": "cloud_paper_usage_audit_v0_2",
                "status": "REVIEW_REQUIRED",
                "reason_code": "DATASET_COVERAGE_INCOMPLETE",
                "run_id": 36584465739,
                "attempt": 1,
                "run_head_sha": "21d37a44c6f3c5bba340908705488a05e7a5f7c7",
                "artifact_id": 11041290995,
                "artifact_name": "cloud-paper-usage-audit-v0-2-36584465739-1",
                "artifact_sha256": "9ece6ff0a937f930d1137b2539052833bb5d94960dff8c1e50cce4cdbdadc258",
                "cloudflare_requests": 1,
                "d1_rows_state": "EMPTY_UNVERIFIED",
                "d1_storage_state": "EMPTY_UNVERIFIED",
                "r2_operations_state": "LIMIT_REACHED",
                "r2_operations_group_count": 10000,
                "r2_storage_state": "PRESENT",
                "r2_storage_group_count": 1297,
                "account_wide_cost": "UNKNOWN",
                "complete_storage_byte_aggregate": "UNKNOWN",
                "shared_writer_coverage": "UNKNOWN",
                "storage_headroom": "UNKNOWN"
            }
        },
        "cloud-paper-r2-usage-audit-v0.3": {
            "version": "V0.3",
            "budget_state": "REVIEW_REQUIRED_V0_3_R2_METRICS_PARTIAL",
            "d1_state": "UNKNOWN_NOT_QUERIED_BY_V0_3",
            "fields": {
                "authority": "cloud-paper-r2-usage-audit-v0.3",
                "status": "READY_FOR_REVIEW",
                "reason_code": "R2_METRICS_CAPTURED_REVIEW_ONLY",
                "run_id": 36593296360,
                "attempt": 1,
                "run_head_sha": "2516a80c32fa04b9789bef379b108eb50c87fd49",
                "artifact_id": 11045150561,
                "artifact_name": "cloud-paper-r2-usage-audit-v0-3-36593296360-1",
                "artifact_sha256": "581514f59892b84520e52ef463e00210e4175952cc0d54af7fda42b18c71c1be",
                "cloudflare_requests": 1,
                "d1_rows_state": "NOT_QUERIED_IN_V0_3",
                "d1_storage_state": "NOT_QUERIED_IN_V0_3",
                "r2_operations_state": "PRESENT",
                "r2_operations_group_count": 6,
                "r2_operations_total_requests": 125309,
                "r2_operations_freshness": "UNKNOWN_QUERY_OMITS_DATETIME_DIMENSION",
                "r2_storage_state": "PRESENT",
                "r2_storage_group_count": 1298,
                "returned_bucket_group_count": 1,
                "object_count": 16304,
                "payload_bytes": 612538247,
                "metadata_bytes": 4003533,
                "total_bytes": 616541780,
                "upload_count": 0,
                "latest_snapshot_utc": "2026-09-29T15:20:00Z",
                "account_wide_cost": "UNKNOWN",
                "complete_storage_byte_aggregate": "UNKNOWN",
                "shared_writer_coverage": "UNKNOWN",
                "storage_headroom": "UNKNOWN"
            }
        }
    }
    evidence = budget.get("usage_audit_evidence")
    if not isinstance(evidence, dict):
        raise RuntimeError("Cloud Paper usage evidence must be an object")
    authority = evidence.get("authority")
    if not isinstance(authority, str) or authority not in contracts:
        raise RuntimeError("Cloud Paper usage authority is unsupported")
    contract = contracts[authority]
    for key, expected in contract["fields"].items():
        if key not in evidence or type(evidence[key]) is not type(expected) or evidence[key] != expected:
            raise RuntimeError(f"Cloud Paper usage evidence changed: {key}")
    required = {
        "monthly_budget_usd": 0,
        "state": "BLOCKED_BUDGET",
        "account_wide_usage_evidence": contract["budget_state"],
        "d1_free_tier_usage_evidence": contract["d1_state"],
        "zero_cost_conclusion": "UNKNOWN",
        "account_wide_writer_coverage": "UNKNOWN",
    }
    for key, expected in required.items():
        if key not in budget or type(budget[key]) is not type(expected) or budget[key] != expected:
            raise RuntimeError(f"Cloud Paper budget evidence changed: {key}")
    capacity = budget.get("storage_capacity")
    if not isinstance(capacity, dict) or "measured_storage_bytes" not in capacity:
        raise RuntimeError("Cloud Paper capacity evidence is missing")
    if capacity["measured_storage_bytes"] is not None or capacity.get("all_writer_coverage_proven") is not False:
        raise RuntimeError("partial storage observation cannot prove account-wide headroom")
    return contract["version"]


def validate_cloud_paper_billing_evidence(cloud_paper: dict[str, object]) -> None:
    evidence = cloud_paper.get("billing_evidence")
    if not isinstance(evidence, dict):
        raise RuntimeError("Cloud Paper billing evidence must be an object")
    expected = {
        "updated_date": "2026-10-02",
        "authority": "cloud-paper-billing-evidence-v0.1",
        "subscription_snapshot": {
            "run_id": 36513941565,
            "attempt": 1,
            "event": "workflow_dispatch",
            "workflow_conclusion": "success",
            "run_head_sha": "414cf9a0a3b60612f9d1e09d7c5d29d76b05455e",
            "artifact_id": 11009764477,
            "artifact_digest": "sha256:7a2d8c5dce415392614c90266ebc8e7625e40cc2e92a19bc457c8cd9fd7d3338",
            "artifact_expires_at_utc": "2026-10-06T02:43:49Z",
            "observed_date": "2026-10-01",
            "report_status": "READY_FOR_BILLING_REVIEW",
            "rate_plan_id": "r2_paid",
            "state": "Paid",
            "listed_price_usd": 0,
            "listed_subscription_price_total_usd": 0,
            "invoices_included": False,
            "metered_charges_included": False,
            "complete_account_product_coverage": False,
            "all_writers_established": False,
            "rate_plan_id_documentation_check": {
                "classification": "UNMAPPED_DOCUMENTED_ENUM_REQUIRES_REVIEW",
                "additional_cloudflare_request_performed": False,
            },
            "run_url": "https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36513941565",
        },
        "billable_usage_snapshot": {
            "run_id": 36852292356,
            "attempt": 1,
            "event": "workflow_dispatch",
            "workflow_conclusion": "success",
            "run_head_sha": "54c099254303512eba7f8f2b57dcd98124b17348",
            "artifact_id": 11156336210,
            "artifact_digest": "sha256:aafc0e4c58bdb8d25426a390c1d9689ce77324ef2c780d91e6fcc2f90c1bbcbf",
            "observed_at_utc": "2026-10-01T10:57:13.348117Z",
            "report_reason_code": "USAGE_ROWS_CAPTURED_REVIEW_REQUIRED_FOR_SCOPE",
            "response_row_count": 42,
            "every_row_has_billed_cost_fields": True,
            "reported_billed_cost_total": 0,
            "currency": "USD",
            "fixed_subscription_charges_included": False,
            "daily_provider_data_may_lag": True,
            "complete_account_usage_coverage": "UNKNOWN_UNTIL_REVIEWED",
            "cloudflare_http_requests_performed": 1,
            "run_url": "https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36852292356",
        },
        "total_cloudflare_http_requests": 2,
        "account_wide_cost": "UNKNOWN",
        "account_wide_writer_coverage": "UNKNOWN",
        "writer_inventory_state": "INCOMPLETE_USER_EXPECTS_ADDITIONAL_SERVICES_LATER",
        "zero_cost_conclusion": "NOT_PROVEN",
        "authority_consumed": True,
        "rerun_authorized": False,
        "cloud_paper_activation": "REMAINS_DISABLED",
    }
    if evidence != expected:
        raise RuntimeError("Cloud Paper billing evidence changed or is incomplete")
    if cloud_paper.get("billing_evidence") != evidence:
        raise RuntimeError("Cloud Paper billing evidence is not stable")


def main() -> int:
    missing = [str(path) for path in REQUIRED if not path.is_file()]
    if missing:
        raise RuntimeError(f"dashboard required files missing: {missing}")
    if not ACTIVE_IMAGE.is_file():
        raise RuntimeError("dashboard active background image is missing")
    for retired in (
        "market-orbit-v2.jpg",
        "research-constellation-v1.jpg",
        "research-orbit-v3.jpg",
    ):
        if any((ROOT / "assets").rglob(retired)):
            raise RuntimeError(f"retired dashboard design asset returned: {retired}")

    combined = "\n".join(path.read_text(encoding="utf-8") for path in REQUIRED)
    for token in FORBIDDEN_TEXT:
        if token in combined:
            raise RuntimeError(f"dashboard contains forbidden secret identifier/material: {token}")
    for phrase in FORBIDDEN_RUNTIME_PHRASES:
        if phrase in combined:
            raise RuntimeError(f"dashboard contains forbidden live/concurrent execution phrase: {phrase}")

    cloud_paper = json.loads(CLOUD_PAPER_LOOP.read_text(encoding="utf-8"))
    if cloud_paper.get("schema") != "qookey-cloud-paper-dashboard-v0.1":
        raise RuntimeError("Cloud Paper dashboard projection schema changed")
    if cloud_paper.get("authority") is not False:
        raise RuntimeError("Cloud Paper dashboard projection must remain non-authoritative")
    if (cloud_paper.get("activation") or {}).get("enabled") is not False:
        raise RuntimeError("Cloud Paper dashboard fixture must remain inactive")
    latest_cloud_run = cloud_paper.get("latest_run") or {}
    if latest_cloud_run.get("status") != "NOT_RUN":
        raise RuntimeError("checked-in Cloud Paper projection must not invent a formal run")
    if latest_cloud_run.get("decision_trace_status") != "NOT_AVAILABLE_NO_OFFICIAL_RUN":
        raise RuntimeError("Cloud Paper trace must remain unavailable without an official run")
    if (cloud_paper.get("strategy") or {}).get("registry_status") != "EMPTY_NO_ELIGIBLE_STRATEGIES":
        raise RuntimeError("Cloud Paper strategy registry fixture changed")
    if cloud_paper.get("model_quality") != "REJECT":
        raise RuntimeError("Cloud Paper model quality must remain REJECT")
    account = cloud_paper.get("account") or {}
    if account.get("initialized") is not False or account.get("planned_initial_equity_usd") != 10000:
        raise RuntimeError("Cloud Paper account must remain uninitialized")
    if any(key not in account or account[key] is not None for key in (
        "confirmed_equity_usd", "open_position_count", "realized_pnl_usd", "unrealized_pnl_usd",
    )):
        raise RuntimeError("Cloud Paper account values are unknown without a formal run")
    cloud_budget = cloud_paper.get("budget") or {}
    validate_cloud_paper_usage_evidence(cloud_budget)
    validate_cloud_paper_billing_evidence(cloud_paper)
    if cloud_budget.get("reservation_guard") != "PROVIDER_R2_GUARD_IMPLEMENTED_RUNTIME_NOT_ACTIVATED":
        raise RuntimeError("Cloud Paper provider/R2 guard projection changed")
    if cloud_budget.get("d1_reservation_ledger") != "SHARED_LEDGER_CODE_PREPARED_MIGRATIONS_NOT_APPLIED_D1_NOT_PROVISIONED":
        raise RuntimeError("Cloud Paper D1 reservation ledger status changed")
    capacity = cloud_budget.get("storage_capacity") or {}
    if capacity.get("state") != "USAGE_PARTIAL_BLOCKED":
        raise RuntimeError("Cloud Paper storage usage must remain blocked with partial evidence")
    if capacity.get("measured_storage_bytes") is not None:
        raise RuntimeError("unknown Cloud Paper storage usage must remain null, not zero")
    if capacity.get("usage_evidence") != "PARTIAL_R2_EVIDENCE_NOT_ZERO_OR_COMPLETE":
        raise RuntimeError("Cloud Paper storage evidence must remain partial and nonzero-unproven")
    if capacity.get("report_object_max_bytes") != 262_144:
        raise RuntimeError("Cloud Paper per-object storage ceiling changed")
    if capacity.get("per_run_growth_max_bytes") != 2_097_152:
        raise RuntimeError("Cloud Paper per-run storage ceiling changed")
    if capacity.get("per_utc_day_growth_max_bytes") != 201_326_592:
        raise RuntimeError("Cloud Paper daily storage ceiling changed")
    if capacity.get("max_31_day_growth_bytes") != 6_241_124_352:
        raise RuntimeError("Cloud Paper 31-day growth envelope changed")
    if capacity.get("warning_threshold_bytes") != 6_400_000_000:
        raise RuntimeError("Cloud Paper storage warning threshold changed")
    if capacity.get("hard_stop_bytes") != 8_000_000_000:
        raise RuntimeError("Cloud Paper storage hard stop changed")
    if capacity.get("all_writer_coverage_proven") is not False:
        raise RuntimeError("Cloud Paper writer coverage must remain unproven")
    production = cloud_paper.get("production") or {}
    if production.get("entrypoint_workflow") != "NOT_WIRED":
        raise RuntimeError("Cloud Paper production entrypoint must remain not wired")
    if production.get("natural_schedule") != "NOT_CONFIGURED":
        raise RuntimeError("Cloud Paper natural schedule must remain unconfigured")
    cloud_boundary = cloud_paper.get("boundary") or {}
    if cloud_boundary.get("paper_only") is not True or any(
        cloud_boundary.get(key) is not False
        for key in (
            "real_money_orders", "live_trading", "holdout_access",
            "source_switch", "model_promotion",
        )
    ):
        raise RuntimeError("Cloud Paper dashboard safety boundary changed")

    data = json.loads((ROOT / "data" / "dashboard.json").read_text(encoding="utf-8"))
    strategy_projection = json.loads((ROOT / "data" / "strategy.json").read_text(encoding="utf-8"))
    if strategy_projection.get("schema") != "qookey-dashboard-strategy-projection-v0.1":
        raise RuntimeError("dashboard strategy projection schema changed")
    if strategy_projection.get("authority") is not False:
        raise RuntimeError("dashboard strategy projection must remain non-authoritative")
    if strategy_projection.get("generatedAtUtc") is not None:
        raise RuntimeError("checked-in strategy fixture must not invent a generation time")
    if any(value is not False for value in strategy_projection.get("safetyBoundary", {}).values()):
        raise RuntimeError("dashboard strategy projection safety boundary changed")
    strategy = strategy_projection.get("baseline") or {}
    if strategy.get("version") != "0.1.0":
        raise RuntimeError("dashboard strategy version changed without a strategy update")
    if strategy.get("mode") != "paper" or strategy.get("direction") != "LONG_ONLY":
        raise RuntimeError("dashboard strategy must remain paper LONG_ONLY")
    if data.get("authority") is not False:
        raise RuntimeError("dashboard fixture must explicitly declare authority=false")
    if data.get("locale") != "zh-Hant-TW":
        raise RuntimeError("dashboard fixture must declare locale=zh-Hant-TW")
    if data.get("generatedAtUtc") is not None:
        raise RuntimeError("checked-in dashboard fixture must not invent a generation time")

    cloud_runs = json.loads(CLOUD_RUNS.read_text(encoding="utf-8"))
    if cloud_runs.get("schema") != "qookey-cloud-run-status-v0.2":
        raise RuntimeError("cloud monitoring fixture schema changed")
    if cloud_runs.get("authority") is not False:
        raise RuntimeError("cloud monitoring fixture must remain non-authoritative")
    if cloud_runs.get("mode") != "GITHUB_ACTIONS_METADATA_ONLY":
        raise RuntimeError("cloud monitoring fixture must remain metadata-only")
    if cloud_runs.get("observedAtUtc") is not None:
        raise RuntimeError("checked-in cloud monitoring fixture must not invent observation time")
    cloud_summary = cloud_runs.get("summary") or {}
    if cloud_summary.get("repositoryCronDeclarationCount") != 8:
        raise RuntimeError("cloud monitoring Repository cron declaration count changed")
    if cloud_summary.get("monitoredCronDeclarationCount") != 8:
        raise RuntimeError("cloud monitoring Health declaration count changed")
    if cloud_summary.get("currentEffectiveScheduleCount") != 7:
        raise RuntimeError("cloud monitoring current-effective schedule count changed")
    if cloud_summary.get("expiredScheduleCount") != 1:
        raise RuntimeError("cloud monitoring expired schedule count changed")
    if cloud_summary.get("pendingScheduleCount") != 0:
        raise RuntimeError("cloud monitoring pending schedule count changed")
    if cloud_summary.get("expiredFrozenCronDeclarationCount") != 1:
        raise RuntimeError("cloud monitoring expired frozen declaration count changed")
    cloud_items = cloud_runs.get("items") or []
    if len(cloud_items) != 8:
        raise RuntimeError("cloud monitoring fixture must contain all eight cron declarations")
    if sum(
        item.get("lifecycleState") == "CURRENT_EFFECTIVE"
        for item in cloud_items
    ) != 7:
        raise RuntimeError("cloud monitoring current-effective lifecycle split changed")
    if sum(
        item.get("lifecycleState") == "EXPIRED_BOUNDED_FROZEN_CRON_DECLARATION"
        for item in cloud_items
    ) != 1:
        raise RuntimeError("cloud monitoring frozen-expired lifecycle split changed")
    for item in cloud_items:
        if (item.get("businessResult") or {}).get("status") != (
            "UNKNOWN_FROM_GITHUB_RUN_METADATA"
        ):
            raise RuntimeError("cloud monitoring must not infer business results from run metadata")
        latest = item.get("latestAutomaticRun") or {}
        if latest.get("runId") is not None or latest.get("headSha") is not None:
            raise RuntimeError("checked-in cloud monitoring fixture must not invent run evidence")
    cloud_boundary = cloud_runs.get("safetyBoundary") or {}
    if not cloud_boundary or any(value is not False for value in cloud_boundary.values()):
        raise RuntimeError("cloud monitoring safety boundary changed")

    alternative_assets = json.loads(ALTERNATIVE_ASSETS.read_text(encoding="utf-8"))
    if alternative_assets.get("schema") != (
        "qookey-pionex-alternative-assets-projection-v0.2"
    ):
        raise RuntimeError("alternative-assets projection schema changed")
    if alternative_assets.get("authority") is not False:
        raise RuntimeError("alternative-assets projection must remain non-authoritative")
    if alternative_assets.get("mode") != "METADATA_ONLY_READ_ONLY":
        raise RuntimeError("alternative-assets projection must remain metadata-only")
    if alternative_assets.get("status") != "WAITING_FIRST_RUN":
        raise RuntimeError("checked-in alternative-assets fixture must await its first run")
    if alternative_assets.get("projection_generated_at_utc") is not None:
        raise RuntimeError("checked-in alternative-assets fixture must not invent a run time")
    candidate_registry = alternative_assets.get("candidate_registry") or {}
    if candidate_registry.get("total") != 125:
        raise RuntimeError("alternative-assets candidate count changed")
    if candidate_registry.get("counts_by_class") != {
        "us_equity_token": 90,
        "etf_or_fund_token": 31,
        "metal_or_other_asset": 4,
    }:
        raise RuntimeError("alternative-assets candidate class counts changed")
    if candidate_registry.get("is_current_listing_proof") is not False:
        raise RuntimeError("candidate registry must not be represented as listing proof")
    if alternative_assets.get("actual_catalog") is not None:
        raise RuntimeError("checked-in fixture must not invent a provider catalog")
    capacity = alternative_assets.get("capacity_candidate_max") or {}
    if capacity.get("total_rows") != 23_010_750:
        raise RuntimeError("alternative-assets capacity row estimate changed")
    reference_capacity = (capacity.get("scenarios") or {}).get("reference") or {}
    if reference_capacity.get("canonical_gb") != 1.472688:
        raise RuntimeError("alternative-assets reference capacity estimate changed")
    if capacity.get("historical_materialization_authorized") is not False:
        raise RuntimeError("capacity projection must not authorize history materialization")
    alternative_security = alternative_assets.get("safety_boundary") or {}
    if not alternative_security or any(
        value is not False for value in alternative_security.values()
    ):
        raise RuntimeError("alternative-assets projection safety boundary changed")

    history_progress = json.loads(HISTORY_PROGRESS.read_text(encoding="utf-8"))
    if history_progress.get("schema") != "qookey-dashboard-history-progress-v0.2":
        raise RuntimeError("dashboard history progress schema changed")
    if history_progress.get("authority") is not False:
        raise RuntimeError("dashboard history progress must remain non-authoritative")
    if history_progress.get("snapshotType") != "CURRENT_OPERATIONS_PROJECTION":
        raise RuntimeError("dashboard history progress must project current operations")
    if history_progress.get("source") != "research/status/current-operations-v0-3.json":
        raise RuntimeError("dashboard history progress source changed")
    if history_progress.get("status") != "COMPLETE":
        raise RuntimeError("dashboard history progress fixture must remain complete")
    if (
        history_progress.get("provider") != "binance_usdm"
        or history_progress.get("mode") != "current_operations"
    ):
        raise RuntimeError("dashboard history progress provider/mode changed")
    if (history_progress.get("shardsComplete"), history_progress.get("shardCount")) != (10, 10):
        raise RuntimeError("dashboard history progress completion count changed")
    if history_progress.get("historyReacquisitionRequired") is not False:
        raise RuntimeError("completed history must not request reacquisition")
    if history_progress.get("trainingRunId") != 34918219864:
        raise RuntimeError("dashboard history progress training run changed")
    if history_progress.get("modelQualityStatus") != "REJECT":
        raise RuntimeError("dashboard history progress model-quality state changed")
    complete = history_progress["shardsComplete"]
    history_security = history_progress.get("safetyBoundary") or {}
    if not history_security or any(value is not False for value in history_security.values()):
        raise RuntimeError("dashboard history progress safety boundary changed")

    calendar = json.loads(RESEARCH_CALENDAR.read_text(encoding="utf-8"))
    if calendar.get("schema") != "qookey-research-calendar-projection-v0.1":
        raise RuntimeError("dashboard research calendar schema changed")
    if calendar.get("authority") is not False:
        raise RuntimeError("dashboard research calendar must declare authority=false")
    if calendar.get("locale") != "zh-Hant-TW" or calendar.get("timezone") != "Asia/Taipei":
        raise RuntimeError("dashboard research calendar locale/timezone changed")
    calendar_generated_at = calendar.get("projectionGeneratedAtUtc")
    if calendar_generated_at is not None:
        try:
            datetime.fromisoformat(str(calendar_generated_at).replace("Z", "+00:00"))
        except ValueError as exc:
            raise RuntimeError("dashboard research calendar generation time is invalid") from exc
    calendar_items = calendar.get("items") or []
    expected_calendar_ids = {
        "v0-12-successor-metadata-window",
        "strategy-research-loop-v0-1",
        "detailed-history-backfill",
        "pionex-alternative-assets-observability-v0-2",
        "paper-training-resumption-v0-2",
        "sstate-evidence-calibration",
        "continuous-learning-target",
    }
    if {item.get("id") for item in calendar_items} != expected_calendar_ids:
        raise RuntimeError("dashboard research calendar stages changed without review")
    allowed_calendar_statuses = {
        "AUTHORIZED",
        "AUTHORIZED_METADATA_ONLY",
        "WAITING_AUTHORITY",
        "NOT_READY",
        "PREPARED",
    }
    for item in calendar_items:
        if item.get("status") not in allowed_calendar_statuses:
            raise RuntimeError(f"dashboard calendar status is not allowlisted: {item.get('status')}")
        if not item.get("windowLabel") or not item.get("title") or not item.get("detail"):
            raise RuntimeError(f"dashboard calendar item is incomplete: {item.get('id')}")
    calendar_security = calendar.get("safetyBoundary") or {}
    if not calendar_security or any(value is not False for value in calendar_security.values()):
        raise RuntimeError("dashboard research calendar must keep every safety authority false")
    calendar_sources = set(calendar.get("sourceAuthorities") or [])
    for required_source in (
        "PROJECT_STATUS.md",
        "config/binance_usdm_detailed_history_v0_1_2.json",
        "config/pionex_alternative_assets_v0_1.json",
        "config/pionex_alternative_assets_observability_v0_2.json",
        "config/post_window_paper_training_v0_2.json",
        "config/provider_equivalence_v0_10_final_atomic_cutover_v0_1.json",
        "config/provider_equivalence_v0_12_successor_metadata_window_v0_1.json",
        "config/provider_equivalence_v0_12_successor_metadata_window_binding_v0_1.json",
        "research/receipts/2026-08-31-provider-equivalence-v0-12-successor-metadata-window-binding.json",
        "config/strategy_edge_validation_v0_1.json",
        "config/strategy_research_loop_v0_1.json",
        "docs/CONTINUOUS_LEARNING_ROADMAP_V0_1.md",
        "docs/HISTORICAL_SSTATE_EVIDENCE_INGESTION_V0_1.md",
    ):
        if required_source not in calendar_sources:
            raise RuntimeError(f"dashboard research calendar lineage missing: {required_source}")

    operations = json.loads(OPERATIONS_SCHEDULE.read_text(encoding="utf-8"))
    if operations.get("schema") != "qookey-automation-schedule-projection-v0.1":
        raise RuntimeError("dashboard automation schedule projection schema changed")
    if operations.get("authority") is not False:
        raise RuntimeError("dashboard automation schedule must remain non-authoritative")
    if operations.get("timezone") != "Asia/Taipei":
        raise RuntimeError("dashboard automation schedule timezone changed")
    operations_generated_at = operations.get("projectionGeneratedAtUtc")
    if operations_generated_at is not None:
        try:
            datetime.fromisoformat(str(operations_generated_at).replace("Z", "+00:00"))
        except ValueError as exc:
            raise RuntimeError("dashboard automation schedule generation time is invalid") from exc
    operations_security = operations.get("safetyBoundary") or {}
    if not operations_security or any(
        value is not False for value in operations_security.values()
    ):
        raise RuntimeError("dashboard automation schedule safety boundary changed")
    operations_summary = operations.get("summary") or {}
    if operations_summary.get("core100HistoryStatus") != "COMPLETE":
        raise RuntimeError("automation projection lost Core100 completion")
    if operations_summary.get("scheduledJobCount") != 7:
        raise RuntimeError("automation projection scheduled job count changed")
    if operations_summary.get("core100HistoryRetirementPending") is not False:
        raise RuntimeError("Core100 History retirement must no longer be pending")
    if operations_summary.get("core100HistoryScheduleRetired") is not True:
        raise RuntimeError("Core100 History retired schedule is not projected")
    if operations_summary.get("core100TrainingDedupeState") != "ACTIVE_FINGERPRINT_NO_CHANGE":
        raise RuntimeError("Core100 Training fingerprint dedupe state changed")
    if operations_summary.get("zecDevelopmentExpectedCells") != 256:
        raise RuntimeError("automation projection ZEC matrix size changed")
    if operations_summary.get("zecDevelopmentCompletedCells") != 256:
        raise RuntimeError("automation projection lost completed ZEC execution evidence")
    source_status = operations.get("sourceStatus") or {}
    resource_status = source_status.get("resourceHub") or {}
    registry_status = source_status.get("externalCapabilityRegistry") or {}
    core100_status = source_status.get("core100") or {}
    zec_status = source_status.get("zecV0_3") or {}
    if resource_status.get("state") != "SCHEDULED_READ_ONLY_CHANGE_WATCH":
        raise RuntimeError("Resource Hub projection state changed")
    if resource_status.get("automaticPullRequestAuthorized") is not False:
        raise RuntimeError("Resource Hub projection cannot auto-create PRs")
    if registry_status.get("candidateCount") != 10:
        raise RuntimeError("external capability registry count changed")
    if registry_status.get("runtimeExecutionAuthorized") is not False:
        raise RuntimeError("external capability runtime must remain closed")
    if core100_status.get("historyState") != "COMPLETE_SCHEDULE_RETIRED":
        raise RuntimeError("Core100 History retirement projection changed")
    if core100_status.get("historyGenericBackfillRetired") is not True:
        raise RuntimeError("Core100 generic backfill retirement projection changed")
    if core100_status.get("trainingState") != "FINGERPRINT_DEDUP_ACTIVE":
        raise RuntimeError("Core100 Training dedupe projection changed")
    if core100_status.get("trainingBaselineRunId") != 34918219864:
        raise RuntimeError("Core100 Training baseline run changed")
    if core100_status.get("trainingNoChangeWritesR2") is not False:
        raise RuntimeError("Core100 Training NO_CHANGE must not write R2")
    if zec_status.get("state") != "COMPLETE_NO_ELIGIBLE_DEVELOPMENT_CANDIDATE":
        raise RuntimeError("ZEC projection completion state changed")
    if zec_status.get("expectedCells") != 256 or zec_status.get("completedCells") != 256:
        raise RuntimeError("ZEC projection must preserve the complete 256-cell matrix")
    if zec_status.get("selectionStatus") != "NO_ELIGIBLE_DEVELOPMENT_CANDIDATE":
        raise RuntimeError("ZEC projection selection result changed")
    if zec_status.get("championFrozen") is not False:
        raise RuntimeError("ZEC projection cannot claim a frozen champion")
    if zec_status.get("diagnosticLeaderId") != "zec-v0-3-45":
        raise RuntimeError("ZEC diagnostic leader evidence changed")
    if zec_status.get("freshConfirmationAccessAuthorized") is not False:
        raise RuntimeError("ZEC fresh confirmation must remain closed")

    zec_completion = json.loads(ZEC_COMPLETION_RECEIPT.read_text(encoding="utf-8"))
    if zec_completion.get("schema") != "qookey-zec-v0-3-development-completion-v0.1":
        raise RuntimeError("ZEC completion receipt schema changed")
    if zec_completion.get("status") != "COMPLETE_NO_ELIGIBLE_DEVELOPMENT_CANDIDATE":
        raise RuntimeError("ZEC completion receipt state changed")
    zec_completion_dev = zec_completion.get("development") or {}
    if zec_completion_dev.get("matrix_cells") != 256:
        raise RuntimeError("ZEC completion receipt matrix changed")
    if zec_completion_dev.get("selection_status") != "NO_ELIGIBLE_DEVELOPMENT_CANDIDATE":
        raise RuntimeError("ZEC completion receipt selection changed")
    if zec_completion_dev.get("champion_frozen") is not False:
        raise RuntimeError("ZEC completion receipt cannot freeze a champion")
    zec_completion_safety = zec_completion.get("safety_boundary") or {}
    if any(value is not False for value in zec_completion_safety.values()):
        raise RuntimeError("ZEC completion receipt safety boundary changed")
    operations_items = operations.get("items") or []
    required_operation_ids = {
        "resource-hub-change-watch-v0-2",
        "research-signal-v0-2",
        "research-signal-quality-v0-1",
        "context-forward-capture-v0-1",
        "live-paper-hourly-v0-2",
        "automation-health-v0-2",
        "dashboard-pages-projection",
        "core100-history-v0-1-2",
        "core100-training-v0-1-2",
        "pionex-alternative-observability-v0-2",
        "external-tool-evaluation-weekly",
        "shadow-comparison-weekly",
        "maintenance-weekly",
        "weekly-handoff",
        "monthly-terms-review",
        "zec-v0-3-development",
        "zec-v0-4-development",
    }
    if {item.get("id") for item in operations_items} != required_operation_ids:
        raise RuntimeError("dashboard automation schedule items changed without review")

    evidence = json.loads(RESEARCH_EVIDENCE.read_text(encoding="utf-8"))
    evidence_schema = json.loads(RESEARCH_EVIDENCE_SCHEMA.read_text(encoding="utf-8"))
    if evidence_schema.get("$id") != "https://qookey109-pixel.github.io/crypto-autopilot/data/research-evidence.schema.json":
        raise RuntimeError("dashboard research evidence schema id changed")
    if (evidence_schema.get("properties") or {}).get("authority", {}).get("const") is not False:
        raise RuntimeError("dashboard research evidence schema must freeze authority=false")
    if evidence.get("schema") != "qookey-dashboard-research-evidence-v0.1":
        raise RuntimeError("dashboard research evidence schema changed")
    if evidence.get("authority") is not False or evidence.get("mode") != "PAPER_ONLY_READ_ONLY":
        raise RuntimeError("dashboard research evidence must remain paper-only and non-authoritative")
    if evidence.get("projectedAtUtc") is not None:
        raise RuntimeError("checked-in research evidence fixture must not invent a projection time")
    if evidence.get("positionsState") != "NOT_READY":
        raise RuntimeError("dashboard positions fixture must remain NOT_READY")
    if evidence.get("backtestsState") != "NOT_AUTHORIZED":
        raise RuntimeError("dashboard backtests fixture must remain NOT_AUTHORIZED")
    if evidence.get("positions") != [] or evidence.get("backtests") != []:
        raise RuntimeError("checked-in research evidence fixture must not invent positions or backtests")
    evidence_security = evidence.get("safetyBoundary") or {}
    if not evidence_security or any(value is not False for value in evidence_security.values()):
        raise RuntimeError("dashboard research evidence must keep every safety authority false")

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

    # Historical V0.8/V0.10 evidence remains frozen; V0.12 owns current schedule.
    if project.get("renderMetadataV0_8CutoverState") != (
        "HISTORICAL_PREPARED_EXECUTION_NOT_AUTHORIZED"
    ):
        raise RuntimeError("dashboard fixture must preserve V0.8 historical prepared state")
    if project.get("renderMetadataV0_9SmokeState") != "PASS_FROZEN":
        raise RuntimeError("dashboard fixture must reflect frozen V0.9 smoke PASS")
    if project.get("renderMetadataV0_10CutoverState") != "EFFECTIVE_AUTHORIZED":
        raise RuntimeError("dashboard fixture must reflect effective V0.10 cutover")
    if project.get("currentMetadataCaptureExecutionPath") != "github_hosted_ubuntu_v0_12":
        raise RuntimeError("dashboard fixture must reflect V0.12 current capture path")
    if project.get("oldV0_2ScheduledExecutionAuthorized") is not False:
        raise RuntimeError("dashboard fixture must keep V0.2 scheduled execution retired")
    if project.get("v0_10ScheduledExecutionAuthorized") is not False:
        raise RuntimeError("dashboard fixture must keep V0.10 scheduled execution retired")
    if project.get("v0_12SuccessorWindowState") != "AUTHORIZED_ON_MAIN_MERGE":
        raise RuntimeError("dashboard fixture must reflect V0.12 successor authority")
    if project.get("successorMetadataCaptureExecutionAuthorized") is not True:
        raise RuntimeError("dashboard fixture must reflect V0.12 metadata capture authority")
    if project.get("successorMetadataScheduleEnabled") is not True:
        raise RuntimeError("dashboard fixture must reflect V0.12 schedule enablement")
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
    for required_id in (
        "cloud-paper-billing-detail",
        "cloud-paper-billing-run",
        "cloud-paper-usage-run",
    ):
        if f'id="{required_id}"' not in html:
            raise RuntimeError(f"Cloud Paper billing projection element missing: {required_id}")

    if '<html lang="zh-Hant-TW">' not in html:
        raise RuntimeError("dashboard HTML must declare zh-Hant-TW")
    if '<a class="skip-link" href="#top">跳到主要內容</a>' not in html:
        raise RuntimeError("dashboard keyboard skip link missing")
    if html.count("<div") != html.count("</div>"):
        raise RuntimeError("dashboard HTML div structure is unbalanced")
    if 'http-equiv="Content-Security-Policy"' not in html:
        raise RuntimeError("dashboard must enforce a CSP meta policy on GitHub Pages")
    for directive in (
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "form-action 'none'",
    ):
        if directive not in html:
            raise RuntimeError(f"dashboard CSP directive missing: {directive}")
    if '<meta name="referrer" content="no-referrer"' not in html:
        raise RuntimeError("dashboard must enforce no-referrer through HTML")
    if 'aria-describedby="nav-scroll-hint"' not in html or 'id="nav-scroll-hint"' not in html:
        raise RuntimeError("dashboard mobile navigation must expose its horizontal-scroll hint")
    for stale in (
        "8/10 分片",
        "訓練尚未完成",
        "PR #292",
        "下次 9/20",
        "目前因歷史補齊失敗而告警",
        "持續模擬（待啟動）",
        "後續版已準備 · 等待資料授權",
        "V0.11 與獨立 holdout 存取 authority 完成前不自動恢復。",
        "下一次排程：2026/09/04",
        "PAPER · LONG_ONLY",
        "資料由 Repository 的六份策略設定重建",
        'id="alternative-assets-candidates">125<',
        'id="alternative-assets-equity">90<',
        'id="alternative-assets-funds">31<',
        'id="alternative-assets-metals">4<',
        'id="strategy-research-candidates">120<',
        'id="strategy-research-families">4<',
    ):
        if stale in html:
            raise RuntimeError(f"dashboard raw template contains stale current-truth text: {stale}")
    for status_id in ("cloud-run-updated", "home-updated"):
        if f'id="{status_id}" role="status"' not in html:
            raise RuntimeError(f"dashboard dynamic status message missing role=status: {status_id}")
    for label in REQUIRED_ZH_HANT_LABELS:
        if label not in html:
            raise RuntimeError(f"dashboard Traditional Chinese label missing: {label}")
    for view in (
        "overview",
        "data-health",
        "signals",
        "strategy",
        "positions",
        "trades",
        "performance",
        "backtests",
        "gates",
    ):
        if f'id="view-{view}"' not in html:
            raise RuntimeError(f"dashboard view missing: {view}")

    app_js = APP_JS.read_text(encoding="utf-8")
    current_operations_js = (ROOT / "assets" / "js" / "current-operations.js").read_text(
        encoding="utf-8"
    )
    styles = STYLES.read_text(encoding="utf-8")
    for stale_runtime in (
        'payload.mode !== "PAPER_ONLY"',
        'payload.pionexValidationStatus !== "PENDING_MANUAL_DISPATCH"',
        'text("readiness-heading", "9/16 目前作業狀態")',
    ):
        if stale_runtime in current_operations_js:
            raise RuntimeError(
                f"dashboard current-operations runtime contains stale contract: {stale_runtime}"
            )
    if "marketCount: 15, fundingMonths: 1010" in app_js:
        raise RuntimeError("dashboard fallback must not fabricate market/funding values")
    for token in (
        '"alternative-assets-candidates"',
        '"alternative-assets-matched"',
        '"alternative-assets-equity"',
        '"alternative-assets-funds"',
        '"alternative-assets-metals"',
        '"alternative-assets-capacity"',
        'setText(id, "—")',
        "不以 0 代替缺少資料",
    ):
        if token not in app_js:
            raise RuntimeError(
                f"alternative-assets missing-data fallback regressed: {token}"
            )
    if "style=" in html or "style=" in app_js:
        raise RuntimeError("dashboard CSP forbids inline style attributes")
    for token in (
        ".site-header { position: sticky",
        ".skip-link",
        "scroll-snap-type: x proximity",
        ".home-details[open] > summary::after",
        ".table-wrap:focus-visible",
        ".strategy-score-progress",
        ".cloud-run-card",
    ):
        if token not in styles:
            raise RuntimeError(f"dashboard responsive/accessibility style missing: {token}")
    for label in (
        "通過 · PASS",
        "已授權 · AUTHORIZED",
        "已準備 · PREPARED",
        "等待授權 · WAITING_AUTHORITY",
        "未授權 · NOT_AUTHORIZED",
        "失敗 · FAIL",
    ):
        if label not in app_js:
            raise RuntimeError(f"dashboard status label missing: {label}")
    for token in (
        "./data/operational-status.json",
        "./data/paper-training.json",
        "./data/research-calendar.json",
        "./data/research-evidence.json",
        "./data/alternative-assets.json",
        "./data/history-progress.json",
        "./data/cloud-runs.json",
        "qookey-cloud-run-status-v0.2",
        "UNKNOWN_FROM_GITHUB_RUN_METADATA",
        "mergeOperationalStatus",
        "renderPaperTraining",
        "renderEquityChart",
        "renderCalendar",
        "calendarTiming",
        "formatTrustedTime",
        "researchEvidenceIsSafe",
        "renderResearchEvidence",
        "alternativeAssetsProjectionIsSafe",
        "historyProgressIsSafe",
        "renderAlternativeAssets",
        "qookey-pionex-alternative-assets-projection-v0.2",
        "qookey-dashboard-strategy-projection-v0.1",
        "strategy-analysis-layers",
        "strategy-score-progress",
        'wrap.setAttribute("role", "region")',
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
    if paper.get("status") != "WAITING_AUTHORITY":
        raise RuntimeError("dashboard Paper successor must remain waiting for authority")
    paper_authority = paper.get("authority") or {}
    if paper_authority.get("publicMarketDataReadAuthorized") is not False:
        raise RuntimeError("waiting Paper fixture cannot authorize provider reads")
    if paper_authority.get("paperCandidateGenerationAuthorized") is not False:
        raise RuntimeError("waiting Paper fixture cannot authorize candidate generation")
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
                "stage": "DASHBOARD_ZH_HANT_STATIC_SAFETY_V0_13_EVIDENCE_PASS",
                "required_files": len(REQUIRED),
                "views": 9,
                "calendar_items": len(calendar_items),
                "history_progress": f"{complete}/{history_progress['shardCount']}",
                "history_source": history_progress["source"],
                "locale": "zh-Hant-TW",
                "authority_fixture": False,
                "operational_authority": False,
                "paper_only": True,
                "equivalence_v0_1": project["providerEquivalenceGateState"],
                "render_v0_10": project["renderMetadataV0_10CutoverState"],
                "successor_v0_12": project["v0_12SuccessorWindowState"],
                "metadata_capture_authorized": True,
                "capture_window_operations": op_project["v0_10CaptureWindowOperationsState"],
                "mid_window_emergency_template": op_project["v0_10MidWindowEmergencyTemplateState"],
                "metadata_stability": op_project["metadataStabilityState"],
                "v0_11_synthetic_rehearsal": op_project["v0_11SyntheticFailureRehearsalState"],
                "v0_11_production_r2_evaluation": op_project["v0_11ProductionR2EvaluationState"],
                "holdout": op_project["replacementHoldoutState"],
                "live_execution_surface": False,
                "github_pages_custom_headers_enforced": False,
                "html_csp_enforced": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
