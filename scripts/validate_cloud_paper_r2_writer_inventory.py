from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
INVENTORY = ROOT / "research" / "status" / "cloud-paper-r2-writer-inventory-v0-1.json"
SECRET_REF = re.compile(
    r"\$\{\{[^}]*\bsecrets\.(?:CLOUDFLARE_ACCOUNT_ID|R2_[A-Z0-9_]+)\b",
    re.IGNORECASE,
)


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
    print(
        "R2 writer inventory matches "
        f"{len(referenced_paths)} credential-referencing workflows "
        f"across {len(workflow_paths)} workflow files."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
