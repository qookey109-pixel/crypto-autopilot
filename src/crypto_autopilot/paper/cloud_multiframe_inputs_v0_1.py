"""Offline validation of prepared multi-timeframe market inputs.

Caller-provided candles are not authenticated provider evidence or strategy
authority. This module performs no network, R2, D1, or scheduling operations.
"""
from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from crypto_autopilot.features.regime import AltBreadthSnapshot, build_alt_breadth_series
from crypto_autopilot.models import Candle
from crypto_autopilot.paper.cloud_market_v0_1 import EARLIEST_CANDLE_MS
from crypto_autopilot.technical import TechnicalSnapshot, build_technical_series, latest_closed_snapshot

_BREADTH = frozenset((
    "AAVE_USDT_PERP", "ADA_USDT_PERP", "APT_USDT_PERP", "ARB_USDT_PERP",
    "AVAX_USDT_PERP", "BCH_USDT_PERP", "BNB_USDT_PERP", "CRV_USDT_PERP",
    "DOGE_USDT_PERP", "DOT_USDT_PERP", "HYPE_USDT_PERP", "INJ_USDT_PERP",
    "LINK_USDT_PERP", "LTC_USDT_PERP", "NEAR_USDT_PERP", "PEPE_USDT_PERP",
    "SHIB_USDT_PERP", "SOL_USDT_PERP", "SUI_USDT_PERP", "TRX_USDT_PERP",
    "UNI_USDT_PERP", "XLM_USDT_PERP", "XRP_USDT_PERP",
))
_REFERENCES = frozenset(("BTC_USDT_PERP", "ETH_USDT_PERP"))
_SYMBOL = re.compile(r"^[A-Z0-9]{1,20}_USDT_PERP$")


@dataclass(frozen=True, slots=True)
class MultiframeInputs:
    breadth: AltBreadthSnapshot
    candidate_technical: Mapping[str, TechnicalSnapshot]
    source_verified: bool = False
    strategy_authorized: bool = False


def _closed_bars(
    bars: Sequence[Candle], *, interval_ms: int, count: int, as_of_ms: int,
) -> tuple[Candle, ...]:
    if isinstance(bars, (str, bytes)) or not isinstance(bars, Sequence) or len(bars) != count:
        raise ValueError("BAR_COUNT_INVALID")
    last = as_of_ms // interval_ms * interval_ms - interval_ms
    first = last - (count - 1) * interval_ms
    if first < EARLIEST_CANDLE_MS:
        raise ValueError("HOLDOUT_OR_PRE_AUTHORITY_WINDOW")
    result = tuple(bars)
    for index, candle in enumerate(result):
        if type(candle) is not Candle or type(candle.time_ms) is not int:
            raise ValueError("BAR_INVALID")
        if candle.time_ms != first + index * interval_ms:
            raise ValueError("BAR_GRID_INVALID")
        values = (candle.open, candle.high, candle.low, candle.close, candle.volume)
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in values):
            raise ValueError("BAR_VALUE_INVALID")
        if min(values[:4]) <= 0 or candle.volume < 0:
            raise ValueError("BAR_VALUE_INVALID")
        if candle.low > min(candle.open, candle.close) or candle.high < max(candle.open, candle.close):
            raise ValueError("BAR_OHLC_INVALID")
    return result


def validate_multiframe_inputs(
    *, as_of_ms: int, breadth: Mapping[str, Sequence[Candle]],
    references: Mapping[str, Sequence[Candle]], candidates: Mapping[str, Sequence[Candle]],
) -> MultiframeInputs:
    """Validate fixed aligned bars and reuse existing calculations in memory only."""
    if type(as_of_ms) is not int or as_of_ms < 0:
        raise ValueError("AS_OF_INVALID")
    if not isinstance(breadth, Mapping) or set(breadth) != _BREADTH:
        raise ValueError("BREADTH_MEMBERSHIP_INVALID")
    if not isinstance(references, Mapping) or set(references) != _REFERENCES:
        raise ValueError("REFERENCE_MEMBERSHIP_INVALID")
    if not isinstance(candidates, Mapping) or len(candidates) > 5 or any(
        not isinstance(symbol, str) or not _SYMBOL.fullmatch(symbol) for symbol in candidates
    ):
        raise ValueError("CANDIDATE_MEMBERSHIP_INVALID")
    four_hour = 14_400_000
    checked = {
        symbol: _closed_bars(rows, interval_ms=four_hour, count=21, as_of_ms=as_of_ms)
        for symbol, rows in breadth.items()
    }
    for rows in references.values():
        _closed_bars(rows, interval_ms=four_hour, count=21, as_of_ms=as_of_ms)
    series = build_alt_breadth_series(checked, "4H")
    if not series or series[-1].above_ema20_ratio is None or series[-1].positive_momentum_ratio is None:
        raise ValueError("BREADTH_NOT_READY")
    technical = {}
    for symbol, rows in candidates.items():
        bars = _closed_bars(rows, interval_ms=900_000, count=200, as_of_ms=as_of_ms)
        snapshots = build_technical_series(bars, "15M")
        latest = latest_closed_snapshot(snapshots, as_of_ms, require_ready=True)
        if latest is None or not latest.ready_v0_2:
            raise ValueError("CANDIDATE_NOT_READY")
        technical[symbol] = latest
    return MultiframeInputs(breadth=series[-1], candidate_technical=technical)
