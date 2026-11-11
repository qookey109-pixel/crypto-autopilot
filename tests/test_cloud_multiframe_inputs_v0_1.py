from __future__ import annotations

import importlib
import importlib.util
import json
from pathlib import Path

import pytest

from crypto_autopilot.models import Candle

ROOT = Path(__file__).resolve().parents[1]
AS_OF = 1_800_000_000_000


def _module():
    name = "crypto_autopilot.paper.cloud_multiframe_inputs_v0_1"
    assert importlib.util.find_spec(name) is not None, "multiframe validator missing"
    return importlib.import_module(name)


def _bars(step: int, count: int) -> tuple[Candle, ...]:
    last = AS_OF // step * step - step
    return tuple(
        Candle(time_ms=last - (count - 1 - i) * step, open=100 + i,
               high=102 + i, low=99 + i, close=101 + i, volume=10)
        for i in range(count)
    )


def _fixture():
    data = json.loads(
        (ROOT / "config/market_regime_pionex_breadth_universe_v0_1.json").read_text()
    )
    symbols = data["membership"]["instruments"]
    breadth = {symbol: _bars(14_400_000, 21) for symbol in symbols}
    references = {s: _bars(14_400_000, 21) for s in ("BTC_USDT_PERP", "ETH_USDT_PERP")}
    candidates = {"SOL_USDT_PERP": _bars(900_000, 200)}
    return breadth, references, candidates


def test_aligned_closed_bars_produce_only_offline_breadth_and_technical_evidence():
    module = _module()
    breadth, references, candidates = _fixture()
    result = module.validate_multiframe_inputs(
        as_of_ms=AS_OF, breadth=breadth, references=references, candidates=candidates,
    )
    assert result.reference_bars["BTC_USDT_PERP"] == references["BTC_USDT_PERP"]
    assert len(result.breadth_series) == 21
    assert result.breadth_series[-1] == result.breadth
    assert result.breadth.universe_size == 23
    assert result.breadth.available_at_ms == AS_OF // 14_400_000 * 14_400_000
    assert set(result.candidate_technical) == {"SOL_USDT_PERP"}
    assert result.candidate_technical["SOL_USDT_PERP"].ready_v0_2
    assert result.source_verified is False
    assert result.strategy_authorized is False


def test_missing_member_stale_reference_and_gapped_entry_fail_closed():
    module = _module()
    breadth, references, candidates = _fixture()
    missing = dict(breadth)
    missing.pop(next(iter(missing)))
    with pytest.raises(ValueError):
        module.validate_multiframe_inputs(
            as_of_ms=AS_OF, breadth=missing, references=references, candidates=candidates,
        )
    stale = dict(references)
    stale["BTC_USDT_PERP"] = references["BTC_USDT_PERP"][:-1]
    with pytest.raises(ValueError):
        module.validate_multiframe_inputs(
            as_of_ms=AS_OF, breadth=breadth, references=stale, candidates=candidates,
        )
    gapped = dict(candidates)
    gapped["SOL_USDT_PERP"] = candidates["SOL_USDT_PERP"][:40] + candidates["SOL_USDT_PERP"][41:]
    with pytest.raises(ValueError):
        module.validate_multiframe_inputs(
            as_of_ms=AS_OF, breadth=breadth, references=references, candidates=gapped,
        )


def test_future_misaligned_nonfinite_and_holdout_bars_fail_closed():
    module = _module()
    breadth, references, candidates = _fixture()
    invalid = list(candidates["SOL_USDT_PERP"])
    last = invalid[-1]
    invalid[-1] = Candle(last.time_ms + 900_000, last.open, last.high, last.low, last.close, last.volume)
    with pytest.raises(ValueError):
        module.validate_multiframe_inputs(as_of_ms=AS_OF, breadth=breadth, references=references,
                                          candidates={"SOL_USDT_PERP": invalid})
    invalid[-1] = Candle(last.time_ms, last.open, last.high, last.low, float("nan"), last.volume)
    with pytest.raises(ValueError):
        module.validate_multiframe_inputs(as_of_ms=AS_OF, breadth=breadth, references=references,
                                          candidates={"SOL_USDT_PERP": invalid})
    with pytest.raises(ValueError):
        module.validate_multiframe_inputs(as_of_ms=1_788_480_000_000, breadth=breadth,
                                          references=references, candidates=candidates)


def test_result_constructor_cannot_claim_source_or_strategy_authority():
    module = _module()
    breadth, references, candidates = _fixture()
    result = module.validate_multiframe_inputs(
        as_of_ms=AS_OF, breadth=breadth, references=references, candidates=candidates,
    )
    with pytest.raises(TypeError):
        module.MultiframeInputs(
            breadth_series=result.breadth_series, reference_bars=result.reference_bars,
            candidate_technical=result.candidate_technical, source_verified=True,
        )
    with pytest.raises(TypeError):
        module.MultiframeInputs(
            breadth_series=result.breadth_series, reference_bars=result.reference_bars,
            candidate_technical=result.candidate_technical, strategy_authorized=True,
        )
