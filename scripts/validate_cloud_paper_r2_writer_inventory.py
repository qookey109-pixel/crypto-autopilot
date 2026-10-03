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
    r"|\bcloud_paper_usage_audit_v0_[12](?:\.py)?\b[^\n]*--output",
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
    "self._usage_guard.validate_evidence()",
    "self._shared_rows_guard.reserve_query(",
    "self._shared_rows_guard.validate_evidence(",
    "self._usage_guard.validate_evidence()",
    "result = self._request(sql, params)",
)


def find_d1_rest_source_paths(source_files: dict[str, str]) -> set[str]:
    """Find Python source files with a direct D1 REST endpoint/client marker."""
    return {
        path for path, contents in source_files.items()
        if D1_REST_SOURCE_MARKER.search(contents)
    }


PREPAID_D1_CLIENT_PATH = "src/crypto_autopilot/paper/prepaid_d1_client_v0_1.py"
PREPAID_D1_QUERY_GUARD_ORDER = (
    "if self._poisoned:",
    "operation = self._validate_statement(sql, params)",
    "self._database_evidence.validate(",
    "self._guard.reserve_query()",
    "self._meter.charge_before_query(",
    "self._guard.validate_evidence()",
    "self._meter.validate_binding(",
    "cost = self._meter.statement_cost(operation)",
    "result, size = self._request(sql, params)",
    "result.rows_read > cost.rows_read",
    "result.rows_written > cost.rows_written",
    "size > self._last_size + cost.storage_bytes",
    "self._poisoned = True",
)


def validate_d1_source_boundary(
    source_files: dict[str, str], expected_client_path: str,
    *, successor_client_path: str | None = None,
) -> list[str]:
    """Allow only named, independently guarded clients; account coverage stays separate."""
    expected = {expected_client_path}
    if successor_client_path is not None:
        if successor_client_path != PREPAID_D1_CLIENT_PATH:
            raise RuntimeError("D1 successor client path is not the versioned implementation")
        expected.add(successor_client_path)
    paths = find_d1_rest_source_paths(source_files)
    if paths != expected:
        raise RuntimeError(
            "D1 REST source boundary mismatch; "
            f"expected={sorted(expected)}, detected={sorted(paths)}"
        )
    contents = source_files[expected_client_path]
    query_start = contents.find("    def query(self, sql: str, params: tuple[object, ...])")
    query_end = contents.find("    def _request(", query_start)
    if query_start < 0 or query_end < 0:
        raise RuntimeError("D1 REST client query boundary is missing")
    query_body = contents[query_start:query_end]
    positions = []
    cursor = 0
    for marker in D1_QUERY_GUARD_ORDER:
        position = query_body.find(marker, cursor)
        if position < 0:
            raise RuntimeError("D1 REST client budget guards are missing or out of order")
        positions.append(position)
        cursor = position + len(marker)
    if successor_client_path is not None:
        successor = source_files[successor_client_path]
        start = successor.find("    def query(self, sql: str, params: tuple[object, ...])")
        end = successor.find("    def _request(", start)
        if start < 0 or end < 0:
            raise RuntimeError("D1 prepaid client query boundary is missing")
        body = successor[start:end]
        cursor = 0
        for marker in PREPAID_D1_QUERY_GUARD_ORDER:
            position = body.find(marker, cursor)
            if position < 0:
                raise RuntimeError("D1 prepaid client guards are missing or out of order")
            cursor = position + len(marker)
    return sorted(paths)


SHARED_ACCOUNT_REGISTRY = (
    ROOT / "config" / "cloudflare_shared_account_writer_registry_v0_1.json"
)
CURRENT_WRITER_ACCESSES = {"WRITER", "CONDITIONAL_WRITER", "COMPLETED_WRITER"}


def validate_shared_account_writer_registry(
    inventory: dict[str, object], registry: dict[str, object],
) -> list[str]:
    """Require every currently effective in-repo writer to be registered.

    This is a repository-only guard. It deliberately refuses to infer that the
    Cloudflare account-wide writer inventory is complete.
    """
    entries = inventory.get("workflows")
    writers = registry.get("repository_writers")
    if not isinstance(entries, list) or not isinstance(writers, list):
        raise RuntimeError("shared account writer registry arrays are missing")

    current_paths: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        workflow = entry.get("workflow")
        lifecycle = entry.get("lifecycle")
        if (
            isinstance(workflow, str)
            and entry.get("access") in CURRENT_WRITER_ACCESSES
            and isinstance(lifecycle, str)
            and lifecycle.startswith("CURRENT_")
        ):
            current_paths.append(workflow)
    current_paths.sort()

    registered_paths: list[str] = []
    writer_ids: list[str] = []
    for entry in writers:
        if not isinstance(entry, dict):
            raise RuntimeError("shared account writer registry entries are invalid")
        workflow = entry.get("workflow")
        writer_id = entry.get("writer_id")
        if not isinstance(workflow, str) or not isinstance(writer_id, str):
            raise RuntimeError("shared account writer registry entries are invalid")
        registered_paths.append(workflow)
        writer_ids.append(writer_id)
    if len(set(registered_paths)) != len(registered_paths):
        raise RuntimeError("shared account writer workflow paths must be unique")
    if len(set(writer_ids)) != len(writer_ids):
        raise RuntimeError("shared account writer IDs must be unique")
    if sorted(registered_paths) != current_paths:
        missing = sorted(set(current_paths) - set(registered_paths))
        stale = sorted(set(registered_paths) - set(current_paths))
        raise RuntimeError(
            "shared account registry does not match current repository writers; "
            f"unregistered={missing}, not_current={stale}"
        )

    for entry in writers:
        if (
            not entry.get("writer_id")
            or entry.get("resource") not in {"R2", "D1"}
            or entry.get("registration_state")
            not in {"DECLARED_SHARED_ADMISSION_NOT_VERIFIED",
                    "SHARED_ADMISSION_VERIFIED"}
        ):
            raise RuntimeError("shared account writer registration fields are invalid")

    external = registry.get("external_writer_inventory")
    gate = registry.get("production_gate")
    if not isinstance(external, dict) or not isinstance(gate, dict):
        raise RuntimeError("shared account external inventory or production gate is missing")
    external_complete = external.get("complete")
    external_state = external.get("state")
    if (
        external_state not in {"UNCONFIRMED", "ATTESTED"}
        or type(external_complete) is not bool
        or (external_complete and external_state != "ATTESTED")
    ):
        raise RuntimeError("external writer inventory completeness is invalid")
    if external_complete:
        receipt = external.get("attestation_receipt")
        if not isinstance(receipt, str) or not receipt:
            raise RuntimeError("complete external inventory requires an attestation receipt")
        receipt_path = (ROOT / receipt).resolve()
        if ROOT.resolve() not in receipt_path.parents or not receipt_path.is_file():
            raise RuntimeError("external writer attestation receipt is missing")
    if (
        type(gate.get("account_wide_coverage_proven")) is not bool
        or (gate.get("account_wide_coverage_proven") and not external_complete)
        or type(gate.get("shared_admission_integrated_for_all_repository_writers"))
        is not bool
        or type(gate.get("d1_provisioned")) is not bool
        or type(gate.get("activation_enabled")) is not bool
    ):
        raise RuntimeError("shared account production gate fields are invalid")
    scoped_r2 = external.get("current_external_r2_owner_attestation")
    if scoped_r2 is not None:
        if not isinstance(scoped_r2, dict):
            raise RuntimeError("scoped R2 owner attestation is invalid")
        receipt = scoped_r2.get("receipt")
        if not isinstance(receipt, str) or not receipt:
            raise RuntimeError("scoped R2 owner attestation receipt is missing")
        receipt_path = (ROOT / receipt).resolve()
        if ROOT.resolve() not in receipt_path.parents or not receipt_path.is_file():
            raise RuntimeError("scoped R2 owner attestation receipt is missing")
        try:
            evidence = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            raise RuntimeError("scoped R2 owner attestation receipt is invalid") from exc
        owner = evidence.get("owner_attestation") if isinstance(evidence, dict) else None
        if (
            not isinstance(evidence, dict)
            or evidence.get("schema") != "qookey-cloudflare-owner-billing-checkpoint-v0.1"
            or not isinstance(owner, dict)
            or owner.get("source") != "DIRECT_USER_MESSAGE"
            or owner.get("scope") != "CURRENT_EXTERNAL_R2_WRITERS"
            or owner.get("external_r2_writers_declared") != []
            or owner.get("future_writer_registration_required") is not True
            or scoped_r2.get("state") != "ATTESTED_NONE_AT_CHECKPOINT"
            or scoped_r2.get("observed_date") != evidence.get("observed_date")
            or scoped_r2.get("scope") != owner.get("scope")
        ):
            raise RuntimeError("scoped R2 owner attestation exceeds receipt evidence")
    if (
        gate.get("account_wide_coverage_proven")
        and not gate.get("shared_admission_integrated_for_all_repository_writers")
    ):
        raise RuntimeError("account coverage claimed with repository admission unverified")
    if (
        gate.get("shared_admission_integrated_for_all_repository_writers")
        and any(
            entry["registration_state"] != "SHARED_ADMISSION_VERIFIED"
            for entry in writers
        )
    ):
        raise RuntimeError("shared admission claimed with unverified writers")
    if (
        gate.get("activation_enabled")
        and (
            not gate.get("account_wide_coverage_proven")
            or not gate.get("shared_admission_integrated_for_all_repository_writers")
            or not gate.get("d1_provisioned")
        )
    ):
        raise RuntimeError("production activation exceeds shared-account evidence")
    return current_paths


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
    registry = json.loads(SHARED_ACCOUNT_REGISTRY.read_text(encoding="utf-8"))
    registered_current = validate_shared_account_writer_registry(inventory, registry)
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
    successor = json.loads(
        (ROOT / "config/prepaid_d1_runtime_gateway_v0_1.json").read_text(encoding="utf-8")
    )
    if (
        successor.get("schema") != "qookey-prepaid-d1-runtime-gateway-v0.1"
        or successor.get("activation_enabled") is not False
        or successor.get("cloudflare_execution_authorized") is not False
        or successor.get("implementation") != PREPAID_D1_CLIENT_PATH
    ):
        raise RuntimeError("D1 prepaid implementation inventory contract is invalid")
    d1_client_paths = validate_d1_source_boundary(
        source_files, expected_d1_client_path,
        successor_client_path=successor["implementation"],
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
        "Shared account registry lists "
        f"{len(registered_current)} current repository writers; "
        "external writer inventory remains independently attested."
    )
    print(
        "R2 writer inventory matches "
        f"{len(referenced_paths)} credential-referencing workflows "
        f"across {len(workflow_paths)} workflow files."
    )
    print(
        "D1 repository source boundary matches guarded client "
        f"{d1_client_paths}; external/account-wide coverage remains unproven."
    )
    print(
        "D1 workflow marker inventory matches "
        f"{len(d1_access_paths)} workflows across {len(workflow_paths)} "
        "repository workflow files; account-wide writer coverage is not proven."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
