from __future__ import annotations

import unittest

from scripts.validate_cloud_paper_r2_writer_inventory import (
    contains_d1_access_reference,
)


class D1WorkflowInventoryTests(unittest.TestCase):
    def test_detects_d1_secret_reference(self) -> None:
        self.assertTrue(contains_d1_access_reference("env: ${{ secrets.D1_DATABASE_ID }}"))

    def test_detects_wrangler_d1_command(self) -> None:
        self.assertTrue(contains_d1_access_reference("run: wrangler d1 execute ledger"))

    def test_detects_d1_binding(self) -> None:
        self.assertTrue(contains_d1_access_reference("d1_databases:"))

    def test_detects_cloudflare_d1_api_path(self) -> None:
        self.assertTrue(
            contains_d1_access_reference(
                "https://api.cloudflare.com/client/v4/accounts/example/d1/database"
            )
        )

    def test_detects_d1_analytics_dataset(self) -> None:
        self.assertTrue(
            contains_d1_access_reference("dataset: d1AnalyticsAdaptiveGroups")
        )

    def test_ignores_unrelated_workflow_text_and_hashes(self) -> None:
        self.assertFalse(
            contains_d1_access_reference(
                "commit sha: d1a24b3d8f38a1a0b51b2dc55e3b40a1f46d3db1"
            )
        )
        self.assertFalse(contains_d1_access_reference("database: sqlite"))

    def test_detects_database_id_secret_name(self) -> None:
        self.assertTrue(contains_d1_access_reference("${{ secrets.DATABASE_ID }}"))


if __name__ == "__main__":
    unittest.main()
