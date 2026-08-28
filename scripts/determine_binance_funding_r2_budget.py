from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from crypto_autopilot.binance_funding import (
    BinanceVisionFundingArchiveKey,
    funding_to_parquet,
    ingest_funding_archive,
)
from crypto_autopilot.binance_funding_budget import (
    project_funding_budget,
    validate_budget_config,
)
from crypto_autopilot.storage.budget import (
    R2Guardrails,
    R2Pricing,
    R2ProjectedUsage,
    evaluate_r2_budget,
)


DEFAULT_CONFIG = "config/binance_funding_r2_budget_v0_1.json"
TRADE_BUDGET_AUTHORITY = "research/receipts/2026-08-18-binance-observed-r2-budget.json"


def load_json(path: str) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def fetch_bytes(url: str, *, attempts: int = 3, timeout_seconds: float = 30.0) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        request = Request(
            url,
            headers={"Accept": "*/*", "User-Agent": "qookey-crypto-autopilot-funding-budget/0.1"},
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - frozen HTTPS host
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last_error}") from last_error


def evaluate(usage: R2ProjectedUsage, policy: dict[str, object]) -> dict[str, object]:
    pricing = policy["pricing_snapshot"]
    guardrails = policy["project_guardrails"]
    return evaluate_r2_budget(
        usage,
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--output", default="artifacts/binance-funding-r2-budget.json")
    args = parser.parse_args()

    config = load_json(args.config)
    validate_budget_config(config)
    coverage = load_json(str(config["coverage_authority"]))
    source_proof = load_json(str(config["source_proof_authority"]))
    r2_policy = load_json(str(config["r2_policy"]))
    trade_budget = load_json(TRADE_BUDGET_AUTHORITY)

    if source_proof.get("status") != "PASS" or source_proof.get("stage") != "BINANCE_FUNDING_SOURCE_PROOF_PASS":
        raise RuntimeError("Funding source proof authority must PASS")
    if trade_budget.get("status") != "PASS" or trade_budget.get("stage") != "BINANCE_OBSERVED_R2_BUDGET_GATE_PASS":
        raise RuntimeError("Observed Binance Trade R2 budget authority must PASS")

    proof_archives = {row["symbol"]: row for row in source_proof["archives"]}
    symbols = tuple(str(item) for item in config["calibration_symbols"])
    period = str(config["calibration_period"])
    if symbols != ("BTCUSDT", "ETHUSDT", "SOLUSDT") or period != "2024-01":
        raise RuntimeError("Funding budget calibration scope changed")

    calibrations: list[dict[str, object]] = []
    for symbol in symbols:
        authority_row = proof_archives.get(symbol)
        if authority_row is None or authority_row.get("period") != period:
            raise RuntimeError(f"Funding source proof missing calibration archive for {symbol}")
        key = BinanceVisionFundingArchiveKey(symbol, period)
        checksum = fetch_bytes(key.checksum_url)
        archive = fetch_bytes(key.url)
        ingested = ingest_funding_archive(
            key,
            archive_bytes=archive,
            checksum_payload=checksum,
        )
        if ingested.receipt.archive_sha256 != authority_row["archive_sha256"]:
            raise RuntimeError(f"Funding calibration archive SHA changed for {symbol}")
        if ingested.receipt.row_count != int(authority_row["row_count"]):
            raise RuntimeError(f"Funding calibration row count changed for {symbol}")
        parquet = funding_to_parquet(ingested.observations)
        bytes_per_row = len(parquet.payload) / parquet.rows
        calibrations.append(
            {
                "symbol": symbol,
                "period": period,
                "rows": parquet.rows,
                "parquet_bytes": len(parquet.payload),
                "parquet_sha256": parquet.sha256,
                "bytes_per_row": bytes_per_row,
                "source_archive_sha256": ingested.receipt.archive_sha256,
            }
        )

    max_bytes_per_row = max(float(row["bytes_per_row"]) for row in calibrations)
    trade_storage = trade_budget["storage_projection"]
    trade_ops = trade_budget["operation_projection"]
    guardrails = r2_policy["project_guardrails"]

    projection = project_funding_budget(
        coverage_authority=coverage,
        calibration_max_bytes_per_row=max_bytes_per_row,
        trade_three_x_storage_gb=float(trade_storage["three_x_capacity_stress_gb_month"]),
        trade_three_x_class_a_requests=int(trade_ops["three_x_class_a_requests"]),
        trade_three_x_class_b_requests=int(trade_ops["three_x_class_b_requests"]),
        storage_warn_gb=float(guardrails["storage_warn_gb_month"]),
        class_a_warn_requests=int(guardrails["class_a_warn_requests_per_month"]),
        class_b_warn_requests=int(guardrails["class_b_warn_requests_per_month"]),
        minimum_budget_interval_hours=int(config["minimum_funding_interval_hours_for_budget"]),
        retained_staging_multiplier=float(config["retained_staging_multiplier"]),
        capacity_stress_multiplier=float(config["capacity_stress_multiplier"]),
        operation_stress_multiplier=int(config["operation_stress_multiplier"]),
    )

    combined_planned = evaluate(
        R2ProjectedUsage(
            storage_gb_month=float(trade_storage["canonical_plus_retained_staging_gb_month"])
            + projection.canonical_plus_staging_gb,
            class_a_requests_per_month=int(trade_ops["planned_class_a_requests"])
            + projection.planned_class_a_requests,
            class_b_requests_per_month=int(trade_ops["planned_class_b_requests"])
            + projection.planned_class_b_requests,
        ),
        r2_policy,
    )
    combined_stress = evaluate(
        R2ProjectedUsage(
            storage_gb_month=projection.combined_trade_plus_funding_three_x_storage_gb,
            class_a_requests_per_month=projection.combined_trade_plus_funding_three_x_class_a_requests,
            class_b_requests_per_month=projection.combined_trade_plus_funding_three_x_class_b_requests,
        ),
        r2_policy,
    )

    if combined_planned["status"] == "BLOCK" or combined_stress["status"] == "BLOCK":
        determination = "BLOCK"
    elif projection.material_budget_change or combined_planned["status"] == "WARN" or combined_stress["status"] == "WARN":
        determination = "MATERIAL_CHANGE_REVIEW_REQUIRED"
    else:
        determination = "NO_MATERIAL_BUDGET_CHANGE"

    payload = {
        "schema": "binance-funding-r2-budget-determination-v0.1",
        "execution_status": "PASS",
        "determination": determination,
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "dataset": "fundingRate",
        "coverage_authority": config["coverage_authority"],
        "source_proof_authority": config["source_proof_authority"],
        "trade_budget_authority": TRADE_BUDGET_AUTHORITY,
        "r2_policy": config["r2_policy"],
        "calibration": {
            "policy": config["bytes_per_row_policy"],
            "symbols": list(symbols),
            "period": period,
            "measurements": calibrations,
            "max_bytes_per_row": max_bytes_per_row,
        },
        "row_projection": {
            "policy": config["row_projection_policy"],
            "minimum_funding_interval_hours": projection.minimum_budget_interval_hours,
            "available_symbol_months": projection.available_symbol_months,
            "available_calendar_days": projection.available_calendar_days,
            "projected_rows": projection.projected_rows,
            "annual_canonical_objects": projection.annual_canonical_objects,
        },
        "funding_projection": asdict(projection),
        "combined_trade_plus_funding": {
            "planned_gate": combined_planned,
            "three_x_stress_gate": combined_stress,
            "trade_three_x_storage_gb": float(trade_storage["three_x_capacity_stress_gb_month"]),
            "funding_three_x_storage_gb": projection.three_x_capacity_stress_gb,
            "combined_three_x_storage_gb": projection.combined_trade_plus_funding_three_x_storage_gb,
            "storage_warn_gb": float(guardrails["storage_warn_gb_month"]),
            "storage_headroom_to_warn_gb": float(guardrails["storage_warn_gb_month"])
            - projection.combined_trade_plus_funding_three_x_storage_gb,
        },
        "interpretation_boundary": {
            "one_hour_funding_assumed_for_budget_only": True,
            "claims_actual_one_hour_funding_cadence": False,
            "actual_source_intervals_preserved_by_materializer": True,
            "calibration_uses_real_proof_archives": True,
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
                "determination": determination,
                "max_bytes_per_row": max_bytes_per_row,
                "funding_canonical_gb": projection.canonical_gb,
                "combined_three_x_storage_gb": projection.combined_trade_plus_funding_three_x_storage_gb,
                "storage_headroom_to_warn_gb": payload["combined_trade_plus_funding"]["storage_headroom_to_warn_gb"],
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    return 0 if determination != "BLOCK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
