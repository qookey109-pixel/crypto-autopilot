"""One-time, read-only R2 usage diagnostic with bounded aggregation."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

AUTHORITY = "cloud-paper-r2-usage-audit-v0.3"
WORKFLOW_FILE = "cloud-paper-r2-usage-audit-v0-3.yml"
REQUEST_URL = "https://api.cloudflare.com/client/v4/graphql"
OPERATIONS_LIMIT = 100
STORAGE_LIMIT = 10_000
FRESHNESS_LIMIT_SECONDS = 172_800
MAX_RESPONSE_BYTES = 33_554_432
REPORT_SCHEMA = "qookey-cloud-paper-r2-usage-report-v0.3"

QUERY = """
query CloudPaperR2UsageAudit($accountTag: string!, $startTime: Time, $endTime: Time) {
  viewer {
    accounts(filter: { accountTag: $accountTag }) {
      r2Operations: r2OperationsAdaptiveGroups(
        limit: 100
        filter: { datetime_geq: $startTime, datetime_leq: $endTime }
      ) {
        sum { requests }
        dimensions { actionType }
      }
      r2Storage: r2StorageAdaptiveGroups(
        limit: 10000
        filter: { datetime_geq: $startTime, datetime_leq: $endTime }
        orderBy: [datetime_DESC]
      ) {
        max { objectCount uploadCount payloadSize metadataSize }
        dimensions { bucketName datetime }
      }
    }
  }
}
"""


class AuditError(ValueError):
    """Fixed safe error code; never includes response bodies or credentials."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _request_json(*, headers: dict[str, str], body: bytes) -> dict[str, Any]:
    request = urllib.request.Request(REQUEST_URL, data=body, headers=headers, method="POST")
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=20) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise AuditError(f"CLOUDFLARE_HTTP_{exc.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise AuditError("CLOUDFLARE_REQUEST_FAILED") from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise AuditError("CLOUDFLARE_RESPONSE_TOO_LARGE")
    try:
        result = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise AuditError("CLOUDFLARE_RESPONSE_INVALID") from None
    if not isinstance(result, dict):
        raise AuditError("CLOUDFLARE_RESPONSE_INVALID")
    return result


def _int(value: object, code: str) -> int:
    if type(value) is not int or value < 0:
        raise AuditError(code)
    return value


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise AuditError("STORAGE_TIMESTAMP_MISSING")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise AuditError("STORAGE_TIMESTAMP_INVALID") from None
    if parsed.tzinfo is None:
        raise AuditError("STORAGE_TIMESTAMP_TIMEZONE_MISSING")
    return parsed.astimezone(UTC)


def _base_report(observed: datetime, start: datetime, end: datetime) -> dict[str, Any]:
    return {
        "schema": REPORT_SCHEMA,
        "authority": AUTHORITY,
        "status": "REVIEW_REQUIRED",
        "observed_at_utc": observed.astimezone(UTC).isoformat(),
        "window_start_utc": start.astimezone(UTC).isoformat(),
        "window_end_utc": end.astimezone(UTC).isoformat(),
        "coverage": {
            "account_scope": "ACCOUNT_TAG_ONLY_NO_BUCKET_FILTER",
            "dataset_group_counts": {"r2_operations": None, "r2_storage": None},
            "dataset_states": {"r2_operations": "NOT_OBSERVED", "r2_storage": "NOT_OBSERVED"},
            "operations_freshness": "UNKNOWN_QUERY_OMITS_DATETIME_DIMENSION",
            "bucket_inventory_completeness": "UNKNOWN_NOT_PROVEN_BY_ANALYTICS_ALONE",
            "d1_inventory_and_usage": "UNKNOWN_NOT_QUERIED",
            "billing_and_zero_cost": "UNKNOWN_NOT_QUERIED",
            "shared_account_writer_coverage": "UNKNOWN_NOT_PROVEN",
        },
        "r2": {
            "operations_total_requests": None,
            "operations_groups": None,
            "latest_returned_storage": None,
            "configured_storage_safety_ceiling_bytes": 8_000_000_000,
            "storage_headroom_gate": "UNKNOWN_NOT_AUTHORIZED_BY_THIS_AUDIT",
        },
        "account_id_persisted": False,
        "bucket_names_persisted": False,
        "raw_response_persisted": False,
        "zero_cost_conclusion": "UNKNOWN",
        "budget_activation": "NOT_AUTHORIZED_BY_THIS_AUDIT",
        "cloud_paper_activation": "REMAINS_DISABLED",
        "cloudflare_http_requests_performed": 0,
    }


def diagnose_r2(
    payload: object, *, observed_at: datetime, start_time: datetime, end_time: datetime,
) -> dict[str, Any]:
    """Summarize R2 operation counts and latest returned storage snapshots."""
    report = _base_report(observed_at, start_time, end_time)
    if any(value.tzinfo is None for value in (observed_at, start_time, end_time)):
        report["reason_code"] = "AUDIT_TIMEZONE_MISSING"
        return report
    observed = observed_at.astimezone(UTC)
    start = start_time.astimezone(UTC)
    end = end_time.astimezone(UTC)
    if end <= start or end > observed or end - start > timedelta(days=31):
        report["reason_code"] = "AUDIT_WINDOW_INVALID"
        return report
    if not isinstance(payload, dict) or payload.get("errors"):
        report["reason_code"] = "GRAPHQL_RESPONSE_ERROR"
        return report
    data = payload.get("data")
    viewer = data.get("viewer") if isinstance(data, dict) else None
    accounts = viewer.get("accounts") if isinstance(viewer, dict) else None
    if not isinstance(accounts, list) or len(accounts) != 1 or not isinstance(accounts[0], dict):
        report["reason_code"] = "ACCOUNT_SCOPE_UNAVAILABLE"
        return report
    account = accounts[0]
    datasets = (
        ("r2_operations", "r2Operations", OPERATIONS_LIMIT),
        ("r2_storage", "r2Storage", STORAGE_LIMIT),
    )
    states = report["coverage"]["dataset_states"]
    counts = report["coverage"]["dataset_group_counts"]
    rows_by_dataset: dict[str, list[dict[str, Any]]] = {}
    for report_name, payload_name, limit in datasets:
        rows = account.get(payload_name)
        if not isinstance(rows, list):
            states[report_name] = "MISSING_OR_INVALID"
            continue
        counts[report_name] = len(rows)
        if len(rows) >= limit:
            states[report_name] = "LIMIT_REACHED"
        elif not rows:
            states[report_name] = "EMPTY_UNVERIFIED"
        elif any(not isinstance(row, dict) for row in rows):
            states[report_name] = "INVALID_ROW"
        else:
            states[report_name] = "PRESENT"
            rows_by_dataset[report_name] = rows
    if any(state != "PRESENT" for state in states.values()):
        report["reason_code"] = "DATASET_COVERAGE_INCOMPLETE"
        return report

    try:
        operations_total = 0
        for row in rows_by_dataset["r2_operations"]:
            dimensions, summary = row.get("dimensions"), row.get("sum")
            if not isinstance(dimensions, dict) or not isinstance(summary, dict):
                raise AuditError("R2_OPERATION_FIELDS_MISSING")
            action = dimensions.get("actionType")
            if not isinstance(action, str) or not action or len(action) > 64:
                raise AuditError("R2_ACTION_TYPE_INVALID")
            operations_total += _int(summary.get("requests"), "R2_REQUEST_COUNT_INVALID")

        latest_by_bucket: dict[str, tuple[datetime, dict[str, int]]] = {}
        for row in rows_by_dataset["r2_storage"]:
            dimensions, metrics = row.get("dimensions"), row.get("max")
            if not isinstance(dimensions, dict) or not isinstance(metrics, dict):
                raise AuditError("R2_STORAGE_FIELDS_MISSING")
            bucket = dimensions.get("bucketName")
            if not isinstance(bucket, str) or not bucket or len(bucket) > 255:
                raise AuditError("R2_BUCKET_DIMENSION_INVALID")
            stamp = _timestamp(dimensions.get("datetime"))
            values = {
                field: _int(metrics.get(field), "R2_STORAGE_METRIC_INVALID")
                for field in ("objectCount", "uploadCount", "payloadSize", "metadataSize")
            }
            previous = latest_by_bucket.get(bucket)
            if previous is not None and stamp == previous[0] and values != previous[1]:
                raise AuditError("R2_STORAGE_SNAPSHOT_CONFLICT")
            if previous is None or stamp > previous[0]:
                latest_by_bucket[bucket] = (stamp, values)
        if not latest_by_bucket:
            raise AuditError("R2_STORAGE_BUCKETS_EMPTY")
        ages = [max(0, int((observed - stamp).total_seconds())) for stamp, _ in latest_by_bucket.values()]
        if max(ages) > FRESHNESS_LIMIT_SECONDS:
            raise AuditError("R2_STORAGE_STALE")
    except AuditError as exc:
        report["reason_code"] = str(exc)
        return report

    report["status"] = "READY_FOR_REVIEW"
    report["coverage"]["dataset_states"] = states
    report["coverage"]["r2_storage_latest_per_returned_bucket_utc"] = {
        "oldest_latest_snapshot_utc": min(stamp for stamp, _ in latest_by_bucket.values()).isoformat(),
        "newest_latest_snapshot_utc": max(stamp for stamp, _ in latest_by_bucket.values()).isoformat(),
        "worst_latest_snapshot_age_seconds": max(ages),
        "freshness_limit_seconds": FRESHNESS_LIMIT_SECONDS,
    }
    report["r2"] = {
        "operations_total_requests": operations_total,
        "operations_groups": len(rows_by_dataset["r2_operations"]),
        "operations_window_days": int((end - start).total_seconds() // 86400),
        "latest_returned_storage": {
            "returned_bucket_group_count": len(latest_by_bucket),
            "object_count": sum(value["objectCount"] for _, value in latest_by_bucket.values()),
            "upload_count": sum(value["uploadCount"] for _, value in latest_by_bucket.values()),
            "payload_bytes": sum(value["payloadSize"] for _, value in latest_by_bucket.values()),
            "metadata_bytes": sum(value["metadataSize"] for _, value in latest_by_bucket.values()),
            "total_bytes": sum(
                value["payloadSize"] + value["metadataSize"]
                for _, value in latest_by_bucket.values()
            ),
        },
        "configured_storage_safety_ceiling_bytes": 8_000_000_000,
        "storage_headroom_gate": "UNKNOWN_NOT_AUTHORIZED_BY_THIS_AUDIT",
    }
    report["reason_code"] = "R2_METRICS_CAPTURED_REVIEW_ONLY"
    return report


def readiness(
    *, variable_present: bool, secret_present: bool, token_present: bool, account_ids_match: bool,
) -> dict[str, Any]:
    if not variable_present:
        reason = "MISSING_ACCOUNT_ID_VARIABLE"
    elif not secret_present:
        reason = "MISSING_ACCOUNT_ID_SECRET"
    elif not token_present:
        reason = "MISSING_READ_ONLY_TOKEN_SECRET"
    elif not account_ids_match:
        reason = "ACCOUNT_ID_SECRET_VARIABLE_MISMATCH"
    else:
        reason = "CONFIGURATION_PRESENT"
    return {
        "schema": "qookey-cloud-paper-r2-usage-readiness-v0.3",
        "state": "READY" if reason == "CONFIGURATION_PRESENT" else "BLOCKED",
        "reason_code": reason,
        "account_id_variable_present": variable_present,
        "account_id_secret_present": secret_present,
        "account_ids_match": account_ids_match,
        "read_only_token_secret_present": token_present,
        "cloudflare_requests_performed": 0,
        "api_permission_state": "NOT_CHECKED_NO_NETWORK",
        "usage_evidence_state": "NOT_CHECKED_BY_READINESS",
        "budget_activation_state": "NOT_AUTHORIZED_BY_READINESS",
        "one_time_authority_consumed": False,
        "secret_values_printed": False,
    }


def _present(value: str | None) -> bool:
    return value == "true"


def _require_single_run() -> None:
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise AuditError("MAIN_BRANCH_REQUIRED")
    if os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
        raise AuditError("RERUN_FORBIDDEN")
    run_id = os.environ.get("GITHUB_RUN_ID")
    repo = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    api = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    if not run_id or not repo or not token:
        raise AuditError("GITHUB_RUN_METADATA_MISSING")
    url = f"{api}/repos/{repo}/actions/workflows/{WORKFLOW_FILE}/runs?branch=main&event=workflow_dispatch&per_page=100"
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            history = json.loads(response.read())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        raise AuditError("WORKFLOW_HISTORY_UNAVAILABLE") from None
    runs = history.get("workflow_runs") if isinstance(history, dict) else None
    if not isinstance(runs, list) or history.get("total_count", 0) >= 100:
        raise AuditError("WORKFLOW_HISTORY_AMBIGUOUS")
    if not any(isinstance(item, dict) and str(item.get("id")) == run_id for item in runs):
        raise AuditError("CURRENT_RUN_NOT_IN_HISTORY")
    if any(isinstance(item, dict) and str(item.get("id")) != run_id for item in runs):
        raise AuditError("ONE_TIME_AUTHORITY_ALREADY_CONSUMED")


def execute(output: Path) -> int:
    observed = datetime.now(UTC)
    start, end = observed - timedelta(days=30), observed
    requests = 0
    report = _base_report(observed, start, end)
    try:
        account = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        token = os.environ.get("CLOUDFLARE_READONLY_API_TOKEN")
        if not account:
            raise AuditError("MISSING_ACCOUNT_ID_SECRET")
        if not token:
            raise AuditError("MISSING_READ_ONLY_TOKEN_SECRET")
        if not _present(os.environ.get("ACCOUNT_ID_PARITY_VERIFIED")):
            raise AuditError("ACCOUNT_ID_SECRET_VARIABLE_MISMATCH")
        _require_single_run()
        variables = {
            "accountTag": account,
            "startTime": start.isoformat().replace("+00:00", "Z"),
            "endTime": end.isoformat().replace("+00:00", "Z"),
        }
        requests = 1
        payload = _request_json(
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            body=json.dumps({"query": QUERY, "variables": variables}).encode(),
        )
        report = diagnose_r2(
            payload,
            observed_at=datetime.now(UTC),
            start_time=start,
            end_time=end,
        )
    except AuditError as exc:
        report["reason_code"] = str(exc)
    report["github"] = {
        "repository": os.environ.get("GITHUB_REPOSITORY"),
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "head_sha": os.environ.get("GITHUB_SHA"),
        "event": "workflow_dispatch",
    }
    report["cloudflare_http_requests_performed"] = requests
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Cloud Paper R2 usage audit V0.3: {report['status']} ({report['reason_code']})")
    return 0 if report["status"] == "READY_FOR_REVIEW" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readiness", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.readiness:
        result = readiness(
            variable_present=_present(os.environ.get("ACCOUNT_ID_VARIABLE_PRESENT")),
            secret_present=_present(os.environ.get("ACCOUNT_ID_SECRET_PRESENT")),
            token_present=_present(os.environ.get("READ_ONLY_TOKEN_SECRET_PRESENT")),
            account_ids_match=_present(os.environ.get("ACCOUNT_ID_PARITY_VERIFIED")),
        )
        print(json.dumps(result, sort_keys=True))
        return 0 if result["state"] == "READY" else 1
    if args.output is None:
        parser.error("--output is required for audit")
    return execute(args.output)


if __name__ == "__main__":
    sys.exit(main())
