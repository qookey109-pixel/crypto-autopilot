from __future__ import annotations

import json
import unittest
from pathlib import Path

from crypto_autopilot.operator_messaging_v0_1 import (
    OperatorMessagingPolicy,
    build_operator_notification,
    operator_messaging_policy_from_config,
    parse_operator_command_request,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "operator_messaging_v0_1.json"


class OperatorMessagingV01Tests(unittest.TestCase):
    def test_notification_is_deterministic_and_provider_neutral(self) -> None:
        kwargs = {
            "source": "paper-run",
            "topic": "paper.status",
            "title": "Paper run complete",
            "body": "Run completed without real-money execution.",
            "severity": "info",
            "created_at_ms": 1234,
            "dedupe_key": "paper:run-7:complete",
            "metadata": {"run_id": "run-7", "positions": 2},
        }
        one = build_operator_notification(**kwargs)
        two = build_operator_notification(**kwargs)

        self.assertEqual(one, two)
        self.assertEqual(one["severity"], "INFO")
        self.assertIsNone(one["delivery"]["provider"])
        self.assertFalse(one["delivery"]["network_delivery_authorized"])
        self.assertFalse(one["authority"]["real_money_order_authorized"])

    def test_secret_bearing_metadata_keys_fail_closed(self) -> None:
        for key in ("token", "api_key", "telegram_session", "password_hint"):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    build_operator_notification(
                        source="paper-run",
                        topic="paper.status",
                        title="Status",
                        body="Safe body",
                        severity="INFO",
                        created_at_ms=1,
                        metadata={key: "value"},
                    )

    def test_invalid_notification_inputs_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            build_operator_notification(
                source="paper-run",
                topic="paper.status",
                title="Status",
                body="Safe body",
                severity="CRITICAL",
                created_at_ms=1,
            )
        with self.assertRaises(ValueError):
            build_operator_notification(
                source="paper-run",
                topic="paper.status",
                title="Status",
                body="Safe body",
                severity="INFO",
                created_at_ms=True,
            )

    def test_only_exact_read_only_commands_are_recognized(self) -> None:
        cases = {
            "help": "HELP",
            "/status": "STATUS",
            "paper_status": "PAPER_STATUS",
            "/paper-status": "PAPER_STATUS",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                result = parse_operator_command_request(raw)
                self.assertTrue(result["recognized"])
                self.assertEqual(result["command"], expected)
                self.assertTrue(result["read_only"])
                self.assertFalse(result["execution_authorized"])

        for raw in ("status now", "buy btc", "pause", "/resume", "paper_status please"):
            with self.subTest(raw=raw):
                result = parse_operator_command_request(raw)
                self.assertFalse(result["recognized"])
                self.assertIsNone(result["command"])
                self.assertFalse(result["execution_authorized"])

    def test_policy_cannot_open_write_or_network_authority(self) -> None:
        for kwargs in (
            {"write_command_requests_authorized": True},
            {"automatic_command_execution_authorized": True},
            {"network_delivery_authorized": True},
            {"telegram_bot_runtime_authorized": True},
            {"telegram_user_session_authorized": True},
            {"secret_access_authorized": True},
            {"real_money_order_authorized": True},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    OperatorMessagingPolicy(**kwargs)

    def test_config_keeps_runtime_and_write_authority_closed(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            operator_messaging_policy_from_config(payload),
            OperatorMessagingPolicy(),
        )
        self.assertEqual(
            payload["read_only_commands"],
            ["help", "status", "paper_status"],
        )
        self.assertTrue(payload["policy"]["notifications_authorized"])
        self.assertTrue(payload["policy"]["read_only_command_requests_authorized"])
        self.assertTrue(
            all(
                value is False
                for key, value in payload["policy"].items()
                if key
                not in {
                    "notifications_authorized",
                    "read_only_command_requests_authorized",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
