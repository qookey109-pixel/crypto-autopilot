from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from crypto_autopilot.historical import INTERVAL_MS
from crypto_autopilot.history.pionex_trailing_coverage_v0_2 import (
    TRAILING_HISTORY_COVERAGE_PREFIX,
    collect_partition_v0_2_with_trailing_coverage,
)
from crypto_autopilot.history.pionex_validation_materialization_v0_1 import (
    ValidationMaterializationRejected,
    _last_aligned_candle_before,
    stamp,
)
from crypto_autopilot.history.pionex_validation_materialization_v0_2 import (
    ZERO_HISTORY_COVERAGE_STATUS,
)
from crypto_autopilot.models import Candle


ROOT = Path(__file__).resolve().parents[1]
BASE_CONFIG = ROOT / "config/pionex_validation_dataset_v0_1.json"
BASE_SHA256 = "83972be4bd6bd04d264a1f136283c5b95cb5e200c86cf22be4f02664d0035cbc"
CLOCK_MS = stamp("2026-09-16T00:00:00Z")


def load_config() -> dict:
    payload = BASE_CONFIG.read_bytes()
    if hashlib.sha256(payload).hexdigest() != BASE_SHA256:
        raise AssertionError("frozen V0.1 config changed")
    return json.loads(payload)


def candle(time_ms: int) -> Candle:
    return Candle(
        time_ms=time_ms,
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.5,
        volume=10.0,
    )


class FiniteClient:
    def __init__(self, candles: list[Candle]) -> None:
        self.candles = sorted(candles, key=lambda row: row.time_ms)
        self.calls: list[int] = []

    def get_klines(self, symbol, interval, *, limit=500, end_time_ms=None):
        cursor = int(end_time_ms)
        self.calls.append(cursor)
        available = [row for row in self.candles if row.time_ms <= cursor]
        return available[-limit:]


class EmptyClient:
    def __init__(self) -> None:
        self.calls = 0

    def get_klines(self, symbol, interval, *, limit=500, end_time_ms=None):
        self.calls += 1
        return []


class FailingClient:
    def get_klines(self, symbol, interval, *, limit=500, end_time_ms=None):
        raise OSError("synthetic provider failure")


class ProtectedRangeClient:
    def __init__(self, cutoff: int) -> None:
        self.cutoff = cutoff

    def get_klines(self, symbol, interval, *, limit=500, end_time_ms=None):
        return [candle(self.cutoff)]


class LaterEndpointGapClient:
    """First page is exact; the second clean page skips its requested cursor."""

    def __init__(self, frozen_cursor: int, step: int) -> None:
        self.frozen_cursor = frozen_cursor
        self.step = step
        self.calls = 0

    def get_klines(self, symbol, interval, *, limit=500, end_time_ms=None):
        self.calls += 1
        cursor = int(end_time_ms)
        if self.calls == 1:
            return [candle(self.frozen_cursor - self.step * index) for index in reversed(range(500))]
        return [candle(cursor - self.step * 2), candle(cursor - self.step)]


class PionexTrailingCoverageV02Tests(unittest.TestCase):
    def test_frozen_v01_config_bytes_remain_unchanged(self) -> None:
        self.assertEqual(hashlib.sha256(BASE_CONFIG.read_bytes()).hexdigest(), BASE_SHA256)

    def test_clean_latest_page_before_cutoff_is_explicit_partial_coverage(self) -> None:
        config = load_config()
        interval = "60M"
        step = INTERVAL_MS[interval]
        cutoff = stamp(config["cutoff_exclusive_utc"])
        frozen_cursor = _last_aligned_candle_before(cutoff, interval)
        provider_latest = frozen_cursor - 24 * step
        rows = [candle(provider_latest - step * index) for index in reversed(range(510))]
        client = FiniteClient(rows)
        progress = {"requests": 0, "protected_range_violation": 0}

        result = collect_partition_v0_2_with_trailing_coverage(
            config,
            client,
            symbol="KORUX_USDT_PERP",
            interval=interval,
            progress=progress,
            clock=lambda: CLOCK_MS,
        )

        self.assertEqual(len(result.candles), 510)
        self.assertEqual(result.candles[-1].time_ms, provider_latest)
        self.assertLess(result.candles[-1].time_ms, frozen_cursor)
        self.assertEqual(
            result.coverage_status,
            f"{TRAILING_HISTORY_COVERAGE_PREFIX}__PROVIDER_EARLIEST_REACHED",
        )
        self.assertEqual(result.requests, 3)
        self.assertEqual(progress["requests"], 3)
        self.assertEqual(progress["protected_range_violation"], 0)
        self.assertFalse(result.receipt_fields()["complete_provider_history_claimed"])

    def test_exact_cutoff_page_keeps_existing_v01_coverage_semantics(self) -> None:
        config = load_config()
        interval = "60M"
        step = INTERVAL_MS[interval]
        cutoff = stamp(config["cutoff_exclusive_utc"])
        frozen_cursor = _last_aligned_candle_before(cutoff, interval)
        rows = [candle(frozen_cursor - step * index) for index in reversed(range(10))]
        progress = {"requests": 0, "protected_range_violation": 0}

        result = collect_partition_v0_2_with_trailing_coverage(
            config,
            FiniteClient(rows),
            symbol="BTC_USDT_PERP",
            interval=interval,
            progress=progress,
            clock=lambda: CLOCK_MS,
        )

        self.assertEqual(result.coverage_status, "PROVIDER_EARLIEST_REACHED")
        self.assertEqual(result.candles[-1].time_ms, frozen_cursor)

    def test_empty_first_response_preserves_explicit_zero_history(self) -> None:
        config = load_config()
        client = EmptyClient()
        progress = {"requests": 0, "protected_range_violation": 0}
        result = collect_partition_v0_2_with_trailing_coverage(
            config,
            client,
            symbol="PONS_USDT_PERP",
            interval="15M",
            progress=progress,
            clock=lambda: CLOCK_MS,
        )
        self.assertEqual(result.coverage_status, ZERO_HISTORY_COVERAGE_STATUS)
        self.assertEqual(result.candles, ())
        self.assertEqual(result.requests, 1)
        self.assertEqual(client.calls, 1)

    def test_provider_exception_before_rows_remains_fail_closed(self) -> None:
        config = load_config()
        progress = {"requests": 0, "protected_range_violation": 0}
        with self.assertRaisesRegex(ValidationMaterializationRejected, "provider request failed"):
            collect_partition_v0_2_with_trailing_coverage(
                config,
                FailingClient(),
                symbol="KORUX_USDT_PERP",
                interval="60M",
                progress=progress,
                clock=lambda: CLOCK_MS,
            )
        self.assertEqual(progress["requests"], 1)

    def test_first_page_internal_gap_is_not_reclassified_as_trailing_absence(self) -> None:
        config = load_config()
        interval = "60M"
        step = INTERVAL_MS[interval]
        cutoff = stamp(config["cutoff_exclusive_utc"])
        frozen_cursor = _last_aligned_candle_before(cutoff, interval)
        provider_latest = frozen_cursor - 12 * step
        rows = [candle(provider_latest - step * index) for index in reversed(range(12))]
        del rows[5]
        progress = {"requests": 0, "protected_range_violation": 0}
        with self.assertRaisesRegex(ValidationMaterializationRejected, "first page before cutoff"):
            collect_partition_v0_2_with_trailing_coverage(
                config,
                FiniteClient(rows),
                symbol="KORUX_USDT_PERP",
                interval=interval,
                progress=progress,
                clock=lambda: CLOCK_MS,
            )

    def test_later_page_endpoint_gap_still_fails_closed(self) -> None:
        config = load_config()
        interval = "60M"
        step = INTERVAL_MS[interval]
        cutoff = stamp(config["cutoff_exclusive_utc"])
        frozen_cursor = _last_aligned_candle_before(cutoff, interval)
        progress = {"requests": 0, "protected_range_violation": 0}
        with self.assertRaisesRegex(ValidationMaterializationRejected, "does not end at requested cursor"):
            collect_partition_v0_2_with_trailing_coverage(
                config,
                LaterEndpointGapClient(frozen_cursor, step),
                symbol="KORUX_USDT_PERP",
                interval=interval,
                progress=progress,
                clock=lambda: CLOCK_MS,
            )
        self.assertEqual(progress["requests"], 2)

    def test_protected_cutoff_row_still_fails_closed(self) -> None:
        config = load_config()
        cutoff = stamp(config["cutoff_exclusive_utc"])
        progress = {"requests": 0, "protected_range_violation": 0}
        with self.assertRaisesRegex(ValidationMaterializationRejected, "protected cutoff"):
            collect_partition_v0_2_with_trailing_coverage(
                config,
                ProtectedRangeClient(cutoff),
                symbol="KORUX_USDT_PERP",
                interval="60M",
                progress=progress,
                clock=lambda: CLOCK_MS,
            )
        self.assertEqual(progress["protected_range_violation"], 1)


if __name__ == "__main__":
    unittest.main()
