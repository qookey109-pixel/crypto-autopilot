from __future__ import annotations

from crypto_autopilot.binance.lifecycle_gap_policy import POLICY_ID, match_lifecycle_gap
from crypto_autopilot.binance.vision import BinanceVisionArchiveKey
from crypto_autopilot.historical import CandleAudit, CandleGap


def _audit(count: int, missing_bars: int) -> CandleAudit:
    step_ms = 4 * 60 * 60 * 1000
    return CandleAudit(
        interval="4H",
        count=count,
        duplicate_timestamps=(),
        out_of_order_pairs=(),
        gaps=(CandleGap(0, (missing_bars + 1) * step_ms, missing_bars),),
        misaligned_timestamps=(),
        invalid_candle_timestamps=(),
    )


def test_exact_cvc_4h_lifecycle_gap_is_checksum_and_geometry_pinned() -> None:
    key = BinanceVisionArchiveKey("klines", "monthly", "CVCUSDT", "4h", "2025-05")
    digest = "fbcbdbb7efb85914de3ee359c07f67b635bad4d81c8fbbb642cdec4d8a5b6151"
    audit = _audit(184, 2)

    assert match_lifecycle_gap(key, archive_sha256=digest, audit=audit) == POLICY_ID
    assert match_lifecycle_gap(key, archive_sha256="0" * 64, audit=audit) is None
    assert match_lifecycle_gap(key, archive_sha256=digest, audit=_audit(184, 3)) is None
    assert match_lifecycle_gap(key, archive_sha256=digest, audit=_audit(185, 2)) is None


def test_cvc_4h_allowance_does_not_generalize_to_other_periods() -> None:
    digest = "fbcbdbb7efb85914de3ee359c07f67b635bad4d81c8fbbb642cdec4d8a5b6151"
    audit = _audit(184, 2)
    other = BinanceVisionArchiveKey("klines", "monthly", "CVCUSDT", "4h", "2025-04")

    assert match_lifecycle_gap(other, archive_sha256=digest, audit=audit) is None
