"""Deterministic Pionex research-universe selection for Simulation Readiness.

This module is deliberately pure: it consumes already-fetched public market
snapshots and produces a deterministic 150+ research-market selection. It does
not perform provider, R2, holdout, account, or trading I/O.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any, Iterable, Mapping, Sequence

from ..models import BookTicker, MarketTicker
from ..providers.pionex_alternative_assets import (
    base_asset_from_pionex_symbol,
    validate_config as validate_alternative_asset_config,
)


class UniverseRejected(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class UniverseMarket:
    selection_rank: int
    symbol: str
    base_asset: str
    asset_class: str
    tags: tuple[str, ...]
    history_profile: str
    close: float
    quote_amount: float
    trade_count: int
    bid_price: float
    ask_price: float
    spread_bps: float

    def payload(self) -> dict[str, object]:
        return asdict(self)


def _registry_map(config: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(base): str(asset_class)
        for asset_class, values in config["registry"].items()
        for base in values
    }


def validate_config(
    config: Mapping[str, Any],
    *,
    alternative_registry_bytes: bytes,
) -> dict[str, str]:
    if config.get("version") != "0.1.0":
        raise UniverseRejected("unexpected universe config version")
    if config.get("status") != "PREPARED_NOT_EXECUTION_AUTHORITY":
        raise UniverseRejected("universe config must remain prepared-only")
    if config.get("provider") != "pionex_public_futures":
        raise UniverseRejected("provider must remain pionex_public_futures")

    inputs = config.get("inputs")
    if not isinstance(inputs, Mapping):
        raise UniverseRejected("inputs missing")
    if inputs.get("alternative_assets_registry") != "config/pionex_alternative_assets_v0_1.json":
        raise UniverseRejected("alternative-assets registry path changed")
    digest = hashlib.sha256(alternative_registry_bytes).hexdigest()
    if inputs.get("alternative_assets_registry_sha256") != digest:
        raise UniverseRejected("alternative-assets registry SHA-256 mismatch")
    try:
        alternative_config = json.loads(alternative_registry_bytes)
    except (TypeError, ValueError) as exc:
        raise UniverseRejected("alternative-assets registry is not valid JSON") from exc
    validate_alternative_asset_config(alternative_config)
    alternative_map = _registry_map(alternative_config)

    meme_values = inputs.get("meme_candidate_roots")
    if not isinstance(meme_values, list) or not meme_values:
        raise UniverseRejected("meme candidate registry must be non-empty")
    meme_roots: set[str] = set()
    for value in meme_values:
        root = str(value)
        if root != root.upper() or not root.isascii() or not root.isalnum():
            raise UniverseRejected(f"unsafe meme candidate root: {value!r}")
        if root in meme_roots:
            raise UniverseRejected(f"duplicate meme candidate root: {root}")
        meme_roots.add(root)
    if meme_roots & set(alternative_map):
        raise UniverseRejected("meme and alternative-asset registries overlap")
    if inputs.get("meme_registry_is_watchlist_metadata_not_investment_endorsement") is not True:
        raise UniverseRejected("meme registry must remain non-endorsement metadata")

    selection = config.get("selection")
    if not isinstance(selection, Mapping):
        raise UniverseRejected("selection contract missing")
    if int(selection.get("minimum_total_markets") or 0) < 150:
        raise UniverseRejected("research universe minimum cannot fall below 150")
    if int(selection.get("crypto_core_target") or 0) != 100:
        raise UniverseRejected("crypto core target must remain 100")
    for key in (
        "include_all_live_meme_candidates",
        "include_all_live_alternative_asset_registry_matches",
        "fill_to_minimum_from_remaining_crypto",
        "literal_market_cap_top_100_requires_separate_rank_source",
    ):
        if selection.get(key) is not True:
            raise UniverseRejected(f"selection.{key} must remain true")
    for key in ("literal_market_cap_top_100_claimed", "forced_exact_total_market_count"):
        if selection.get(key) is not False:
            raise UniverseRejected(f"selection.{key} must remain false")
    if selection.get("ranking") != "QUOTE_AMOUNT_DESC_SPREAD_BPS_ASC_TRADE_COUNT_DESC_SYMBOL_ASC":
        raise UniverseRejected("ranking changed")
    if selection.get("crypto_core_semantics") != "PIONEX_LIQUIDITY_RANKED_NOT_MARKET_CAP_TOP_100":
        raise UniverseRejected("crypto-core semantics changed")

    quality = config.get("market_quality")
    if not isinstance(quality, Mapping):
        raise UniverseRejected("market-quality contract missing")
    if quality.get("hard_spread_rejection_bps") is not None:
        raise UniverseRejected("prepared research universe must not invent a spread cutoff")
    required_quality_true = (
        "require_live_symbol",
        "require_ticker",
        "require_book_ticker",
        "require_finite_positive_close",
        "require_finite_nonnegative_quote_amount",
        "require_nonnegative_trade_count",
        "require_finite_positive_bid_ask",
        "require_ask_not_below_bid",
        "invalid_markets_are_reported_not_silently_repaired",
    )
    if any(quality.get(key) is not True for key in required_quality_true):
        raise UniverseRejected("market-quality policy widened or weakened")

    profiles = config.get("history_profiles")
    if not isinstance(profiles, Mapping):
        raise UniverseRejected("history profiles missing")
    if profiles.get("FULL_INTRADAY") != {
        "maximum_markets": 30,
        "intervals": ["15M", "60M", "4H", "1D", "1W"],
    }:
        raise UniverseRejected("FULL_INTRADAY profile changed")
    if profiles.get("MULTISCALE_RESEARCH") != {
        "applies_to": ["crypto_core", "meme_candidate"],
        "intervals": ["60M", "4H", "1D", "1W"],
    }:
        raise UniverseRejected("MULTISCALE_RESEARCH profile changed")
    if profiles.get("BREADTH_BACKGROUND") != {
        "default_for_selected_market": True,
        "intervals": ["1D", "1W"],
    }:
        raise UniverseRejected("BREADTH_BACKGROUND profile changed")

    derived = config.get("derived_timeframes")
    if derived != {
        "1Y": {
            "provider_native": False,
            "source_interval": "1D",
            "derivation_authorized_by_this_stage": False,
        }
    }:
        raise UniverseRejected("derived timeframe policy changed")

    authority = config.get("authority")
    expected_authority = {
        "synthetic_fixture_validation": True,
        "public_pionex_requests": False,
        "private_api": False,
        "r2_read": False,
        "r2_write": False,
        "historical_materialization": False,
        "holdout_access": False,
        "training": False,
        "formal_backtest_admission": False,
        "strategy_change": False,
        "source_switch": False,
        "trade_plan": False,
        "real_money_orders": False,
        "live_trading": False,
    }
    if authority != expected_authority:
        raise UniverseRejected("prepared authority widened or changed")

    return alternative_map


def _ticker_map(values: Sequence[MarketTicker]) -> dict[str, MarketTicker]:
    output: dict[str, MarketTicker] = {}
    for item in values:
        symbol = str(item.symbol).upper()
        if symbol in output:
            raise UniverseRejected(f"duplicate ticker symbol: {symbol}")
        output[symbol] = item
    return output


def _book_map(values: Sequence[BookTicker]) -> dict[str, BookTicker]:
    output: dict[str, BookTicker] = {}
    for item in values:
        symbol = str(item.symbol).upper()
        if symbol in output:
            raise UniverseRejected(f"duplicate book ticker symbol: {symbol}")
        output[symbol] = item
    return output


def _market_metrics(
    symbol: str,
    *,
    ticker: MarketTicker | None,
    book: BookTicker | None,
) -> tuple[dict[str, float | int], str | None]:
    if ticker is None:
        return {}, "MISSING_TICKER"
    if book is None:
        return {}, "MISSING_BOOK_TICKER"
    if str(ticker.symbol).upper() != symbol or str(book.symbol).upper() != symbol:
        return {}, "SYMBOL_MISMATCH"

    if not math.isfinite(ticker.close) or ticker.close <= 0:
        return {}, "INVALID_CLOSE"
    if not math.isfinite(ticker.quote_amount) or ticker.quote_amount < 0:
        return {}, "INVALID_QUOTE_AMOUNT"
    if ticker.trade_count < 0:
        return {}, "INVALID_TRADE_COUNT"

    book_values = (book.bid_price, book.ask_price)
    if not all(math.isfinite(value) and value > 0 for value in book_values):
        return {}, "INVALID_BID_ASK"
    if book.ask_price < book.bid_price:
        return {}, "CROSSED_BOOK"

    midpoint = (book.bid_price + book.ask_price) / 2.0
    spread_bps = (book.ask_price - book.bid_price) / midpoint * 10_000.0
    if not math.isfinite(spread_bps) or spread_bps < 0:
        return {}, "INVALID_SPREAD"

    return {
        "close": float(ticker.close),
        "quote_amount": float(ticker.quote_amount),
        "trade_count": int(ticker.trade_count),
        "bid_price": float(book.bid_price),
        "ask_price": float(book.ask_price),
        "spread_bps": float(spread_bps),
    }, None


def build_universe(
    config: Mapping[str, Any],
    *,
    alternative_registry_bytes: bytes,
    live_symbols: Iterable[str],
    tickers: Sequence[MarketTicker],
    book_tickers: Sequence[BookTicker],
) -> dict[str, object]:
    alternative_map = validate_config(
        config,
        alternative_registry_bytes=alternative_registry_bytes,
    )
    meme_roots = {str(value) for value in config["inputs"]["meme_candidate_roots"]}
    ticker_map = _ticker_map(tickers)
    book_map = _book_map(book_tickers)

    live = tuple(sorted({str(value).upper() for value in live_symbols}))
    if not live:
        raise UniverseRejected("live Pionex perpetual catalog is empty")

    eligible: list[dict[str, object]] = []
    excluded: list[dict[str, str]] = []
    for symbol in live:
        base = base_asset_from_pionex_symbol(symbol)
        if base is None:
            excluded.append({"symbol": symbol, "reason": "NOT_USDT_PERP"})
            continue
        metrics, reason = _market_metrics(
            symbol,
            ticker=ticker_map.get(symbol),
            book=book_map.get(symbol),
        )
        if reason is not None:
            excluded.append({"symbol": symbol, "reason": reason})
            continue

        alternative_class = alternative_map.get(base)
        asset_class = alternative_class or "crypto"
        tags: list[str] = []
        if alternative_class is not None:
            tags.append("alternative_asset")
        if base in meme_roots:
            tags.append("meme_candidate")
        eligible.append(
            {
                "symbol": symbol,
                "base_asset": base,
                "asset_class": asset_class,
                "tags": tags,
                **metrics,
            }
        )

    def rank_key(item: Mapping[str, object]) -> tuple[float, float, int, str]:
        return (
            -float(item["quote_amount"]),
            float(item["spread_bps"]),
            -int(item["trade_count"]),
            str(item["symbol"]),
        )

    ranked = sorted(eligible, key=rank_key)
    crypto = [item for item in ranked if item["asset_class"] == "crypto"]
    core_target = int(config["selection"]["crypto_core_target"])
    if len(crypto) < core_target:
        raise UniverseRejected(
            f"fewer than {core_target} eligible Pionex crypto markets"
        )
    core_symbols = {str(item["symbol"]) for item in crypto[:core_target]}

    meme_symbols = {
        str(item["symbol"])
        for item in ranked
        if "meme_candidate" in item["tags"]
    }
    alternative_symbols = {
        str(item["symbol"])
        for item in ranked
        if "alternative_asset" in item["tags"]
    }
    selected_symbols = set(core_symbols) | meme_symbols | alternative_symbols

    minimum_total = int(config["selection"]["minimum_total_markets"])
    if len(selected_symbols) < minimum_total:
        for item in crypto[core_target:]:
            selected_symbols.add(str(item["symbol"]))
            if len(selected_symbols) >= minimum_total:
                break
    if len(selected_symbols) < minimum_total:
        raise UniverseRejected(
            f"only {len(selected_symbols)} eligible research markets; "
            f"minimum is {minimum_total}"
        )

    ranked_selected = [item for item in ranked if str(item["symbol"]) in selected_symbols]
    full_limit = int(config["history_profiles"]["FULL_INTRADAY"]["maximum_markets"])
    markets: list[UniverseMarket] = []
    for index, item in enumerate(ranked_selected, start=1):
        symbol = str(item["symbol"])
        tags = list(item["tags"])
        if symbol in core_symbols:
            tags.append("crypto_core")
        if index <= full_limit:
            profile = "FULL_INTRADAY"
        elif "crypto_core" in tags or "meme_candidate" in tags:
            profile = "MULTISCALE_RESEARCH"
        else:
            profile = "BREADTH_BACKGROUND"
        markets.append(
            UniverseMarket(
                selection_rank=index,
                symbol=symbol,
                base_asset=str(item["base_asset"]),
                asset_class=str(item["asset_class"]),
                tags=tuple(sorted(tags)),
                history_profile=profile,
                close=float(item["close"]),
                quote_amount=float(item["quote_amount"]),
                trade_count=int(item["trade_count"]),
                bid_price=float(item["bid_price"]),
                ask_price=float(item["ask_price"]),
                spread_bps=float(item["spread_bps"]),
            )
        )

    alternative_counts: dict[str, int] = {}
    profile_counts: dict[str, int] = {}
    for market in markets:
        if "alternative_asset" in market.tags:
            alternative_counts[market.asset_class] = (
                alternative_counts.get(market.asset_class, 0) + 1
            )
        profile_counts[market.history_profile] = (
            profile_counts.get(market.history_profile, 0) + 1
        )

    return {
        "status": "PASS",
        "provider": config["provider"],
        "selection_mode": "PIONEX_150_PLUS_LIQUIDITY_AND_REGISTRY",
        "market_cap_top_100_claimed": False,
        "live_perpetual_market_count": len(live),
        "eligible_market_count": len(eligible),
        "selected_market_count": len(markets),
        "crypto_core_count": len(core_symbols),
        "meme_candidate_selected_count": sum(
            "meme_candidate" in market.tags for market in markets
        ),
        "alternative_asset_selected_count": sum(
            "alternative_asset" in market.tags for market in markets
        ),
        "alternative_asset_class_counts": dict(sorted(alternative_counts.items())),
        "history_profile_counts": dict(sorted(profile_counts.items())),
        "excluded_markets": excluded,
        "markets": [market.payload() for market in markets],
        "derived_1y_authorized": False,
        "provider_requests_performed_by_builder": 0,
        "r2_accessed": False,
        "holdout_accessed": False,
        "training_authorized": False,
        "formal_backtest_admission_authorized": False,
        "real_money_orders_authorized": False,
        "live_trading_authorized": False,
    }
