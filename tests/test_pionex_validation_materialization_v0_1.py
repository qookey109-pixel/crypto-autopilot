from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from crypto_autopilot.history.pionex_gap_boundary_v0_1 import GapBoundaryKlineClient
from crypto_autopilot.history.pionex_validation_materialization_v0_1 import (
    ValidationMaterializationRejected,
    _last_aligned_candle_before,
    asset_class_for_symbol,
    collect_partition,
    partition_count,
    profile_for_symbol,
    stamp,
    validate_config,
)
from crypto_autopilot.historical import INTERVAL_MS
from crypto_autopilot.models import Candle


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/pionex_validation_dataset_v0_1.json"
CONFIG_SHA256 = "83972be4bd6bd04d264a1f136283c5b95cb5e200c86cf22be4f02664d0035cbc"


def load_config() -> dict:
    payload = CONFIG_PATH.read_bytes()
    actual = hashlib.sha256(payload).hexdigest()
    if actual != CONFIG_SHA256:
        raise AssertionError(
            f"validation config SHA-256 changed: actual={actual} expected={CONFIG_SHA256}"
        )
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
    def __init__(self, candles: list[Candle], *, fail_probe: bool = False) -> None:
        self.candles = sorted(candles, key=lambda item: item.time_ms)
        self.fail_probe = fail_probe
        self.calls = 0

    def get_klines(self, symbol, interval, *, limit=500, end_time_ms=None):
        self.calls += 1
        available = [item for item in self.candles if item.time_ms <= int(end_time_ms)]
        if not available and self.fail_probe:
            raise RuntimeError("synthetic provider boundary")
        return available[-limit:]


class ProtectedRangeClient:
    def __init__(self, cutoff: int) -> None:
        self.cutoff = cutoff

    def get_klines(self, symbol, interval, *, limit=500, end_time_ms=None):
        return [candle(self.cutoff)]


class PionexValidationMaterializationTests(unittest.TestCase):
    def test_config_partitions_and_asset_overlay_are_exact(self) -> None:
        config = load_config()
        validate_config(config)
        self.assertEqual(partition_count(config), 682)
        self.assertEqual(
            {name: len(value["symbols"]) for name, value in config["history_profiles"].items()},
            {"FULL_INTRADAY": 30, "MULTISCALE_RESEARCH": 99, "BREADTH_BACKGROUND": 68},
        )
        self.assertEqual(sum(config["classification_overlay"]["class_counts"].values()), 197)
        self.assertEqual(asset_class_for_symbol(config, "BTC_USDT_PERP"), "crypto")
        self.assertEqual(
            asset_class_for_symbol(config, "AAPLX_USDT_PERP"), "equity_linked_token"
        )
        self.assertEqual(
            asset_class_for_symbol(config, "KORUX_USDT_PERP"), "etf_or_fund_linked_token"
        )
        self.assertEqual(
            asset_class_for_symbol(config, "OPENAI_USDT_PERP"), "company_reference_perpetual"
        )
        self.assertEqual(
            asset_class_for_symbol(config, "WTI_USDT_PERP"), "energy_commodity_reference"
        )
        self.assertEqual(
            asset_class_for_symbol(config, "COPPER_USDT_PERP"), "industrial_metal_reference"
        )
        self.assertEqual(
            asset_class_for_symbol(config, "XAU_USDT_PERP"), "precious_metal_reference"
        )
        self.assertEqual(
            asset_class_for_symbol(config, "XAUT_USDT_PERP"), "tokenized_precious_metal"
        )
        self.assertEqual(profile_for_symbol(config, "WTI_USDT_PERP"), "FULL_INTRADAY")

    def test_finite_provider_history_reaches_earliest_without_splicing(self) -> None:
        config = load_config()
        cutoff = stamp(config["cutoff_exclusive_utc"])
        interval = "60M"
        step = INTERVAL_MS[interval]
        last = _last_aligned_candle_before(cutoff, interval)
        rows = [candle(last - step * index) for index in reversed(range(10))]
        client = FiniteClient(rows)
        progress = {"requests": 0, "protected_range_violation": 0}
        result = collect_partition(
            config,
            client,
            symbol="BTC_USDT_PERP",
            interval=interval,
            progress=progress,
            clock=lambda: stamp("2026-09-16T00:00:00Z"),
        )
        self.assertEqual(result.coverage_status, "PROVIDER_EARLIEST_REACHED")
        self.assertEqual(len(result.candles), 10)
        self.assertEqual(result.candles[-1].time_ms, last)
        self.assertEqual(progress["protected_range_violation"], 0)

    def test_boundary_probe_failure_keeps_only_verified_contiguous_rows(self) -> None:
        config = load_config()
        cutoff = stamp(config["cutoff_exclusive_utc"])
        interval = "60M"
        step = INTERVAL_MS[interval]
        last = _last_aligned_candle_before(cutoff, interval)
        rows = [candle(last - step * index) for index in reversed(range(7))]
        client = FiniteClient(rows, fail_probe=True)
        progress = {"requests": 0, "protected_range_violation": 0}
        result = collect_partition(
            config,
            client,
            symbol="BTC_USDT_PERP",
            interval=interval,
            progress=progress,
            clock=lambda: stamp("2026-09-16T00:00:00Z"),
        )
        self.assertEqual(result.coverage_status, "PARTIAL_PROVIDER_BOUNDARY_PROBE_FAILED")
        self.assertEqual(len(result.candles), 7)
        self.assertEqual(result.provider_error_type, "RuntimeError")
        self.assertFalse(result.receipt_fields()["complete_provider_history_claimed"])

    def test_invalid_ohlc_boundary_keeps_only_newer_verified_suffix(self) -> None:
        config = load_config()
        cutoff = stamp(config["cutoff_exclusive_utc"])
        interval = "60M"
        step = INTERVAL_MS[interval]
        last = _last_aligned_candle_before(cutoff, interval)
        boundary = last - step * 7
        rows = [candle(last - step * index) for index in reversed(range(11))]
        rows = [
            Candle(
                time_ms=item.time_ms,
                open=item.open,
                high=100.0 if item.time_ms == boundary else item.high,
                low=item.low,
                close=item.close,
                volume=item.volume,
            )
            for item in rows
        ]
        client = GapBoundaryKlineClient(FiniteClient(rows))
        progress = {"requests": 0, "protected_range_violation": 0}
        result = collect_partition(
            config,
            client,
            symbol="AAVE_USDT_PERP",
            interval=interval,
            progress=progress,
            clock=lambda: stamp("2026-09-16T00:00:00Z"),
        )
        self.assertEqual(result.coverage_status, "PARTIAL_PROVIDER_BOUNDARY_PROBE_FAILED")
        self.assertEqual(result.provider_error_type, "PionexInvalidCandleBoundary")
        self.assertEqual(len(result.candles), 7)
        self.assertEqual(result.candles[0].time_ms, boundary + step)
        self.assertEqual(result.candles[-1].time_ms, last)
        self.assertFalse(result.receipt_fields()["complete_provider_history_claimed"])

    def test_protected_range_response_fails_closed(self) -> None:
        config = load_config()
        cutoff = stamp(config["cutoff_exclusive_utc"])
        progress = {"requests": 0, "protected_range_violation": 0}
        with self.assertRaisesRegex(ValidationMaterializationRejected, "protected cutoff"):
            collect_partition(
                config,
                ProtectedRangeClient(cutoff),
                symbol="BTC_USDT_PERP",
                interval="60M",
                progress=progress,
                clock=lambda: stamp("2026-09-16T00:00:00Z"),
            )
        self.assertEqual(progress["protected_range_violation"], 1)


if __name__ == "__main__":
    unittest.main()
