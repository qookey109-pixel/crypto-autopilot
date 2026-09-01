from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.provider_metadata_capture_v0_12 import capture_v0_12


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("capture",), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = capture_v0_12()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
