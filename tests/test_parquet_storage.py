import hashlib
import unittest

from crypto_autopilot.models import Candle
from crypto_autopilot.storage.parquet import candles_to_parquet, parquet_to_candles


class ParquetStorageTests(unittest.TestCase):
    def test_round_trip_preserves_candles_and_hash(self) -> None:
        candles = [
            Candle(time_ms=2, open=2.0, high=3.0, low=1.0, close=2.5, volume=20.0),
            Candle(time_ms=1, open=1.0, high=2.0, low=0.5, close=1.5, volume=10.0),
        ]
        artifact = candles_to_parquet(candles)
        restored = parquet_to_candles(artifact.payload)

        self.assertEqual(artifact.rows, 2)
        self.assertEqual(artifact.first_time_ms, 1)
        self.assertEqual(artifact.last_time_ms, 2)
        self.assertEqual(artifact.sha256, hashlib.sha256(artifact.payload).hexdigest())
        self.assertEqual([c.time_ms for c in restored], [1, 2])
        self.assertEqual(restored[0].close, 1.5)
        self.assertEqual(restored[1].volume, 20.0)


if __name__ == "__main__":
    unittest.main()
