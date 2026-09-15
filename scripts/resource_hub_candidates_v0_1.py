#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.toolkit.resource_hub_supply_chain import build_candidate_registry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a read-only Crypto Autopilot integration-candidate registry from AI Resource Hub."
    )
    parser.add_argument("--input", required=True, help="Local Resource Hub resources.json path")
    parser.add_argument(
        "--policy",
        default="config/resource_hub_supply_chain_v0_1.json",
        help="Repository-relative supply-chain policy path",
    )
    parser.add_argument(
        "--source-commit",
        required=True,
        help="Exact lowercase 40-character AI Resource Hub commit SHA",
    )
    parser.add_argument("--output", help="Optional output JSON path; stdout when omitted")
    return parser.parse_args()


def load_json(path: str) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return payload


def main() -> int:
    args = parse_args()
    catalog = load_json(args.input)
    policy = load_json(args.policy)
    result = build_candidate_registry(catalog, policy, source_commit=args.source_commit)
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
