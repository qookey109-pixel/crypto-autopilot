from __future__ import annotations

import unittest

from crypto_autopilot.backtest import LongTradePlan
from crypto_autopilot.historical_admission import admit_plans_by_historical_liquidity
from crypto_autopilot.historical_liquidity import (
    HistoricalLiquidityBatch,
    HistoricalLiquidityEvidenceError,
    HistoricalLiquidityIndex,
    HistoricalLiquidityMarket,
    HistoricalLiquidityPolicy,
)
from crypto_autopilot.historical_universe import HistoricalMarketRecord, HistoricalUniverseIndex


class HistoricalLiquidityAdmissionTest(unittest.TestCase):
    def _universe(self) -> HistoricalUniverseIndex:
        records: list[HistoricalMarketRecord] = []
        for symbol in ("AAA_USDT_PERP", "BBB_USDT_PERP", "CCC_USDT_PERP"):
            for interval in ("15M", "60M", "4H"):
                records.append(
                    HistoricalMarketRecord(
                        provider="pionex",
                        market_type="perp",
                        symbol=symbol,
                        interval=interval,
                        available_from_ms=0,
                        available_to_ms=10_000,
                        evidence_type="verified_partition_receipt",
                        source_ref=f"fixture:universe:{symbol}:{interval}",
                        source_sha256="a" * 64,
                        native=True,
                    )
                )
        return HistoricalUniverseIndex(records)

    def _market(self, symbol: str, quote_amount: float, *, spread_bps: float = 5.0) -> HistoricalLiquidityMarket:
        return HistoricalLiquidityMarket(
            symbol=symbol,
            quote_amount_24h=quote_amount,
            spread_bps=spread_bps,
            close=10.0,
            trade_count_24h=100,
        )

    def _batch(
        self,
        *,
        snapshot_id: str,
        snapshot_time_ms: int,
        markets: tuple[HistoricalLiquidityMarket, ...],
    ) -> HistoricalLiquidityBatch:
        return HistoricalLiquidityBatch(
            provider="pionex",
            market_type="perp",
            snapshot_id=snapshot_id,
            snapshot_time_ms=snapshot_time_ms,
            available_at_ms=snapshot_time_ms,
            markets=markets,
            source_ref=f"fixture:liquidity:{snapshot_id}",
            source_sha256="b" * 64,
            native=True,
        )

    def _plan(self, plan_id: str, symbol: str, signal_time_ms: int) -> LongTradePlan:
        return LongTradePlan(
            plan_id=plan_id,
            symbol=symbol,
            signal_time_ms=signal_time_ms,
            stop_price=9.0,
            target_price=11.0,
        )

    def test_only_point_in_time_ranked_symbols_are_admitted(self) -> None:
        universe = self._universe()
        batch = self._batch(
            snapshot_id="s1",
            snapshot_time_ms=900,
            markets=(
                self._market("AAA_USDT_PERP", 300.0),
                self._market("BBB_USDT_PERP", 200.0),
                self._market("CCC_USDT_PERP", 100.0),
            ),
        )
        result = admit_plans_by_historical_liquidity(
            (
                self._plan("aaa", "AAA_USDT_PERP", 1000),
                self._plan("ccc", "CCC_USDT_PERP", 1000),
            ),
            liquidity_index=HistoricalLiquidityIndex((batch,)),
            universe_index=universe,
            provider="pionex",
            policy=HistoricalLiquidityPolicy(target_size=2, max_snapshot_age_ms=200),
        )

        self.assertEqual(tuple(plan.plan_id for plan in result.admitted_plans), ("aaa",))
        self.assertEqual(
            result.rejected_plans,
            (("ccc", "symbol_not_in_historical_liquidity_ranked_universe_at_signal_time"),),
        )
        admitted = result.decisions[0]
        self.assertTrue(admitted.admitted)
        self.assertEqual(admitted.liquidity_rank, 1)
        self.assertEqual(admitted.liquidity_batch_id, "s1")
        self.assertEqual(len(admitted.universe_authority_refs), 3)
        self.assertEqual(admitted.liquidity_authority_ref, "fixture:liquidity:s1")

    def test_each_plan_uses_its_own_signal_time_not_latest_snapshot(self) -> None:
        universe = self._universe()
        early = self._batch(
            snapshot_id="early",
            snapshot_time_ms=900,
            markets=(
                self._market("AAA_USDT_PERP", 300.0),
                self._market("BBB_USDT_PERP", 200.0),
                self._market("CCC_USDT_PERP", 100.0),
            ),
        )
        late = self._batch(
            snapshot_id="late",
            snapshot_time_ms=1900,
            markets=(
                self._market("AAA_USDT_PERP", 100.0),
                self._market("BBB_USDT_PERP", 400.0),
                self._market("CCC_USDT_PERP", 200.0),
            ),
        )
        result = admit_plans_by_historical_liquidity(
            (
                self._plan("early-aaa", "AAA_USDT_PERP", 1000),
                self._plan("late-bbb", "BBB_USDT_PERP", 2000),
            ),
            liquidity_index=HistoricalLiquidityIndex((early, late)),
            universe_index=universe,
            provider="pionex",
            policy=HistoricalLiquidityPolicy(target_size=1, max_snapshot_age_ms=200),
        )

        self.assertEqual(tuple(plan.plan_id for plan in result.admitted_plans), ("early-aaa", "late-bbb"))
        self.assertEqual(tuple(decision.liquidity_batch_id for decision in result.decisions), ("early", "late"))

    def test_symbol_outside_historical_universe_is_rejected_even_if_liquidity_batch_contains_it(self) -> None:
        universe = self._universe()
        batch = self._batch(
            snapshot_id="s1",
            snapshot_time_ms=900,
            markets=(
                self._market("AAA_USDT_PERP", 300.0),
                self._market("BBB_USDT_PERP", 200.0),
                self._market("CCC_USDT_PERP", 100.0),
                self._market("DDD_USDT_PERP", 999.0),
            ),
        )
        result = admit_plans_by_historical_liquidity(
            (self._plan("ddd", "DDD_USDT_PERP", 1000),),
            liquidity_index=HistoricalLiquidityIndex((batch,)),
            universe_index=universe,
            provider="pionex",
            policy=HistoricalLiquidityPolicy(target_size=3, max_snapshot_age_ms=200),
        )

        self.assertEqual(
            result.rejected_plans,
            (("ddd", "symbol_not_historically_eligible_at_signal_time"),),
        )
        self.assertEqual(result.decisions[0].universe_authority_refs, ())
        self.assertIsNone(result.decisions[0].liquidity_rank)

    def test_missing_or_stale_liquidity_authority_is_evidence_error_not_strategy_rejection(self) -> None:
        universe = self._universe()
        stale = self._batch(
            snapshot_id="stale",
            snapshot_time_ms=500,
            markets=(
                self._market("AAA_USDT_PERP", 300.0),
                self._market("BBB_USDT_PERP", 200.0),
                self._market("CCC_USDT_PERP", 100.0),
            ),
        )

        with self.assertRaisesRegex(HistoricalLiquidityEvidenceError, "no fresh historical liquidity batch"):
            admit_plans_by_historical_liquidity(
                (self._plan("aaa", "AAA_USDT_PERP", 1000),),
                liquidity_index=HistoricalLiquidityIndex((stale,)),
                universe_index=universe,
                provider="pionex",
                policy=HistoricalLiquidityPolicy(target_size=1, max_snapshot_age_ms=200),
            )

    def test_incomplete_batch_aborts_admission_instead_of_changing_candidate_set(self) -> None:
        universe = self._universe()
        incomplete = self._batch(
            snapshot_id="incomplete",
            snapshot_time_ms=900,
            markets=(
                self._market("AAA_USDT_PERP", 300.0),
                self._market("BBB_USDT_PERP", 200.0),
            ),
        )

        with self.assertRaisesRegex(HistoricalLiquidityEvidenceError, "complete evidence-bounded universe"):
            admit_plans_by_historical_liquidity(
                (self._plan("aaa", "AAA_USDT_PERP", 1000),),
                liquidity_index=HistoricalLiquidityIndex((incomplete,)),
                universe_index=universe,
                provider="pionex",
                policy=HistoricalLiquidityPolicy(target_size=1, max_snapshot_age_ms=200),
            )

    def test_duplicate_plan_ids_are_rejected_before_liquidity_admission(self) -> None:
        universe = self._universe()
        batch = self._batch(
            snapshot_id="s1",
            snapshot_time_ms=900,
            markets=(
                self._market("AAA_USDT_PERP", 300.0),
                self._market("BBB_USDT_PERP", 200.0),
                self._market("CCC_USDT_PERP", 100.0),
            ),
        )

        with self.assertRaisesRegex(ValueError, "plan_id values must be unique"):
            admit_plans_by_historical_liquidity(
                (
                    self._plan("dup", "AAA_USDT_PERP", 1000),
                    self._plan("dup", "BBB_USDT_PERP", 1000),
                ),
                liquidity_index=HistoricalLiquidityIndex((batch,)),
                universe_index=universe,
                provider="pionex",
                policy=HistoricalLiquidityPolicy(target_size=2, max_snapshot_age_ms=200),
            )


if __name__ == "__main__":
    unittest.main()
