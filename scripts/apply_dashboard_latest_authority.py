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
V07_RENDER_PROTOCOL = Path(
    "config/provider_equivalence_v0_7_render_metadata_capture_protocol_v0_1.json"
)
V08_CUTOVER_PROTOCOL = Path(
    "config/provider_equivalence_v0_8_render_metadata_execution_cutover_v0_1.json"
)
V08_CUTOVER_RECEIPT = Path(
    "research/receipts/2026-08-19-provider-equivalence-v0-8-render-metadata-cutover-prepared.json"
)
V08_HANDSHAKE = Path(
    "research/receipts/2026-08-19-provider-equivalence-v0-8-shared-relay-secret-handshake-pass.json"
)
V09_SMOKE = Path(
    "research/receipts/2026-08-20-provider-equivalence-v0-9-render-relay-smoke-pass.json"
)
V10_CONFIG = Path("config/provider_equivalence_v0_10_final_atomic_cutover_v0_1.json")
V10_AUTHORITY = Path(
    "research/receipts/2026-08-20-provider-equivalence-v0-10-final-atomic-cutover-authority.json"
)
V10_EMERGENCY_SCHEDULE_AUTHORITY = Path(
    "config/v0_10_mid_window_emergency_schedule_reactivation_v0_1.json"
)
V10_EMERGENCY_SCHEDULE_EFFECTIVE = Path(
    "research/receipts/2026-08-27-v0-10-mid-window-emergency-schedule-reactivation-effective.json"
)
OLD_V02_WORKFLOW = Path(
    ".github/workflows/provider-equivalence-v0-2-metadata-capture.yml"
)
V10_WORKFLOW = Path(
    ".github/workflows/provider-equivalence-v0-10-render-metadata-capture.yml"
)
STRATEGY_EDGE_CONFIG = Path("config/strategy_edge_validation_v0_1.json")
STRATEGY_EDGE_RECEIPT = Path(
    "research/receipts/2026-08-28-strategy-edge-validation-v0-1-prepared.json"
)
STRATEGY_RESEARCH_CONFIG = Path("config/strategy_research_loop_v0_1.json")
STRATEGY_RESEARCH_RECEIPT = Path(
    "research/receipts/2026-08-28-strategy-research-loop-v0-1-prepared.json"
)

EXPECTED_SCOPE_SHA = "1e0ff54daeec8e5e47376fedb631c663687dd6fb6a4c297d269c33acdf99ad58"
EXPECTED_CHECKSUM_SHA = "881c14d3b3c780b8a0d56ca2f7fd57d2abff310fcd7cb4b13dc01f506b9b64f3"
EXPECTED_EQUIVALENCE_ARTIFACT_SHA = "16975dfcdc34c621b7abe8326cb3cdab0aebffcee27dce2720a8db7f28640af0"
EXPECTED_EQUIVALENCE_RESULT_SHA = "c4ddf68700b03c907fbf43101e9a8a39ead12fa80d395119aa53d3b52e527353"
EXPECTED_FROZEN_V10_CRONS = (
    '    - cron: "17,47 * 27-31 8 *"',
    '    - cron: "17,47 * 1-3 9 *"',
    '    - cron: "17,47 0-1 4 9 *"',
)
EXPECTED_EMERGENCY_REGISTRATION_CRONS = (
    '    - cron: "17,47 * 27,28,29,30,31 8 *"',
    '    - cron: "17,47 * 1,2,3 9 *"',
    '    - cron: "17,47 0,1 4 9 *"',
)


def load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def require_dict(payload: object, label: str) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected object: {label}")
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


def validate_foundation() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    materialization = load(MATERIALIZATION)
    usage = load(R2_USAGE)
    equivalence = load(EQUIVALENCE)

    if materialization.get("status") != "PASS":
        raise RuntimeError("Funding materialization authority is not PASS")
    if materialization.get("stage") != "BINANCE_FUNDING_R2_V0_2_MATERIALIZATION_PASS":
        raise RuntimeError("Funding materialization stage changed")
    exact_scope = require_dict(materialization.get("exact_scope") or {}, "funding exact scope")
    postwrite = require_dict(materialization.get("postwrite_results") or {}, "funding postwrite")
    blocked = require_dict(
        materialization.get("explicitly_not_authorized") or {}, "funding blocked boundary"
    )
    if exact_scope.get("canonical_scope_sha256") != EXPECTED_SCOPE_SHA:
        raise RuntimeError("Funding materialization scope SHA changed")
    if exact_scope.get("source_checksum_set_sha256") != EXPECTED_CHECKSUM_SHA:
        raise RuntimeError("Funding materialization checksum SHA changed")
    if exact_scope.get("source_archive_count") != 1003:
        raise RuntimeError("Funding source archive count changed")
    if exact_scope.get("annual_canonical_object_count") != 94:
        raise RuntimeError("Funding canonical object count changed")
    if exact_scope.get("authorized_object_identity_count") != 192:
        raise RuntimeError("Funding authorized identity count changed")
    if postwrite.get("actual_r2_materialization_completed") is not True:
        raise RuntimeError("Funding materialization is not complete")
    if postwrite.get("all_192_authorized_objects_verified_after_write") is not True:
        raise RuntimeError("Funding postwrite verification changed")
    if blocked.get("source_switch_authorized") is not False:
        raise RuntimeError("Funding authority changed source-switch boundary")
    if blocked.get("live_trading_authorized") is not False:
        raise RuntimeError("Funding authority changed live boundary")

    if usage.get("status") != "PASS":
        raise RuntimeError("R2 usage authority is not PASS")
    if usage.get("stage") != "R2_BUCKET_USAGE_READ_ONLY_INVENTORY_PASS":
        raise RuntimeError("R2 usage stage changed")
    usage_execution = require_dict(usage.get("execution") or {}, "R2 usage execution")
    inventory = require_dict(usage.get("inventory") or {}, "R2 usage inventory")
    if usage_execution.get("read_only") is not True:
        raise RuntimeError("R2 usage inventory is no longer read-only")
    if usage_execution.get("writes_performed") is not False:
        raise RuntimeError("R2 usage inventory unexpectedly wrote")
    if usage_execution.get("deletes_performed") is not False:
        raise RuntimeError("R2 usage inventory unexpectedly deleted")
    if inventory.get("total_object_count") != 457 or inventory.get("total_bytes") != 22120404:
        raise RuntimeError("Frozen R2 usage inventory totals changed")

    if equivalence.get("status") != "FAIL":
        raise RuntimeError("Equivalence V0.1 must remain frozen FAIL")
    if equivalence.get("stage") != "PIONEX_BINANCE_EQUIVALENCE_GATE_FAIL":
        raise RuntimeError("Equivalence V0.1 stage changed")
    eq_execution = require_dict(equivalence.get("execution") or {}, "equivalence execution")
    eq_aggregate = require_dict(equivalence.get("aggregate") or {}, "equivalence aggregate")
    eq_boundary = require_dict(equivalence.get("authority_boundary") or {}, "equivalence boundary")
    if eq_execution.get("workflow_run_id") != 32206479914:
        raise RuntimeError("Equivalence evidence run changed")
    if eq_execution.get("execution_status") != "PASS":
        raise RuntimeError("Equivalence evidence execution did not complete")
    if eq_execution.get("artifact_zip_sha256") != EXPECTED_EQUIVALENCE_ARTIFACT_SHA:
        raise RuntimeError("Equivalence artifact SHA changed")
    if eq_execution.get("result_json_sha256") != EXPECTED_EQUIVALENCE_RESULT_SHA:
        raise RuntimeError("Equivalence result SHA changed")
    if eq_aggregate.get("gate_status") != "FAIL":
        raise RuntimeError("Equivalence gate status changed")
    if (
        eq_aggregate.get("pass_count"),
        eq_aggregate.get("review_count"),
        eq_aggregate.get("fail_count"),
    ) != (18, 18, 9):
        raise RuntimeError("Equivalence aggregate counts changed")
    if eq_boundary.get("source_switch_authorized") is not False:
        raise RuntimeError("Equivalence FAIL cannot authorize source switch")
    if eq_boundary.get("staged_trade_kline_w1_materialization_authorized") is not False:
        raise RuntimeError("Equivalence FAIL cannot authorize W1")
    if eq_boundary.get("live_trading_authorized") is not False:
        raise RuntimeError("Equivalence FAIL cannot authorize live trading")

    return materialization, usage, equivalence


def validate_render_lineage() -> dict[str, object]:
    v05 = load(V05_RENDER_PASS)
    v06 = load(V06_RENDER_TRANSITION)
    v07 = load(V07_RENDER_PROTOCOL)
    v08 = load(V08_CUTOVER_PROTOCOL)
    v08_receipt = load(V08_CUTOVER_RECEIPT)
    handshake = load(V08_HANDSHAKE)
    smoke = load(V09_SMOKE)
    v10 = load(V10_CONFIG)
    v10_authority = load(V10_AUTHORITY)
    emergency = load(V10_EMERGENCY_SCHEDULE_AUTHORITY)
    emergency_effective = load(V10_EMERGENCY_SCHEDULE_EFFECTIVE)

    if v05.get("status") != "PASS" or v05.get("stage") != (
        "PROVIDER_EQUIVALENCE_V0_5_RENDER_FREE_BINANCE_TRANSPORT_PASS"
    ):
        raise RuntimeError("V0.5 Render transport PASS authority changed")
    v05_execution = require_dict(v05.get("execution_evidence") or {}, "V0.5 execution")
    v05_safety = require_dict(v05.get("sanitization_and_safety") or {}, "V0.5 safety")
    if (
        v05_execution.get("upstream_status"),
        v05_execution.get("json_ok"),
        v05_execution.get("symbols_array"),
        v05_execution.get("symbol_count"),
    ) != (200, True, True, 872):
        raise RuntimeError("V0.5 sanitized transport evidence changed")
    for key in (
        "api_key_used",
        "r2_writes_performed",
        "holdout_candles_accessed",
        "source_switch_performed",
        "live_trading_performed",
    ):
        if v05_safety.get(key) is not False:
            raise RuntimeError(f"V0.5 safety boundary changed: {key}")

    if v06.get("status") != "PASS" or v06.get("stage") != (
        "PROVIDER_EQUIVALENCE_V0_6_RENDER_TRANSPORT_AUTHORITY_TRANSITION_FROZEN"
    ):
        raise RuntimeError("V0.6 Render transition authority changed")
    v06_decision = require_dict(v06.get("decision") or {}, "V0.6 decision")
    if v06_decision.get("successor_public_metadata_transport_authority") != (
        "render_free_web_service"
    ):
        raise RuntimeError("V0.6 successor transport changed")

    if v07.get("status") != "PROTOCOL_AND_RUNTIME_BOUNDARY_FROZEN_EXECUTION_NOT_AUTHORIZED":
        raise RuntimeError("V0.7 historical prepared protocol changed")
    v07_holdout = require_dict(v07.get("holdout") or {}, "V0.7 holdout")
    v07_window = require_dict(v07.get("metadata_capture_window") or {}, "V0.7 window")
    if v07_holdout.get("state") != "FROZEN_UNOPENED":
        raise RuntimeError("V0.7 holdout state changed")
    if v07_window.get("hourly_slot_count") != 194:
        raise RuntimeError("V0.7 hourly-slot count changed")
    if v07_window.get("scheduled_minutes_utc") != [17, 47]:
        raise RuntimeError("V0.7 scheduled minutes changed")

    if v08.get("status") != "CUTOVER_CONTRACT_FROZEN_EXECUTION_NOT_AUTHORIZED":
        raise RuntimeError("V0.8 historical cutover protocol changed")
    if v08_receipt.get("status") != "PASS" or v08_receipt.get("stage") != (
        "PROVIDER_EQUIVALENCE_V0_8_RENDER_METADATA_CUTOVER_PREPARED_EXECUTION_NOT_AUTHORIZED"
    ):
        raise RuntimeError("V0.8 prepared receipt changed")

    if handshake.get("status") != "PASS" or handshake.get("stage") != (
        "PROVIDER_EQUIVALENCE_V0_8_SHARED_RELAY_SECRET_HANDSHAKE_PASS"
    ):
        raise RuntimeError("V0.8 shared-secret handshake is not frozen PASS")
    handshake_result = require_dict(handshake.get("result") or {}, "V0.8 handshake result")
    if handshake_result.get("shared_secret_match") is not True:
        raise RuntimeError("V0.8 shared secret match changed")
    if handshake_result.get("secret_value_recorded") is not False:
        raise RuntimeError("V0.8 handshake must not record secret value")
    if handshake_result.get("provider_requests_performed") != 0:
        raise RuntimeError("V0.8 handshake must remain provider-request free")
    if handshake_result.get("r2_writes_performed") is not False:
        raise RuntimeError("V0.8 handshake must remain R2-write free")

    if smoke.get("status") != "PASS" or smoke.get("stage") != (
        "PROVIDER_EQUIVALENCE_V0_9_RENDER_RELAY_LIVE_SMOKE_PASS"
    ):
        raise RuntimeError("V0.9 relay smoke is not frozen PASS")
    smoke_result = require_dict(smoke.get("result") or {}, "V0.9 smoke result")
    if (
        smoke_result.get("upstream_status"),
        smoke_result.get("json_ok"),
        smoke_result.get("symbols_array"),
        smoke_result.get("symbol_count"),
        smoke_result.get("provider_requests_performed"),
    ) != (200, True, True, 872, 1):
        raise RuntimeError("V0.9 sanitized smoke evidence changed")
    for key in (
        "api_key_used",
        "raw_exchange_info_emitted",
        "raw_exchange_info_persisted",
        "r2_writes_performed",
        "holdout_candles_accessed",
        "source_switch_performed",
        "live_trading_performed",
    ):
        if smoke_result.get(key) is not False:
            raise RuntimeError(f"V0.9 safety boundary changed: {key}")

    if v10.get("status") != "FINAL_ATOMIC_CUTOVER_AUTHORIZED_ON_MAIN_MERGE":
        raise RuntimeError("V0.10 cutover config is not merge-authorized")
    v10_scope = require_dict(v10.get("scientific_scope") or {}, "V0.10 scope")
    v10_cutover = require_dict(
        v10.get("atomic_repository_cutover") or {}, "V0.10 atomic cutover"
    )
    v10_transport = require_dict(v10.get("render_transport") or {}, "V0.10 transport")
    v10_storage = require_dict(v10.get("storage") or {}, "V0.10 storage")
    v10_boundary = require_dict(
        v10.get("authorization_boundary") or {}, "V0.10 authorization boundary"
    )
    if v10_scope.get("replacement_holdout_state") != "FROZEN_UNOPENED":
        raise RuntimeError("V0.10 replacement holdout changed")
    if v10_scope.get("hourly_slot_count") != 194:
        raise RuntimeError("V0.10 hourly-slot count changed")
    if v10_scope.get("scheduled_minutes_utc") != [17, 47]:
        raise RuntimeError("V0.10 scheduled minutes changed")
    if v10_scope.get("holdout_candles_access_authorized") is not False:
        raise RuntimeError("V0.10 cannot authorize holdout access")
    if v10_scope.get("holdout_evaluation_authorized") is not False:
        raise RuntimeError("V0.10 cannot authorize holdout evaluation")
    if v10_cutover.get("old_schedule_removed_in_same_change") is not True:
        raise RuntimeError("V0.10 old schedule removal changed")
    if v10_cutover.get("successor_schedule_enabled_in_same_change") is not True:
        raise RuntimeError("V0.10 successor schedule enablement changed")
    if v10_cutover.get("concurrent_old_and_new_capture_paths_authorized") is not False:
        raise RuntimeError("V0.10 cannot authorize concurrent capture paths")
    if v10_transport.get("plan") != "free" or v10_transport.get("monthly_budget_usd") != 0:
        raise RuntimeError("V0.10 Render FREE-ONLY boundary changed")
    if v10_transport.get("v0_10_raw_relay_path") != (
        "/metadata/v0-10/binance-exchange-info"
    ):
        raise RuntimeError("V0.10 raw relay path changed")
    if v10_transport.get("v0_7_raw_relay_remains_disabled") is not True:
        raise RuntimeError("V0.7 historical raw relay must remain disabled")
    if v10_transport.get("render_receives_r2_credentials") is not False:
        raise RuntimeError("Render must not receive R2 credentials")
    if v10_storage.get("free_only_operational_hard_stop_bytes") != 8_000_000_000:
        raise RuntimeError("V0.10 R2 hard stop changed")
    if v10_boundary.get("v0_10_metadata_capture_execution_authorized_on_main_merge") is not True:
        raise RuntimeError("V0.10 metadata capture authority changed")
    if v10_boundary.get("v0_10_metadata_only_r2_writes_authorized_on_main_merge") is not True:
        raise RuntimeError("V0.10 metadata-only R2 authority changed")
    for key in (
        "holdout_candle_access_authorized",
        "holdout_evaluation_authorized",
        "source_switch_authorized",
        "provider_splicing_authorized",
        "pionex_native_relabel_authorized",
        "staged_trade_kline_w1_materialization_authorized",
        "historical_universe_membership_authorized",
        "backtest_admission_authorized",
        "strategy_parameter_change_authorized",
        "automatic_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if v10_boundary.get(key) is not False:
            raise RuntimeError(f"V0.10 safety boundary changed: {key}")

    if v10_authority.get("status") != "PASS" or v10_authority.get("stage") != (
        "PROVIDER_EQUIVALENCE_V0_10_FINAL_ATOMIC_CUTOVER_AUTHORIZED_ON_MAIN_MERGE"
    ):
        raise RuntimeError("V0.10 final cutover receipt is not PASS")
    post_merge = require_dict(
        v10_authority.get("post_merge_authorization") or {}, "V0.10 post-merge authority"
    )
    if post_merge.get("metadata_capture_execution_authorized") is not True:
        raise RuntimeError("V0.10 post-merge capture authority missing")
    if post_merge.get("metadata_only_r2_writes_authorized") is not True:
        raise RuntimeError("V0.10 post-merge metadata write authority missing")
    if post_merge.get("old_v0_2_scheduled_execution_authorized") is not False:
        raise RuntimeError("V0.2 scheduled execution must be retired")
    if post_merge.get("concurrent_old_new_capture_authorized") is not False:
        raise RuntimeError("Concurrent old/new capture must remain forbidden")

    old_lines = OLD_V02_WORKFLOW.read_text(encoding="utf-8").splitlines()
    new_lines = V10_WORKFLOW.read_text(encoding="utf-8").splitlines()
    if any(line == "  schedule:" for line in old_lines):
        raise RuntimeError("V0.2 workflow still has a schedule trigger")
    if not any(line == "  schedule:" for line in new_lines):
        raise RuntimeError("V0.10 workflow has no schedule trigger")
    if emergency.get("status") != (
        "AUTHORIZED_FOR_PROTECTED_MAIN_REVIEW_NOT_EFFECTIVE_BEFORE_MERGE"
    ):
        raise RuntimeError("V0.10 emergency schedule authority is invalid")
    emergency_lineage = require_dict(emergency.get("lineage") or {}, "V0.10 emergency lineage")
    emergency_schedule = require_dict(
        emergency.get("schedule_equivalence") or {}, "V0.10 emergency schedule"
    )
    emergency_boundary = require_dict(
        emergency.get("authorization_boundary") or {}, "V0.10 emergency boundary"
    )
    if emergency_lineage.get("protected_main_pr_number") != 201:
        raise RuntimeError("V0.10 emergency PR binding changed")
    if emergency_lineage.get("pre_change_main_sha") != (
        "49c6bedb1e79e20963519b7f344762129669feb9"
    ):
        raise RuntimeError("V0.10 emergency pre-change main SHA changed")
    if emergency_schedule.get("original_authorized_crons") != [
        cron.split('"', 2)[1] for cron in EXPECTED_FROZEN_V10_CRONS
    ]:
        raise RuntimeError("V0.10 frozen cron lineage changed")
    if emergency_schedule.get("original_authorized_crons") != v10_cutover.get(
        "successor_cron_utc"
    ):
        raise RuntimeError("V0.10 original cron authority changed")
    if emergency_schedule.get("replacement_registration_crons") != [
        cron.split('"', 2)[1] for cron in EXPECTED_EMERGENCY_REGISTRATION_CRONS
    ]:
        raise RuntimeError("V0.10 emergency cron registration scope changed")
    if not set(EXPECTED_EMERGENCY_REGISTRATION_CRONS).issubset(set(new_lines)):
        raise RuntimeError("V0.10 emergency schedule registration changed")
    if any(value is not False for value in emergency_boundary.values()):
        raise RuntimeError("V0.10 emergency schedule expanded downstream authority")
    if emergency.get("render_boundary", {}).get("transport_affected") is not False:
        raise RuntimeError("V0.10 emergency schedule unexpectedly affects Render")
    if emergency_effective.get("status") != "PASS" or emergency_effective.get(
        "stage"
    ) != "V0_10_MID_WINDOW_EMERGENCY_SCHEDULE_REACTIVATION_EFFECTIVE_ON_PROTECTED_MAIN":
        raise RuntimeError("V0.10 emergency schedule post-merge receipt is not PASS")
    if (
        emergency_effective.get("source_authority")
        != str(V10_EMERGENCY_SCHEDULE_AUTHORITY)
        or emergency_effective.get("source_pr") != 201
        or emergency_effective.get("source_pr_head_sha")
        != "5148161fecd3a0939e51a6ad94db3ec475ae95a2"
        or emergency_effective.get("post_merge_main_sha")
        != "cf83b6320bc0f0817d8e6ae15d88fe304b933330"
    ):
        raise RuntimeError("V0.10 emergency schedule post-merge lineage changed")
    effective_change = require_dict(
        emergency_effective.get("validated_change") or {},
        "V0.10 emergency effective change",
    )
    effective_boundary = require_dict(
        emergency_effective.get("authorization_boundary") or {},
        "V0.10 emergency effective boundary",
    )
    if effective_change.get("effective_registration_crons") != [
        cron.split('"', 2)[1] for cron in EXPECTED_EMERGENCY_REGISTRATION_CRONS
    ]:
        raise RuntimeError("V0.10 effective schedule registration changed")
    if effective_change.get("semantic_attempt_set_equal") is not True:
        raise RuntimeError("V0.10 schedule semantic equivalence is not PASS")
    if any(value is not False for value in effective_boundary.values()):
        raise RuntimeError("V0.10 post-merge receipt expanded downstream authority")

    return {
        "v05": v05,
        "v06": v06,
        "v07": v07,
        "v08": v08,
        "handshake": handshake,
        "smoke": smoke,
        "v10": v10,
        "v10_authority": v10_authority,
        "v10_emergency_schedule_authority": emergency,
        "v10_emergency_schedule_effective": emergency_effective,
    }


def validate_strategy_research_lineage() -> dict[str, object]:
    edge = load(STRATEGY_EDGE_CONFIG)
    edge_receipt = load(STRATEGY_EDGE_RECEIPT)
    research = load(STRATEGY_RESEARCH_CONFIG)
    research_receipt = load(STRATEGY_RESEARCH_RECEIPT)

    for payload, label in (
        (edge, "Strategy Edge config"),
        (edge_receipt, "Strategy Edge receipt"),
        (research, "Strategy Research Loop config"),
        (research_receipt, "Strategy Research Loop receipt"),
    ):
        if payload.get("status") != "PREPARED_RESEARCH_ONLY":
            raise RuntimeError(f"{label} is not PREPARED_RESEARCH_ONLY")

    candidate_search = require_dict(
        research.get("candidate_search") or {}, "strategy candidate search"
    )
    families = candidate_search.get("families") or []
    if candidate_search.get("expected_candidate_count") != 120:
        raise RuntimeError("Strategy Research Loop candidate count changed")
    if candidate_search.get("execution_authorized") is not False:
        raise RuntimeError("Strategy Research Loop candidate execution became authorized")
    if not isinstance(families, list) or len(families) != 4:
        raise RuntimeError("Strategy Research Loop family contract changed")
    horizons = {
        str(horizon)
        for family in families
        for horizon in require_dict(family, "strategy family").get("horizons", [])
    }
    if horizons != {"INTRADAY", "MULTIDAY", "SWING"}:
        raise RuntimeError("Strategy Research Loop horizon contract changed")

    edge_methods = edge.get("methods") or []
    if not isinstance(edge_methods, list) or len(edge_methods) != 6:
        raise RuntimeError("Strategy Edge method contract changed")
    for payload, label in (
        (require_dict(edge.get("authority") or {}, "Strategy Edge authority"), "edge"),
        (
            require_dict(research.get("authority") or {}, "Strategy Research authority"),
            "research",
        ),
    ):
        for key in (
            "replacement_holdout_access_authorized",
            "source_switch_authorized",
            "historical_universe_membership_authorized",
            "backtest_admission_authorized",
            "trade_plan_authorized",
            "real_money_order_authorized",
            "live_trading_authorized",
        ):
            if payload.get(key) is not False:
                raise RuntimeError(f"Strategy {label} authority changed: {key}")
        if payload.get("model_promotion_authority") != 0:
            raise RuntimeError(f"Strategy {label} model promotion authority changed")

    receipt_authority = require_dict(
        research_receipt.get("authority") or {}, "Strategy Research receipt authority"
    )
    for key in (
        "workflow_created",
        "schedule_created",
        "provider_requests_authorized",
        "production_dataset_execution_authorized",
        "r2_list_read_write_authorized",
        "replacement_holdout_access_authorized",
        "backtest_admission_authorized",
        "trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if receipt_authority.get(key) is not False:
            raise RuntimeError(f"Strategy Research receipt boundary changed: {key}")

    return {
        "candidate_count": int(candidate_search["expected_candidate_count"]),
        "family_count": len(families),
        "horizon_count": len(horizons),
        "edge_method_count": len(edge_methods),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    dashboard = load(args.input)
    materialization, usage, equivalence = validate_foundation()
    lineage = validate_render_lineage()
    strategy_research = validate_strategy_research_lineage()

    require_dict(materialization.get("exact_scope") or {}, "funding exact scope")
    postwrite = require_dict(materialization.get("postwrite_results") or {}, "funding postwrite")
    inventory = require_dict(usage.get("inventory") or {}, "R2 inventory")
    eq_aggregate = require_dict(equivalence.get("aggregate") or {}, "equivalence aggregate")
    v10 = require_dict(lineage["v10"], "V0.10 config")
    v10_scope = require_dict(v10.get("scientific_scope") or {}, "V0.10 scope")

    project = require_dict(dashboard.get("project") or {}, "dashboard project")
    if project.get("mode") != "PAPER-ONLY":
        raise RuntimeError("dashboard must remain PAPER-ONLY")
    if project.get("liveTradingAuthorized") is not False:
        raise RuntimeError("dashboard live-trading boundary changed")

    project.update(
        {
            "fundingMaterializationComplete": True,
            "fundingMaterializationState": "PASS",
            "fundingV0_2UploadedObjectCount": int(postwrite["uploaded_object_count"]),
            "fundingV0_2VerifiedExistingObjectCount": int(
                postwrite["verified_existing_object_count"]
            ),
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
            "renderMetadataV0_7State": "HISTORICAL_PREPARED_EXECUTION_NOT_AUTHORIZED",
            "renderMetadataV0_8CutoverState": "HISTORICAL_PREPARED_EXECUTION_NOT_AUTHORIZED",
            "renderMetadataV0_8SharedSecretState": "PASS_FROZEN",
            "renderMetadataV0_9SmokeState": "PASS_FROZEN",
            "renderMetadataV0_10CutoverState": "EFFECTIVE_AUTHORIZED",
            "v0_10EmergencyScheduleRegistrationState": "EFFECTIVE",
            "v0_10EmergencyScheduleRegistrationMergeSha": (
                "cf83b6320bc0f0817d8e6ae15d88fe304b933330"
            ),
            "metadataStabilityState": "NOT_YET_RUN",
            "replacementHoldoutState": "FROZEN_UNOPENED",
            "currentMetadataCaptureExecutionPath": "github_hosted_ubuntu_v0_10",
            "currentMetadataCaptureBinanceTransport": "render_free_frankfurt_v0_10_relay",
            "oldV0_2ScheduledExecutionAuthorized": False,
            "successorMetadataCaptureExecutionAuthorized": True,
            "successorMetadataScheduleEnabled": True,
            "metadataCapturePathsConcurrentAuthorized": False,
            "metadataCaptureStartUtc": str(v10_scope["metadata_capture_start_utc"]),
            "metadataCaptureEndUtc": str(v10_scope["metadata_capture_end_utc"]),
            "metadataCaptureHourlySlotCount": int(v10_scope["hourly_slot_count"]),
            "metadataCaptureScheduledMinutesUtc": list(v10_scope["scheduled_minutes_utc"]),
            "cloudRuntimeMonthlyBudgetUsd": 0,
            "strategyResearchLoopState": "PREPARED_RESEARCH_ONLY",
            "strategyResearchCandidateCount": strategy_research["candidate_count"],
            "strategyResearchFamilyCount": strategy_research["family_count"],
            "strategyResearchHorizonCount": strategy_research["horizon_count"],
            "strategyEdgeValidationState": "PREPARED_RESEARCH_ONLY",
            "strategyEdgeMethodCount": strategy_research["edge_method_count"],
            "strategyResearchExecutionAuthorized": False,
            "strategyModelPromotionAuthority": 0,
            "tradePlanAuthorized": False,
            "liveTradingAuthorized": False,
        }
    )
    dashboard["project"] = project
    dashboard["schema"] = "qookey-dashboard-authority-snapshot-v0.10"
    dashboard["snapshotLabel"] = (
        "Repository 正式 Authority 狀態快照 · Equivalence V0.1 FAIL / "
        "Funding V0.2 R2 PASS / V0.10 Metadata Cutover EFFECTIVE / "
        "Schedule Re-registration EFFECTIVE / Strategy Research Loop PREPARED"
    )

    source_authorities = dashboard.get("sourceAuthorities") or []
    if not isinstance(source_authorities, list):
        raise RuntimeError("dashboard sourceAuthorities shape changed")
    for path in (
        V05_RENDER_PASS,
        V06_RENDER_TRANSITION,
        V07_RENDER_PROTOCOL,
        V08_CUTOVER_PROTOCOL,
        V08_CUTOVER_RECEIPT,
        V08_HANDSHAKE,
        V09_SMOKE,
        V10_CONFIG,
        V10_AUTHORITY,
        V10_EMERGENCY_SCHEDULE_AUTHORITY,
        V10_EMERGENCY_SCHEDULE_EFFECTIVE,
        STRATEGY_EDGE_CONFIG,
        STRATEGY_EDGE_RECEIPT,
        STRATEGY_RESEARCH_CONFIG,
        STRATEGY_RESEARCH_RECEIPT,
        OLD_V02_WORKFLOW,
        V10_WORKFLOW,
    ):
        text = str(path)
        if text not in source_authorities:
            source_authorities.append(text)
    dashboard["sourceAuthorities"] = source_authorities

    pipeline_raw = dashboard.get("pipeline") or []
    if not isinstance(pipeline_raw, list):
        raise RuntimeError("dashboard pipeline shape changed")
    pipeline = [require_dict(row, "dashboard pipeline row") for row in pipeline_raw]
    replace_pipeline_item(
        pipeline,
        "Funding V0.2 實際 R2 Materialization",
        "正式 run 32168151926 已完成：192/192 identities post-write 驗證 PASS；HYPEUSDT 2026 仍維持 deferred。",
        "PASS",
    )
    replace_pipeline_item(
        pipeline,
        "R2 實際使用容量",
        "最新 frozen read-only inventory：457 objects / 22.120404 MB；V0.10 每次 metadata write 前仍需 fresh whole-bucket headroom check。",
        "PASS",
    )
    replace_pipeline_item(
        pipeline,
        "Pionex ↔ Binance 等價性",
        "凍結 V0.1 已完成 45/45 pairs：18 PASS / 18 REVIEW / 9 FAIL；source switch 與 W1 materialization 維持未授權。",
        "FAIL",
    )
    replace_pipeline_item(
        pipeline,
        "Render Free Binance Transport",
        "V0.5 Frankfurt transport PASS；V0.6 successor transport authority PASS；公開 exchangeInfo sanitized evidence symbol_count=872。",
        "PASS",
    )
    replace_pipeline_item(
        pipeline,
        "Render Metadata V0.7 Protocol",
        "歷史 prepared authority 保留；V0.7 raw relay 仍 hard-disabled，不是 current execution path。",
        "PREPARED",
    )
    replace_pipeline_item(
        pipeline,
        "Render Metadata V0.8 Cutover",
        "歷史 prepared contract 保留；shared-secret handshake 已 PASS 並凍結。V0.10 已接手 effective execution authority。",
        "PASS",
    )
    replace_pipeline_item(
        pipeline,
        "V0.8 Shared Secret / V0.9 Smoke",
        "Shared-secret handshake 與 authenticated Render relay smoke 均已 PASS 並凍結為 regression-only evidence。",
        "PASS",
    )
    replace_pipeline_item(
        pipeline,
        "V0.10 Metadata Atomic Cutover",
        "PR #127 已合併；V0.2 self-hosted schedule 已退役，V0.10 GitHub-hosted schedule 已成為 current metadata execution path。",
        "AUTHORIZED",
    )
    replace_pipeline_item(
        pipeline,
        "V0.10 Schedule Re-registration",
        "PR #201 已合併至 protected main；等價的 :17/:47 schedule registration text 已生效。先前缺漏與失敗仍保留，Pionex failure root cause 仍未確認。",
        "EFFECTIVE",
    )
    replace_pipeline_item(
        pipeline,
        "Metadata Stability 194 Slots",
        "Frozen window 2026-08-27 至 2026-09-04；完整 194-slot stability evidence 尚未完成。",
        "PENDING",
    )
    replace_pipeline_item(
        pipeline,
        "Strategy Research Loop V0.1",
        "PR #204 已合併：120 個預註冊候選、4 類策略、短線／中線／波段三種週期；目前只允許 synthetic fixtures。",
        "PREPARED",
    )
    replace_pipeline_item(
        pipeline,
        "Strategy Edge Validation V0.1",
        "六項 anti-overfitting 與驗證方法已準備；最強結果也只進入人工審查，不會自動晉升模型。",
        "PREPARED",
    )
    dashboard["pipeline"] = pipeline

    gates_raw = dashboard.get("gates") or []
    if not isinstance(gates_raw, list):
        raise RuntimeError("dashboard gates shape changed")
    gates = [require_dict(row, "dashboard gate row") for row in gates_raw]
    upsert_gate(
        gates,
        "R2 儲存預算",
        "最新 frozen inventory 22.120404 MB / 457 objects；每次 V0.10 metadata write 前須 fresh whole-bucket inventory，8 GB hard stop fail closed。",
        "PASS",
        "pass",
        False,
    )
    upsert_gate(
        gates,
        "Provider 等價性",
        "V0.1 Gate 正式 FAIL：45 pairs 中 9 FAIL；不得降低 frozen thresholds，也不得以 Binance 改寫 Pionex provenance。",
        "FAIL",
        "danger",
        True,
    )
    upsert_gate(
        gates,
        "Funding R2 Materialization",
        "正式 run 32168151926 已完成 192/192 identities post-write 驗證；HYPEUSDT 2026 仍維持 deferred。",
        "PASS",
        "pass",
        False,
    )
    upsert_gate(
        gates,
        "Render Metadata Cutover",
        "V0.10 atomic cutover 已生效：V0.2 schedule retired、V0.10 schedule authorized；concurrent capture path 仍禁止。",
        "AUTHORIZED",
        "pass",
        False,
    )
    upsert_gate(
        gates,
        "V0.10 Metadata Cutover",
        "Atomic old/new cutover 已生效；V0.10 只授權 frozen-window metadata capture 與 metadata-only R2 writes。",
        "AUTHORIZED",
        "pass",
        False,
    )
    upsert_gate(
        gates,
        "Metadata Stability",
        "194 個 UTC hourly slots 尚未完成；完整 stability review 前不得進入 replacement holdout candle access。",
        "PENDING",
        "pending",
        True,
    )
    upsert_gate(
        gates,
        "Replacement Holdout",
        "2026-08-28 至 2026-09-03 維持 FROZEN_UNOPENED；metadata capture 不等於 holdout-access authority。",
        "NOT_AUTHORIZED",
        "blocked",
        True,
    )
    upsert_gate(
        gates,
        "策略研究執行",
        "Strategy Research Loop 僅準備合成測試；沒有 production dataset、provider、R2、workflow 或 schedule 執行權限。",
        "NOT_AUTHORIZED",
        "blocked",
        True,
    )
    upsert_gate(
        gates,
        "策略自動晉升",
        "Edge PASS 也只能產生人工審查資格；model promotion authority 維持 0。",
        "NOT_AUTHORIZED",
        "blocked",
        True,
    )
    dashboard["gates"] = gates

    security = require_dict(dashboard.get("securityBoundary") or {}, "dashboard security")
    security.update(
        {
            "containsSecrets": False,
            "containsPrivateExchangeResponses": False,
            "authorizesSourceSwitch": False,
            "authorizesPionexNativeRelabeling": False,
            "authorizesTradePlans": False,
            "authorizesLiveTrading": False,
            "authorizesMetadataCapture": True,
            "authorizesHoldoutAccess": False,
        }
    )
    dashboard["securityBoundary"] = security

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(dashboard, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "stage": "DASHBOARD_LATEST_AUTHORITY_OVERLAY_V0_10_PASS",
                "funding_materialization_state": project["fundingMaterializationState"],
                "equivalence_gate_state": project["providerEquivalenceGateState"],
                "render_v0_9": project["renderMetadataV0_9SmokeState"],
                "render_v0_10": project["renderMetadataV0_10CutoverState"],
                "v0_10_schedule_registration": project[
                    "v0_10EmergencyScheduleRegistrationState"
                ],
                "current_capture_path": project["currentMetadataCaptureExecutionPath"],
                "successor_capture_authorized": project[
                    "successorMetadataCaptureExecutionAuthorized"
                ],
                "successor_schedule_enabled": project["successorMetadataScheduleEnabled"],
                "metadata_stability": project["metadataStabilityState"],
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
