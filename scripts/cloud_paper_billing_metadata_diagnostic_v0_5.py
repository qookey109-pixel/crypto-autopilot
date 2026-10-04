"""One-request, value-free successor diagnostic for consumed Billing History V0.3."""
from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.cloud_paper_billing_history_v0_2 import BillingHistoryError, _NoRedirect, _request_json

AUTHORITY = "cloud-paper-billing-metadata-diagnostic-v0.5"
WORKFLOW_FILE = "cloud-paper-billing-metadata-diagnostic-v0-5.yml"
REQUESTED_PAGE = 1
REQUESTED_PER_PAGE = 100
MAX_RESPONSE_BYTES = 1_048_576


def _json_type(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "other"


def diagnose_payload(payload: object, *, observed_at: datetime) -> dict[str, Any]:
    """Summarize only fixed codes, JSON types, field presence, and booleans."""
    if observed_at.tzinfo is None:
        raise BillingHistoryError("OBSERVATION_TIMEZONE_MISSING")
    report: dict[str, Any] = {
        "schema": "qookey-cloud-paper-billing-metadata-diagnostic-report-v0.5",
        "authority": AUTHORITY,
        "stage": "ONE_TIME_READ_ONLY_EXECUTION",
        "status": "REVIEW_REQUIRED",
        "reason_code": "NOT_EVALUATED",
        "observed_at_utc": observed_at.astimezone(UTC).isoformat(),
        "requested_page": REQUESTED_PAGE,
        "requested_per_page": REQUESTED_PER_PAGE,
        "response_object": isinstance(payload, dict),
        "success_is_true": False,
        "errors_present": False,
        "result_is_array": False,
        "result_info_is_object": False,
        "pagination_fields": {},
        "raw_response_persisted": False,
        "account_identity_persisted": False,
        "billing_values_persisted": False,
        "cloudflare_http_requests_performed": 0,
        "billing_readiness": "UNKNOWN",
        "zero_cost_conclusion": "UNKNOWN",
        "cloud_paper_activation": "REMAINS_DISABLED",
    }
    if not isinstance(payload, dict):
        report["reason_code"] = "RESPONSE_NOT_OBJECT"
        return report
    report["success_is_true"] = payload.get("success") is True
    if payload.get("success") is not True:
        report["reason_code"] = "SUCCESS_FLAG_NOT_TRUE"
        return report
    errors = payload.get("errors")
    report["errors_present"] = bool(errors)
    if errors:
        report["reason_code"] = "API_ERRORS_PRESENT"
        return report

    rows = payload.get("result")
    report["result_is_array"] = isinstance(rows, list)
    if not isinstance(rows, list):
        report["reason_code"] = "RESULT_NOT_ARRAY"
        return report
    info = payload.get("result_info")
    report["result_info_is_object"] = isinstance(info, dict)
    if not isinstance(info, dict):
        report["reason_code"] = "RESULT_INFO_NOT_OBJECT"
        return report

    fields: dict[str, dict[str, object]] = {}
    invalid: list[str] = []
    mismatch: list[str] = []
    for field, expected in (("page", REQUESTED_PAGE), ("per_page", REQUESTED_PER_PAGE)):
        present = field in info
        value = info.get(field)
        valid = type(value) is int and value >= 0
        matches = valid and value == expected
        fields[field] = {
            "present": present,
            "json_type": _json_type(value),
            "nonnegative_integer": valid,
            "matches_request": matches,
        }
        if not present or not valid:
            invalid.append(field)
        elif not matches:
            mismatch.append(field)

    for field in ("count", "total_count"):
        present = field in info
        value = info.get(field)
        valid = type(value) is int and value >= 0
        fields[field] = {
            "present": present,
            "json_type": _json_type(value),
            "nonnegative_integer": valid,
        }
        if not present or not valid:
            invalid.append(field)

    count = info.get("count")
    total = info.get("total_count")
    count_valid = type(count) is int and count >= 0
    total_valid = type(total) is int and total >= 0
    fields["count"]["matches_result_length"] = count_valid and count == len(rows)
    fields["count"]["within_requested_page_size"] = count_valid and count <= REQUESTED_PER_PAGE
    fields["total_count"]["covers_returned_count"] = (
        total_valid and count_valid and total >= count
    )
    if count_valid:
        if count != len(rows) or count > REQUESTED_PER_PAGE:
            mismatch.append("count")
    if total_valid and count_valid and total < count:
        mismatch.append("total_count")

    report["pagination_fields"] = fields
    if invalid:
        report["reason_code"] = "PAGINATION_METADATA_INVALID"
        report["invalid_fields"] = invalid
        return report
    if mismatch:
        report["reason_code"] = "PAGINATION_METADATA_MISMATCH"
        report["mismatched_fields"] = mismatch
        return report
    report["status"] = "DIAGNOSTIC_COMPLETE"
    report["reason_code"] = "FIRST_PAGE_METADATA_VALID"
    return report


def require_owner_confirmation() -> None:
    if os.environ.get("INPUT_CONFIRM_ONE_TIME_READ_ONLY") != "true":
        raise BillingHistoryError("DISTINCT_OWNER_CONFIRMATION_REQUIRED")


def _require_single_dispatch() -> None:
    require_owner_confirmation()
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise BillingHistoryError("MAIN_BRANCH_REQUIRED")
    if os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        raise BillingHistoryError("MANUAL_DISPATCH_REQUIRED")
    if os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
        raise BillingHistoryError("RERUN_FORBIDDEN")
    run_id = os.environ.get("GITHUB_RUN_ID")
    repo = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    api = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    if not run_id or repo != "qookey109-pixel/crypto-autopilot" or not token:
        raise BillingHistoryError("GITHUB_RUN_METADATA_INVALID")
    url = f"{api}/repos/{repo}/actions/workflows/{WORKFLOW_FILE}/runs?branch=main&event=workflow_dispatch&per_page=100"
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.build_opener(_NoRedirect).open(request, timeout=20) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise BillingHistoryError("GITHUB_HISTORY_RESPONSE_TOO_LARGE")
        history = json.loads(raw)
    except BillingHistoryError:
        raise
    except Exception:
        raise BillingHistoryError("GITHUB_HISTORY_REQUEST_FAILED") from None
    runs = history.get("workflow_runs") if isinstance(history, dict) else None
    if (
        not isinstance(runs, list)
        or type(history.get("total_count")) is not int
        or history["total_count"] != 1
        or len(runs) != 1
        or not isinstance(runs[0], dict)
        or str(runs[0].get("id")) != run_id
        or runs[0].get("run_attempt") != 1
    ):
        raise BillingHistoryError("ONE_TIME_AUTHORITY_ALREADY_USED_OR_AMBIGUOUS")


def execute_one_request(*, fetch_payload, observed_at: datetime) -> dict[str, Any]:
    report = diagnose_payload({}, observed_at=observed_at)
    report["reason_code"] = "NOT_EXECUTED"
    attempted = 0
    try:
        _require_single_dispatch()
        account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
        token = os.environ.get("CLOUDFLARE_BILLING_READONLY_API_TOKEN", "")
        if not account or not token:
            raise BillingHistoryError("MISSING_BILLING_READ_ONLY_CREDENTIAL")
        attempted = 1
        payload = fetch_payload(account, token, REQUESTED_PAGE, REQUESTED_PER_PAGE)
        report = diagnose_payload(payload, observed_at=observed_at)
    except BillingHistoryError as exc:
        report = diagnose_payload({}, observed_at=observed_at)
        report["reason_code"] = str(exc)
    except Exception:
        report = diagnose_payload({}, observed_at=observed_at)
        report["reason_code"] = "REQUEST_OR_PARSE_FAILED"
    report["cloudflare_http_requests_performed"] = attempted
    return report


def _fetch_payload(account: str, token: str, page: int, per_page: int) -> dict[str, Any]:
    query = urllib.parse.urlencode({"page": page, "per_page": per_page})
    url = (
        "https://api.cloudflare.com/client/v4/accounts/"
        f"{urllib.parse.quote(account, safe='')}/billing/history?{query}"
    )
    return _request_json(url, token=token)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    report = execute_one_request(fetch_payload=_fetch_payload, observed_at=datetime.now(UTC))
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\\n", encoding="utf-8")
    print(f"Billing metadata diagnostic: {report['status']} ({report['reason_code']})")
    return 0 if report["status"] == "DIAGNOSTIC_COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
