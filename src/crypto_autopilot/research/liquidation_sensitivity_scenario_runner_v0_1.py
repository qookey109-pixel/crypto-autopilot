from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from crypto_autopilot.research.liquidation_coverage_sensitivity_v0_1 import (
    assess_liquidation_coverage_sensitivity,
)
from crypto_autopilot.research.liquidation_synthetic_degradation_v0_1 import (
    degrade_liquidation_snapshot,
)
from crypto_autopilot.research.venue_local_liquidation_summary_v0_1 import (
    ALLOWED_VENUES,
    build_venue_local_liquidation_summary,
)

SCENARIOS = (
    "drop_first",
    "drop_last",
    "drop_largest_long",
    "drop_largest_short",
    "drop_every_second",
    "drop_all_long",
    "drop_all_short",
    "drop_all_events",
)


@dataclass(frozen=True, slots=True)
class LiquidationSensitivityScenarioRunnerPolicy:
    deterministic_scenario_runner_authorized: bool = True
    random_sampling_authorized: bool = False
    real_missingness_estimation_authorized: bool = False
    coverage_weighting_authorized: bool = False
    cross_venue_aggregation_authorized: bool = False
    signal_generation_authorized: bool = False
    strategy_router_integration_authorized: bool = False
    network_capture_authorized: bool = False
    r2_write_authorized: bool = False
    holdout_access_authorized: bool = False
    training_authorized: bool = False
    model_promotion_authorized: bool = False
    real_money_order_authorized: bool = False
    live_real_trading_authorized: bool = False

    def __post_init__(self) -> None:
        values = tuple(getattr(self, name) for name in self.__dataclass_fields__)
        if any(not isinstance(value, bool) for value in values):
            raise ValueError("scenario-runner policy flags must be booleans")
        if not self.deterministic_scenario_runner_authorized:
            raise ValueError("V0.1 requires deterministic scenario-runner authority")
        if any(values[1:]):
            raise ValueError("scenario runner cannot grant random, real-missingness, weighting, aggregation, signal, routing, storage, training or trading authority")


def _venue_events(snapshot: Mapping[str, object], venue: str) -> list[Mapping[str, object]]:
    if snapshot.get("schema") != "qookey-liquidation-quality-context-snapshot-v0.1":
        raise ValueError("unsupported liquidation snapshot schema")
    if snapshot.get("input_class") != "synthetic_fixture":
        raise ValueError("scenario runner accepts synthetic_fixture input only")
    if venue not in ALLOWED_VENUES:
        raise ValueError("unsupported liquidation venue")
    events = snapshot.get("events")
    if not isinstance(events, list):
        raise ValueError("liquidation snapshot events must be an array")
    selected = [row for row in events if isinstance(row, Mapping) and row.get("exchange") == venue]
    if len(selected) < 2:
        raise ValueError("scenario runner requires at least two venue events")
    if not any(row.get("side_semantics") == "LONG_LIQUIDATED" for row in selected):
        raise ValueError("scenario runner requires at least one LONG_LIQUIDATED event")
    if not any(row.get("side_semantics") == "SHORT_LIQUIDATED" for row in selected):
        raise ValueError("scenario runner requires at least one SHORT_LIQUIDATED event")
    return selected


def _largest_index(events: list[Mapping[str, object]], side: str) -> int:
    candidates: list[tuple[float, int]] = []
    for index, row in enumerate(events):
        if row.get("side_semantics") != side:
            continue
        value = row.get("notional_usd")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("notional_usd must be numeric")
        candidates.append((float(value), index))
    return max(candidates, key=lambda item: (item[0], -item[1]))[1]


def _scenario_indices(events: list[Mapping[str, object]]) -> dict[str, list[int]]:
    return {
        "drop_first": [0],
        "drop_last": [len(events) - 1],
        "drop_largest_long": [_largest_index(events, "LONG_LIQUIDATED")],
        "drop_largest_short": [_largest_index(events, "SHORT_LIQUIDATED")],
        "drop_every_second": list(range(1, len(events), 2)),
        "drop_all_long": [i for i, row in enumerate(events) if row.get("side_semantics") == "LONG_LIQUIDATED"],
        "drop_all_short": [i for i, row in enumerate(events) if row.get("side_semantics") == "SHORT_LIQUIDATED"],
        "drop_all_events": list(range(len(events))),
    }


def run_liquidation_sensitivity_scenarios(
    *,
    snapshot: Mapping[str, object],
    venue: str,
    policy: LiquidationSensitivityScenarioRunnerPolicy = LiquidationSensitivityScenarioRunnerPolicy(),
) -> dict[str, object]:
    if not policy.deterministic_scenario_runner_authorized:
        raise ValueError("deterministic scenario runner is not authorized")
    events = _venue_events(snapshot, venue)
    reference = build_venue_local_liquidation_summary(snapshot=snapshot, venue=venue)
    results = []
    for name, indices in _scenario_indices(events).items():
        degraded = degrade_liquidation_snapshot(snapshot=snapshot, venue=venue, drop_event_indices=indices)
        degraded_summary = build_venue_local_liquidation_summary(snapshot=degraded, venue=venue)
        sensitivity = assess_liquidation_coverage_sensitivity(
            reference_summary=reference,
            degraded_summary=degraded_summary,
        )
        results.append({
            "scenario": name,
            "drop_event_indices": indices,
            "degradation_scenario_id": degraded["synthetic_degradation"]["scenario_id"],
            "sensitivity": sensitivity,
        })
    return {
        "schema": "qookey-liquidation-sensitivity-scenario-runner-result-v0.1",
        "symbol": snapshot.get("symbol"),
        "venue": venue,
        "as_of_ms": snapshot.get("as_of_ms"),
        "input_class": "synthetic_fixture",
        "scenario_count": len(results),
        "scenarios": results,
        "random_sampling_used": False,
        "estimated_real_missingness_rate": None,
        "correction_weight": None,
        "interpretation": "DETERMINISTIC_SYNTHETIC_SENSITIVITY_SCENARIOS_ONLY",
        "authority": {
            "deterministic_scenario_runner_only": True,
            "random_sampling_authorized": False,
            "real_missingness_estimation_authorized": False,
            "coverage_weighting_authorized": False,
            "cross_venue_aggregation_authorized": False,
            "signal_generation_authorized": False,
            "strategy_router_integration_authorized": False,
            "network_capture_authorized": False,
            "r2_write_authorized": False,
            "holdout_access_authorized": False,
            "training_authorized": False,
            "model_promotion_authorized": False,
            "real_money_order_authorized": False,
            "live_real_trading_authorized": False,
        },
    }
