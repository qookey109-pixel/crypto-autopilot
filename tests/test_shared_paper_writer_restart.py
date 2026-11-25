"""Cross-writer acceptance on one persistent, synthetic account ledger."""
from contextlib import closing, contextmanager
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Store
from crypto_autopilot.paper.prepaid_live_coordinator_v0_2 import run_prepaid_live_coordinator
from crypto_autopilot.paper.prepaid_shared_recovery_v0_3 import run_prepaid_shared_recovery_v0_3
from crypto_autopilot.paper.shared_writer_budget_gate_v0_5 import (
    READ_SHARED_WRITER_SQL,
    RESERVE_SHARED_WRITER_SQL,
)
import test_prepaid_d1_runtime_v0_1 as common
import test_prepaid_live_coordinator_v0_1 as coordinator
import test_prepaid_shared_recovery_v0_2 as recovery


@contextmanager
def configured(case):
    try:
        case.setUp()
        yield case
    finally:
        case.doCleanups()


class SharedPaperWriterRestartTests(unittest.TestCase):
    def setUp(self):
        for target in ("socket.getaddrinfo", "socket.socket.connect", "socket.socket.connect_ex"):
            self.enterContext(patch(target, side_effect=AssertionError("unexpected network access")))
        self.database = Path(self.enterContext(tempfile.TemporaryDirectory())) / "account.sqlite"

    def commit_no_trade(self, reservation_limit):
        with configured(coordinator.SharedLiveCoordinatorTests()) as fixture:
            with closing(sqlite3.connect(self.database)) as db:
                fixture.db.commit()
                fixture.db.backup(db)
                db.execute(
                    "INSERT INTO cloudflare_shared_writer_identities_v0_3 VALUES (?, 'ACTIVE', ?, ?)",
                    (recovery.WRITER, "a" * 64, fixture.f.now),
                )
                db.execute(
                    "UPDATE cloudflare_shared_writer_budget_policy_v0_4 "
                    "SET max_reservations_per_utc_day = ?", (reservation_limit,),
                )
                db.commit()
                fixture.db = db
                report = run_prepaid_live_coordinator(**fixture.args())
                self.assertEqual(report["status"], "COMMITTED")
                self.assertEqual(report["provider_requests_performed"], 0)
                self.assertEqual(fixture.statements, [RESERVE_SHARED_WRITER_SQL])
                return report["run_id"], fixture.f.sdk

    def check_recovery(self, reservation_limit):
        run_id, sdk = self.commit_no_trade(reservation_limit)
        previous_calls = len(sdk.calls)
        with configured(recovery.PrepaidSharedRecoveryTests()) as fixture:
            fixture.f._set_run(102)
            fixture.f.meter = fixture.f.claim(102)
            with closing(sqlite3.connect(self.database)) as db:
                with patch.object(fixture.f, "sqlite", return_value=db):
                    _, statements, opener = fixture.transport()
                env = {"CLOUDFLARE_D1_API_TOKEN": "fixture", "CLOUDFLARE_ACCOUNT_ID": "a" * 32,
                       "CLOUDFLARE_D1_DATABASE_ID": common.DB_ID}

                def store_factory(*, bucket, before_external, policy, **kwargs):
                    return BudgetedR2Store(client=sdk, bucket=bucket,
                                           before_external=before_external, policy=policy)

                with (patch.dict("os.environ", env),
                      patch(common.CLIENT_MODULE + ".build_opener", return_value=opener),
                      patch.object(BudgetedR2Store, "from_credentials", side_effect=store_factory) as store):
                    args = fixture.args(run_id=run_id, repair_missing_result_seals=False)
                    if reservation_limit == 1:
                        with self.assertRaisesRegex(BudgetBlocked, "SHARED_WRITER_POLICY_OR_WRITER_GATE"):
                            run_prepaid_shared_recovery_v0_3(**args)
                        store.assert_not_called()
                        self.assertEqual(statements, [RESERVE_SHARED_WRITER_SQL, READ_SHARED_WRITER_SQL])
                        self.assertEqual(sdk.calls[previous_calls:], [])
                    else:
                        audit = run_prepaid_shared_recovery_v0_3(**args)
                        self.assertEqual(audit["state"], "RUN_CONSISTENT")
                        self.assertEqual(audit["step_count"], 1)
                        self.assertEqual(audit["result_seal_writes_performed"], 0)
                        self.assertEqual(audit["provider_requests_performed"], 0)
                        self.assertEqual(statements, [RESERVE_SHARED_WRITER_SQL])
                        operations = {call["operation"] for call in sdk.calls[previous_calls:]}
                        self.assertEqual(operations, {"GET", "LIST"})
                rows = db.execute(
                    "SELECT writer_id FROM cloudflare_shared_writer_reservations_v0_3 ORDER BY writer_id"
                ).fetchall()
                expected = [coordinator.WRITER] if reservation_limit == 1 else [coordinator.WRITER, recovery.WRITER]
                self.assertEqual(rows, [(writer,) for writer in sorted(expected)])

    def test_spent_account_reservation_blocks_other_writer_after_restart(self):
        self.check_recovery(reservation_limit=1)

    def test_second_reservation_audits_first_writers_actual_objects_after_restart(self):
        self.check_recovery(reservation_limit=2)
