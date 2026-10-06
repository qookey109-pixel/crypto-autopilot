from __future__ import annotations

import json
import unittest
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from crypto_autopilot.models import BookTicker, Candle, MarketTicker
from crypto_autopilot.research.prospective_shadow_collector_v0_1 import (
    build_collection_record,
)

ROOT = Path(__file__).resolve().parents[1]
HOUR_MS = 3_600_000
NOW = 1_800_000_000_000


class FakeClient:
    def __init__(self) -> None:
        bases = ["BTC", "ETH"] + [f"X{index:03d}" for index in range(158)]
        self.symbols = [f"{base}_USDT_PERP" for base in bases]
        self.tickers = [
            MarketTicker(
                symbol=symbol,
                close=1000.0 - index,
                base_volume=10_000.0,
                quote_amount=10_000_000_000.0 - index * 1_000_000.0,
                trade_count=100_000 - index,
            )
            for index, symbol in enumerate(self.symbols)
        ]
        self.books = [
            BookTicker(
                symbol=symbol,
                bid_price=99.9,
                bid_size=100.0,
                ask_price=100.1,
                ask_size=100.0,
                timestamp_ms=NOW - 1_000,
            )
            for symbol in self.symbols
        ]
        self.kline_symbols: list[str] = []

    def list_perpetual_symbols(self) -> list[str]:
        return list(self.symbols)

    def list_perpetual_tickers(self) -> list[MarketTicker]:
        return list(self.tickers)

    def list_perpetual_book_tickers(self) -> list[BookTicker]:
        return list(self.books)

    def get_klines(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
        end_time_ms: int | None = None,
    ) -> list[Candle]:
        self.kline_symbols.append(symbol)
        self.assertions(interval, limit, end_time_ms)
        first = NOW - 240 * HOUR_MS
        return [
            Candle(
                time_ms=first + index * HOUR_MS,
                open=100.0 + index * 0.1,
                high=101.0 + index * 0.1,
                low=99.0 + index * 0.1,
                close=100.5 + index * 0.1,
                volume=1_000.0 + index,
            )
            for index in range(240)
        ]

    @staticmethod
    def assertions(interval: str, limit: int, end_time_ms: int | None) -> None:
        if interval != "60M":
            raise AssertionError(interval)
        if limit != 240:
            raise AssertionError(limit)
        if end_time_ms != NOW - 1:
            raise AssertionError(end_time_ms)


def load(path: str) -> dict[str, object]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def fetch_context(url: str) -> bytes:
    if url.endswith("/global"):
        return json.dumps(
            {
                "market_cap_usd": 3_000_000_000_000,
                "bitcoin_dominance_percentage": 50.0,
                "last_updated": NOW // 1000,
            }
        ).encode()
    if url.endswith("/tickers/eth-ethereum"):
        stamp = datetime.fromtimestamp(NOW / 1000, UTC).isoformat().replace("+00:00", "Z")
        return json.dumps(
            {
                "id": "eth-ethereum",
                "symbol": "ETH",
                "last_updated": stamp,
                "quotes": {"USD": {"market_cap": 400_000_000_000}},
            }
        ).encode()
    raise AssertionError(url)


class ProspectiveShadowCollectorV01Tests(unittest.TestCase):
    def test_collects_normalized_top5_evidence_without_trading_authority(self) -> None:
        client = FakeClient()
        record = build_collection_record(
            execution_config=load(
                "config/prospective_shadow_collection_execution_v0_1.json"
            ),
            universe_config=load("config/pionex_research_universe_v0_1.json"),
            alternative_registry_bytes=(
                ROOT / "config/pionex_alternative_assets_v0_1.json"
            ).read_bytes(),
            context_config=load("config/context_forward_capture_v0_1.json"),
            source_lineage_bytes=(
                ROOT / "config/context_source_lineage_v0_1.json"
            ).read_bytes(),
            client=client,
            fetch_public_bytes=fetch_context,
            capture_timestamp_ms=NOW,
        )

        self.assertEqual(
            record["schema"],
            "qookey-prospective-shadow-collection-run-v0.1",
        )
        self.assertEqual(len(client.kline_symbols), 5)
        self.assertEqual(len(record["market_evidence"]), 5)
        self.assertEqual(
            len(record["market_evidence"][0]["candles_60m"]),
            240,
        )
        self.assertEqual(
            record["context_snapshot"]["provider"],
            "coinpaprika",
        )
        observation = record["regime_observation_input"]
        self.assertEqual(
            observation["breadth_scope"],
            "TOP5_GOVERNED_SCAN_RESEARCH_PROXY",
        )
        self.assertFalse(observation["production_regime_equivalence_claimed"])
        self.assertFalse(
            record["replay_state"]["signal_selection_performed_in_collector"]
        )
        self.assertFalse(record["authority"]["paper_submission_performed"])
        self.assertFalse(record["authority"]["live_trading_performed"])
        self.assertEqual(len(record["record_id"]), 64)

    def test_authority_widening_fails_closed(self) -> None:
        config = load("config/prospective_shadow_collection_execution_v0_1.json")
        widened = deepcopy(config)
        widened["authority"]["r2_read_authorized"] = True
        with self.assertRaises(ValueError):
            build_collection_record(
                execution_config=widened,
                universe_config=load("config/pionex_research_universe_v0_1.json"),
                alternative_registry_bytes=(
                    ROOT / "config/pionex_alternative_assets_v0_1.json"
                ).read_bytes(),
                context_config=load("config/context_forward_capture_v0_1.json"),
                source_lineage_bytes=(
                    ROOT / "config/context_source_lineage_v0_1.json"
                ).read_bytes(),
                client=FakeClient(),
                fetch_public_bytes=fetch_context,
                capture_timestamp_ms=NOW,
            )


if __name__ == "__main__":
    unittest.main()
