#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import traceback
from pathlib import Path
from urllib.error import HTTPError, URLError

from crypto_autopilot.exchanges.pionex_public import PionexPublicClient
from crypto_autopilot.historical import PacedKlineClient
from crypto_autopilot.storage.historical_backfill import (
    CanonicalConflictError,
    PlannedInterruption,
    run_historical_backfill_pilot,
)
from crypto_autopilot.storage.r2 import R2Store

EXIT_TRANSIENT = 70
EXIT_PLANNED_STOP = 75
EXIT_CANONICAL_CONFLICT = 78
EXIT_AUDIT_FAILURE = 79


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a bounded resumable Pionex historical backfill pilot into Cloudflare R2."
    )
    parser.add_argument(
        "--authority-receipt",
        type=Path,
        default=Path("research/receipts/2026-08-17-m1a-pionex.json"),
    )
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=3)
    parser.add_argument("--requests-per-second", type=float, default=3.0)
    parser.add_argument("--page-limit", type=int, default=500)
    parser.add_argument("--planned-stop-after-staged", type=int)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def load_authority_symbols(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("stage") != "M1A_COMPLETE" or not payload.get("audit", {}).get("pass"):
        raise ValueError("Authority receipt is not a passing M1A authority")
    symbols = [str(item["symbol"]) for item in payload.get("selected_universe", [])]
    if not symbols:
        raise ValueError("Authority receipt has no selected universe")
    return symbols


def shard_symbols(symbols: list[str], shard_index: int, shard_count: int) -> list[str]:
    if shard_count < 1:
        raise ValueError("shard_count must be positive")
    if shard_index < 0 or shard_index >= shard_count:
        raise ValueError("shard_index must be between 0 and shard_count - 1")
    return symbols[shard_index::shard_count]


def write_summary(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def runtime_context(args: argparse.Namespace, storage_run_id: str) -> dict[str, object]:
    return {
        "shard_index": args.shard_index,
        "shard_count": args.shard_count,
        "authority_receipt": str(args.authority_receipt),
        "storage_run_id": storage_run_id,
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "github_sha": os.environ.get("GITHUB_SHA"),
        "process_attempt": os.environ.get("PILOT_PROCESS_ATTEMPT"),
    }


def classify_failure(exc: Exception) -> int:
    if isinstance(exc, CanonicalConflictError):
        return EXIT_CANONICAL_CONFLICT
    message = str(exc)
    if "Historical audit failed" in message or "Parquet audit failed" in message:
        return EXIT_AUDIT_FAILURE
    if isinstance(exc, HTTPError):
        return EXIT_TRANSIENT if exc.code in {408, 425, 429, 500, 502, 503, 504} else 1
    if isinstance(exc, (URLError, TimeoutError, ConnectionError)):
        return EXIT_TRANSIENT
    transient_names = {
        "ConnectTimeoutError",
        "ConnectionClosedError",
        "EndpointConnectionError",
        "ReadTimeoutError",
    }
    if type(exc).__name__ in transient_names:
        return EXIT_TRANSIENT
    transient_fragments = ("SlowDown", "RequestTimeout", "temporarily unavailable")
    if any(fragment.lower() in message.lower() for fragment in transient_fragments):
        return EXIT_TRANSIENT
    return 1


def main() -> int:
    args = parse_args()
    storage_run_id = f"historical-pilot-{args.year}-shard{args.shard_index}"

    try:
        symbols = shard_symbols(
            load_authority_symbols(args.authority_receipt),
            args.shard_index,
            args.shard_count,
        )
        store = R2Store(
            account_id=required("CLOUDFLARE_ACCOUNT_ID"),
            bucket=required("R2_BUCKET_NAME"),
            access_key_id=required("R2_ACCESS_KEY_ID"),
            secret_access_key=required("R2_SECRET_ACCESS_KEY"),
        )
        client = PacedKlineClient(
            PionexPublicClient(),
            requests_per_second=args.requests_per_second,
            retry_after_seconds=65.0,
            max_429_retries=4,
            jitter_seconds=2.0,
        )
        summary = run_historical_backfill_pilot(
            client=client,
            store=store,
            symbols=symbols,
            year=args.year,
            storage_run_id=storage_run_id,
            page_limit=args.page_limit,
            planned_stop_after_staged=args.planned_stop_after_staged,
        )
    except PlannedInterruption as exc:
        summary = {
            **exc.summary,
            **runtime_context(args, storage_run_id),
            "planned_interruption": str(exc),
            "exit_code": EXIT_PLANNED_STOP,
        }
        write_summary(args.output, summary)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return EXIT_PLANNED_STOP
    except Exception as exc:
        exit_code = classify_failure(exc)
        summary = {
            "schema_version": 1,
            "status": "FAIL",
            "year": args.year,
            **runtime_context(args, storage_run_id),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "exit_code": exit_code,
            "traceback": traceback.format_exc(),
        }
        write_summary(args.output, summary)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return exit_code

    summary = {
        **summary,
        **runtime_context(args, storage_run_id),
        "exit_code": 0,
    }
    write_summary(args.output, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
