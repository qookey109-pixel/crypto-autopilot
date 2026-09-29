from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
INVENTORY = ROOT / "research" / "status" / "cloud-paper-r2-writer-inventory-v0-1.json"
SECRET_REF = re.compile(
    r"\$\{\{[^}]*\bsecrets\.(?:CLOUDFLARE_ACCOUNT_ID|CLOUDFLARE_BILLING_READONLY_API_TOKEN|R2_[A-Z0-9_]+)\b",
    re.IGNORECASE,
)


D1_ACCESS_REF = re.compile(
    r"\$\{\{[^}]*\bsecrets\.[A-Z0-9_]*(?:D1|DATABASE_ID)[A-Z0-9_]*\b[^}]*\}\}"
    r"|\bwrangler\s+d1\b"
    r"|^\s*d1_databases\s*:"
    r"|/(?:accounts|zones)/[^\s\"']+/d1/(?:database|databases)(?:/|\b)"
    r"|\bd1(?:Analytics|Storage|Queries)AdaptiveGroups\b"
    r"|\bcloud_paper_usage_audit_v0_[12]\.py\b",
    re.IGNORECASE | re.MULTILINE,
)


def contains_d1_access_reference(contents: str) -> bool:
    """Detect direct D1 markers and the explicitly scoped analytics audit entrypoint."""
    return D1_ACCESS_REF.search(contents) is not None


D1_REST_SOURCE_MARKER = re.compile(
    r"api\.cloudflare\.com/client/v4/accounts/[^/\\s]+/d1/(?:database|databases)(?:/|\\b)"
    r"|/d1/(?:database|databases)(?:/|\b)"
    r"|\bclass\s+CloudflareD1QueryClient\b",
    re.IGNORECASE,
)
D1_QUERY_GUARD_ORDER = (
    "self._usage_guard.reserve_query()",
    "if self._shared_rows_guard is None:",
    "self._shared_rows_guard.reserve_query(",
    "result = self._request(sql, params)",
)


def find_d1_rest_source_paths(source_files: dict[str, str]) -> set[str]:
    """Find Python source files with a direct D1 REST endpoint/client marker."""
    return {
        path for path, contents in source_files.items()
        if D1_REST_SOURCE_MARKER.search(contents)
    }


def validate_d1_source_boundary(
    source_files: dict[str, str], expected_client_path: str,
) -> list[str]:
    """Require one guarded in-repository D1 REST client; account coverage stays separate."""
    paths = find_d1_rest_source_paths(source_files)
    if paths != {expected_client_path}:
        raise RuntimeError(
            "D1 REST source boundary mismatch; "
            f"expected={[expected_client_path]}, detected={sorted(paths)}"
        )
    contents = source_files[expected_client_path]
    query_start = contents.find("    def query(self, sql: str, params: tuple[object, ...])")
    query_end = contents.find("    def _request(", query_start)
    if query_start < 0 or query_end < 0:
        raise RuntimeError("D1 REST client query boundary is missing")
    query_body = contents[query_start:query_end]
    positions = [query_body.find(marker) for marker in D1_QUERY_GUARD_ORDER]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        raise RuntimeError("D1 REST client budget guards are missing or out of order")
    return sorted(paths)

def main() -> int:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    workflow_paths = sorted(
        path.relative_to(ROOT).as_posix()
        for path in WORKFLOWS.rglob("*")
        if path.is_file() and path.suffix in {".yml", ".yaml"}
    )
    referenced_paths = {
        relative_path
        for relative_path in workflow_paths
        if SECRET_REF.search((ROOT / relative_path).read_text(encoding="utf-8"))
    }
    entries = inventory.get("workflows")
    if not isinstance(entries, list):
        raise RuntimeError("R2 writer inventory workflows must be an array")
    listed_paths = [entry.get("workflow") for entry in entries if isinstance(entry, dict)]
    if len(listed_paths) != len(entries) or len(set(listed_paths)) != len(listed_paths):
        raise RuntimeError("R2 writer inventory contains invalid or duplicate workflow paths")
    if set(listed_paths) != referenced_paths:
        missing = sorted(referenced_paths - set(listed_paths))
        stale = sorted(set(listed_paths) - referenced_paths)
        raise RuntimeError(
            "R2 writer inventory does not match workflow secret references; "
            f"unlisted={missing}, no_longer_referenced={stale}"
        )
    scan = inventory.get("scan", {})
    if scan.get("workflow_file_count") != len(workflow_paths):
        raise RuntimeError(
            "R2 writer inventory workflow count is stale: "
            f"recorded={scan.get('workflow_file_count')}, actual={len(workflow_paths)}"
        )
    if scan.get("workflows_with_r2_or_cloudflare_secret_references") != len(referenced_paths):
        raise RuntimeError(
            "R2 writer inventory credential-reference count is stale: "
            f"recorded={scan.get('workflows_with_r2_or_cloudflare_secret_references')}, "
            f"actual={len(referenced_paths)}"
        )
    source_files = {
        path.relative_to(ROOT).as_posix(): path.read_text(encoding="utf-8")
        for source_root in (ROOT / "src", ROOT / "scripts")
        for path in source_root.rglob("*.py")
    }
    source_boundary = inventory.get("d1_source_boundary", {})
    expected_d1_client_path = source_boundary.get("expected_d1_rest_client_path")
    if not isinstance(expected_d1_client_path, str) or not expected_d1_client_path:
        raise RuntimeError("D1 source boundary expected client path is missing")
    d1_client_paths = validate_d1_source_boundary(
        source_files, expected_d1_client_path,
    )
    if source_boundary.get("scope") != "REPOSITORY_SOURCE_ONLY":
        raise RuntimeError("D1 source boundary scope must remain explicit")
    if source_boundary.get("account_wide_coverage") != "NOT_PROVEN":
        raise RuntimeError("D1 source scan must not claim account-wide coverage")
    d1_access_paths = {
        relative_path
        for relative_path in workflow_paths
        if contains_d1_access_reference((ROOT / relative_path).read_text(encoding="utf-8"))
    }
    d1_inventory = inventory.get("d1_access_workflows", {})
    d1_listed_paths = d1_inventory.get("workflow_paths")
    if not isinstance(d1_listed_paths, list) or len(set(d1_listed_paths)) != len(d1_listed_paths):
        raise RuntimeError("D1 workflow inventory paths must be a unique array")
    if set(d1_listed_paths) != d1_access_paths:
        missing = sorted(d1_access_paths - set(d1_listed_paths))
        stale = sorted(set(d1_listed_paths) - d1_access_paths)
        raise RuntimeError(
            "D1 workflow inventory does not match detected workflow markers; "
            f"unlisted={missing}, no_longer_detected={stale}"
        )
    if d1_inventory.get("workflow_count") != len(d1_access_paths):
        raise RuntimeError(
            "D1 workflow inventory count is stale: "
            f"recorded={d1_inventory.get('workflow_count')}, actual={len(d1_access_paths)}"
        )
    print(
        "R2 writer inventory matches "
        f"{len(referenced_paths)} credential-referencing workflows "
        f"across {len(workflow_paths)} workflow files."
    )
    print(
        "D1 repository source boundary matches guarded client "
        f"{d1_client_paths[0]}; external/account-wide coverage remains unproven."
    )
    print(
        "D1 workflow marker inventory matches "
        f"{len(d1_access_paths)} workflows across {len(workflow_paths)} "
        "repository workflow files; account-wide writer coverage is not proven."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
