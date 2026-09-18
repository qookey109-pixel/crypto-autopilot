from __future__ import annotations

from dataclasses import asdict
from typing import Sequence

from ..binance.vision import BinanceVisionArchiveKey, BinanceVisionKlineArchive
from ..models import Candle
from .bitget_macd_real_history import (
    EXPECTED_END_PERIOD,
    EXPECTED_INTERVAL,
    EXPECTED_START_PERIOD,
    EXPECTED_SYMBOL,
    BitgetMacdRealHistoryError,
    expected_monthly_periods,
    validate_contiguous_15m_history,
)


def zec_monthly_archive_keys() -> tuple[BinanceVisionArchiveKey, ...]:
    return tuple(
        BinanceVisionArchiveKey(
            dataset="klines",
            frequency="monthly",
            symbol=EXPECTED_SYMBOL,
            interval=EXPECTED_INTERVAL,
            period=period,
        )
        for period in expected_monthly_periods(EXPECTED_START_PERIOD, EXPECTED_END_PERIOD)
    )


def combine_verified_zec_archives(
    archives: Sequence[BinanceVisionKlineArchive],
) -> tuple[tuple[Candle, ...], tuple[dict[str, object], ...]]:
    expected_keys = zec_monthly_archive_keys()
    if len(archives) != len(expected_keys):
        raise BitgetMacdRealHistoryError(
            f"expected {len(expected_keys)} ZEC monthly archives, got {len(archives)}"
        )

    candles: list[Candle] = []
    receipts: list[dict[str, object]] = []
    for expected, observed in zip(expected_keys, archives):
        if observed.key.identity != expected.identity:
            raise BitgetMacdRealHistoryError(
                f"ZEC archive identity mismatch: expected {expected.identity}, got {observed.key.identity}"
            )
        if not observed.receipt.audit_ok:
            raise BitgetMacdRealHistoryError(
                f"ZEC monthly archive did not pass strict audit: {expected.period}"
            )
        if observed.receipt.archive_sha256 != observed.receipt.expected_sha256:
            raise BitgetMacdRealHistoryError(
                f"ZEC monthly archive checksum mismatch: {expected.period}"
            )
        candles.extend(observed.candles)
        receipts.append(asdict(observed.receipt))

    ordered = tuple(candles)
    validate_contiguous_15m_history(ordered)
    return ordered, tuple(receipts)
