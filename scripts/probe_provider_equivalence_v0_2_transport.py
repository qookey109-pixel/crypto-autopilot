from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.provider_transport_probe_v0_2 import (
    result_exit_code,
    run_local_transport_probe,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the frozen V0.2 local provider transport connectivity probe."
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = run_local_transport_probe()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return result_exit_code(result)


if __name__ == "__main__":
    raise SystemExit(main())
