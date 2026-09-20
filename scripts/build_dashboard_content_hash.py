from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


GLOBAL_VOLATILE_JSON_KEYS = frozenset(
    {
        "generatedAtUtc",
        "projectionGeneratedAtUtc",
        "projection_generated_at_utc",
    }
)
VOLATILE_JSON_KEYS: dict[str, frozenset[str]] = {
    "data/cloud-runs.json": frozenset({"observedAtUtc"}),
}
EXCLUDED = {
    "data/content-hash.txt",
    "data/content-manifest.json",
    ".nojekyll",
}


def _strip_keys(value: Any, keys: frozenset[str]) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_keys(item, keys)
            for key, item in value.items()
            if key not in keys
        }
    if isinstance(value, list):
        return [_strip_keys(item, keys) for item in value]
    return value


def _normalized_bytes(path: Path, relative: str) -> bytes:
    if relative.endswith(".json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        keys = GLOBAL_VOLATILE_JSON_KEYS | VOLATILE_JSON_KEYS.get(
            relative, frozenset()
        )
        normalized = _strip_keys(payload, keys)
        return json.dumps(
            normalized,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    return path.read_bytes()


def build_content_hash(site: Path) -> tuple[str, list[dict[str, str]]]:
    if not site.is_dir():
        raise RuntimeError(f"site directory missing: {site}")
    entries: list[dict[str, str]] = []
    for path in sorted(item for item in site.rglob("*") if item.is_file()):
        relative = path.relative_to(site).as_posix()
        if relative in EXCLUDED:
            continue
        digest = hashlib.sha256(_normalized_bytes(path, relative)).hexdigest()
        entries.append({"path": relative, "sha256": digest})

    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest(), entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()

    digest, entries = build_content_hash(args.site)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(digest + "\n", encoding="utf-8")
    if args.manifest is not None:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(
                {
                    "schema": "qookey-dashboard-content-manifest-v0.1",
                    "business_content_sha256": digest,
                    "files": entries,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
