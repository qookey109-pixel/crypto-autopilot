from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RETIRED_WORKFLOWS = (
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


class AuthorityStatusSyncTests(unittest.TestCase):
    def test_project_status_lists_all_retired_workflows(self) -> None:
        status = (ROOT / "PROJECT_STATUS.md").read_text(encoding="utf-8")
        self.assertIn("17 historical workflows", status)
        for name in RETIRED_WORKFLOWS:
            with self.subTest(workflow=name):
                self.assertIn(f"`{name}`", status)

    def test_project_status_records_reproducibility_hardening(self) -> None:
        status = (ROOT / "PROJECT_STATUS.md").read_text(encoding="utf-8")
        for marker in (
            "requirements/ci-constraints.txt",
            "Python 3.13",
            "immutable 40-character commit SHAs",
            "PR #136",
            "PR #137",
            "PR #140",
            "D1_DATABASE_ID",
            "PR #141",
            "ruff==0.16.0",
            "E4",
            "E7",
            "E9",
            "PR #142",
            "pull_request",
            "PR #143",
            "Python 3.12 and Python 3.13",
            "test (3.12)",
            "test (3.13)",
            "Issue #139",
        ):
            self.assertIn(marker, status, marker)

    def test_security_policy_matches_current_workflow_hardening(self) -> None:
        security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        for marker in (
            "immutable 40-character commit SHAs",
            "persist-credentials: false",
            "requirements/ci-constraints.txt",
            "Python 3.13",
            "Do not assume `main` is protected",
        ):
            self.assertIn(marker, security, marker)

    def test_env_example_contains_only_current_or_intentional_secret_placeholders(self) -> None:
        env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
        for marker in (
            "PIONEX_API_KEY=",
            "PIONEX_API_SECRET=",
            "CLOUDFLARE_ACCOUNT_ID=",
            "R2_BUCKET_NAME=",
            "R2_ACCESS_KEY_ID=",
            "R2_SECRET_ACCESS_KEY=",
            "DIAGNOSTIC_TOKEN=",
            "METADATA_RELAY_TOKEN=",
        ):
            self.assertIn(marker, env_example, marker)
        self.assertNotIn("D1_DATABASE_ID", env_example)
        self.assertNotIn("Future Cloudflare services", env_example)


if __name__ == "__main__":
    unittest.main()
