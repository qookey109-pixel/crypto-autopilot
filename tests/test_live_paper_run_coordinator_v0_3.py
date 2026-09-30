from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import test_live_paper_run_coordinator_v0_1 as legacy_tests
from crypto_autopilot.paper.run_coordinator_v0_3 import (
    LivePaperRunCoordinatorPolicy,
    coordinate_live_paper_run_step,
    live_paper_run_coordinator_policy_from_config,
    read_live_paper_run_step_tick,
    verify_live_paper_run_step,
)
from crypto_autopilot.paper.run_store_v0_1 import LocalPaperRunStore

ROOT = Path(__file__).resolve().parents[1]
SequenceFeed = legacy_tests.SequenceFeed
frame = legacy_tests.frame


class LivePaperRunCoordinatorV03Tests(unittest.TestCase):
    _first_fixture = legacy_tests.LivePaperRunCoordinatorV01Tests._first_fixture

    def test_compact_step_replay_and_mixed_schema_continuation(self) -> None:
        state, spec, first_feed = self._first_fixture()
        compact_policy = LivePaperRunCoordinatorPolicy(compact_tick_reference=True)
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalPaperRunStore(Path(tmp).resolve())
            first = coordinate_live_paper_run_step(
                run_name="mixed-schema", tick_time_ms=5_000,
                candidate_specs=(spec,), feed=first_feed, store=store,
                initial_state=state,
            )
            old_step = copy.deepcopy(first["run_step"])
            second_feed = SequenceFeed({
                ("BTC_USDT_PERP", 6_000): frame(
                    symbol="BTC_USDT_PERP", tick=6_000, open_=100.5,
                    high=106.0, low=100.0, close=105.0, mark=105.0,
                ),
            })
            second = coordinate_live_paper_run_step(
                run_name="mixed-schema", tick_time_ms=6_000,
                candidate_specs=(), feed=second_feed, store=store,
                previous_step=first["run_step"], policy=compact_policy,
            )
            compact = second["run_step"]
            self.assertEqual(compact["schema"], "qookey-live-paper-run-step-report-v0.2")
            self.assertNotIn("tick_report", compact)
            tick = read_live_paper_run_step_tick(store, compact)
            self.assertIsNone(tick["next_state"]["active_session"])
            self.assertEqual(first["run_step"], old_step)
            self.assertEqual(
                verify_live_paper_run_step(compact, tick_report=tick), second["step_id"],
            )
            with self.assertRaisesRegex(ValueError, "requires persisted tick"):
                verify_live_paper_run_step(compact)
            objects = store.list_json_ids("live-run-step")
            replay_feed = SequenceFeed({})
            replay = coordinate_live_paper_run_step(
                run_name="mixed-schema", tick_time_ms=6_000,
                candidate_specs=(), feed=replay_feed, store=store,
                previous_step=first["run_step"], policy=compact_policy,
            )
            self.assertEqual(replay["step_id"], second["step_id"])
            self.assertEqual(replay_feed.calls, [])
            self.assertEqual(store.list_json_ids("live-run-step"), objects)
            third = coordinate_live_paper_run_step(
                run_name="mixed-schema", tick_time_ms=7_000,
                candidate_specs=(), feed=SequenceFeed({}), store=store,
                previous_step=compact, policy=compact_policy,
            )
            self.assertEqual(third["sequence"], 3)
            self.assertEqual(third["run_step"]["previous_state_id"], compact["next_state_id"])

    def test_compact_tick_reference_rejects_changed_hash_and_inline_payload(self) -> None:
        state, spec, feed = self._first_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalPaperRunStore(Path(tmp).resolve())
            report = coordinate_live_paper_run_step(
                run_name="compact-integrity", tick_time_ms=5_000,
                candidate_specs=(spec,), feed=feed, store=store,
                initial_state=state,
                policy=LivePaperRunCoordinatorPolicy(compact_tick_reference=True),
            )
            step = report["run_step"]
            tick = read_live_paper_run_step_tick(store, step)
            changed = copy.deepcopy(tick)
            # This informational field is outside the tick identity; the step
            # digest must still detect a valid-looking tick with changed content.
            changed["limitations"].append("tampered")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                verify_live_paper_run_step(step, tick_report=changed)
            inline = {**step, "tick_report": tick}
            with self.assertRaisesRegex(ValueError, "cannot embed"):
                verify_live_paper_run_step(inline, tick_report=tick)
            wrong_schema = {**step, "schema": "qookey-live-paper-run-step-report-v0.1",
                            "tick_report": tick}
            with self.assertRaisesRegex(ValueError, "step id mismatch"):
                verify_live_paper_run_step(wrong_schema)

    def test_v0_3_storage_contract_keeps_runtime_closed_and_requires_compaction(self) -> None:
        path = ROOT / "config" / "live_paper_run_coordinator_v0_3.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        policy = live_paper_run_coordinator_policy_from_config(config)
        self.assertTrue(policy.compact_tick_reference)
        self.assertTrue(policy.run_slot_claim_required)
        self.assertTrue(all(value is False for value in config["runtime"].values()))
        config["policy"]["compact_tick_reference"] = False
        with self.assertRaisesRegex(ValueError, "requires compact"):
            live_paper_run_coordinator_policy_from_config(config)

    def test_prepared_successor_receipt_binds_current_files_and_no_runtime(self) -> None:
        receipt = json.loads((ROOT / "research/receipts/"
                              "2026-09-30-live-paper-step-reference-v0-2-prepared.json")
                             .read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "PREPARED_STORAGE_SCHEMA_ONLY")
        for key in ("activation_enabled", "schedule_enabled", "d1_access_performed",
                    "r2_access_performed", "budget_authority_changed"):
            self.assertIs(receipt["runtime"][key], False)
        self.assertEqual(receipt["runtime"]["provider_requests_performed"], 0)
        paths = {row["path"] for row in receipt["bound_files"]}
        self.assertIn("src/crypto_autopilot/paper/run_coordinator_v0_3.py", paths)
        self.assertIn("src/crypto_autopilot/paper/run_recovery_v0_2.py", paths)
        for row in receipt["bound_files"]:
            payload = (ROOT / row["path"]).read_bytes()
            framed = f"blob {len(payload)}\0".encode("ascii") + payload
            self.assertEqual(hashlib.sha1(framed).hexdigest(), row["git_blob_sha"],
                             row["path"])
        legacy = json.loads((ROOT / "research/receipts/"
                             "2026-09-22-live-paper-run-slot-claim-v0-1-prepared.json")
                            .read_text(encoding="utf-8"))
        for row in legacy["bound_files"]:
            payload = (ROOT / row["path"]).read_bytes()
            framed = f"blob {len(payload)}\0".encode("ascii") + payload
            self.assertEqual(hashlib.sha1(framed).hexdigest(), row["git_blob_sha"],
                             row["path"])
