#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.providers.context_forward_capture_report import (
    validate_context_forward_execution_report,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config/context_forward_capture_execution_v0_1.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    config = json.loads(args.config.read_text(encoding="utf-8"))
    status = validate_context_forward_execution_report(report, config=config)
    print(
        json.dumps(
            {
                "status": "PASS",
                "stage": "CONTEXT_FORWARD_EXECUTION_REPORT_VALIDATION_V0_1",
                "execution_report_status": status,
                "authority_expanded": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
