from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pyarrow.parquet as pq

from crypto_autopilot.storage.ephemeral import require_ephemeral_output
from crypto_autopilot.training.shadow_ablation import run_shadow_ablation


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local-only Binance Spot V0.6 Shadow ablation")
    parser.add_argument("--config", default="config/binance_spot_shadow_v0_6.json")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--end-exclusive-ms", type=int, required=True)
    args = parser.parse_args()

    output = require_ephemeral_output(args.output)
    config_path = ROOT / args.config
    config_payload = config_path.read_bytes()
    config = json.loads(config_payload)
    config["generated_at_utc"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    dataset_path = Path(args.dataset)
    dataset_payload = dataset_path.read_bytes()
    required_columns = [
        "asset_class",
        "symbol",
        "audit_ok",
        "open_time_ms",
        "open",
        "high",
        "low",
        "close",
        "base_volume",
        "quote_volume",
    ]
    optional_orderflow_columns = [
        "taker_buy_base_volume",
        "taker_buy_quote_volume",
    ]
    schema_names = set(pq.read_schema(dataset_path).names)
    rows = pq.read_table(
        dataset_path,
        columns=required_columns
        + [name for name in optional_orderflow_columns if name in schema_names],
    ).to_pylist()
    result = run_shadow_ablation(
        rows,
        config=config,
        data_sha256=hashlib.sha256(dataset_payload).hexdigest(),
        config_sha256=hashlib.sha256(config_payload).hexdigest(),
        end_exclusive_ms=args.end_exclusive_ms,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "experiment_id": result["experiment_id"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
