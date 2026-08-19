from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.provider_metadata_capture_v0_8 import (
    guarded_capture_entrypoint,
    validate_cutover_contract,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("validate", "guard"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = validate_cutover_contract() if args.mode == "validate" else guarded_capture_entrypoint()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
