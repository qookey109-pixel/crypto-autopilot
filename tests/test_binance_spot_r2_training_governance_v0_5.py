from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from crypto_autopilot.training.quality import (
    TrainingQualityError,
    load_v0_3_bootstrap_baseline,
    load_v0_5_authority_pair,
    validate_v0_5_authority_pair,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/binance_spot_r2_training_governance_v0_5.json"


class BinanceSpotR2TrainingGovernanceV05Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config_payload = CONFIG_PATH.read_bytes()
        self.config = json.loads(self.config_payload)
        self.authority = json.loads(
            Path(
                "research/receipts/2026-08-23-binance-spot-r2-training-governance-v0-5-authority.json"
            ).read_text()
        )
        self.weekly = Path(
            ".github/workflows/binance-spot-r2-training-governance-v0-5.yml"
        ).read_text()
        self.monthly = Path(
            ".github/workflows/binance-spot-r2-monthly-governance-v0-5.yml"
        ).read_text()

    def test_versioned_authority_and_namespaces_are_distinct(self) -> None:
        self.assertEqual(self.config["version"], "0.5.0")
        self.assertEqual(
            self.authority["status"],
            "TRAINING_GOVERNANCE_V0_5_AUTHORIZED_ON_MAIN_MERGE",
        )
        storage = self.config["storage"]
        self.assertEqual(storage["schema_version"], "v0.5")
        self.assertIn("/v0.5", storage["dataset_runs_namespace"])
        self.assertIn("/v0.5", storage["training_namespace"])
        self.assertIn("/v0.5/", self.config["monthly_universe_review"]["namespace"] + "/")

    def test_exact_config_authority_and_bootstrap_baseline_are_bound(self) -> None:
        _, evidence = load_v0_5_authority_pair(
            self.config,
            config_path=CONFIG_PATH,
            config_payload=self.config_payload,
            repository_root=ROOT,
        )
        baseline = load_v0_3_bootstrap_baseline(
            self.config,
            repository_root=ROOT,
        )
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(baseline["dataset"]["market_count_requested"], 748)
        self.assertEqual(baseline["dataset"]["market_count_audited"], 723)

    def test_authority_schedule_or_namespace_drift_fails_closed(self) -> None:
        for target in ("schedule", "namespace"):
            with self.subTest(target=target):
                authority = copy.deepcopy(self.authority)
                if target == "schedule":
                    authority["weekly_schedule_utc"] = "0 0 * * *"
                else:
                    authority["exact_namespaces"]["training_namespace"] = (
                        "training/binance_spot/daily-direction/v0.4"
                    )
                with self.assertRaisesRegex(
                    TrainingQualityError,
                    "authority receipt does not match configuration",
                ):
                    validate_v0_5_authority_pair(
                        self.config,
                        authority,
                        config_sha256=self.authority["authorized_config"]["sha256"],
                    )

    def test_historical_schedule_contracts_remain_but_expired_crons_are_retired(self) -> None:
        self.assertEqual(self.config["schedule"]["cron_utc"], "37 2 * * 0")
        self.assertNotIn("  schedule:", self.weekly)
        self.assertIn("  workflow_dispatch:", self.weekly)
        self.assertNotIn("\n  push:", self.weekly)
        self.assertEqual(
            self.config["monthly_universe_review"]["cron_utc"],
            "37 3 1 * *",
        )
        self.assertNotIn("  schedule:", self.monthly)
        self.assertIn("  workflow_dispatch:", self.monthly)
        self.assertNotIn("\n  push:", self.monthly)
        self.assertFalse(self.config["schedule"]["automatic_resume_after_stop"])

    def test_monthly_initial_activation_is_one_time_manual_and_pre_stop(self) -> None:
        activation = self.config["monthly_universe_review"]["initial_activation"]
        self.assertEqual(
            activation,
            self.authority["monthly_initial_activation"],
        )
        self.assertEqual(activation["mode"], "ONE_TIME_MANUAL_WORKFLOW_DISPATCH")
        self.assertEqual(
            activation["purpose"],
            "CREATE_INITIAL_V0_5_MONTHLY_BASELINE",
        )
        self.assertTrue(activation["required"])
        self.assertEqual(
            activation["must_complete_before_utc"],
            self.config["schedule"]["provider_read_stop_utc"],
        )
        self.assertFalse(activation["push_trigger_authorized"])
        self.assertFalse(activation["repeat_manual_activation_authorized"])
        self.assertTrue(
            self.authority["authority"][
                "monthly_one_time_manual_activation_authorized"
            ]
        )
        self.assertIn("workflow_dispatch:", self.monthly)
        self.assertNotIn("\n  push:", self.monthly)
        self.assertIn('--event-name "${GITHUB_EVENT_NAME}"', self.monthly)
        self.assertIn(
            '--activation-mode "${V0_5_MONTHLY_ACTIVATION_MODE}"',
            self.monthly,
        )
        self.assertIn("ONE_TIME_MANUAL_WORKFLOW_DISPATCH", self.monthly)
        self.assertIn("SCHEDULED_REVIEW", self.monthly)
        self.assertIn("retention-days: 90", self.monthly)
        self.assertNotIn("retention-days: 365", self.monthly)

    def test_monthly_initial_activation_drift_fails_closed(self) -> None:
        authority = copy.deepcopy(self.authority)
        authority["monthly_initial_activation"][
            "repeat_manual_activation_authorized"
        ] = True
        with self.assertRaisesRegex(
            TrainingQualityError,
            "authority receipt does not match configuration",
        ):
            validate_v0_5_authority_pair(
                self.config,
                authority,
                config_sha256=self.authority["authorized_config"]["sha256"],
            )

    def test_quality_gates_and_publish_order_are_explicit(self) -> None:
        data_gate = self.config["data_quality"]
        self.assertEqual(data_gate["minimum_catalog_market_count"], 500)
        self.assertEqual(data_gate["minimum_audited_market_fraction"], 0.9)
        self.assertEqual(data_gate["minimum_market_count_fraction_of_previous"], 0.8)
        self.assertEqual(data_gate["minimum_row_count_fraction_of_previous"], 0.8)
        model_gate = self.config["weekly_review"]["quality_gate"]
        self.assertEqual(model_gate["required_baseline_improvements"], ["log_loss", "brier_score"])
        self.assertEqual(model_gate["maximum_diagnostic_drawdown_pct"], 50.0)
        self.assertIn("Validate locally then publish", self.weekly)
        self.assertIn('publish["weekly_review_contract"]["status"] == "PASS"', self.weekly)

    def test_authority_never_expands_holdout_promotion_or_trading(self) -> None:
        boundary = self.config["authority"]
        for key in (
            "formal_backtest_admission_authorized",
            "automatic_model_promotion_authorized",
            "historical_universe_membership_authorized",
            "holdout_access_authorized",
            "source_switch_authorized",
            "automatic_trade_plan_authorized",
            "real_money_order_authorized",
            "live_trading_authorized",
        ):
            self.assertFalse(boundary[key], key)
        self.assertFalse(
            self.authority["authority"]["v0_10_production_critical_path_mutation"]
        )


if __name__ == "__main__":
    unittest.main()
