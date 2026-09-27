from __future__ import annotations

import unittest

from crypto_autopilot.paper.cloud_genesis_v0_1 import (
    cash_genesis_checkpoint, initialize_cloud_paper_state,
)
from crypto_autopilot.paper.checkpoint_v0_1 import (
    paper_loop_checkpoint_report_id_from_mapping,
)


class CloudPaperGenesisTests(unittest.TestCase):
    def test_funded_cash_genesis_has_no_fabricated_trade(self):
        report = cash_genesis_checkpoint()
        self.assertEqual(paper_loop_checkpoint_report_id_from_mapping(report),
                         report["checkpoint_id"])
        account = report["account_snapshot"]
        self.assertEqual(account["initial_equity_usd"], 10000.0)
        self.assertEqual(account["cash_usd"], 10000.0)
        self.assertEqual(account["equity_usd"], 10000.0)
        self.assertEqual(account["open_position_count"], 0)
        self.assertEqual(account["closed_position_count"], 0)
        self.assertEqual(report["next_account_input"]["records"], [])
        self.assertEqual(report["batch_id"], "GENESIS_NO_BATCH")
        self.assertIs(report["origin"]["previous_batch_exists"], False)
        self.assertEqual(report["origin"]["trade_count"], 0)
        self.assertEqual(report["provider_requests_performed"], 0)
        self.assertEqual(report["persistent_state_writes_performed"], 0)

    def test_initialized_state_is_deterministic_and_valid(self):
        first = initialize_cloud_paper_state()
        second = initialize_cloud_paper_state()
        self.assertEqual(first["state_id"], second["state_id"])
        self.assertEqual(first["checkpoint_report"]["account_snapshot"]["cash_usd"],
                         10000.0)
        self.assertEqual(first["last_tick_ms"], 0)
