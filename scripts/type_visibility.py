#!/usr/bin/env python3
"""Emit deterministic, non-blocking semantic type-check visibility.

This report is informational only. Mypy diagnostics are baseline evidence, not
CI failures, and grant no validation, promotion, holdout, source-switch, or
trading authority.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import re
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RECEIPT_ROOT = ROOT / "research" / "receipts"
SCAN_TARGETS = ("src/crypto_autopilot",)
MYPY_LINE_RE = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+)(?::(?P<column>\d+))?: "
    r"(?P<severity>error|note): (?P<message>.*?)(?: \[(?P<code>[^\]]+)\])?$"
)
MAX_DIAGNOSTICS = 500


def _display_path(raw: str) -> str:
    path = Path(raw)
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except (OSError, ValueError):
        return raw


def _receipt_bindings() -> dict[str, tuple[str, ...]]:
    bindings: dict[str, set[str]] = {}
    if not RECEIPT_ROOT.exists():
        return {}

    for receipt_path in sorted(RECEIPT_ROOT.rglob("*.json")):
        try:
            payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        artifacts = payload.get("artifacts")
        if not isinstance(artifacts, Mapping):
            continue
        receipt_display = receipt_path.relative_to(ROOT).as_posix()
        for artifact in artifacts.values():
            if not isinstance(artifact, Mapping):
                continue
            raw_path = artifact.get("path")
            digest = artifact.get("sha256")
            if not isinstance(raw_path, str) or not raw_path.strip():
                continue
            if not isinstance(digest, str) or len(digest) != 64:
                continue
            path = Path(raw_path).as_posix()
            bindings.setdefault(path, set()).add(receipt_display)

    return {
        path: tuple(sorted(receipts))
        for path, receipts in sorted(bindings.items())
    }


def parse_mypy_output(
    output: str,
    *,
    receipt_bindings: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, object]:
    diagnostics: list[dict[str, Any]] = []
    by_code: Counter[str] = Counter()
    by_file: Counter[str] = Counter()
    unparsable_lines: list[str] = []
    active_bindings = receipt_bindings or {}

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = MYPY_LINE_RE.match(line)
        if match is None:
            unparsable_lines.append(line)
            continue

        severity = match.group("severity")
        code = match.group("code") or "NO_CODE"
        display_path = _display_path(match.group("path"))
        receipt_paths = tuple(sorted(set(active_bindings.get(display_path, ()))))
        row = {
            "path": display_path,
            "line": int(match.group("line")),
            "column": (
                int(match.group("column"))
                if match.group("column") is not None
                else None
            ),
            "severity": severity,
            "code": code,
            "message": match.group("message"),
            "receipt_bound": bool(receipt_paths),
            "receipt_paths": list(receipt_paths),
        }
        diagnostics.append(row)
        if severity == "error":
            by_code[code] += 1
            by_file[display_path] += 1

    diagnostics.sort(
        key=lambda row: (
            str(row["path"]),
            int(row["line"]),
            int(row["column"] or 0),
            str(row["severity"]),
            str(row["code"]),
        )
    )
    error_count = sum(row["severity"] == "error" for row in diagnostics)
    note_count = sum(row["severity"] == "note" for row in diagnostics)
    receipt_bound_error_count = sum(
        row["severity"] == "error" and bool(row["receipt_bound"])
        for row in diagnostics
    )
    return {
        "diagnostic_count": len(diagnostics),
        "error_count": error_count,
        "note_count": note_count,
        "receipt_bound_error_count": receipt_bound_error_count,
        "unbound_error_count": error_count - receipt_bound_error_count,
        "by_error_code": dict(sorted(by_code.items())),
        "by_error_file": dict(sorted(by_file.items())),
        "diagnostics": diagnostics[:MAX_DIAGNOSTICS],
        "diagnostics_truncated": len(diagnostics) > MAX_DIAGNOSTICS,
        "unparsable_lines": unparsable_lines[:100],
        "unparsable_lines_truncated": len(unparsable_lines) > 100,
    }


def _mypy_version() -> dict[str, object]:
    try:
        completed = subprocess.run(
            ["mypy", "--version"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {
            "available": False,
            "version": None,
            "error": type(exc).__name__,
        }

    return {
        "available": completed.returncode == 0,
        "version": (completed.stdout or completed.stderr).strip() or None,
        "returncode": completed.returncode,
    }


def build_report(*, run_tool: bool = True) -> dict[str, object]:
    receipt_bindings = _receipt_bindings()
    version = _mypy_version() if run_tool else {
        "available": None,
        "version": None,
        "skipped_for_test": True,
    }
    base: dict[str, object] = {
        "schema": "qookey-type-visibility-v0.1",
        "policy": {
            "informational_only": True,
            "blocking_gate": False,
            "thresholds_enforced": False,
            "promotion_authority": False,
            "validation_authority": False,
            "holdout_authority": False,
            "source_switch_authority": False,
            "trading_authority": False,
        },
        "scan_targets": list(SCAN_TARGETS),
        "python_version_target": "3.13",
        "receipt_binding": {
            "source_glob": "research/receipts/**/*.json",
            "bound_file_count": len(receipt_bindings),
            "bound_files": sorted(receipt_bindings),
        },
        "tool": {
            "name": "mypy",
            **version,
        },
    }

    if not run_tool:
        base["result"] = {
            "ran": False,
            "skipped_for_test": True,
            "baseline_clean": None,
            "returncode": None,
            "diagnostic_count": None,
            "error_count": None,
            "note_count": None,
            "receipt_bound_error_count": None,
            "unbound_error_count": None,
            "by_error_code": {},
            "by_error_file": {},
            "diagnostics": [],
            "diagnostics_truncated": False,
            "unparsable_lines": [],
            "unparsable_lines_truncated": False,
        }
        return base

    command = [
        "mypy",
        *SCAN_TARGETS,
        "--python-version",
        "3.13",
        "--ignore-missing-imports",
        "--show-error-codes",
        "--show-column-numbers",
        "--no-error-summary",
        "--no-pretty",
        "--no-color-output",
        "--no-incremental",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=180,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        base["result"] = {
            "ran": False,
            "baseline_clean": None,
            "returncode": None,
            "diagnostic_count": None,
            "error_count": None,
            "note_count": None,
            "receipt_bound_error_count": None,
            "unbound_error_count": None,
            "by_error_code": {},
            "by_error_file": {},
            "diagnostics": [],
            "diagnostics_truncated": False,
            "unparsable_lines": [],
            "unparsable_lines_truncated": False,
            "tool_error": type(exc).__name__,
        }
        return base

    parsed = parse_mypy_output(
        completed.stdout,
        receipt_bindings=receipt_bindings,
    )
    parsed.update(
        {
            "ran": True,
            "returncode": completed.returncode,
            "baseline_clean": completed.returncode == 0,
            "tool_error": completed.returncode not in {0, 1},
            "stderr_tail": completed.stderr[-2000:] if completed.stderr else "",
        }
    )
    base["result"] = parsed
    return base


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="type-visibility.json")
    args = parser.parse_args()

    report = build_report()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    result = report["result"]
    print(
        json.dumps(
            {
                "schema": report["schema"],
                "tool_available": report["tool"].get("available"),
                "ran": result.get("ran"),
                "baseline_clean": result.get("baseline_clean"),
                "error_count": result.get("error_count"),
                "receipt_bound_error_count": result.get("receipt_bound_error_count"),
                "unbound_error_count": result.get("unbound_error_count"),
                "blocking_gate": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
