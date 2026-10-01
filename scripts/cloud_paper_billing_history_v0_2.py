"""One-time, bounded read-only Cloudflare account billing-history snapshot."""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

AUTHORITY = "cloud-paper-billing-history-v0.2"
WORKFLOW_FILE = "cloud-paper-billing-history-v0-2.yml"
PAGE_SIZE = 100
MAX_PAGES = 10
MAX_ITEMS = PAGE_SIZE * MAX_PAGES
MAX_RESPONSE_BYTES = 1_048_576
_CATEGORY = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")


class BillingHistoryError(ValueError):
    """Fixed safe error code; never includes response bodies or credentials."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _number(value: object, code: str, *, allow_negative: bool) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BillingHistoryError(code)
    if not math.isfinite(value) or (not allow_negative and value < 0):
        raise BillingHistoryError(code)
    return float(value)


def _category(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _CATEGORY.fullmatch(value):
        return "UNKNOWN"
    return value


def _occurred_month(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise BillingHistoryError("OCCURRED_AT_INVALID")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise BillingHistoryError("OCCURRED_AT_INVALID") from None
    if parsed.tzinfo is None:
        raise BillingHistoryError("OCCURRED_AT_TIMEZONE_MISSING")
    return parsed.astimezone(UTC).strftime("%Y-%m")


def _normalize_row(row: object) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise BillingHistoryError("BILLING_HISTORY_ROW_INVALID")
    currency = row.get("currency")
    if currency is not None and (
        not isinstance(currency, str) or not re.fullmatch(r"[A-Za-z]{3}", currency)
    ):
        raise BillingHistoryError("BILLING_CURRENCY_INVALID")
    return {
        "occurred_month_utc": _occurred_month(row.get("occurred_at")),
        "action": _category(row.get("action")),
        "type": _category(row.get("type")),
        "status": _category(row.get("status")),
        "currency": currency.upper() if isinstance(currency, str) else None,
        "amount": _number(row.get("amount"), "BILLING_AMOUNT_INVALID", allow_negative=True),
        "amount_to_pay": _number(
            row.get("amount_to_pay"), "AMOUNT_TO_PAY_INVALID", allow_negative=True
        ),
    }


def _safe_json_type(value: object) -> str:
    """Return a value-free JSON type label for bounded metadata diagnostics."""
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


def summarize_pages(
    pages: list[object], *, observed_at: datetime, page_size: int = PAGE_SIZE,
    max_items: int = MAX_ITEMS,
) -> dict[str, Any]:
    if observed_at.tzinfo is None:
        raise BillingHistoryError("OBSERVATION_TIMEZONE_MISSING")
    report: dict[str, Any] = {
        "schema": "qookey-cloud-paper-billing-history-report-v0.2",
        "authority": AUTHORITY,
        "status": "REVIEW_REQUIRED",
        "reason_code": "NOT_EVALUATED",
        "observed_at_utc": observed_at.astimezone(UTC).isoformat(),
        "query_scope": "ALL_AVAILABLE_ACCOUNT_BILLING_HISTORY_NO_STATUS_FILTER",
        "page_size_requested": page_size,
        "page_count_read": 0,
        "pagination_metadata_diagnostics": [],
        "reported_total_count": None,
        "returned_row_count": 0,
        "complete_history_coverage": False,
        "items": [],
        "account_identity_persisted": False,
        "item_ids_persisted": False,
        "invoice_ids_or_urls_persisted": False,
        "descriptions_persisted": False,
        "raw_response_persisted": False,
        "cloudflare_http_requests_performed": 0,
        "zero_cost_conclusion": "UNKNOWN",
        "cloud_paper_activation": "REMAINS_DISABLED",
    }
    if not isinstance(pages, list) or not pages:
        report["reason_code"] = "BILLING_HISTORY_PAGE_MISSING"
        return report
    normalized_pages: list[tuple[int, int, int, list[dict[str, Any]], list[str]]] = []
    total: int | None = None
    seen_ids: set[str] = set()
    for expected_page, payload in enumerate(pages, 1):
        if not isinstance(payload, dict) or payload.get("success") is not True:
            report["reason_code"] = "CLOUDFLARE_RESPONSE_UNSUCCESSFUL"
            return report
        if payload.get("errors"):
            report["reason_code"] = "CLOUDFLARE_RESPONSE_HAS_ERRORS"
            return report
        rows, info = payload.get("result"), payload.get("result_info")
        if not isinstance(rows, list) or not isinstance(info, dict):
            report["reason_code"] = "BILLING_HISTORY_PAGE_MISSING"
            return report
        count, page, actual_size, reported_total = (
            info.get("count"), info.get("page"), info.get("per_page"), info.get("total_count")
        )
        values = {
            "count": count, "page": page, "per_page": actual_size,
            "total_count": reported_total,
        }
        invalid_metadata = any(
            type(value) is not int or value < 0 for value in values.values()
        )
        if invalid_metadata:
            report["pagination_metadata_diagnostics"].append({
                "requested_page": expected_page,
                "fields": {
                    name: {
                        "present": name in info,
                        "type": _safe_json_type(value),
                        "nonnegative_integer": type(value) is int and value >= 0,
                    }
                    for name, value in values.items()
                },
            })
            report["reason_code"] = "BILLING_HISTORY_PAGE_METADATA_INVALID"
            return report
        if page != expected_page or count != len(rows) or actual_size <= 0:
            report["reason_code"] = "BILLING_HISTORY_PAGE_METADATA_MISMATCH"
            return report
        if total is None:
            total = reported_total
        elif total != reported_total:
            report["reason_code"] = "BILLING_HISTORY_TOTAL_CHANGED_DURING_READ"
            return report
        expected_count = min(actual_size, max(0, total - (page - 1) * actual_size))
        if count != expected_count:
            report["reason_code"] = "BILLING_HISTORY_PAGE_COUNT_MISMATCH"
            return report
        normalized: list[dict[str, Any]] = []
        page_ids: list[str] = []
        for row in rows:
            normalized.append(_normalize_row(row))
            item_id = row.get("id")
            if item_id is not None:
                if not isinstance(item_id, str) or not item_id or len(item_id) > 128:
                    report["reason_code"] = "BILLING_HISTORY_ITEM_ID_INVALID"
                    return report
                if item_id in seen_ids:
                    report["reason_code"] = "DUPLICATE_BILLING_HISTORY_ITEM"
                    return report
                seen_ids.add(item_id)
                page_ids.append(item_id)
        normalized_pages.append((page, count, actual_size, normalized, page_ids))

    returned = sum(x[1] for x in normalized_pages)
    actual_page_size = normalized_pages[0][2]
    if any(x[2] != actual_page_size for x in normalized_pages):
        report["reason_code"] = "BILLING_HISTORY_PAGE_SIZE_CHANGED"
        return report
    required_pages = max(1, math.ceil((total or 0) / actual_page_size))
    cap_pages = max(1, max_items // actual_page_size)
    report["page_count_read"] = len(normalized_pages)
    report["reported_total_count"] = total
    report["returned_row_count"] = returned
    report["items"] = [item for page in normalized_pages for item in page[3]]
    report["complete_history_coverage"] = (
        returned == total and len(normalized_pages) == required_pages
    )
    if total is not None and total > max_items:
        report["reason_code"] = "BILLING_HISTORY_ITEM_CAP_EXCEEDED"
    elif len(normalized_pages) < required_pages:
        report["reason_code"] = "BILLING_HISTORY_PAGES_INCOMPLETE"
    elif len(normalized_pages) > cap_pages:
        report["reason_code"] = "BILLING_HISTORY_PAGE_CAP_EXCEEDED"
    elif not report["complete_history_coverage"]:
        report["reason_code"] = "BILLING_HISTORY_COVERAGE_INCOMPLETE"
    else:
        report["status"] = "READY_FOR_BILLING_REVIEW"
        report["reason_code"] = "COMPLETE_HISTORY_REQUIRES_COST_RECONCILIATION"
    return report


def _request_json(url: str, *, token: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "crypto-autopilot-billing-history-audit/0.2",
    }, method="GET")
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=20) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise BillingHistoryError(f"CLOUDFLARE_HTTP_{exc.code}") from None
    except (urllib.error.URLError, TimeoutError):
        raise BillingHistoryError("CLOUDFLARE_REQUEST_FAILED") from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise BillingHistoryError("CLOUDFLARE_RESPONSE_TOO_LARGE")
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise BillingHistoryError("CLOUDFLARE_RESPONSE_INVALID") from None
    if not isinstance(payload, dict):
        raise BillingHistoryError("CLOUDFLARE_RESPONSE_INVALID")
    return payload


def _require_single_run() -> None:
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise BillingHistoryError("MAIN_BRANCH_REQUIRED")
    if os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        raise BillingHistoryError("MANUAL_DISPATCH_REQUIRED")
    if os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
        raise BillingHistoryError("RERUN_FORBIDDEN")
    run_id, repo, token = (
        os.environ.get("GITHUB_RUN_ID"), os.environ.get("GITHUB_REPOSITORY"),
        os.environ.get("GITHUB_TOKEN"),
    )
    api = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    if not run_id or not repo or not token:
        raise BillingHistoryError("GITHUB_RUN_METADATA_MISSING")
    url = f"{api}/repos/{repo}/actions/workflows/{WORKFLOW_FILE}/runs?branch=main&event=workflow_dispatch&per_page=100"
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        raise BillingHistoryError("GITHUB_HISTORY_REQUEST_FAILED") from None
    runs = payload.get("workflow_runs") if isinstance(payload, dict) else None
    if not isinstance(runs, list) or payload.get("total_count") != 1 or len(runs) != 1:
        raise BillingHistoryError("ONE_TIME_AUTHORITY_ALREADY_USED_OR_AMBIGUOUS")
    run = runs[0]
    if not isinstance(run, dict) or str(run.get("id")) != run_id or run.get("run_attempt") != 1:
        raise BillingHistoryError("CURRENT_RUN_NOT_UNIQUE_FIRST_ATTEMPT")


def collect_history(
    account_id: str, token: str, *, fetch_page, max_pages: int = MAX_PAGES,
    page_size: int = PAGE_SIZE,
) -> tuple[list[object], int]:
    pages: list[object] = []
    total: int | None = None
    actual_size: int | None = None
    for page in range(1, max_pages + 1):
        payload = fetch_page(page, page_size)
        pages.append(payload)
        if not isinstance(payload, dict) or not isinstance(payload.get("result_info"), dict):
            break
        info = payload["result_info"]
        count, current_page, current_size, current_total = (
            info.get("count"), info.get("page"), info.get("per_page"), info.get("total_count")
        )
        if any(type(x) is not int or x < 0 for x in (count, current_page, current_size, current_total)):
            break
        if current_page != page or count != len(payload.get("result", [])) or current_size <= 0:
            break
        if total is None:
            total, actual_size = current_total, current_size
        elif total != current_total or actual_size != current_size:
            break
        if count < current_size or page * current_size >= current_total:
            break
    return pages, len(pages)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    request_count = 0
    try:
        account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        token = os.environ.get("CLOUDFLARE_BILLING_READONLY_API_TOKEN")
        if not account_id or not token:
            raise BillingHistoryError("MISSING_BILLING_READ_ONLY_CREDENTIAL")
        _require_single_run()

        def fetch_page(page: int, page_size: int):
            nonlocal request_count
            if request_count >= MAX_PAGES:
                raise BillingHistoryError("BILLING_HISTORY_REQUEST_CAP_EXCEEDED")
            query = urllib.parse.urlencode({"page": page, "per_page": page_size})
            url = f"https://api.cloudflare.com/client/v4/accounts/{urllib.parse.quote(account_id, safe='')}/billing/history?{query}"
            request_count += 1
            return _request_json(url, token=token)

        pages, _ = collect_history(account_id, token, fetch_page=fetch_page)
        report = summarize_pages(pages, observed_at=datetime.now(UTC))
        report["cloudflare_http_requests_performed"] = request_count
    except BillingHistoryError as exc:
        report = {
            "schema": "qookey-cloud-paper-billing-history-report-v0.2",
            "authority": AUTHORITY,
            "status": "REVIEW_REQUIRED",
            "reason_code": str(exc),
            "observed_at_utc": datetime.now(UTC).isoformat(),
            "page_count_read": 0,
            "pagination_metadata_diagnostics": [],
            "returned_row_count": 0,
            "complete_history_coverage": False,
            "items": [],
            "account_identity_persisted": False,
            "item_ids_persisted": False,
            "invoice_ids_or_urls_persisted": False,
            "descriptions_persisted": False,
            "raw_response_persisted": False,
            "cloudflare_http_requests_performed": request_count,
            "zero_cost_conclusion": "UNKNOWN",
            "cloud_paper_activation": "REMAINS_DISABLED",
        }
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Billing history review required: {report['reason_code']}")
        return 1
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Billing history status: {report['status']} ({report['reason_code']})")
    return 0 if report["status"] == "READY_FOR_BILLING_REVIEW" else 1


if __name__ == "__main__":
    sys.exit(main())
