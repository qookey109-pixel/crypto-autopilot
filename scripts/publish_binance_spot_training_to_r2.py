from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from crypto_autopilot.online_r2_training import build_online_objects, publish_online_objects
from crypto_autopilot.storage.r2 import R2Store


AUTHORITY_PATH = Path(
    "research/receipts/2026-08-22-binance-spot-r2-automated-training-v0-3-authority.json"
)


def required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"required GitHub Actions R2 secret is missing: {name}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish Binance Spot dataset and research model to Cloudflare R2")
    parser.add_argument("--config", default="config/binance_spot_r2_automated_training_v0_3.json")
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--dataset-receipt", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--metrics", required=True)
    parser.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID") or "local")
    parser.add_argument("--output", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    authority = json.loads(AUTHORITY_PATH.read_text(encoding="utf-8"))
    if config.get("status") != "R2_FIRST_AUTOMATED_TRAINING_AUTHORIZED_ON_MAIN_MERGE":
        raise RuntimeError("V0.3 R2-first configuration is not authorized")
    if authority.get("status") != "AUTHORIZED_ON_MAIN_MERGE":
        raise RuntimeError("V0.3 R2-first authority receipt is not active")
    boundary = config.get("authority") or {}
    for key in (
        "production_r2_client_construction_authorized",
        "production_r2_reads_authorized",
        "production_r2_writes_authorized_for_exact_namespaces",
        "automated_research_model_training_authorized",
    ):
        if boundary.get(key) is not True:
            raise RuntimeError(f"V0.3 required online authority missing: {key}")
    for key in (
        "source_switch_authorized",
        "holdout_access_authorized",
        "automatic_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if boundary.get(key) is not False:
            raise RuntimeError(f"unsafe V0.3 authority boundary: {key}")

    payloads = {
        name: Path(path).read_bytes()
        for name, path in (
            ("catalog", args.catalog),
            ("dataset", args.dataset),
            ("dataset_receipt", args.dataset_receipt),
            ("model", args.model),
            ("metrics", args.metrics),
        )
    }
    dataset_receipt = json.loads(payloads["dataset_receipt"])
    model = json.loads(payloads["model"])
    metrics = json.loads(payloads["metrics"])
    if dataset_receipt.get("status") != "PASS" or dataset_receipt.get("provider") != "binance_spot":
        raise RuntimeError("dataset receipt is not a Binance Spot PASS")
    if model.get("status") != "PASS" or model.get("mode") != "RESEARCH_TRAINING_ONLY":
        raise RuntimeError("model is not a research-only PASS")
    actual_data_sha = hashlib.sha256(payloads["dataset"]).hexdigest()
    if model.get("data_sha256") != actual_data_sha:
        raise RuntimeError("model dataset SHA does not match the publish payload")
    actual_model_sha = hashlib.sha256(payloads["model"]).hexdigest()
    if (
        metrics.get("status") != "PASS"
        or metrics.get("provider") != "binance_spot"
        or metrics.get("data_sha256") != actual_data_sha
        or metrics.get("model_file_sha256") != actual_model_sha
    ):
        raise RuntimeError("training metrics lineage does not match the publish payloads")

    generated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    objects = build_online_objects(
        config=config,
        run_id=args.run_id,
        dataset=payloads["dataset"],
        catalog=payloads["catalog"],
        dataset_receipt=payloads["dataset_receipt"],
        model=payloads["model"],
        metrics=payloads["metrics"],
        generated_at_utc=generated_at,
    )
    if args.dry_run:
        result = {
            "status": "PREPARED",
            "stage": "BINANCE_SPOT_R2_AUTOMATED_TRAINING_DRY_RUN_V0_3",
            "planned_write_bytes": sum(len(item.payload) for item in objects),
            "objects": [
                {
                    "role": item.role,
                    "key": item.key,
                    "bytes": len(item.payload),
                    "sha256": hashlib.sha256(item.payload).hexdigest(),
                    "immutable": item.immutable,
                }
                for item in objects
            ],
            "latest_pointer_written_last": objects[-1].role == "latest_pointer",
            "r2_client_constructed": False,
            "r2_writes_performed": False,
        }
    else:
        store = R2Store(
            account_id=required("CLOUDFLARE_ACCOUNT_ID"),
            bucket=required("R2_BUCKET_NAME"),
            access_key_id=required("R2_ACCESS_KEY_ID"),
            secret_access_key=required("R2_SECRET_ACCESS_KEY"),
        )
        result = publish_online_objects(
            store=store,
            objects=objects,
            hard_stop_bytes=int(config["storage"]["free_only_hard_stop_bytes"]),
        )
    result.update(
        {
            "generated_at_utc": generated_at,
            "run_id": args.run_id,
            "provider": "binance_spot",
            "dataset_sha256": actual_data_sha,
            "source_switch_authorized": False,
            "automatic_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        }
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "stage": result["stage"], "objects": len(result.get("objects", []))}))
    return 0 if result["status"] in {"PASS", "PREPARED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
