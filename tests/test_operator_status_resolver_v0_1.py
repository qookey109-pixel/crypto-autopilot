from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from crypto_autopilot.operator_messaging_v0_1 import parse_operator_command_request
from crypto_autopilot.operator_status_resolver_v0_1 import (
    OperatorStatusResolverPolicy,
    resolve_operator_status,
)


ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "research" / "status" / "current-operations-v0-3.json"


class OperatorStatusResolverV01Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.current = json.loads(CURRENT.read_text(encoding="utf-8"))

    def test_help_is_small_read_only_capability_list(self) -> None:
        result = resolve_operator_status(
            command_request=parse_operator_command_request("help"),
            current_operations=self.current,
        )

        self.assertEqual(result["command"], "HELP")
        self.assertEqual(result["data"]["commands"], ["help", "status", "paper_status"])
        self.assertFalse(result["data"]["write_commands_available"])
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["authority"]["network_access_authorized"])

    def test_status_projects_existing_current_operations_without_new_authority(self) -> None:
        result = resolve_operator_status(
            command_request=parse_operator_command_request("/status"),
            current_operations=self.current,
        )

        self.assertEqual(result["command"], "STATUS")
        self.assertEqual(result["data"]["core100_history"], "COMPLETE")
        self.assertEqual(result["data"]["model_quality"], "REJECT")
        self.assertEqual(result["data"]["holdout"], "FROZEN_UNOPENED")
        self.assertEqual(result["data"]["real_money_orders"], "CLOSED")
        self.assertEqual(result["data"]["live_trading"], "CLOSED")
        self.assertEqual(
            result["data"]["live_paper_simulation"],
            "AUTHORIZED_PUBLIC_MARKET_PAPER_ONLY",
        )

    def test_paper_status_preserves_public_paper_vs_real_trading_boundary(self) -> None:
        result = resolve_operator_status(
            command_request=parse_operator_command_request("paper_status"),
            current_operations=self.current,
        )

        self.assertEqual(result["command"], "PAPER_STATUS")
        self.assertTrue(result["data"]["public_live_market_data"])
        self.assertTrue(result["data"]["live_paper_simulation"])
        self.assertTrue(result["data"]["paper_state_persistence"])
        self.assertFalse(result["data"]["private_exchange_api"])
        self.assertFalse(result["data"]["real_money_orders"])
        self.assertFalse(result["data"]["live_real_trading"])

    def test_snapshot_is_never_misrepresented_as_latest_main(self) -> None:
        result = resolve_operator_status(
            command_request=parse_operator_command_request("status"),
            current_operations=self.current,
        )

        self.assertFalse(result["snapshot_is_latest_main_claim"])
        self.assertEqual(
            result["repository_authority"],
            "RESOLVE_MAIN_LIVE_AT_READ_TIME",
        )
        self.assertEqual(result["snapshot_updated_date"], "2026-09-22")

    def test_unrecognized_or_execution_authorized_command_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            resolve_operator_status(
                command_request=parse_operator_command_request("buy btc"),
                current_operations=self.current,
            )

        unsafe = parse_operator_command_request("status")
        unsafe["execution_authorized"] = True
        with self.assertRaises(ValueError):
            resolve_operator_status(
                command_request=unsafe,
                current_operations=self.current,
            )

    def test_status_schema_or_authority_drift_fails_closed(self) -> None:
        wrong_schema = deepcopy(self.current)
        wrong_schema["schema"] = "qookey-current-operations-v0.4"
        with self.assertRaises(ValueError):
            resolve_operator_status(
                command_request=parse_operator_command_request("status"),
                current_operations=wrong_schema,
            )

        wrong_authority = deepcopy(self.current)
        wrong_authority["repository_authority"] = "STATIC_SHA_IS_LATEST"
        with self.assertRaises(ValueError):
            resolve_operator_status(
                command_request=parse_operator_command_request("status"),
                current_operations=wrong_authority,
            )

    def test_policy_cannot_open_network_execution_or_trading(self) -> None:
        for kwargs in (
            {"network_access_authorized": True},
            {"secret_access_authorized": True},
            {"command_execution_authorized": True},
            {"state_mutation_authorized": True},
            {"strategy_router_integration_authorized": True},
            {"portfolio_admission_authorized": True},
            {"real_money_order_authorized": True},
            {"live_real_trading_authorized": True},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    OperatorStatusResolverPolicy(**kwargs)


if __name__ == "__main__":
    unittest.main()
