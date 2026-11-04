"""Synthetic replay tests: in-memory SQLite, never production Cloudflare."""
import socket
import sqlite3
import unittest
from unittest.mock import patch

from crypto_autopilot.paper.synthetic_job_replay_v0_1 import (
    claim_synthetic_job,
    initialize_synthetic_replay_ledger,
)


class SyntheticJobReplayTests(unittest.TestCase):
    def setUp(self):
        for obj, name in ((socket, "getaddrinfo"), (socket.socket, "connect"),
                          (socket.socket, "connect_ex")):
            guard = patch.object(obj, name, side_effect=AssertionError("network forbidden"))
            guard.start()
            self.addCleanup(guard.stop)
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        initialize_synthetic_replay_ledger(self.db)
        self.identity = {
            "repository_id": "123", "run_id": "456", "attempt": "1",
            "check_run_id": "789", "writer_id": "paper", "slot_id": "slot:1234",
        }

    def claim(self, **changes):
        return claim_synthetic_job(self.db, **(self.identity | changes))

    def test_new_token_cannot_reclaim_same_job_or_slot(self):
        self.assertTrue(self.claim())
        # A fresh JWT/jti cannot change either key; it is not an input.
        self.assertFalse(self.claim())
        self.assertFalse(self.claim(slot_id="slot:1235"))
        self.assertFalse(self.claim(run_id="457", check_run_id="790"))

    def test_unrelated_job_and_slot_can_claim(self):
        self.assertTrue(self.claim())
        self.assertTrue(self.claim(run_id="457", check_run_id="790", slot_id="slot:1235"))

    def test_invalid_and_existing_transaction_stop_before_mutation(self):
        for changes in ({"run_id": ""}, {"attempt": "2"}, {"slot_id": "slot:-1"},
                        {"writer_id": "../paper"}, {"check_run_id": True}):
            with self.subTest(changes=changes):
                self.assertFalse(self.claim(**changes))
        self.db.execute("BEGIN")
        self.assertFalse(self.claim())
        self.db.rollback()
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM synthetic_job_claim").fetchone()[0], 0)

    def test_rollback_after_ambiguous_response_never_reclaims_committed_key(self):
        class LostResponse:
            def __init__(self, db):
                self.db = db

            @property
            def in_transaction(self):
                return self.db.in_transaction

            def execute(self, *args):
                return self.db.execute(*args)

            def commit(self):
                self.db.commit()
                raise sqlite3.OperationalError("lost result")

            def rollback(self):
                self.db.rollback()

        self.assertFalse(claim_synthetic_job(LostResponse(self.db), **self.identity))
        self.assertFalse(self.claim())
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM synthetic_job_claim").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
