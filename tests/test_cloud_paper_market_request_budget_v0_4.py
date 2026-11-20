from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_regime_budget_includes_ema_then_regime_warmup():
    path = ROOT / "config/cloud_paper_market_request_budget_v0_4.json"
    assert path.exists(), "full regime warmup budget successor missing"
    contract = json.loads(path.read_text(encoding="utf-8"))
    bars = contract["warmup"]
    assert bars["four_hour_breadth_closed_bars_per_symbol"] == 40
    assert bars["four_hour_reference_closed_bars_per_symbol"] == 21
    assert bars["maximum_closed_bars_per_slot"] == 23 * 40 + 2 * 21 + 10 * 200
    assert contract["requests"]["total_calls_per_slot"] == 48
    assert contract["authority"] and all(value is False for value in contract["authority"].values())
