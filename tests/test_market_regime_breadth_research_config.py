from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_market_regime_breadth_research_authority_is_fail_closed() -> None:
    config = json.loads(
        (ROOT / "config" / "market_regime_breadth_research_v0_1.json").read_text()
    )

    assert config["version"] == "0.1.0"
    assert config["mode"] == "cross_market_regime_research_only"
    assert config["supported_intervals"] == ["4H", "1D"]

    breadth = config["breadth"]
    assert breadth["ema_period"] == 20
    assert breadth["momentum_lookback_bars"] == 5
    assert breadth["minimum_assets"] == 20
    assert breadth["majority_ratio"] == 0.5
    assert breadth["membership_policy"] == "fixed_exact_aligned_universe"
    assert breadth["missing_bar_policy"] == "fail_closed_no_fill_no_interpolation"
    assert breadth["weighting"] == "equal_weight"

    regime = config["regime"]
    assert regime["lookback_bars"] == 20
    assert regime["minimum_votes"] == 4
    assert regime["absolute_price_levels_used"] is False
    assert regime["kol_price_levels_allowed_as_parameters"] is False

    authority = config["authority"]
    assert authority["research_only"] is True
    for key, value in authority.items():
        if key != "research_only":
            assert value is False, key


def test_market_regime_research_does_not_modify_strategy_v0_1_contract() -> None:
    strategy = json.loads((ROOT / "config" / "strategy_v0_1.json").read_text())

    serialized = json.dumps(strategy, sort_keys=True)
    assert "market_regime_breadth_research_v0_1" not in serialized
    assert "ALT_EXPANSION" not in serialized
    assert "BTC_CONCENTRATION" not in serialized
    assert "BROAD_RISK_OFF" not in serialized
