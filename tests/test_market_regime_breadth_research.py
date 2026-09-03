from __future__ import annotations

import pytest

from crypto_autopilot.features.regime import (
    MarketRegimeObservation,
    build_alt_breadth_series,
    build_market_regime_series,
    latest_market_regime_as_of,
)
from crypto_autopilot.historical import INTERVAL_MS
from crypto_autopilot.models import Candle


STEP = INTERVAL_MS["4H"]


def _candles(base: float, slope: float, count: int = 25) -> tuple[Candle, ...]:
    output = []
    for index in range(count):
        close = base + slope * index
        output.append(
            Candle(
                time_ms=index * STEP,
                open=close,
                high=close + 1.0,
                low=max(0.01, close - 1.0),
                close=close,
                volume=1000.0 + index,
            )
        )
    return tuple(output)


def _observation(
    index: int,
    *,
    btc: float,
    eth: float,
    total3: float,
    dominance: float,
    breadth_ema: float,
    breadth_momentum: float,
) -> MarketRegimeObservation:
    return MarketRegimeObservation(
        time_ms=index * STEP,
        available_at_ms=(index + 1) * STEP,
        btc_close=btc,
        eth_close=eth,
        total3_value=total3,
        btc_dominance_pct=dominance,
        alt_breadth_above_ema20=breadth_ema,
        alt_breadth_positive_momentum=breadth_momentum,
    )


def test_fixed_universe_breadth_is_equal_weight_and_causal() -> None:
    markets = {
        **{f"UP{index}USDT": _candles(20.0 + index, 0.5) for index in range(15)},
        **{f"DOWN{index}USDT": _candles(50.0 + index, -0.5) for index in range(5)},
        "BTCUSDT": _candles(100.0, 10.0),
        "ETHUSDT": _candles(50.0, 5.0),
    }

    series = build_alt_breadth_series(markets, "4H")

    assert len(series) == 25
    assert series[18].above_ema20_ratio is None
    assert series[19].above_ema20_ratio == pytest.approx(0.75)
    assert series[19].positive_momentum_ratio == pytest.approx(0.75)
    assert series[19].universe_size == 20
    assert series[19].available_at_ms == 20 * STEP


def test_breadth_fails_closed_on_misaligned_market() -> None:
    markets = {f"ALT{index}USDT": _candles(20.0 + index, 0.2) for index in range(20)}
    shifted = list(markets["ALT0USDT"])
    shifted[-1] = Candle(
        time_ms=shifted[-1].time_ms + STEP,
        open=shifted[-1].open,
        high=shifted[-1].high,
        low=shifted[-1].low,
        close=shifted[-1].close,
        volume=shifted[-1].volume,
    )
    markets["ALT0USDT"] = tuple(shifted)

    with pytest.raises(ValueError, match="aligned timestamp grid"):
        build_alt_breadth_series(markets, "4H")


def test_alt_expansion_requires_broad_confirmation() -> None:
    observations = (
        _observation(
            0,
            btc=100.0,
            eth=10.0,
            total3=1000.0,
            dominance=50.0,
            breadth_ema=0.40,
            breadth_momentum=0.40,
        ),
        _observation(
            1,
            btc=104.0,
            eth=11.0,
            total3=1080.0,
            dominance=49.0,
            breadth_ema=0.65,
            breadth_momentum=0.60,
        ),
        _observation(
            2,
            btc=110.0,
            eth=13.0,
            total3=1200.0,
            dominance=48.0,
            breadth_ema=0.80,
            breadth_momentum=0.75,
        ),
    )

    series = build_market_regime_series(observations, "4H", lookback_bars=2)

    assert series[0].state == "INSUFFICIENT"
    assert series[1].state == "INSUFFICIENT"
    assert series[2].state == "ALT_EXPANSION"
    assert series[2].alt_expansion_votes == 5
    assert series[2].ready is True


def test_btc_concentration_state_is_not_an_altcoin_buy_signal() -> None:
    observations = (
        _observation(
            0,
            btc=100.0,
            eth=10.0,
            total3=1000.0,
            dominance=50.0,
            breadth_ema=0.60,
            breadth_momentum=0.60,
        ),
        _observation(
            1,
            btc=108.0,
            eth=10.3,
            total3=1020.0,
            dominance=51.0,
            breadth_ema=0.45,
            breadth_momentum=0.45,
        ),
        _observation(
            2,
            btc=120.0,
            eth=10.5,
            total3=1050.0,
            dominance=52.0,
            breadth_ema=0.30,
            breadth_momentum=0.35,
        ),
    )

    series = build_market_regime_series(observations, "4H", lookback_bars=2)

    assert series[2].state == "BTC_CONCENTRATION"
    assert series[2].btc_concentration_votes == 5


def test_broad_risk_off_state_is_symmetric_research_evidence_only() -> None:
    observations = (
        _observation(
            0,
            btc=100.0,
            eth=10.0,
            total3=1000.0,
            dominance=50.0,
            breadth_ema=0.60,
            breadth_momentum=0.60,
        ),
        _observation(
            1,
            btc=95.0,
            eth=9.0,
            total3=900.0,
            dominance=50.5,
            breadth_ema=0.40,
            breadth_momentum=0.40,
        ),
        _observation(
            2,
            btc=90.0,
            eth=8.0,
            total3=800.0,
            dominance=51.0,
            breadth_ema=0.30,
            breadth_momentum=0.25,
        ),
    )

    series = build_market_regime_series(observations, "4H", lookback_bars=2)

    assert series[2].state == "BROAD_RISK_OFF"
    assert series[2].broad_risk_off_votes == 5


def test_as_of_reader_never_returns_future_regime_evidence() -> None:
    observations = tuple(
        _observation(
            index,
            btc=100.0 + index,
            eth=10.0 + index * 0.2,
            total3=1000.0 + index * 20.0,
            dominance=50.0 - index * 0.1,
            breadth_ema=0.60,
            breadth_momentum=0.60,
        )
        for index in range(4)
    )
    series = build_market_regime_series(observations, "4H", lookback_bars=2)

    assert latest_market_regime_as_of(series, STEP - 1) is None
    assert latest_market_regime_as_of(series, STEP) == series[0]
    assert latest_market_regime_as_of(series, 3 * STEP - 1) == series[1]
    assert latest_market_regime_as_of(series, 3 * STEP, require_ready=True) == series[2]


def test_regime_observations_fail_closed_on_bad_cadence_or_breadth() -> None:
    good = _observation(
        0,
        btc=100.0,
        eth=10.0,
        total3=1000.0,
        dominance=50.0,
        breadth_ema=0.50,
        breadth_momentum=0.50,
    )
    bad_ratio = MarketRegimeObservation(
        time_ms=STEP,
        available_at_ms=2 * STEP,
        btc_close=101.0,
        eth_close=10.1,
        total3_value=1010.0,
        btc_dominance_pct=50.0,
        alt_breadth_above_ema20=1.01,
        alt_breadth_positive_momentum=0.50,
    )
    with pytest.raises(ValueError, match="Breadth ratios"):
        build_market_regime_series((good, bad_ratio), "4H", lookback_bars=1)

    bad_cadence = _observation(
        2,
        btc=101.0,
        eth=10.1,
        total3=1010.0,
        dominance=50.0,
        breadth_ema=0.50,
        breadth_momentum=0.50,
    )
    with pytest.raises(ValueError, match="exact aligned bar grid"):
        build_market_regime_series((good, bad_cadence), "4H", lookback_bars=1)
