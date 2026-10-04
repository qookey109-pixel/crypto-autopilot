from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime

from scripts.cloud_paper_billing_metadata_diagnostic_v0_4 import diagnose_payload


NOW = datetime(2026, 10, 4, 7, 17, tzinfo=UTC)


def response(*, page=1, per_page=100, success=True, result=None):
    return {
        "success": success,
        "errors": [],
        "result": [] if result is None else result,
        "result_info": {"page": page, "per_page": per_page},
    }


class BillingMetadataDiagnosticV04Tests(unittest.TestCase):
    def test_matching_metadata_is_value_free_and_not_billing_readiness(self):
        report = diagnose_payload(response(result=[{"amount": 123, "id": "private"}]), observed_at=NOW)
        self.assertEqual(report["status"], "DIAGNOSTIC_COMPLETE")
        self.assertEqual(report["reason_code"], "REQUEST_METADATA_MATCHED")
        self.assertTrue(report["pagination_fields"]["page"]["matches_requested"])
        self.assertTrue(report["pagination_fields"]["per_page"]["matches_requested"])
        self.assertEqual(report["billing_readiness"], "UNKNOWN")
        self.assertEqual(report["zero_cost_conclusion"], "UNKNOWN")
        self.assertEqual(report["cloudflare_http_requests_performed"], 0)
        encoded = json.dumps(report)
        self.assertNotIn("private", encoded)
        self.assertNotIn("123", encoded)
        self.assertNotIn('"amount"', encoded)

    def test_reports_only_names_for_mismatched_fields(self):
        report = diagnose_payload(response(page=9, per_page=500), observed_at=NOW)
        self.assertEqual(report["reason_code"], "PAGINATION_METADATA_MISMATCH")
        self.assertEqual(report["mismatched_fields"], ["page", "per_page"])
        self.assertNotIn('"9"', json.dumps(report))
        self.assertNotIn('"500"', json.dumps(report))

    def test_missing_and_wrong_type_fields_are_classified_without_values(self):
        payload = response(page="private-value")
        del payload["result_info"]["per_page"]
        report = diagnose_payload(payload, observed_at=NOW)
        self.assertEqual(report["reason_code"], "PAGINATION_METADATA_INVALID")
        self.assertEqual(report["invalid_fields"], ["page", "per_page"])
        self.assertEqual(report["pagination_fields"]["page"]["json_type"], "string")
        self.assertFalse(report["pagination_fields"]["per_page"]["present"])
        self.assertNotIn("private-value", json.dumps(report))

    def test_boolean_is_not_accepted_as_integer(self):
        report = diagnose_payload(response(page=True), observed_at=NOW)
        self.assertEqual(report["reason_code"], "PAGINATION_METADATA_INVALID")
        self.assertEqual(report["pagination_fields"]["page"]["json_type"], "boolean")
        self.assertFalse(report["pagination_fields"]["page"]["nonnegative_integer"])

    def test_response_errors_are_not_copied_to_report(self):
        payload = response(success=False)
        payload["errors"] = [{"message": "private provider body"}]
        report = diagnose_payload(payload, observed_at=NOW)
        self.assertEqual(report["reason_code"], "SUCCESS_FLAG_NOT_TRUE")
        self.assertNotIn("private provider body", json.dumps(report))

    def test_invalid_response_shapes_fail_closed(self):
        cases = [
            ([], "RESPONSE_NOT_OBJECT"),
            ({"success": True, "errors": [], "result": None, "result_info": {}},
             "RESULT_NOT_ARRAY"),
            ({"success": True, "errors": [], "result": [], "result_info": []},
             "RESULT_INFO_NOT_OBJECT"),
        ]
        for payload, reason in cases:
            with self.subTest(reason=reason):
                self.assertEqual(
                    diagnose_payload(payload, observed_at=NOW)["reason_code"], reason
                )


if __name__ == "__main__":
    unittest.main()
