"""Prepared bounded billing pagination successor; no network or execution entrypoint."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from scripts.cloud_paper_billing_history_v0_2 import (
    BillingHistoryError, _normalize_row, _safe_json_type,
)

MAX_PAGES = 10
MAX_ITEMS = 1000
PAGE_SIZE = 100


def _inspect(payload: object, expected: int, size: int) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise BillingHistoryError("CLOUDFLARE_RESPONSE_UNSUCCESSFUL")
    if payload.get("errors"):
        raise BillingHistoryError("CLOUDFLARE_RESPONSE_HAS_ERRORS")
    rows, info = payload.get("result"), payload.get("result_info")
    if not isinstance(rows, list) or not isinstance(info, dict):
        raise BillingHistoryError("BILLING_HISTORY_PAGE_MISSING")
    if len(rows) > size:
        raise BillingHistoryError("BILLING_HISTORY_PAGE_SIZE_EXCEEDED")
    for key in ("page", "per_page", "count", "total_count"):
        if key in info and (type(info[key]) is not int or info[key] < 0):
            raise BillingHistoryError("BILLING_HISTORY_PAGE_METADATA_INVALID")
    # Missing optional totals are supported; request/response identity remains required.
    if info.get("page") != expected or info.get("per_page") != size:
        raise BillingHistoryError("BILLING_HISTORY_PAGE_METADATA_MISMATCH")
    if "count" in info and info["count"] != len(rows):
        raise BillingHistoryError("BILLING_HISTORY_PAGE_COUNT_MISMATCH")
    if any(not isinstance(row, dict) for row in rows):
        raise BillingHistoryError("BILLING_HISTORY_ROW_INVALID")
    return rows


def summarize_pages(
    pages: list[object], *, observed_at: datetime, page_size: int = PAGE_SIZE,
    max_pages: int = MAX_PAGES, max_items: int = MAX_ITEMS,
) -> dict[str, Any]:
    if observed_at.tzinfo is None:
        raise BillingHistoryError("OBSERVATION_TIMEZONE_MISSING")
    if (type(page_size) is not int or not 1 <= page_size <= PAGE_SIZE
            or type(max_pages) is not int or not 1 <= max_pages <= MAX_PAGES
            or type(max_items) is not int or not 1 <= max_items <= MAX_ITEMS):
        raise BillingHistoryError("BILLING_HISTORY_LIMITS_INVALID")
    report: dict[str, Any] = {
        "schema": "qookey-cloud-paper-billing-pagination-report-v0.3",
        "stage": "PREPARED_NO_EXTERNAL_EXECUTION",
        "status": "REVIEW_REQUIRED", "reason_code": "BILLING_HISTORY_PAGES_INCOMPLETE",
        "observed_at_utc": observed_at.isoformat(),
        "page_count_read": 0, "returned_row_count": 0,
        "reported_total_count": None, "items": [],
        "traversal_terminal_seen": False, "complete_history_coverage": False,
        "atomic_snapshot_proven": False, "zero_cost_conclusion": "UNKNOWN",
        "cloud_paper_activation": "REMAINS_DISABLED",
        "pagination_metadata_diagnostics": [],
        "raw_response_persisted": False, "item_ids_persisted": False,
    }
    if not isinstance(pages, list) or not pages:
        report["reason_code"] = "BILLING_HISTORY_PAGE_MISSING"
        return report
    if len(pages) > max_pages:
        report["reason_code"] = "BILLING_HISTORY_PAGE_CAP_EXCEEDED"
        return report
    seen: set[str] = set()
    total: int | None = None
    terminal = False
    try:
        for number, payload in enumerate(pages, 1):
            if terminal:
                raise BillingHistoryError("BILLING_HISTORY_DATA_AFTER_TERMINAL")
            rows = _inspect(payload, number, page_size)
            info = payload["result_info"]
            current_total = info.get("total_count")
            if current_total is not None:
                if total is not None and current_total != total:
                    raise BillingHistoryError("BILLING_HISTORY_TOTAL_CHANGED_DURING_READ")
                total = current_total
                report["reported_total_count"] = total
            if report["returned_row_count"] + len(rows) > max_items:
                raise BillingHistoryError("BILLING_HISTORY_ITEM_CAP_EXCEEDED")
            normalized = []
            ids = set()
            for row in rows:
                item_id = row.get("id")
                if not isinstance(item_id, str) or not item_id or len(item_id) > 128:
                    raise BillingHistoryError("BILLING_HISTORY_ITEM_ID_INVALID")
                if item_id in seen or item_id in ids:
                    raise BillingHistoryError("DUPLICATE_BILLING_HISTORY_ITEM")
                ids.add(item_id)
                normalized.append(_normalize_row(row))
            proposed = report["returned_row_count"] + len(rows)
            if total is not None and (proposed > total or (not rows and proposed != total)):
                raise BillingHistoryError("BILLING_HISTORY_TOTAL_MISMATCH")
            seen.update(ids)
            report["items"].extend(normalized)
            report["returned_row_count"] = proposed
            report["page_count_read"] = number
            terminal = not rows
            report["traversal_terminal_seen"] = terminal
    except BillingHistoryError as exc:
        report["reason_code"] = str(exc)
        if str(exc) == "BILLING_HISTORY_PAGE_METADATA_INVALID":
            info = payload.get("result_info", {})
            report["pagination_metadata_diagnostics"] = [{
                "requested_page": number,
                "fields": {key: {"present": key in info,
                                 "type": _safe_json_type(info.get(key))}
                           for key in ("page", "per_page", "count", "total_count")},
            }]
        return report
    if terminal:
        report["status"] = "READY_FOR_BILLING_REVIEW"
        report["reason_code"] = "TERMINAL_PAGE_OBSERVED_RECONCILIATION_REQUIRED"
        # Traversal is bounded evidence, not an atomic account-history snapshot.
        report["complete_history_coverage"] = True
    elif len(pages) == max_pages:
        report["reason_code"] = "BILLING_HISTORY_PAGE_CAP_REACHED_WITHOUT_TERMINAL"
    return report


def collect_pages(fetch_page: Callable[[int, int], object], *,
                  observed_at: datetime, page_size: int = PAGE_SIZE,
                  max_pages: int = MAX_PAGES, max_items: int = MAX_ITEMS
                  ) -> tuple[list[object], dict[str, Any]]:
    # Validate ceilings before invoking any supplied fetch function.
    summarize_pages([], observed_at=observed_at, page_size=page_size,
                    max_pages=max_pages, max_items=max_items)
    pages: list[object] = []
    for number in range(1, max_pages + 1):
        pages.append(fetch_page(number, page_size))
        report = summarize_pages(pages, observed_at=observed_at, page_size=page_size,
                                 max_pages=max_pages, max_items=max_items)
        if report["status"] == "READY_FOR_BILLING_REVIEW":
            return pages, report
        if report["reason_code"] != "BILLING_HISTORY_PAGES_INCOMPLETE":
            return pages, report
    return pages, report
