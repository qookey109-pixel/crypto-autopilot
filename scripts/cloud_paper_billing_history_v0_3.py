"""Separate one-time read-only billing successor; no product activation."""
from __future__ import annotations

import argparse
import json
import os
import urllib.parse
from datetime import UTC, datetime
from pathlib import Path

from scripts.cloud_paper_billing_history_v0_2 import BillingHistoryError, _request_json
from scripts.cloud_paper_billing_pagination_v0_3 import summarize_pages

AUTHORITY = "cloud-paper-billing-history-v0.3"
WORKFLOW_FILE = "cloud-paper-billing-history-v0-3.yml"
MAX_PAGES = 10
MAX_ITEMS = 1000
PAGE_SIZE = 100


def require_owner_confirmation() -> None:
    if os.environ.get("INPUT_CONFIRM_ONE_TIME_READ_ONLY") != "true":
        raise BillingHistoryError("DISTINCT_OWNER_CONFIRMATION_REQUIRED")


def require_single_run() -> None:
    import urllib.request
    from scripts.cloud_paper_billing_history_v0_2 import _NoRedirect

    require_owner_confirmation()
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
    if not run_id or repo != "qookey109-pixel/crypto-autopilot" or not token:
        raise BillingHistoryError("GITHUB_RUN_METADATA_INVALID")
    url = (
        f"https://api.github.com/repos/{repo}/actions/workflows/{WORKFLOW_FILE}/runs"
        "?branch=main&event=workflow_dispatch&per_page=100"
    )
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.build_opener(_NoRedirect).open(request, timeout=20) as response:
            raw = response.read(1048577)
        if len(raw) > 1048576:
            raise BillingHistoryError("GITHUB_HISTORY_RESPONSE_TOO_LARGE")
        payload = json.loads(raw)
    except BillingHistoryError:
        raise
    except Exception:
        raise BillingHistoryError("GITHUB_HISTORY_REQUEST_FAILED") from None
    runs = payload.get("workflow_runs") if isinstance(payload, dict) else None
    if (
        not isinstance(runs, list) or type(payload.get("total_count")) is not int
        or payload["total_count"] != 1 or len(runs) != 1
        or not isinstance(runs[0], dict) or str(runs[0].get("id")) != run_id
        or runs[0].get("run_attempt") != 1
    ):
        raise BillingHistoryError("ONE_TIME_AUTHORITY_ALREADY_USED_OR_AMBIGUOUS")


def collect_report(fetch_page, *, observed_at: datetime) -> dict[str, object]:
    pages: list[object] = []
    report = summarize_pages(pages, observed_at=observed_at)
    attempted = 0
    for page in range(1, MAX_PAGES + 1):
        attempted += 1
        try:
            payload = fetch_page(page, PAGE_SIZE)
            pages.append(payload)
            report = summarize_pages(pages, observed_at=observed_at)
        except Exception as exc:
            report["status"] = "REVIEW_REQUIRED"
            report["reason_code"] = (
                str(exc) if isinstance(exc, BillingHistoryError) else "REQUEST_OR_PARSE_FAILED"
            )
            report["bounded_traversal_complete"] = False
            report["complete_history_coverage"] = False
            report["coverage_basis"] = "INCOMPLETE"
            break
        if report["reason_code"] != "BILLING_HISTORY_PAGES_INCOMPLETE":
            break
    report["account_identity_persisted"] = False
    report["invoice_ids_or_urls_persisted"] = False
    report["descriptions_persisted"] = False
    report["authority"] = AUTHORITY
    report["stage"] = "ONE_TIME_READ_ONLY_EXECUTION"
    report["cloudflare_http_requests_performed"] = attempted
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    report = summarize_pages([], observed_at=datetime.now(UTC))
    report["authority"] = AUTHORITY
    report["cloudflare_http_requests_performed"] = 0
    try:
        require_single_run()
        account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
        token = os.environ.get("CLOUDFLARE_BILLING_READONLY_API_TOKEN", "")
        if not account or not token:
            raise BillingHistoryError("MISSING_BILLING_READ_ONLY_CREDENTIAL")

        def fetch_page(page: int, size: int):
            query = urllib.parse.urlencode({"page": page, "per_page": size})
            url = (
                "https://api.cloudflare.com/client/v4/accounts/"
                f"{urllib.parse.quote(account, safe='')}/billing/history?{query}"
            )
            return _request_json(url, token=token)

        report = collect_report(fetch_page, observed_at=datetime.now(UTC))
    except BillingHistoryError as exc:
        report["reason_code"] = str(exc)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Billing history status: {report['status']} ({report['reason_code']})")
    return 0 if report["status"] == "READY_FOR_BILLING_REVIEW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
