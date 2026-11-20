from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_direct_regime_budget_includes_excluded_btc_and_eth() -> None:
    path = ROOT / "config/cloud_paper_market_request_budget_v0_3.json"
    assert path.exists(), "prepared direct-reference budget successor is missing"
    contract = json.loads(path.read_text(encoding="utf-8"))
    universe = json.loads(
        (ROOT / "config/market_regime_pionex_breadth_universe_v0_1.json").read_text(encoding="utf-8")
    )["membership"]
    symbols = set(universe["instruments"])
    references = set(contract["assumptions"]["reference_4h_symbols"])
    assert len(symbols) == 23
    assert references == {"BTC_USDT_PERP", "ETH_USDT_PERP"}
    assert symbols.isdisjoint(references)
    requests = contract["requests"]
    total = sum(requests[key] for key in (
        "shared_market_calls_per_slot", "four_hour_breadth_calls_per_slot",
        "four_hour_reference_calls_per_slot", "sixty_minute_candidate_calls_per_slot",
        "fifteen_minute_candidate_calls_per_slot", "execution_frame_calls_per_slot_max",
    ))
    assert total == requests["total_calls_per_slot"] == 48
    assert requests["minimum_shared_and_fixed_4h_calls_per_slot"] == 28
    assert requests["maximum_calls_per_utc_day"] == total * 96
    assert requests["maximum_calls_per_rolling_30_days"] == total * 96 * 30
    assert contract["warmup"]["maximum_closed_bars_per_slot"] == 25 * 21 + 10 * 200
    assert contract["assumptions"]["reuse_60m_as_4h_assumed"] is False
    assert contract["authority"] and all(value is False for value in contract["authority"].values())
