from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

from crypto_autopilot.binance_expansion_plan import (
    build_waves,
    load_capacity_basis,
    load_coverage_windows,
    months_for_year,
    validate_config,
    validate_existing_2025,
)


DEFAULT_CONFIG = "config/binance_staged_expansion_plan_v0_1.json"


def load_json(path: str) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--output", default="artifacts/binance-staged-expansion-plan.json")
    args = parser.parse_args()

    config = load_json(args.config)
    validate_config(config)

    coverage_path = str(config["coverage_authority"])
    capacity_path = str(config["capacity_authority"])
    existing_path = str(config["existing_materialization_authority"])
    coverage = load_json(coverage_path)
    capacity = load_json(capacity_path)
    existing = load_json(existing_path)

    windows = load_coverage_windows(coverage)
    rows_per_full_market_year, bytes_per_row, staging_multiplier, stress_multiplier = load_capacity_basis(capacity)
    validate_existing_2025(existing)
    existing_scope = existing.get("scope") or {}
    existing_parquet_bytes = int(existing_scope.get("total_parquet_bytes") or 0)
    if existing_parquet_bytes <= 0:
        raise RuntimeError("existing 2025 authority has no positive Parquet byte count")

    materialized_years = tuple(int(year) for year in config.get("already_materialized_years", []))
    waves = build_waves(
        coverage,
        windows,
        already_materialized_years=materialized_years,
        rows_per_full_market_year=rows_per_full_market_year,
        bytes_per_row=bytes_per_row,
    )
    if not waves:
        raise RuntimeError("staged planner produced no historical expansion waves")
    if tuple(wave.year for wave in waves) != tuple(sorted((wave.year for wave in waves), reverse=True)):
        raise RuntimeError("historical expansion waves must be newest-to-oldest")
    if any(wave.year in materialized_years for wave in waves):
        raise RuntimeError("planner attempted to rewrite an already-materialized year")

    running_bytes = existing_parquet_bytes
    wave_rows: list[dict[str, object]] = []
    for wave in waves:
        running_bytes += wave.estimated_parquet_bytes
        wave_rows.append(
            {
                "wave_id": wave.wave_id,
                "year": wave.year,
                "symbol_count": wave.symbol_count,
                "symbol_months": wave.symbol_months,
                "source_archive_count": wave.source_archive_count,
                "planned_r2_object_count": wave.object_count,
                "estimated_rows": wave.estimated_rows,
                "estimated_parquet_bytes": wave.estimated_parquet_bytes,
                "estimated_canonical_gb": wave.estimated_parquet_bytes / 1_000_000_000,
                "cumulative_canonical_including_existing_2025_gb": running_bytes / 1_000_000_000,
                "symbols": [
                    {
                        "symbol": item.symbol,
                        "months": list(item.months),
                        "month_count": len(item.months),
                        "partial_year": item.months != tuple(range(1, 13)),
                    }
                    for item in wave.symbol_years
                ],
                "materialization_authorized": False,
            }
        )

    protocol = coverage.get("protocol") or {}
    last_complete_text = str(protocol.get("last_complete_month_scanned") or "")
    last_year, last_month = (int(piece) for piece in last_complete_text.split("-", 1))
    deferred_year = last_year
    deferred_symbol_rows: list[dict[str, object]] = []
    for window in windows:
        months = months_for_year(window, deferred_year, last_complete=(last_year, last_month))
        if months:
            deferred_symbol_rows.append(
                {
                    "symbol": window.symbol,
                    "months": list(months),
                    "month_count": len(months),
                }
            )
    deferred_symbol_months = sum(int(row["month_count"]) for row in deferred_symbol_rows)
    deferred_rows = math.ceil(rows_per_full_market_year * deferred_symbol_months / 12)
    deferred_bytes = math.ceil(deferred_rows * bytes_per_row)

    incremental_bytes = sum(wave.estimated_parquet_bytes for wave in waves)
    total_canonical_bytes = existing_parquet_bytes + incremental_bytes
    observed_projection_gb = float(
        (capacity.get("storage_projection") or {}).get("canonical_only_gb_month") or 0.0
    )

    payload = {
        "schema": "binance-staged-multiyear-expansion-plan-v0.1",
        "execution_status": "PASS",
        "plan_status": "READY_FOR_REVIEW",
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "execution_exchange": "pionex",
        "native_to_execution_exchange": False,
        "may_authorize_pionex_native_history": False,
        "config": args.config,
        "coverage_authority": coverage_path,
        "capacity_authority": capacity_path,
        "existing_materialization_authority": existing_path,
        "candidate_count": len(windows),
        "planning_scope": "trade_klines_only",
        "already_materialized_years": list(materialized_years),
        "wave_policy": config["wave_policy"],
        "wave_count": len(waves),
        "waves": wave_rows,
        "totals": {
            "historical_increment_symbol_months": sum(wave.symbol_months for wave in waves),
            "historical_increment_source_archives": sum(wave.source_archive_count for wave in waves),
            "historical_increment_r2_objects": sum(wave.object_count for wave in waves),
            "historical_increment_estimated_rows": sum(wave.estimated_rows for wave in waves),
            "historical_increment_estimated_parquet_bytes": incremental_bytes,
            "existing_2025_parquet_bytes": existing_parquet_bytes,
            "projected_canonical_through_historical_waves_bytes": total_canonical_bytes,
            "projected_canonical_through_historical_waves_gb": total_canonical_bytes / 1_000_000_000,
            "projected_with_retained_staging_gb": total_canonical_bytes * staging_multiplier / 1_000_000_000,
            "projected_three_x_capacity_stress_gb": total_canonical_bytes * stress_multiplier / 1_000_000_000,
            "share_of_observed_250_market_8y_canonical_projection": (
                (total_canonical_bytes / 1_000_000_000) / observed_projection_gb
                if observed_projection_gb > 0
                else None
            ),
        },
        "current_incomplete_year_deferred": {
            "year": deferred_year,
            "through_complete_month": last_month,
            "symbol_count": len(deferred_symbol_rows),
            "symbol_months": deferred_symbol_months,
            "estimated_rows": deferred_rows,
            "estimated_parquet_bytes": deferred_bytes,
            "symbols": deferred_symbol_rows,
            "reason": "Current incomplete year is intentionally excluded from historical expansion waves by frozen protocol.",
            "materialization_authorized": False,
        },
        "required_before_any_wave_materialization": config[
            "required_before_any_wave_materialization"
        ],
        "separate_future_authorities": config["separate_future_authorities"],
        "interpretation_boundary": {
            "planner_reads_frozen_coverage_not_assumed_listing_dates": True,
            "partial_onset_months_are_never_synthesized": True,
            "partial_month_budgeted_as_full_month_equivalent": True,
            "existing_2025_r2_objects_are_not_replanned": True,
            "current_incomplete_year_is_deferred": True,
            "mark_price_materialization_in_scope": False,
            "funding_materialization_in_scope": False,
            "historical_universe_authority_complete": False,
            "pionex_binance_equivalence_passed": False,
            "source_switch_authorized": False,
            "large_scale_backfill_authorized": False,
            "r2_writes_performed": False,
            "live_trading_authorized": False,
        },
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "github_sha": os.getenv("GITHUB_SHA"),
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "execution_status": payload["execution_status"],
                "plan_status": payload["plan_status"],
                "wave_years": [wave.year for wave in waves],
                "incremental_objects": payload["totals"]["historical_increment_r2_objects"],
                "incremental_parquet_bytes": incremental_bytes,
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
