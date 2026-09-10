#!/usr/bin/env python3
"""One cloud-only, pre-holdout capacity pilot under exact V0.2 authority."""
import argparse
import json
import os
import re
from pathlib import Path

from crypto_autopilot.pionex_bounded_pilot import (
    PilotRejected, collect, digest, encoded, now_ms, require_window,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/pionex_historical_research_execution_v0_2.json"
RECEIPT = ROOT / "research/receipts/2026-09-10-pionex-bounded-pilot-v0-2-authority.json"
CONFIG_SHA256 = "a66fdf7def02023590163091fbdd1eceabe5d96a774ffa0207e7b7a7f506f932"


def load_authority():
    payload = CONFIG.read_bytes()
    config, receipt = json.loads(payload), json.loads(RECEIPT.read_bytes())
    if (receipt["config_sha256"] != digest(payload) or digest(payload) != CONFIG_SHA256
            or receipt["status"] != "AUTHORIZED_AFTER_PROTECTED_MAIN_MERGE"):
        raise PilotRejected("V0.2 authority mismatch")
    if receipt["prepared_pool_config_sha256"] != digest((ROOT / "config/pionex_historical_research_pool_v0_1.json").read_bytes()):
        raise PilotRejected("prepared pool changed")
    if config["symbol"] != "BTC_USDT_PERP" or config["intervals"] != ["15M", "60M", "4H"]:
        raise PilotRejected("pilot scope changed")
    if config["authority"] != {
        "public_pionex_reads": True, "r2_headroom_and_pilot_publication": True,
        "automatic_schedule": False, "full_history_complete": False,
        "full_150_market_materialization": False, "holdout_access": False,
        "training": False, "backtest": False, "source_switch": False,
        "model_promotion": False, "trade_plan": False, "live_trading": False,
    }:
        raise PilotRejected("pilot authority widened")
    if (config["namespace"] != "market-data/pionex/historical-research-pool-v0.2/pilot"
            or config["free_only_hard_stop_bytes"] != 8_000_000_000
            or config["maximum_requests"] != 10
            or config["maximum_provider_lookback_bars"] != 9000):
        raise PilotRejected("pilot resource boundary changed")
    return config


def execute(config, store, client, run_id, progress, *, clock=now_ms):
    from crypto_autopilot.storage.parquet import candles_to_parquet, parquet_to_candles
    from crypto_autopilot.training.online_r2 import current_bucket_bytes

    require_window(config, clock)
    if not re.fullmatch(r"github-[0-9]+-1", run_id):
        raise PilotRejected("only a fresh main dispatch is allowed")
    prefix = config["namespace"] + "/run=" + run_id
    latest_key = config["namespace"] + "/latest.json"

    def headroom(reservation):
        require_window(config, clock)
        if current_bucket_bytes(store) + reservation > config["free_only_hard_stop_bytes"]:
            raise PilotRejected("FREE-ONLY headroom exceeded")

    headroom(config["maximum_planned_run_bytes"])
    old = store.get_bytes_if_exists(latest_key)
    if old is not None:
        latest = json.loads(old)
        receipt_key = latest.get("receipt_key", "")
        if not re.fullmatch(re.escape(config["namespace"]) + r"/run=github-[0-9]+-1/receipt.json", receipt_key):
            raise PilotRejected("existing pointer outside pilot namespace")
        prior = json.loads(store.get_bytes_verified(receipt_key, expected_sha256=latest["receipt_sha256"]))
        if (prior.get("status") != "PASS" or prior.get("config_sha256") != CONFIG_SHA256
                or prior.get("coverage_claim") != config["coverage_claim"]):
            raise PilotRejected("existing pointer receipt mismatch")
        return {"status": "ALREADY_COMPLETE", "coverage_claim": config["coverage_claim"]}

    series = collect(config, client, clock, progress)
    objects, details = [], []
    for interval, candles in series.items():
        parquet = candles_to_parquet(candles)
        if parquet_to_candles(parquet.payload) != list(candles):
            raise PilotRejected("Parquet roundtrip mismatch")
        key = prefix + "/" + interval + ".parquet"
        objects.append((key, parquet.payload, "application/vnd.apache.parquet"))
        details.append({"interval": interval, "rows": len(candles), "first_time_ms": candles[0].time_ms,
                        "last_time_ms": candles[-1].time_ms, "bytes": len(parquet.payload),
                        "sha256": digest(parquet.payload), "key": key})
    receipt = {"schema": "pionex-capacity-pilot-v0.2", "status": "PASS", "run_id": run_id,
               "provider": config["provider"], "symbol": config["symbol"],
               "config_sha256": CONFIG_SHA256, "coverage_claim": config["coverage_claim"],
               "start_utc": config["start_utc"], "end_exclusive_utc": config["end_exclusive_utc"],
               "intervals": details, "holdout_accessed": False, "live_trading_authorized": False}
    receipt_key = prefix + "/receipt.json"
    receipt_bytes = encoded(receipt)
    objects.append((receipt_key, receipt_bytes, "application/json"))
    latest = encoded({"schema": "pionex-capacity-pilot-latest-v0.2", "receipt_key": receipt_key,
                      "receipt_sha256": digest(receipt_bytes)})
    objects.append((latest_key, latest, "application/json"))
    planned = sum(len(data) for _, data, _ in objects)
    if planned > config["maximum_planned_run_bytes"]:
        raise PilotRejected("output reservation exceeded")
    # Preflight every target before the first write. A prior partial execution
    # must not silently become a new successful run.
    for key, _, _ in objects:
        if store.get_bytes_if_exists(key) is not None:
            raise PilotRejected("existing partial target needs review")
    for key, data, content_type in objects:
        headroom(planned)
        progress["r2_writes_performed"] = "UNKNOWN_WRITE_ATTEMPTED"
        store.put_bytes(key, data, content_type=content_type,
                        metadata={"provider": config["provider"], "version": "v0.2"})
        progress["r2_writes_performed"] = True
        if store.get_bytes_verified(key, expected_sha256=digest(data)) != data:
            raise PilotRejected("write readback mismatch")
        planned -= len(data)
    return {**receipt, "r2_latest_pointer_written_last": True, "training_authorized": False,
            "source_switch_authorized": False, "binance_relabel_as_pionex_authorized": False}


def main():
    from crypto_autopilot.exchanges.pionex_public import PionexPublicClient
    from crypto_autopilot.storage.ephemeral import require_ephemeral_output
    from crypto_autopilot.storage.r2 import R2Store

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    progress = {"requests": 0, "r2_writes_performed": False, "holdout_accessed": False}
    try:
        if any(os.environ.get(key) != value for key, value in {
            "GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_REF": "refs/heads/main", "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_REPOSITORY": "qookey109-pixel/crypto-autopilot",
        }.items()):
            raise PilotRejected("fresh GitHub main manual execution required")
        config = load_authority()
        require_window(config, now_ms)
        store = R2Store(account_id=os.environ["CLOUDFLARE_ACCOUNT_ID"], bucket=os.environ["R2_BUCKET_NAME"],
                        access_key_id=os.environ["R2_ACCESS_KEY_ID"], secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"])
        result = execute(config, store, PionexPublicClient(requests_per_second=config["requests_per_second"]),
                         "github-" + os.environ["GITHUB_RUN_ID"] + "-1", progress)
    except Exception as exc:
        reason = str(exc) if isinstance(exc, PilotRejected) else "runtime failure: " + type(exc).__name__
        result = {"status": "FAIL", "reason": reason}
    report = {**result, **progress, "live_trading_authorized": False,
              "schema": "pionex-bounded-pilot-run-report-v0.2"}
    output = require_ephemeral_output(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(encoded(report))
    print(json.dumps(report, sort_keys=True))
    return 2 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
