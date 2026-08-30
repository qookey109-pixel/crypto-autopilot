from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from crypto_autopilot.providers.pionex_alternative_assets import (
    PionexAlternativeAssetError,
    base_asset_from_pionex_symbol,
    build_catalog,
    build_catalog_objects,
    load_authority_pair,
    publish_catalog_objects,
    require_execution_window,
)
from crypto_autopilot.storage.r2 import R2ObjectReceipt


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/pionex_alternative_assets_v0_1.json"
AUTHORITY = (
    ROOT
    / "research/receipts/2026-08-30-pionex-alternative-assets-v0-1-authority.json"
)
RETIRED_WORKFLOW = ROOT / ".github/workflows/pionex-alternative-assets-catalog-v0-1.yml"


class FakeStore:
    bucket = "test-bucket"

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def get_bytes_if_exists(self, key: str) -> bytes | None:
        return self.objects.get(key)

    def put_bytes(
        self,
        key: str,
        payload: bytes,
        *,
        content_type: str,
        metadata: dict[str, str],
    ) -> R2ObjectReceipt:
        self.objects[key] = payload
        return R2ObjectReceipt(
            bucket=self.bucket,
            key=key,
            bytes=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
            etag="test",
        )

    def get_bytes_verified(self, key: str, *, expected_sha256: str) -> bytes:
        payload = self.objects[key]
        if hashlib.sha256(payload).hexdigest() != expected_sha256:
            raise ValueError("bad test sha")
        return payload


class PionexAlternativeAssetsV01Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config, self.authority, self.config_bytes = load_authority_pair(
            CONFIG, AUTHORITY
        )

    def test_authority_is_hash_bound_and_registry_has_three_classes(self) -> None:
        self.assertEqual(
            self.authority["config_sha256"], hashlib.sha256(self.config_bytes).hexdigest()
        )
        counts = {key: len(value) for key, value in self.config["registry"].items()}
        self.assertEqual(
            counts,
            {
                "us_equity_token": 90,
                "etf_or_fund_token": 31,
                "metal_or_other_asset": 4,
            },
        )
        self.assertEqual(sum(counts.values()), 125)
        self.assertIn("AAPLX", self.config["registry"]["us_equity_token"])
        self.assertIn("SPYX", self.config["registry"]["etf_or_fund_token"])
        self.assertEqual(
            set(self.config["registry"]["metal_or_other_asset"]),
            {"XAU", "XAG", "XPT", "XPD"},
        )

    def test_only_live_registry_intersection_is_selected(self) -> None:
        catalog = build_catalog(
            [
                "BTC_USDT_PERP",
                "AAPLX_USDT_PERP",
                "SPYX_USDT_PERP",
                "XAU_USDT_PERP",
                "UNKNOWNX_USDT_PERP",
                "AAPLX_USDT_PERP",
            ],
            config=self.config,
            retrieved_at_utc="2026-09-04T02:53:00Z",
        )
        self.assertEqual(catalog["matched_market_count"], 3)
        self.assertEqual(
            {item["symbol"] for item in catalog["markets"]},
            {"AAPLX_USDT_PERP", "SPYX_USDT_PERP", "XAU_USDT_PERP"},
        )
        self.assertEqual(
            catalog["matched_counts_by_class"],
            {
                "us_equity_token": 1,
                "etf_or_fund_token": 1,
                "metal_or_other_asset": 1,
            },
        )
        self.assertEqual(
            catalog["unresolved_x_suffix_symbols"][0]["symbol"],
            "UNKNOWNX_USDT_PERP",
        )
        self.assertNotIn("BTC_USDT_PERP", {item["symbol"] for item in catalog["markets"]})

    def test_symbol_parser_and_execution_window_fail_closed(self) -> None:
        self.assertEqual(base_asset_from_pionex_symbol("AAPLX_USDT_PERP"), "AAPLX")
        self.assertIsNone(base_asset_from_pionex_symbol("AAPLXUSDT"))
        with self.assertRaisesRegex(PionexAlternativeAssetError, "V0.10 window"):
            require_execution_window(
                self.config,
                observed_at=datetime(2026, 9, 4, 1, 59, 59, tzinfo=UTC),
            )
        require_execution_window(
            self.config,
            observed_at=datetime(2026, 9, 4, 2, 0, 0, tzinfo=UTC),
        )
        with self.assertRaisesRegex(PionexAlternativeAssetError, "expired"):
            require_execution_window(
                self.config,
                observed_at=datetime(2026, 10, 1, 0, 0, 0, tzinfo=UTC),
            )

    def test_catalog_publication_is_round_trip_verified_and_pointer_is_last(self) -> None:
        catalog = build_catalog(
            ["AAPLX_USDT_PERP", "SPYX_USDT_PERP", "XAU_USDT_PERP"],
            config=self.config,
            retrieved_at_utc="2026-09-04T02:53:00Z",
        )
        objects = build_catalog_objects(
            config=self.config, catalog=catalog, run_id="test-run"
        )
        self.assertEqual([item.role for item in objects], ["catalog", "manifest", "latest_pointer"])
        store = FakeStore()
        result = publish_catalog_objects(
            store=store,
            objects=objects,
            hard_stop_bytes=8_000_000_000,
            current_bytes=0,
        )
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["latest_pointer_written_last"])
        self.assertTrue(result["r2_writes_performed"])
        result_again = publish_catalog_objects(
            store=store,
            objects=objects,
            hard_stop_bytes=8_000_000_000,
            current_bytes=sum(len(value) for value in store.objects.values()),
        )
        self.assertEqual(
            [item["action"] for item in result_again["objects"]],
            ["VERIFY_EXISTING", "VERIFY_EXISTING", "UPLOAD"],
        )

    def test_v0_1_schedule_is_retired_before_first_execution(self) -> None:
        self.assertFalse(RETIRED_WORKFLOW.exists())

    def test_pre_window_script_skips_before_r2_or_provider(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT / "src")
            for name in (
                "CLOUDFLARE_ACCOUNT_ID",
                "R2_BUCKET_NAME",
                "R2_ACCESS_KEY_ID",
                "R2_SECRET_ACCESS_KEY",
            ):
                env.pop(name, None)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/run_pionex_alternative_assets_catalog.py"),
                    "--config",
                    str(CONFIG),
                    "--authority",
                    str(AUTHORITY),
                    "--run-id",
                    "pre-window-test",
                    "--observed-at-utc",
                    "2026-09-04T01:59:59Z",
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                report["stage"], "PIONEX_ALTERNATIVE_ASSETS_CATALOG_NOT_BEFORE_GUARD"
            )
            self.assertEqual(report["provider_requests_performed"], 0)
            self.assertFalse(report["r2_access_performed"])

    def test_config_json_is_stable_and_all_authority_gates_are_explicit(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertFalse(payload["next_stage"]["provider_splicing_allowed"])
        self.assertFalse(payload["next_stage"]["binance_relabel_as_pionex_allowed"])
        self.assertFalse(payload["authority"]["replacement_holdout_access_authorized"])
        self.assertFalse(payload["authority"]["historical_materialization_authorized"])
        self.assertFalse(payload["authority"]["live_trading_authorized"])


if __name__ == "__main__":
    unittest.main()
