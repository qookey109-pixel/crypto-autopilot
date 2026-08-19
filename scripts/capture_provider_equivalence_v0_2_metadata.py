from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.provider_metadata_capture_suspension_v0_2 import suspended_execution_result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("connectivity-preflight", "capture"),
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    # Latest authority supersedes the previously authorized GitHub-hosted
    # execution path. Do not contact providers or construct an R2 client until
    # a separately versioned transport connectivity PASS authority exists.
    result = suspended_execution_result(requested_mode=args.mode)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
