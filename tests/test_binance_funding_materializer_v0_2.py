from __future__ import annotations

import json
import unittest
from pathlib import Path

from crypto_autopilot.binance_funding_materialization_plan_v0_2 import build_v0_2_scope
from crypto_autopilot.binance_funding_materializer_v0_2 import (
    AUTHORITY_PATH,
    CONFIG_PATH,
    PREFLIGHT_AUTHORITY_PATH,
    EXPECTED_CHECKSUM_SET_SHA256,
    EXPECTED_SCOPE_SHA256,
    BinanceFundingMaterializerV02Error,
    FundingChecksumRecord,
    checksum_set_sha256,
    run_metadata_keys,
    source_keys_from_scope,
    validate_execution_marker,
    validate_preflight_authority,
    validate_runtime_authority,
)


ROOT = Path(__file__).resolve().parents[1]
COVERAGE = ROOT / "research/receipts/2026-08-18-binance-funding-coverage.json"


def load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"expected JSON object: {path}")
    return payload


def valid_marker() -> dict[str, object]:
    return {
        "status": "EXECUTE_AUTHORIZED_FUNDING_R2_MATERIALIZATION_V0_2",
        "execute": True,
        "provider": "binance_usdm",
        "dataset": "fundingRate",
        "canonical_scope_sha256": EXPECTED_SCOPE_SHA256,
        "source_checksum_set_sha256": EXPECTED_CHECKSUM_SET_SHA256,
        "materialization_authority": AUTHORITY_PATH,
        "preflight_authority": PREFLIGHT_AUTHORITY_PATH,
        "source_switch_authorized": False,
        "provider_splicing_authorized": False,
        "interpolation_authorized": False,
        "pionex_native_relabel_authorized": False,
        "historical_universe_membership_authorized": False,
        "backtest_admission_authorized": False,
        "trade_plan_authorized": False,
        "real_money_order_authorized": False,
        "live_trading_authorized": False,
    }


class BinanceFundingMaterializerV02Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load(ROOT / CONFIG_PATH)
        self.authority = load(ROOT / AUTHORITY_PATH)
        self.preflight = load(ROOT / PREFLIGHT_AUTHORITY_PATH)
        self.coverage = load(COVERAGE)
        self.scope = build_v0_2_scope(self.coverage)

    def test_real_runtime_authority_binds_exact_v0_2_scope(self) -> None:
        scope_sha, checksum_sha = validate_runtime_authority(
            config=self.config,
            authority=self.authority,
            scope=self.scope,
        )
        self.assertEqual(scope_sha, EXPECTED_SCOPE_SHA256)
        self.assertEqual(checksum_sha, EXPECTED_CHECKSUM_SET_SHA256)
        self.assertEqual(self.scope.symbol_months, 1003)
        self.assertEqual(self.scope.canonical_objects, 94)

    def test_real_preflight_authority_is_execution_prerequisite(self) -> None:
        validate_preflight_authority(self.preflight)
        changed = json.loads(json.dumps(self.preflight))
        changed["execution_boundary"]["actual_write_execution_must_repeat_full_preflight"] = False
        with self.assertRaises(BinanceFundingMaterializerV02Error):
            validate_preflight_authority(changed)

    def test_source_keys_are_exact_and_defer_hype_2026(self) -> None:
        keys = source_keys_from_scope(self.scope)
        self.assertEqual(len(keys), 1003)
        self.assertEqual(len({key.identity for key in keys}), 1003)
        self.assertFalse(
            any(key.symbol == "HYPEUSDT" and key.period.startswith("2026-") for key in keys)
        )
        self.assertTrue(any(key.identity == ("HYPEUSDT", "2025-05") for key in keys))
        self.assertTrue(any(key.identity == ("HYPEUSDT", "2025-12") for key in keys))

    def test_checksum_set_is_order_independent_and_identity_unique(self) -> None:
        rows = (
            FundingChecksumRecord("BTCUSDT", "2025-02", "b" * 64),
            FundingChecksumRecord("BTCUSDT", "2025-01", "a" * 64),
        )
        reversed_rows = tuple(reversed(rows))
        self.assertEqual(checksum_set_sha256(rows), checksum_set_sha256(reversed_rows))
        with self.assertRaises(BinanceFundingMaterializerV02Error):
            checksum_set_sha256((rows[0], rows[0]))

    def test_run_metadata_is_exactly_four_provider_separated_objects(self) -> None:
        keys = run_metadata_keys("123456")
        self.assertEqual(len(keys.all), 4)
        self.assertEqual(len(set(keys.all)), 4)
        self.assertTrue(all("binance_usdm" in key for key in keys.all))
        self.assertTrue(all("pionex" not in key.lower() for key in keys.all))
        self.assertTrue(all("materialization-v0-2" in key for key in keys.all))

    def test_execution_marker_is_exact_and_trade_safe(self) -> None:
        marker = valid_marker()
        validate_execution_marker(marker)
        for field in ("source_switch_authorized", "provider_splicing_authorized", "live_trading_authorized"):
            with self.subTest(field=field):
                changed = dict(marker)
                changed[field] = True
                with self.assertRaises(BinanceFundingMaterializerV02Error):
                    validate_execution_marker(changed)
        changed = dict(marker)
        changed["canonical_scope_sha256"] = "0" * 64
        with self.assertRaises(BinanceFundingMaterializerV02Error):
            validate_execution_marker(changed)

    def test_writer_rejects_old_scope_reactivation(self) -> None:
        changed = json.loads(json.dumps(self.authority))
        changed["explicitly_not_authorized"]["v0_1_scope_reactivation_authorized"] = True
        with self.assertRaises(BinanceFundingMaterializerV02Error):
            validate_runtime_authority(config=self.config, authority=changed, scope=self.scope)

    def test_writer_rejects_hype_2026_materialization(self) -> None:
        changed = json.loads(json.dumps(self.authority))
        changed["deferred_scope"]["materialization_authorized"] = True
        with self.assertRaises(BinanceFundingMaterializerV02Error):
            validate_runtime_authority(config=self.config, authority=changed, scope=self.scope)

    def test_writer_rejects_source_switch_or_live_trading(self) -> None:
        for field in ("source_switch_authorized", "live_trading_authorized"):
            with self.subTest(field=field):
                changed = json.loads(json.dumps(self.authority))
                changed["explicitly_not_authorized"][field] = True
                with self.assertRaises(BinanceFundingMaterializerV02Error):
                    validate_runtime_authority(config=self.config, authority=changed, scope=self.scope)


if __name__ == "__main__":
    unittest.main()
