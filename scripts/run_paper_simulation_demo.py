#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.paper.simulation_demo import build_demo_payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the deterministic, synthetic, paper-only simulation demo."
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = build_demo_payload()
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
