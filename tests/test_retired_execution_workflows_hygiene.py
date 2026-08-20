from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

RETIRED = (
    "historical-backfill-pilot.yml",
    "diagnose-v0-2-self-hosted-mac-binance-transport.yml",
    "binance-2025-r2-pilot.yml",
    "binance-vision-live-proof.yml",
    "binance-vision-r2-proof.yml",
    "binance-funding-r2-v0-2-preflight.yml",
    "binance-funding-r2-v0-2-materialize.yml",
    "m1b-m1a-dataset-upload.yml",
    "m1b-r2-roundtrip.yml",
    "binance-2025-coverage-scan.yml",
    "binance-funding-source-proof.yml",
    "binance-funding-coverage.yml",
    "binance-max-coverage-discovery.yml",
    "m1a-acquisition.yml",
    "pionex-binance-equivalence-proof.yml",
    "pionex-binance-equivalence-v0-1-forensics.yml",
    "historical-universe-long-horizon-review.yml",
)

FORBIDDEN_EXECUTION_TOKENS = (
    "${{ secrets.",
    "runs-on: [self-hosted",
    "scripts/run_historical_backfill_pilot.py",
    "scripts/materialize_binance_2025_r2_pilot.py",
    "scripts/prove_binance_vision_source.py",
    "scripts/prove_binance_vision_r2.py",
    "scripts/preflight_binance_funding_r2_v0_2.py",
    "scripts/materialize_binance_funding_r2_v0_2.py",
    "scripts/upload_m1a_dataset_to_r2.py",
    "scripts/r2_roundtrip_proof.py",
    "scripts/scan_binance_2025_coverage.py",
    "scripts/prove_binance_funding_source.py",
    "scripts/discover_binance_funding_coverage.py",
    "scripts/discover_binance_max_coverage.py",
    "scripts/select_pionex_universe.py",
    "scripts/acquire_pionex_sample.py",
    "scripts/prove_pionex_binance_equivalence.py",
    "scripts/forensic_pionex_binance_equivalence_v0_1.py",
    "scripts/review_historical_universe_long_horizon.py",
    "urllib.request.urlopen",
)


class RetiredExecutionWorkflowHygieneTests(unittest.TestCase):
    def test_retired_historical_execution_workflows_are_validation_only(self) -> None:
        for name in RETIRED:
            with self.subTest(workflow=name):
                text = (WORKFLOWS / name).read_text(encoding="utf-8")
                lines = text.splitlines()
                self.assertIn("RETIRED", text)
                self.assertIn("RETIRED_NO_EXECUTION", text)
                self.assertFalse(any(line == "  schedule:" for line in lines))
                self.assertFalse(any(line == "  push:" for line in lines))
                self.assertFalse(any(line.strip() == "workflow_dispatch:" for line in lines))
                for token in FORBIDDEN_EXECUTION_TOKENS:
                    self.assertNotIn(token, text, token)
                for marker in (
                    "provider_requests_performed=0",
                    "r2_writes_performed=false",
                    "holdout_candles_accessed=false",
                    "source_switch_authorized=false",
                    "live_trading_authorized=false",
                ):
                    self.assertIn(marker, text, marker)

    def test_v0_10_current_metadata_schedule_remains_active_and_unique(self) -> None:
        current = (
            WORKFLOWS / "provider-equivalence-v0-10-render-metadata-capture.yml"
        ).read_text(encoding="utf-8")
        old = (WORKFLOWS / "provider-equivalence-v0-2-metadata-capture.yml").read_text(
            encoding="utf-8"
        )
        self.assertTrue(any(line == "  schedule:" for line in current.splitlines()))
        self.assertFalse(any(line == "  schedule:" for line in old.splitlines()))
        for cron in (
            '    - cron: "17,47 * 27-31 8 *"',
            '    - cron: "17,47 * 1-3 9 *"',
            '    - cron: "17,47 0-1 4 9 *"',
        ):
            self.assertIn(cron, current)


if __name__ == "__main__":
    unittest.main()
