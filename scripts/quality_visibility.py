#!/usr/bin/env python3
"""Emit deterministic, non-blocking Python quality visibility for the repository.

This report is informational only. It does not enforce thresholds and must not
be used as a promotion, validation, holdout, source-switch, or trading gate.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import json
import re
import subprocess
from pathlib import Path
from typing import Any


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
BROAD_RUFF_SELECT = ("F", "I", "UP", "B", "C90")


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


def _callable_annotation_rows(tree: ast.AST, path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        positional = [*node.args.posonlyargs, *node.args.args]
        parameter_nodes: list[ast.arg] = list(positional)
        parameter_nodes.extend(node.args.kwonlyargs)
        if node.args.vararg is not None:
            parameter_nodes.append(node.args.vararg)
        if node.args.kwarg is not None:
            parameter_nodes.append(node.args.kwarg)

        ignored_receiver: str | None = None
        if positional and positional[0].arg in {"self", "cls"}:
            ignored_receiver = positional[0].arg
            parameter_nodes = [arg for arg in parameter_nodes if arg is not positional[0]]

        missing_parameters = sorted(
            arg.arg for arg in parameter_nodes if arg.annotation is None
        )
        parameter_count = len(parameter_nodes)
        annotated_parameter_count = parameter_count - len(missing_parameters)
        return_annotated = node.returns is not None

        rows.append(
            {
                "path": _relative(path),
                "name": node.name,
                "line": node.lineno,
                "ignored_receiver": ignored_receiver,
                "parameter_count": parameter_count,
                "annotated_parameter_count": annotated_parameter_count,
                "parameter_annotation_fraction": (
                    1.0
                    if parameter_count == 0
                    else round(annotated_parameter_count / parameter_count, 6)
                ),
                "missing_parameter_annotations": missing_parameters,
                "return_annotated": return_annotated,
                "fully_annotated": not missing_parameters and return_annotated,
            }
        )
    return rows


def _loaded_names(tree: ast.AST) -> Counter[str]:
    names: Counter[str] = Counter()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            names[node.id] += 1
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
            names[node.attr] += 1
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names[alias.name.rsplit(".", 1)[-1]] += 1
    return names


def _private_dead_code_candidates(
    parsed: list[tuple[Path, ast.AST]],
) -> list[dict[str, object]]:
    references: Counter[str] = Counter()
    for _, tree in parsed:
        references.update(_loaded_names(tree))

    candidates: list[dict[str, object]] = []
    for path, tree in parsed:
        if _bucket(path) == "tests":
            continue
        for node in getattr(tree, "body", ()):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if not node.name.startswith("_") or node.name.startswith("__"):
                continue
            if references[node.name] != 0:
                continue
            candidates.append(
                {
                    "path": _relative(path),
                    "kind": "class" if isinstance(node, ast.ClassDef) else "function",
                    "name": node.name,
                    "line": node.lineno,
                    "observed_static_reference_count": 0,
                    "heuristic_only": True,
                }
            )
    return sorted(
        candidates,
        key=lambda row: (str(row["path"]), int(row["line"]), str(row["name"])),
    )


def _broad_ruff_visibility() -> dict[str, object]:
    command = [
        "ruff",
        "check",
        *SCAN_ROOTS,
        "--select",
        ",".join(BROAD_RUFF_SELECT),
        "--output-format",
        "json",
        "--exit-zero",
        "--no-cache",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {
            "tool": "ruff",
            "available": False,
            "rules": list(BROAD_RUFF_SELECT),
            "diagnostic_count": None,
            "error": type(exc).__name__,
        }

    try:
        raw = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError:
        return {
            "tool": "ruff",
            "available": True,
            "rules": list(BROAD_RUFF_SELECT),
            "diagnostic_count": None,
            "parse_error": True,
            "stderr": completed.stderr[-2000:],
        }

    diagnostics: list[dict[str, Any]] = []
    by_code: Counter[str] = Counter()
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "UNKNOWN")
        by_code[code] += 1
        filename = str(item.get("filename") or "")
        try:
            display_path = Path(filename).resolve().relative_to(ROOT).as_posix()
        except (OSError, ValueError):
            display_path = filename
        location = item.get("location") if isinstance(item.get("location"), dict) else {}
        diagnostics.append(
            {
                "code": code,
                "path": display_path,
                "line": location.get("row"),
                "column": location.get("column"),
                "message": item.get("message"),
            }
        )

    diagnostics.sort(
        key=lambda row: (
            str(row["path"]),
            int(row["line"] or 0),
            int(row["column"] or 0),
            str(row["code"]),
        )
    )
    return {
        "tool": "ruff",
        "available": True,
        "rules": list(BROAD_RUFF_SELECT),
        "blocking_gate": False,
        "diagnostic_count": len(diagnostics),
        "by_code": dict(sorted(by_code.items())),
        "diagnostics": diagnostics[:500],
        "diagnostics_truncated": len(diagnostics) > 500,
    }


def build_report(*, include_broad_ruff: bool = True) -> dict[str, object]:
    files = _python_files()
    file_rows: list[dict[str, object]] = []
    definitions: list[dict[str, object]] = []
    annotations: list[dict[str, object]] = []
    parsed: list[tuple[Path, ast.AST]] = []
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
        totals = bucket_totals.setdefault(
            bucket,
            {"files": 0, "lines": 0, "nonblank_lines": 0},
        )
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
            parsed.append((path, tree))
            definitions.extend(_definition_rows(tree, path))
            annotations.extend(_callable_annotation_rows(tree, path))
        file_rows.append(row)

    largest_files = sorted(
        file_rows,
        key=lambda row: (-int(row["lines"]), str(row["path"])),
    )[:20]
    largest_definitions = sorted(
        definitions,
        key=lambda row: (
            -int(row["line_span"]),
            str(row["path"]),
            int(row["start_line"]),
        ),
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

    callable_count = len(annotations)
    fully_annotated_count = sum(bool(row["fully_annotated"]) for row in annotations)
    parameter_count = sum(int(row["parameter_count"]) for row in annotations)
    annotated_parameter_count = sum(
        int(row["annotated_parameter_count"]) for row in annotations
    )
    return_annotated_count = sum(bool(row["return_annotated"]) for row in annotations)
    incomplete_annotations = sorted(
        (row for row in annotations if not bool(row["fully_annotated"])),
        key=lambda row: (str(row["path"]), int(row["line"]), str(row["name"])),
    )

    report: dict[str, object] = {
        "schema": "qookey-quality-visibility-v0.2",
        "policy": {
            "informational_only": True,
            "blocking_gate": False,
            "thresholds_enforced": False,
            "semantic_type_checker_run": False,
            "dead_code_candidates_are_heuristic": True,
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
            "total_nonblank_lines": sum(
                int(row["nonblank_lines"]) for row in file_rows
            ),
            "definitions": len(definitions),
            "syntax_issue_count": len(syntax_issues),
            "marker_counts": marker_counts,
            "by_root": dict(sorted(bucket_totals.items())),
        },
        "annotation_visibility": {
            "callables": callable_count,
            "fully_annotated_callables": fully_annotated_count,
            "fully_annotated_callable_fraction": (
                1.0
                if callable_count == 0
                else round(fully_annotated_count / callable_count, 6)
            ),
            "parameters": parameter_count,
            "annotated_parameters": annotated_parameter_count,
            "parameter_annotation_fraction": (
                1.0
                if parameter_count == 0
                else round(annotated_parameter_count / parameter_count, 6)
            ),
            "return_annotated_callables": return_annotated_count,
            "return_annotation_fraction": (
                1.0
                if callable_count == 0
                else round(return_annotated_count / callable_count, 6)
            ),
            "incomplete_annotation_rows": incomplete_annotations[:500],
            "rows_truncated": len(incomplete_annotations) > 500,
        },
        "dead_code_visibility": {
            "scope": "unreferenced_private_module_level_definitions_only",
            "heuristic_only": True,
            "candidates": _private_dead_code_candidates(parsed),
        },
        "largest_python_files": largest_files,
        "largest_definitions": largest_definitions,
        "decision_point_proxy_leaders": decision_heavy_definitions,
        "syntax_issues": sorted(syntax_issues, key=lambda row: str(row["path"])),
    }
    report["broad_ruff_visibility"] = (
        _broad_ruff_visibility()
        if include_broad_ruff
        else {
            "tool": "ruff",
            "available": None,
            "skipped_for_test": True,
            "rules": list(BROAD_RUFF_SELECT),
        }
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="quality-visibility.json")
    args = parser.parse_args()

    report = build_report()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    inventory = report["inventory"]
    annotations = report["annotation_visibility"]
    broad_ruff = report["broad_ruff_visibility"]
    print(
        json.dumps(
            {
                "schema": report["schema"],
                "python_files": inventory["python_files"],
                "total_lines": inventory["total_lines"],
                "definitions": inventory["definitions"],
                "syntax_issue_count": inventory["syntax_issue_count"],
                "fully_annotated_callable_fraction": annotations[
                    "fully_annotated_callable_fraction"
                ],
                "broad_ruff_diagnostic_count": broad_ruff.get("diagnostic_count"),
                "blocking_gate": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
