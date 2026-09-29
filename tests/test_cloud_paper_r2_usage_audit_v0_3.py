from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from scripts.cloud_paper_r2_usage_audit_v0_3 import (
    diagnose_r2,
    readiness,
)

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
START = NOW - timedelta(days=30)


def payload():
    return {
        "data": {
            "viewer": {
                "accounts": [{
                    "r2Operations": [
                        {"sum": {"requests": 4}, "dimensions": {"actionType": "GetObject"}},
                        {"sum": {"requests": 3}, "dimensions": {"actionType": "PutObject"}},
                    ],
                    "r2Storage": [
                        {
                            "max": {
                                "objectCount": 2,
                                "uploadCount": 0,
                                "payloadSize": 900,
                                "metadataSize": 40,
                            },
                            "dimensions": {
                                "bucketName": "private-bucket-name",
                                "datetime": "2026-09-28T10:00:00Z",
                            },
                        },
                        {
                            "max": {
                                "objectCount": 3,
                                "uploadCount": 1,
                                "payloadSize": 1200,
                                "metadataSize": 50,
                            },
                            "dimensions": {
                                "bucketName": "private-bucket-name",
                                "datetime": "2026-09-29T11:00:00Z",
                            },
                        },
                    ],
                }]
            }
        }
    }


class CloudPaperR2UsageAuditV03Tests(unittest.TestCase):
    def test_aggregates_operations_without_time_dimension_and_latest_bucket_snapshot(self):
        result = diagnose_r2(payload(), observed_at=NOW, start_time=START, end_time=NOW)
        self.assertEqual(result["status"], "READY_FOR_REVIEW")
        self.assertEqual(result["r2"]["operations_total_requests"], 7)
        self.assertEqual(result["r2"]["operations_groups"], 2)
        self.assertEqual(result["r2"]["latest_returned_storage"]["returned_bucket_group_count"], 1)
        self.assertEqual(result["r2"]["latest_returned_storage"]["object_count"], 3)
        self.assertEqual(result["r2"]["latest_returned_storage"]["total_bytes"], 1250)
        self.assertEqual(result["zero_cost_conclusion"], "UNKNOWN")
        self.assertEqual(result["budget_activation"], "NOT_AUTHORIZED_BY_THIS_AUDIT")
        self.assertEqual(result["coverage"]["d1_inventory_and_usage"], "UNKNOWN_NOT_QUERIED")
        self.assertEqual(result["coverage"]["cloudflare_api_permission_state"], "NOT_CHECKED")
        encoded = str(result)
        self.assertNotIn("private-bucket-name", encoded)
        self.assertNotIn("GetObject", encoded)
        self.assertNotIn("PutObject", encoded)

    def test_operation_group_cap_fails_closed(self):
        value = payload()
        value["data"]["viewer"]["accounts"][0]["r2Operations"] = [
            {"sum": {"requests": 1}, "dimensions": {"actionType": f"Action{i}"}}
            for i in range(100)
        ]
        result = diagnose_r2(value, observed_at=NOW, start_time=START, end_time=NOW)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["coverage"]["dataset_states"]["r2_operations"], "LIMIT_REACHED")
        self.assertEqual(result["r2"]["operations_total_requests"], None)

    def test_empty_or_missing_dataset_is_not_zero(self):
        value = payload()
        value["data"]["viewer"]["accounts"][0]["r2Operations"] = []
        result = diagnose_r2(value, observed_at=NOW, start_time=START, end_time=NOW)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["coverage"]["dataset_states"]["r2_operations"], "EMPTY_UNVERIFIED")
        self.assertEqual(result["r2"]["operations_total_requests"], None)

    def test_stale_latest_bucket_snapshot_requires_review(self):
        value = payload()
        rows = value["data"]["viewer"]["accounts"][0]["r2Storage"]
        value["data"]["viewer"]["accounts"][0]["r2Storage"] = [rows[0]]
        value["data"]["viewer"]["accounts"][0]["r2Storage"][0]["dimensions"]["datetime"] = "2026-09-20T00:00:00Z"
        result = diagnose_r2(value, observed_at=NOW, start_time=START, end_time=NOW)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason_code"], "R2_STORAGE_STALE")

    def test_disagreeing_duplicate_timestamp_requires_review(self):
        value = payload()
        duplicate = dict(value["data"]["viewer"]["accounts"][0]["r2Storage"][-1])
        duplicate["max"] = {**duplicate["max"], "payloadSize": 8}
        value["data"]["viewer"]["accounts"][0]["r2Storage"].append(duplicate)
        result = diagnose_r2(value, observed_at=NOW, start_time=START, end_time=NOW)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason_code"], "R2_STORAGE_SNAPSHOT_CONFLICT")

    def test_invalid_metric_fails_closed(self):
        value = payload()
        value["data"]["viewer"]["accounts"][0]["r2Operations"][0]["sum"]["requests"] = -1
        result = diagnose_r2(value, observed_at=NOW, start_time=START, end_time=NOW)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason_code"], "R2_REQUEST_COUNT_INVALID")

    def test_readiness_separates_configuration_presence_from_permission(self):
        result = readiness(
            variable_present=True,
            secret_present=True,
            token_present=True,
            account_ids_match=True,
        )
        self.assertEqual(result["state"], "READY")
        self.assertEqual(result["api_permission_state"], "NOT_CHECKED_NO_NETWORK")
        self.assertEqual(result["budget_activation_state"], "NOT_AUTHORIZED_BY_READINESS")

    def test_readiness_reports_missing_variable_and_token_separately(self):
        variable_missing = readiness(
            variable_present=False,
            secret_present=True,
            token_present=True,
            account_ids_match=False,
        )
        token_missing = readiness(
            variable_present=True,
            secret_present=True,
            token_present=False,
            account_ids_match=True,
        )
        self.assertEqual(variable_missing["reason_code"], "MISSING_ACCOUNT_ID_VARIABLE")
        self.assertEqual(token_missing["reason_code"], "MISSING_READ_ONLY_TOKEN_SECRET")


if __name__ == "__main__":
    unittest.main()
