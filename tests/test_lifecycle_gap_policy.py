from __future__ import annotations

import hashlib
import io
import json
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from crypto_autopilot.binance.lifecycle_gap_policy import (
    POLICY_ID,
    match_lifecycle_gap,
    reviewed_allowances,
)
from crypto_autopilot.binance.vision import BinanceVisionArchiveKey, ingest_kline_archive
from crypto_autopilot.binance_historical import BINANCE_INTERVAL_MS
from crypto_autopilot.historical import CandleAudit, CandleGap


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/binance_usdm_lifecycle_gap_policy_v0_1.json"
AUTHORITY = (
    ROOT
    / "research/receipts/2026-09-12-binance-usdm-lifecycle-gap-policy-v0-1-authority.json"
)


def make_zip(filename: str, rows: list[str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(filename, "\n".join(rows) + "\n")
    return buffer.getvalue()


def checksum_for(filename: str, payload: bytes) -> str:
    return f"{hashlib.sha256(payload).hexdigest()}  {filename}\n"


class LifecycleGapPolicyTests(unittest.TestCase):
    def test_runtime_allowlist_matches_reviewed_config_and_authority(self) -> None:
        raw = CONFIG.read_bytes()
        config = json.loads(raw)
        authority = json.loads(AUTHORITY.read_bytes())
        self.assertEqual(config["policy_id"], POLICY_ID)
        self.assertEqual(config["allowances"], list(reviewed_allowances()))
        self.assertEqual(len(config["allowances"]), authority["entries"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), authority["config_sha256"])
        self.assertTrue(authority["user_authorized_operational_treatment"])
        self.assertTrue(authority["exact_allowlist_only"])
        self.assertFalse(authority["synthetic_candles_authorized"])
        self.assertFalse(authority["interpolation_authorized"])
        self.assertFalse(authority["source_switch_authorized"])
        self.assertFalse(authority["holdout_access_authorized"])
        self.assertTrue(authority["training_segmentation_required"])

    def test_exact_ctk_gap_matches_but_revision_or_geometry_does_not(self) -> None:
        key = BinanceVisionArchiveKey("klines", "monthly", "CTKUSDT", "15m", "2025-04")
        audit = CandleAudit(
            interval="15M",
            count=2839,
            duplicate_timestamps=(),
            out_of_order_pairs=(),
            gaps=(CandleGap(1745970300000, 1746008100000, 41),),
            misaligned_timestamps=(),
            invalid_candle_timestamps=(),
        )
        digest = "bd77c44d0061511b2e8f5c140a06ad2dd30007c640586fad5b035d71b0c3c61c"
        self.assertEqual(
            match_lifecycle_gap(key, archive_sha256=digest, audit=audit), POLICY_ID
        )
        self.assertIsNone(match_lifecycle_gap(key, archive_sha256="0" * 64, audit=audit))

        wrong_gap = CandleAudit(
            interval="15M",
            count=2839,
            duplicate_timestamps=(),
            out_of_order_pairs=(),
            gaps=(CandleGap(1745970300000, 1746009000000, 42),),
            misaligned_timestamps=(),
            invalid_candle_timestamps=(),
        )
        self.assertIsNone(
            match_lifecycle_gap(key, archive_sha256=digest, audit=wrong_gap)
        )

    def test_exact_cvc_relaunch_month_gap_is_archive_pinned(self) -> None:
        key = BinanceVisionArchiveKey("klines", "monthly", "CVCUSDT", "15m", "2025-05")
        audit = CandleAudit(
            interval="15M",
            count=2942,
            duplicate_timestamps=(),
            out_of_order_pairs=(),
            gaps=(CandleGap(0, 35 * 900000, 34),),
            misaligned_timestamps=(),
            invalid_candle_timestamps=(),
        )
        digest = "d9940880a57d29b57185712e3c12defd2ea5b0f9044d2da23510d9450570bd40"
        self.assertEqual(
            match_lifecycle_gap(key, archive_sha256=digest, audit=audit), POLICY_ID
        )
        self.assertIsNone(match_lifecycle_gap(key, archive_sha256="0" * 64, audit=audit))

        wrong_missing = CandleAudit(
            interval=audit.interval,
            count=audit.count,
            duplicate_timestamps=(),
            out_of_order_pairs=(),
            gaps=(CandleGap(0, 36 * 900000, 35),),
            misaligned_timestamps=(),
            invalid_candle_timestamps=(),
        )
        self.assertIsNone(
            match_lifecycle_gap(key, archive_sha256=digest, audit=wrong_missing)
        )

    def test_lit_allowance_is_archive_pinned_and_rejects_other_defects(self) -> None:
        key = BinanceVisionArchiveKey("klines", "monthly", "LITUSDT", "15m", "2025-12")
        audit = CandleAudit(
            interval="15M",
            count=2906,
            duplicate_timestamps=(),
            out_of_order_pairs=(),
            gaps=(CandleGap(0, 71 * 900000, 70),),
            misaligned_timestamps=(),
            invalid_candle_timestamps=(),
        )
        digest = "246dca9c1bcc046af274cc4d5b61fdd1fb818f243a2ae3c82a20471bdecdd160"
        self.assertEqual(
            match_lifecycle_gap(key, archive_sha256=digest, audit=audit), POLICY_ID
        )
        with_duplicate = CandleAudit(
            interval=audit.interval,
            count=audit.count,
            duplicate_timestamps=(0,),
            out_of_order_pairs=(),
            gaps=audit.gaps,
            misaligned_timestamps=(),
            invalid_candle_timestamps=(),
        )
        self.assertIsNone(
            match_lifecycle_gap(key, archive_sha256=digest, audit=with_duplicate)
        )

    def test_accepted_gap_is_preserved_without_synthetic_rows(self) -> None:
        key = BinanceVisionArchiveKey("klines", "monthly", "TESTUSDT", "1h", "2025-01")
        step = BINANCE_INTERVAL_MS["1h"]
        rows = [
            f"0,100,102,99,101,10,{step - 1},0,1,0,0,0",
            f"{2 * step},102,104,101,103,12,{3 * step - 1},0,1,0,0,0",
        ]
        payload = make_zip(key.csv_filename, rows)
        with patch(
            "crypto_autopilot.binance.vision.match_lifecycle_gap",
            return_value=POLICY_ID,
        ):
            result = ingest_kline_archive(
                key,
                archive_bytes=payload,
                checksum_payload=checksum_for(key.filename, payload),
            )
        self.assertEqual([candle.time_ms for candle in result.candles], [0, 2 * step])
        self.assertFalse(result.receipt.audit_ok)


if __name__ == "__main__":
    unittest.main()
