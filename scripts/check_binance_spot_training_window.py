from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from crypto_autopilot.training.quality import (
    load_v0_3_bootstrap_baseline,
    load_v0_5_authority_pair,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed schedule guard for Binance Spot online training")
    parser.add_argument(
        "--config", default="config/binance_spot_r2_training_governance_v0_5.json"
    )
    parser.add_argument("--now-utc")
    parser.add_argument("--github-output")
    args = parser.parse_args()

    config_path = Path(args.config)
    config_payload = config_path.read_bytes()
    config = json.loads(config_payload)
    _, governance_contract = load_v0_5_authority_pair(
        config,
        config_path=config_path,
        config_payload=config_payload,
        repository_root=REPOSITORY_ROOT,
    )
    baseline = load_v0_3_bootstrap_baseline(
        config,
        repository_root=REPOSITORY_ROOT,
    )
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
        "governance_contract": governance_contract,
        "bootstrap_baseline_schema": baseline["schema"],
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
