from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from crypto_autopilot.training.quality import (
    TrainingQualityError,
    load_v0_3_bootstrap_baseline,
    load_v0_5_authority_pair,
    sha256_payload,
    validate_v0_5_authority_pair,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "binance_spot_r2_training_governance_v0_5.json"


class TrainingQualityCharacterizationV01Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config_payload = CONFIG_PATH.read_bytes()
        cls.config = json.loads(cls.config_payload)
        cls.authority_path = ROOT / cls.config["authority_receipt"]
        cls.authority = json.loads(cls.authority_path.read_bytes())
        cls.config_sha256 = hashlib.sha256(cls.config_payload).hexdigest()

    def test_v0_5_authority_pair_exact_output_and_input_immutability(self) -> None:
        config = deepcopy(self.config)
        authority = deepcopy(self.authority)
        config_before = deepcopy(config)
        authority_before = deepcopy(authority)

        evidence = validate_v0_5_authority_pair(
            config,
            authority,
            config_sha256=self.config_sha256,
        )

        self.assertEqual(
            evidence,
            {
                "status": "PASS",
                "config_version": "0.5.0",
                "config_sha256": self.config_sha256,
                "authority_receipt": self.config["authority_receipt"],
                "provider": "binance_spot",
            },
        )
        self.assertEqual(config, config_before)
        self.assertEqual(authority, authority_before)

    def test_canonical_loader_matches_direct_validation(self) -> None:
        direct = validate_v0_5_authority_pair(
            deepcopy(self.config),
            deepcopy(self.authority),
            config_sha256=self.config_sha256,
        )
        loaded_authority, loaded_evidence = load_v0_5_authority_pair(
            deepcopy(self.config),
            config_path=CONFIG_PATH,
            config_payload=self.config_payload,
            repository_root=ROOT,
        )

        self.assertEqual(loaded_authority, self.authority)
        self.assertEqual(loaded_evidence, direct)

    def test_noncanonical_config_path_fails_before_authority_use(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            alternate = Path(directory) / CONFIG_PATH.name
            alternate.write_bytes(self.config_payload)

            with self.assertRaisesRegex(
                TrainingQualityError,
                "only the canonical V0.5 config path is executable",
            ):
                load_v0_5_authority_pair(
                    deepcopy(self.config),
                    config_path=alternate,
                    config_payload=self.config_payload,
                    repository_root=ROOT,
                )

    def test_bootstrap_baseline_contract_is_stable_and_read_only(self) -> None:
        config = deepcopy(self.config)
        before = deepcopy(config)

        baseline = load_v0_3_bootstrap_baseline(config, repository_root=ROOT)

        self.assertEqual(config, before)
        self.assertEqual(
            baseline["schema"],
            "binance-spot-r2-automated-training-pass-v0.3",
        )
        self.assertEqual(baseline["provider"], "binance_spot")
        self.assertEqual(
            baseline["dataset"]["market_count_requested"],
            748,
        )
        self.assertEqual(
            baseline["dataset"]["market_count_audited"],
            723,
        )
        self.assertEqual(baseline["dataset"]["row_count"], 701275)
        self.assertFalse(baseline["authority"]["source_switch_authorized"])
        self.assertFalse(baseline["authority"]["holdout_accessed"])
        self.assertFalse(baseline["authority"]["real_money_order_authorized"])
        self.assertFalse(baseline["authority"]["live_trading_authorized"])

    def test_sha256_payload_is_exact_bytes_not_json_semantics(self) -> None:
        first = b'{"a":1}\n'
        second = b'{ "a": 1 }\n'

        self.assertEqual(sha256_payload(first), hashlib.sha256(first).hexdigest())
        self.assertEqual(sha256_payload(second), hashlib.sha256(second).hexdigest())
        self.assertNotEqual(sha256_payload(first), sha256_payload(second))


if __name__ == "__main__":
    unittest.main()
