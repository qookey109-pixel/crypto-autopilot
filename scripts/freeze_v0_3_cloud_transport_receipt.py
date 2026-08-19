from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

OFFICIAL_ENDPOINT = "https://fapi.binance.com/fapi/v1/exchangeInfo"

REQUIRED_FALSE_FIELDS = (
    "api_key_used",
    "increment_values_emitted",
    "raw_exchange_info_persisted",
    "r2_client_constructed",
    "r2_writes_performed",
    "holdout_candles_accessed",
    "holdout_evaluated",
    "source_switch_performed",
    "live_trading_performed",
)

FORBIDDEN_SERIALIZED_TOKENS = (
    "tickSize",
    "quoteStep",
    "apiSecret",
    "secretKey",
)


def validate_sanitized_pass(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("transport result must be a JSON object")

    required = {
        "status": "PASS",
        "transport": "cloudflare_container",
        "upstream_url": OFFICIAL_ENDPOINT,
        "upstream_status": 200,
        "json_ok": True,
        "symbols_array": True,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise ValueError(f"unexpected {key}: {payload.get(key)!r}")

    symbol_count = payload.get("symbol_count")
    if not isinstance(symbol_count, int) or isinstance(symbol_count, bool) or symbol_count <= 0:
        raise ValueError("symbol_count must be a positive integer")

    for key in REQUIRED_FALSE_FIELDS:
        if payload.get(key) is not False:
            raise ValueError(f"{key} must be false")

    serialized = json.dumps(payload, sort_keys=True)
    for token in FORBIDDEN_SERIALIZED_TOKENS:
        if token in serialized:
            raise ValueError(f"forbidden unsanitized token present: {token}")

    return payload


def build_receipt(
    *,
    payload: dict[str, Any],
    run_id: int,
    run_url: str,
    head_sha: str,
    observed_at: str,
) -> dict[str, Any]:
    validate_sanitized_pass(payload)
    return {
        "schema_version": "provider_equivalence_v0_3_cloud_transport_receipt_v0_1",
        "stage": "V0_3_CLOUDFLARE_CONTAINER_BINANCE_TRANSPORT_PASS",
        "observed_at": observed_at,
        "source_workflow": {
            "event": "workflow_dispatch",
            "run_id": run_id,
            "run_url": run_url,
            "head_sha": head_sha,
        },
        "transport_evidence": payload,
        "authority_boundary": {
            "transport_preflight_passed": True,
            "v0_1_equivalence_status": "FAIL",
            "v0_1_mutated": False,
            "v0_2_self_hosted_mac_transport_authority_mutated": False,
            "cloud_transport_authorized_for_metadata_capture": False,
            "metadata_capture_execution_authorized_by_this_receipt": False,
            "holdout_candle_access_authorized": False,
            "source_switch_authorized": False,
            "historical_universe_membership_authorized": False,
            "backtest_admission_authorized": False,
            "automatic_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
        "next_required_authority": "separate_versioned_cloud_transport_authority_transition",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--observed-at", required=True)
    args = parser.parse_args()

    payload = json.loads(args.result.read_text())
    receipt = build_receipt(
        payload=payload,
        run_id=args.run_id,
        run_url=args.run_url,
        head_sha=args.head_sha,
        observed_at=args.observed_at,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
