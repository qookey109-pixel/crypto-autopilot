from __future__ import annotations

import calendar
import math
from dataclasses import dataclass


class BinanceFundingBudgetError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class FundingBudgetProjection:
    available_symbol_months: int
    available_calendar_days: int
    annual_canonical_objects: int
    minimum_budget_interval_hours: int
    projected_rows: int
    calibration_max_bytes_per_row: float
    canonical_bytes: int
    canonical_gb: float
    canonical_plus_staging_gb: float
    three_x_capacity_stress_gb: float
    planned_class_a_requests: int
    planned_class_b_requests: int
    three_x_class_a_requests: int
    three_x_class_b_requests: int
    combined_trade_plus_funding_three_x_storage_gb: float
    combined_trade_plus_funding_three_x_class_a_requests: int
    combined_trade_plus_funding_three_x_class_b_requests: int
    material_budget_change: bool


def _month_range(first: str, last: str) -> tuple[tuple[int, int], ...]:
    try:
        first_year, first_month = (int(part) for part in first.split("-", 1))
        last_year, last_month = (int(part) for part in last.split("-", 1))
    except ValueError as exc:
        raise BinanceFundingBudgetError("Funding month bounds must be YYYY-MM") from exc
    if not 1 <= first_month <= 12 or not 1 <= last_month <= 12:
        raise BinanceFundingBudgetError("Funding month bounds contain invalid month")
    if (first_year, first_month) > (last_year, last_month):
        raise BinanceFundingBudgetError("Funding first month is after last month")
    rows: list[tuple[int, int]] = []
    year, month = first_year, first_month
    while (year, month) <= (last_year, last_month):
        rows.append((year, month))
        month += 1
        if month == 13:
            year += 1
            month = 1
    return tuple(rows)


def coverage_shape(coverage_authority: dict[str, object]) -> tuple[int, int, int]:
    if coverage_authority.get("status") != "PASS" or coverage_authority.get("stage") != "BINANCE_FUNDING_COVERAGE_DISCOVERY_PASS":
        raise BinanceFundingBudgetError("Funding coverage authority must PASS")
    scan = coverage_authority.get("scan") or {}
    if int(scan.get("symbols_with_observed_funding_coverage") or 0) != 15:
        raise BinanceFundingBudgetError("Funding coverage authority must contain all 15 observed symbols")
    if scan.get("symbols_with_internal_monthly_presence_gap") != []:
        raise BinanceFundingBudgetError("Funding coverage contains internal monthly presence gaps")
    if int(scan.get("monthly_available_checks") or 0) != 1010:
        raise BinanceFundingBudgetError("Funding available symbol-month count changed")

    boundaries = coverage_authority.get("symbol_boundaries") or {}
    if len(boundaries) != 15:
        raise BinanceFundingBudgetError("Funding coverage must contain 15 symbol boundaries")

    total_months = 0
    total_days = 0
    annual_objects = 0
    for symbol, boundary in boundaries.items():
        first = str(boundary.get("first_available_period") or "")
        last = str(boundary.get("last_available_period") or "")
        months = _month_range(first, last)
        if len(months) != int(boundary.get("available_months") or 0):
            raise BinanceFundingBudgetError(f"Funding available month mismatch for {symbol}")
        if boundary.get("internal_missing_months") != []:
            raise BinanceFundingBudgetError(f"Funding internal gaps present for {symbol}")
        total_months += len(months)
        total_days += sum(calendar.monthrange(year, month)[1] for year, month in months)
        annual_objects += len({year for year, _ in months})

    if total_months != int(scan["monthly_available_checks"]):
        raise BinanceFundingBudgetError("Funding boundary months do not match scan aggregate")
    return total_months, total_days, annual_objects


def validate_budget_config(config: dict[str, object]) -> None:
    if config.get("status") != "PROTOCOL_FROZEN_BEFORE_BUDGET_MEASUREMENT":
        raise BinanceFundingBudgetError("Funding budget protocol must be frozen before measurement")
    if config.get("provider") != "binance_usdm" or config.get("dataset") != "fundingRate":
        raise BinanceFundingBudgetError("Funding budget provider/dataset mismatch")
    if config.get("bytes_per_row_policy") != "MAX_OF_PROOF_SYMBOL_MONTH_PARQUET_BYTES_PER_ROW":
        raise BinanceFundingBudgetError("Funding bytes-per-row policy changed")
    if config.get("row_projection_policy") != "ASSUME_ONE_HOUR_FUNDING_FOR_EVERY_CALENDAR_HOUR_IN_EVERY_AVAILABLE_MONTH":
        raise BinanceFundingBudgetError("Funding row projection policy changed")
    if int(config.get("minimum_funding_interval_hours_for_budget") or 0) != 1:
        raise BinanceFundingBudgetError("Funding budget minimum interval must remain one hour")
    if float(config.get("retained_staging_multiplier") or 0.0) != 2.0:
        raise BinanceFundingBudgetError("Funding staging multiplier changed")
    if float(config.get("capacity_stress_multiplier") or 0.0) != 3.0:
        raise BinanceFundingBudgetError("Funding capacity stress multiplier changed")
    if int(config.get("operation_stress_multiplier") or 0) != 3:
        raise BinanceFundingBudgetError("Funding operation stress multiplier changed")
    for field in (
        "source_switch_authorized",
        "r2_writes_authorized",
        "funding_materialization_authorized",
        "pionex_native_relabel_authorized",
        "provider_splicing_authorized",
        "backtest_admission_authorized",
        "trade_plan_authorized",
        "live_trading_authorized",
    ):
        if config.get(field) is not False:
            raise BinanceFundingBudgetError(f"{field} must remain false during budget determination")


def project_funding_budget(
    *,
    coverage_authority: dict[str, object],
    calibration_max_bytes_per_row: float,
    trade_three_x_storage_gb: float,
    trade_three_x_class_a_requests: int,
    trade_three_x_class_b_requests: int,
    storage_warn_gb: float,
    class_a_warn_requests: int,
    class_b_warn_requests: int,
    minimum_budget_interval_hours: int = 1,
    retained_staging_multiplier: float = 2.0,
    capacity_stress_multiplier: float = 3.0,
    operation_stress_multiplier: int = 3,
) -> FundingBudgetProjection:
    if minimum_budget_interval_hours != 1:
        raise BinanceFundingBudgetError("V0.1 Funding budget projection must remain one-hour conservative")
    if not math.isfinite(calibration_max_bytes_per_row) or calibration_max_bytes_per_row <= 0:
        raise BinanceFundingBudgetError("Funding calibration bytes-per-row must be finite and positive")
    if retained_staging_multiplier != 2.0 or capacity_stress_multiplier != 3.0 or operation_stress_multiplier != 3:
        raise BinanceFundingBudgetError("Funding budget stress multipliers changed")

    months, days, annual_objects = coverage_shape(coverage_authority)
    projected_rows = days * (24 // minimum_budget_interval_hours)
    canonical_bytes = math.ceil(projected_rows * calibration_max_bytes_per_row)
    canonical_gb = canonical_bytes / 1_000_000_000.0
    plus_staging = canonical_gb * retained_staging_multiplier
    stress_storage = canonical_gb * capacity_stress_multiplier

    planned_class_a = annual_objects * 2 + 4
    planned_class_b = annual_objects * 2 + 4
    stress_class_a = planned_class_a * operation_stress_multiplier
    stress_class_b = planned_class_b * operation_stress_multiplier

    combined_storage = trade_three_x_storage_gb + stress_storage
    combined_class_a = trade_three_x_class_a_requests + stress_class_a
    combined_class_b = trade_three_x_class_b_requests + stress_class_b
    material = (
        combined_storage >= storage_warn_gb
        or combined_class_a >= class_a_warn_requests
        or combined_class_b >= class_b_warn_requests
    )

    return FundingBudgetProjection(
        available_symbol_months=months,
        available_calendar_days=days,
        annual_canonical_objects=annual_objects,
        minimum_budget_interval_hours=minimum_budget_interval_hours,
        projected_rows=projected_rows,
        calibration_max_bytes_per_row=calibration_max_bytes_per_row,
        canonical_bytes=canonical_bytes,
        canonical_gb=canonical_gb,
        canonical_plus_staging_gb=plus_staging,
        three_x_capacity_stress_gb=stress_storage,
        planned_class_a_requests=planned_class_a,
        planned_class_b_requests=planned_class_b,
        three_x_class_a_requests=stress_class_a,
        three_x_class_b_requests=stress_class_b,
        combined_trade_plus_funding_three_x_storage_gb=combined_storage,
        combined_trade_plus_funding_three_x_class_a_requests=combined_class_a,
        combined_trade_plus_funding_three_x_class_b_requests=combined_class_b,
        material_budget_change=material,
    )
