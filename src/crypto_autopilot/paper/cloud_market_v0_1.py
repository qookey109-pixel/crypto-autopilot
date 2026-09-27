"""Bounded public-market adapter for the cloud paper loop.

No strategy parameters are changed. Missing macro context stays unavailable;
a Pionex price series is never relabeled as TOTAL3 or BTC dominance.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Protocol

from crypto_autopilot.features.regime import MarketRegimeSnapshot
from crypto_autopilot.features.structure import (
    build_market_structure_series,
    latest_market_structure_as_of,
)
from crypto_autopilot.models import BookTicker, Candle, MarketTicker
from crypto_autopilot.opportunity_engine import rank_daily_opportunities
from crypto_autopilot.strategy_router import route_strategy_families
from crypto_autopilot.technical import (
    TechnicalSnapshot,
    build_technical_series,
    latest_closed_snapshot,
)
from crypto_autopilot.universe import rank_perpetual_universe

HOUR_MS = 3_600_000
EARLIEST_CANDLE_MS = 1_788_480_000_000  # 2026-09-04T00:00:00Z


class MarketInputRejected(ValueError):
    """Safe, fixed reason code for a rejected market input."""


class PublicMarketClient(Protocol):
    def list_perpetual_symbols(self) -> list[str]: ...
    def list_perpetual_tickers(self) -> list[MarketTicker]: ...
    def list_perpetual_book_tickers(self) -> list[BookTicker]: ...
    def get_klines(
        self, symbol: str, interval: str, *, limit: int,
        end_time_ms: int | None = None,
    ) -> list[Candle]: ...


@dataclass(frozen=True, slots=True)
class MarketCapture:
    as_of_ms: int
    symbols: tuple[str, ...]
    tickers: tuple[MarketTicker, ...]
    books: tuple[BookTicker, ...]
    candles: Mapping[str, tuple[Candle, ...]]
    rejected: Mapping[str, str]
    requests_attempted: int


def validate_window(as_of_ms: int, count: int = 240) -> int:
    if type(as_of_ms) is not int or type(count) is not int or not 200 <= count <= 240:
        raise MarketInputRejected("INVALID_CAPTURE_WINDOW")
    end = as_of_ms // HOUR_MS * HOUR_MS - 1
    if end - count * HOUR_MS + 1 < EARLIEST_CANDLE_MS:
        raise MarketInputRejected("HOLDOUT_OR_PRE_AUTHORITY_WINDOW")
    return end


def validated_candles(
    candles: Sequence[Candle], *, as_of_ms: int, count: int = 240,
) -> tuple[Candle, ...]:
    end = validate_window(as_of_ms, count)
    lower = end - count * HOUR_MS + 1
    source = tuple(candles)
    if not 200 <= len(source) <= count:
        raise MarketInputRejected("INSUFFICIENT_OR_EXCESS_BARS")
    if any(c.time_ms < lower or c.time_ms > end for c in source):
        raise MarketInputRejected("OUTSIDE_REQUESTED_WINDOW")
    if any(c.time_ms % HOUR_MS or c.time_ms + HOUR_MS > as_of_ms for c in source):
        raise MarketInputRejected("UNALIGNED_OR_UNCLOSED_BAR")
    if any(b.time_ms - a.time_ms != HOUR_MS for a, b in zip(source, source[1:])):
        raise MarketInputRejected("NONCONTIGUOUS_OR_DUPLICATE_BARS")
    if source[-1].time_ms + HOUR_MS != end + 1:
        raise MarketInputRejected("STALE_CLOSED_BARS")
    for candle in source:
        values = (candle.open, candle.high, candle.low, candle.close, candle.volume)
        if not all(math.isfinite(x) for x in values):
            raise MarketInputRejected("NONFINITE_CANDLE")
        if min(values[:4]) <= 0 or candle.volume < 0:
            raise MarketInputRejected("INVALID_CANDLE")
        if candle.low > min(candle.open, candle.close) or candle.high < max(
            candle.open, candle.close
        ):
            raise MarketInputRejected("INVALID_OHLC")
    return source


def capture_market(
    client: PublicMarketClient, *, as_of_ms: int,
    allowed_base_assets: frozenset[str], before_request: Callable[[], None],
) -> MarketCapture:
    end = validate_window(as_of_ms)
    if not allowed_base_assets:
        raise MarketInputRejected("EMPTY_GOVERNED_CRYPTO_ALLOWLIST")
    attempted = 0

    def permit() -> None:
        nonlocal attempted
        before_request()
        attempted += 1

    permit()
    symbols = client.list_perpetual_symbols()
    permit()
    tickers = client.list_perpetual_tickers()
    permit()
    books = client.list_perpetual_book_tickers()
    if len({t.symbol for t in tickers}) != len(tickers):
        raise MarketInputRejected("DUPLICATE_TICKERS")
    if len({b.symbol for b in books}) != len(books):
        raise MarketInputRejected("DUPLICATE_BOOKS")
    valid_tickers = [
        t for t in tickers
        if all(math.isfinite(v) for v in (t.close, t.quote_amount, t.base_volume))
        and t.close > 0 and t.quote_amount > 0 and t.trade_count >= 0
    ]
    valid_books = [
        b for b in books
        if all(math.isfinite(v) for v in (b.bid_price, b.ask_price))
        and 0 <= as_of_ms - b.timestamp_ms <= 60_000
    ]
    universe = rank_perpetual_universe(
        symbols, valid_tickers, valid_books, target_size=5,
        allowed_base_assets=allowed_base_assets,
    )
    candles: dict[str, tuple[Candle, ...]] = {}
    rejected: dict[str, str] = {}
    for item in universe:
        permit()
        try:
            rows = client.get_klines(item.symbol, "60M", limit=240, end_time_ms=end)
            candles[item.symbol] = validated_candles(rows, as_of_ms=as_of_ms)
        except MarketInputRejected as exc:
            rejected[item.symbol] = str(exc)
    return MarketCapture(
        as_of_ms=as_of_ms,
        symbols=tuple(item.symbol for item in universe),
        tickers=tuple(valid_tickers), books=tuple(valid_books),
        candles=candles, rejected=rejected, requests_attempted=attempted,
    )


def analyze_capture(
    capture: MarketCapture, *, allowed_base_assets: frozenset[str],
    regime: MarketRegimeSnapshot | None = None,
) -> dict[str, object]:
    universe = rank_perpetual_universe(
        capture.symbols, capture.tickers, capture.books, target_size=5,
        allowed_base_assets=allowed_base_assets,
    )
    technical: dict[str, TechnicalSnapshot] = {}
    structures = {}
    evidence: dict[str, object] = {}
    for symbol, candles in capture.candles.items():
        source = validated_candles(candles, as_of_ms=capture.as_of_ms)
        series = build_technical_series(source, "60M")
        snapshot = latest_closed_snapshot(series, capture.as_of_ms, require_ready=True)
        if snapshot is None or not snapshot.ready_v0_2:
            continue
        technical[symbol] = snapshot
        structures[symbol] = latest_market_structure_as_of(
            build_market_structure_series(source, "60M", technical_series=series),
            capture.as_of_ms,
        )
        encoded = json.dumps([asdict(c) for c in source], sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode()
        evidence[symbol] = {
            "provider": "PIONEX_PUBLIC", "interval": "60M",
            "first_bar_ms": source[0].time_ms, "last_bar_ms": source[-1].time_ms,
            "bar_count": len(source), "sha256": hashlib.sha256(encoded).hexdigest(),
            "technical": asdict(snapshot),
        }
    if regime is not None and (
        not regime.ready or not 0 <= capture.as_of_ms - regime.available_at_ms <= HOUR_MS
    ):
        regime = None
    opportunities = rank_daily_opportunities(
        universe, technical, regime, as_of_ms=capture.as_of_ms,
    )
    routes = [
        asdict(route_strategy_families(
            decision, technical.get(decision.symbol), regime,
            structures.get(decision.symbol), as_of_ms=capture.as_of_ms,
        ))
        for decision in opportunities.selected
    ]
    return {
        "schema": "qookey-cloud-paper-market-report-v0.1",
        "provider": "PIONEX_PUBLIC", "as_of_ms": capture.as_of_ms,
        "market_status": "REVIEW_REQUIRED" if capture.rejected else "CAPTURED",
        "opportunity_status": opportunities.status,
        "opportunities": asdict(opportunities), "routes": routes,
        "market_evidence": evidence, "rejected": dict(capture.rejected),
        "requests_attempted": capture.requests_attempted,
        "context_status": "AVAILABLE" if regime is not None else "REGIME_UNAVAILABLE",
        "candidate_specs": [],
        "execution_selection_performed": False,
    }
