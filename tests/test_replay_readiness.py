from __future__ import annotations

import unittest

from crypto_autopilot.models import SStateContext
from crypto_autopilot.history.replay_readiness import (
    GateStatus,
    ReplayGatePolicy,
    assess_replay_readiness,
    evaluate_sstate_gate,
)
from crypto_autopilot.technical import TechnicalSnapshot


def snapshot(
    *,
    ema20: float | None = 105.0,
    ema50: float | None = 100.0,
    slope: float | None = 1.0,
    close: float = 106.0,
) -> TechnicalSnapshot:
    return TechnicalSnapshot(
        bar_time_ms=0,
        available_at_ms=1,
        close=close,
        volume=100.0,
        ema20=ema20,
        ema50=ema50,
        ema20_slope=slope,
        atr14=2.0,
        volume_sma20=90.0,
        volume_ratio=100.0 / 90.0,
        previous_high=104.0,
        extension_from_ema20_atr=0.5,
    )


class ReplayReadinessTest(unittest.TestCase):
    def test_frozen_sstate_gate_passes_only_when_all_conditions_pass(self) -> None:
        context = SStateContext(state="S3", probability=0.60, samples=50, available=True)
        self.assertEqual(evaluate_sstate_gate(context).status, GateStatus.PASS)

        self.assertEqual(
            evaluate_sstate_gate(SStateContext(state="S0", probability=0.9, samples=500, available=True)).status,
            GateStatus.FAIL,
        )
        self.assertEqual(
            evaluate_sstate_gate(SStateContext(state="S3", probability=0.9, samples=49, available=True)).status,
            GateStatus.FAIL,
        )
        self.assertEqual(
            evaluate_sstate_gate(SStateContext(state="S3", probability=0.59, samples=500, available=True)).status,
            GateStatus.FAIL,
        )

    def test_defined_setup_rules_can_pass_but_trade_plan_stays_blocked(self) -> None:
        result = assess_replay_readiness(
            sstate=SStateContext(state="S3", probability=0.7, samples=100, available=True),
            setup_1h=snapshot(),
            entry_15m=snapshot(),
        )
        self.assertEqual(result.sstate_gate.status, GateStatus.PASS)
        self.assertEqual(result.setup_ema_order.status, GateStatus.PASS)
        self.assertEqual(result.setup_ema20_slope.status, GateStatus.PASS)
        self.assertEqual(result.setup_close_above_ema20.status, GateStatus.PASS)
        self.assertFalse(result.trade_plan_authorized)

    def test_current_unfrozen_rules_are_explicitly_undefined(self) -> None:
        result = assess_replay_readiness(
            sstate=SStateContext(state="S1", probability=0.7, samples=100, available=True),
            setup_1h=snapshot(),
            entry_15m=snapshot(),
        )
        self.assertEqual(
            result.undefined_rules,
            (
                "setup_atr_normalized_overextension_threshold",
                "entry_pullback_toward_ema20",
                "entry_reclaim_ema20",
                "entry_break_previous_high",
                "entry_volume_confirmation",
                "stop_atr_buffer",
            ),
        )
        self.assertTrue(all(status.status is GateStatus.UNDEFINED for status in (
            result.setup_extension,
            result.entry_pullback,
            result.entry_reclaim,
            result.entry_previous_high_break,
            result.entry_volume_confirmation,
            result.stop_atr_buffer,
        )))

    def test_bad_defined_setup_rule_fails_separately_from_undefined_rules(self) -> None:
        result = assess_replay_readiness(
            sstate=SStateContext(state="S3", probability=0.7, samples=100, available=True),
            setup_1h=snapshot(ema20=99.0, ema50=100.0, slope=-1.0, close=98.0),
            entry_15m=snapshot(),
        )
        self.assertEqual(
            result.failed_rules,
            (
                "setup_ema20_above_ema50",
                "setup_ema20_slope_positive",
                "setup_close_above_ema20",
            ),
        )
        self.assertFalse(result.trade_plan_authorized)

    def test_unwarmed_technical_values_fail_closed(self) -> None:
        result = assess_replay_readiness(
            sstate=SStateContext(state="S3", probability=0.7, samples=100, available=True),
            setup_1h=snapshot(ema20=None, ema50=None, slope=None),
            entry_15m=snapshot(),
        )
        self.assertEqual(result.setup_ema_order.reason, "technical_not_ready")
        self.assertEqual(result.setup_ema_order.status, GateStatus.FAIL)
        self.assertEqual(result.setup_ema20_slope.status, GateStatus.FAIL)
        self.assertEqual(result.setup_close_above_ema20.status, GateStatus.FAIL)

    def test_policy_is_explicit_and_validated(self) -> None:
        policy = ReplayGatePolicy(
            allowed_sstates=("S3",),
            minimum_probability=0.65,
            minimum_samples=75,
        )
        self.assertEqual(
            evaluate_sstate_gate(
                SStateContext(state="S3", probability=0.66, samples=75, available=True),
                policy=policy,
            ).status,
            GateStatus.PASS,
        )
        with self.assertRaises(ValueError):
            ReplayGatePolicy(minimum_probability=1.1)


if __name__ == "__main__":
    unittest.main()
