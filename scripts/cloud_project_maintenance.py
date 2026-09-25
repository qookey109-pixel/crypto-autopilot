"""GitHub-hosted entrypoint. Never execute this against a user checkout."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from crypto_autopilot.research.cloud_maintenance import (
    GitHub, REPOSITORY, Stop, collect, digest, publish, require, summary,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("inspect", "publish"), required=True)
    args = parser.parse_args()
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    try:
        require(os.environ.get("GITHUB_ACTIONS") == "true"
                and os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted"
                and os.environ.get("GITHUB_REPOSITORY") == REPOSITORY
                and os.environ.get("GITHUB_EVENT_NAME") == "workflow_run",
                "CLOUD_ONLY")
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
        require(event.get("repository", {}).get("private") is False, "FREE_ONLY_PUBLIC_REPO")
        api = GitHub(os.environ.get("GITHUB_TOKEN", ""), writable=args.mode == "publish")
        record = collect(api, event, os.environ["GITHUB_SHA"], datetime.now(timezone.utc))
        semantic = digest(record["semantic"])
        if args.mode == "publish":
            require(record["evidence"]["main_sha"] == os.environ.get("EXPECTED_MAIN")
                    and semantic == os.environ.get("EXPECTED_DIGEST"), "OBSERVATION_CHANGED")
            result = publish(api, record)
        else:
            result = {"status": "READ_ONLY_COMPLETE"}
            with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
                output.write(f"main_sha={record['evidence']['main_sha']}\n")
                output.write(f"semantic_digest={semantic}\nready=true\n")
        report = summary(record, result)
        require(len(report.encode()) <= 900_000, "SUMMARY_SIZE_LIMIT")
        if summary_path:
            Path(summary_path).write_text(report, encoding="utf-8")
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Stop, KeyError, TypeError, ValueError, OSError) as exc:
        code = str(exc) if isinstance(exc, Stop) else "UNKNOWN_INVALID_INPUT"
        # No exception text from API/metadata/OS is exposed.
        if summary_path:
            Path(summary_path).write_text(
                "# Cloud Project Maintenance V0.1\n\n"
                f"Result: **{code}**\n\n"
                "Publication stopped. Read current main and CLOUD-02 in the continuation "
                "runbook. No retry, secret request, permission expansion or dispatch.\n",
                encoding="utf-8")
        print(json.dumps({"status": code}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
