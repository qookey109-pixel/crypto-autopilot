from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from crypto_autopilot.storage.m1a_dataset import materialize_m1a_dataset
from crypto_autopilot.storage.r2 import R2Store


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload the frozen M1A bounded Pionex evidence dataset to Cloudflare R2."
    )
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--authority-receipt", type=Path, required=True)
    parser.add_argument("--storage-run-id", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = R2Store(
        account_id=required("CLOUDFLARE_ACCOUNT_ID"),
        bucket=required("R2_BUCKET_NAME"),
        access_key_id=required("R2_ACCESS_KEY_ID"),
        secret_access_key=required("R2_SECRET_ACCESS_KEY"),
    )
    manifest, receipt = materialize_m1a_dataset(
        input_dir=args.input_dir,
        authority_receipt_path=args.authority_receipt,
        store=store,
        storage_run_id=args.storage_run_id,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "m1b-m1a-dataset-manifest.json"
    receipt_path = args.output_dir / "m1b-m1a-dataset-receipt.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "dataset": receipt["dataset"],
                "manifest_key": receipt["manifest"]["key"],
                "manifest_sha256": receipt["manifest"]["sha256"],
                "object_count": receipt["object_count"],
                "receipt_key": receipt["receipt"]["key"],
                "receipt_sha256": receipt["receipt"]["sha256"],
                "source_artifact_sha256": receipt["source_artifact_sha256"],
                "status": receipt["status"],
                "storage_run_id": receipt["storage_run_id"],
                "total_parquet_bytes": receipt["total_parquet_bytes"],
                "total_rows": receipt["total_rows"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
