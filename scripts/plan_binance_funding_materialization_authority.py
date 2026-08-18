from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from crypto_autopilot.binance_funding_materialization_plan import (
    build_materialization_scope,
    validate_authorities,
    validate_plan_config,
)


DEFAULT_CONFIG = "config/binance_funding_materialization_authority_v0_1.json"


def load_json(path: str) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--output", default="artifacts/binance-funding-materialization-authority-plan.json")
    args = parser.parse_args()

    config = load_json(args.config)
    validate_plan_config(config)
    coverage = load_json(str(config["coverage_authority"]))
    budget = load_json(str(config["budget_authority"]))
    source_proof = load_json(str(config["source_proof_authority"]))
    validate_authorities(coverage, budget, source_proof)

    scope = build_materialization_scope(coverage)
    annual_rows = [
        {
            "symbol": item.symbol,
            "year": item.year,
            "months": list(item.months),
            "source_archive_count": item.source_archive_count,
            "canonical_key": item.canonical_key,
            "partition_receipt_key": item.receipt_key,
        }
        for item in scope.annual_scopes
    ]
    canonical_scope_bytes = json.dumps(annual_rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    scope_sha256 = hashlib.sha256(canonical_scope_bytes).hexdigest()

    planned_partition_objects = scope.canonical_objects * 2
    global_metadata_objects = int(config["planned_global_metadata_objects"])
    payload = {
        "schema": "binance-funding-materialization-authority-plan-v0.1",
        "execution_status": "PASS",
        "plan_status": "ELIGIBLE_FOR_EXPLICIT_AUTHORITY",
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "execution_exchange": "pionex",
        "native_to_execution_exchange": False,
        "dataset": "fundingRate",
        "coverage_authority": config["coverage_authority"],
        "budget_authority": config["budget_authority"],
        "source_proof_authority": config["source_proof_authority"],
        "scope": {
            "symbol_count": scope.symbol_count,
            "available_symbol_months": scope.symbol_months,
            "annual_canonical_objects": scope.canonical_objects,
            "annual_partition_receipts": scope.canonical_objects,
            "planned_global_metadata_objects": global_metadata_objects,
            "planned_total_r2_write_objects": planned_partition_objects + global_metadata_objects,
            "canonical_scope_sha256": scope_sha256,
            "annual_scopes": annual_rows,
        },
        "writer_contract": {
            "all_1010_source_archives_must_checksum_and_content_audit_before_first_r2_write": True,
            "all_annual_cross_month_cadence_audits_must_pass_before_first_r2_write": True,
            "materialization_cadence_jitter_tolerance_ms": int(config["materialization_cadence_jitter_tolerance_ms"]),
            "raw_source_calc_time_preserved": True,
            "source_declared_funding_interval_hours_preserved": True,
            "source_archives_retained_in_r2": False,
            "existing_canonical_object_policy": config["existing_canonical_object_policy"],
            "existing_receipt_policy": config["existing_receipt_policy"],
            "writer_requires_explicit_authority_receipt": True,
        },
        "explicit_authority_may_authorize": {
            "funding_r2_writes_for_exact_scope_only": True,
            "canonical_funding_objects": True,
            "partition_receipts": True,
            "run_metadata_objects": True,
        },
        "explicit_authority_must_not_authorize": {
            "source_switch": True,
            "provider_splicing": True,
            "pionex_native_relabeling": True,
            "historical_universe_membership": True,
            "backtest_admission": True,
            "automatic_trade_plans": True,
            "real_money_orders": True,
            "live_trading": True,
        },
        "planning_boundary": {
            "r2_writes_performed": False,
            "funding_materialization_authorized": False,
            "source_switch_authorized": False,
            "pionex_native_relabel_authorized": False,
            "backtest_admission_authorized": False,
            "trade_plan_authorized": False,
            "live_trading_authorized": False,
        },
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "execution_status": "PASS",
                "plan_status": payload["plan_status"],
                "symbol_months": scope.symbol_months,
                "annual_objects": scope.canonical_objects,
                "scope_sha256": scope_sha256,
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
