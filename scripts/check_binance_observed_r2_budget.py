#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from crypto_autopilot.binance.capacity import estimate_binance_observed_capacity
from crypto_autopilot.storage.budget import R2Guardrails, R2Pricing, R2ProjectedUsage, evaluate_r2_budget


POLICY = Path("config/r2_budget_v0_1.json")
ESTIMATE = Path("research/estimates/2026-08-18-binance-observed-r2-budget.json")
AUTHORITY = Path("research/receipts/2026-08-18-binance-2025-r2-pilot.json")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(usage: dict, policy: dict) -> dict:
    pricing = policy["pricing_snapshot"]
    guardrails = policy["project_guardrails"]
    return evaluate_r2_budget(
        R2ProjectedUsage(
            storage_gb_month=float(usage["storage_gb_month"]),
            class_a_requests_per_month=int(usage["class_a_requests_per_month"]),
            class_b_requests_per_month=int(usage["class_b_requests_per_month"]),
        ),
        R2Pricing(
            free_storage_gb_month=float(pricing["free_storage_gb_month"]),
            storage_usd_per_gb_month=float(pricing["storage_usd_per_gb_month"]),
            free_class_a_requests_per_month=int(pricing["free_class_a_requests_per_month"]),
            class_a_usd_per_million=float(pricing["class_a_usd_per_million"]),
            free_class_b_requests_per_month=int(pricing["free_class_b_requests_per_month"]),
            class_b_usd_per_million=float(pricing["class_b_usd_per_million"]),
        ),
        R2Guardrails(
            storage_warn_gb_month=float(guardrails["storage_warn_gb_month"]),
            storage_block_gb_month=float(guardrails["storage_block_gb_month"]),
            class_a_warn_requests_per_month=int(guardrails["class_a_warn_requests_per_month"]),
            class_a_block_requests_per_month=int(guardrails["class_a_block_requests_per_month"]),
            class_b_warn_requests_per_month=int(guardrails["class_b_warn_requests_per_month"]),
            class_b_block_requests_per_month=int(guardrails["class_b_block_requests_per_month"]),
        ),
    )


def assert_close(name: str, observed: float, expected: float, tolerance: float = 1e-9) -> None:
    if abs(observed - expected) > tolerance:
        raise RuntimeError(f"{name} mismatch: recomputed={observed}, frozen={expected}")


def main() -> int:
    policy = load(POLICY)
    estimate = load(ESTIMATE)
    authority = load(AUTHORITY)
    if authority.get("status") != "PASS" or authority.get("stage") != "BINANCE_2025_R2_PILOT_PASS":
        raise RuntimeError("Binance 2025 R2 pilot authority must be PASS")

    basis = estimate["basis"]
    if int(authority["scope"]["total_rows"]) != int(basis["observed_rows"]):
        raise RuntimeError("observed row count no longer matches frozen pilot authority")
    if int(authority["scope"]["total_parquet_bytes"]) != int(basis["observed_parquet_bytes"]):
        raise RuntimeError("observed Parquet byte count no longer matches frozen pilot authority")

    recalculated = estimate_binance_observed_capacity(
        observed_rows=int(basis["observed_rows"]),
        observed_parquet_bytes=int(basis["observed_parquet_bytes"]),
        observed_candidate_count=int(basis["observed_candidate_count"]),
        rows_per_full_market_year=int(basis["rows_per_full_market_year"]),
        target_markets=int(basis["target_markets"]),
        target_years=int(basis["target_years"]),
    )
    assert_close(
        "observed_bytes_per_row",
        recalculated.observed_bytes_per_row,
        float(basis["observed_bytes_per_row"]),
        tolerance=1e-12,
    )
    assert_close(
        "full_candidate_year_equivalent_bytes",
        recalculated.full_candidate_year_equivalent_bytes,
        float(basis["full_candidate_year_equivalent_bytes"]),
        tolerance=1e-6,
    )
    assert_close(
        "canonical_target_gb",
        recalculated.canonical_target_gb,
        float(estimate["storage_scenarios"]["canonical_only"]["gb_month"]),
    )
    assert_close(
        "canonical_plus_staging_gb",
        recalculated.canonical_plus_staging_gb,
        float(estimate["storage_scenarios"]["canonical_plus_retained_staging"]["gb_month"]),
    )
    assert_close(
        "three_x_capacity_stress_gb",
        recalculated.three_x_capacity_stress_gb,
        float(estimate["storage_scenarios"]["three_x_capacity_stress"]["gb_month"]),
    )

    planned = evaluate(estimate["planned_usage"], policy)
    stress = evaluate(estimate["stress_usage"], policy)
    expected = estimate["gate_expectation"]
    if planned["status"] != expected["planned_usage"]:
        raise RuntimeError(
            f"planned Binance observed budget expected {expected['planned_usage']}, got {planned['status']}"
        )
    if stress["status"] != expected["three_x_capacity_and_operation_stress"]:
        raise RuntimeError(
            "stress Binance observed budget expected "
            f"{expected['three_x_capacity_and_operation_stress']}, got {stress['status']}"
        )
    if planned["status"] == "BLOCK" or stress["status"] == "BLOCK":
        return 2

    print(
        json.dumps(
            {
                "status": "PASS",
                "canonical_target_gb": recalculated.canonical_target_gb,
                "canonical_plus_staging_gb": recalculated.canonical_plus_staging_gb,
                "three_x_capacity_stress_gb": recalculated.three_x_capacity_stress_gb,
                "planned_gate": planned,
                "stress_gate": stress,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
