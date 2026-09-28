"""One-time, read-only Cloudflare subscription snapshot for Cloud Paper cost review."""
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

AUTHORITY = "cloud-paper-billing-evidence-v0.1"
WORKFLOW_FILE = "cloud-paper-billing-evidence-v0-1.yml"
PAGE_SIZE = 20


class BillingEvidenceError(ValueError):
    """Fixed safe error code; never includes response bodies or credentials."""


def summarize_subscriptions(payload: object, *, observed_at: datetime) -> dict[str, Any]:
    """Validate one complete subscription page and emit only non-identifying fields."""
    if observed_at.tzinfo is None:
        raise BillingEvidenceError("OBSERVATION_TIMEZONE_MISSING")
    observed = observed_at.astimezone(UTC)
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise BillingEvidenceError("CLOUDFLARE_RESPONSE_UNSUCCESSFUL")
    if payload.get("errors"):
        raise BillingEvidenceError("CLOUDFLARE_RESPONSE_HAS_ERRORS")
    results = payload.get("result")
    info = payload.get("result_info")
    if not isinstance(results, list) or not isinstance(info, dict):
        raise BillingEvidenceError("SUBSCRIPTION_PAGE_MISSING")
    count = info.get("count")
    total = info.get("total_count")
    page = info.get("page")
    per_page = info.get("per_page")
    if any(type(value) is not int or value < 0 for value in (count, total, page, per_page)):
        raise BillingEvidenceError("SUBSCRIPTION_PAGE_METADATA_INVALID")
    if page != 1 or count != len(results) or total != len(results) or per_page < count:
        raise BillingEvidenceError("SUBSCRIPTION_PAGE_INCOMPLETE")
    if count > PAGE_SIZE:
        raise BillingEvidenceError("SUBSCRIPTION_PAGE_LIMIT_EXCEEDED")

    normalized = []
    for item in results:
        if not isinstance(item, dict):
            raise BillingEvidenceError("SUBSCRIPTION_ROW_INVALID")
        rate_plan = item.get("rate_plan")
        if not isinstance(rate_plan, dict):
            raise BillingEvidenceError("SUBSCRIPTION_RATE_PLAN_MISSING")
        plan_id = rate_plan.get("id")
        state = item.get("state")
        currency = item.get("currency")
        price = item.get("price")
        if not isinstance(plan_id, str) or not plan_id:
            raise BillingEvidenceError("SUBSCRIPTION_PLAN_ID_MISSING")
        if not isinstance(state, str) or not state:
            raise BillingEvidenceError("SUBSCRIPTION_STATE_MISSING")
        if not isinstance(currency, str) or not currency:
            raise BillingEvidenceError("SUBSCRIPTION_CURRENCY_MISSING")
        if isinstance(price, bool) or not isinstance(price, (int, float)):
            raise BillingEvidenceError("SUBSCRIPTION_PRICE_MISSING")
        if not math.isfinite(price) or price < 0:
            raise BillingEvidenceError("SUBSCRIPTION_PRICE_INVALID")
        normalized.append({
            "rate_plan_id": plan_id,
            "state": state,
            "price_usd": float(price),
            "currency": currency,
        })

    normalized.sort(key=lambda row: (
        row["rate_plan_id"], row["state"], row["currency"], row["price_usd"],
    ))
    return {
        "schema": "qookey-cloud-paper-billing-evidence-report-v0.1",
        "authority": AUTHORITY,
        "status": "READY_FOR_BILLING_REVIEW",
        "observed_at_utc": observed.isoformat(),
        "account_id_persisted": False,
        "subscription_ids_persisted": False,
        "raw_response_persisted": False,
        "subscription_page": {"page": 1, "count": count, "total_count": total},
        "subscriptions": normalized,
        "listed_subscription_price_total_usd": round(
            sum(row["price_usd"] for row in normalized), 6,
        ),
        "zero_cost_conclusion": "NOT_PROVEN_BY_SUBSCRIPTION_SNAPSHOT",
        "activation": "REMAINS_DISABLED",
        "limitations": [
            "This endpoint reports subscriptions and their listed prices, not invoices or all metered charges.",
            "A complete subscription page does not prove all account products, external writers, or usage are covered.",
            "Compare with a fresh account-wide usage report and billing records before any cost conclusion.",
        ],
    }


def _request_json(url: str, *, token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "crypto-autopilot-cloud-paper-billing-audit/0.1",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            parsed = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise BillingEvidenceError(f"CLOUDFLARE_HTTP_{exc.code}") from None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        raise BillingEvidenceError("CLOUDFLARE_REQUEST_FAILED") from None
    if not isinstance(parsed, dict):
        raise BillingEvidenceError("CLOUDFLARE_RESPONSE_INVALID")
    return parsed


def _require_single_run() -> None:
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise BillingEvidenceError("MAIN_BRANCH_REQUIRED")
    if os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
        raise BillingEvidenceError("RERUN_FORBIDDEN")
    run_id = os.environ.get("GITHUB_RUN_ID")
    repo = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    api = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    if not run_id or not repo or not token:
        raise BillingEvidenceError("GITHUB_RUN_METADATA_MISSING")
    url = (
        f"{api}/repos/{repo}/actions/workflows/{WORKFLOW_FILE}/runs"
        "?branch=main&event=workflow_dispatch&per_page=100"
    )
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        raise BillingEvidenceError("GITHUB_HISTORY_REQUEST_FAILED") from None
    runs = payload.get("workflow_runs") if isinstance(payload, dict) else None
    if not isinstance(runs, list) or payload.get("total_count") != 1 or len(runs) != 1:
        raise BillingEvidenceError("ONE_TIME_AUTHORITY_ALREADY_USED_OR_AMBIGUOUS")
    run = runs[0]
    if not isinstance(run, dict) or str(run.get("id")) != run_id or run.get("run_attempt") != 1:
        raise BillingEvidenceError("CURRENT_RUN_NOT_UNIQUE_FIRST_ATTEMPT")


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
            raise BillingEvidenceError("MISSING_BILLING_READ_ONLY_CREDENTIAL")
        _require_single_run()
        url = (
            "https://api.cloudflare.com/client/v4/accounts/"
            f"{urllib.parse.quote(account_id, safe='')}/subscriptions?page=1&per_page={PAGE_SIZE}"
        )
        payload = _request_json(url, token=api_token)
        report = summarize_subscriptions(payload, observed_at=datetime.now(UTC))
    except BillingEvidenceError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
