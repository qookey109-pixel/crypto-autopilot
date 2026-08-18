from __future__ import annotations

import unittest

from crypto_autopilot.historical_universe import (
    HistoricalMarketRecord,
    HistoricalUniverseConflictError,
    HistoricalUniverseIndex,
    record_from_partition_receipt,
)


DAY = 86_400_000


def record(
    symbol: str,
    interval: str,
    start_day: int,
    end_day: int,
    *,
    provider: str = "pionex",
    native: bool = True,
    source_ref: str | None = None,
) -> HistoricalMarketRecord:
    return HistoricalMarketRecord(
        provider=provider,
        market_type="perp",
        symbol=symbol,
        interval=interval,
        available_from_ms=start_day * DAY,
        available_to_ms=end_day * DAY,
        evidence_type="verified_partition_receipt",
        source_ref=source_ref or f"{provider}:{symbol}:{interval}:{start_day}-{end_day}",
        native=native,
    )


class HistoricalUniverseTest(unittest.TestCase):
    def test_symbol_requires_coverage_for_all_required_intervals(self) -> None:
        index = HistoricalUniverseIndex(
            [
                record("BTC_USDT_PERP", "15M", 0, 100),
                record("BTC_USDT_PERP", "60M", 0, 100),
                record("BTC_USDT_PERP", "4H", 0, 100),
                record("NEW_USDT_PERP", "15M", 50, 100),
                record("NEW_USDT_PERP", "60M", 50, 100),
            ]
        )
        self.assertEqual(
            index.available_symbols_at(60 * DAY, provider="pionex"),
            ("BTC_USDT_PERP",),
        )

    def test_no_survivorship_extrapolation_before_first_observed_history(self) -> None:
        index = HistoricalUniverseIndex(
            [
                record("OLD_USDT_PERP", "15M", 0, 100),
                record("OLD_USDT_PERP", "60M", 0, 100),
                record("OLD_USDT_PERP", "4H", 0, 100),
                record("NEW_USDT_PERP", "15M", 50, 100),
                record("NEW_USDT_PERP", "60M", 50, 100),
                record("NEW_USDT_PERP", "4H", 50, 100),
            ]
        )
        self.assertEqual(index.available_symbols_at(25 * DAY, provider="pionex"), ("OLD_USDT_PERP",))
        self.assertEqual(
            index.available_symbols_at(60 * DAY, provider="pionex"),
            ("NEW_USDT_PERP", "OLD_USDT_PERP"),
        )

    def test_no_extrapolation_after_last_observed_history(self) -> None:
        index = HistoricalUniverseIndex(
            [
                record("DELISTED_USDT_PERP", "15M", 0, 40),
                record("DELISTED_USDT_PERP", "60M", 0, 40),
                record("DELISTED_USDT_PERP", "4H", 0, 40),
            ]
        )
        self.assertEqual(index.available_symbols_at(41 * DAY, provider="pionex"), ())

    def test_external_proxy_is_excluded_from_native_snapshot(self) -> None:
        records = [
            record("BTC_USDT_PERP", "15M", 0, 100, provider="binance", native=False),
            record("BTC_USDT_PERP", "60M", 0, 100, provider="binance", native=False),
            record("BTC_USDT_PERP", "4H", 0, 100, provider="binance", native=False),
        ]
        index = HistoricalUniverseIndex(records)
        self.assertEqual(index.available_symbols_at(10 * DAY, provider="binance", native_only=True), ())
        self.assertEqual(
            index.available_symbols_at(10 * DAY, provider="binance", native_only=False),
            ("BTC_USDT_PERP",),
        )

    def test_overlapping_non_identical_authority_is_rejected(self) -> None:
        with self.assertRaises(HistoricalUniverseConflictError):
            HistoricalUniverseIndex(
                [
                    record("BTC_USDT_PERP", "15M", 0, 50, source_ref="receipt-a"),
                    record("BTC_USDT_PERP", "15M", 40, 80, source_ref="receipt-b"),
                ]
            )

    def test_snapshot_is_sorted_and_records_authority_refs(self) -> None:
        records = []
        for symbol in ("ETH_USDT_PERP", "BTC_USDT_PERP"):
            for interval in ("15M", "60M", "4H"):
                records.append(record(symbol, interval, 0, 100))
        snapshot = HistoricalUniverseIndex(records).snapshot(10 * DAY, provider="pionex")
        self.assertEqual(snapshot.symbols, ("BTC_USDT_PERP", "ETH_USDT_PERP"))
        self.assertEqual(tuple(sorted(snapshot.authority_refs)), snapshot.authority_refs)
        self.assertEqual(len(snapshot.authority_refs), 6)

    def test_partition_receipt_conversion_requires_pass_and_explicit_provenance(self) -> None:
        payload = {
            "status": "PASS",
            "provider": "pionex",
            "market_type": "perp",
            "symbol": "BTC_USDT_PERP",
            "interval": "15M",
            "actual_first_ms": 1000,
            "actual_last_ms": 2000,
            "audit_ok": True,
        }
        converted = record_from_partition_receipt(payload, source_ref="r2-receipt", native=True)
        self.assertIsNotNone(converted)
        assert converted is not None
        self.assertTrue(converted.native)
        self.assertEqual(converted.available_from_ms, 1000)
        self.assertEqual(converted.available_to_ms, 2000)

        bad = {**payload, "audit_ok": False}
        with self.assertRaises(ValueError):
            record_from_partition_receipt(bad, source_ref="bad", native=True)

        self.assertIsNone(
            record_from_partition_receipt(
                {**payload, "status": "NO_DATA"},
                source_ref="empty",
                native=True,
            )
        )


if __name__ == "__main__":
    unittest.main()
