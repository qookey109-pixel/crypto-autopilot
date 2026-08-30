from __future__ import annotations

import copy
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
    CatalogObject,
    PionexAlternativeAssetError,
    build_catalog,
    canonical_json_bytes,
)
from crypto_autopilot.providers.pionex_alternative_assets_observability import (
    build_analysis,
    build_objects,
    build_safe_projection,
    compare_catalogs,
    load_previous_catalog,
    project_capacity,
    publish_objects,
    require_execution_window,
    validate_catalog,
    validate_observability_config,
)
from crypto_autopilot.storage.r2 import R2ObjectReceipt


ROOT = Path(__file__).resolve().parents[1]
CATALOG_CONFIG = ROOT / "config/pionex_alternative_assets_v0_1.json"
CONFIG = ROOT / "config/pionex_alternative_assets_observability_v0_2.json"
AUTHORITY = (
    ROOT
    / "research/receipts/2026-08-30-pionex-alternative-assets-observability-v0-2-authority.json"
)
WORKFLOW = ROOT / ".github/workflows/pionex-alternative-assets-observability-v0-2.yml"
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
        del content_type, metadata
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
            raise ValueError("test SHA mismatch")
        return payload


class PionexAlternativeAssetsObservabilityV02Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog_bytes = CATALOG_CONFIG.read_bytes()
        self.config_bytes = CONFIG.read_bytes()
        self.catalog_config = json.loads(self.catalog_bytes)
        self.config = json.loads(self.config_bytes)
        self.authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))
        self.catalog = build_catalog(
            ["AAPLX_USDT_PERP", "SPYX_USDT_PERP", "XAU_USDT_PERP"],
            config=self.catalog_config,
            retrieved_at_utc="2026-09-04T02:53:00Z",
        )

    def test_authority_and_supersession_are_hash_bound(self) -> None:
        self.assertEqual(
            self.authority["config_sha256"], hashlib.sha256(self.config_bytes).hexdigest()
        )
        self.assertEqual(
            self.authority["catalog_source_sha256"],
            hashlib.sha256(self.catalog_bytes).hexdigest(),
        )
        validate_observability_config(
            self.config, catalog_config_bytes=self.catalog_bytes
        )
        self.assertTrue(
            self.config["supersession"]["superseded_before_first_provider_request"]
        )
        self.assertFalse(
            self.config["supersession"]["concurrent_v0_1_schedule_authorized"]
        )

    def test_execution_window_is_exact_and_bounded(self) -> None:
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

    def test_catalog_validation_is_structural_and_fail_closed(self) -> None:
        result = validate_catalog(self.catalog, catalog_config=self.catalog_config)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["matched_market_count"], 3)
        self.assertFalse(result["catalog_absence_is_delisting_proof"])

        duplicate = copy.deepcopy(self.catalog)
        duplicate["markets"].append(copy.deepcopy(duplicate["markets"][0]))
        duplicate["matched_market_count"] += 1
        with self.assertRaisesRegex(PionexAlternativeAssetError, "duplicate"):
            validate_catalog(duplicate, catalog_config=self.catalog_config)

        unsafe = copy.deepcopy(self.catalog)
        unsafe["authority"]["training_authorized"] = True
        with self.assertRaisesRegex(PionexAlternativeAssetError, "downstream authority"):
            validate_catalog(unsafe, catalog_config=self.catalog_config)

    def test_catalog_diff_baseline_and_collapse_are_explicit(self) -> None:
        baseline = compare_catalogs(self.catalog, None, ratio_review_threshold=0.5)
        self.assertEqual(baseline["status"], "BASELINE_CREATED")
        self.assertIn("NO_DELISTING_CONCLUSION", baseline["removal_interpretation"])

        current = build_catalog(
            ["AAPLX_USDT_PERP"],
            config=self.catalog_config,
            retrieved_at_utc="2026-09-06T03:53:00Z",
        )
        diff = compare_catalogs(current, self.catalog, ratio_review_threshold=0.5)
        self.assertEqual(diff["status"], "REVIEW_REQUIRED")
        self.assertEqual(diff["removed_symbols"], ["SPYX_USDT_PERP", "XAU_USDT_PERP"])
        self.assertIn(
            "MATCHED_MARKET_COUNT_COLLAPSED_BELOW_FROZEN_RATIO",
            diff["review_reasons"],
        )
        self.assertIn("NOT_PROOF_OF_DELISTING", diff["removal_interpretation"])

    def test_four_year_capacity_is_estimate_only(self) -> None:
        capacity = project_capacity(125, config=self.config)
        self.assertEqual(capacity["total_rows"], 23_010_750)
        self.assertEqual(capacity["rows_by_interval"]["15M"], 17_532_000)
        self.assertEqual(capacity["scenarios"]["reference"]["canonical_gb"], 1.472688)
        self.assertEqual(
            capacity["scenarios"]["stress"]["operational_stress_gb"], 3.68172
        )
        self.assertFalse(capacity["historical_materialization_authorized"])
        self.assertEqual(project_capacity(0, config=self.config)["total_rows"], 0)

    def test_safe_projection_contains_summary_but_no_raw_market_list(self) -> None:
        analysis = build_analysis(
            catalog=self.catalog,
            previous_catalog=None,
            catalog_config=self.catalog_config,
            observability_config=self.config,
        )
        projection = build_safe_projection(
            catalog_config=self.catalog_config,
            observability_config=self.config,
            catalog=self.catalog,
            analysis=analysis,
        )
        self.assertEqual(projection["candidate_registry"]["total"], 125)
        self.assertEqual(projection["actual_catalog"]["matched_market_count"], 3)
        self.assertNotIn("markets", projection["actual_catalog"])
        self.assertTrue(all(value is False for value in projection["safety_boundary"].values()))

    def test_publication_is_immutable_sha_verified_and_pointer_is_last(self) -> None:
        analysis = build_analysis(
            catalog=self.catalog,
            previous_catalog=None,
            catalog_config=self.catalog_config,
            observability_config=self.config,
        )
        projection = build_safe_projection(
            catalog_config=self.catalog_config,
            observability_config=self.config,
            catalog=self.catalog,
            analysis=analysis,
        )
        objects = build_objects(
            catalog=self.catalog,
            analysis=analysis,
            safe_projection=projection,
            config=self.config,
            run_id="test-run",
        )
        self.assertEqual(
            [item.role for item in objects],
            ["catalog", "analysis", "safe_projection", "manifest", "latest_pointer"],
        )
        store = FakeStore()
        result = publish_objects(
            store=store,
            objects=objects,
            hard_stop_bytes=8_000_000_000,
            current_bytes=0,
        )
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["latest_pointer_written_last"])
        restored = load_previous_catalog(store, config=self.config)
        self.assertEqual(restored, self.catalog)

        conflict = list(objects)
        conflict[0] = CatalogObject(
            conflict[0].key,
            canonical_json_bytes({"changed": True}),
            conflict[0].content_type,
            conflict[0].immutable,
            conflict[0].role,
        )
        with self.assertRaisesRegex(PionexAlternativeAssetError, "immutable"):
            publish_objects(
                store=store,
                objects=tuple(conflict),
                hard_stop_bytes=8_000_000_000,
                current_bytes=0,
            )

    def test_headroom_gate_blocks_before_writes(self) -> None:
        analysis = build_analysis(
            catalog=self.catalog,
            previous_catalog=None,
            catalog_config=self.catalog_config,
            observability_config=self.config,
        )
        objects = build_objects(
            catalog=self.catalog,
            analysis=analysis,
            safe_projection=build_safe_projection(
                catalog_config=self.catalog_config,
                observability_config=self.config,
                catalog=self.catalog,
                analysis=analysis,
            ),
            config=self.config,
            run_id="blocked",
        )
        store = FakeStore()
        result = publish_objects(
            store=store,
            objects=objects,
            hard_stop_bytes=1,
            current_bytes=0,
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["r2_writes_performed"])
        self.assertEqual(store.objects, {})

    def test_pre_window_script_skips_before_r2_or_provider(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            projection = Path(directory) / "projection.json"
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
                    str(ROOT / "scripts/run_pionex_alternative_assets_observability_v0_2.py"),
                    "--run-id",
                    "pre-window-test",
                    "--observed-at-utc",
                    "2026-09-04T01:59:59Z",
                    "--output",
                    str(output),
                    "--projection-output",
                    str(projection),
                ],
                cwd=ROOT,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "SKIPPED")
            self.assertEqual(report["provider_requests_performed"], 0)
            self.assertFalse(report["r2_access_performed"])
            safe = json.loads(projection.read_text(encoding="utf-8"))
            self.assertIsNone(safe["actual_catalog"])

    def test_only_v0_2_metadata_schedule_remains(self) -> None:
        self.assertFalse(RETIRED_WORKFLOW.exists())
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('cron: "53 2 4 9 *"', text)
        self.assertIn('cron: "53 3 6,13,20,27 9 *"', text)
        self.assertIn("cancel-in-progress: false", text)
        self.assertIn("run_pionex_alternative_assets_observability_v0_2.py", text)
        self.assertNotIn("PIONEX_API_KEY", text)
        self.assertNotIn("kline", text.lower())
        self.assertNotIn("place_order", text.lower())
        self.assertNotIn("/api/v1/trade", text)


if __name__ == "__main__":
    unittest.main()
