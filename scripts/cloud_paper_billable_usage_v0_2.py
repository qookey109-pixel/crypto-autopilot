"""One-time bounded read-only Cloudflare billable-usage diagnostic V0.2."""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

AUTHORITY = "cloud-paper-billable-usage-v0.2"
WORKFLOW_FILE = "cloud-paper-billable-usage-v0-2.yml"
MAX_RESPONSE_BYTES = 1_048_576
MAX_REPORT_ROWS = 500


class UsageError(ValueError):
    """Fixed safe error code; never includes response bodies or credentials."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _parse_time(value: object, code: str) -> datetime:
    if not isinstance(value, str):
        raise UsageError(code)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise UsageError(code) from None
    if parsed.tzinfo is None:
        raise UsageError(code)
    return parsed.astimezone(UTC)


def summarize_usage(
    payload: object, *, observed_at: datetime, window_start: date, window_end: date,
) -> dict[str, Any]:
    """Validate rows, redact account identity, and preserve unknown cost/coverage."""
    if observed_at.tzinfo is None:
        raise UsageError("OBSERVATION_TIMEZONE_MISSING")
    observed = observed_at.astimezone(UTC)
    base: dict[str, Any] = {
        "schema": "qookey-cloud-paper-billable-usage-report-v0.2",
        "authority": AUTHORITY,
        "status": "REVIEW_REQUIRED",
        "reason_code": "NOT_EVALUATED",
        "observed_at_utc": observed.isoformat(),
        "query_window_utc": {
            "from": window_start.isoformat(),
            "to": window_end.isoformat(),
        },
        "response_row_count": None,
        "rows": [],
        "coverage_completeness": "UNKNOWN_ENDPOINT_DOES_NOT_PROVE_ALL_PRODUCTS_OR_WRITERS",
        "cost_fields_present_for_all_rows": None,
        "reported_cost_total": None,
        "reported_cost_currency": None,
        "zero_cost_conclusion": "UNKNOWN",
        "account_id_persisted": False,
        "billing_account_fields_persisted": False,
        "raw_response_persisted": False,
        "cloudflare_http_requests_performed": 0,
        "cloud_paper_activation": "REMAINS_DISABLED",
    }
    if window_end < window_start or (window_end - window_start).days > 30:
        base["reason_code"] = "QUERY_WINDOW_INVALID"
        return base
    if not isinstance(payload, dict) or payload.get("success") is not True:
        base["reason_code"] = "CLOUDFLARE_RESPONSE_UNSUCCESSFUL"
        return base
    if payload.get("errors"):
        base["reason_code"] = "CLOUDFLARE_RESPONSE_HAS_ERRORS"
        return base
    source_rows = payload.get("result")
    if not isinstance(source_rows, list):
        base["reason_code"] = "USAGE_ROWS_MISSING"
        return base
    base["response_row_count"] = len(source_rows)
    if len(source_rows) > MAX_REPORT_ROWS:
        base["reason_code"] = "USAGE_ROW_LIMIT_EXCEEDED"
        return base
    if not source_rows:
        base["reason_code"] = "EMPTY_USAGE_RESPONSE_NOT_ZERO"
        return base

    window_stop = window_end + timedelta(days=1)
    safe_rows: list[dict[str, Any]] = []
    all_costs = True
    currencies: set[str] = set()
    cost_total = 0.0
    for row in source_rows:
        if not isinstance(row, dict):
            base["reason_code"] = "USAGE_ROW_INVALID"
            return base
        period_start = _parse_time(row.get("ChargePeriodStart"), "CHARGE_PERIOD_START_INVALID")
        period_end = _parse_time(row.get("ChargePeriodEnd"), "CHARGE_PERIOD_END_INVALID")
        metric = row.get("x_BillableMetricId")
        unit = row.get("ConsumedUnit")
        quantity = row.get("ConsumedQuantity")
        if period_end <= period_start:
            base["reason_code"] = "CHARGE_PERIOD_INVALID"
            return base
        if (period_start.date() < window_start or period_start.date() >= window_stop
                or period_end.date() > window_stop):
            base["reason_code"] = "CHARGE_PERIOD_OUTSIDE_QUERY_WINDOW"
            return base
        if not isinstance(metric, str) or not metric or len(metric) > 128:
            base["reason_code"] = "BILLABLE_METRIC_ID_INVALID"
            return base
        if not isinstance(unit, str) or not unit or len(unit) > 64:
            base["reason_code"] = "CONSUMED_UNIT_INVALID"
            return base
        if (isinstance(quantity, bool) or not isinstance(quantity, (int, float))
                or not math.isfinite(quantity) or quantity < 0):
            base["reason_code"] = "CONSUMED_QUANTITY_INVALID"
            return base
        safe_row: dict[str, Any] = {
            "charge_period_start_utc": period_start.isoformat(),
            "charge_period_end_utc": period_end.isoformat(),
            "billable_metric_id": metric,
            "consumed_quantity": quantity,
            "consumed_unit": unit,
        }
        amount = row.get("BilledCost")
        currency = row.get("BillingCurrency")
        if amount is None or currency is None:
            all_costs = False
            safe_row["billed_cost"] = None
            safe_row["billing_currency"] = None
        elif (isinstance(amount, bool) or not isinstance(amount, (int, float))
              or not math.isfinite(amount) or amount < 0
              or not isinstance(currency, str) or len(currency) != 3):
            base["reason_code"] = "BILLED_COST_INVALID"
            return base
        else:
            safe_row["billed_cost"] = amount
            safe_row["billing_currency"] = currency
            cost_total += amount
            currencies.add(currency)
        safe_rows.append(safe_row)

    base["rows"] = safe_rows
    base["cost_fields_present_for_all_rows"] = all_costs
    if all_costs and len(currencies) == 1:
        base["reported_cost_total"] = round(cost_total, 8)
        base["reported_cost_currency"] = next(iter(currencies))
    elif all_costs and len(currencies) > 1:
        base["reason_code"] = "MIXED_BILLING_CURRENCIES"
        return base
    base["status"] = "READY_FOR_REVIEW"
    base["reason_code"] = (
        "USAGE_ROWS_CAPTURED_COST_FIELDS_INCOMPLETE"
        if not all_costs
        else "USAGE_ROWS_CAPTURED_REVIEW_REQUIRED_FOR_COVERAGE"
    )
    # The Alpha/Restricted API documents that cost fields may be absent until
    # billing integration is complete; this cannot prove account-wide zero cost.
    base["zero_cost_conclusion"] = "UNKNOWN"
    return base


def _require_single_run() -> None:
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise UsageError("MAIN_BRANCH_REQUIRED")
    if os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        raise UsageError("MANUAL_DISPATCH_REQUIRED")
    if os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
        raise UsageError("RERUN_FORBIDDEN")
    run_id = os.environ.get("GITHUB_RUN_ID")
    repo = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    api = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    if not run_id or not repo or not token:
        raise UsageError("GITHUB_RUN_METADATA_MISSING")
    url = (
        api + "/repos/" + repo + "/actions/workflows/" + WORKFLOW_FILE + "/runs"
        "?branch=main&event=workflow_dispatch&per_page=100"
    )
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        raise UsageError("GITHUB_HISTORY_REQUEST_FAILED") from None
    runs = payload.get("workflow_runs") if isinstance(payload, dict) else None
    if not isinstance(runs, list) or payload.get("total_count") != 1 or len(runs) != 1:
        raise UsageError("ONE_TIME_AUTHORITY_ALREADY_USED_OR_AMBIGUOUS")
    run = runs[0]
    if not isinstance(run, dict) or str(run.get("id")) != run_id or run.get("run_attempt") != 1:
        raise UsageError("CURRENT_RUN_NOT_UNIQUE_FIRST_ATTEMPT")


def _request_json(url: str, *, token: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "Authorization": "Bearer " + token,
        "User-Agent": "crypto-autopilot-cloud-paper-usage-audit/0.2",
    })
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=20) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise UsageError("CLOUDFLARE_HTTP_" + str(exc.code)) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise UsageError("CLOUDFLARE_REQUEST_FAILED") from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise UsageError("CLOUDFLARE_RESPONSE_TOO_LARGE")
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise UsageError("CLOUDFLARE_RESPONSE_INVALID") from None
    if not isinstance(payload, dict):
        raise UsageError("CLOUDFLARE_RESPONSE_INVALID")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        api_token = os.environ.get("CLOUDFLARE_BILLING_READONLY_API_TOKEN")
        if not account_id or not api_token:
            raise UsageError("MISSING_BILLING_READ_ONLY_CREDENTIAL")
        _require_single_run()
        today = datetime.now(UTC).date()
        start = today.replace(day=1)
        query = urllib.parse.urlencode({"from": start.isoformat(), "to": today.isoformat()})
        url = (
            "https://api.cloudflare.com/client/v4/accounts/"
            + urllib.parse.quote(account_id, safe="")
            + "/billable/usage?"
            + query
        )
        payload = _request_json(url, token=api_token)
        report = summarize_usage(
            payload, observed_at=datetime.now(UTC), window_start=start, window_end=today,
        )
    except UsageError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    report["cloudflare_http_requests_performed"] = 1
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
