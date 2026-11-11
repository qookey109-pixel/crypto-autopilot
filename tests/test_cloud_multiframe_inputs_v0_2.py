from __future__ import annotations

import importlib
import importlib.util

import pytest

from crypto_autopilot.features.regime import (
    MarketRegimeObservation,
    build_market_regime_series,
)
from test_cloud_multiframe_inputs_v0_1 import AS_OF, _bars, _fixture


def test_full_regime_warmup_requires_forty_aligned_breadth_bars():
    name = "crypto_autopilot.paper.cloud_multiframe_inputs_v0_2"
    assert importlib.util.find_spec(name) is not None, "full regime warmup successor missing"
    module = importlib.import_module(name)
    old_breadth, references, candidates = _fixture()
    breadth = {symbol: _bars(14_400_000, 40) for symbol in old_breadth}
    result = module.validate_multiframe_inputs(
        as_of_ms=AS_OF, breadth=breadth, references=references, candidates=candidates,
    )
    assert len(result.breadth_series) == 21
    assert all(item.ready for item in result.breadth_series)
    btc = result.reference_bars["BTC_USDT_PERP"]
    eth = result.reference_bars["ETH_USDT_PERP"]
    assert [item.bar_time_ms for item in result.breadth_series] == [bar.time_ms for bar in btc]
    observations = tuple(
        MarketRegimeObservation(
            time_ms=snapshot.bar_time_ms,
            available_at_ms=snapshot.available_at_ms,
            btc_close=btc[i].close,
            eth_close=eth[i].close,
            total3_value=1000.0 + i,
            btc_dominance_pct=50.0,
            alt_breadth_above_ema20=snapshot.above_ema20_ratio,
            alt_breadth_positive_momentum=snapshot.positive_momentum_ratio,
        )
        for i, snapshot in enumerate(result.breadth_series)
    )
    assert build_market_regime_series(observations, "4H")[-1].ready
    assert result.source_verified is False
    assert result.strategy_authorized is False
    with pytest.raises(ValueError):
        module.validate_multiframe_inputs(
            as_of_ms=AS_OF, breadth=old_breadth, references=references, candidates=candidates,
        )


def test_missing_warmup_bar_is_rejected():
    name = "crypto_autopilot.paper.cloud_multiframe_inputs_v0_2"
    assert importlib.util.find_spec(name) is not None, "full regime warmup successor missing"
    module = importlib.import_module(name)
    old_breadth, references, candidates = _fixture()
    breadth = {symbol: _bars(14_400_000, 40) for symbol in old_breadth}
    symbol = next(iter(breadth))
    breadth[symbol] = breadth[symbol][1:]
    with pytest.raises(ValueError):
        module.validate_multiframe_inputs(
            as_of_ms=AS_OF, breadth=breadth, references=references, candidates=candidates,
        )
