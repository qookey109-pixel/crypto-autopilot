from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from crypto_autopilot.historical_universe_review import (
    build_membership_contract,
    review_target_wave,
)


DEFAULT_CONFIG = "config/historical_universe_long_horizon_review_v0_1.json"


def load_json(path: str) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--output", default="artifacts/historical-universe-long-horizon-review.json")
    args = parser.parse_args()

    config = load_json(args.config)
    coverage_path = str(config["coverage_authority"])
    staged_plan_path = str(config["staged_plan_authority"])
    coverage = load_json(coverage_path)
    staged_plan = load_json(staged_plan_path)

    review = review_target_wave(coverage, staged_plan, config)
    membership_contract = build_membership_contract(config)

    full_year = [scope.symbol for scope in review.scopes if scope.full_year]
    partial_year = [scope.symbol for scope in review.scopes if not scope.full_year]
    payload = {
        "schema": "historical-universe-long-horizon-review-v0.1",
        "execution_status": "PASS",
        "review_status": "COMPLETE",
        "review_prerequisite_satisfied": True,
        "historical_universe_membership_authority_status": "NOT_READY",
        "provider": "binance_usdm",
        "execution_exchange": "pionex",
        "market_type": "perp",
        "target_wave": review.target_wave,
        "target_year": review.target_year,
        "coverage_authority": coverage_path,
        "staged_plan_authority": staged_plan_path,
        "required_intervals": list(config["required_intervals"]),
        "acquisition_scope_review": {
            "status": "CONSISTENT_WITH_FROZEN_COVERAGE_AND_PLAN",
            "symbol_count": review.symbol_count,
            "symbol_months": review.symbol_months,
            "full_year_symbol_count": review.full_year_symbol_count,
            "partial_year_symbol_count": len(partial_year),
            "symbols": [
                {
                    "symbol": scope.symbol,
                    "months": list(scope.months),
                    "month_count": len(scope.months),
                    "full_year": scope.full_year,
                }
                for scope in review.scopes
            ],
            "excluded_symbols": list(review.excluded_symbols),
            "full_year_symbols": full_year,
            "partial_year_symbols": partial_year,
            "wave_materialization_authorized": False,
        },
        "membership_evidence_review": {
            "coverage_receipt_is_membership_authority": False,
            "coverage_receipt_is_listing_authority": False,
            "verified_partition_receipts_exist_for_target_wave": False,
            "pre_materialization_membership_record_count": 0,
            "membership_contract": membership_contract,
            "historical_universe_membership_authorized": False,
            "native_pionex_backtest_admission_authorized": False,
        },
        "dependency_resolution": {
            "circular_dependency_resolved": True,
            "review_can_complete_before_materialization": True,
            "reason": (
                "The review validates acquisition scope and the future evidence contract only. "
                "Historical Universe membership remains blocked until audited target-wave partition receipts exist."
            ),
            "post_materialization_next_step": (
                "Convert each audited Binance partition receipt into provider-separated proxy HistoricalMarketRecord evidence; "
                "do not create Pionex-native membership or infer listing dates from first candles."
            ),
        },
        "remaining_before_w1_materialization": [
            "PIONEX_BINANCE_EQUIVALENCE_GATE_PASS_AUTHORITY",
            "EXPLICIT_STAGED_EXPANSION_AUTHORITY_FOR_W1",
        ],
        "remaining_before_backtest_membership": [
            "AUDITED_W1_PARTITION_RECEIPTS_FOR_15M_60M_4H",
            "PROVIDER_SEPARATED_HISTORICAL_UNIVERSE_RECORDS",
            "SEPARATE_SOURCE_SWITCH_OR_PROXY_ADMISSION_AUTHORITY_IF_BINANCE_IS_USED_FOR_STRATEGY_BACKTESTS",
        ],
        "interpretation_boundary": {
            "review_completion_authorizes_materialization": False,
            "review_completion_authorizes_backtest_membership": False,
            "coverage_onset_equals_listing_date": False,
            "binance_evidence_becomes_pionex_native": False,
            "provider_splicing_used": False,
            "current_universe_backprojection_used": False,
            "source_switch_authorized": False,
            "w1_materialization_authorized": False,
            "backtest_admission_authorized": False,
            "trade_plan_authorized": False,
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
                "review_status": payload["review_status"],
                "target_wave": review.target_wave,
                "target_year": review.target_year,
                "symbol_count": review.symbol_count,
                "symbol_months": review.symbol_months,
                "excluded_symbols": list(review.excluded_symbols),
                "membership_authority": payload["historical_universe_membership_authority_status"],
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
