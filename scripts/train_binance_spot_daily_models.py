from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pyarrow.parquet as pq

from crypto_autopilot.online_training import train_daily_direction_models
from crypto_autopilot.ephemeral_storage import require_ephemeral_output
from crypto_autopilot.weekly_model_review import build_weekly_model_review


def main() -> int:
    parser = argparse.ArgumentParser(description="Train deterministic research models from Binance Spot 1D Parquet")
    parser.add_argument("--config", default="config/binance_spot_r2_automated_training_v0_3.json")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--model-output", required=True)
    parser.add_argument("--metrics-output", required=True)
    parser.add_argument("--review-output")
    args = parser.parse_args()
    model_output = require_ephemeral_output(args.model_output)
    metrics_output = require_ephemeral_output(args.metrics_output)
    review_output = (
        require_ephemeral_output(args.review_output) if args.review_output else None
    )

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    allowed_statuses = {
        "R2_FIRST_AUTOMATED_TRAINING_AUTHORIZED_ON_MAIN_MERGE",
        "R2_ONLY_WEEKLY_MODEL_REVIEW_AUTHORIZED_ON_MAIN_MERGE",
    }
    if config.get("status") not in allowed_statuses:
        raise RuntimeError("automated training authority is not active")
    authority = config.get("authority") or {}
    if authority.get("automated_research_model_training_authorized") is not True:
        raise RuntimeError("automated research training is not authorized")
    for key in ("automatic_trade_plan_authorized", "real_money_order_authorized", "live_trading_authorized"):
        if authority.get(key) is not False:
            raise RuntimeError(f"unsafe V0.3 authority boundary: {key}")

    dataset_path = Path(args.dataset)
    payload = dataset_path.read_bytes()
    data_sha256 = hashlib.sha256(payload).hexdigest()
    columns = [
        "asset_class",
        "symbol",
        "audit_ok",
        "open_time_ms",
        "close",
        "quote_volume",
    ]
    rows = pq.read_table(dataset_path, columns=columns).to_pylist()
    stop = datetime.fromisoformat(config["schedule"]["provider_read_stop_utc"].replace("Z", "+00:00"))
    generated = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    model, metrics = train_daily_direction_models(
        rows,
        training_config=config["training"],
        data_sha256=data_sha256,
        end_exclusive_ms=int(stop.timestamp() * 1000),
        generated_at_utc=generated,
    )
    model_payload = (json.dumps(model, ensure_ascii=False, indent=2) + "\n").encode()
    metrics["model_file_sha256"] = hashlib.sha256(model_payload).hexdigest()
    metrics_payload = (json.dumps(metrics, ensure_ascii=False, indent=2) + "\n").encode()
    for path_value, payload in (
        (model_output, model_payload),
        (metrics_output, metrics_payload),
    ):
        path_value.parent.mkdir(parents=True, exist_ok=True)
        path_value.write_bytes(payload)
    if "weekly_review" in config:
        if review_output is None:
            raise RuntimeError("weekly review output is required by V0.4")
        review = build_weekly_model_review(
            rows,
            training_config=config["training"],
            review_config=config["weekly_review"],
            data_sha256=data_sha256,
            end_exclusive_ms=int(stop.timestamp() * 1000),
            generated_at_utc=generated,
        )
        review_output.parent.mkdir(parents=True, exist_ok=True)
        review_output.write_text(
            json.dumps(review, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if review["status"] != "PASS":
            return 2
    print(json.dumps({"status": model["status"], "data_sha256": data_sha256, "classes": list(model["models"])}, ensure_ascii=False))
    return 0 if model["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
