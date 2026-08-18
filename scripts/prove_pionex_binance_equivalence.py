from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from crypto_autopilot.binance_historical import pionex_perp_to_binance_usdm
from crypto_autopilot.exchanges.binance_usdm_public import BinanceUSDMPublicClient
from crypto_autopilot.provider_equivalence import (
    ProviderEquivalencePolicy,
    aggregate_provider_equivalence,
    compare_provider_pair,
)
from crypto_autopilot.storage.parquet import parquet_to_candles
from crypto_autopilot.storage.r2 import R2Store


M1A_AUTHORITY = Path("research/receipts/2026-08-17-m1a-pionex.json")
M1B_AUTHORITY = Path("research/receipts/2026-08-18-m1b-r2.json")
POLICY_PATH = Path("config/provider_equivalence_v0_1.json")
BINANCE_INTERVAL = {"15M": "15m", "60M": "1h", "4H": "4h"}


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def canonical_candle_sha(candles) -> str:
    rows = [
        {
            "time_ms": candle.time_ms,
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
        }
        for candle in candles
    ]
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_frozen_policy(policy_json: dict) -> ProviderEquivalencePolicy:
    if policy_json.get("status") != "PROTOCOL_FROZEN_BEFORE_LIVE_EVIDENCE":
        raise RuntimeError("equivalence protocol must be frozen before live evidence")
    if policy_json.get("providers", {}).get("left") != "pionex":
        raise RuntimeError("left provider must remain Pionex")
    if policy_json.get("providers", {}).get("right") != "binance_usdm":
        raise RuntimeError("right provider must remain Binance USD-M")
    if policy_json.get("strategy_boundary", {}).get("source_switch_authorized_by_v0_1") is not False:
        raise RuntimeError("V0.1 protocol must not authorize a source switch")

    policy = ProviderEquivalencePolicy()
    frozen = policy_json["price_metrics_bps"]
    behavior = policy_json["behavior_metrics"]
    expected = {
        "median_ohlc_bps_pass": float(frozen["median_ohlc"]["pass_max"]),
        "median_ohlc_bps_review": float(frozen["median_ohlc"]["review_max"]),
        "p95_open_close_bps_pass": float(frozen["p95_open_close"]["pass_max"]),
        "p95_open_close_bps_review": float(frozen["p95_open_close"]["review_max"]),
        "p95_high_low_bps_pass": float(frozen["p95_high_low"]["pass_max"]),
        "p95_high_low_bps_review": float(frozen["p95_high_low"]["review_max"]),
        "return_direction_agreement_pass": float(
            behavior["close_to_close_direction_agreement"]["pass_min"]
        ),
        "return_direction_agreement_review": float(
            behavior["close_to_close_direction_agreement"]["review_min"]
        ),
        "setup_60m_agreement_pass": float(behavior["setup_60m_agreement"]["pass_min"]),
        "setup_60m_agreement_review": float(behavior["setup_60m_agreement"]["review_min"]),
        "min_ready_setup_bars_60m": int(behavior["setup_60m_agreement"]["minimum_ready_bars"]),
        "min_rows_15m": int(policy_json["minimum_rows"]["15M"]),
        "min_rows_60m": int(policy_json["minimum_rows"]["60M"]),
        "min_rows_4h": int(policy_json["minimum_rows"]["4H"]),
        "max_review_fraction_for_aggregate_review": 0.20,
    }
    for field, value in expected.items():
        if getattr(policy, field) != value:
            raise RuntimeError(
                f"code/config equivalence-policy mismatch for {field}: "
                f"code={getattr(policy, field)} config={value}"
            )
    return policy


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/pionex-binance-equivalence.json")
    args = parser.parse_args()

    m1a = load_json(M1A_AUTHORITY)
    m1b = load_json(M1B_AUTHORITY)
    policy_json = load_json(POLICY_PATH)
    policy = validate_frozen_policy(policy_json)

    if m1a.get("stage") != "M1A_COMPLETE" or m1a.get("audit", {}).get("pass") is not True:
        raise RuntimeError("M1A Pionex authority must be COMPLETE and audit PASS")
    if m1b.get("stage") != "M1B_COMPLETE" or m1b.get("status") != "PASS":
        raise RuntimeError("M1B R2 authority must be PASS")
    if m1b.get("dataset", {}).get("object_count") != 45:
        raise RuntimeError("M1B authority must contain exactly 45 overlap objects")

    start_utc = m1a["sample"]["requested_start_utc"]
    end_utc = m1a["sample"]["requested_end_utc"]
    if policy_json["overlap_window"]["start_utc"] != start_utc:
        raise RuntimeError("policy/M1A overlap start mismatch")
    if policy_json["overlap_window"]["end_utc"] != end_utc:
        raise RuntimeError("policy/M1A overlap end mismatch")
    start_ms = int(datetime.fromisoformat(start_utc.replace("Z", "+00:00")).timestamp() * 1000)
    end_ms = int(datetime.fromisoformat(end_utc.replace("Z", "+00:00")).timestamp() * 1000)

    store = R2Store(
        account_id=os.environ["CLOUDFLARE_ACCOUNT_ID"],
        bucket=os.environ["R2_BUCKET_NAME"],
        access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    )
    manifest_meta = m1b["manifest"]
    manifest_bytes = store.get_bytes_verified(
        str(manifest_meta["key"]), expected_sha256=str(manifest_meta["r2_sha256"])
    )
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    if manifest.get("dataset") != "M1A_PIONEX_BOUNDED" or manifest.get("object_count") != 45:
        raise RuntimeError("unexpected M1B manifest identity")
    if int(manifest.get("requested_start_ms")) != start_ms or int(manifest.get("requested_end_ms")) != end_ms:
        raise RuntimeError("M1B manifest overlap window mismatch")

    object_index = {
        (str(item["symbol"]), str(item["interval"])): item
        for item in manifest.get("objects", [])
    }
    if len(object_index) != 45:
        raise RuntimeError("M1B manifest does not contain 45 unique symbol/interval objects")

    client = BinanceUSDMPublicClient(timeout_seconds=30.0)
    results = []
    evidence_pairs = []
    for selected in m1a.get("selected_universe", []):
        pionex_symbol = str(selected["symbol"])
        binance_symbol = pionex_perp_to_binance_usdm(pionex_symbol)
        for interval in ("15M", "60M", "4H"):
            source = object_index[(pionex_symbol, interval)]
            pionex_payload = store.get_bytes_verified(
                str(source["key"]), expected_sha256=str(source["sha256"])
            )
            pionex_candles = tuple(parquet_to_candles(pionex_payload))
            if len(pionex_candles) != int(source["rows"]):
                raise RuntimeError(f"Pionex R2 row mismatch: {pionex_symbol} {interval}")

            binance_candles = tuple(
                client.get_klines(
                    binance_symbol,
                    BINANCE_INTERVAL[interval],
                    start_time_ms=start_ms,
                    end_time_ms=end_ms,
                    limit=1500,
                )
            )
            if not binance_candles:
                raise RuntimeError(f"Binance returned no overlap candles: {binance_symbol} {interval}")

            result = compare_provider_pair(
                pionex_symbol=pionex_symbol,
                binance_symbol=binance_symbol,
                interval=interval,
                pionex_candles=pionex_candles,
                binance_candles=binance_candles,
                policy=policy,
            )
            results.append(result)
            evidence_pairs.append(
                {
                    "pionex_symbol": pionex_symbol,
                    "binance_symbol": binance_symbol,
                    "interval": interval,
                    "pionex_r2_key": source["key"],
                    "pionex_r2_sha256": source["sha256"],
                    "pionex_candle_sha256": canonical_candle_sha(pionex_candles),
                    "binance_endpoint": "/fapi/v1/klines",
                    "binance_interval": BINANCE_INTERVAL[interval],
                    "binance_candle_sha256": canonical_candle_sha(binance_candles),
                    "requested_start_ms": start_ms,
                    "requested_end_ms": end_ms,
                    "result": asdict(result),
                }
            )

    aggregate = aggregate_provider_equivalence(results, expected_pair_count=45, policy=policy)
    status_counts = {
        "PASS": aggregate.pass_count,
        "REVIEW": aggregate.review_count,
        "FAIL": aggregate.fail_count,
    }
    payload = {
        "schema": "pionex-binance-equivalence-evidence-v0.1",
        "execution_status": "PASS",
        "gate_status": aggregate.status,
        "source_switch_authorized": aggregate.source_switch_authorized,
        "full_strategy_signal_equivalence_status": aggregate.full_strategy_signal_equivalence_status,
        "left_provider": "pionex",
        "right_provider": "binance_usdm",
        "execution_target": "pionex",
        "policy": str(POLICY_PATH),
        "policy_status": policy_json["status"],
        "pionex_authority": str(M1A_AUTHORITY),
        "pionex_r2_authority": str(M1B_AUTHORITY),
        "overlap_start_ms": start_ms,
        "overlap_end_ms": end_ms,
        "pair_count": len(results),
        "status_counts": status_counts,
        "aggregate": {
            "expected_pair_count": aggregate.expected_pair_count,
            "evaluated_pair_count": aggregate.evaluated_pair_count,
            "pass_count": aggregate.pass_count,
            "review_count": aggregate.review_count,
            "fail_count": aggregate.fail_count,
            "status": aggregate.status,
            "source_switch_authorized": aggregate.source_switch_authorized,
            "full_strategy_signal_equivalence_status": aggregate.full_strategy_signal_equivalence_status,
        },
        "pairs": evidence_pairs,
        "volume_equivalence_evaluated": False,
        "private_api_used": False,
        "live_trading_authorized": False,
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "github_sha": os.getenv("GITHUB_SHA"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "authority_boundary": {
            "thresholds_changed_after_evidence": False,
            "binance_relabelled_as_pionex_native": False,
            "provider_splicing_used": False,
            "full_strategy_signal_equivalence_proven": False,
            "source_switch_authorized": False,
            "automatic_trade_plans_authorized": False,
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
                "gate_status": aggregate.status,
                "pass": aggregate.pass_count,
                "review": aggregate.review_count,
                "fail": aggregate.fail_count,
                "source_switch_authorized": aggregate.source_switch_authorized,
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    # REVIEW or FAIL are valid evidence outcomes. Only evidence-production errors
    # raise and fail the workflow.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
