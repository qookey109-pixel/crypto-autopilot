import hashlib
import io
import unittest
import zipfile
from datetime import datetime, timezone

from crypto_autopilot.binance.vision import BinanceVisionArchiveKey, BinanceVisionEvidenceError
from crypto_autopilot.history.archive_repair import reconcile_monthly_from_daily


class ArchiveRepairTests(unittest.TestCase):
    def setUp(self):
        self.key = BinanceVisionArchiveKey("klines", "monthly", "BNXUSDT", "15m", "2022-08")
        self.start = int(datetime(2022, 8, 1, tzinfo=timezone.utc).timestamp() * 1000)
        self.step = 900000
        self.times = list(range(self.start, self.start + 31 * 86400000, self.step))
        self.missing = set(self.times[9 * 96:12 * 96])
        self.original = [t for t in self.times if t not in self.missing]
        self.month, self.checksum = self.zip(self.key, self.original)

    def zip(self, key, times, close="1.5", volume="1"):
        csv = "\n".join(f"{t},1,2,0.5,{close},{volume},{t + self.step - 1}" for t in times)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr(key.csv_filename, csv)
        data = buf.getvalue()
        return data, hashlib.sha256(data).hexdigest() + "  " + key.filename

    def daily(self, day, **kwargs):
        key = BinanceVisionArchiveKey("klines", "daily", "BNXUSDT", "15m", f"2022-08-{day:02d}")
        times = self.times[(day - 1) * 96:day * 96]
        data, checksum = self.zip(key, times, **kwargs)
        return key, data, checksum

    def run_repair(self, daily, **kwargs):
        return reconcile_monthly_from_daily(
            self.key, self.month, self.checksum, daily,
            expected_monthly_sha256=kwargs.get("sha", hashlib.sha256(self.month).hexdigest()),
        )

    def test_three_days_restored_with_original_values_preserved(self):
        candidate = self.run_repair([self.daily(d) for d in (9, 10, 11, 12)])
        self.assertEqual(len(candidate.candles), 2976)
        self.assertEqual(candidate.inserted_rows, 288)
        self.assertEqual(candidate.overlapping_rows_verified, 96)
        self.assertFalse(candidate.publication_authorized)
        self.assertEqual(candidate.status, "REPAIR_CANDIDATE_NOT_AUTHORIZED")
        self.assertEqual([r.time_ms for r in candidate.candles], self.times)
        self.assertTrue(all(r.close == 1.5 for r in candidate.candles))

    def test_incomplete_daily_supply_is_rejected(self):
        with self.assertRaises(BinanceVisionEvidenceError):
            self.run_repair([self.daily(9), self.daily(10)])

    def test_conflicting_overlap_is_rejected(self):
        with self.assertRaisesRegex(BinanceVisionEvidenceError, "overlap conflict"):
            self.run_repair([self.daily(9, close="1.6")] + [self.daily(d) for d in (10, 11, 12)])

    def test_no_overlap_is_rejected(self):
        with self.assertRaisesRegex(BinanceVisionEvidenceError, "overlap evidence"):
            self.run_repair([self.daily(d) for d in (10, 11, 12)])

    def test_checksums_revisions_duplicates_and_invalid_candles_rejected(self):
        days = [self.daily(d) for d in (9, 10, 11, 12)]
        with self.assertRaisesRegex(BinanceVisionEvidenceError, "revision"):
            self.run_repair(days, sha="0" * 64)
        key, data, checksum = days[0]
        with self.assertRaises(BinanceVisionEvidenceError):
            self.run_repair([(key, data, "0" * 64 + "  " + key.filename)] + days[1:])
        with self.assertRaises(BinanceVisionEvidenceError):
            self.run_repair(days + [days[0]])
        with self.assertRaises(BinanceVisionEvidenceError):
            self.run_repair([self.daily(9, volume="-1")] + days[1:])

    def test_wrong_symbol_and_wrong_month_rejected(self):
        days = [self.daily(d) for d in (9, 10, 11, 12)]
        for key in (
            BinanceVisionArchiveKey("klines", "daily", "BTCUSDT", "15m", "2022-08-09"),
            BinanceVisionArchiveKey("klines", "daily", "BNXUSDT", "15m", "2022-09-09"),
        ):
            with self.assertRaises(BinanceVisionEvidenceError):
                self.run_repair([(key, days[0][1], days[0][2])] + days[1:])

    def test_complete_month_is_not_repaired(self):
        self.month, self.checksum = self.zip(self.key, self.times)
        with self.assertRaisesRegex(BinanceVisionEvidenceError, "already complete"):
            self.run_repair([self.daily(9)])

    def test_edge_missing_bars_are_checked(self):
        self.month, self.checksum = self.zip(self.key, self.times[96:])
        result = self.run_repair([self.daily(1), self.daily(2)])
        self.assertEqual(result.inserted_rows, 96)

    def test_partial_daily_file_rejected_even_without_internal_gap(self):
        key, _, _ = self.daily(10)
        data, checksum = self.zip(key, self.times[9 * 96:10 * 96 - 1])
        with self.assertRaisesRegex(BinanceVisionEvidenceError, "entire UTC day"):
            self.run_repair([self.daily(9), (key, data, checksum), self.daily(11), self.daily(12)])


if __name__ == "__main__":
    unittest.main()
