"""Deterministic capacity planner for a future Pionex 150+ history materialization.

Pure planning only: no provider, R2, holdout, account, training or trading I/O.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping


class HistoryPlanRejected(RuntimeError):
    pass


def validate_config(config: Mapping[str, Any]) -> None:
    if config.get("version") != "0.1.0":
        raise HistoryPlanRejected("unexpected planner config version")
    if config.get("status") != "PREPARED_NOT_EXECUTION_AUTHORITY":
        raise HistoryPlanRejected("planner must remain prepared-only")
    inputs = config.get("inputs")
    planning = config.get("planning")
    authority = config.get("authority")
    if not isinstance(inputs, Mapping) or not isinstance(planning, Mapping):
        raise HistoryPlanRejected("planner inputs/planning missing")
    if inputs.get("required_provider") != "pionex_public_futures":
        raise HistoryPlanRejected("provider scope changed")
    required = ["15M", "60M", "4H", "1D", "1W"]
    if inputs.get("required_intervals") != required:
        raise HistoryPlanRejected("required interval scope changed")
    if planning.get("page_limit") != 500:
        raise HistoryPlanRejected("page limit changed")
    if planning.get("documented_max_records_per_market_interval") != 10_000:
        raise HistoryPlanRejected("record cap changed")
    if planning.get("max_data_pages_per_market_interval") != 20:
        raise HistoryPlanRejected("page budget changed")
    if planning.get("boundary_probe_allowance_per_market_interval") != 1:
        raise HistoryPlanRejected("boundary probe allowance changed")
    if planning.get("derived_1y_provider_native") is not False:
        raise HistoryPlanRejected("1Y cannot be claimed provider-native")
    if planning.get("derived_1y_authorized") is not False:
        raise HistoryPlanRejected("yearly derivation is not authorized here")
    expected_profiles = {
        "FULL_INTRADAY": ["15M", "60M", "4H", "1D", "1W"],
        "MULTISCALE_RESEARCH": ["60M", "4H", "1D", "1W"],
        "BREADTH_BACKGROUND": ["1D", "1W"],
    }
    if planning.get("history_profiles") != expected_profiles:
        raise HistoryPlanRejected("history profile contract changed")
    if not isinstance(authority, Mapping):
        raise HistoryPlanRejected("authority missing")
    for key, value in authority.items():
        if key == "synthetic_fixture_validation":
            if value is not True:
                raise HistoryPlanRejected("synthetic fixture validation must remain enabled")
        elif value is not False:
            raise HistoryPlanRejected(f"planner authority widened: {key}")


def _validate_reach(config: Mapping[str, Any], report: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    inputs = config["inputs"]
    if report.get("schema") != inputs["reach_report_schema"]:
        raise HistoryPlanRejected("unexpected reach report schema")
    if report.get("status") != "PASS":
        raise HistoryPlanRejected("reach report is not PASS")
    if report.get("symbol") != inputs["required_reach_symbol"]:
        raise HistoryPlanRejected("reach report symbol changed")
    if report.get("r2_accessed") is not False or report.get("holdout_accessed") is not False:
        raise HistoryPlanRejected("reach report crossed a forbidden boundary")
    rows = report.get("intervals")
    if not isinstance(rows, list):
        raise HistoryPlanRejected("reach intervals missing")
    by_interval: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise HistoryPlanRejected("invalid reach interval row")
        interval = str(row.get("interval"))
        if interval in by_interval:
            raise HistoryPlanRejected("duplicate reach interval")
        if row.get("classification") not in {
            "PROVIDER_EARLIEST_REACHED",
            "DOCUMENTED_RECORD_CAP_REACHED",
        }:
            raise HistoryPlanRejected("invalid reach classification")
        records = row.get("records_observed")
        if not isinstance(records, int) or not 1 <= records <= 10_000:
            raise HistoryPlanRejected("invalid reference reach record count")
        if row.get("continuity_verified") is not True:
            raise HistoryPlanRejected("reach continuity not verified")
        by_interval[interval] = row
    required = list(inputs["required_intervals"])
    if set(by_interval) != set(required):
        raise HistoryPlanRejected("reach report does not cover exact required intervals")
    return by_interval


def _validate_universe(config: Mapping[str, Any], report: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    inputs = config["inputs"]
    if report.get("schema") != inputs["universe_report_schema"]:
        raise HistoryPlanRejected("unexpected universe report schema")
    if report.get("status") != "PASS":
        raise HistoryPlanRejected("universe report is not PASS")
    if report.get("provider") != inputs["required_provider"]:
        raise HistoryPlanRejected("universe provider changed")
    if report.get("r2_accessed") is not False or report.get("holdout_accessed") is not False:
        raise HistoryPlanRejected("universe report crossed a forbidden boundary")
    markets = report.get("markets")
    if not isinstance(markets, list) or len(markets) < 150:
        raise HistoryPlanRejected("universe must contain at least 150 markets")
    if report.get("selected_market_count") != len(markets):
        raise HistoryPlanRejected("universe market count mismatch")
    symbols: set[str] = set()
    profiles = config["planning"]["history_profiles"]
    normalized: list[Mapping[str, Any]] = []
    for market in markets:
        if not isinstance(market, Mapping):
            raise HistoryPlanRejected("invalid universe market row")
        symbol = str(market.get("symbol") or "")
        profile = str(market.get("history_profile") or "")
        if not symbol or symbol in symbols:
            raise HistoryPlanRejected("missing or duplicate universe symbol")
        if profile not in profiles:
            raise HistoryPlanRejected("unknown history profile")
        symbols.add(symbol)
        normalized.append(market)
    return normalized


def build_plan(
    config: Mapping[str, Any],
    *,
    universe_report: Mapping[str, Any],
    reach_report: Mapping[str, Any],
) -> dict[str, object]:
    validate_config(config)
    reach = _validate_reach(config, reach_report)
    markets = _validate_universe(config, universe_report)
    planning = config["planning"]
    request_per_interval = (
        int(planning["max_data_pages_per_market_interval"])
        + int(planning["boundary_probe_allowance_per_market_interval"])
    )
    profiles = planning["history_profiles"]
    profile_counts = Counter(str(item["history_profile"]) for item in markets)
    output_markets = []
    total_jobs = 0
    total_requests = 0
    for market in markets:
        profile = str(market["history_profile"])
        interval_jobs = []
        for interval in profiles[profile]:
            reference = reach[interval]
            interval_jobs.append(
                {
                    "interval": interval,
                    "max_records_to_attempt": int(planning["documented_max_records_per_market_interval"]),
                    "request_upper_bound": request_per_interval,
                    "btc_reference_classification": reference["classification"],
                    "btc_reference_records_observed": int(reference["records_observed"]),
                    "market_earliest_boundary_proven": False,
                }
            )
        total_jobs += len(interval_jobs)
        market_requests = len(interval_jobs) * request_per_interval
        total_requests += market_requests
        output_markets.append(
            {
                "symbol": market["symbol"],
                "selection_rank": market.get("selection_rank"),
                "history_profile": profile,
                "interval_jobs": interval_jobs,
                "request_upper_bound": market_requests,
            }
        )
    return {
        "status": "PASS",
        "planning_mode": "CAPACITY_ONLY_NO_EXECUTION",
        "selected_market_count": len(markets),
        "history_profile_counts": dict(sorted(profile_counts.items())),
        "market_interval_job_count": total_jobs,
        "request_upper_bound": total_requests,
        "page_limit": planning["page_limit"],
        "documented_record_cap_per_market_interval": planning[
            "documented_max_records_per_market_interval"
        ],
        "btc_reach_used_as_provider_reference_only": True,
        "per_market_listing_history_inferred_from_btc": False,
        "each_market_earliest_boundary_must_be_proven": True,
        "markets": output_markets,
        "derived_1y_authorized": False,
        "provider_requests_performed": 0,
        "r2_accessed": False,
        "holdout_accessed": False,
        "historical_materialization_authorized": False,
        "formal_backtest_admission_authorized": False,
        "real_money_orders_authorized": False,
        "live_trading_authorized": False,
    }
