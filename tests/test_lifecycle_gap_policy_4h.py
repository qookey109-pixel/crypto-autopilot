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


def test_exact_lit_4h_lifecycle_gap_is_checksum_and_geometry_pinned() -> None:
    key = BinanceVisionArchiveKey("klines", "monthly", "LITUSDT", "4h", "2025-12")
    digest = "4d7e61e25eb2fab01e4d1206b36372009ee3bfc60dab72405076e9f6aa8852b2"
    audit = _audit(182, 4)

    assert match_lifecycle_gap(key, archive_sha256=digest, audit=audit) == POLICY_ID
    assert match_lifecycle_gap(key, archive_sha256="0" * 64, audit=audit) is None
    assert match_lifecycle_gap(key, archive_sha256=digest, audit=_audit(182, 5)) is None
    assert match_lifecycle_gap(key, archive_sha256=digest, audit=_audit(183, 4)) is None


def test_lit_4h_allowance_does_not_generalize_to_other_periods() -> None:
    digest = "4d7e61e25eb2fab01e4d1206b36372009ee3bfc60dab72405076e9f6aa8852b2"
    audit = _audit(182, 4)
    other = BinanceVisionArchiveKey("klines", "monthly", "LITUSDT", "4h", "2025-11")

    assert match_lifecycle_gap(other, archive_sha256=digest, audit=audit) is None
