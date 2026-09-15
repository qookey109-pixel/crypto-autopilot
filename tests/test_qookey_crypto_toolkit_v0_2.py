from __future__ import annotations

import unittest

from crypto_autopilot.toolkit import (
    build_research_report,
    compare_backtests,
    list_capabilities,
    list_capabilities_v0_2,
    run_paper_backtest,
    stress_paper_backtest,
    validate_candles,
)


def _backtest_payload(*, fee_bps: float = 0.0, slippage_bps: float = 0.0):
    return {
        "candles_by_symbol": {
            "BTCUSDT": [
                {
                    "time_ms": 0,
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.0,
                    "volume": 10.0,
                },
                {
                    "time_ms": 60_000,
                    "open": 100.0,
                    "high": 106.0,
                    "low": 99.0,
                    "close": 105.0,
                    "volume": 12.0,
                },
            ]
        },
        "plans": [
            {
                "plan_id": "paper-1",
                "symbol": "BTCUSDT",
                "signal_time_ms": 0,
                "stop_price": 95.0,
                "target_price": 105.0,
            }
        ],
        "config": {
            "taker_fee_bps": fee_bps,
            "slippage_bps": slippage_bps,
        },
    }


class QookeyCryptoToolkitV02Tests(unittest.TestCase):
    def test_v01_capabilities_remain_compatible_and_v02_is_superset(self) -> None:
        v01 = list_capabilities()
        v02 = list_capabilities_v0_2()
        v01_names = {tool["name"] for tool in v01["tools"]}
        v02_names = {tool["name"] for tool in v02["tools"]}
        self.assertEqual(v01["schema"], "qookey-crypto-toolkit-capabilities-v0.1")
        self.assertEqual(len(v01_names), 4)
        self.assertTrue(v01_names < v02_names)
        self.assertEqual(
            v02_names - v01_names,
            {
                "validate_candles",
                "stress_paper_backtest",
                "compare_backtests",
                "build_research_report",
            },
        )
        self.assertEqual(
            v02["interfaces"]["rest_api"],
            "IMPLEMENTED_PREPARED_RESEARCH_ONLY",
        )
        self.assertEqual(v02["interfaces"]["telegram"], "DEFERRED")
        self.assertEqual(v02["interfaces"]["mcp"], "DEFERRED")
        self.assertTrue(all(value is False for value in v02["safety_boundary"].values()))

    def test_validate_candles_preserves_gap_and_never_repairs(self) -> None:
        result = validate_candles(
            [
                {
                    "time_ms": 0,
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.0,
                    "volume": 10.0,
                },
                {
                    "time_ms": 7_200_000,
                    "open": 101.0,
                    "high": 102.0,
                    "low": 100.0,
                    "close": 101.0,
                    "volume": 11.0,
                },
            ],
            interval="1h",
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["canonical_interval"], "60M")
        self.assertEqual(result["gap_count"], 1)
        self.assertEqual(result["missing_bars"], 1)
        self.assertFalse(result["repair_performed"])
        self.assertFalse(result["interpolation_performed"])
        self.assertFalse(result["synthetic_candles_emitted"])
        self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_stress_backtest_is_bounded_and_does_not_mutate_strategy(self) -> None:
        result = stress_paper_backtest(
            {
                "backtest": _backtest_payload(),
                "scenarios": [
                    {"name": "base", "taker_fee_bps": 0.0, "slippage_bps": 0.0},
                    {"name": "cost", "taker_fee_bps": 10.0, "slippage_bps": 10.0},
                ],
            }
        )
        self.assertEqual(result["mode"], "PAPER_ONLY")
        self.assertEqual(result["scenario_count"], 2)
        self.assertFalse(result["automatic_strategy_mutation_performed"])
        by_name = {item["name"]: item for item in result["scenarios"]}
        self.assertGreater(
            by_name["base"]["metrics"]["return_pct"],
            by_name["cost"]["metrics"]["return_pct"],
        )
        self.assertTrue(all(value is False for value in result["authority"].values()))

        with self.assertRaisesRegex(ValueError, "unsupported stress override"):
            stress_paper_backtest(
                {
                    "backtest": _backtest_payload(),
                    "scenarios": [{"name": "bad", "stop_price": 90.0}],
                }
            )

    def test_compare_backtests_is_descriptive_only(self) -> None:
        baseline = run_paper_backtest(_backtest_payload())
        cost = run_paper_backtest(_backtest_payload(fee_bps=10.0, slippage_bps=10.0))
        result = compare_backtests(
            {
                "results": [
                    {"label": "baseline", "result": baseline},
                    {"label": "cost-stress", "result": cost},
                ]
            }
        )
        self.assertEqual(result["mode"], "RESEARCH_ONLY")
        self.assertEqual(result["baseline_label"], "baseline")
        self.assertEqual(result["descriptive_extremes"]["highest_return"], "baseline")
        self.assertFalse(result["selection_or_promotion_performed"])
        self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_report_surfaces_failed_data_quality_without_recommendation(self) -> None:
        validation = validate_candles(
            [
                {
                    "time_ms": 0,
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.0,
                    "volume": 10.0,
                },
                {
                    "time_ms": 7_200_000,
                    "open": 101.0,
                    "high": 102.0,
                    "low": 100.0,
                    "close": 101.0,
                    "volume": 11.0,
                },
            ],
            interval="1h",
        )
        report = build_research_report(
            {"title": "Local research check", "validation": validation}
        )
        self.assertEqual(report["status"], "RESEARCH_ONLY")
        self.assertIn("CANDLE_VALIDATION_FAILED", report["warnings"])
        self.assertIn("not a live-trading recommendation", report["markdown"])
        self.assertTrue(all(value is False for value in report["authority"].values()))


if __name__ == "__main__":
    unittest.main()
