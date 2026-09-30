from __future__ import annotations

import unittest

from scripts.validate_cloud_paper_r2_writer_inventory import (
    contains_d1_access_reference,
    find_d1_rest_source_paths,
    validate_d1_source_boundary,
)


class D1WorkflowInventoryTests(unittest.TestCase):

    def test_accepts_single_guarded_repository_d1_client(self) -> None:
        path = "src/crypto_autopilot/paper/cloud_budget_ledger_v0_1.py"
        source = """class CloudflareD1QueryClient:
    def query(self, sql: str, params: tuple[object, ...]) -> D1QueryResult:
        self._usage_guard.reserve_query()
        if self._shared_rows_guard is None:
            raise BudgetBlocked()
        self._usage_guard.validate_evidence()
        self._shared_rows_guard.reserve_query(
        self._shared_rows_guard.validate_evidence(
        self._usage_guard.validate_evidence()
            result = self._request(sql, params)
    def _request(self, sql: str, params: tuple[object, ...]) -> D1QueryResult:
        return D1QueryResult()
"""
        self.assertEqual(
            validate_d1_source_boundary({path: source}, path),
            [path],
        )

    def test_rejects_missing_post_admission_freshness_recheck(self) -> None:
        path = "src/crypto_autopilot/paper/cloud_budget_ledger_v0_1.py"
        source = """class CloudflareD1QueryClient:
    def query(self, sql: str, params: tuple[object, ...]) -> D1QueryResult:
        self._usage_guard.reserve_query()
        if self._shared_rows_guard is None:
            raise BudgetBlocked()
        self._usage_guard.validate_evidence()
        self._shared_rows_guard.reserve_query(
        self._shared_rows_guard.validate_evidence(
        self._usage_guard.validate_evidence()
            result = self._request(sql, params)
    def _request(self, sql: str, params: tuple[object, ...]) -> D1QueryResult:
        return D1QueryResult()
"""
        with self.assertRaisesRegex(RuntimeError, "guards are missing"):
            validate_d1_source_boundary({path: source}, path)


    def test_ignores_non_d1_cloudflare_account_endpoint(self) -> None:
        path = "scripts/cloud_paper_billing_evidence_v0_1.py"
        source = 'url = "https://api.cloudflare.com/client/v4/accounts/{account_id}/subscriptions"'
        self.assertEqual(find_d1_rest_source_paths({path: source}), set())

    def test_rejects_unlisted_direct_d1_rest_source(self) -> None:
        path = "src/crypto_autopilot/paper/cloud_budget_ledger_v0_1.py"
        source = """class CloudflareD1QueryClient:
    def query(self, sql: str, params: tuple[object, ...]) -> D1QueryResult:
        self._usage_guard.reserve_query()
        if self._shared_rows_guard is None:
            raise BudgetBlocked()
        self._shared_rows_guard.reserve_query(
            result = self._request(sql, params)
    def _request(self, sql: str, params: tuple[object, ...]) -> D1QueryResult:
        return D1QueryResult()
"""
        second_path = "scripts/direct_d1_writer.py"
        with self.assertRaisesRegex(RuntimeError, "source boundary mismatch"):
            validate_d1_source_boundary(
                {
                    path: source,
                    second_path: 'url = "https://api.cloudflare.com/client/v4/accounts/a/d1/database"',
                },
                path,
            )

    def test_rejects_missing_shared_budget_guard(self) -> None:
        path = "src/crypto_autopilot/paper/cloud_budget_ledger_v0_1.py"
        source = """class CloudflareD1QueryClient:
    def query(self, sql: str, params: tuple[object, ...]) -> D1QueryResult:
        result = self._request(sql, params)
    def _request(self, sql: str, params: tuple[object, ...]) -> D1QueryResult:
        return D1QueryResult()
"""
        with self.assertRaisesRegex(RuntimeError, "guards are missing"):
            validate_d1_source_boundary({path: source}, path)


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

    def test_detects_successor_usage_audit_entrypoint(self) -> None:
        self.assertTrue(contains_d1_access_reference(
            "python -m scripts.cloud_paper_usage_audit_v0_2 --output report.json"
        ))

    def test_ignores_successor_zero_network_readiness(self) -> None:
        self.assertFalse(contains_d1_access_reference(
            "python -m scripts.cloud_paper_usage_audit_v0_2 --readiness"
        ))

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
