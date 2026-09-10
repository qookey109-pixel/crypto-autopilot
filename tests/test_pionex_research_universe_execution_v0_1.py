from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import unittest

from crypto_autopilot.models import BookTicker, MarketTicker
from crypto_autopilot.research.pionex_universe_execution_v0_1 import (
    UniverseExecutionRejected,
    capture_public_snapshot,
    require_execution_window,
    validate_execution_config,
)


ROOT = Path(__file__).resolve().parents[1]
EXEC_CONFIG = ROOT / "config/pionex_research_universe_execution_v0_1.json"
SELECTION_CONFIG = ROOT / "config/pionex_research_universe_v0_1.json"
ALT_REGISTRY = ROOT / "config/pionex_alternative_assets_v0_1.json"
RECEIPT = (
    ROOT
    / "research"
    / "receipts"
    / "2026-09-11-pionex-research-universe-execution-v0-1-authority.json"
)


def market(symbol: str, rank: int) -> tuple[MarketTicker, BookTicker]:
    close = 100.0 + rank * 0.01
    ticker = MarketTicker(
        symbol=symbol,
        close=close,
        base_volume=10_000.0,
        quote_amount=1_000_000_000.0 - rank * 1_000_000.0,
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


class FakeSnapshotClient:
    def __init__(
        self,
        selection_config: dict[str, object],
        alt_config: dict[str, object],
    ) -> None:
        self.calls: list[str] = []
        self.symbols: list[str] = []
        self.tickers: list[MarketTicker] = []
        self.books: list[BookTicker] = []
        rank = 0
        for index in range(170):
            symbol = f"C{index:03d}_USDT_PERP"
            ticker, book = market(symbol, rank)
            self.symbols.append(symbol)
            self.tickers.append(ticker)
            self.books.append(book)
            rank += 1

        for root in list(selection_config["inputs"]["meme_candidate_roots"])[:5]:
            symbol = f"{root}_USDT_PERP"
            ticker, book = market(symbol, rank)
            ticker = MarketTicker(
                symbol=ticker.symbol,
                close=ticker.close,
                base_volume=ticker.base_volume,
                quote_amount=1_000.0 + rank,
                trade_count=100,
            )
            self.symbols.append(symbol)
            self.tickers.append(ticker)
            self.books.append(book)
            rank += 1

        for values in alt_config["registry"].values():
            root = values[0]
            symbol = f"{root}_USDT_PERP"
            ticker, book = market(symbol, rank)
            ticker = MarketTicker(
                symbol=ticker.symbol,
                close=ticker.close,
                base_volume=ticker.base_volume,
                quote_amount=500.0 + rank,
                trade_count=50,
            )
            self.symbols.append(symbol)
            self.tickers.append(ticker)
            self.books.append(book)
            rank += 1

    def list_perpetual_symbols(self) -> list[str]:
        self.calls.append("symbols")
        return list(self.symbols)

    def list_perpetual_tickers(self) -> list[MarketTicker]:
        self.calls.append("tickers")
        return list(self.tickers)

    def list_perpetual_book_tickers(self) -> list[BookTicker]:
        self.calls.append("bookTickers")
        return list(self.books)


class PionexResearchUniverseExecutionV01Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config_bytes = EXEC_CONFIG.read_bytes()
        self.config = json.loads(self.config_bytes)
        self.selection_bytes = SELECTION_CONFIG.read_bytes()
        self.selection = json.loads(self.selection_bytes)
        self.alt_bytes = ALT_REGISTRY.read_bytes()
        self.alt_config = json.loads(self.alt_bytes)

    def test_execution_config_is_public_only_and_bounded(self) -> None:
        validate_execution_config(
            self.config,
            selection_config_bytes=self.selection_bytes,
            alternative_registry_bytes=self.alt_bytes,
        )
        execution = self.config["execution"]
        self.assertEqual(execution["provider_request_count_exact"], 3)
        self.assertEqual(execution["automatic_retries"], 0)
        self.assertTrue(execution["github_actions_main_only"])
        self.assertTrue(execution["workflow_dispatch_only"])
        self.assertFalse(execution["workflow_wiring_included_by_this_stage"])
        authority = self.config["authority"]
        self.assertTrue(authority["public_pionex_snapshot_reads_after_merge"])
        self.assertFalse(authority["api_key_required"])
        self.assertFalse(authority["private_api"])
        self.assertFalse(authority["r2_read"])
        self.assertFalse(authority["r2_write"])
        self.assertFalse(authority["holdout_access"])
        self.assertFalse(authority["live_trading"])

    def test_capture_uses_exactly_three_public_snapshot_calls(self) -> None:
        client = FakeSnapshotClient(self.selection, self.alt_config)
        report = capture_public_snapshot(
            self.config,
            selection_config_bytes=self.selection_bytes,
            alternative_registry_bytes=self.alt_bytes,
            client=client,
            observed_at=datetime(2026, 9, 11, 1, 0, tzinfo=UTC),
        )
        self.assertEqual(client.calls, ["symbols", "tickers", "bookTickers"])
        self.assertEqual(report["provider_request_count"], 3)
        self.assertGreaterEqual(report["selected_market_count"], 150)
        self.assertEqual(report["crypto_core_count"], 100)
        self.assertFalse(report["api_key_used"])
        self.assertFalse(report["r2_accessed"])
        self.assertFalse(report["holdout_accessed"])
        self.assertFalse(report["live_trading_authorized"])

    def test_selection_config_mutation_fails_closed(self) -> None:
        changed = self.selection_bytes + b"\n"
        with self.assertRaisesRegex(UniverseExecutionRejected, "selection config SHA-256 mismatch"):
            validate_execution_config(
                self.config,
                selection_config_bytes=changed,
                alternative_registry_bytes=self.alt_bytes,
            )

    def test_alternative_registry_mutation_fails_closed(self) -> None:
        changed = self.alt_bytes + b"\n"
        with self.assertRaisesRegex(UniverseExecutionRejected, "alternative registry SHA-256 mismatch"):
            validate_execution_config(
                self.config,
                selection_config_bytes=self.selection_bytes,
                alternative_registry_bytes=changed,
            )

    def test_execution_window_fails_before_and_after_bounds(self) -> None:
        with self.assertRaisesRegex(UniverseExecutionRejected, "before not-before"):
            require_execution_window(
                self.config,
                observed_at=datetime(2026, 9, 10, 18, 59, 59, tzinfo=UTC),
            )
        with self.assertRaisesRegex(UniverseExecutionRejected, "expired"):
            require_execution_window(
                self.config,
                observed_at=datetime(2026, 9, 16, 0, 0, tzinfo=UTC),
            )

    def test_receipt_binds_execution_config_exactly(self) -> None:
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        digest = hashlib.sha256(self.config_bytes).hexdigest()
        self.assertEqual(receipt["config_sha256"], digest)
        self.assertFalse(receipt["execution_performed_by_this_receipt"])
        self.assertEqual(
            receipt["selection_config_sha256"],
            hashlib.sha256(self.selection_bytes).hexdigest(),
        )
        self.assertFalse(receipt["authority"]["r2_read"])
        self.assertFalse(receipt["authority"]["holdout_access"])
        self.assertFalse(receipt["authority"]["live_trading"])

    def test_runner_has_no_secret_or_r2_binding(self) -> None:
        runner = (ROOT / "scripts/run_pionex_research_universe_v0_1.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("secrets.", runner)
        self.assertNotIn("R2_", runner)
        self.assertNotIn("PIONEX-KEY", runner)
        self.assertIn('"GITHUB_EVENT_NAME": "workflow_dispatch"', runner)
        self.assertIn('"GITHUB_REF": "refs/heads/main"', runner)
        self.assertIn('"GITHUB_RUN_ATTEMPT": "1"', runner)


if __name__ == "__main__":
    unittest.main()
