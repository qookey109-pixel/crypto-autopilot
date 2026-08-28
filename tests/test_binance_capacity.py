from __future__ import annotations

import unittest

from crypto_autopilot.binance.capacity import estimate_binance_observed_capacity


class BinanceObservedCapacityTests(unittest.TestCase):
    def test_2025_pilot_imputes_partial_market_before_scaling(self) -> None:
        result = estimate_binance_observed_capacity(
            observed_rows=671_022,
            observed_parquet_bytes=18_778_928,
        )
        self.assertEqual(result.full_candidate_year_rows, 689_850)
        self.assertEqual(result.missing_equivalent_rows, 18_828)
        self.assertAlmostEqual(result.observed_bytes_per_row, 27.98556232135459)
        self.assertAlmostEqual(result.canonical_target_gb, 2.5741120223181953)
        self.assertAlmostEqual(result.canonical_plus_staging_gb, 5.148224044636391)
        self.assertAlmostEqual(result.three_x_capacity_stress_gb, 7.722336066954586)

    def test_full_coverage_does_not_impute_rows(self) -> None:
        rows = 15 * 45_990
        result = estimate_binance_observed_capacity(
            observed_rows=rows,
            observed_parquet_bytes=20_000_000,
        )
        self.assertEqual(result.missing_equivalent_rows, 0)
        self.assertEqual(result.full_candidate_year_equivalent_bytes, 20_000_000)

    def test_observation_above_frozen_row_envelope_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            estimate_binance_observed_capacity(
                observed_rows=15 * 45_990 + 1,
                observed_parquet_bytes=20_000_000,
            )

    def test_invalid_inputs_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            estimate_binance_observed_capacity(observed_rows=0, observed_parquet_bytes=1)
        with self.assertRaises(ValueError):
            estimate_binance_observed_capacity(observed_rows=1, observed_parquet_bytes=0)


if __name__ == "__main__":
    unittest.main()
