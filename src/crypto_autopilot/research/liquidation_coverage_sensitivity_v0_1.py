from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

INPUT_SCHEMA: Final[str] = (
    "qookey-venue-local-liquidation-summary-snapshot-v0.1"
)
ALLOWED_INPUT_CLASS: Final[str] = "synthetic_fixture"
DECISION: Final[str] = "SYNTHETIC_SENSITIVITY_ONLY_NO_WEIGHT"


@dataclass(frozen=True, slots=True)
class LiquidationCoverageSensitivityPolicy:
    synthetic_sensitivity_authorized: bool = True
    real_missingness_estimation_authorized: bool = False
    coverage_weighting_authorized: bool = False
    cross_venue_aggregation_authorized: bool = False
    signal_generation_authorized: bool = False
    strategy_router_integration_authorized: bool = False
    daily_opportunity_integration_authorized: bool = False
    automatic_candidate_generation_authorized: bool = False
    automatic_strategy_selection_authorized: bool = False
    network_capture_authorized: bool = False
    mcp_runtime_authorized: bool = False
    r2_write_authorized: bool = False
    holdout_access_authorized: bool = False
    training_authorized: bool = False
    model_promotion_authorized: bool = False
    formal_trade_plan_authorized: bool = False
    real_money_order_authorized: bool = False
    live_real_trading_authorized: bool = False

    def __post_init__(self) -> None:
        values = (
            self.synthetic_sensitivity_authorized,
            self.real_missingness_estimation_authorized,
            self.coverage_weighting_authorized,
            self.cross_venue_aggregation_authorized,
            self.signal_generation_authorized,
            self.strategy_router_integration_authorized,
            self.daily_opportunity_integration_authorized,
            self.automatic_candidate_generation_authorized,
            self.automatic_strategy_selection_authorized,
            self.network_capture_authorized,
            self.mcp_runtime_authorized,
            self.r2_write_authorized,
            self.holdout_access_authorized,
            self.training_authorized,
            self.model_promotion_authorized,
            self.formal_trade_plan_authorized,
            self.real_money_order_authorized,
            self.live_real_trading_authorized,
        )
        if any(not isinstance(value, bool) for value in values):
            raise ValueError("coverage-sensitivity policy flags must be booleans")
        if not self.synthetic_sensitivity_authorized:
            raise ValueError("V0.1 requires synthetic sensitivity authority")
        if any(values[1:]):
            raise ValueError(
                "Liquidation Coverage Sensitivity V0.1 cannot grant real "
                "missingness estimation, weighting, aggregation, signals, "
                "routing, storage, training or trading authority"
            )


def _number(value: object, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"{label} must be finite")
    return number


def _non_negative(value: object, label: str) -> float:
    number = _number(value, label)
    if number < 0:
        raise ValueError(f"{label} cannot be negative")
    return number


def _non_negative_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _validate_summary(summary: Mapping[str, object], label: str) -> None:
    if summary.get("schema") != INPUT_SCHEMA:
        raise ValueError(f"{label} has unsupported summary schema")
    if summary.get("input_class") != ALLOWED_INPUT_CLASS:
        raise ValueError(
            f"{label} must come from synthetic_fixture input for V0.1"
        )
    if not isinstance(summary.get("symbol"), str) or not summary.get("symbol"):
        raise ValueError(f"{label}.symbol is required")
    if not isinstance(summary.get("venue"), str) or not summary.get("venue"):
        raise ValueError(f"{label}.venue is required")
    _non_negative_int(summary.get("as_of_ms"), f"{label}.as_of_ms")
    _non_negative_int(summary.get("event_count"), f"{label}.event_count")
    for key in (
        "long_liquidated_notional_usd",
        "short_liquidated_notional_usd",
        "gross_liquidated_notional_usd",
        "max_event_notional_usd",
    ):
        _non_negative(summary.get(key), f"{label}.{key}")
    imbalance = _number(summary.get("side_imbalance"), f"{label}.side_imbalance")
    if imbalance < -1.0 or imbalance > 1.0:
        raise ValueError(f"{label}.side_imbalance must be within [-1, 1]")


def _retention(observed: float, reference: float) -> float | None:
    if reference == 0.0:
        return None
    return observed / reference


def assess_liquidation_coverage_sensitivity(
    *,
    reference_summary: Mapping[str, object],
    degraded_summary: Mapping[str, object],
    policy: LiquidationCoverageSensitivityPolicy = LiquidationCoverageSensitivityPolicy(),
) -> dict[str, object]:
    """Compare synthetic full/reference and degraded summaries for one venue."""

    if not policy.synthetic_sensitivity_authorized:
        raise ValueError("synthetic liquidation sensitivity is not authorized")

    _validate_summary(reference_summary, "reference_summary")
    _validate_summary(degraded_summary, "degraded_summary")

    for key in ("symbol", "venue", "as_of_ms", "input_class"):
        if reference_summary.get(key) != degraded_summary.get(key):
            raise ValueError(
                f"reference and degraded summaries must share {key}"
            )

    ref_count = _non_negative_int(
        reference_summary.get("event_count"), "reference event_count"
    )
    obs_count = _non_negative_int(
        degraded_summary.get("event_count"), "degraded event_count"
    )
    if obs_count > ref_count:
        raise ValueError(
            "degraded synthetic fixture cannot contain more events than reference"
        )

    metrics = {}
    for key in (
        "long_liquidated_notional_usd",
        "short_liquidated_notional_usd",
        "gross_liquidated_notional_usd",
        "max_event_notional_usd",
    ):
        ref = _non_negative(reference_summary.get(key), f"reference {key}")
        obs = _non_negative(degraded_summary.get(key), f"degraded {key}")
        metrics[key] = {
            "reference": ref,
            "degraded": obs,
            "absolute_delta": obs - ref,
            "retention_ratio": _retention(obs, ref),
        }

    ref_imbalance = _number(
        reference_summary.get("side_imbalance"), "reference side_imbalance"
    )
    obs_imbalance = _number(
        degraded_summary.get("side_imbalance"), "degraded side_imbalance"
    )

    return {
        "schema": "qookey-liquidation-coverage-sensitivity-result-v0.1",
        "symbol": reference_summary["symbol"],
        "venue": reference_summary["venue"],
        "as_of_ms": reference_summary["as_of_ms"],
        "input_class": ALLOWED_INPUT_CLASS,
        "decision": DECISION,
        "reference_coverage_quality": reference_summary.get("coverage_quality"),
        "degraded_coverage_quality": degraded_summary.get("coverage_quality"),
        "event_count": {
            "reference": ref_count,
            "degraded": obs_count,
            "absolute_delta": obs_count - ref_count,
            "retention_ratio": None if ref_count == 0 else obs_count / ref_count,
        },
        "notional_metrics": metrics,
        "side_imbalance": {
            "reference": ref_imbalance,
            "degraded": obs_imbalance,
            "delta": obs_imbalance - ref_imbalance,
            "sign_changed": (
                ref_imbalance != 0.0
                and obs_imbalance != 0.0
                and (ref_imbalance > 0) != (obs_imbalance > 0)
            ),
        },
        "interpretation": "SYNTHETIC_MISSINGNESS_SENSITIVITY_ONLY",
        "correction_weight": None,
        "estimated_real_missingness_rate": None,
        "authority": {
            "synthetic_sensitivity_only": True,
            "real_missingness_estimation_authorized": False,
            "coverage_weighting_authorized": False,
            "cross_venue_aggregation_authorized": False,
            "signal_generation_authorized": False,
            "strategy_router_integration_authorized": False,
            "daily_opportunity_integration_authorized": False,
            "automatic_candidate_generation_authorized": False,
            "automatic_strategy_selection_authorized": False,
            "network_capture_authorized": False,
            "mcp_runtime_authorized": False,
            "r2_write_authorized": False,
            "holdout_access_authorized": False,
            "training_authorized": False,
            "model_promotion_authorized": False,
            "formal_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_real_trading_authorized": False,
        },
    }


def liquidation_coverage_sensitivity_policy_from_config(
    payload: Mapping[str, object],
) -> LiquidationCoverageSensitivityPolicy:
    if payload.get("schema") != "qookey-liquidation-coverage-sensitivity-v0.1":
        raise ValueError("unsupported liquidation coverage sensitivity config")
    if payload.get("input_schema") != INPUT_SCHEMA:
        raise ValueError("coverage sensitivity input schema mismatch")
    if payload.get("allowed_input_class") != ALLOWED_INPUT_CLASS:
        raise ValueError("coverage sensitivity input class mismatch")
    if payload.get("decision") != DECISION:
        raise ValueError("coverage sensitivity decision mismatch")

    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("coverage sensitivity policy is required")

    keys = (
        "synthetic_sensitivity_authorized",
        "real_missingness_estimation_authorized",
        "coverage_weighting_authorized",
        "cross_venue_aggregation_authorized",
        "signal_generation_authorized",
        "strategy_router_integration_authorized",
        "daily_opportunity_integration_authorized",
        "automatic_candidate_generation_authorized",
        "automatic_strategy_selection_authorized",
        "network_capture_authorized",
        "mcp_runtime_authorized",
        "r2_write_authorized",
        "holdout_access_authorized",
        "training_authorized",
        "model_promotion_authorized",
        "formal_trade_plan_authorized",
        "real_money_order_authorized",
        "live_real_trading_authorized",
    )
    values: dict[str, bool] = {}
    for key in keys:
        value = policy.get(key)
        if not isinstance(value, bool):
            raise ValueError(f"policy.{key} must be a JSON boolean")
        values[key] = value

    return LiquidationCoverageSensitivityPolicy(**values)
