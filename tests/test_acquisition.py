import unittest

from crypto_autopilot.historical import INTERVAL_MS
from scripts.acquire_pionex_sample import closed_boundary_ms


class AcquisitionTests(unittest.TestCase):
    def test_closed_boundary_excludes_current_four_hour_bucket(self) -> None:
        step = INTERVAL_MS["4H"]
        now = 10 * step + 12345
        self.assertEqual(closed_boundary_ms(now), 10 * step - 1)


if __name__ == "__main__":
    unittest.main()
