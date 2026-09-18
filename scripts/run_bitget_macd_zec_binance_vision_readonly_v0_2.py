#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from crypto_autopilot.binance.vision import ingest_kline_archive
from crypto_autopilot.research.bitget_macd import (
    BitgetMacdResearchConfig,
    default_bitget_macd_candidate_grid,
    result_summary,
    run_bitget_macd_long_30m_research,
)
from crypto_autopilot.research.bitget_macd_binance_vision import (
    combine_verified_zec_archives,
    zec_monthly_archive_keys,
)
from crypto_autopilot.research.bitget_macd_validation import (
    BitgetMacdValidationPlan,
    build_preregistered_windows,
    plan_sha256,
    run_preregistered_validation,
    validation_summary,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUTHORITY = (
    ROOT
    / "research/receipts/2026-09-18-bitget-macd-zec-binance-vision-read-only-authority-v0-2.json"
)
PREREGISTERED_MAIN_SHA = "a0e216a41feaca61433bae9ca93c870a5baea9cc"
PRIOR_FAILED_RUN_ID = 35297163219


def _load_authority(path: Path) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("schema") != "qookey-bitget-macd-zec-binance-vision-read-only-authority-v0.2":
        raise RuntimeError("unsupported Binance Vision ZEC authority schema")
    if receipt.get("status") != "AUTHORIZED_PUBLIC_READ_ONLY_ONE_SHOT":
        raise RuntimeError("Binance Vision ZEC authority is not active")
    if receipt.get("authorized_source_main_sha") != PREREGISTERED_MAIN_SHA:
        raise RuntimeError("authority is not bound to the preregistered main")
    prior = receipt.get("prior_attempt") or {}
    if (
        prior.get("workflow_run_id") != PRIOR_FAILED_RUN_ID
        or prior.get("authority_consumed") is not True
        or prior.get("zec_history_partition_reads_performed") is not False
    ):
        raise RuntimeError("prior fail-closed attempt lineage mismatch")
    scope = receipt.get("authorized_scope") or {}
    expected = {
        "provider": "binance_usdm",
        "delivery": "binance_vision_public_monthly",
        "symbol": "ZECUSDT",
        "interval": "15m",
        "source_month_start": "2022-08",
        "source_month_end": "2026-07",
        "monthly_archive_count": 48,
        "checksum_reads_authorized": True,
        "archive_reads_authorized": True,
        "r2_access_authorized": False,
        "provider_fallback_authorized": False,
        "raw_candle_persistence_authorized": False,
    }
    for key, value in expected.items():
        if scope.get(key) != value:
            raise RuntimeError(f"Binance Vision ZEC authority scope mismatch: {key}")
    execution = receipt.get("execution") or {}
    if execution.get("one_shot") is not True or execution.get("max_runs") != 1:
        raise RuntimeError("Binance Vision ZEC authority must be one-shot")
    boundary = receipt.get("safety_boundary") or {}
    if not boundary or any(value is not False for value in boundary.values()):
        raise RuntimeError("Binance Vision ZEC safety boundary changed")
    return receipt


def _download(
    url: str,
    *,
    timeout_seconds: float = 45.0,
    retries: int = 4,
) -> tuple[bytes, int]:
    attempts = 0
    last_error: Exception | None = None
    for attempt in range(retries):
        attempts += 1
        try:
            request = Request(
                url,
                headers={"User-Agent": "qookey-bitget-zec-readonly/0.2"},
            )
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
                return response.read(), attempts
        except HTTPError as exc:
            last_error = exc
            if exc.code not in {408, 425, 429, 500, 502, 503, 504}:
                break
        except (URLError, TimeoutError) as exc:
            last_error = exc
        if attempt + 1 < retries:
            time.sleep(float(attempt + 1))
    raise RuntimeError(f"public Binance Vision read failed for {url}: {last_error}") from last_error


def _utc_ms(value: str) -> int:
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)


def _confirmation_source(candles, plan: BitgetMacdValidationPlan):
    _development, confirmation = build_preregistered_windows(candles, plan=plan)
    return tuple(
        candle
        for candle in candles
        if confirmation.start_time_ms <= candle.time_ms < confirmation.end_time_ms
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    authority = _load_authority(args.authority)
    archives = []
    provider_requests = 0
    for key in zec_monthly_archive_keys():
        archive_bytes, attempts = _download(key.url)
        provider_requests += attempts
        checksum_bytes, attempts = _download(key.checksum_url)
        provider_requests += attempts
        archives.append(
            ingest_kline_archive(
                key,
                archive_bytes=archive_bytes,
                checksum_payload=checksum_bytes,
            )
        )

    candles, archive_receipts = combine_verified_zec_archives(archives)
    if candles[0].time_ms != _utc_ms("2022-08-01T00:00:00Z"):
        raise RuntimeError("ZEC public history does not begin at frozen source start")
    if candles[-1].time_ms != _utc_ms("2026-08-01T00:00:00Z") - 15 * 60 * 1000:
        raise RuntimeError("ZEC public history does not end at frozen source end")

    plan = BitgetMacdValidationPlan()
    configs = default_bitget_macd_candidate_grid()
    if len(configs) != 2304:
        raise RuntimeError("candidate grid drifted from preregistration")

    baseline = BitgetMacdResearchConfig()
    baseline_full = run_bitget_macd_long_30m_research(
        candles_15m=candles,
        config=baseline,
        initial_equity_usd=10_000.0,
    )
    confirmation_candles = _confirmation_source(candles, plan)
    baseline_confirmation = []
    for slippage in plan.confirmation_slippage_stress_bps_per_side:
        stressed = replace(baseline, slippage_bps_per_side=slippage)
        baseline_confirmation.append(
            {
                "slippage_bps_per_side": slippage,
                "result": result_summary(
                    run_bitget_macd_long_30m_research(
                        candles_15m=confirmation_candles,
                        config=stressed,
                        initial_equity_usd=10_000.0,
                    )
                ),
            }
        )

    validation = run_preregistered_validation(
        candles_15m=candles,
        configs=configs,
        plan=plan,
        initial_equity_usd=10_000.0,
    )
    if validation.candidate_count != 2304:
        raise RuntimeError("preregistered candidate count mismatch")
    if len(validation.selected_development_candidates) != 24:
        raise RuntimeError("preregistered Top 24 mismatch")
    if validation.confirmation_used_for_selection:
        raise RuntimeError("confirmation leaked into parameter selection")
    if validation.formal_project_holdout_accessed:
        raise RuntimeError("formal project holdout was accessed")

    report = {
        "schema": "qookey-bitget-macd-zec-binance-vision-read-only-result-v0.2",
        "status": "PASS",
        "stage": "BITGET_MACD_ZEC_PUBLIC_BINANCE_VISION_PREREGISTERED_VALIDATION_COMPLETE",
        "observed_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source": {
            "provider": "binance_usdm",
            "delivery": "binance_vision_public_monthly",
            "symbol": "ZECUSDT",
            "interval": "15m",
            "source_month_start": "2022-08",
            "source_month_end": "2026-07",
            "archive_count": len(archive_receipts),
            "row_count": len(candles),
            "first_time_ms": candles[0].time_ms,
            "last_time_ms": candles[-1].time_ms,
            "archives": list(archive_receipts),
            "formal_replacement_holdout_accessed": False,
        },
        "preregistration": {
            "source_main_sha": PREREGISTERED_MAIN_SHA,
            "plan_sha256": plan_sha256(plan),
            "candidate_grid_count": len(configs),
            "development_fraction": plan.development_fraction,
            "development_folds": plan.development_folds,
            "top_k": plan.top_k,
            "confirmation_slippage_stress_bps_per_side": list(
                plan.confirmation_slippage_stress_bps_per_side
            ),
            "confirmation_can_change_parameters": False,
        },
        "user_baseline": {
            "config": asdict(baseline),
            "full_period": result_summary(baseline_full),
            "confirmation_stress": baseline_confirmation,
        },
        "validation": validation_summary(validation),
        "execution": {
            "authority_schema": authority["schema"],
            "one_shot": True,
            "provider_requests_performed": provider_requests,
            "r2_access_performed": False,
            "r2_writes_performed": False,
            "raw_candles_persisted": False,
            "training_performed": False,
        },
        "authority": {
            "formal_backtest_admission_authorized": False,
            "strategy_parameter_change_authorized": False,
            "source_switch_authorized": False,
            "holdout_access_authorized": False,
            "model_promotion_authorized": False,
            "formal_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "archives": len(archive_receipts),
                "rows": len(candles),
                "provider_requests": provider_requests,
                "candidate_count": validation.candidate_count,
                "selected": len(validation.selected_development_candidates),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
