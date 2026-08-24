from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from crypto_autopilot.research_automation_health import (
    audit_workflow_inventory,
    evaluate_automation_health,
    expectation_from_config,
    fetch_workflow_runs,
    markdown_summary,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check research automation health from GitHub metadata")
    parser.add_argument("--config", default="config/research_automation_health_v0_1.json")
    parser.add_argument("--output", required=True)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--now-utc")
    parser.add_argument("--fail-on-alert", action="store_true")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    if config.get("schema") != "research-automation-health-v0.1":
        raise RuntimeError("unexpected research automation health config")
    token = os.environ.get("GITHUB_TOKEN", "")
    expectations = [expectation_from_config(item) for item in config["workflows"]]
    runs = {
        item.workflow: fetch_workflow_runs(
            repository=args.repository,
            workflow=item.workflow,
            token=token,
        )
        for item in expectations
    }
    now = (
        datetime.fromisoformat(args.now_utc.replace("Z", "+00:00"))
        if args.now_utc
        else datetime.now(timezone.utc)
    )
    report = evaluate_automation_health(expectations, runs, now=now)
    report["workflow_inventory"] = audit_workflow_inventory(".github/workflows")
    thresholds = config["inventory_warn_thresholds"]
    report["workflow_inventory"]["retired_pr_warning"] = (
        report["workflow_inventory"]["retired_pull_request_workflows"]
        >= int(thresholds["retired_pull_request_workflows"])
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    summary = markdown_summary(report)
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        Path(step_summary).write_text(summary, encoding="utf-8")
    print(summary)
    return 2 if args.fail_on_alert and report["status"] == "ALERT" else 0


if __name__ == "__main__":
    raise SystemExit(main())
