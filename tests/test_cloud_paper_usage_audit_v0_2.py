from __future__ import annotations

import json
import unittest
from io import BytesIO
from unittest.mock import MagicMock, patch
from datetime import UTC, datetime, timedelta

from scripts.cloud_paper_usage_audit_v0_2 import (
    AuditError, _NoRedirect, _cloudflare_json, diagnose_usage, readiness,
)

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
START = NOW - timedelta(days=30)


def payload() -> dict:
    return {
        "data": {
            "viewer": {
                "accounts": [{
                    "d1Rows": [
                        {"sum": {"rowsRead": 100, "rowsWritten": 10},
                         "dimensions": {"date": "2026-09-29"}},
                    ],
                    "d1Storage": [
                        {"max": {"databaseSizeBytes": 1024},
                         "dimensions": {"databaseId": "private-db-id", "datetime": "2026-09-29T10:00:00Z"}},
                    ],
                    "r2Operations": [
                        {"sum": {"requests": 5},
                         "dimensions": {"actionType": "GetObject", "datetime": "2026-09-29T10:00:00Z"}},
                    ],
                    "r2Storage": [
                        {"max": {"objectCount": 2, "uploadCount": 0,
                                 "payloadSize": 2048, "metadataSize": 100},
                         "dimensions": {"bucketName": "private-bucket-name",
                                        "datetime": "2026-09-29T10:00:00Z"}},
                    ],
                }]
            }
        }
    }


def diagnose(value: object) -> dict:
    return diagnose_usage(value, observed_at=NOW, start_time=START, end_time=NOW)


class CloudPaperUsageAuditV02Tests(unittest.TestCase):
    def test_all_present_reports_metrics_without_identifiers(self) -> None:
        report = diagnose(payload())
        self.assertEqual(report["status"], "READY_FOR_REVIEW")
        self.assertEqual(report["coverage"]["dataset_group_counts"], {
            "d1Rows": 1, "d1Storage": 1, "r2Operations": 1, "r2Storage": 1,
        })
        self.assertTrue(all(
            state == "PRESENT" for state in report["coverage"]["dataset_states"].values()
        ))
        self.assertEqual(report["activation"], "REMAINS_DISABLED")
        self.assertEqual(report["r2"]["latest_storage"]["payloadSize"], 2048)
        encoded = json.dumps(report)
        self.assertNotIn("private-db-id", encoded)
        self.assertNotIn("private-bucket-name", encoded)

    def test_each_empty_dataset_is_named_and_never_treated_as_zero_usage(self) -> None:
        for name in ("d1Rows", "d1Storage", "r2Operations", "r2Storage"):
            with self.subTest(name=name):
                value = payload()
                value["data"]["viewer"]["accounts"][0][name] = []
                report = diagnose(value)
                self.assertEqual(report["status"], "REVIEW_REQUIRED")
                self.assertEqual(report["reason_code"], "DATASET_COVERAGE_INCOMPLETE")
                self.assertEqual(report["coverage"]["dataset_states"][name], "EMPTY_UNVERIFIED")
                self.assertEqual(report["coverage"]["dataset_group_counts"][name], 0)
                self.assertEqual(report["zero_cost_conclusion"], "UNKNOWN")
                self.assertNotIn("d1", report)
                self.assertNotIn("r2", report)

    def test_missing_and_capped_datasets_are_distinct(self) -> None:
        value = payload()
        del value["data"]["viewer"]["accounts"][0]["d1Storage"]
        value["data"]["viewer"]["accounts"][0]["r2Operations"] = [{}] * 10000
        report = diagnose(value)
        self.assertEqual(report["coverage"]["dataset_states"]["d1Storage"], "MISSING_OR_INVALID")
        self.assertIsNone(report["coverage"]["dataset_group_counts"]["d1Storage"])
        self.assertEqual(report["coverage"]["dataset_states"]["r2Operations"], "LIMIT_REACHED")

    def test_partial_graphql_error_drops_all_response_content(self) -> None:
        value = payload()
        value["errors"] = [{"message": "private-db-id token"}]
        report = diagnose(value)
        self.assertEqual(report["reason_code"], "GRAPHQL_RESPONSE_ERROR")
        self.assertNotIn("private-db-id", json.dumps(report))

    def test_stale_dataset_keeps_activation_disabled(self) -> None:
        value = payload()
        value["data"]["viewer"]["accounts"][0]["r2Storage"][0]["dimensions"]["datetime"] = "2026-09-20T00:00:00Z"
        report = diagnose(value)
        self.assertEqual(report["status"], "REVIEW_REQUIRED")
        self.assertEqual(report["reason_code"], "STALE_DATASET")
        self.assertEqual(report["activation"], "REMAINS_DISABLED")

    def test_cloudflare_request_is_single_and_bounded(self) -> None:
        opener = MagicMock()
        opener.open.return_value = BytesIO(b'{"data": {}}')
        with patch("scripts.cloud_paper_usage_audit_v0_2.urllib.request.build_opener",
                   return_value=opener):
            self.assertEqual(_cloudflare_json(headers={}, body=b"{}"), {"data": {}})
        opener.open.assert_called_once()
        self.assertIsNone(_NoRedirect().redirect_request(None, None, 302, "", {}, "/again"))

        opener.open.return_value = BytesIO(b"12345678901")
        with (
            patch("scripts.cloud_paper_usage_audit_v0_2.urllib.request.build_opener",
                  return_value=opener),
            patch("scripts.cloud_paper_usage_audit_v0_2.MAX_RESPONSE_BYTES", 10),
        ):
            with self.assertRaisesRegex(AuditError, "CLOUDFLARE_RESPONSE_TOO_LARGE"):
                _cloudflare_json(headers={}, body=b"{}")

    def test_readiness_separates_missing_names_and_parity(self) -> None:
        cases = [
            ((False, True, True, True), "MISSING_ACCOUNT_ID_VARIABLE"),
            ((True, False, True, False), "MISSING_ACCOUNT_ID_SECRET"),
            ((True, True, False, True), "MISSING_READ_ONLY_TOKEN_SECRET"),
            ((True, True, True, False), "ACCOUNT_ID_SECRET_VARIABLE_MISMATCH"),
            ((True, True, True, True), "CONFIGURATION_PRESENT"),
        ]
        for flags, expected in cases:
            with self.subTest(expected=expected):
                report = readiness(
                    variable_present=flags[0], secret_present=flags[1],
                    token_present=flags[2], account_ids_match=flags[3],
                )
                self.assertEqual(report["reason_code"], expected)
                self.assertEqual(report["cloudflare_requests_performed"], 0)
                self.assertEqual(report["one_time_authority_consumed"], False)
                self.assertEqual(report["state"], "READY" if expected == "CONFIGURATION_PRESENT" else "BLOCKED")


if __name__ == "__main__":
    unittest.main()
