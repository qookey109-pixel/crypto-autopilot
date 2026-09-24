"""Bounded GitHub-only maintenance; no provider, storage or model clients.

Executed on GitHub-hosted runners only. Pure projection functions are usable by
cloud CI with synthetic data. The GitHub adapter never consumes PR code/logs.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from crypto_autopilot.research.automation_health import (
    evaluate_workflow, expectation_from_config, parse_utc,
)

REPOSITORY = "qookey109-pixel/crypto-autopilot"
POLICY = "config/cloud_project_maintenance_v0_1.json"
RECEIPT = "research/receipts/2026-09-25-cloud-project-maintenance-v0-1.json"
HEALTH = ".github/workflows/research-automation-health-v0-2.yml"
TARGETS = ("CURRENT_STATUS.md", "docs/PROJECT_CONTINUATION_RUNBOOK.md")
PREFIX = "codex/cloud-maintenance-"
BEGIN = "<!-- cloud-maintenance:v0.1:begin -->"
END = "<!-- cloud-maintenance:v0.1:end -->"
MESSAGE = "docs: refresh cloud maintenance evidence v0.1"
SCHEMA = "cloud-project-maintenance-v0.1"
MAX_PAGES = 10


class Stop(ValueError):
    """A safe, fixed status code; never include API response bodies or tokens."""


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                                     separators=(",", ":")).encode()).hexdigest()


def require(condition, code):
    if not condition:
        raise Stop(code)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Stop("UNKNOWN_REDIRECT")


class GitHub:
    def __init__(self, token, *, writable=False):
        require(bool(token), "BLOCKED_PERMISSION")
        self.token = token
        self.writable = writable
        self.coverage = []

    def request(self, method, path, payload=None, *, missing_ok=False):
        require(path.startswith("/") and "://" not in path and ".." not in path,
                "INVALID_API_PATH")
        require(method == "GET" or self.writable, "WRITE_NOT_AUTHORIZED")
        url = f"https://api.github.com/repos/{REPOSITORY}{path}"
        request = Request(url, method=method,
                          data=None if payload is None else json.dumps(payload).encode(),
                          headers={"Authorization": f"Bearer {self.token}",
                                   "Accept": "application/vnd.github+json",
                                   "Content-Type": "application/json",
                                   "X-GitHub-Api-Version": "2022-11-28",
                                   "User-Agent": "qookey-cloud-maintenance-v0.1"})
        try:
            with build_opener(NoRedirect).open(request, timeout=20) as response:
                body = response.read(4_000_001)
                require(len(body) <= 4_000_000, "UNKNOWN_RESPONSE_TOO_LARGE")
                return json.loads(body) if body else {}
        except HTTPError as exc:
            if exc.code == 404 and missing_ok:
                return None
            raise Stop("BLOCKED_PERMISSION" if exc.code in {401, 403} else
                       "UNKNOWN_RATE_LIMIT" if exc.code == 429 else "UNKNOWN_HTTP") from None
        except (URLError, TimeoutError, OSError, json.JSONDecodeError):
            raise Stop("UNKNOWN_TRANSPORT") from None

    def pages(self, path, key=None, params=None):
        result, seen, total = [], set(), None
        for page in range(1, MAX_PAGES + 1):
            query = urlencode({**(params or {}), "per_page": 100, "page": page})
            data = self.request("GET", f"{path}?{query}")
            rows = data.get(key) if key else data
            require(isinstance(rows, list), "UNKNOWN_MALFORMED_PAGE")
            if key:
                count = data.get("total_count")
                require(type(count) is int and count >= 0, "UNKNOWN_TOTAL")
                if total is None:
                    total = count
                require(count == total, "UNKNOWN_PAGINATION_CHANGED")
            for row in rows:
                require(isinstance(row, dict), "UNKNOWN_MALFORMED_ROW")
                identifier = row.get("id", row.get("sha"))
                require(identifier is not None and identifier not in seen,
                        "UNKNOWN_DUPLICATE_PAGE")
                seen.add(identifier)
                result.append(row)
            if len(rows) < 100:
                require(total is None or total == len(result), "UNKNOWN_MISSING_PAGE")
                self.coverage.append({"path": path, "filters": params or {},
                                      "pages": page, "rows": len(result), "complete": True})
                return result
        raise Stop("UNKNOWN_PAGE_LIMIT")

    def main(self):
        sha = self.request("GET", "/git/ref/heads/main")["object"]["sha"]
        require(bool(re.fullmatch("[0-9a-f]{40}", sha)), "UNKNOWN_MAIN")
        return sha

    def file(self, path, ref):
        data = self.request("GET", f"/contents/{quote(path, safe='/')}?ref={quote(ref, safe='')}")
        require(data.get("type") == "file" and data.get("encoding") == "base64",
                "UNKNOWN_SOURCE_FILE")
        try:
            return base64.b64decode(data["content"], validate=False).decode("utf-8")
        except (ValueError, UnicodeError, KeyError):
            raise Stop("UNKNOWN_SOURCE_FILE") from None


def validate_contract(config, receipt):
    require(config["schema"] == SCHEMA and config["status"] == "AUTHORIZED_ON_MAIN_MERGE",
            "AUTHORITY_REQUIRED")
    require(config["repository"] == REPOSITORY and config["write_paths"] == list(TARGETS),
            "SCOPE_CHANGED")
    require(config["health_workflow"] == HEALTH and
            config["health_policy"] == "config/research_automation_health_v0_2.json",
            "SUCCESSOR_REVIEW_REQUIRED")
    require(config["authority"] == {
        "github_metadata_read": True, "generated_blocks_write": True, "draft_pr": True,
        "merge": False, "dispatch": False, "provider": False, "r2": False,
        "holdout": False, "training": False, "promotion": False, "trading": False,
        "local_user_files": False, "paid_runtime": False,
    }, "AUTHORITY_CHANGED")
    require(receipt["schema"] == SCHEMA and receipt["policy_path"] == POLICY
            and receipt["policy_contract"] == config
            and receipt["effective_only_after_main_merge"] is True, "RECEIPT_MISMATCH")


def validate_trigger(event, run, main_sha):
    source = event.get("workflow_run", {})
    require(event.get("action") == "completed"
            and event.get("repository", {}).get("full_name") == REPOSITORY,
            "IGNORED_UNTRUSTED_EVENT")
    for candidate in (source, run):
        require(candidate.get("repository", {}).get("full_name") == REPOSITORY
                and candidate.get("head_repository", {}).get("full_name") == REPOSITORY
                and candidate.get("event") == "schedule"
                and candidate.get("head_branch") == "main"
                and candidate.get("path") == HEALTH
                and candidate.get("status") == "completed"
                and candidate.get("head_sha") == main_sha,
                "STALE_OR_UNTRUSTED_SOURCE")
    require(type(source.get("id")) is int and source["id"] == run.get("id")
            and source.get("run_attempt") == run.get("run_attempt"),
            "SOURCE_ATTEMPT_CHANGED")


def run_evidence(run):
    require(type(run.get("id")) is int and type(run.get("run_attempt")) is int
            and bool(re.fullmatch("[0-9a-f]{40}", run.get("head_sha", ""))),
            "UNKNOWN_RUN")
    return {key: run.get(key) for key in (
        "id", "run_attempt", "event", "head_sha", "status", "conclusion",
        "created_at", "run_started_at")}


def classify_checks(checks):
    if not checks:
        return "UNKNOWN_NO_CHECKS"
    if any(c.get("status") in {"waiting", "requested", "pending"} for c in checks):
        return "WAITING_CI_APPROVAL_OR_START"
    if any(c.get("status") != "completed" for c in checks):
        return "PENDING"
    if any(c.get("conclusion") not in {"success", "neutral", "skipped"} for c in checks):
        return "FAILURE"
    if any(c.get("conclusion") == "skipped" for c in checks):
        return "COMPLETED_WITH_SKIPS"
    return "SUCCESS"


def split_block(text):
    require(text.count(BEGIN) == 1 and text.count(END) == 1, "MANUAL_EDIT_OR_MARKER_ERROR")
    before, rest = text.split(BEGIN)
    middle, after = rest.split(END)
    return before, middle, after


def render(record):
    # Only our canonical record is rendered. PR titles/bodies/logs are never interpolated.
    encoded = base64.b64encode(json.dumps(record, sort_keys=True,
                                         ensure_ascii=True).encode()).decode()
    sem, evidence = record["semantic"], record["evidence"]
    lines = ["", f"<!-- record:{encoded} -->", "",
             "### 雲端維護觀測（非執行權限）", "",
             f"- 此次證據基準 main：`{evidence['main_sha']}`；不是永久最新 main。",
             f"- 語意摘要：`{digest(sem)}`。",
             "- 本機工作：EXCLUDED_BY_USER；研究結果：UNKNOWN_FROM_METADATA。",
             "- 每次接續先重查 main；本區塊保留上次實質變更證據，不因時間戳更新。", "",
             "| 工作 | 狀態 | 證據 |", "| --- | --- | --- |"]
    for row in sem["workflows"]:
        run = evidence["workflows"].get(row["workflow"])
        link = (f"[run {run['id']}](https://github.com/{REPOSITORY}/actions/runs/{run['id']})"
                if run else "UNKNOWN／無適用 run")
        job_text = "; ".join(f"{name}={state}" for name, state in row["jobs"])
        lines.append(f"| `{row['workflow']}` | {row['health']} / {row['conclusion']}"
                     f" / registration={row['registration']} {job_text} | {link} |")
    for row in sem["prs"]:
        lines.append(f"| PR #{row['number']} | {row['state']} / {row['checks']} | "
                     f"[PR](https://github.com/{REPOSITORY}/pull/{row['number']}) |")
    lines.extend(["", f"下一步：{sem['next_action']}", ""])
    return "\n".join(lines)


def existing_record(text):
    _, middle, _ = split_block(text)
    if middle == "\nPENDING_FIRST_CLOUD_OBSERVATION\n":
        return None
    match = re.search(r"^<!-- record:([A-Za-z0-9+/=]+) -->$", middle, re.MULTILINE)
    require(match is not None, "MANUAL_EDIT_DETECTED")
    try:
        record = json.loads(base64.b64decode(match.group(1), validate=True))
        require(record["schema"] == SCHEMA and middle == render(record),
                "MANUAL_EDIT_DETECTED")
        return record
    except (ValueError, KeyError, TypeError):
        raise Stop("MANUAL_EDIT_DETECTED") from None


def project_documents(documents, record):
    require(set(documents) == set(TARGETS), "OUTSIDE_ALLOWLIST")
    proposed = {}
    for path, text in documents.items():
        old = existing_record(text)
        if old is not None and old["semantic"] == record["semantic"]:
            proposed[path] = text
        else:
            before, _, after = split_block(text)
            proposed[path] = before + BEGIN + render(record) + END + after
    return proposed


def validate_branch_documents(base_docs, head_docs):
    require(set(base_docs) == set(head_docs) == set(TARGETS), "OUTSIDE_ALLOWLIST")
    for path in TARGETS:
        before, _, after = split_block(base_docs[path])
        head_before, _, head_after = split_block(head_docs[path])
        require((before, after) == (head_before, head_after), "MANUAL_EDIT_DETECTED")
        existing_record(head_docs[path])


def collect(api, event, checkout_sha, now):
    main = api.main()
    require(main == checkout_sha, "MAIN_CHANGED")
    config = json.loads(api.file(POLICY, main))
    receipt = json.loads(api.file(RECEIPT, main))
    validate_contract(config, receipt)
    source_id = event.get("workflow_run", {}).get("id")
    require(type(source_id) is int, "IGNORED_UNTRUSTED_EVENT")
    source = api.request("GET", f"/actions/runs/{source_id}")
    validate_trigger(event, source, main)
    policy = json.loads(api.file(config["health_policy"], main))
    require(policy["schema"] == "research-automation-health-v0.2",
            "SUCCESSOR_REVIEW_REQUIRED")
    companion = json.loads(api.file("research/status/current-operations-v0-3.json", main))
    # Do not silently ignore a merged monitoring-policy successor.
    health_text = api.file(HEALTH, main)
    require(f"--config {config['health_policy']}" in health_text,
            "SUCCESSOR_REVIEW_REQUIRED")
    require(companion["gates"]["source_switch_authorized"] is False, "AUTHORITY_REVIEW")
    tree = api.request("GET", f"/git/trees/{main}?recursive=1")
    require(tree.get("truncated") is False, "UNKNOWN_TREE_TRUNCATED")
    for target in TARGETS:
        entries = [f for f in tree["tree"] if f["path"] == target]
        require(len(entries) == 1 and entries[0].get("mode") == "100644",
                "UNSAFE_TARGET_FILE")
    files = [f for f in tree["tree"] if f["path"].startswith(".github/workflows/")
             and f["path"].endswith((".yml", ".yaml"))]
    scheduled = set()
    for entry in files:
        text = api.file(entry["path"], main)
        if re.search(r"^  schedule:", text, re.MULTILINE):
            scheduled.add(entry["path"].split("/")[-1])
    policies = policy["workflows"]
    require(scheduled == {p["workflow"] for p in policies}
            and len(policies) == len(scheduled), "UNKNOWN_SCHEDULE_COVERAGE")
    rows, evidence = [], {}
    since = (now - timedelta(days=14)).isoformat().replace("+00:00", "Z")
    for item in policies:
        require(item["allowed_events"] == ["schedule"], "POLICY_EVENT_REVIEW")
        name = item["workflow"]
        registration = api.request("GET", f"/actions/workflows/{quote(name, safe='')}")
        expectation = expectation_from_config(item)
        expired = expectation.active_until_utc and now >= parse_utc(expectation.active_until_utc)
        runs = [] if expired else api.pages(
            f"/actions/workflows/{quote(name, safe='')}/runs", "workflow_runs",
            {"branch": "main", "event": "schedule", "created": f">={since}"})
        for run in runs:
            require(run.get("event") == "schedule" and run.get("head_branch") == "main"
                    and run.get("head_repository", {}).get("full_name") == REPOSITORY,
                    "UNKNOWN_RUN_LINEAGE")
        row = evaluate_workflow(expectation, runs, now=now)
        latest = next((r for r in runs if r["id"] == (row.get("last_run") or {}).get("id")), None)
        evidence[name] = run_evidence(latest) if latest else None
        jobs_state = []
        if name == "dashboard-github-pages.yml" and latest:
            jobs = api.pages(f"/actions/runs/{latest['id']}/attempts/{latest['run_attempt']}/jobs",
                             "jobs")
            for job_name in ("build", "deploy", "browser-production"):
                matching = [j for j in jobs if j.get("name") == job_name]
                state = (matching[0].get("conclusion") or matching[0].get("status")
                         if len(matching) == 1 else "UNKNOWN")
                jobs_state.append([job_name, state])
        rows.append({"workflow": name, "health": row["status"],
                     "registration": registration["state"],
                     "conclusion": (latest or {}).get("conclusion") or "UNKNOWN",
                     "jobs": jobs_state})
    prs = api.pages("/pulls", params={"state": "open", "base": "main"})
    numbers = {p["number"] for p in prs if not p["head"]["ref"].startswith(PREFIX)} | {496, 497}
    pr_rows, pr_evidence = [], {}
    for number in sorted(numbers):
        pr = api.request("GET", f"/pulls/{number}")
        checks = api.pages(f"/commits/{pr['head']['sha']}/check-runs", "check_runs")
        state = "MERGED" if pr.get("merged") else "CLOSED" if pr["state"] == "closed" else (
            "DRAFT" if pr["draft"] else "OPEN")
        pr_rows.append({"number": number, "head": pr["head"]["sha"],
                        "state": state, "checks": classify_checks(checks)})
        pr_evidence[str(number)] = {"head": pr["head"]["sha"], "base": pr["base"]["sha"],
                                   "checks": [{"name": c["name"], "status": c["status"],
                                               "conclusion": c.get("conclusion")} for c in checks]}
    attention = any(r["health"] not in {"HEALTHY", "HEALTHY_CONDITIONAL", "EXPECTED_STOP",
                                       "WAITING_WINDOW"} for r in rows)
    action = ("執行 CLOUD-02：查核異常 metadata，禁止補跑或修改研究權限。" if attention else
              "執行 CLOUD-01：審查既有 PR 與雲端維護驗收；fingerprint 切換僅準備提案。")
    record = {"schema": SCHEMA,
              "semantic": {"workflows": sorted(rows, key=lambda r: r["workflow"]),
                           "prs": pr_rows, "next_action": action},
              "evidence": {"main_sha": main, "observed_at_utc": now.isoformat(),
                           "source": run_evidence(source), "workflows": evidence,
                           "prs": pr_evidence, "coverage": api.coverage}}
    require(api.main() == main, "MAIN_CHANGED")
    return record


def guard_main(api, expected):
    require(api.main() == expected, "MAIN_CHANGED")


def publish(api, record):
    main = record["evidence"]["main_sha"]
    base_docs = {p: api.file(p, main) for p in TARGETS}
    candidates = [p for p in api.pages("/pulls", params={"state": "open", "base": "main"})
                  if p["head"]["ref"].startswith(PREFIX)]
    require(len(candidates) <= 1, "MULTIPLE_MAINTENANCE_PRS")
    pr = candidates[0] if candidates else None
    branch = pr["head"]["ref"] if pr else PREFIX + main[:12]
    ref = api.request("GET", f"/git/ref/heads/{branch}", missing_ok=True)
    head = ref["object"]["sha"] if ref else main
    documents = base_docs
    if pr:
        require(pr["draft"] is True and pr["user"]["login"] == "github-actions[bot]"
                and pr["head"]["repo"]["full_name"] == REPOSITORY, "MANUAL_EDIT_DETECTED")
        require(pr["head"]["sha"] == head, "BRANCH_CHANGED")
    if ref and not pr:
        history = api.pages("/pulls", params={
            "state": "closed", "head": f"qookey109-pixel:{branch}"})
        require(not history, "CLOSED_BRANCH_REVIEW_REQUIRED")
    if head != main:
        comparison = api.request("GET", f"/compare/{main}...{head}")
        require(comparison["status"] == "ahead" and comparison["behind_by"] == 0
                and comparison["merge_base_commit"]["sha"] == main, "MAIN_CHANGED")
        require(set(f["filename"] for f in comparison["files"]) <= set(TARGETS),
                "OUTSIDE_ALLOWLIST")
        require(comparison["total_commits"] == len(comparison["commits"]),
                "UNKNOWN_COMMIT_COVERAGE")
        for commit in comparison["commits"]:
            require((commit.get("author") or {}).get("login") == "github-actions[bot]"
                    and commit["commit"]["message"] == MESSAGE, "MANUAL_EDIT_DETECTED")
        documents = {p: api.file(p, head) for p in TARGETS}
        validate_branch_documents(base_docs, documents)
    proposed = project_documents(documents, record)
    changed = {p: text for p, text in proposed.items() if text != documents[p]}
    if not changed and (pr or head == main):
        return {"status": "NO_CHANGE", "pr": pr["number"] if pr else None,
                "head_sha": head, "commits_created": 0}
    # Frozen paths cannot enter this hardcoded allowlist.
    require(set(changed) <= set(TARGETS), "OUTSIDE_ALLOWLIST")
    guard_main(api, main)
    if changed:
        parent = api.request("GET", f"/git/commits/{head}")
        tree = api.request("POST", "/git/trees", {
            "base_tree": parent["tree"]["sha"],
            "tree": [{"path": p, "mode": "100644", "type": "blob", "content": content}
                     for p, content in sorted(changed.items())]})
        commit = api.request("POST", "/git/commits", {
            "message": MESSAGE, "tree": tree["sha"], "parents": [head]})
        guard_main(api, main)
        current = api.request("GET", f"/git/ref/heads/{branch}", missing_ok=True)
        require((current["object"]["sha"] if current else None) == (head if ref else None),
                "BRANCH_CHANGED")
        if ref:
            api.request("PATCH", f"/git/refs/heads/{branch}",
                        {"sha": commit["sha"], "force": False})
        else:
            api.request("POST", "/git/refs", {"ref": f"refs/heads/{branch}", "sha": commit["sha"]})
        head = commit["sha"]
        # GitHub does not offer a main+delivery-ref transaction; stale drafts cannot merge.
        guard_main(api, main)
    if not pr:
        pr = api.request("POST", "/pulls", {
            "title": "docs: refresh cloud maintenance evidence",
            "head": branch, "base": "main", "draft": True,
            "body": "Cloud maintenance V0.1; generated blocks only. No research authority. "
                    "Recheck exact head and current main before review. "
                    "CI may require approval; missing checks are UNKNOWN. "
                    "No automatic merge or deployment."})
    require(pr["draft"] is True, "DRAFT_REQUIRED")
    return {"status": "DRAFT_UPDATED" if changed else "DRAFT_RECOVERED",
            "pr": pr["number"], "head_sha": head, "commits_created": int(bool(changed)),
            "ci": "WAITING_CI_VERIFICATION"}


def summary(record, result):
    return ("# Cloud Project Maintenance V0.1\n\n"
            f"Result: **{result['status']}**\n\n"
            + render(record).split("-->", 1)[1]
            + "\n\nEvidence (metadata only; times are not execution authority):\n\n"
            + "```json\n" + json.dumps({"evidence": record["evidence"], "delivery": result},
                                         ensure_ascii=False, sort_keys=True, indent=2)
            + "\n```\n")
