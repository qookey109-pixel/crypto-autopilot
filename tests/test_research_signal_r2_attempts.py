from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from botocore.awsrequest import AWSResponse
from botocore.httpsession import URLLib3Session

from crypto_autopilot.research.signal_ingest_v0_2 import ResearchSignalIngestError
from crypto_autopilot.research.signal_r2_attempts import SignalR2Attempts
from scripts import run_research_signal_layer_v0_2 as runner


class SignalAttemptTests(unittest.TestCase):
    def test_cli_counts_sdk_sends_on_success_and_after_failed_manifest_write(self):
        def response(request, status, body=b""):
            raw = SimpleNamespace(stream=lambda: iter([body]))
            return AWSResponse(request.url, status, {}, raw)

        for fail_manifest in (False, True):
            with self.subTest(fail_manifest=fail_manifest), tempfile.TemporaryDirectory() as temp:
                calls = []
                def transport(request):
                    calls.append(request.method)
                    if "list-type=2" in request.url:
                        return response(request, 200, (
                            b"<ListBucketResult><KeyCount>0</KeyCount>"
                            b"<IsTruncated>false</IsTruncated></ListBucketResult>"
                        ))
                    if request.method == "GET":
                        return response(request, 404, b"<Error><Code>NoSuchKey</Code></Error>")
                    if fail_manifest and request.url.endswith("/manifest.json"):
                        raise OSError("fixture transport failure")
                    return response(request, 200)

                output = io.StringIO()
                argv = ["research", "--run-id", "github-1-1", "--publish-r2",
                        "--output", str(Path(temp) / "signals.json")]
                env = {"AWS_MAX_ATTEMPTS": "1", "AWS_RETRY_MODE": "standard",
                       "CLOUDFLARE_ACCOUNT_ID": "test", "R2_BUCKET_NAME": "test",
                       "R2_ACCESS_KEY_ID": "test", "R2_SECRET_ACCESS_KEY": "test"}
                with (patch.dict(os.environ, env), patch.object(sys, "argv", argv),
                      patch.object(runner, "collect_sources", return_value=((), ())),
                      patch.object(URLLib3Session, "send", side_effect=transport),
                      redirect_stdout(output)):
                    if fail_manifest:
                        with self.assertRaises(OSError):
                            runner.main()
                    else:
                        self.assertEqual(runner.main(), 0)

                rows = [json.loads(line) for line in output.getvalue().splitlines()]
                receipt = rows[-1]
                self.assertEqual(receipt["admitted_send_attempts"], {
                    "ListObjectsV2": 2, "GetObject": 2, "PutObject": 2 if fail_manifest else 3,
                })
                self.assertEqual(calls, ["GET", "GET", "GET", "PUT", "GET", "PUT"]
                                 + ([] if fail_manifest else ["PUT"]))
                self.assertGreater(receipt["attempted_put_payload_bytes"], 0)
                if not fail_manifest:
                    self.assertEqual(receipt["attempted_put_payload_bytes"], rows[0]["planned_write_bytes"])

    def test_subsequent_send_above_each_limit_is_blocked_before_debit(self):
        for operation, maximum in (("ListObjectsV2", 64), ("GetObject", 2), ("PutObject", 3)):
            with self.subTest(operation=operation):
                meter = SignalR2Attempts(3)
                kwargs = {"event_name": f"before-send.s3.{operation}",
                          "request": SimpleNamespace(headers={"Content-Length": b"1"})}
                for _ in range(maximum):
                    meter.before_send(**kwargs)
                with self.assertRaisesRegex(ResearchSignalIngestError, "ATTEMPT_LIMIT"):
                    meter.before_send(**kwargs)
                self.assertEqual(meter.attempts[operation], maximum)

    def test_payload_budget_counts_decoded_size_and_keeps_blocked_state(self):
        meter = SignalR2Attempts(3)
        put = "before-send.s3.PutObject"
        request = SimpleNamespace(headers={"Content-Length": b"45", "x-amz-decoded-content-length": b"3"})
        meter.before_send(event_name=put, request=request)
        with self.assertRaisesRegex(ResearchSignalIngestError, "BYTES_LIMIT"):
            meter.before_send(event_name=put, request=request)
        with self.assertRaisesRegex(ResearchSignalIngestError, "BYTES_LIMIT"):
            meter.before_send(event_name="before-send.s3.GetObject", request=request)
        self.assertEqual(meter.attempts, {"PutObject": 1, "ListObjectsV2": 0, "GetObject": 0})
        self.assertEqual(meter.put_payload_bytes, 3)

    def test_unsupported_operation_and_unknown_put_length_stop_before_transport(self):
        for op, headers in (("HeadBucket", {}), ("PutObject", {}), ("PutObject", {"Content-Length": b"-1"})):
            with self.subTest(op=op, headers=headers):
                meter = SignalR2Attempts(100)
                with self.assertRaises(ResearchSignalIngestError):
                    meter.before_send(event_name="before-send.s3." + op, request=SimpleNamespace(headers=headers))
                self.assertEqual(sum(meter.attempts.values()), 0)
