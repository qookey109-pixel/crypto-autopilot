from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import test_live_paper_run_recovery_v0_1 as legacy_tests
from crypto_autopilot.paper.run_coordinator_v0_3 import (
    LivePaperRunCoordinatorPolicy,
    coordinate_live_paper_run_step,
)
from crypto_autopilot.paper.run_recovery_v0_2 import reconcile_live_paper_run
from crypto_autopilot.paper.run_store_v0_1 import LocalPaperRunStore

_bootstrap_state = legacy_tests._bootstrap_state
_Feed = legacy_tests._Feed
_delete_object = legacy_tests._delete_object


class LivePaperRunRecoveryV02Tests(unittest.TestCase):
    def _committed_run(
        self,
        root: Path,
        *,
        tick_time_ms: int = 5_000,
        compact_tick_reference: bool = False,
    ) -> tuple[LocalPaperRunStore, dict[str, object], dict[str, object], dict[str, object]]:
        state, spec = _bootstrap_state()
        store = LocalPaperRunStore(root)
        report = coordinate_live_paper_run_step(
            run_name="recovery-fixture",
            tick_time_ms=tick_time_ms,
            candidate_specs=(spec,),
            feed=_Feed(tick_time_ms),
            store=store,
            initial_state=state,
            policy=LivePaperRunCoordinatorPolicy(compact_tick_reference=compact_tick_reference),
        )
        return store, state, spec, report

    def test_compact_step_repairs_only_missing_seal_and_replays_without_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            store, state, spec, committed = self._committed_run(
                root, compact_tick_reference=True,
            )
            step = committed["run_step"]
            before = {kind: store.list_json_ids(kind)
                      for kind in ("live-state", "live-tick", "live-run-step")}
            _delete_object(root, "live-run-result", step["request_id"])
            audit = reconcile_live_paper_run(run_id=committed["run_id"], store=store)
            self.assertEqual(audit["state"], "MISSING_RESULT_SEALS_REPAIRABLE")
            repaired = reconcile_live_paper_run(
                run_id=committed["run_id"], store=store, repair_missing_result_seals=True,
            )
            self.assertEqual(repaired["state"], "MISSING_RESULT_SEALS_REPAIRED")
            self.assertEqual(repaired["result_seal_writes_performed"], 1)
            self.assertEqual(before, {kind: store.list_json_ids(kind) for kind in before})
            self.assertEqual(repaired["provider_requests_performed"], 0)
            feed = _Feed(5_000)
            replay = coordinate_live_paper_run_step(
                run_name="recovery-fixture", tick_time_ms=5_000,
                candidate_specs=(spec,), feed=feed, store=store, initial_state=state,
                policy=LivePaperRunCoordinatorPolicy(compact_tick_reference=True),
            )
            self.assertEqual(replay["step_id"], committed["step_id"])
            self.assertEqual(feed.calls, 0)

    def test_compact_step_missing_tick_blocks_repair_replay_and_continuation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            store, state, spec, committed = self._committed_run(
                root, compact_tick_reference=True,
            )
            step = committed["run_step"]
            _delete_object(root, "live-run-result", step["request_id"])
            _delete_object(root, "live-tick", step["tick_id"])
            recovery = reconcile_live_paper_run(
                run_id=committed["run_id"], store=store, repair_missing_result_seals=True,
            )
            self.assertEqual(recovery["state"], "REVIEW_REQUIRED")
            self.assertEqual(recovery["result_seal_writes_performed"], 0)
            self.assertIsNone(store.get_json("live-run-result", step["request_id"]))
            feed = _Feed(6_000)
            with self.assertRaisesRegex(ValueError, "persisted live tick is missing"):
                coordinate_live_paper_run_step(
                    run_name="recovery-fixture", tick_time_ms=6_000,
                    candidate_specs=(), feed=feed, store=store, previous_step=step,
                )
            self.assertEqual(feed.calls, 0)
            self.assertEqual(state["state_id"], step["previous_state_id"])

    def test_missing_tick_evidence_requires_review_and_is_not_repaired(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            store, _, _, committed = self._committed_run(root)
            step = committed["run_step"]
            _delete_object(root, "live-tick", step["tick_id"])
            _delete_object(root, "live-run-result", step["request_id"])

            recovery = reconcile_live_paper_run(
                run_id=committed["run_id"],
                store=store,
                repair_missing_result_seals=True,
            )

            self.assertEqual(recovery["state"], "REVIEW_REQUIRED")
            self.assertEqual(recovery["result_seal_writes_performed"], 0)
            self.assertTrue(
                any(
                    issue.startswith("incomplete_step_evidence:")
                    for issue in recovery["issues"]
                )
            )
            self.assertIsNone(
                store.get_json("live-run-result", step["request_id"])
            )
