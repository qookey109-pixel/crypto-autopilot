from __future__ import annotations

import unittest
from dataclasses import dataclass
from datetime import UTC, datetime

from crypto_autopilot.models import BookTicker, Candle, MarketTicker
from crypto_autopilot.paper.cloud_composition_v0_1 import (
    CloudPaperCompositionBlocked,
    CloudPaperNoTradeComposition,
)
from crypto_autopilot.paper.live_v0_1 import LivePaperPolicy
from crypto_autopilot.paper.run_store_v0_1 import PaperRunObjectAlreadyExistsError

NOW = int(datetime(2026, 9, 27, 8, 7, tzinfo=UTC).timestamp() * 1000)
HOUR_MS = 3_600_000


def bars():
    end = NOW // HOUR_MS * HOUR_MS
    return [
        Candle(
            time_ms=end - (240 - i) * HOUR_MS,
            open=100 + i, high=102 + i, low=99 + i,
            close=101 + i, volume=1000,
        )
        for i in range(240)
    ]


class FakeClient:
    def __init__(self):
        self.calls = []

    def list_perpetual_symbols(self):
        self.calls.append("symbols")
        return ["BTC_USDT_PERP", "UNKNOWNX_USDT_PERP"]

    def list_perpetual_tickers(self):
        self.calls.append("tickers")
        return [
            MarketTicker(symbol=s, close=340, base_volume=1000,
                         quote_amount=1_000_000, trade_count=100)
            for s in ("BTC_USDT_PERP", "UNKNOWNX_USDT_PERP")
        ]

    def list_perpetual_book_tickers(self):
        self.calls.append("books")
        return [
            BookTicker(symbol=s, bid_price=340, bid_size=10,
                       ask_price=340.1, ask_size=10, timestamp_ms=NOW)
            for s in ("BTC_USDT_PERP", "UNKNOWNX_USDT_PERP")
        ]

    def get_klines(self, symbol, interval, *, limit, end_time_ms):
        self.calls.append(("klines", symbol, interval, limit, end_time_ms))
        return bars()

    def get_order_book(self, symbol, *, limit):
        raise AssertionError("empty-registry no-trade path must not fetch a book")

    def get_recent_trades(self, symbol, *, limit):
        raise AssertionError("empty-registry no-trade path must not fetch trades")


@dataclass
class Receipt:
    replayed: bool


class MemoryStore:
    def __init__(self):
        self.objects = {}
        self.calls = []

    def get_json(self, kind, object_id):
        self.calls.append(("get", kind, object_id))
        return self.objects.get((kind, object_id))

    def list_json_ids(self, kind):
        self.calls.append(("list", kind))
        return tuple(sorted(
            object_id for (stored_kind, object_id) in self.objects
            if stored_kind == kind
        ))

    def put_json(self, kind, object_id, payload):
        self.calls.append(("put", kind, object_id))
        key = (kind, object_id)
        if key in self.objects:
            if self.objects[key] != dict(payload):
                raise ValueError("immutable collision")
            return Receipt(True)
        self.objects[key] = dict(payload)
        return Receipt(False)

    def put_json_if_absent(self, kind, object_id, payload):
        self.calls.append(("put_if_absent", kind, object_id))
        key = (kind, object_id)
        if key in self.objects:
            raise PaperRunObjectAlreadyExistsError("already claimed")
        self.objects[key] = dict(payload)
        return Receipt(False)


REGISTRY = {
    "schema": "qookey-cloud-paper-strategy-registry-v0.1",
    "status": "EMPTY_NO_ELIGIBLE_STRATEGIES",
    "provider": "PIONEX_PUBLIC",
    "strategies": [],
    "model_quality": "REJECT",
    "production_fixture_admission": False,
    "automatic_promotion": False,
}


def composition(client, store, registry=REGISTRY, permits=None, accesses=None):
    permits = permits if permits is not None else []
    accesses = accesses if accesses is not None else []
    return CloudPaperNoTradeComposition(
        client=client,
        store=store,
        strategy_registry=registry,
        allowed_base_assets=frozenset({"BTC"}),
        paper_policy=LivePaperPolicy(),
        reserve_provider_request=lambda: permits.append("PIONEX_PUBLIC"),
        before_external=lambda: accesses.append("guard"),
    )


class CloudPaperCompositionTests(unittest.TestCase):
    def test_disabled_is_side_effect_free(self):
        client, store, permits, accesses = FakeClient(), MemoryStore(), [], []
        result = composition(client, store, permits=permits, accesses=accesses).run_slot(
            tick_ms=NOW, previous_slot=None,
        )
        self.assertEqual(result["state"], "DISABLED")
        self.assertEqual(result["reason"], "ACTIVATION_DISABLED")
        self.assertEqual(client.calls, [])
        self.assertEqual(store.calls, [])
        self.assertEqual(permits, [])
        self.assertEqual(accesses, [])

    def test_nonempty_registry_fails_before_external_access(self):
        client, store, permits, accesses = FakeClient(), MemoryStore(), [], []
        registry = {**REGISTRY, "status": "READY", "strategies": [{"strategy_id": "x"}]}
        runtime = composition(client, store, registry, permits, accesses)
        with self.assertRaisesRegex(
            CloudPaperCompositionBlocked, "PRODUCTION_STRATEGY_AUTHORITY_UNAVAILABLE",
        ):
            runtime.run_slot(tick_ms=NOW, previous_slot=None, activation_enabled=True)
        self.assertEqual(client.calls, [])
        self.assertEqual(store.calls, [])
        self.assertEqual(permits, [])
        self.assertEqual(accesses, [])

    def test_enabled_empty_registry_composes_to_audited_no_trade(self):
        client, store, permits, accesses = FakeClient(), MemoryStore(), [], []
        result = composition(client, store, permits=permits, accesses=accesses).run_slot(
            tick_ms=NOW, previous_slot=None, activation_enabled=True,
        )
        self.assertEqual(result["state"], "NO_TRADE")
        self.assertEqual(result["reason_codes"], [
            "REGIME_UNAVAILABLE", "NO_ELIGIBLE_STRATEGY",
        ])
        self.assertEqual(result["market"]["provider"], "PIONEX_PUBLIC")
        self.assertEqual(result["market"]["candidate_specs"], [])
        self.assertEqual(result["operation_counts"]["provider_requests"], 4)
        self.assertEqual(len(permits), 4)
        self.assertTrue(store.calls)
        self.assertTrue(accesses)
        self.assertTrue(any(kind == "cloud-report" for kind, _ in store.objects))
        self.assertTrue(any(kind == "cloud-result" for kind, _ in store.objects))


if __name__ == "__main__":
    unittest.main()
