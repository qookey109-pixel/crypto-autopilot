#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from crypto_autopilot.paper.cloud_pionex_client_v0_1 import (
    CloudPaperPionexPublicClient,
)
from crypto_autopilot.research.prospective_shadow_collector_v0_1 import (
    build_collection_record,
)

ROOT = Path(__file__).resolve().parents[1]
EXECUTION_CONFIG = ROOT / "config/prospective_shadow_collection_execution_v0_1.json"
RUNTIME_CONFIG = ROOT / "config/prospective_shadow_collection_runtime_v0_1.json"
UNIVERSE_CONFIG = ROOT / "config/pionex_research_universe_v0_1.json"
ALTERNATIVE_REGISTRY = ROOT / "config/pionex_alternative_assets_v0_1.json"
CONTEXT_CONFIG = ROOT / "config/context_forward_capture_v0_1.json"
SOURCE_LINEAGE = ROOT / "config/context_source_lineage_v0_1.json"

ALLOWED_COINPAPRIKA_URLS = frozenset(
    {
        "https://api.coinpaprika.com/v1/global",
        "https://api.coinpaprika.com/v1/tickers/eth-ethereum",
    }
)
MAX_COINPAPRIKA_BYTES = 1_048_576


class CollectionBlocked(RuntimeError):
    pass


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        fp.close()
        raise CollectionBlocked("PUBLIC_PROVIDER_REDIRECT_REJECTED")


class RequestBudget:
    def __init__(self, *, pionex_max: int = 8, coinpaprika_max: int = 2) -> None:
        self.pionex_max = pionex_max
        self.coinpaprika_max = coinpaprika_max
        self.pionex_requests = 0
        self.coinpaprika_requests = 0

    def reserve_pionex(self) -> None:
        if self.pionex_requests >= self.pionex_max:
            raise CollectionBlocked("PIONEX_REQUEST_BUDGET_EXHAUSTED")
        self.pionex_requests += 1

    def fetch_coinpaprika(self, url: str) -> bytes:
        if url not in ALLOWED_COINPAPRIKA_URLS:
            raise CollectionBlocked("COINPAPRIKA_URL_NOT_ALLOWED")
        if self.coinpaprika_requests >= self.coinpaprika_max:
            raise CollectionBlocked("COINPAPRIKA_REQUEST_BUDGET_EXHAUSTED")
        self.coinpaprika_requests += 1
        request = Request(
            url,
            method="GET",
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "identity",
                "User-Agent": "qookey-prospective-shadow-v0.1",
            },
        )
        try:
            with build_opener(_NoRedirect).open(request, timeout=20) as response:
                if response.getcode() != 200:
                    raise CollectionBlocked("COINPAPRIKA_HTTP_STATUS_REJECTED")
                encoding = response.headers.get("Content-Encoding", "identity").strip().lower()
                if encoding not in {"", "identity"}:
                    raise CollectionBlocked("COINPAPRIKA_CONTENT_ENCODING_REJECTED")
                body = response.read(MAX_COINPAPRIKA_BYTES + 1)
        except CollectionBlocked:
            raise
        except (HTTPError, URLError, TimeoutError, OSError):
            raise CollectionBlocked("COINPAPRIKA_REQUEST_FAILED") from None
        if len(body) > MAX_COINPAPRIKA_BYTES:
            raise CollectionBlocked("COINPAPRIKA_RESPONSE_TOO_LARGE")
        return body


def _load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CollectionBlocked(f"JSON object required: {path.name}")
    return value


def _parse_utc(value: str) -> int:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise CollectionBlocked("runtime window timestamp must be explicit UTC")
    return int(parsed.timestamp() * 1000)


def _require_runtime_boundary(runtime: dict[str, object], now_ms: int) -> None:
    if runtime.get("schema") != "qookey-prospective-shadow-collection-runtime-v0.1":
        raise CollectionBlocked("unexpected runtime schema")
    if runtime.get("status") != "IMPLEMENTATION_BOUND_TO_AUTHORITY":
        raise CollectionBlocked("runtime implementation is not bound")
    window = runtime.get("window")
    if not isinstance(window, dict):
        raise CollectionBlocked("runtime window missing")
    not_before = _parse_utc(str(window.get("not_before_utc")))
    expires = _parse_utc(str(window.get("expires_utc")))
    if not not_before <= now_ms < expires:
        raise CollectionBlocked("OUTSIDE_AUTHORIZED_COLLECTION_WINDOW")


def _require_github_main() -> None:
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise CollectionBlocked("GITHUB_ACTIONS_REQUIRED")
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise CollectionBlocked("PROTECTED_MAIN_REQUIRED")
    if os.environ.get("GITHUB_EVENT_NAME") not in {"schedule", "workflow_dispatch"}:
        raise CollectionBlocked("UNAUTHORIZED_GITHUB_EVENT")


def run(output: Path) -> dict[str, object]:
    _require_github_main()
    execution = _load_json(EXECUTION_CONFIG)
    runtime = _load_json(RUNTIME_CONFIG)
    universe = _load_json(UNIVERSE_CONFIG)
    context = _load_json(CONTEXT_CONFIG)
    now_ms = time.time_ns() // 1_000_000
    _require_runtime_boundary(runtime, now_ms)

    budget = RequestBudget()
    client = CloudPaperPionexPublicClient(
        before_send=budget.reserve_pionex,
        timeout_seconds=10,
        requests_per_second=3,
    )
    record = build_collection_record(
        execution_config=execution,
        universe_config=universe,
        alternative_registry_bytes=ALTERNATIVE_REGISTRY.read_bytes(),
        context_config=context,
        source_lineage_bytes=SOURCE_LINEAGE.read_bytes(),
        client=client,
        fetch_public_bytes=budget.fetch_coinpaprika,
        capture_timestamp_ms=now_ms,
    )

    report = {
        "schema": "qookey-prospective-shadow-collection-execution-report-v0.1",
        "status": "PASS",
        "github": {
            "event_name": os.environ.get("GITHUB_EVENT_NAME"),
            "ref": os.environ.get("GITHUB_REF"),
            "sha": os.environ.get("GITHUB_SHA"),
            "run_id": os.environ.get("GITHUB_RUN_ID"),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        },
        "provider_requests": {
            "pionex": budget.pionex_requests,
            "coinpaprika": budget.coinpaprika_requests,
            "total": budget.pionex_requests + budget.coinpaprika_requests,
        },
        "collection": record,
        "authority": {
            "artifact_only_persistence": True,
            "r2_accessed": False,
            "d1_accessed": False,
            "holdout_accessed": False,
            "training_performed": False,
            "model_promotion_performed": False,
            "paper_submission_performed": False,
            "real_money_order_performed": False,
            "live_trading_performed": False,
        },
    }
    if budget.pionex_requests != 8:
        raise CollectionBlocked("PIONEX_REQUEST_COUNT_MISMATCH")
    if budget.coinpaprika_requests != 2:
        raise CollectionBlocked("COINPAPRIKA_REQUEST_COUNT_MISMATCH")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False),
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run bounded prospective shadow research collection V0.1"
    )
    parser.add_argument(
        "--output",
        default="artifacts/prospective-shadow-collection-v0-1/report.json",
    )
    args = parser.parse_args()
    run(Path(args.output))


if __name__ == "__main__":
    main()
