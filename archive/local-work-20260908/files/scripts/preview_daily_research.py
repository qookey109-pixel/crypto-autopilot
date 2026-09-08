#!/usr/bin/env python3
"""Print a fixed synthetic shortlist demonstration; no market inputs or output files."""
from __future__ import annotations

import json
from pathlib import Path

from crypto_autopilot.daily_research_preview import (
    DENIALS, PROVIDER, build_daily_research_preview,
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / "config/paper_training_v0_1.json").read_text())
    observed = "2024-01-01T01:00:00Z"
    # Manually specified scores exercise presentation only, not strategy performance.
    rows = [
        ("BTC_USDT_PERP", 82, True),
        ("ETH_USDT_PERP", 88, True),
        ("SOL_USDT_PERP", 95, False),
    ]
    report = {
        "schema": "pionex-public-paper-training-run-v0.1",
        "status": "PASS", "mode": "PAPER_TRAINING_ONLY",
        "provider": PROVIDER, "dataClass": "SYNTHETIC_FIXTURE",
        "observedAtUtc": observed,
        "authority": {key: False for key in DENIALS},
        "latestCandidates": [{
            "symbol": symbol, "score": score, "eligible": eligible,
            "signal_time_ms": 1704070800000 - 900000,
            "reasons": ["eligible_paper_candidate" if eligible else "trend_strength_below_gate"],
        } for symbol, score, eligible in rows],
    }
    universe = {
        "provider": PROVIDER, "dataClass": "SYNTHETIC_FIXTURE",
        "observedAtUtc": observed, "symbols": [row[0] for row in rows],
    }
    result = build_daily_research_preview(
        report, universe, as_of_utc=observed,
        minimum_score=config["candidate_thresholds"]["minimum_candidate_score"],
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if result["status"] == "PREVIEW_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
