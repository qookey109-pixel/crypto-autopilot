from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed schedule guard for Binance Spot online training")
    parser.add_argument("--config", default="config/binance_spot_r2_automated_training_v0_3.json")
    parser.add_argument("--now-utc")
    parser.add_argument("--github-output")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    now = (
        datetime.fromisoformat(args.now_utc.replace("Z", "+00:00"))
        if args.now_utc
        else datetime.now(UTC)
    )
    stop = datetime.fromisoformat(config["schedule"]["provider_read_stop_utc"].replace("Z", "+00:00"))
    allowed = now < stop
    result = {
        "status": "PASS" if allowed else "SKIP",
        "stage": "ONLINE_TRAINING_WINDOW_OPEN" if allowed else "FROZEN_HOLDOUT_GUARD_STOP",
        "observed_at_utc": now.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "provider_read_stop_utc": stop.isoformat().replace("+00:00", "Z"),
        "run_allowed": allowed,
        "provider_requests_performed": 0,
        "r2_client_constructed": False,
        "r2_writes_performed": False,
        "holdout_accessed": False,
        "live_trading_authorized": False,
    }
    if args.github_output:
        with Path(args.github_output).open("a", encoding="utf-8") as handle:
            handle.write(f"run_allowed={'true' if allowed else 'false'}\n")
            handle.write(f"stage={result['stage']}\n")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
