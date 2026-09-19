from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from crypto_autopilot.paper.conditional_write_v0_1 import (
    PaperRunConditionalWritePolicy,
    create_paper_run_object_if_absent,
    paper_run_conditional_write_policy_from_config,
)
from crypto_autopilot.paper.run_store_v0_1 import (
    LocalPaperRunStore,
    PaperRunObjectAlreadyExistsError,
    R2PaperRunStore,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "paper_run_conditional_write_v0_1.json"


class FakePreconditionFailed(Exception):
    def __init__(self) -> None:
        super().__init__("precondition failed")
        self.response = {
            "Error": {"Code": "PreconditionFailed"},
            "ResponseMetadata": {"HTTPStatusCode": 412},
        }


class FakeConditionalClient:
    def __init__(self, parent: "FakeR2") -> None:
        self.parent = parent
        self.calls: list[dict[str, object]] = []

    def put_object(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(dict(kwargs))
        key = kwargs.get("Key")
        body = kwargs.get("Body")
        if not isinstance(key, str) or not isinstance(body, bytes):
            raise AssertionError("fake R2 requires string key and bytes body")
        if kwargs.get("IfNoneMatch") != "*":
            raise AssertionError("conditional create must use IfNoneMatch='*'")
        if key in self.parent.objects:
            raise FakePreconditionFailed()
        self.parent.objects[key] = body
        return {"ETag": '"fake-etag"'}


class FakeR2:
    def __init__(self) -> None:
        self.bucket = "paper-test"
        self.objects: dict[str, bytes] = {}
        self.client = FakeConditionalClient(self)

    def get_bytes_if_exists(self, key: str) -> bytes | None:
        return self.objects.get(key)

    def put_bytes(
        self,
        key: str,
        payload: bytes,
        *,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> SimpleNamespace:
        del content_type, metadata
        self.objects[key] = payload
        return SimpleNamespace(bytes=len(payload))


class PaperRunConditionalWriteV01Tests(unittest.TestCase):
    def test_local_create_if_absent_rejects_second_writer(self) -> None:
        payload = {"schema": "fixture-v0.1", "writer": "one"}
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalPaperRunStore(Path(tmp).resolve())
            receipt = store.put_json_if_absent(
                "live-run-claim",
                "claim-1",
                payload,
            )

            self.assertFalse(receipt.replayed)
            self.assertEqual(
                store.get_json("live-run-claim", "claim-1"),
                payload,
            )
            with self.assertRaises(PaperRunObjectAlreadyExistsError):
                store.put_json_if_absent(
                    "live-run-claim",
                    "claim-1",
                    payload,
                )

    def test_r2_create_if_absent_uses_conditional_put_and_preserves_winner(
        self,
    ) -> None:
        fake = FakeR2()
        store = R2PaperRunStore(fake)  # type: ignore[arg-type]
        first = {"schema": "fixture-v0.1", "writer": "one"}
        second = {"schema": "fixture-v0.1", "writer": "two"}

        receipt = store.put_json_if_absent(
            "live-run-claim",
            "claim-1",
            first,
        )
        self.assertFalse(receipt.replayed)
        self.assertEqual(
            fake.client.calls[0]["IfNoneMatch"],
            "*",
        )

        with self.assertRaises(PaperRunObjectAlreadyExistsError):
            store.put_json_if_absent(
                "live-run-claim",
                "claim-1",
                second,
            )
        self.assertEqual(
            store.get_json("live-run-claim", "claim-1"),
            first,
        )

    def test_conditional_write_report_grants_no_execution_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalPaperRunStore(Path(tmp).resolve())
            report = create_paper_run_object_if_absent(
                store=store,
                kind="live-run-claim",
                object_id="claim-1",
                payload={"schema": "fixture-v0.1"},
            )

        self.assertEqual(report["state"], "CREATED")
        self.assertEqual(report["provider_requests_performed"], 0)
        self.assertEqual(report["live_market_data_requests_performed"], 0)
        self.assertEqual(report["account_state_mutations_performed"], 0)
        authority = report["authority"]
        self.assertTrue(authority["storage_primitive_only"])
        self.assertFalse(authority["coordinator_integration_authorized"])
        self.assertFalse(authority["automatic_retry_authorized"])
        self.assertFalse(authority["automatic_schedule_authorized"])
        self.assertFalse(authority["real_money_order_authorized"])
        self.assertFalse(authority["live_real_trading_authorized"])

    def test_existing_key_conflict_is_not_reported_as_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalPaperRunStore(Path(tmp).resolve())
            create_paper_run_object_if_absent(
                store=store,
                kind="live-run-claim",
                object_id="claim-1",
                payload={"schema": "fixture-v0.1"},
            )
            with self.assertRaises(PaperRunObjectAlreadyExistsError):
                create_paper_run_object_if_absent(
                    store=store,
                    kind="live-run-claim",
                    object_id="claim-1",
                    payload={"schema": "fixture-v0.1"},
                )

    def test_versioned_config_matches_fail_closed_policy(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            paper_run_conditional_write_policy_from_config(payload),
            PaperRunConditionalWritePolicy(),
        )

        bad = json.loads(CONFIG.read_text(encoding="utf-8"))
        bad["policy"]["coordinator_integration_authorized"] = True
        with self.assertRaises(ValueError):
            paper_run_conditional_write_policy_from_config(bad)


if __name__ == "__main__":
    unittest.main()
