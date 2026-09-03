from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from crypto_autopilot.historical import INTERVAL_MS
from crypto_autopilot.models import Candle
from crypto_autopilot.technical import build_technical_series


@dataclass(frozen=True, slots=True)
class AltBreadthSnapshot:
    """Cross-sectional breadth from one fixed, aligned closed-bar universe."""

    bar_time_ms: int
    available_at_ms: int
    universe_size: int
    above_ema20_ratio: float | None
    positive_momentum_ratio: float | None

    @property
    def ready(self) -> bool:
        return self.above_ema20_ratio is not None and self.positive_momentum_ratio is not None


@dataclass(frozen=True, slots=True)
class MarketRegimeObservation:
    """Aligned external/context values known no earlier than ``available_at_ms``.

    ``total3_value`` means aggregate crypto market capitalization excluding BTC
    and ETH. It is a semantic metric, not a dependency on any named charting
    vendor. ``btc_dominance_pct`` means BTC market capitalization divided by
    total crypto market capitalization, expressed as a percentage.
    """

    time_ms: int
    available_at_ms: int
    btc_close: float
    eth_close: float
    total3_value: float
    btc_dominance_pct: float
    alt_breadth_above_ema20: float
    alt_breadth_positive_momentum: float


@dataclass(frozen=True, slots=True)
class MarketRegimeSnapshot:
    """Causal cross-market regime evidence; never a trade decision."""

    bar_time_ms: int
    available_at_ms: int
    btc_return: float | None
    total3_return: float | None
    eth_btc_return: float | None
    btc_dominance_delta_pct_points: float | None
    alt_breadth_above_ema20: float | None
    alt_breadth_positive_momentum: float | None
    alt_expansion_votes: int
    btc_concentration_votes: int
    broad_risk_off_votes: int
    state: str

    @property
    def ready(self) -> bool:
        return all(
            value is not None
            for value in (
                self.btc_return,
                self.total3_return,
                self.eth_btc_return,
                self.btc_dominance_delta_pct_points,
                self.alt_breadth_above_ema20,
                self.alt_breadth_positive_momentum,
            )
        )


def build_alt_breadth_series(
    markets: Mapping[str, Sequence[Candle]],
    interval: str,
    *,
    excluded_symbols: Sequence[str] = ("BTCUSDT", "ETHUSDT"),
    momentum_lookback_bars: int = 5,
    minimum_assets: int = 20,
) -> tuple[AltBreadthSnapshot, ...]:
    """Build equal-weight fixed-universe breadth without filling missing bars.

    Every included market must have exactly the same timestamp grid. This is
    deliberately strict: changing membership, missing bars, interpolation and
    survivorship repair require separate research authority rather than being
    silently hidden inside the breadth metric.
    """

    if interval not in INTERVAL_MS:
        raise ValueError(f"Unsupported breadth interval: {interval}")
    if momentum_lookback_bars < 1:
        raise ValueError("momentum_lookback_bars must be positive")
    if minimum_assets < 1:
        raise ValueError("minimum_assets must be positive")

    excluded = {symbol.upper() for symbol in excluded_symbols}
    eligible = {
        symbol: tuple(candles)
        for symbol, candles in markets.items()
        if symbol.upper() not in excluded
    }
    if len(eligible) < minimum_assets:
        raise ValueError(
            f"Breadth universe has {len(eligible)} assets; minimum is {minimum_assets}"
        )

    ordered_symbols = tuple(sorted(eligible))
    first_symbol = ordered_symbols[0]
    reference_times = tuple(candle.time_ms for candle in eligible[first_symbol])
    if not reference_times:
        return ()

    technical_by_symbol = {}
    for symbol in ordered_symbols:
        candles = eligible[symbol]
        times = tuple(candle.time_ms for candle in candles)
        if times != reference_times:
            raise ValueError(
                f"Breadth market {symbol} does not match the fixed aligned timestamp grid"
            )
        technical_by_symbol[symbol] = build_technical_series(candles, interval)

    step_ms = INTERVAL_MS[interval]
    output: list[AltBreadthSnapshot] = []
    for index, bar_time_ms in enumerate(reference_times):
        above_ema20_ratio = None
        if all(technical_by_symbol[symbol][index].ema20 is not None for symbol in ordered_symbols):
            above_count = sum(
                technical_by_symbol[symbol][index].close
                > technical_by_symbol[symbol][index].ema20  # type: ignore[operator]
                for symbol in ordered_symbols
            )
            above_ema20_ratio = above_count / len(ordered_symbols)

        positive_momentum_ratio = None
        if index >= momentum_lookback_bars:
            positive_count = sum(
                eligible[symbol][index].close
                > eligible[symbol][index - momentum_lookback_bars].close
                for symbol in ordered_symbols
            )
            positive_momentum_ratio = positive_count / len(ordered_symbols)

        output.append(
            AltBreadthSnapshot(
                bar_time_ms=bar_time_ms,
                available_at_ms=bar_time_ms + step_ms,
                universe_size=len(ordered_symbols),
                above_ema20_ratio=above_ema20_ratio,
                positive_momentum_ratio=positive_momentum_ratio,
            )
        )

    return tuple(output)


def _validate_observations(
    observations: tuple[MarketRegimeObservation, ...], interval: str
) -> None:
    if interval not in INTERVAL_MS:
        raise ValueError(f"Unsupported market-regime interval: {interval}")
    if not observations:
        return

    step_ms = INTERVAL_MS[interval]
    previous_time = None
    previous_available_at = None
    for item in observations:
        values = (
            item.btc_close,
            item.eth_close,
            item.total3_value,
            item.btc_dominance_pct,
            item.alt_breadth_above_ema20,
            item.alt_breadth_positive_momentum,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Market-regime observations must be finite")
        if min(item.btc_close, item.eth_close, item.total3_value) <= 0:
            raise ValueError("Market-regime price and market-cap values must be positive")
        if not 0.0 < item.btc_dominance_pct <= 100.0:
            raise ValueError("btc_dominance_pct must be in (0, 100]")
        for ratio in (
            item.alt_breadth_above_ema20,
            item.alt_breadth_positive_momentum,
        ):
            if not 0.0 <= ratio <= 1.0:
                raise ValueError("Breadth ratios must be in [0, 1]")
        if item.available_at_ms < item.time_ms:
            raise ValueError("available_at_ms cannot precede the observation time")
        if previous_time is not None and item.time_ms - previous_time != step_ms:
            raise ValueError("Market-regime observations must use an exact aligned bar grid")
        if previous_available_at is not None and item.available_at_ms < previous_available_at:
            raise ValueError("Market-regime availability timestamps must be nondecreasing")
        previous_time = item.time_ms
        previous_available_at = item.available_at_ms


def _votes(*conditions: bool) -> int:
    return sum(bool(condition) for condition in conditions)


def build_market_regime_series(
    observations: Sequence[MarketRegimeObservation],
    interval: str,
    *,
    lookback_bars: int = 20,
    majority_ratio: float = 0.5,
    minimum_votes: int = 4,
) -> tuple[MarketRegimeSnapshot, ...]:
    """Build sign/majority-based cross-market regime evidence.

    No absolute BTC, TOTAL3 or dominance level is used. The classification is a
    descriptive research label only and does not modify strategy eligibility,
    score, risk, leverage or order behavior.
    """

    if lookback_bars < 1:
        raise ValueError("lookback_bars must be positive")
    if not 0.0 < majority_ratio < 1.0:
        raise ValueError("majority_ratio must be in (0, 1)")
    if not 1 <= minimum_votes <= 5:
        raise ValueError("minimum_votes must be between 1 and 5")

    source = tuple(observations)
    _validate_observations(source, interval)
    output: list[MarketRegimeSnapshot] = []

    for index, current in enumerate(source):
        if index < lookback_bars:
            output.append(
                MarketRegimeSnapshot(
                    bar_time_ms=current.time_ms,
                    available_at_ms=current.available_at_ms,
                    btc_return=None,
                    total3_return=None,
                    eth_btc_return=None,
                    btc_dominance_delta_pct_points=None,
                    alt_breadth_above_ema20=None,
                    alt_breadth_positive_momentum=None,
                    alt_expansion_votes=0,
                    btc_concentration_votes=0,
                    broad_risk_off_votes=0,
                    state="INSUFFICIENT",
                )
            )
            continue

        previous = source[index - lookback_bars]
        btc_return = current.btc_close / previous.btc_close - 1.0
        total3_return = current.total3_value / previous.total3_value - 1.0
        current_eth_btc = current.eth_close / current.btc_close
        previous_eth_btc = previous.eth_close / previous.btc_close
        eth_btc_return = current_eth_btc / previous_eth_btc - 1.0
        dominance_delta = current.btc_dominance_pct - previous.btc_dominance_pct
        breadth_ema = current.alt_breadth_above_ema20
        breadth_momentum = current.alt_breadth_positive_momentum

        alt_votes = _votes(
            total3_return > 0.0,
            dominance_delta < 0.0,
            eth_btc_return > 0.0,
            breadth_ema > majority_ratio,
            breadth_momentum > majority_ratio,
        )
        concentration_votes = _votes(
            btc_return > 0.0,
            dominance_delta > 0.0,
            eth_btc_return < 0.0,
            breadth_ema < majority_ratio,
            total3_return < btc_return,
        )
        risk_off_votes = _votes(
            btc_return < 0.0,
            total3_return < 0.0,
            eth_btc_return < 0.0,
            breadth_ema < majority_ratio,
            breadth_momentum < majority_ratio,
        )

        candidates = {
            "ALT_EXPANSION": alt_votes,
            "BTC_CONCENTRATION": concentration_votes,
            "BROAD_RISK_OFF": risk_off_votes,
        }
        best_vote_count = max(candidates.values())
        winners = tuple(state for state, votes in candidates.items() if votes == best_vote_count)
        state = winners[0] if best_vote_count >= minimum_votes and len(winners) == 1 else "MIXED"

        output.append(
            MarketRegimeSnapshot(
                bar_time_ms=current.time_ms,
                available_at_ms=current.available_at_ms,
                btc_return=btc_return,
                total3_return=total3_return,
                eth_btc_return=eth_btc_return,
                btc_dominance_delta_pct_points=dominance_delta,
                alt_breadth_above_ema20=breadth_ema,
                alt_breadth_positive_momentum=breadth_momentum,
                alt_expansion_votes=alt_votes,
                btc_concentration_votes=concentration_votes,
                broad_risk_off_votes=risk_off_votes,
                state=state,
            )
        )

    return tuple(output)


def latest_market_regime_as_of(
    series: Sequence[MarketRegimeSnapshot],
    as_of_ms: int,
    *,
    require_ready: bool = False,
) -> MarketRegimeSnapshot | None:
    """Return only regime evidence that was causally available by ``as_of_ms``."""

    if as_of_ms < 0:
        raise ValueError("as_of_ms cannot be negative")
    available = tuple(item for item in series if item.available_at_ms <= as_of_ms)
    if require_ready:
        available = tuple(item for item in available if item.ready)
    return available[-1] if available else None


def mask_market_regime_after(
    snapshot: MarketRegimeSnapshot, as_of_ms: int
) -> MarketRegimeSnapshot | None:
    """Fail closed when a historical snapshot was not yet available."""

    if as_of_ms < 0:
        raise ValueError("as_of_ms cannot be negative")
    if snapshot.available_at_ms > as_of_ms:
        return None
    return replace(snapshot)
