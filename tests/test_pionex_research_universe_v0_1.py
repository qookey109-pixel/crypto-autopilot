from __future__ import annotations

import json
from pathlib import Path
import unittest

from crypto_autopilot.models import BookTicker, MarketTicker
from crypto_autopilot.research.pionex_universe_v0_1 import (
    UniverseRejected,
    build_universe,
    validate_config,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/pionex_research_universe_v0_1.json"
ALT_REGISTRY = ROOT / "config/pionex_alternative_assets_v0_1.json"


def market(symbol: str, rank: int) -> tuple[MarketTicker, BookTicker]:
    close = 100.0 + rank * 0.01
    quote_amount = 1_000_000_000.0 - rank * 1_000_000.0
    ticker = MarketTicker(
        symbol=symbol,
        close=close,
        base_volume=10_000.0,
        quote_amount=quote_amount,
        trade_count=max(0, 100_000 - rank),
    )
    book = BookTicker(
        symbol=symbol,
        bid_price=close * 0.999,
        bid_size=100.0,
        ask_price=close * 1.001,
        ask_size=100.0,
        timestamp_ms=1_000_000 + rank,
    )
    return ticker, book


def fixtures(
    config: dict[str, object],
    alt_config: dict[str, object],
    *,
    generic_crypto_count: int = 170,
    include_special: bool = True,
) -> tuple[list[str], list[MarketTicker], list[BookTicker]]:
    symbols: list[str] = []
    tickers: list[MarketTicker] = []
    books: list[BookTicker] = []

    for index in range(generic_crypto_count):
        symbol = f"C{index:03d}_USDT_PERP"
        ticker, book = market(symbol, index)
        symbols.append(symbol)
        tickers.append(ticker)
        books.append(book)

    if include_special:
        rank = generic_crypto_count + 100
        for root in list(config["inputs"]["meme_candidate_roots"])[:5]:
            symbol = f"{root}_USDT_PERP"
            ticker, book = market(symbol, rank)
            ticker = MarketTicker(
                symbol=ticker.symbol,
                close=ticker.close,
                base_volume=ticker.base_volume,
                quote_amount=1_000.0 + rank,
                trade_count=100,
            )
            symbols.append(symbol)
            tickers.append(ticker)
            books.append(book)
            rank += 1

        alternative_roots = [values[0] for values in alt_config["registry"].values()]
        for root in alternative_roots:
            symbol = f"{root}_USDT_PERP"
            ticker, book = market(symbol, rank)
            ticker = MarketTicker(
                symbol=ticker.symbol,
                close=ticker.close,
                base_volume=ticker.base_volume,
                quote_amount=500.0 + rank,
                trade_count=50,
            )
            symbols.append(symbol)
            tickers.append(ticker)
            books.append(book)
            rank += 1

    return symbols, tickers, books


class PionexResearchUniverseV01Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.alt_bytes = ALT_REGISTRY.read_bytes()
        self.alt_config = json.loads(self.alt_bytes)

    def test_config_is_prepared_only_and_requires_150_plus(self) -> None:
        validate_config(self.config, alternative_registry_bytes=self.alt_bytes)
        self.assertEqual(self.config["selection"]["minimum_total_markets"], 150)
        self.assertEqual(self.config["selection"]["crypto_core_target"], 100)
        self.assertFalse(self.config["selection"]["literal_market_cap_top_100_claimed"])
        self.assertFalse(self.config["authority"]["public_pionex_requests"])
        self.assertFalse(self.config["authority"]["r2_read"])
        self.assertFalse(self.config["authority"]["r2_write"])
        self.assertFalse(self.config["authority"]["holdout_access"])
        self.assertFalse(self.config["authority"]["live_trading"])

    def test_builds_150_plus_and_preserves_meme_and_alternative_assets(self) -> None:
        symbols, tickers, books = fixtures(self.config, self.alt_config)
        report = build_universe(
            self.config,
            alternative_registry_bytes=self.alt_bytes,
            live_symbols=symbols,
            tickers=tickers,
            book_tickers=books,
        )
        self.assertEqual(report["status"], "PASS")
        self.assertGreaterEqual(report["selected_market_count"], 150)
        self.assertEqual(report["crypto_core_count"], 100)
        self.assertGreaterEqual(report["meme_candidate_selected_count"], 5)
        self.assertGreaterEqual(report["alternative_asset_selected_count"], 3)
        self.assertFalse(report["market_cap_top_100_claimed"])
        self.assertFalse(report["r2_accessed"])
        self.assertFalse(report["holdout_accessed"])
        self.assertFalse(report["live_trading_authorized"])

        selected = {item["symbol"]: item for item in report["markets"]}
        for root in list(self.config["inputs"]["meme_candidate_roots"])[:5]:
            self.assertIn(f"{root}_USDT_PERP", selected)
            self.assertIn("meme_candidate", selected[f"{root}_USDT_PERP"]["tags"])
        for values in self.alt_config["registry"].values():
            root = values[0]
            self.assertIn(f"{root}_USDT_PERP", selected)
            self.assertIn("alternative_asset", selected[f"{root}_USDT_PERP"]["tags"])

    def test_history_profiles_limit_expensive_intraday_scope(self) -> None:
        symbols, tickers, books = fixtures(self.config, self.alt_config)
        report = build_universe(
            self.config,
            alternative_registry_bytes=self.alt_bytes,
            live_symbols=symbols,
            tickers=tickers,
            book_tickers=books,
        )
        counts = report["history_profile_counts"]
        self.assertEqual(counts["FULL_INTRADAY"], 30)
        self.assertEqual(
            self.config["history_profiles"]["FULL_INTRADAY"]["intervals"],
            ["15M", "60M", "4H", "1D", "1W"],
        )
        self.assertEqual(
            self.config["history_profiles"]["BREADTH_BACKGROUND"]["intervals"],
            ["1D", "1W"],
        )
        self.assertFalse(
            self.config["derived_timeframes"]["1Y"]["derivation_authorized_by_this_stage"]
        )

    def test_missing_market_metric_is_reported_not_fabricated(self) -> None:
        symbols, tickers, books = fixtures(self.config, self.alt_config)
        missing_symbol = symbols[120]
        books = [book for book in books if book.symbol != missing_symbol]
        report = build_universe(
            self.config,
            alternative_registry_bytes=self.alt_bytes,
            live_symbols=symbols,
            tickers=tickers,
            book_tickers=books,
        )
        self.assertIn(
            {"symbol": missing_symbol, "reason": "MISSING_BOOK_TICKER"},
            report["excluded_markets"],
        )
        self.assertNotIn(
            missing_symbol,
            {item["symbol"] for item in report["markets"]},
        )

    def test_fails_if_crypto_core_cannot_reach_100(self) -> None:
        symbols, tickers, books = fixtures(
            self.config,
            self.alt_config,
            generic_crypto_count=99,
            include_special=False,
        )
        with self.assertRaisesRegex(UniverseRejected, "fewer than 100"):
            build_universe(
                self.config,
                alternative_registry_bytes=self.alt_bytes,
                live_symbols=symbols,
                tickers=tickers,
                book_tickers=books,
            )

    def test_fails_if_total_universe_cannot_reach_150(self) -> None:
        symbols, tickers, books = fixtures(
            self.config,
            self.alt_config,
            generic_crypto_count=120,
            include_special=False,
        )
        with self.assertRaisesRegex(UniverseRejected, "minimum is 150"):
            build_universe(
                self.config,
                alternative_registry_bytes=self.alt_bytes,
                live_symbols=symbols,
                tickers=tickers,
                book_tickers=books,
            )

    def test_registry_hash_mutation_fails_closed(self) -> None:
        changed = self.alt_bytes + b"\n"
        with self.assertRaisesRegex(UniverseRejected, "SHA-256 mismatch"):
            validate_config(self.config, alternative_registry_bytes=changed)

    def test_order_is_deterministic_under_reversed_inputs(self) -> None:
        symbols, tickers, books = fixtures(self.config, self.alt_config)
        left = build_universe(
            self.config,
            alternative_registry_bytes=self.alt_bytes,
            live_symbols=symbols,
            tickers=tickers,
            book_tickers=books,
        )
        right = build_universe(
            self.config,
            alternative_registry_bytes=self.alt_bytes,
            live_symbols=reversed(symbols),
            tickers=list(reversed(tickers)),
            book_tickers=list(reversed(books)),
        )
        self.assertEqual(left["markets"], right["markets"])
        self.assertEqual(left["excluded_markets"], right["excluded_markets"])

    def test_invalid_crossed_book_is_excluded(self) -> None:
        symbols, tickers, books = fixtures(self.config, self.alt_config)
        target = symbols[130]
        books = [
            BookTicker(
                symbol=book.symbol,
                bid_price=101.0,
                bid_size=book.bid_size,
                ask_price=100.0,
                ask_size=book.ask_size,
                timestamp_ms=book.timestamp_ms,
            )
            if book.symbol == target
            else book
            for book in books
        ]
        report = build_universe(
            self.config,
            alternative_registry_bytes=self.alt_bytes,
            live_symbols=symbols,
            tickers=tickers,
            book_tickers=books,
        )
        self.assertIn(
            {"symbol": target, "reason": "CROSSED_BOOK"},
            report["excluded_markets"],
        )


if __name__ == "__main__":
    unittest.main()
