#!/usr/bin/env python3
"""Run one bounded Pionex asset-classification execution under V0.1 authority."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from crypto_autopilot.research.pionex_asset_classification_verifier_v0_1 import (
    AssetClassificationRejected,
    verify_selected_market_classification,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config/pionex_asset_classification_execution_v0_1.json"
DEFAULT_VERIFIER = ROOT / "config/pionex_asset_classification_verifier_v0_1.json"
DEFAULT_ALT_REGISTRY = ROOT / "config/pionex_alternative_assets_v0_1.json"
AUTHORITY = ROOT / "research/receipts/2026-09-12-pionex-asset-classification-execution-v0-1-authority.json"
CONFIG_SHA256 = "1e9f812b569739af0d2535fe4263f625c6ff7cb574bd5cd5559363a5d722f658"


class ClassificationExecutionRejected(RuntimeError):
    pass


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def _parse_utc(value: str, *, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ClassificationExecutionRejected(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ClassificationExecutionRejected(f"{field} must be explicit UTC")
    return parsed


def require_github_main_dispatch() -> None:
    expected = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_REPOSITORY": "qookey109-pixel/crypto-autopilot",
        "GITHUB_RUN_ATTEMPT": "1",
    }
    if any(os.environ.get(key) != value for key, value in expected.items()):
        raise ClassificationExecutionRejected(
            "fresh GitHub main workflow_dispatch attempt 1 required"
        )
    if not (os.environ.get("GITHUB_RUN_ID") or "").isdigit():
        raise ClassificationExecutionRejected("GitHub run id missing")


def load_authority(
    config_path: Path,
    verifier_path: Path,
    alternative_registry_path: Path,
) -> tuple[dict[str, Any], bytes, bytes]:
    config_bytes = config_path.read_bytes()
    if sha256_bytes(config_bytes) != CONFIG_SHA256:
        raise ClassificationExecutionRejected("execution config bytes changed")
    config = json.loads(config_bytes)
    receipt = json.loads(AUTHORITY.read_bytes())
    if receipt.get("config_sha256") != CONFIG_SHA256:
        raise ClassificationExecutionRejected(
            "authority receipt does not bind execution config"
        )
    if (
        receipt.get("status")
        != "AUTHORIZED_AFTER_PROTECTED_MAIN_MERGE_MANUAL_CLASSIFICATION_ONLY"
    ):
        raise ClassificationExecutionRejected("authority receipt is not executable")
    if receipt.get("execution_performed_by_this_receipt") is not False:
        raise ClassificationExecutionRejected("authority receipt cannot claim execution")
    if config.get("status") != receipt.get("status"):
        raise ClassificationExecutionRejected("execution config/receipt status mismatch")

    verifier_bytes = verifier_path.read_bytes()
    alt_bytes = alternative_registry_path.read_bytes()
    contract = config.get("verifier_contract")
    if not isinstance(contract, Mapping):
        raise ClassificationExecutionRejected("verifier contract missing")
    if contract.get("path") != "config/pionex_asset_classification_verifier_v0_1.json":
        raise ClassificationExecutionRejected("verifier path changed")
    if contract.get("sha256") != sha256_bytes(verifier_bytes):
        raise ClassificationExecutionRejected("verifier config SHA-256 mismatch")

    expected_authority = {
        "github_actions_artifact_read": True,
        "public_coinpaprika_metadata_read": True,
        "workflow_dispatch": True,
        "automatic_schedule": False,
        "api_key_required": False,
        "private_account_reads": False,
        "r2_read": False,
        "r2_write": False,
        "universe_membership_change": False,
        "historical_materialization": False,
        "holdout_access": False,
        "training": False,
        "automatic_model_promotion": False,
        "strategy_change": False,
        "source_switch": False,
        "trade_plan": False,
        "real_money_orders": False,
        "live_trading": False,
    }
    if config.get("authority") != expected_authority:
        raise ClassificationExecutionRejected("execution authority widened or changed")
    if receipt.get("public_coinpaprika_metadata_read_authorized") is not True:
        raise ClassificationExecutionRejected("provider read not authorized")
    if any(
        receipt.get(key) is not False
        for key in (
            "automatic_schedule_authorized",
            "r2_access_authorized",
            "holdout_access_authorized",
            "universe_membership_change_authorized",
            "historical_materialization_authorized",
            "training_authorized",
            "automatic_model_promotion_authorized",
            "strategy_change_authorized",
            "source_switch_authorized",
            "trade_plan_authorized",
            "real_money_orders_authorized",
            "live_trading_authorized",
        )
    ):
        raise ClassificationExecutionRejected("authority receipt widened")

    return config, verifier_bytes, alt_bytes


def require_execution_window(config: Mapping[str, Any], *, observed_at: datetime) -> None:
    execution = config.get("execution")
    if not isinstance(execution, Mapping):
        raise ClassificationExecutionRejected("execution contract missing")
    start = _parse_utc(str(execution.get("not_before_utc")), field="not_before_utc")
    stop = _parse_utc(str(execution.get("stop_exclusive_utc")), field="stop_exclusive_utc")
    if not start <= observed_at < stop:
        raise ClassificationExecutionRejected("execution window closed")
    if execution.get("provider_request_count_exact") != 1:
        raise ClassificationExecutionRejected("provider request count changed")
    if execution.get("automatic_retries") != 0:
        raise ClassificationExecutionRejected("automatic retries must remain zero")
    if execution.get("github_actions_main_only") is not True:
        raise ClassificationExecutionRejected("main-only guard disabled")
    if execution.get("workflow_dispatch_only") is not True:
        raise ClassificationExecutionRejected("manual-only guard disabled")
    if execution.get("accepted_run_attempt") != 1:
        raise ClassificationExecutionRejected("accepted run attempt changed")


def validate_universe_report(config: Mapping[str, Any], payload: bytes) -> dict[str, Any]:
    source = config.get("universe_source")
    if not isinstance(source, Mapping):
        raise ClassificationExecutionRejected("universe source missing")
    if sha256_bytes(payload) != source.get("report_sha256"):
        raise ClassificationExecutionRejected("universe report SHA-256 mismatch")
    try:
        report = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ClassificationExecutionRejected("universe report is not valid JSON") from exc
    expected = {
        "status": source.get("expected_status"),
        "selected_market_count": source.get("expected_selected_market_count"),
        "crypto_core_count": source.get("expected_crypto_core_count"),
        "run_id": str(source.get("run_id")),
        "run_attempt": str(source.get("run_attempt")),
        "head_ref": "refs/heads/main",
        "provider": "pionex_public_futures",
    }
    for key, value in expected.items():
        if report.get(key) != value:
            raise ClassificationExecutionRejected(
                f"universe report binding mismatch: {key}"
            )
    if len(report.get("markets") or []) != source.get("expected_selected_market_count"):
        raise ClassificationExecutionRejected("universe market list length mismatch")
    return report


def fetch_coinpaprika(config: Mapping[str, Any]) -> bytes:
    provider = config.get("provider")
    execution = config.get("execution")
    if not isinstance(provider, Mapping) or not isinstance(execution, Mapping):
        raise ClassificationExecutionRejected("provider/execution contract missing")
    if provider != {
        "name": "coinpaprika",
        "endpoint": "https://api.coinpaprika.com/v1/coins",
        "authentication_required": False,
        "metadata_only": True,
    }:
        raise ClassificationExecutionRejected("provider contract changed")
    request = Request(
        str(provider["endpoint"]),
        headers={
            "User-Agent": str(execution["user_agent"]),
            "Accept": "application/json",
        },
        method="GET",
    )
    max_bytes = int(execution["max_response_bytes"])
    try:
        with urlopen(
            request, timeout=int(execution["request_timeout_seconds"])
        ) as response:  # noqa: S310
            if int(getattr(response, "status", 200)) != 200:
                raise ClassificationExecutionRejected(
                    "CoinPaprika HTTP status rejected"
                )
            payload = response.read(max_bytes + 1)
    except HTTPError as exc:
        raise ClassificationExecutionRejected(
            f"CoinPaprika HTTP error: {exc.code}"
        ) from exc
    except (URLError, TimeoutError) as exc:
        raise ClassificationExecutionRejected(
            "CoinPaprika request failed or timed out"
        ) from exc
    if not payload:
        raise ClassificationExecutionRejected("CoinPaprika returned empty payload")
    if len(payload) > max_bytes:
        raise ClassificationExecutionRejected(
            "CoinPaprika payload exceeded max_response_bytes"
        )
    return payload


def run(
    *,
    config_path: Path,
    verifier_path: Path,
    alternative_registry_path: Path,
    universe_report_path: Path,
    output: Path,
) -> int:
    require_github_main_dispatch()
    config, verifier_bytes, alt_bytes = load_authority(
        config_path, verifier_path, alternative_registry_path
    )
    require_execution_window(config, observed_at=datetime.now(UTC))
    universe_payload = universe_report_path.read_bytes()
    universe_report = validate_universe_report(config, universe_payload)
    coinpaprika_payload = fetch_coinpaprika(config)
    verifier_config = json.loads(verifier_bytes)
    try:
        result = verify_selected_market_classification(
            verifier_config,
            alternative_registry_bytes=alt_bytes,
            universe_report=universe_report,
            coinpaprika_payload=coinpaprika_payload,
        )
    except AssetClassificationRejected as exc:
        raise ClassificationExecutionRejected(str(exc)) from exc

    report = {
        "schema": "pionex-asset-classification-execution-report-v0.1",
        "status": "PASS",
        "classification_gate_status": result["status"],
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "event": os.environ.get("GITHUB_EVENT_NAME"),
        "head_ref": os.environ.get("GITHUB_REF"),
        "execution_config_sha256": CONFIG_SHA256,
        "source_universe_run_id": config["universe_source"]["run_id"],
        "source_universe_report_sha256": config["universe_source"]["report_sha256"],
        "provider": "coinpaprika",
        "provider_requests_performed": 1,
        "automatic_retries_performed": 0,
        "raw_provider_payload_persisted": False,
        "r2_accessed": False,
        "holdout_accessed": False,
        "universe_membership_changed": False,
        "historical_materialization_performed": False,
        "training_authorized": False,
        "automatic_model_promotion_authorized": False,
        "strategy_changed": False,
        "source_switch_authorized": False,
        "trade_plan_authorized": False,
        "real_money_orders_authorized": False,
        "live_trading_authorized": False,
        "classification_result": result,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes(report))
    print(
        json.dumps(
            {
                "status": report["status"],
                "classification_gate_status": report["classification_gate_status"],
                "selected_market_count": result["selected_market_count"],
                "unresolved_count": result["unresolved_count"],
                "provider_requests_performed": 1,
            },
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--verifier-config", type=Path, default=DEFAULT_VERIFIER)
    parser.add_argument("--alternative-registry", type=Path, default=DEFAULT_ALT_REGISTRY)
    parser.add_argument("--universe-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    return run(
        config_path=args.config,
        verifier_path=args.verifier_config,
        alternative_registry_path=args.alternative_registry,
        universe_report_path=args.universe_report,
        output=args.output,
    )


if __name__ == "__main__":
    raise SystemExit(main())
