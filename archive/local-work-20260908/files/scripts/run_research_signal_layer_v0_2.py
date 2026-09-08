from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from crypto_autopilot.research_signal_ingest_v0_2 import (
    ResearchSignalIngestError,
    build_signal_payload,
    collect_sources,
    current_bucket_bytes,
    load_config,
    publish_signal_payload,
    utc_now_iso,
)
from crypto_autopilot.storage.r2 import R2Store


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ResearchSignalIngestError(f"required GitHub Actions secret is missing: {name}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect public research signals without trading authority")
    parser.add_argument("--config", default="config/research_signal_layer_v0_2.json")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--publish-r2", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    store = None
    if args.publish_r2:
        storage = config["storage"]
        if storage.get("r2_write_authorized") is not True:
            raise ResearchSignalIngestError("V0.2 R2 write authority is not active")
        store = R2Store(
            account_id=_required("CLOUDFLARE_ACCOUNT_ID"),
            bucket=_required("R2_BUCKET_NAME"),
            access_key_id=_required("R2_ACCESS_KEY_ID"),
            secret_access_key=_required("R2_SECRET_ACCESS_KEY"),
        )
        current = current_bucket_bytes(store)
        reservation = int(storage["max_planned_write_bytes"])
        hard_stop = int(storage["hard_stop_bytes"])
        if current + reservation > hard_stop:
            raise ResearchSignalIngestError("R2 FREE-ONLY headroom gate blocked before provider access")

    sources = config["sources"][: int(config["fetch"]["max_sources_per_run"])]
    snapshots, forecasts = collect_sources(
        sources,
        timeout_seconds=float(config["fetch"]["timeout_seconds"]),
        max_bytes=int(config["fetch"]["max_bytes_per_source"]),
    )
    payload = build_signal_payload(
        run_id=args.run_id,
        generated_at_utc=utc_now_iso(),
        snapshots=snapshots,
        forecasts=forecasts,
    )
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    if not args.publish_r2:
        print(json.dumps({"status": "DRY_RUN", "forecasts": len(forecasts)}, ensure_ascii=False))
        return 0
    storage = config["storage"]
    assert store is not None
    result = publish_signal_payload(
        store,
        payload=payload,
        namespace=str(storage["namespace"]),
        run_id=args.run_id,
        hard_stop_bytes=int(storage["hard_stop_bytes"]),
        planned_reservation_bytes=int(storage["max_planned_write_bytes"]),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if result["status"] == "BLOCKED":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
