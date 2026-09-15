from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from crypto_autopilot.toolkit.descriptive_context_v0_1 import (
    DescriptiveContextError,
    build_descriptive_context_envelope,
)


POLICY_PATH = Path("config/resource_hub_descriptive_context_v0_1.json")
AS_OF = "2026-09-15T09:20:00Z"


def _payload() -> dict[str, object]:
    return {
        "source": "synthetic-world-monitor-fixture",
        "context_type": "supply_chain_disruption",
        "observed_at": "2026-09-15T09:00:00Z",
        "cached_at": "2026-09-15T09:05:00Z",
        "stale": False,
        "summary": "A shipping route interruption was reported near a major chokepoint.",
        "severity": "elevated",
        "provenance": [
            {
                "source_name": "Synthetic Newswire",
                "source_url": "https://example.invalid/synthetic-event-1",
            }
        ],
    }


class ResourceHubDescriptiveContextV01Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    def test_valid_synthetic_context_is_descriptive_only(self) -> None:
        report = build_descriptive_context_envelope(
            _payload(),
            self.policy,
            input_class="synthetic_fixture",
            as_of=AS_OF,
        )
        self.assertEqual(report["schema"], "resource-hub-descriptive-context-envelope-v0.1")
        self.assertEqual(report["status"], "RESEARCH_ONLY")
        self.assertEqual(report["decision"], "DESCRIPTIVE_CONTEXT_ONLY")
        self.assertEqual(report["freshness"]["cache_age_seconds"], 900)
        self.assertEqual(report["freshness"]["observation_age_seconds"], 1200)
        self.assertIsNone(report["directional_signal"])
        self.assertFalse(report["strategy_eligible"])
        self.assertFalse(report["formal_backtest_eligible"])
        self.assertFalse(report["trade_plan_eligible"])
        self.assertTrue(all(value is False for value in report["authority"].values()))

    def test_stale_or_over_age_context_fails_closed(self) -> None:
        stale = _payload()
        stale["stale"] = True
        with self.assertRaisesRegex(DescriptiveContextError, "stale context"):
            build_descriptive_context_envelope(
                stale,
                self.policy,
                input_class="synthetic_fixture",
                as_of=AS_OF,
            )

        old_cache = _payload()
        old_cache["cached_at"] = "2026-09-15T08:00:00Z"
        old_cache["observed_at"] = "2026-09-15T07:55:00Z"
        with self.assertRaisesRegex(DescriptiveContextError, "freshness budget"):
            build_descriptive_context_envelope(
                old_cache,
                self.policy,
                input_class="synthetic_fixture",
                as_of=AS_OF,
            )

    def test_future_or_inverted_timestamps_fail_closed(self) -> None:
        inverted = _payload()
        inverted["observed_at"] = "2026-09-15T09:10:00Z"
        inverted["cached_at"] = "2026-09-15T09:05:00Z"
        with self.assertRaisesRegex(DescriptiveContextError, "later than cached_at"):
            build_descriptive_context_envelope(
                inverted,
                self.policy,
                input_class="synthetic_fixture",
                as_of=AS_OF,
            )

        future = _payload()
        future["cached_at"] = "2026-09-15T09:21:00Z"
        future["observed_at"] = "2026-09-15T09:20:45Z"
        with self.assertRaisesRegex(DescriptiveContextError, "future"):
            build_descriptive_context_envelope(
                future,
                self.policy,
                input_class="synthetic_fixture",
                as_of=AS_OF,
            )

    def test_missing_or_invalid_provenance_fails_closed(self) -> None:
        missing = _payload()
        missing["provenance"] = []
        with self.assertRaisesRegex(DescriptiveContextError, "source count"):
            build_descriptive_context_envelope(
                missing,
                self.policy,
                input_class="synthetic_fixture",
                as_of=AS_OF,
            )

        insecure = _payload()
        insecure["provenance"] = [
            {
                "source_name": "Synthetic Newswire",
                "source_url": "http://example.invalid/synthetic-event-1",
            }
        ]
        with self.assertRaisesRegex(DescriptiveContextError, "HTTPS"):
            build_descriptive_context_envelope(
                insecure,
                self.policy,
                input_class="synthetic_fixture",
                as_of=AS_OF,
            )

    def test_non_synthetic_input_classes_are_rejected(self) -> None:
        for input_class in (
            "existing_non_holdout_fixture",
            "worldmonitor_live",
            "provider_data",
            "r2_fixture",
            "holdout",
        ):
            with self.subTest(input_class=input_class):
                with self.assertRaisesRegex(DescriptiveContextError, "input class"):
                    build_descriptive_context_envelope(
                        _payload(),
                        self.policy,
                        input_class=input_class,
                        as_of=AS_OF,
                    )

    def test_directional_or_trade_language_is_rejected(self) -> None:
        for summary in (
            "Buy BTC because the chokepoint is disrupted.",
            "The environment is bullish for crypto.",
            "Use a 3x leverage trade plan.",
            "Treat this as a risk-off signal.",
        ):
            payload = _payload()
            payload["summary"] = summary
            with self.subTest(summary=summary):
                with self.assertRaisesRegex(DescriptiveContextError, "directional"):
                    build_descriptive_context_envelope(
                        payload,
                        self.policy,
                        input_class="synthetic_fixture",
                        as_of=AS_OF,
                    )

    def test_extra_strategy_or_return_fields_are_rejected(self) -> None:
        payload = _payload()
        payload["expected_return"] = 0.10
        with self.assertRaisesRegex(DescriptiveContextError, "payload keys"):
            build_descriptive_context_envelope(
                payload,
                self.policy,
                input_class="synthetic_fixture",
                as_of=AS_OF,
            )

    def test_any_authority_or_interpretation_expansion_fails_closed(self) -> None:
        unsafe_authority = deepcopy(self.policy)
        unsafe_authority["authority"]["worldmonitor_network_call_authorized"] = True
        with self.assertRaisesRegex(DescriptiveContextError, "authority flags"):
            build_descriptive_context_envelope(
                _payload(),
                unsafe_authority,
                input_class="synthetic_fixture",
                as_of=AS_OF,
            )

        unsafe_interpretation = deepcopy(self.policy)
        unsafe_interpretation["interpretation"]["strategy_input"] = True
        with self.assertRaisesRegex(DescriptiveContextError, "interpretation flags"):
            build_descriptive_context_envelope(
                _payload(),
                unsafe_interpretation,
                input_class="synthetic_fixture",
                as_of=AS_OF,
            )


if __name__ == "__main__":
    unittest.main()
