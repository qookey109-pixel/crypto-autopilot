from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "config/provider_equivalence_v0_11_synthetic_failure_rehearsal_v0_1.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    protocol = json.loads(MATRIX.read_text(encoding="utf-8"))
    scenarios = protocol["rehearsal_matrix"]
    selectors = [scenario["pytest_selector"] for scenario in scenarios]
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *selectors],
        cwd=ROOT,
        check=False,
    )

    passed = completed.returncode == 0
    payload = {
        "schema": "provider-equivalence-v0-11-synthetic-failure-rehearsal-result-v0.1",
        "status": "PASS" if passed else "FAIL",
        "stage": (
            "PROVIDER_EQUIVALENCE_V0_11_SYNTHETIC_FAILURE_REHEARSAL_PASS"
            if passed
            else "PROVIDER_EQUIVALENCE_V0_11_SYNTHETIC_FAILURE_REHEARSAL_FAIL"
        ),
        "protocol": "provider_equivalence_v0_11_synthetic_failure_rehearsal_v0_1",
        "scenario_count": len(scenarios),
        "scenario_ids": [scenario["id"] for scenario in scenarios],
        "synthetic_fixtures_only": True,
        "production_metadata_evidence_consumed": False,
        "r2_client_constructed": False,
        "r2_reads_performed": False,
        "r2_writes_performed": False,
        "provider_requests_performed": 0,
        "render_requests_performed": 0,
        "capture_artifacts_read": False,
        "holdout_candles_accessed": False,
        "holdout_evaluated": False,
        "holdout_access_authorized": False,
        "source_switch_authorized": False,
        "w1_materialization_authorized": False,
        "real_money_order_authorized": False,
        "live_trading_authorized": False,
        "interpretation": (
            "Synthetic regression rehearsal only; PASS is not production metadata stability evidence "
            "and does not authorize R2 production evaluation or holdout access."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
