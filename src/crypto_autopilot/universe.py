from __future__ import annotations

from dataclasses import dataclass

from .models import BookTicker, MarketTicker


@dataclass(frozen=True, slots=True)
class UniverseCandidate:
    symbol: str
    quote_amount_24h: float
    spread_bps: float
    close: float
    trade_count_24h: int


def spread_bps(book: BookTicker) -> float | None:
    if book.bid_price <= 0 or book.ask_price <= 0 or book.ask_price < book.bid_price:
        return None
    mid = (book.bid_price + book.ask_price) / 2.0
    if mid <= 0:
        return None
    return (book.ask_price - book.bid_price) / mid * 10_000.0


def base_asset_from_symbol(symbol: str, quote_suffix: str = "_USDT_PERP") -> str | None:
    if not quote_suffix or not symbol.endswith(quote_suffix):
        return None
    base = symbol[: -len(quote_suffix)]
    return base or None


def rank_perpetual_universe(
    active_symbols: list[str] | tuple[str, ...],
    tickers: list[MarketTicker] | tuple[MarketTicker, ...],
    books: list[BookTicker] | tuple[BookTicker, ...],
    *,
    target_size: int = 15,
    quote_suffix: str = "_USDT_PERP",
    max_spread_bps: float = 30.0,
    allowed_base_assets: set[str] | frozenset[str] | None = None,
) -> tuple[UniverseCandidate, ...]:
    if not 1 <= target_size <= 20:
        raise ValueError("target_size must be between 1 and 20")
    if max_spread_bps <= 0:
        raise ValueError("max_spread_bps must be positive")

    allowed = None
    if allowed_base_assets is not None:
        allowed = {str(item).upper() for item in allowed_base_assets if str(item).strip()}
        if not allowed:
            raise ValueError("allowed_base_assets must not be empty when supplied")

    ticker_by_symbol = {ticker.symbol: ticker for ticker in tickers}
    book_by_symbol = {book.symbol: book for book in books}
    candidates: list[UniverseCandidate] = []

    for symbol in sorted(set(active_symbols)):
        base_asset = base_asset_from_symbol(symbol, quote_suffix)
        if base_asset is None:
            continue
        if allowed is not None and base_asset.upper() not in allowed:
            continue
        ticker = ticker_by_symbol.get(symbol)
        book = book_by_symbol.get(symbol)
        if ticker is None or book is None or ticker.quote_amount <= 0 or ticker.close <= 0:
            continue
        current_spread = spread_bps(book)
        if current_spread is None or current_spread > max_spread_bps:
            continue
        candidates.append(
            UniverseCandidate(
                symbol=symbol,
                quote_amount_24h=ticker.quote_amount,
                spread_bps=current_spread,
                close=ticker.close,
                trade_count_24h=ticker.trade_count,
            )
        )

    candidates.sort(key=lambda item: (-item.quote_amount_24h, item.spread_bps, item.symbol))
    return tuple(candidates[:target_size])
