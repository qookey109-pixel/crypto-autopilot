#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from crypto_autopilot.binance.vision import (
    BinanceVisionArchiveKey,
    ingest_kline_archive,
)
from crypto_autopilot.models import Candle
from crypto_autopilot.research.zec_v0_3_development_contract import (
    build_zec_v0_3_candidate_grid,
)
from crypto_autopilot.research.zec_v0_3_development_execution_authority import (
    AUTHORITY_ID,
    validate_zec_v0_3_development_execution_authority,
)
from crypto_autopilot.research.zec_v0_3_development_runner import (
    run_zec_v0_3_development_matrix,
    select_zec_v0_3_development_champion,
)
from crypto_autopilot.research.zec_v0_3_selection_policy import (
    validate_zec_v0_3_selection_policy,
)


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "research/receipts/2026-09-21-zec-v0-3-development-one-shot-authority.json"
CONTRACT = ROOT / "config/zec_strategy_v0_3_development_matrix_v0_1.json"
SELECTION_POLICY = ROOT / "config/zec_strategy_v0_3_selection_policy_v0_1.json"
WORKFLOW = "zec-v0-3-development-execution-v0-1.yml"
REPOSITORY = "qookey109-pixel/crypto-autopilot"
STEP_MS = 15 * 60 * 1000


class ZecV03ExecutionPreflightError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()  # noqa: S324 - Git object identity


def _request_bytes(url: str, *, timeout_seconds: float = 45.0) -> bytes:
    """Perform exactly one bounded public-source request.

    The reviewed authority caps the full 48-month study at 96 requests
    (archive + checksum). Retries would silently expand that authority, so any
    network failure fails closed and requires a new versioned authority.
    """

    request = Request(
        url,
        headers={"User-Agent": "qookey-zec-v0-3-development/0.1"},
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - URL comes from validated Binance Vision key
            return response.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        if isinstance(exc, HTTPError) and exc.code == 404:
            raise RuntimeError("required frozen Binance Vision archive is missing") from exc
        raise RuntimeError("failed to read required frozen Binance Vision archive") from exc


def _github_json(url: str) -> dict[str, Any]:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ZecV03ExecutionPreflightError("scoped GITHUB_TOKEN is required")
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "qookey-zec-v0-3-authority-preflight/0.1",
        },
    )
    with urlopen(request, timeout=20.0) as response:  # noqa: S310 - fixed GitHub API host
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ZecV03ExecutionPreflightError("unexpected GitHub API response")
    return payload


def _verify_runtime_authority(
    authority_payload: dict[str, Any],
    *,
    requested_authority_id: str,
) -> tuple[object, dict[str, Any]]:
    if requested_authority_id != AUTHORITY_ID:
        raise ZecV03ExecutionPreflightError("workflow authority id mismatch")
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise ZecV03ExecutionPreflightError("GitHub-hosted execution is required")
    if os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        raise ZecV03ExecutionPreflightError("workflow_dispatch is required")
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise ZecV03ExecutionPreflightError("execution must run from protected main")
    if os.environ.get("GITHUB_REPOSITORY") != REPOSITORY:
        raise ZecV03ExecutionPreflightError("unexpected GitHub repository")
    if os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
        raise ZecV03ExecutionPreflightError("one-shot authority forbids workflow reruns")

    run_id = os.environ.get("GITHUB_RUN_ID")
    head_sha = os.environ.get("GITHUB_SHA")
    if not run_id or not run_id.isdigit():
        raise ZecV03ExecutionPreflightError("valid GitHub run id is required")
    if (
        not isinstance(head_sha, str)
        or len(head_sha) != 40
        or any(ch not in "0123456789abcdef" for ch in head_sha)
    ):
        raise ZecV03ExecutionPreflightError("valid GitHub head SHA is required")

    pr_number = authority_payload.get("authority_pr_number")
    if isinstance(pr_number, bool) or not isinstance(pr_number, int) or pr_number < 1:
        raise ZecV03ExecutionPreflightError("authority PR number is not finalized")
    pr = _github_json(f"https://api.github.com/repos/{REPOSITORY}/pulls/{pr_number}")
    merge_sha = pr.get("merge_commit_sha")
    if (
        pr.get("merged_at") is None
        or pr.get("base", {}).get("ref") != "main"
        or not isinstance(merge_sha, str)
        or len(merge_sha) != 40
    ):
        raise ZecV03ExecutionPreflightError("authority PR is not merged on main")

    comparison = _github_json(
        f"https://api.github.com/repos/{REPOSITORY}/compare/{merge_sha}...{head_sha}"
    )
    if comparison.get("status") not in {"identical", "ahead"}:
        raise ZecV03ExecutionPreflightError(
            "current main does not descend from the authority merge"
        )

    title = f"ZEC V0.3 Development · {AUTHORITY_ID}"
    runs = _github_json(
        f"https://api.github.com/repos/{REPOSITORY}/actions/workflows/{WORKFLOW}/runs"
        "?branch=main&event=workflow_dispatch&per_page=100"
    )
    prior = [
        row
        for row in runs.get("workflow_runs", [])
        if isinstance(row, dict)
        and str(row.get("id")) != run_id
        and row.get("display_title") == title
    ]
    if prior:
        raise ZecV03ExecutionPreflightError(
            "one-shot ZEC V0.3 development authority is already consumed"
        )

    bindings = authority_payload.get("bound_git_blobs")
    if not isinstance(bindings, dict):
        raise ZecV03ExecutionPreflightError("authority Git blob bindings are missing")
    observed = {
        relative: _git_blob_sha(ROOT / relative)
        for relative in bindings
    }
    authority = validate_zec_v0_3_development_execution_authority(
        authority_payload,
        authority_pr_merged=True,
        observed_blob_shas=observed,
    )
    if not authority.effective:
        raise ZecV03ExecutionPreflightError("authority did not become effective")
    return authority, {
        "authority_pr_number": pr_number,
        "authority_merge_sha": merge_sha,
        "execution_head_sha": head_sha,
        "github_run_id": int(run_id),
        "github_run_attempt": 1,
    }


def _periods() -> tuple[str, ...]:
    output: list[str] = []
    year, month = 2022, 8
    while (year, month) <= (2026, 7):
        output.append(f"{year:04d}-{month:02d}")
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
    if len(output) != 48:
        raise RuntimeError("frozen development month inventory drifted")
    return tuple(output)


def _month_bounds(period: str) -> tuple[int, int]:
    start = datetime.strptime(period + "-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if start.month == 12:
        next_month = start.replace(year=start.year + 1, month=1)
    else:
        next_month = start.replace(month=start.month + 1)
    return int(start.timestamp() * 1000), int(next_month.timestamp() * 1000)


def _load_frozen_development_source() -> tuple[tuple[Candle, ...], list[dict[str, Any]]]:
    candles: list[Candle] = []
    receipts: list[dict[str, Any]] = []
    for period in _periods():
        key = BinanceVisionArchiveKey(
            dataset="klines",
            frequency="monthly",
            symbol="ZECUSDT",
            interval="15m",
            period=period,
        )
        archive_bytes = _request_bytes(key.url)
        checksum_bytes = _request_bytes(key.checksum_url)
        result = ingest_kline_archive(
            key,
            archive_bytes=archive_bytes,
            checksum_payload=checksum_bytes,
        )
        receipt = result.receipt
        start_ms, end_ms = _month_bounds(period)
        expected_rows = (end_ms - start_ms) // STEP_MS
        if receipt.audit_ok is not True:
            raise RuntimeError("ZEC V0.3 requires strict full-month candle audit")
        if receipt.first_time_ms != start_ms:
            raise RuntimeError("ZEC V0.3 monthly archive does not start at month boundary")
        if receipt.last_time_ms != end_ms - STEP_MS:
            raise RuntimeError("ZEC V0.3 monthly archive does not end at month boundary")
        if receipt.row_count != expected_rows:
            raise RuntimeError("ZEC V0.3 monthly archive row count mismatch")
        candles.extend(result.candles)
        receipts.append({
            "period": period,
            "archive_sha256": receipt.archive_sha256,
            "row_count": receipt.row_count,
            "first_time_ms": receipt.first_time_ms,
            "last_time_ms": receipt.last_time_ms,
            "audit_ok": receipt.audit_ok,
        })

    if len(candles) != 140256:
        raise RuntimeError("ZEC V0.3 frozen development row count mismatch")
    if candles[0].time_ms != 1659312000000:
        raise RuntimeError("ZEC V0.3 frozen development start mismatch")
    if candles[-1].time_ms != 1785541500000:
        raise RuntimeError("ZEC V0.3 frozen development end mismatch")
    if any(
        right.time_ms - left.time_ms != STEP_MS
        for left, right in zip(candles, candles[1:])
    ):
        raise RuntimeError("ZEC V0.3 development source is not globally contiguous")
    return tuple(candles), receipts


def _cell_payload(row: object) -> dict[str, Any]:
    metrics = getattr(row, "metrics")
    return {
        "candidate_id": getattr(row, "candidate_id"),
        "fold_id": getattr(row, "fold_id"),
        "start_time_ms": getattr(row, "start_time_ms"),
        "end_exclusive_time_ms": getattr(row, "end_exclusive_time_ms"),
        "initial_equity_usd": getattr(row, "initial_equity_usd"),
        "final_equity_usd": getattr(row, "final_equity_usd"),
        "metrics": asdict(metrics),
        "paper_only": getattr(row, "paper_only"),
        "provider_requests_performed": getattr(row, "provider_requests_performed"),
        "r2_reads_performed": getattr(row, "r2_reads_performed"),
        "r2_writes_performed": getattr(row, "r2_writes_performed"),
        "formal_holdout_accessed": getattr(row, "formal_holdout_accessed"),
        "live_trading_authorized": getattr(row, "live_trading_authorized"),
    }


def execute(*, requested_authority_id: str) -> dict[str, Any]:
    authority_payload = _read_json(AUTHORITY)
    execution_authority, runtime = _verify_runtime_authority(
        authority_payload,
        requested_authority_id=requested_authority_id,
    )

    contract = _read_json(CONTRACT)
    selection_payload = _read_json(SELECTION_POLICY)
    selection_policy, selection_sha = validate_zec_v0_3_selection_policy(
        selection_payload
    )

    candles, source_receipts = _load_frozen_development_source()
    results, ranking = run_zec_v0_3_development_matrix(
        candles_15m=candles,
        contract=contract,
        execution_authority=execution_authority,
        funding_points=None,
    )
    candidates = build_zec_v0_3_candidate_grid(contract)
    fold_ids = tuple(
        str(row["fold_id"])
        for row in contract["development_window"]["folds"]
    )
    selection = select_zec_v0_3_development_champion(
        candidates=candidates,
        fold_ids=fold_ids,
        results=results,
        policy=selection_policy,
        policy_sha256=selection_sha,
    )

    if len(results) != 256:
        raise RuntimeError("ZEC V0.3 development matrix is incomplete")
    if any(row.provider_requests_performed != 0 for row in results):
        raise RuntimeError("offline development engine performed provider requests")
    if any(row.r2_reads_performed or row.r2_writes_performed for row in results):
        raise RuntimeError("offline development engine touched R2")
    if any(row.formal_holdout_accessed for row in results):
        raise RuntimeError("offline development engine touched formal holdout")

    return {
        "schema": "qookey-zec-v0-3-development-run-report-v0.1",
        "status": "PASS_EXECUTION_COMPLETE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "authority_id": AUTHORITY_ID,
        "runtime_authority": runtime,
        "source": {
            "provider": "binance_usdm",
            "delivery": "binance_vision_public_monthly",
            "symbol": "ZECUSDT",
            "interval": "15m",
            "archive_count": len(source_receipts),
            "provider_requests_performed": len(source_receipts) * 2,
            "row_count": len(candles),
            "first_time_ms": candles[0].time_ms,
            "last_time_ms": candles[-1].time_ms,
            "raw_candles_persisted": False,
            "archive_receipts": source_receipts,
        },
        "development": {
            "candidate_count": len(candidates),
            "fold_count": len(fold_ids),
            "matrix_cells": len(results),
            "primary_slippage_bps_per_side": 5.0,
            "funding_status": "UNAVAILABLE_NOT_FABRICATED",
            "matrix": [_cell_payload(row) for row in results],
            "diagnostic_ranking": asdict(ranking),
            "selection": asdict(selection),
        },
        "safety_boundary": {
            "fresh_confirmation_accessed": False,
            "fresh_confirmation_access_authorized": False,
            "r2_reads_performed": False,
            "r2_writes_performed": False,
            "raw_candles_persisted": False,
            "raw_trade_artifact_emitted": False,
            "formal_holdout_accessed": False,
            "source_switch_authorized": False,
            "model_promotion_authorized": False,
            "formal_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        report = execute(requested_authority_id=args.authority_id)
    except Exception as exc:
        report = {
            "schema": "qookey-zec-v0-3-development-run-report-v0.1",
            "status": "FAIL_CLOSED",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "authority_id": args.authority_id,
            "error_class": type(exc).__name__,
            "error": str(exc),
            "safety_boundary": {
                "fresh_confirmation_accessed": False,
                "r2_writes_performed": False,
                "formal_holdout_accessed": False,
                "source_switch_authorized": False,
                "model_promotion_authorized": False,
                "real_money_order_authorized": False,
                "live_trading_authorized": False,
            },
        }
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({"status": "FAIL_CLOSED", "error_class": type(exc).__name__}))
        return 1

    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": report["status"],
        "matrix_cells": report["development"]["matrix_cells"],
        "selection_status": report["development"]["selection"]["status"],
        "provider_requests_performed": report["source"]["provider_requests_performed"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
