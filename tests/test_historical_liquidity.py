from __future__ import annotations

import unittest

from crypto_autopilot.historical_liquidity import (
    HistoricalLiquidityBatch,
    HistoricalLiquidityConflictError,
    HistoricalLiquidityEvidenceError,
    HistoricalLiquidityIndex,
    HistoricalLiquidityMarket,
    HistoricalLiquidityPolicy,
)
from crypto_autopilot.historical_universe import HistoricalMarketRecord, HistoricalUniverseIndex


class HistoricalLiquidityTest(unittest.TestCase):
    def _universe(
        self,
        symbols: tuple[str, ...] = ("AAA_USDT_PERP", "BBB_USDT_PERP", "CCC_USDT_PERP"),
        *,
        start_ms: int = 0,
        end_ms: int = 10_000,
    ) -> HistoricalUniverseIndex:
        records: list[HistoricalMarketRecord] = []
        for symbol in symbols:
            for interval in ("15M", "60M", "4H"):
                records.append(
                    HistoricalMarketRecord(
                        provider="pionex",
                        market_type="perp",
                        symbol=symbol,
                        interval=interval,
                        available_from_ms=start_ms,
                        available_to_ms=end_ms,
                        evidence_type="verified_partition_receipt",
                        source_ref=f"fixture:universe:{symbol}:{interval}",
                        source_sha256="a" * 64,
                        native=True,
                    )
                )
        return HistoricalUniverseIndex(records)

    def _market(
        self,
        symbol: str,
        quote_amount: float,
        *,
        spread_bps: float = 5.0,
    ) -> HistoricalLiquidityMarket:
        return HistoricalLiquidityMarket(
            symbol=symbol,
            quote_amount_24h=quote_amount,
            spread_bps=spread_bps,
            close=10.0,
            trade_count_24h=100,
        )

    def _batch(
        self,
        markets: tuple[HistoricalLiquidityMarket, ...],
        *,
        snapshot_id: str = "snapshot-1",
        snapshot_time_ms: int = 900,
        available_at_ms: int = 950,
        native: bool = True,
        source_ref: str = "fixture:liquidity:snapshot-1",
    ) -> HistoricalLiquidityBatch:
        return HistoricalLiquidityBatch(
            provider="pionex",
            market_type="perp",
            snapshot_id=snapshot_id,
            snapshot_time_ms=snapshot_time_ms,
            available_at_ms=available_at_ms,
            markets=markets,
            source_ref=source_ref,
            source_sha256="b" * 64,
            native=native,
        )

    def test_rank_is_deterministic_and_uses_turnover_then_spread_then_symbol(self) -> None:
        universe = self._universe()
        batch = self._batch(
            (
                self._market("AAA_USDT_PERP", 100.0, spread_bps=1.0),
                self._market("BBB_USDT_PERP", 200.0, spread_bps=2.0),
                self._market("CCC_USDT_PERP", 200.0, spread_bps=1.0),
                self._market("EXTRA_USDT_PERP", 999.0, spread_bps=0.1),
            )
        )
        index = HistoricalLiquidityIndex((batch,))
        policy = HistoricalLiquidityPolicy(target_size=3, max_snapshot_age_ms=200)

        first = index.snapshot(1000, historical_universe=universe, provider="pionex", policy=policy)
        second = index.snapshot(1000, historical_universe=universe, provider="pionex", policy=policy)

        self.assertEqual(first, second)
        self.assertEqual(first.symbols, ("CCC_USDT_PERP", "BBB_USDT_PERP", "AAA_USDT_PERP"))
        self.assertNotIn("EXTRA_USDT_PERP", first.symbols)
        self.assertEqual(first.historical_universe_symbols, universe.available_symbols_at(1000, provider="pionex"))
        self.assertEqual(first.liquidity_authority_ref, batch.source_ref)

    def test_incomplete_liquidity_batch_fails_closed_instead_of_ranking_partial_coverage(self) -> None:
        universe = self._universe()
        batch = self._batch(
            (
                self._market("AAA_USDT_PERP", 100.0),
                self._market("BBB_USDT_PERP", 200.0),
            )
        )
        index = HistoricalLiquidityIndex((batch,))

        with self.assertRaisesRegex(HistoricalLiquidityEvidenceError, "complete evidence-bounded universe"):
            index.snapshot(
                1000,
                historical_universe=universe,
                provider="pionex",
                policy=HistoricalLiquidityPolicy(max_snapshot_age_ms=200),
            )

    def test_later_snapshot_cannot_be_backprojected_into_earlier_time(self) -> None:
        universe = self._universe()
        batch = self._batch(
            tuple(self._market(symbol, 100.0) for symbol in universe.available_symbols_at(1000, provider="pionex")),
            snapshot_time_ms=1100,
            available_at_ms=1150,
        )
        index = HistoricalLiquidityIndex((batch,))

        with self.assertRaisesRegex(HistoricalLiquidityEvidenceError, "no fresh historical liquidity batch"):
            index.snapshot(
                1000,
                historical_universe=universe,
                provider="pionex",
                policy=HistoricalLiquidityPolicy(max_snapshot_age_ms=500),
            )

    def test_snapshot_is_hidden_until_recorded_availability_time(self) -> None:
        universe = self._universe()
        symbols = universe.available_symbols_at(1000, provider="pionex")
        batch = self._batch(
            tuple(self._market(symbol, 100.0) for symbol in symbols),
            snapshot_time_ms=900,
            available_at_ms=1050,
        )
        index = HistoricalLiquidityIndex((batch,))

        with self.assertRaisesRegex(HistoricalLiquidityEvidenceError, "no fresh historical liquidity batch"):
            index.snapshot(
                1000,
                historical_universe=universe,
                provider="pionex",
                policy=HistoricalLiquidityPolicy(max_snapshot_age_ms=500),
            )

    def test_stale_snapshot_is_not_silently_carried_forward(self) -> None:
        universe = self._universe()
        symbols = universe.available_symbols_at(1000, provider="pionex")
        batch = self._batch(
            tuple(self._market(symbol, 100.0) for symbol in symbols),
            snapshot_time_ms=800,
            available_at_ms=800,
        )
        index = HistoricalLiquidityIndex((batch,))

        with self.assertRaisesRegex(HistoricalLiquidityEvidenceError, "no fresh historical liquidity batch"):
            index.snapshot(
                1000,
                historical_universe=universe,
                provider="pionex",
                policy=HistoricalLiquidityPolicy(max_snapshot_age_ms=100),
            )

    def test_proxy_snapshot_cannot_authorize_native_ranking(self) -> None:
        universe = self._universe()
        symbols = universe.available_symbols_at(1000, provider="pionex")
        batch = self._batch(
            tuple(self._market(symbol, 100.0) for symbol in symbols),
            native=False,
        )
        index = HistoricalLiquidityIndex((batch,))

        with self.assertRaisesRegex(HistoricalLiquidityEvidenceError, "no fresh historical liquidity batch"):
            index.snapshot(
                1000,
                historical_universe=universe,
                provider="pionex",
                policy=HistoricalLiquidityPolicy(max_snapshot_age_ms=200, native_only=True),
            )

    def test_spread_gate_filters_without_forcing_target_size(self) -> None:
        universe = self._universe()
        batch = self._batch(
            (
                self._market("AAA_USDT_PERP", 300.0, spread_bps=31.0),
                self._market("BBB_USDT_PERP", 200.0, spread_bps=5.0),
                self._market("CCC_USDT_PERP", 100.0, spread_bps=5.0),
            )
        )
        index = HistoricalLiquidityIndex((batch,))
        snapshot = index.snapshot(
            1000,
            historical_universe=universe,
            provider="pionex",
            policy=HistoricalLiquidityPolicy(target_size=3, max_spread_bps=30.0, max_snapshot_age_ms=200),
        )

        self.assertEqual(snapshot.symbols, ("BBB_USDT_PERP", "CCC_USDT_PERP"))

    def test_conflicting_authority_for_same_snapshot_id_is_rejected(self) -> None:
        markets = (self._market("AAA_USDT_PERP", 100.0),)
        first = self._batch(markets, source_ref="fixture:first")
        second = self._batch(markets, source_ref="fixture:second")

        with self.assertRaisesRegex(HistoricalLiquidityConflictError, "conflicting historical liquidity authority"):
            HistoricalLiquidityIndex((first, second))


if __name__ == "__main__":
    unittest.main()
