from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from crypto_autopilot.models import SStateContext
from crypto_autopilot.technical import TechnicalSnapshot


class GateStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNDEFINED = "UNDEFINED"


@dataclass(frozen=True, slots=True)
class GateResult:
    name: str
    status: GateStatus
    reason: str


@dataclass(frozen=True, slots=True)
class ReplayGatePolicy:
    allowed_sstates: tuple[str, ...] = ("S3", "S0.5", "S2", "S1")
    minimum_probability: float = 0.60
    minimum_samples: int = 50

    def __post_init__(self) -> None:
        if not self.allowed_sstates or any(not state.strip() for state in self.allowed_sstates):
            raise ValueError("allowed_sstates must contain non-empty values")
        if not 0.0 <= self.minimum_probability <= 1.0:
            raise ValueError("minimum_probability must be within [0, 1]")
        if self.minimum_samples < 0:
            raise ValueError("minimum_samples cannot be negative")


@dataclass(frozen=True, slots=True)
class ReplayReadiness:
    sstate_gate: GateResult
    setup_ema_order: GateResult
    setup_ema20_slope: GateResult
    setup_close_above_ema20: GateResult
    setup_extension: GateResult
    entry_pullback: GateResult
    entry_reclaim: GateResult
    entry_previous_high_break: GateResult
    entry_volume_confirmation: GateResult
    stop_atr_buffer: GateResult
    trade_plan_authorized: bool

    @property
    def undefined_rules(self) -> tuple[str, ...]:
        return tuple(
            result.name
            for result in self._all_results()
            if result.status is GateStatus.UNDEFINED
        )

    @property
    def failed_rules(self) -> tuple[str, ...]:
        return tuple(
            result.name
            for result in self._all_results()
            if result.status is GateStatus.FAIL
        )

    def _all_results(self) -> tuple[GateResult, ...]:
        return (
            self.sstate_gate,
            self.setup_ema_order,
            self.setup_ema20_slope,
            self.setup_close_above_ema20,
            self.setup_extension,
            self.entry_pullback,
            self.entry_reclaim,
            self.entry_previous_high_break,
            self.entry_volume_confirmation,
            self.stop_atr_buffer,
        )


def evaluate_sstate_gate(
    context: SStateContext,
    *,
    policy: ReplayGatePolicy = ReplayGatePolicy(),
) -> GateResult:
    if context.state not in policy.allowed_sstates:
        return GateResult("sstate_gate", GateStatus.FAIL, f"state_not_allowed:{context.state}")
    if not context.available or context.probability is None:
        return GateResult("sstate_gate", GateStatus.FAIL, "probability_unavailable")
    if context.samples < policy.minimum_samples:
        return GateResult("sstate_gate", GateStatus.FAIL, "insufficient_samples")
    if context.probability < policy.minimum_probability:
        return GateResult("sstate_gate", GateStatus.FAIL, "probability_below_minimum")
    return GateResult("sstate_gate", GateStatus.PASS, "frozen_v0_1_gate_pass")


def _technical_defined(
    name: str,
    value: bool | None,
    *,
    missing_reason: str,
) -> GateResult:
    if value is None:
        return GateResult(name, GateStatus.FAIL, missing_reason)
    return GateResult(name, GateStatus.PASS if value else GateStatus.FAIL, "condition_true" if value else "condition_false")


def assess_replay_readiness(
    *,
    sstate: SStateContext,
    setup_1h: TechnicalSnapshot,
    entry_15m: TechnicalSnapshot,
    policy: ReplayGatePolicy = ReplayGatePolicy(),
) -> ReplayReadiness:
    """Assess only rules currently frozen by V0.1 authority.

    Undefined strategy semantics remain UNDEFINED and force
    `trade_plan_authorized=False`; this function never invents a threshold.
    """

    ema_order = None if setup_1h.ema20 is None or setup_1h.ema50 is None else setup_1h.ema20 > setup_1h.ema50
    slope_positive = None if setup_1h.ema20_slope is None else setup_1h.ema20_slope > 0
    close_above = None if setup_1h.ema20 is None else setup_1h.close > setup_1h.ema20

    sstate_result = evaluate_sstate_gate(sstate, policy=policy)
    ema_order_result = _technical_defined("setup_ema20_above_ema50", ema_order, missing_reason="technical_not_ready")
    slope_result = _technical_defined("setup_ema20_slope_positive", slope_positive, missing_reason="technical_not_ready")
    close_result = _technical_defined("setup_close_above_ema20", close_above, missing_reason="technical_not_ready")

    undefined = (
        GateResult("setup_atr_normalized_overextension_threshold", GateStatus.UNDEFINED, "threshold_not_frozen"),
        GateResult("entry_pullback_toward_ema20", GateStatus.UNDEFINED, "semantics_not_frozen"),
        GateResult("entry_reclaim_ema20", GateStatus.UNDEFINED, "semantics_not_frozen"),
        GateResult("entry_break_previous_high", GateStatus.UNDEFINED, "break_semantics_not_frozen"),
        GateResult("entry_volume_confirmation", GateStatus.UNDEFINED, "multiplier_not_frozen"),
        GateResult("stop_atr_buffer", GateStatus.UNDEFINED, "buffer_size_not_frozen"),
    )

    del entry_15m  # Raw entry features exist, but their gate semantics are intentionally not frozen yet.

    return ReplayReadiness(
        sstate_gate=sstate_result,
        setup_ema_order=ema_order_result,
        setup_ema20_slope=slope_result,
        setup_close_above_ema20=close_result,
        setup_extension=undefined[0],
        entry_pullback=undefined[1],
        entry_reclaim=undefined[2],
        entry_previous_high_break=undefined[3],
        entry_volume_confirmation=undefined[4],
        stop_atr_buffer=undefined[5],
        trade_plan_authorized=False,
    )
