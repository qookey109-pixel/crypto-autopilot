"""Pure, synthetic-only billing pagination metadata diagnostic for V0.4.

This module deliberately has no network client or execution entrypoint.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime


AUTHORITY = "cloud-paper-billing-metadata-diagnostic-v0.4"
REQUESTED_PAGE = 1
REQUESTED_PER_PAGE = 100


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


def diagnose_payload(
    payload: object, *, observed_at: datetime | None = None,
) -> dict[str, object]:
    """Return only fixed codes, field names, booleans, and JSON type labels."""
    observed = observed_at or datetime.now(UTC)
    if observed.tzinfo is None:
        raise ValueError("OBSERVATION_TIMEZONE_MISSING")

    report: dict[str, object] = {
        "schema": "qookey-cloud-paper-billing-metadata-diagnostic-report-v0.4",
        "authority": AUTHORITY,
        "stage": "SYNTHETIC_PARSER_ONLY",
        "status": "REVIEW_REQUIRED",
        "reason_code": "NOT_EVALUATED",
        "observed_at_utc": observed.astimezone(UTC).isoformat(),
        "requested_page": REQUESTED_PAGE,
        "requested_per_page": REQUESTED_PER_PAGE,
        "response_object": isinstance(payload, dict),
        "success_is_true": False,
        "errors_present": False,
        "result_is_array": False,
        "result_info_is_object": False,
        "pagination_fields": {},
        "mismatched_fields": [],
        "cloudflare_http_requests_performed": 0,
        "raw_response_persisted": False,
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

    result = payload.get("result")
    report["result_is_array"] = isinstance(result, list)
    if not isinstance(result, list):
        report["reason_code"] = "RESULT_NOT_ARRAY"
        return report

    info = payload.get("result_info")
    report["result_info_is_object"] = isinstance(info, dict)
    if not isinstance(info, dict):
        report["reason_code"] = "RESULT_INFO_NOT_OBJECT"
        return report

    metadata: dict[str, dict[str, object]] = {}
    mismatched: list[str] = []
    invalid: list[str] = []
    for field, expected in (
        ("page", REQUESTED_PAGE),
        ("per_page", REQUESTED_PER_PAGE),
    ):
        present = field in info
        value = info.get(field)
        valid_integer = type(value) is int and value >= 0
        matches = valid_integer and value == expected
        metadata[field] = {
            "present": present,
            "json_type": _json_type(value),
            "nonnegative_integer": valid_integer,
            "matches_requested": matches,
        }
        if not present or not valid_integer:
            invalid.append(field)
        elif not matches:
            mismatched.append(field)

    report["pagination_fields"] = metadata
    report["mismatched_fields"] = mismatched
    if invalid:
        report["reason_code"] = "PAGINATION_METADATA_INVALID"
        report["invalid_fields"] = invalid
        return report
    if mismatched:
        report["reason_code"] = "PAGINATION_METADATA_MISMATCH"
        return report

    report["status"] = "DIAGNOSTIC_COMPLETE"
    report["reason_code"] = "REQUEST_METADATA_MATCHED"
    return report


def report_is_value_free(report: dict[str, object]) -> bool:
    """Check serialized output shape for forbidden billing response values."""
    try:
        encoded = json.dumps(report, allow_nan=False)
    except (TypeError, ValueError):
        return False
    return (
        "amount" not in encoded
        and "invoice" not in encoded.lower()
        and "account_id" not in encoded.lower()
        and "items" not in encoded
        and "raw_response" in encoded
    )
