import unittest

from crypto_autopilot.exchanges.base import LiveTradingDisabledError
from crypto_autopilot.exchanges.paper import PaperBroker


class PaperBrokerTests(unittest.TestCase):
    def test_duplicate_order_id_is_idempotent(self) -> None:
        broker = PaperBroker()
        a = broker.submit_long(order_id="sig-1", symbol="BTC_USDT_PERP", notional_usd=100)
        b = broker.submit_long(order_id="sig-1", symbol="BTC_USDT_PERP", notional_usd=100)
        self.assertEqual(a, b)
        self.assertEqual(len(broker.orders), 1)

    def test_live_path_is_disabled(self) -> None:
        broker = PaperBroker()
        with self.assertRaises(LiveTradingDisabledError):
            broker.submit_live_order()


if __name__ == "__main__":
    unittest.main()
