from __future__ import annotations

from crypto_autopilot.binance.lifecycle_gap_policy import POLICY_ID, match_lifecycle_gap
from crypto_autopilot.binance.vision import BinanceVisionArchiveKey
from crypto_autopilot.historical import CandleAudit, CandleGap


def _audit(interval: str, count: int, missing_bars: int, step_ms: int) -> CandleAudit:
    return CandleAudit(
        interval=interval.upper(),
        count=count,
        duplicate_timestamps=(),
        out_of_order_pairs=(),
        gaps=(CandleGap(0, (missing_bars + 1) * step_ms, missing_bars),),
        misaligned_timestamps=(),
        invalid_candle_timestamps=(),
    )


def test_exact_cvc_1h_lifecycle_gap_is_checksum_and_geometry_pinned() -> None:
    key = BinanceVisionArchiveKey("klines", "monthly", "CVCUSDT", "1h", "2025-05")
    digest = "236cf0cecf8c927f3f5d07e7fc0c5171a09b60377641b1c7a8df3609674bd454"
    audit = _audit("1h", 736, 8, 3_600_000)

    assert match_lifecycle_gap(key, archive_sha256=digest, audit=audit) == POLICY_ID
    assert match_lifecycle_gap(key, archive_sha256="0" * 64, audit=audit) is None
    assert (
        match_lifecycle_gap(
            key,
            archive_sha256=digest,
            audit=_audit("1h", 736, 9, 3_600_000),
        )
        is None
    )


def test_exact_lit_1h_lifecycle_gap_is_checksum_and_geometry_pinned() -> None:
    key = BinanceVisionArchiveKey("klines", "monthly", "LITUSDT", "1h", "2025-12")
    digest = "8a92afa0f2ee875b880d37161055690394f14172eea48d6e243061db9426c6d3"
    audit = _audit("1h", 727, 17, 3_600_000)

    assert match_lifecycle_gap(key, archive_sha256=digest, audit=audit) == POLICY_ID
    assert match_lifecycle_gap(key, archive_sha256="f" * 64, audit=audit) is None
    assert (
        match_lifecycle_gap(
            key,
            archive_sha256=digest,
            audit=_audit("1h", 728, 17, 3_600_000),
        )
        is None
    )
