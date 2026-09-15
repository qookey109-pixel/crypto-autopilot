#!/usr/bin/env python3
"""Emit deterministic, non-blocking Python quality visibility for the repository.

This report is intentionally informational. It does not enforce thresholds and
must not be used as a promotion, validation, holdout, source-switch, or trading
gate.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = ("src", "scripts", "tests")
MARKER_RE = re.compile(r"\b(TODO|FIXME|HACK)\b", re.IGNORECASE)
DECISION_NODE_TYPES = (
    ast.If,
    ast.IfExp,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.Match,
    ast.comprehension,
)


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _python_files() -> list[Path]:
    files: list[Path] = []
    for root_name in SCAN_ROOTS:
        root = ROOT / root_name
        if root.exists():
            files.extend(path for path in root.rglob("*.py") if path.is_file())
    return sorted(set(files), key=_relative)


def _bucket(path: Path) -> str:
    relative = _relative(path)
    return relative.split("/", 1)[0]


def _definition_rows(tree: ast.AST, path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        end_lineno = getattr(node, "end_lineno", None) or node.lineno
        subtree = list(ast.walk(node))
        decision_points = sum(isinstance(child, DECISION_NODE_TYPES) for child in subtree)
        decision_points += sum(
            max(0, len(child.values) - 1)
            for child in subtree
            if isinstance(child, ast.BoolOp)
        )
        rows.append(
            {
                "path": _relative(path),
                "kind": "class" if isinstance(node, ast.ClassDef) else "function",
                "name": node.name,
                "start_line": node.lineno,
                "end_line": end_lineno,
                "line_span": end_lineno - node.lineno + 1,
                "decision_point_proxy": decision_points,
            }
        )
    return rows


def build_report() -> dict[str, object]:
    files = _python_files()
    file_rows: list[dict[str, object]] = []
    definitions: list[dict[str, object]] = []
    syntax_issues: list[dict[str, object]] = []
    marker_counts = {"TODO": 0, "FIXME": 0, "HACK": 0}
    bucket_totals: dict[str, dict[str, int]] = {}

    for path in files:
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        markers = {"TODO": 0, "FIXME": 0, "HACK": 0}
        for match in MARKER_RE.finditer(text):
            marker = match.group(1).upper()
            markers[marker] += 1
            marker_counts[marker] += 1

        bucket = _bucket(path)
        totals = bucket_totals.setdefault(bucket, {"files": 0, "lines": 0, "nonblank_lines": 0})
        totals["files"] += 1
        totals["lines"] += len(lines)
        totals["nonblank_lines"] += sum(bool(line.strip()) for line in lines)

        row: dict[str, object] = {
            "path": _relative(path),
            "bucket": bucket,
            "lines": len(lines),
            "nonblank_lines": sum(bool(line.strip()) for line in lines),
            "todo_count": markers["TODO"],
            "fixme_count": markers["FIXME"],
            "hack_count": markers["HACK"],
        }
        try:
            tree = ast.parse(text, filename=_relative(path))
        except SyntaxError as exc:
            row["ast_parse_ok"] = False
            syntax_issues.append(
                {
                    "path": _relative(path),
                    "line": exc.lineno,
                    "offset": exc.offset,
                    "message": exc.msg,
                }
            )
        else:
            row["ast_parse_ok"] = True
            row["ast_node_count"] = sum(1 for _ in ast.walk(tree))
            definitions.extend(_definition_rows(tree, path))
        file_rows.append(row)

    largest_files = sorted(
        file_rows,
        key=lambda row: (-int(row["lines"]), str(row["path"])),
    )[:20]
    largest_definitions = sorted(
        definitions,
        key=lambda row: (-int(row["line_span"]), str(row["path"]), int(row["start_line"])),
    )[:20]
    decision_heavy_definitions = sorted(
        definitions,
        key=lambda row: (
            -int(row["decision_point_proxy"]),
            -int(row["line_span"]),
            str(row["path"]),
            int(row["start_line"]),
        ),
    )[:20]

    return {
        "schema": "qookey-quality-visibility-v0.1",
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
        "scan_roots": list(SCAN_ROOTS),
        "inventory": {
            "python_files": len(file_rows),
            "total_lines": sum(int(row["lines"]) for row in file_rows),
            "total_nonblank_lines": sum(int(row["nonblank_lines"]) for row in file_rows),
            "definitions": len(definitions),
            "syntax_issue_count": len(syntax_issues),
            "marker_counts": marker_counts,
            "by_root": dict(sorted(bucket_totals.items())),
        },
        "largest_python_files": largest_files,
        "largest_definitions": largest_definitions,
        "decision_point_proxy_leaders": decision_heavy_definitions,
        "syntax_issues": sorted(syntax_issues, key=lambda row: str(row["path"])),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="quality-visibility.json")
    args = parser.parse_args()

    report = build_report()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    inventory = report["inventory"]
    print(
        json.dumps(
            {
                "schema": report["schema"],
                "python_files": inventory["python_files"],
                "total_lines": inventory["total_lines"],
                "definitions": inventory["definitions"],
                "syntax_issue_count": inventory["syntax_issue_count"],
                "blocking_gate": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
