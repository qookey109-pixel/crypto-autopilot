from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .historical import INTERVAL_MS
from .market_structure import MarketStructureSnapshot, build_market_structure_series
from .models import Candle
from .technical import (
    TechnicalSnapshot,
    build_technical_series,
)


TECHNICAL_INTERVALS = ("4H", "60M", "15M")


@dataclass(frozen=True, slots=True)
class TechnicalTimeframeSnapshot:
    interval: str
    bar_time_ms: int
    available_at_ms: int
    technical: TechnicalSnapshot
    market_structure: MarketStructureSnapshot
    ready: bool

    @property
    def technical_features(self) -> TechnicalSnapshot:
        return self.technical

    @property
    def technical_snapshot(self) -> TechnicalSnapshot:
        return self.technical

    @property
    def structure_features(self) -> MarketStructureSnapshot:
        return self.market_structure

    @property
    def market_structure_features(self) -> MarketStructureSnapshot:
        return self.market_structure


@dataclass(frozen=True, slots=True)
class MultiTimeframeTechnicalSnapshot:
    symbol: str
    as_of_ms: int
    four_hour: TechnicalTimeframeSnapshot | None
    one_hour: TechnicalTimeframeSnapshot | None
    fifteen_minute: TechnicalTimeframeSnapshot | None
    ready: bool

    @property
    def timeframes(self) -> Mapping[str, TechnicalTimeframeSnapshot | None]:
        return {
            "4H": self.four_hour,
            "60M": self.one_hour,
            "15M": self.fifteen_minute,
        }


def build_technical_timeframe_series(
    candles: Sequence[Candle],
    interval: str,
    *,
    rolling_window: int = 20,
    swing_left: int = 2,
    swing_right: int = 2,
) -> tuple[TechnicalTimeframeSnapshot, ...]:
    if interval not in INTERVAL_MS:
        raise ValueError(f"Unsupported technical interval: {interval}")
    technical = build_technical_series(candles, interval)
    structure = build_market_structure_series(
        candles,
        interval,
        rolling_window=rolling_window,
        swing_left=swing_left,
        swing_right=swing_right,
        technical_series=technical,
    )
    return tuple(
        TechnicalTimeframeSnapshot(
            interval=interval,
            bar_time_ms=technical_snapshot.bar_time_ms,
            available_at_ms=technical_snapshot.available_at_ms,
            technical=technical_snapshot,
            market_structure=structure_snapshot,
            ready=technical_snapshot.ready_v0_2 and structure_snapshot.ready,
        )
        for technical_snapshot, structure_snapshot in zip(technical, structure)
    )


def latest_technical_timeframe_as_of(
    series: Sequence[TechnicalTimeframeSnapshot],
    as_of_ms: int,
) -> TechnicalTimeframeSnapshot | None:
    if as_of_ms < 0:
        raise ValueError("as_of_ms cannot be negative")
    available = tuple(snapshot for snapshot in series if snapshot.available_at_ms <= as_of_ms)
    return available[-1] if available else None


def build_multi_timeframe_snapshot(
    *,
    symbol: str,
    as_of_ms: int,
    candles_by_interval: Mapping[str, Sequence[Candle]],
    rolling_window: int = 20,
    swing_left: int = 2,
    swing_right: int = 2,
) -> MultiTimeframeTechnicalSnapshot:
    """Align 4H, 60M and 15M evidence without using future bars.

    Missing timeframes produce a non-ready snapshot. Invalid candle audits
    fail closed by propagating ``TechnicalDataError`` rather than repairing or
    substituting another interval.
    """
    if as_of_ms < 0:
        raise ValueError("as_of_ms cannot be negative")

    snapshots: dict[str, TechnicalTimeframeSnapshot | None] = {}
    for interval in TECHNICAL_INTERVALS:
        candles = candles_by_interval.get(interval)
        if candles is None:
            snapshots[interval] = None
            continue
        series = build_technical_timeframe_series(
            candles,
            interval,
            rolling_window=rolling_window,
            swing_left=swing_left,
            swing_right=swing_right,
        )
        snapshots[interval] = latest_technical_timeframe_as_of(series, as_of_ms)

    four_hour = snapshots["4H"]
    one_hour = snapshots["60M"]
    fifteen_minute = snapshots["15M"]
    ready = all(
        snapshot is not None and snapshot.ready
        for snapshot in (four_hour, one_hour, fifteen_minute)
    )
    return MultiTimeframeTechnicalSnapshot(
        symbol=symbol,
        as_of_ms=as_of_ms,
        four_hour=four_hour,
        one_hour=one_hour,
        fifteen_minute=fifteen_minute,
        ready=ready,
    )


def build_multi_timeframe_technical_snapshot(
    *,
    symbol: str,
    as_of_ms: int,
    candles_by_interval: Mapping[str, Sequence[Candle]],
    rolling_window: int = 20,
    swing_left: int = 2,
    swing_right: int = 2,
) -> MultiTimeframeTechnicalSnapshot:
    """Compatibility alias with the full object name used in V0.2 handoff."""
    return build_multi_timeframe_snapshot(
        symbol=symbol,
        as_of_ms=as_of_ms,
        candles_by_interval=candles_by_interval,
        rolling_window=rolling_window,
        swing_left=swing_left,
        swing_right=swing_right,
    )
