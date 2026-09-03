from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "failed_breakout_research_v0_1.json"


def test_failed_breakout_v0_1_is_research_only() -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))

    assert payload["status"] == "PREPARED_RESEARCH_ONLY"
    assert payload["candidate"]["hardcoded_market_price_levels"] is False
    assert payload["candidate"]["kol_price_levels_as_strategy_parameters"] is False
    assert payload["causality"]["closed_bars_only"] is True
    assert payload["causality"]["no_lookahead"] is True

    authority = payload["authority"]
    assert authority
    assert all(value is False for value in authority.values())


def test_failed_breakout_v0_1_initial_hypothesis_is_frozen() -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    resolution = payload["resolution"]

    assert resolution == {
        "followup_bars": 3,
        "acceptance_closes": 2,
        "acceptance_buffer_bps": 5.0,
        "failure_reentry_buffer_bps": 5.0,
        "statuses": ["PENDING", "ACCEPTED", "FAILED", "EXPIRED"],
    }
    assert payload["evaluation"]["parameter_tuning_from_replacement_holdout"] is False
