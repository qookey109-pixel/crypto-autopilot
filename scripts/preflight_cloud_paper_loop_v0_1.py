from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def build_report(
    loop_contract: dict[str, Any],
    delivery_status: dict[str, Any],
    strategy_registry: dict[str, Any],
    writer_inventory: dict[str, Any],
) -> dict[str, Any]:
    activation = loop_contract.get("activation")
    if not isinstance(activation, dict) or activation.get("enabled") is not False:
        raise ValueError("non-access preflight requires Cloud Paper activation to remain disabled")

    strategies = strategy_registry.get("strategies")
    if not isinstance(strategies, list):
        raise ValueError("production strategy registry must be an array")

    blockers = delivery_status.get("activation_blockers")
    if not isinstance(blockers, dict):
        raise ValueError("Cloud Paper delivery blockers are missing")

    reservation = writer_inventory.get("account_wide_reservation_coverage")
    if not isinstance(reservation, dict):
        raise ValueError("R2 writer reservation coverage is missing")

    reason_codes = ["NON_ACCESS_PREFLIGHT_ONLY", "ACTIVATION_DISABLED"]
    for code, key in (
        ("R2_USAGE_EVIDENCE_MISSING", "shared_account_r2_usage_evidence"),
        ("D1_LEDGER_NOT_READY", "complete_account_wide_reservation_ledger"),
        ("D1_USAGE_EVIDENCE_MISSING", "d1_free_tier_usage_evidence"),
        ("CONTROLLED_MAIN_ACCEPTANCE_NOT_RUN", "controlled_main_acceptance"),
        ("GENESIS_PROOF_NOT_ACCEPTED", "genesis_empty_ledger_proof"),
        ("PRODUCTION_ENTRYPOINT_NOT_WIRED", "production_entrypoint_workflow"),
    ):
        value = blockers.get(key)
        if value not in (None, "", "PASS", "COMPLETE"):
            reason_codes.append(code)

    if reservation.get("cloud_paper_d1_ledger") != "PROVISIONED_AND_WIRED":
        if "D1_LEDGER_NOT_READY" not in reason_codes:
            reason_codes.append("D1_LEDGER_NOT_READY")
    if reservation.get("every_current_writer_reserves_through_shared_ledger") is not True:
        reason_codes.append("SHARED_WRITER_RESERVATIONS_NOT_PROVEN")
    if reservation.get("shared_account_r2_usage_evidence") != "VERIFIED_CURRENT":
        reason_codes.append("R2_USAGE_EVIDENCE_MISSING")
    if strategy_registry.get("status") == "EMPTY_NO_ELIGIBLE_STRATEGIES":
        reason_codes.append("STRATEGY_REGISTRY_EMPTY")
    if strategy_registry.get("model_quality") == "REJECT":
        reason_codes.append("MODEL_QUALITY_REJECT")
    if delivery_status.get("macro_regime") == "REGIME_UNAVAILABLE":
        reason_codes.append("MACRO_REGIME_UNAVAILABLE")

    return {
        "schema": "qookey-cloud-paper-nonaccess-preflight-v0.1",
        "status": "DISABLED",
        "mode": "NON_ACCESS_PREFLIGHT_ONLY",
        "reason_codes": sorted(set(reason_codes)),
        "strategy_registry_count": len(strategies),
        "strategy_outcome": "NOT_EVALUATED",
        "planned_schedule_cron_utc": loop_contract.get("schedule", {}).get("cron_utc"),
        "external_access": {
            "provider_requests_performed": 0,
            "r2_access_performed": False,
            "d1_access_performed": False,
            "training_performed": False,
            "holdout_accessed": False,
        },
        "authority": {
            "activation_enabled": False,
            "synthetic_data_in_production": False,
            "model_promotion": False,
            "source_switch": False,
            "real_money_orders": False,
            "live_trading": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit a Cloud Paper non-access preflight report.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = build_report(
        json.loads((ROOT / "config/cloud_paper_loop_v0_1.json").read_text(encoding="utf-8")),
        json.loads(
            (ROOT / "research/status/cloud-paper-delivery-v0-1.json").read_text(
                encoding="utf-8"
            )
        ),
        json.loads(
            (ROOT / "config/cloud_paper_strategy_registry_v0_1.json").read_text(
                encoding="utf-8"
            )
        ),
        json.loads(
            (ROOT / "research/status/cloud-paper-r2-writer-inventory-v0-1.json").read_text(
                encoding="utf-8"
            )
        ),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Cloud Paper preflight: {report['status']} ({len(report['reason_codes'])} reasons)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
