from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from crypto_autopilot.paper.run_claim_v0_1 import (
    LivePaperRunClaimConflictError,
    LivePaperRunClaimPolicy,
    acquire_live_paper_run_claim,
    build_live_paper_run_claim,
    live_paper_run_claim_policy_from_config,
    live_paper_run_slot_id,
    verify_live_paper_run_claim,
)
from crypto_autopilot.paper.run_store_v0_1 import LocalPaperRunStore


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "live_paper_run_claim_v0_1.json"


class LivePaperRunClaimV01Tests(unittest.TestCase):
    def test_slot_identity_excludes_tick_and_candidates(self) -> None:
        one = live_paper_run_slot_id(
            run_id="run-1",
            sequence=1,
            previous_step_id=None,
            previous_state_id="state-1",
        )
        two = live_paper_run_slot_id(
            run_id="run-1",
            sequence=1,
            previous_step_id=None,
            previous_state_id="state-1",
        )
        self.assertEqual(one, two)

        claim_a = build_live_paper_run_claim(
            run_id="run-1",
            sequence=1,
            previous_step_id=None,
            previous_state_id="state-1",
            request_id="request-a",
            tick_time_ms=1_000,
            candidate_specs_sha256="a" * 64,
        )
        claim_b = build_live_paper_run_claim(
            run_id="run-1",
            sequence=1,
            previous_step_id=None,
            previous_state_id="state-1",
            request_id="request-b",
            tick_time_ms=2_000,
            candidate_specs_sha256="b" * 64,
        )
        self.assertEqual(claim_a["slot_id"], claim_b["slot_id"])
        self.assertEqual(verify_live_paper_run_claim(claim_a), one)

    def test_only_one_request_can_claim_the_same_run_slot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalPaperRunStore(Path(tmp).resolve())
            first, receipt = acquire_live_paper_run_claim(
                store=store,
                run_id="run-1",
                sequence=1,
                previous_step_id=None,
                previous_state_id="state-1",
                request_id="request-a",
                tick_time_ms=1_000,
                candidate_specs_sha256="a" * 64,
            )
            self.assertFalse(receipt.replayed)
            self.assertIsNotNone(
                store.get_json("live-run-claim", str(first["slot_id"]))
            )

            with self.assertRaisesRegex(
                LivePaperRunClaimConflictError,
                "same_request",
            ):
                acquire_live_paper_run_claim(
                    store=store,
                    run_id="run-1",
                    sequence=1,
                    previous_step_id=None,
                    previous_state_id="state-1",
                    request_id="request-a",
                    tick_time_ms=1_000,
                    candidate_specs_sha256="a" * 64,
                )

            with self.assertRaisesRegex(
                LivePaperRunClaimConflictError,
                "different_request",
            ):
                acquire_live_paper_run_claim(
                    store=store,
                    run_id="run-1",
                    sequence=1,
                    previous_step_id=None,
                    previous_state_id="state-1",
                    request_id="request-b",
                    tick_time_ms=2_000,
                    candidate_specs_sha256="b" * 64,
                )

    def test_next_sequence_is_a_different_slot(self) -> None:
        first = live_paper_run_slot_id(
            run_id="run-1",
            sequence=1,
            previous_step_id=None,
            previous_state_id="state-1",
        )
        second = live_paper_run_slot_id(
            run_id="run-1",
            sequence=2,
            previous_step_id="step-1",
            previous_state_id="state-2",
        )
        self.assertNotEqual(first, second)

    def test_policy_forbids_expiry_takeover_retry_and_execution_authority(self) -> None:
        for kwargs in (
            {"claim_expiry_authorized": True},
            {"claim_takeover_authorized": True},
            {"automatic_retry_after_conflict_authorized": True},
            {"provider_access_authorized": True},
            {"live_market_data_access_authorized": True},
            {"account_state_mutation_authorized": True},
            {"automatic_schedule_authorized": True},
            {"private_exchange_api_authorized": True},
            {"holdout_access_authorized": True},
            {"real_money_order_authorized": True},
            {"live_real_trading_authorized": True},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    LivePaperRunClaimPolicy(**kwargs)

    def test_versioned_config_matches_claim_policy(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            live_paper_run_claim_policy_from_config(payload),
            LivePaperRunClaimPolicy(),
        )
        self.assertFalse(payload["crash_contract"]["automatic_takeover"])
        self.assertTrue(payload["crash_contract"]["unresolved_claim_requires_review"])


if __name__ == "__main__":
    unittest.main()
