from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/cloud_free_tier_policy_v0_1.json"
RECEIPT = ROOT / "research/receipts/2026-08-19-provider-equivalence-v0-3-cloudflare-container-free-plan-blocked.json"


def _policy() -> dict[str, object]:
    return json.loads(POLICY.read_text())


def test_free_only_policy_never_authorizes_paid_runtime() -> None:
    cfg = _policy()
    assert cfg["status"] == "FREE_ONLY_FROZEN"
    assert cfg["monthly_budget_usd"] == 0
    billing = cfg["billing_policy"]
    assert billing["workers_paid_upgrade_authorized"] is False
    assert billing["paid_fallback_authorized"] is False
    assert billing["usage_overage_authorized"] is False
    assert billing["automatic_subscription_change_authorized"] is False
    assert billing["fail_closed_before_project_safety_ceiling"] is True


def test_project_ceilings_stay_below_official_free_limits() -> None:
    cf = _policy()["cloudflare"]

    workers = cf["workers"]
    assert workers["project_safety_ceiling"]["requests_per_day"] < workers["official_free_limits"]["requests_per_day"]
    assert workers["project_safety_ceiling"]["external_subrequests_per_invocation"] < workers["official_free_limits"]["external_subrequests_per_invocation"]
    assert workers["project_safety_ceiling"]["cron_triggers"] < workers["official_free_limits"]["cron_triggers_per_account"]

    workflows = cf["workflows"]
    assert workflows["project_safety_ceiling"]["steps_per_day"] < workflows["official_free_limits"]["steps_per_day"]
    assert workflows["project_safety_ceiling"]["storage_gb_month"] < workflows["official_free_limits"]["storage_gb_month"]
    assert workflows["project_safety_ceiling"]["max_steps_per_instance"] < workflows["official_free_limits"]["max_steps_per_instance"]

    queues = cf["queues"]
    assert queues["project_safety_ceiling"]["operations_per_day"] < queues["official_free_limits"]["operations_per_day"]

    d1 = cf["d1"]
    assert d1["project_safety_ceiling"]["rows_read_per_day"] < d1["official_free_limits"]["rows_read_per_day"]
    assert d1["project_safety_ceiling"]["rows_written_per_day"] < d1["official_free_limits"]["rows_written_per_day"]
    assert d1["project_safety_ceiling"]["storage_gb_total"] < d1["official_free_limits"]["storage_gb_total"]

    r2 = cf["r2_standard"]
    assert r2["project_safety_ceiling"]["storage_gb_month"] < r2["official_free_limits"]["storage_gb_month"]
    assert r2["project_safety_ceiling"]["class_a_requests_per_month"] < r2["official_free_limits"]["class_a_requests_per_month"]
    assert r2["project_safety_ceiling"]["class_b_requests_per_month"] < r2["official_free_limits"]["class_b_requests_per_month"]


def test_paid_or_usage_based_optional_services_are_not_enabled() -> None:
    cf = _policy()["cloudflare"]
    assert cf["containers"]["allowed"] is False
    assert cf["containers"]["upgrade_authorized"] is False
    assert cf["containers"]["automatic_retry_authorized"] is False
    assert cf["r2_sql"]["allowed"] is False
    assert cf["r2_data_catalog"]["allowed"] is False
    assert cf["durable_objects"]["allowed"] is False


def test_free_only_policy_does_not_open_scientific_or_trading_gates() -> None:
    boundary = _policy()["authority_boundary"]
    assert boundary["v0_1_equivalence_status"] == "FAIL"
    assert boundary["v0_1_mutated"] is False
    assert boundary["v0_2_self_hosted_mac_transport_authority_mutated"] is False
    for key in (
        "cloudflare_container_transport_authorized",
        "cloud_transport_authorized_for_metadata_capture",
        "metadata_capture_execution_authorized_by_this_policy",
        "holdout_candle_access_authorized",
        "source_switch_authorized",
        "historical_universe_membership_authorized",
        "backtest_admission_authorized",
        "automatic_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        assert boundary[key] is False, key


def test_container_block_receipt_is_fail_closed_and_no_binance_probe_happened() -> None:
    receipt = json.loads(RECEIPT.read_text())
    assert receipt["stage"] == "V0_3_CLOUDFLARE_CONTAINER_BLOCKED_FREE_PLAN"
    assert receipt["evidence"]["validate"] == "PASS"
    assert receipt["evidence"]["worker_upload_completed"] is True
    assert receipt["evidence"]["container_image_build_completed"] is True
    assert receipt["evidence"]["container_application_registration"] == "UNAUTHORIZED"
    assert receipt["evidence"]["binance_probe_reached"] is False
    assert receipt["result"]["transport_pass"] is False
    assert receipt["result"]["retry_same_container_path_authorized"] is False
    assert receipt["result"]["workers_paid_upgrade_authorized"] is False
    assert receipt["side_effects"]["r2_writes_performed"] is False
    assert receipt["side_effects"]["holdout_candles_accessed"] is False
    assert receipt["side_effects"]["source_switch_performed"] is False
    assert receipt["side_effects"]["live_trading_performed"] is False
