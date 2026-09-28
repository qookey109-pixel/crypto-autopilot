from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from scripts.cloud_paper_usage_audit_v0_1 import AuditError, summarize_usage

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)


def payload(*, stale=False):
    stamp = "2026-09-29T10:00:00Z" if not stale else "2026-09-20T00:00:00Z"
    return {
        "data": {
            "viewer": {
                "accounts": [{
                    "d1Rows": [
                        {"sum": {"rowsRead": 100, "rowsWritten": 10},
                         "dimensions": {"date": "2026-09-29"}}
                    ],
                    "d1Storage": [
                        {"max": {"databaseSizeBytes": 1024},
                         "dimensions": {"databaseId": "db-1", "datetime": stamp}}
                    ],
                    "r2Operations": [
                        {"sum": {"requests": 5},
                         "dimensions": {"actionType": "GetObject", "datetime": stamp}}
                    ],
                    "r2Storage": [
                        {"max": {"objectCount": 2, "uploadCount": 0,
                                 "payloadSize": 2048, "metadataSize": 100},
                         "dimensions": {"bucketName": "bucket-1", "datetime": stamp}}
                    ],
                }]
            }
        }
    }


class CloudPaperUsageAuditTests(unittest.TestCase):
    def test_summarizes_account_wide_metrics_without_identifiers(self):
        report = summarize_usage(
            payload(), observed_at=NOW, start_time=NOW - timedelta(days=30),
            end_time=NOW,
        )
        self.assertEqual(report["status"], "READY_FOR_REVIEW")
        self.assertEqual(report["d1"]["latest_storage_total_bytes"], 1024)
        self.assertEqual(report["r2"]["latest_storage"]["payloadSize"], 2048)
        self.assertEqual(report["r2"]["operations_by_action"], {"GetObject": 5})
        encoded = str(report)
        self.assertNotIn("db-1", encoded)
        self.assertNotIn("bucket-1", encoded)
        self.assertEqual(report["zero_cost_conclusion"], "UNKNOWN_PLAN_AND_BILLING_NOT_QUERIED")

    def test_stale_usage_is_review_required(self):
        report = summarize_usage(
            payload(stale=True), observed_at=NOW,
            start_time=NOW - timedelta(days=30), end_time=NOW,
        )
        self.assertEqual(report["status"], "REVIEW_REQUIRED")

    def test_partial_graphql_errors_fail_closed(self):
        value = payload()
        value["errors"] = [{"message": "partial"}]
        with self.assertRaisesRegex(AuditError, "GRAPHQL_RESPONSE_ERROR"):
            summarize_usage(value, observed_at=NOW,
                            start_time=NOW - timedelta(days=30), end_time=NOW)

    def test_empty_dataset_does_not_become_zero_usage(self):
        value = payload()
        value["data"]["viewer"]["accounts"][0]["r2Operations"] = []
        with self.assertRaisesRegex(AuditError, "DATASET_EMPTY_UNVERIFIED"):
            summarize_usage(value, observed_at=NOW,
                            start_time=NOW - timedelta(days=30), end_time=NOW)

    def test_saturated_dataset_fails_closed(self):
        value = payload()
        value["data"]["viewer"]["accounts"][0]["d1Rows"] = [{}] * 10000
        with self.assertRaisesRegex(AuditError, "DATASET_LIMIT_REACHED"):
            summarize_usage(value, observed_at=NOW,
                            start_time=NOW - timedelta(days=30), end_time=NOW)


if __name__ == "__main__":
    unittest.main()
