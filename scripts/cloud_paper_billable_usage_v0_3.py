"""One-shot read-only Cloudflare billable-usage V0.3 using the self-serve V1 route."""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

AUTHORITY = "cloud-paper-billable-usage-v0.3"
WORKFLOW_FILE = "cloud-paper-billable-usage-v0-3.yml"
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


def summarize_usage(payload: object, *, observed_at: datetime) -> dict[str, Any]:
    """Redact identities and summarize current billing-cycle usage rows."""
    if observed_at.tzinfo is None:
        raise UsageError("OBSERVATION_TIMEZONE_MISSING")
    base: dict[str, Any] = {
        "schema": "qookey-cloud-paper-billable-usage-report-v0.3",
        "authority": AUTHORITY,
        "status": "REVIEW_REQUIRED",
        "reason_code": "NOT_EVALUATED",
        "observed_at_utc": observed_at.astimezone(UTC).isoformat(),
        "query_scope": "CURRENT_BILLING_PERIOD_NO_DATE_FILTER",
        "provider_refresh_cadence": "DAILY_PROVIDER_DATA_MAY_LAG",
        "response_row_count": None,
        "rows": [],
        "all_rows_have_billed_cost": None,
        "reported_billed_cost_total": None,
        "reported_billing_currency": None,
        "usage_data_scope": "USAGE_BASED_CHARGES_ONLY",
        "fixed_subscription_charges_included": False,
        "complete_account_usage_coverage": "UNKNOWN_UNTIL_REVIEWED",
        "zero_cost_conclusion": "UNKNOWN",
        "account_identity_persisted": False,
        "raw_response_persisted": False,
        "cloudflare_http_requests_performed": 0,
        "cloud_paper_activation": "REMAINS_DISABLED",
    }
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

    safe_rows: list[dict[str, Any]] = []
    all_costs = True
    currencies: set[str] = set()
    billed_total = 0.0
    for row in source_rows:
        if not isinstance(row, dict):
            base["reason_code"] = "USAGE_ROW_INVALID"
            return base
        period_start = _parse_time(row.get("ChargePeriodStart"), "CHARGE_PERIOD_START_INVALID")
        period_end = _parse_time(row.get("ChargePeriodEnd"), "CHARGE_PERIOD_END_INVALID")
        billing_start = _parse_time(row.get("BillingPeriodStart"), "BILLING_PERIOD_START_INVALID")
        service = row.get("ServiceName")
        if period_end <= period_start or billing_start > period_start:
            base["reason_code"] = "BILLING_PERIOD_INVALID"
            return base
        if not isinstance(service, str) or not service or len(service) > 128:
            base["reason_code"] = "SERVICE_NAME_INVALID"
            return base
        quantity = row.get("ConsumedQuantity")
        if quantity is not None and (
            isinstance(quantity, bool) or not isinstance(quantity, (int, float))
            or not math.isfinite(quantity) or quantity < 0
        ):
            base["reason_code"] = "CONSUMED_QUANTITY_INVALID"
            return base
        unit = row.get("ConsumedUnit")
        family = row.get("ServiceFamilyName")
        if unit is not None and (not isinstance(unit, str) or len(unit) > 64):
            base["reason_code"] = "CONSUMED_UNIT_INVALID"
            return base
        if family is not None and (not isinstance(family, str) or len(family) > 128):
            base["reason_code"] = "SERVICE_FAMILY_INVALID"
            return base

        amount = row.get("BilledCost")
        currency = row.get("BillingCurrency")
        if amount is None or currency is None:
            all_costs = False
            safe_amount = None
            safe_currency = None
        elif (
            isinstance(amount, bool) or not isinstance(amount, (int, float))
            or not math.isfinite(amount) or amount < 0
            or not isinstance(currency, str) or len(currency) != 3
        ):
            base["reason_code"] = "BILLED_COST_INVALID"
            return base
        else:
            safe_amount = amount
            safe_currency = currency
            billed_total += amount
            currencies.add(currency)

        safe_rows.append({
            "billing_period_start_utc": billing_start.isoformat(),
            "charge_period_start_utc": period_start.isoformat(),
            "charge_period_end_utc": period_end.isoformat(),
            "service_name": service,
            "service_family_name": family,
            "consumed_quantity": quantity,
            "consumed_unit": unit,
            "billed_cost": safe_amount,
            "billing_currency": safe_currency,
        })

    base["rows"] = safe_rows
    base["all_rows_have_billed_cost"] = all_costs
    if all_costs and len(currencies) == 1:
        base["reported_billed_cost_total"] = round(billed_total, 8)
        base["reported_billing_currency"] = next(iter(currencies))
    elif all_costs and len(currencies) > 1:
        base["reason_code"] = "MIXED_BILLING_CURRENCIES"
        return base

    base["status"] = "READY_FOR_REVIEW"
    base["reason_code"] = (
        "USAGE_ROWS_CAPTURED_COST_FIELDS_INCOMPLETE"
        if not all_costs
        else "USAGE_ROWS_CAPTURED_REVIEW_REQUIRED_FOR_SCOPE"
    )
    # This endpoint omits fixed subscription fees; daily updates may also lag.
    # Neither an empty response nor a zero usage subtotal establishes zero cost.
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
    except (
        urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
        OSError, json.JSONDecodeError,
    ):
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
        "User-Agent": "crypto-autopilot-cloud-paper-usage-audit/0.3",
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
        url = (
            "https://api.cloudflare.com/client/v4/accounts/"
            + urllib.parse.quote(account_id, safe="")
            + "/billable-usage"
        )
        payload = _request_json(url, token=api_token)
        report = summarize_usage(payload, observed_at=datetime.now(UTC))
    except UsageError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    report["cloudflare_http_requests_performed"] = 1
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
