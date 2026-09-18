from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from crypto_autopilot.paper.artifact_export_v0_1 import (
    PaperRunPackageArtifactPolicy,
    artifact_export_policy_from_config,
    export_paper_loop_run_package_artifact,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "paper_run_package_artifact_export_v0_1.json"


class PaperRunPackageArtifactExportV01Tests(unittest.TestCase):
    def test_export_writes_canonical_secondary_evidence(self) -> None:
        package = {
            "schema": "qookey-paper-loop-run-package-report-v0.1",
            "package_id": "paper-loop-run-package-v0-1-fixture",
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "artifact"
            with patch(
                "crypto_autopilot.paper.artifact_export_v0_1.verify_paper_loop_run_package",
                return_value="paper-loop-run-package-v0-1-fixture",
            ):
                receipt = export_paper_loop_run_package_artifact(
                    package=package,
                    output_dir=output,
                )

            self.assertEqual(receipt["state"], "ARTIFACT_EXPORT_READY")
            self.assertFalse(receipt["authority"]["artifact_is_execution_authority"])
            self.assertFalse(receipt["authority"]["real_money_order_authorized"])
            self.assertFalse(receipt["authority"]["live_real_trading_authorized"])
            self.assertTrue((output / "package.json").is_file())
            self.assertTrue((output / "manifest.json").is_file())
            self.assertTrue((output / "SHA256SUMS").is_file())
            self.assertTrue((output / "export-receipt.json").is_file())

            package_bytes = (output / "package.json").read_bytes()
            self.assertTrue(package_bytes.endswith(b"\n"))
            rebuilt = json.loads(package_bytes)
            self.assertEqual(rebuilt, package)

            manifest = json.loads(
                (output / "manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                manifest["schema"],
                "qookey-paper-run-package-artifact-manifest-v0.1",
            )
            self.assertEqual(manifest["package_id"], package["package_id"])
            self.assertFalse(
                manifest["authority"]["artifact_is_execution_authority"]
            )

    def test_package_id_mismatch_fails_closed(self) -> None:
        package = {
            "schema": "qookey-paper-loop-run-package-report-v0.1",
            "package_id": "different",
        }
        with tempfile.TemporaryDirectory() as directory, patch(
            "crypto_autopilot.paper.artifact_export_v0_1.verify_paper_loop_run_package",
            return_value="verified",
        ):
            with self.assertRaises(ValueError):
                export_paper_loop_run_package_artifact(
                    package=package,
                    output_dir=Path(directory),
                )

    def test_invalid_real_package_is_rejected_by_existing_verifier(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                export_paper_loop_run_package_artifact(
                    package={"schema": "wrong"},
                    output_dir=Path(directory),
                )

    def test_policy_config_preserves_secondary_only_authority(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            artifact_export_policy_from_config(payload),
            PaperRunPackageArtifactPolicy(),
        )

        bad = json.loads(CONFIG.read_text(encoding="utf-8"))
        bad["policy"]["artifact_is_execution_authority"] = True
        with self.assertRaises(ValueError):
            artifact_export_policy_from_config(bad)

        bad_real = json.loads(CONFIG.read_text(encoding="utf-8"))
        bad_real["policy"]["real_money_order_authorized"] = True
        with self.assertRaises(ValueError):
            artifact_export_policy_from_config(bad_real)


if __name__ == "__main__":
    unittest.main()
