from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_autopilot.research.signal_quality import (
    ResearchSignalQualityError,
    evaluate_research_signal_quality,
)
from crypto_autopilot.storage.r2 import R2Store


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ResearchSignalQualityError(f"required GitHub Actions secret is missing: {name}")
    return value


def _write_report(path: str, report: dict[str, object]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_previous(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    source = Path(path)
    if not source.exists():
        return None
    value = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != "research-signal-quality-v0.1":
        raise ResearchSignalQualityError("previous quality evidence has an unexpected schema")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Check public research signal quality")
    parser.add_argument("--config", default="config/research_signal_quality_v0_1.json")
    parser.add_argument("--output", required=True)
    parser.add_argument("--previous-report")
    parser.add_argument("--expected-run-id")
    parser.add_argument("--source-workflow-run-id")
    parser.add_argument("--source-head-sha")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    if config.get("schema") != "research-signal-quality-v0.1":
        raise RuntimeError("unexpected research signal quality config")
    storage = config["storage"]
    if storage.get("r2_list_authorized") is not False:
        raise RuntimeError("research signal quality must not list R2")
    if storage.get("r2_write_authorized") is not False:
        raise RuntimeError("research signal quality must not write R2")

    previous = None
    try:
        previous = _load_previous(args.previous_report)
    except (ResearchSignalQualityError, ValueError, json.JSONDecodeError) as exc:
        print(f"::warning::previous quality evidence ignored: {exc}")

    try:
        store = R2Store(
            account_id=_required("CLOUDFLARE_ACCOUNT_ID"),
            bucket=_required("R2_BUCKET_NAME"),
            access_key_id=_required("R2_ACCESS_KEY_ID"),
            secret_access_key=_required("R2_SECRET_ACCESS_KEY"),
        )
        report = evaluate_research_signal_quality(
            store,
            namespace=str(storage["namespace"]),
            now=datetime.now(timezone.utc),
            max_age_seconds=int(config["quality"]["max_age_seconds"]),
            expected_run_id=args.expected_run_id,
            previous_report=previous,
        )
    except (ResearchSignalQualityError, ValueError) as exc:
        report = {
            "schema": "research-signal-quality-v0.1",
            "status": "ALERT",
            "quality": "INVALID_OR_MISSING",
            "decision": "EVALUATION_FAILED",
            "error": str(exc),
            "authority": {
                "r2_exact_object_read_only": True,
                "r2_list": False,
                "r2_write": False,
                "provider_access": False,
                "holdout_access": False,
                "automatic_model_promotion": False,
                "direct_trade_trigger": False,
                "real_money_order": False,
                "live_trading": False,
            },
        }

    report["execution_provenance"] = {
        "quality_workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "quality_workflow_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "quality_head_sha": os.environ.get("GITHUB_SHA"),
        "trigger_event": os.environ.get("GITHUB_EVENT_NAME"),
        "source_workflow_run_id": args.source_workflow_run_id,
        "source_head_sha": args.source_head_sha,
        "expected_signal_run_id": args.expected_run_id,
    }
    _write_report(args.output, report)
    summary = (
        "# Research Signal Quality V0.1\n\n"
        f"Status: **{report['status']}** · quality: **{report['quality']}**"
        f" · decision: **{report.get('decision', 'UNKNOWN')}**\n"
    )
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with Path(step_summary).open("a", encoding="utf-8") as handle:
            handle.write(summary)
    print(summary)
    return 2 if report["status"] == "ALERT" else 0


if __name__ == "__main__":
    raise SystemExit(main())
