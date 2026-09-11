"""Fail-closed one-shot guard for the formally completed BTC fixed sample."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT = ROOT / "research/receipts/2026-09-11-simulation-btc-fixed-sample-v0-1-pass.json"

EXPECTED = {
    "schema": "simulation-btc-fixed-sample-receipt-v0.1",
    "status": "PASS",
    "claim": "BTC_FIXED_SAMPLE_READY",
    "scope": "BTC_FIXED_27_DAY_ENGINE_VALIDATION_ONLY",
    "full_simulation_ready": False,
    "full_universe_ready": False,
    "execution_authority_granted_by_this_receipt": False,
    "source_switch_authorized": False,
    "holdout_accessed": False,
    "live_trading_authorized": False,
    "real_money_orders_authorized": False,
    "r2_writes": False,
    "main_sha": "25cdf4a9cf66749885fb7b5c33046330870d19d8",
    "workflow_name": "BTC Fixed Sample Simulation V0.1",
    "workflow_run_id": "34615465566",
    "workflow_run_attempt": 1,
    "artifact_id": "10269674365",
    "artifact_zip_sha256": "3966385491520c9818309c4ad76a06de17c8d3c1c333274f6f08b2ef25958d9c",
    "report_sha256": "8cde42d1d52fffcaf39251a29541ac1c13a91658a5349ef664e7601d061ee2a5",
    "report_schema": "simulation-btc-run-v0.1",
    "report_status": "READY",
    "report_stage": "COMPLETE",
    "r2_get_attempts": 3,
    "blockers": [],
}


def completion_is_frozen(receipt_path: Path) -> bool:
    """Return False only when no receipt exists; malformed present evidence fails closed."""

    if not receipt_path.exists():
        return False
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("completion receipt is unreadable") from exc
    if not isinstance(receipt, dict):
        raise ValueError("completion receipt must be an object")
    for key, expected in EXPECTED.items():
        if receipt.get(key) != expected:
            raise ValueError(f"completion receipt mismatch: {key}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    try:
        complete = completion_is_frozen(args.receipt)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.github_output is not None:
        with args.github_output.open("a", encoding="utf-8") as handle:
            handle.write(f"complete={'true' if complete else 'false'}\n")
    print(json.dumps({"complete": complete, "r2_access_performed": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
