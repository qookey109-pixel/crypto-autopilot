from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.binance_funding_materialization_plan_v0_2 import (
    build_v0_2_scope,
    canonical_scope_rows,
    canonical_scope_sha256,
    validate_v0_2_authorities,
    validate_v0_2_config,
)


DEFAULT_CONFIG = "config/binance_funding_materialization_authority_v0_2.json"


def load_json(path: str) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--output", default="artifacts/binance-funding-materialization-plan-v0-2.json")
    args = parser.parse_args()

    config = load_json(args.config)
    validate_v0_2_config(config)
    coverage = load_json(str(config["coverage_authority"]))
    budget = load_json(str(config["budget_authority"]))
    source_proof = load_json(str(config["source_proof_authority"]))
    continuity_review = load_json(str(config["continuity_review_authority"]))
    validate_v0_2_authorities(coverage, budget, source_proof, continuity_review)

    scope = build_v0_2_scope(coverage)
    scope_sha = canonical_scope_sha256(scope)
    if scope_sha != config["expected_canonical_scope_sha256"]:
        raise RuntimeError(
            f"Funding V0.2 scope SHA mismatch: {scope_sha} != {config['expected_canonical_scope_sha256']}"
        )

    payload = {
        "schema": "binance-funding-materialization-plan-v0.2",
        "execution_status": "PASS",
        "plan_status": "ELIGIBLE_FOR_EXPLICIT_V0_2_AUTHORITY",
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "execution_exchange": "pionex",
        "native_to_execution_exchange": False,
        "dataset": "fundingRate",
        "scope": {
            "symbol_count": scope.symbol_count,
            "materialized_symbol_months": scope.symbol_months,
            "annual_canonical_objects": scope.canonical_objects,
            "annual_partition_receipts": scope.canonical_objects,
            "run_level_metadata_objects": int(config["planned_global_metadata_objects"]),
            "total_r2_object_identities": scope.canonical_objects * 2 + int(config["planned_global_metadata_objects"]),
            "canonical_scope_sha256": scope_sha,
            "source_checksum_set_sha256": config["expected_source_checksum_set_sha256"],
            "annual_scopes": canonical_scope_rows(scope),
        },
        "deferred_scope": config["deferred_annual_partitions"],
        "continuity_review_authority": config["continuity_review_authority"],
        "source_checksum_set_derivation": config["source_checksum_set_derivation"],
        "writer_contract": {
            "all_1003_materialized_source_archives_must_pass_before_first_r2_write": True,
            "all_94_annual_cross_month_audits_must_pass_before_first_r2_write": True,
            "all_94_annual_parquet_objects_must_build_before_first_r2_write": True,
            "materialization_cadence_jitter_tolerance_ms": 50,
            "raw_source_timestamps_preserved": True,
            "source_declared_intervals_preserved": True,
            "interpolation_forbidden": True,
            "provider_splicing_forbidden": True,
            "existing_objects_exact_verify_or_fail": True,
            "writer_requires_separate_v0_2_authority": True,
        },
        "planning_boundary": {
            "r2_writes_performed": False,
            "funding_materialization_authorized": False,
            "source_switch_authorized": False,
            "pionex_native_relabel_authorized": False,
            "historical_universe_membership_authorized": False,
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
                "source_months": scope.symbol_months,
                "annual_objects": scope.canonical_objects,
                "scope_sha256": scope_sha,
                "checksum_set_sha256": config["expected_source_checksum_set_sha256"],
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
