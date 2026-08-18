from __future__ import annotations

import unittest

from crypto_autopilot.backtest import LongTradePlan
from crypto_autopilot.historical_admission import admit_plans_by_historical_universe
from crypto_autopilot.historical_universe import HistoricalMarketRecord, HistoricalUniverseIndex


def _record(
    symbol: str,
    interval: str,
    start: int,
    end: int,
    *,
    source_ref: str | None = None,
    native: bool = True,
) -> HistoricalMarketRecord:
    return HistoricalMarketRecord(
        provider="pionex",
        market_type="perp",
        symbol=symbol,
        interval=interval,
        available_from_ms=start,
        available_to_ms=end,
        evidence_type="verified_partition_receipt" if native else "external_proxy_observation",
        source_ref=source_ref or f"receipt:{symbol}:{interval}:{start}:{end}:{native}",
        native=native,
    )


def _native_bundle(symbol: str, start: int, end: int) -> list[HistoricalMarketRecord]:
    return [_record(symbol, interval, start, end) for interval in ("15M", "60M", "4H")]


def _plan(plan_id: str, symbol: str, signal_time_ms: int) -> LongTradePlan:
    return LongTradePlan(
        plan_id=plan_id,
        symbol=symbol,
        signal_time_ms=signal_time_ms,
        stop_price=90.0,
        target_price=120.0,
    )


class HistoricalAdmissionTest(unittest.TestCase):
    def test_plan_is_admitted_only_inside_complete_native_coverage(self) -> None:
        index = HistoricalUniverseIndex(_native_bundle("BTC_USDT_PERP", 1000, 5000))
        result = admit_plans_by_historical_universe(
            [_plan("p1", "BTC_USDT_PERP", 3000)],
            index=index,
            provider="pionex",
        )

        self.assertEqual([plan.plan_id for plan in result.admitted_plans], ["p1"])
        self.assertEqual(result.rejected_plans, ())
        self.assertTrue(result.decisions[0].admitted)
        self.assertEqual(result.decisions[0].reason, "historical_universe_eligible")
        self.assertEqual(len(result.decisions[0].authority_refs), 3)

    def test_today_or_later_coverage_never_authorizes_an_earlier_plan(self) -> None:
        index = HistoricalUniverseIndex(_native_bundle("NEW_USDT_PERP", 10_000, 20_000))
        result = admit_plans_by_historical_universe(
            [_plan("early", "NEW_USDT_PERP", 9_999)],
            index=index,
            provider="pionex",
        )

        self.assertEqual(result.admitted_plans, ())
        self.assertEqual(
            result.rejected_plans,
            (("early", "symbol_not_historically_eligible_at_signal_time"),),
        )
        self.assertEqual(result.decisions[0].authority_refs, ())

    def test_missing_required_interval_fails_closed(self) -> None:
        records = [
            _record("BTC_USDT_PERP", "15M", 0, 5000),
            _record("BTC_USDT_PERP", "60M", 0, 5000),
        ]
        index = HistoricalUniverseIndex(records)
        result = admit_plans_by_historical_universe(
            [_plan("missing-4h", "BTC_USDT_PERP", 2000)],
            index=index,
            provider="pionex",
        )

        self.assertEqual(result.admitted_plans, ())
        self.assertFalse(result.decisions[0].admitted)

    def test_proxy_only_coverage_cannot_admit_native_backtest_plan(self) -> None:
        records = [
            _record("BTC_USDT_PERP", interval, 0, 5000, native=False)
            for interval in ("15M", "60M", "4H")
        ]
        index = HistoricalUniverseIndex(records)
        result = admit_plans_by_historical_universe(
            [_plan("proxy", "BTC_USDT_PERP", 2000)],
            index=index,
            provider="pionex",
        )

        self.assertEqual(result.admitted_plans, ())
        self.assertFalse(result.decisions[0].admitted)

    def test_each_plan_is_checked_at_its_own_signal_time(self) -> None:
        index = HistoricalUniverseIndex(_native_bundle("BTC_USDT_PERP", 1000, 5000))
        plans = [
            _plan("inside", "BTC_USDT_PERP", 3000),
            _plan("after", "BTC_USDT_PERP", 5001),
        ]
        result = admit_plans_by_historical_universe(plans, index=index, provider="pionex")

        self.assertEqual([plan.plan_id for plan in result.admitted_plans], ["inside"])
        self.assertEqual(result.rejected_plans[0][0], "after")
        self.assertEqual([decision.signal_time_ms for decision in result.decisions], [3000, 5001])

    def test_authority_refs_are_scoped_to_the_plan_symbol(self) -> None:
        records = _native_bundle("BTC_USDT_PERP", 0, 5000) + _native_bundle("ETH_USDT_PERP", 0, 5000)
        index = HistoricalUniverseIndex(records)
        result = admit_plans_by_historical_universe(
            [_plan("btc", "BTC_USDT_PERP", 2000)],
            index=index,
            provider="pionex",
        )

        refs = result.decisions[0].authority_refs
        self.assertEqual(len(refs), 3)
        self.assertTrue(all("BTC_USDT_PERP" in ref for ref in refs))
        self.assertTrue(all("ETH_USDT_PERP" not in ref for ref in refs))

    def test_duplicate_plan_ids_are_rejected_before_admission(self) -> None:
        index = HistoricalUniverseIndex(_native_bundle("BTC_USDT_PERP", 0, 5000))
        plans = [
            _plan("same", "BTC_USDT_PERP", 1000),
            _plan("same", "BTC_USDT_PERP", 2000),
        ]

        with self.assertRaisesRegex(ValueError, "plan_id values must be unique"):
            admit_plans_by_historical_universe(plans, index=index, provider="pionex")

    def test_admission_is_deterministic(self) -> None:
        index = HistoricalUniverseIndex(_native_bundle("BTC_USDT_PERP", 0, 5000))
        plans = [_plan("p1", "BTC_USDT_PERP", 2000)]

        first = admit_plans_by_historical_universe(plans, index=index, provider="pionex")
        second = admit_plans_by_historical_universe(plans, index=index, provider="pionex")

        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
