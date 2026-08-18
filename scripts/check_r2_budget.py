#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.r2_budget import R2Guardrails, R2Pricing, R2ProjectedUsage, evaluate_r2_budget


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the frozen Cloudflare R2 project budget gate.")
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path("config/r2_budget_v0_1.json"),
    )
    parser.add_argument(
        "--estimate",
        type=Path,
        default=Path("research/estimates/2026-08-18-r2-cost-budget.json"),
    )
    args = parser.parse_args()

    policy = load_json(args.policy)
    estimate = load_json(args.estimate)
    pricing_row = policy["pricing_snapshot"]
    guardrail_row = policy["project_guardrails"]
    usage_row = estimate["planned_usage"]

    result = evaluate_r2_budget(
        R2ProjectedUsage(
            storage_gb_month=float(usage_row["storage_gb_month"]),
            class_a_requests_per_month=int(usage_row["class_a_requests_per_month"]),
            class_b_requests_per_month=int(usage_row["class_b_requests_per_month"]),
        ),
        R2Pricing(
            free_storage_gb_month=float(pricing_row["free_storage_gb_month"]),
            storage_usd_per_gb_month=float(pricing_row["storage_usd_per_gb_month"]),
            free_class_a_requests_per_month=int(pricing_row["free_class_a_requests_per_month"]),
            class_a_usd_per_million=float(pricing_row["class_a_usd_per_million"]),
            free_class_b_requests_per_month=int(pricing_row["free_class_b_requests_per_month"]),
            class_b_usd_per_million=float(pricing_row["class_b_usd_per_million"]),
        ),
        R2Guardrails(
            storage_warn_gb_month=float(guardrail_row["storage_warn_gb_month"]),
            storage_block_gb_month=float(guardrail_row["storage_block_gb_month"]),
            class_a_warn_requests_per_month=int(guardrail_row["class_a_warn_requests_per_month"]),
            class_a_block_requests_per_month=int(guardrail_row["class_a_block_requests_per_month"]),
            class_b_warn_requests_per_month=int(guardrail_row["class_b_warn_requests_per_month"]),
            class_b_block_requests_per_month=int(guardrail_row["class_b_block_requests_per_month"]),
        ),
    )
    print(json.dumps(result, indent=2, sort_keys=True))

    expected = str(estimate.get("gate_expectation", {}).get("planned_usage") or "")
    if expected and result["status"] != expected:
        print(f"Expected gate status {expected}, got {result['status']}")
        return 3
    if result["status"] == "BLOCK":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
