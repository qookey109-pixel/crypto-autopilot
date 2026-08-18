#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.pilot_evidence import aggregate_pilot_evidence


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate Historical Backfill Pilot shard evidence.")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--shard-count", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    aggregate = aggregate_pilot_evidence(
        args.input_dir,
        year=args.year,
        shard_count=args.shard_count,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(aggregate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(aggregate, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
