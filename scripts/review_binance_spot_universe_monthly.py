from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from crypto_autopilot.ephemeral_storage import require_ephemeral_output
from crypto_autopilot.monthly_universe_review import (
    build_monthly_universe_objects,
    build_monthly_universe_review,
)
from crypto_autopilot.online_r2_training import publish_online_objects
from crypto_autopilot.storage.r2 import R2Store


def required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"required GitHub Actions R2 secret is missing: {name}")
    return value


def _previous_review(store: R2Store, config: dict[str, object]) -> dict | None:
    latest_key = str(config["monthly_universe_review"]["latest_pointer_key"])
    latest_payload = store.get_bytes_if_exists(latest_key)
    if latest_payload is None:
        return None
    latest = json.loads(latest_payload)
    return json.loads(
        store.get_bytes_verified(
            str(latest["review_key"]),
            expected_sha256=str(latest["review_sha256"]),
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Review Binance Spot universe monthly and publish to R2")
    parser.add_argument("--config", default="config/binance_spot_r2_weekly_training_v0_4.json")
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID") or "local")
    parser.add_argument("--review-output", required=True)
    parser.add_argument("--receipt-output", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    review_output = require_ephemeral_output(args.review_output)
    receipt_output = require_ephemeral_output(args.receipt_output)

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    if config.get("status") != "R2_ONLY_WEEKLY_MODEL_REVIEW_AUTHORIZED_ON_MAIN_MERGE":
        raise RuntimeError("V0.4 monthly universe review authority is not active")
    boundary = config.get("authority") or {}
    if boundary.get("github_actions_monthly_universe_review_authorized") is not True:
        raise RuntimeError("monthly universe review is not authorized")
    for key in (
        "historical_universe_membership_authorized",
        "formal_backtest_admission_authorized",
        "automatic_model_promotion_authorized",
        "automatic_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if boundary.get(key) is not False:
            raise RuntimeError(f"unsafe monthly review authority boundary: {key}")

    store = None
    previous = None
    if not args.dry_run:
        store = R2Store(
            account_id=required("CLOUDFLARE_ACCOUNT_ID"),
            bucket=required("R2_BUCKET_NAME"),
            access_key_id=required("R2_ACCESS_KEY_ID"),
            secret_access_key=required("R2_SECRET_ACCESS_KEY"),
        )
        previous = _previous_review(store, config)
    generated = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    catalog_payload = Path(args.catalog).read_bytes()
    catalog = json.loads(catalog_payload)
    review = build_monthly_universe_review(
        catalog,
        previous_review=previous,
        generated_at_utc=generated,
    )
    review_payload = (json.dumps(review, ensure_ascii=False, indent=2) + "\n").encode()
    objects = build_monthly_universe_objects(
        config=config,
        run_id=args.run_id,
        catalog=catalog_payload,
        review=review_payload,
        generated_at_utc=generated,
    )
    if args.dry_run:
        result = {
            "status": "PREPARED",
            "stage": "BINANCE_SPOT_MONTHLY_UNIVERSE_REVIEW_DRY_RUN_V0_4",
            "r2_client_constructed": False,
            "r2_writes_performed": False,
            "objects": [
                {"role": item.role, "key": item.key, "bytes": len(item.payload)}
                for item in objects
            ],
        }
    else:
        assert store is not None
        result = publish_online_objects(
            store=store,
            objects=objects,
            hard_stop_bytes=int(config["storage"]["free_only_hard_stop_bytes"]),
            pass_stage="BINANCE_SPOT_MONTHLY_UNIVERSE_REVIEW_PUBLISHED_V0_4",
            metadata_version="v0.4",
        )
    result.update(
        {
            "generated_at_utc": generated,
            "run_id": args.run_id,
            "provider": "binance_spot",
            "baseline_created": review["baseline_created"],
            "market_count": review["market_count"],
            "historical_universe_membership_authorized": False,
            "formal_backtest_admission_authorized": False,
            "automatic_model_promotion_authorized": False,
            "automatic_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        }
    )
    review_output.parent.mkdir(parents=True, exist_ok=True)
    review_output.write_bytes(review_payload)
    receipt_output.parent.mkdir(parents=True, exist_ok=True)
    receipt_output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": result["status"], "markets": review["market_count"]}))
    return 0 if result["status"] in {"PASS", "PREPARED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
