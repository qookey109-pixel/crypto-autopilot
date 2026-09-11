#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.providers.context_forward_capture_execution import canonical_json_bytes
from crypto_autopilot.providers.context_forward_capture_receipt import (
    build_context_forward_evidence_receipt,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config/context_forward_capture_execution_v0_1.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--repository-main-sha", required=True)
    parser.add_argument("--workflow-run-id", type=int, required=True)
    parser.add_argument("--workflow-run-attempt", type=int, required=True)
    parser.add_argument("--artifact-id", type=int, required=True)
    parser.add_argument("--artifact-name", required=True)
    parser.add_argument("--artifact-zip-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report_bytes = args.report.read_bytes()
    report = json.loads(report_bytes)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    receipt = build_context_forward_evidence_receipt(
        report,
        config=config,
        report_bytes=report_bytes,
        repository_main_sha=args.repository_main_sha,
        workflow_run_id=args.workflow_run_id,
        workflow_run_attempt=args.workflow_run_attempt,
        artifact_id=args.artifact_id,
        artifact_name=args.artifact_name,
        artifact_zip_sha256=args.artifact_zip_sha256,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json_bytes(receipt))
    print(json.dumps({"status": "PASS", "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
