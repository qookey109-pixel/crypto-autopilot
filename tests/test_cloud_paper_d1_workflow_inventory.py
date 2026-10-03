from __future__ import annotations

import unittest
from pathlib import Path

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


    def test_accepts_exact_two_guarded_clients_under_successor_inventory(self) -> None:
        from scripts.validate_cloud_paper_r2_writer_inventory import PREPAID_D1_CLIENT_PATH
        root = Path(__file__).parents[1]
        legacy = "src/crypto_autopilot/paper/cloud_budget_ledger_v0_1.py"
        sources = {path: (root / path).read_text() for path in (legacy, PREPAID_D1_CLIENT_PATH)}
        self.assertEqual(
            validate_d1_source_boundary(sources, legacy, successor_client_path=PREPAID_D1_CLIENT_PATH),
            sorted(sources),
        )

    def test_prepaid_inventory_rejects_missing_each_guard_and_extra_client(self) -> None:
        from scripts.validate_cloud_paper_r2_writer_inventory import (
            PREPAID_D1_CLIENT_PATH,
            PREPAID_D1_QUERY_GUARD_ORDER,
        )
        root = Path(__file__).parents[1]
        legacy = "src/crypto_autopilot/paper/cloud_budget_ledger_v0_1.py"
        original = {path: (root / path).read_text() for path in (legacy, PREPAID_D1_CLIENT_PATH)}
        for marker in PREPAID_D1_QUERY_GUARD_ORDER:
            with self.subTest(marker=marker):
                sources = dict(original)
                sources[PREPAID_D1_CLIENT_PATH] = sources[PREPAID_D1_CLIENT_PATH].replace(marker, "GUARD_REMOVED")
                with self.assertRaisesRegex(RuntimeError, "guards are missing"):
                    validate_d1_source_boundary(sources, legacy, successor_client_path=PREPAID_D1_CLIENT_PATH)
        sources = dict(original)
        sources["scripts/unregistered_d1.py"] = 'endpoint = "/d1/database/test"'
        with self.assertRaisesRegex(RuntimeError, "boundary mismatch"):
            validate_d1_source_boundary(sources, legacy, successor_client_path=PREPAID_D1_CLIENT_PATH)
        with self.assertRaisesRegex(RuntimeError, "versioned implementation"):
            validate_d1_source_boundary(original, legacy, successor_client_path="scripts/unregistered_d1.py")

    @staticmethod
    def _shared_registry_fixture():
        inventory = {
            "workflows": [
                {
                    "workflow": ".github/workflows/paper.yml",
                    "access": "WRITER",
                    "lifecycle": "CURRENT_MANUAL_PAPER",
                },
                {
                    "workflow": ".github/workflows/retired.yml",
                    "access": "WRITER",
                    "lifecycle": "EXPIRED",
                },
            ]
        }
        registry = {
            "repository_writers": [
                {
                    "writer_id": "repo:paper",
                    "workflow": ".github/workflows/paper.yml",
                    "resource": "R2",
                    "registration_state": "DECLARED_SHARED_ADMISSION_NOT_VERIFIED",
                }
            ],
            "external_writer_inventory": {
                "state": "UNCONFIRMED",
                "complete": False,
                "registered_writers": [],
            },
            "production_gate": {
                "account_wide_coverage_proven": False,
                "shared_admission_integrated_for_all_repository_writers": False,
                "d1_provisioned": False,
                "activation_enabled": False,
            },
        }
        return inventory, registry

    def test_shared_registry_lists_current_repository_writer_without_claiming_account_coverage(self) -> None:
        from scripts.validate_cloud_paper_r2_writer_inventory import (
            validate_shared_account_writer_registry,
        )

        inventory, registry = self._shared_registry_fixture()
        self.assertEqual(
            validate_shared_account_writer_registry(inventory, registry),
            [".github/workflows/paper.yml"],
        )

    def test_shared_registry_rejects_new_unregistered_current_writer(self) -> None:
        from scripts.validate_cloud_paper_r2_writer_inventory import (
            validate_shared_account_writer_registry,
        )

        inventory, registry = self._shared_registry_fixture()
        inventory["workflows"].append(
            {
                "workflow": ".github/workflows/new-writer.yml",
                "access": "CONDITIONAL_WRITER",
                "lifecycle": "CURRENT_CONDITIONAL",
            }
        )
        with self.assertRaisesRegex(RuntimeError, "unregistered"):
            validate_shared_account_writer_registry(inventory, registry)

    def test_shared_registry_rejects_activation_with_unknown_external_writers(self) -> None:
        from scripts.validate_cloud_paper_r2_writer_inventory import (
            validate_shared_account_writer_registry,
        )

        inventory, registry = self._shared_registry_fixture()
        registry["production_gate"].update(
            {
                "shared_admission_integrated_for_all_repository_writers": True,
                "d1_provisioned": True,
                "activation_enabled": True,
            }
        )
        registry["repository_writers"][0]["registration_state"] = (
            "SHARED_ADMISSION_VERIFIED"
        )
        with self.assertRaisesRegex(RuntimeError, "production activation"):
            validate_shared_account_writer_registry(inventory, registry)

    def test_shared_registry_requires_receipt_before_external_inventory_is_complete(self) -> None:
        from scripts.validate_cloud_paper_r2_writer_inventory import (
            validate_shared_account_writer_registry,
        )

        inventory, registry = self._shared_registry_fixture()
        registry["external_writer_inventory"].update(
            {"state": "ATTESTED", "complete": True}
        )
        registry["production_gate"]["account_wide_coverage_proven"] = True
        with self.assertRaisesRegex(RuntimeError, "attestation receipt"):
            validate_shared_account_writer_registry(inventory, registry)


class ScopedOwnerAttestationTests(unittest.TestCase):
    _shared_registry_fixture = staticmethod(D1WorkflowInventoryTests._shared_registry_fixture)
    @staticmethod
    def _scoped(registry):
        registry["external_writer_inventory"]["current_external_r2_owner_attestation"] = {
            "state": "ATTESTED_NONE_AT_CHECKPOINT",
            "scope": "CURRENT_EXTERNAL_R2_WRITERS",
            "observed_date": "2026-10-03",
            "receipt": "research/receipts/2026-10-03-cloudflare-owner-billing-checkpoint-v0-1.json",
        }

    def test_scoped_r2_attestation_keeps_account_gate_closed(self):
        from scripts.validate_cloud_paper_r2_writer_inventory import validate_shared_account_writer_registry
        inventory, registry = self._shared_registry_fixture()
        self._scoped(registry)
        self.assertEqual(validate_shared_account_writer_registry(inventory, registry),
                         [".github/workflows/paper.yml"])
        self.assertFalse(registry["production_gate"]["account_wide_coverage_proven"])

    def test_scoped_r2_rejects_changed_scope_date_or_receipt(self):
        from scripts.validate_cloud_paper_r2_writer_inventory import validate_shared_account_writer_registry
        for field, value in (("scope", "ALL_ACCOUNT_WRITERS"), ("observed_date", "2099-01-01"),
                             ("receipt", "README.md"), ("receipt", "../outside.json")):
            with self.subTest(field=field, value=value):
                inventory, registry = self._shared_registry_fixture()
                self._scoped(registry)
                registry["external_writer_inventory"]["current_external_r2_owner_attestation"][field] = value
                with self.assertRaisesRegex(RuntimeError, "attestation"):
                    validate_shared_account_writer_registry(inventory, registry)

    def test_external_complete_allows_repository_admission_still_unverified(self):
        from scripts.validate_cloud_paper_r2_writer_inventory import validate_shared_account_writer_registry
        inventory, registry = self._shared_registry_fixture()
        registry["external_writer_inventory"].update({
            "state": "ATTESTED", "complete": True,
            "attestation_receipt": "research/receipts/2026-10-03-cloudflare-owner-billing-checkpoint-v0-1.json",
        })
        self.assertEqual(validate_shared_account_writer_registry(inventory, registry),
                         [".github/workflows/paper.yml"])
        registry["production_gate"]["account_wide_coverage_proven"] = True
        with self.assertRaisesRegex(RuntimeError, "repository admission"):
            validate_shared_account_writer_registry(inventory, registry)


if __name__ == "__main__":
    unittest.main()
