from __future__ import annotations

import calendar
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable


class BinanceExpansionPlanError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CoverageWindow:
    symbol: str
    earliest_ms: int
    latest_ms: int

    @property
    def earliest(self) -> datetime:
        return datetime.fromtimestamp(self.earliest_ms / 1000, tz=timezone.utc)

    @property
    def latest(self) -> datetime:
        return datetime.fromtimestamp(self.latest_ms / 1000, tz=timezone.utc)


@dataclass(frozen=True, slots=True)
class SymbolYearPlan:
    symbol: str
    year: int
    months: tuple[int, ...]

    @property
    def object_count(self) -> int:
        return len(self.months) + 2

    @property
    def source_archive_count(self) -> int:
        return len(self.months) * 3


@dataclass(frozen=True, slots=True)
class WavePlan:
    wave_id: str
    year: int
    symbol_years: tuple[SymbolYearPlan, ...]
    estimated_rows: int
    estimated_parquet_bytes: int

    @property
    def symbol_count(self) -> int:
        return len(self.symbol_years)

    @property
    def symbol_months(self) -> int:
        return sum(len(item.months) for item in self.symbol_years)

    @property
    def object_count(self) -> int:
        return sum(item.object_count for item in self.symbol_years)

    @property
    def source_archive_count(self) -> int:
        return sum(item.source_archive_count for item in self.symbol_years)


def validate_config(config: dict[str, object]) -> None:
    if config.get("status") != "PROTOCOL_FROZEN_BEFORE_PLANNING":
        raise BinanceExpansionPlanError("planning protocol must be frozen before planning")
    if config.get("provider") != "binance_usdm" or config.get("delivery") != "binance_vision":
        raise BinanceExpansionPlanError("provider/delivery mismatch")
    if int(config.get("candidate_count") or 0) != 15:
        raise BinanceExpansionPlanError("V0.1 planning requires the frozen 15-market candidate universe")
    if config.get("planning_scope") != "trade_klines_only":
        raise BinanceExpansionPlanError("V0.1 planning scope must remain trade_klines_only")
    if tuple(config.get("project_intervals") or ()) != ("15M", "60M", "4H"):
        raise BinanceExpansionPlanError("project intervals changed")
    if tuple(config.get("source_intervals") or ()) != ("15m", "1h", "4h"):
        raise BinanceExpansionPlanError("source intervals changed")
    if config.get("current_incomplete_year_policy") != "DEFER":
        raise BinanceExpansionPlanError("current incomplete year must remain deferred")
    for field in (
        "source_switch_authorized",
        "large_scale_backfill_authorized",
        "r2_writes_authorized",
        "pionex_native_relabel_authorized",
        "provider_splicing_authorized",
        "silent_interpolation_authorized",
        "trade_plan_authorized",
        "live_trading_authorized",
    ):
        if config.get(field) is not False:
            raise BinanceExpansionPlanError(f"{field} must remain false")


def load_coverage_windows(payload: dict[str, object]) -> tuple[CoverageWindow, ...]:
    if payload.get("status") != "PASS" or payload.get("stage") != "BINANCE_MAX_COVERAGE_DISCOVERY_PASS":
        raise BinanceExpansionPlanError("coverage authority must be BINANCE_MAX_COVERAGE_DISCOVERY_PASS")
    if payload.get("provider") != "binance_usdm" or payload.get("delivery") != "binance_vision":
        raise BinanceExpansionPlanError("coverage authority provider/delivery mismatch")
    if int(payload.get("candidate_count") or 0) != 15:
        raise BinanceExpansionPlanError("coverage authority must contain 15 candidates")
    boundary = payload.get("authority_boundary") or {}
    if boundary.get("authorizes_source_switch") is not False:
        raise BinanceExpansionPlanError("coverage authority must not authorize source switching")
    if boundary.get("authorizes_large_scale_backfill") is not False:
        raise BinanceExpansionPlanError("coverage authority must not authorize large-scale backfill")

    rows = payload.get("strategy_price_common_windows") or []
    windows: list[CoverageWindow] = []
    for row in rows:
        windows.append(
            CoverageWindow(
                symbol=str(row["symbol"]),
                earliest_ms=int(row["earliest_candle_time_ms"]),
                latest_ms=int(row["latest_candle_time_ms"]),
            )
        )
    if len(windows) != 15 or len({item.symbol for item in windows}) != 15:
        raise BinanceExpansionPlanError("coverage authority must contain 15 unique strategy-price windows")
    return tuple(sorted(windows, key=lambda item: item.symbol))


def load_capacity_basis(payload: dict[str, object]) -> tuple[int, float, float, float]:
    if payload.get("status") != "PASS" or payload.get("stage") != "BINANCE_OBSERVED_R2_BUDGET_GATE_PASS":
        raise BinanceExpansionPlanError("capacity authority must be BINANCE_OBSERVED_R2_BUDGET_GATE_PASS")
    basis = payload.get("basis") or {}
    projection = payload.get("storage_projection") or {}
    rows_per_full_market_year = int(basis.get("rows_per_full_market_year") or 0)
    bytes_per_row = float(basis.get("observed_bytes_per_row") or 0.0)
    canonical = float(projection.get("canonical_only_gb_month") or 0.0)
    canonical_plus_staging = float(projection.get("canonical_plus_retained_staging_gb_month") or 0.0)
    stress = float(projection.get("three_x_capacity_stress_gb_month") or 0.0)
    if rows_per_full_market_year <= 0 or bytes_per_row <= 0 or canonical <= 0:
        raise BinanceExpansionPlanError("invalid observed capacity basis")
    staging_multiplier = canonical_plus_staging / canonical
    stress_multiplier = stress / canonical
    if staging_multiplier < 1.0 or stress_multiplier < staging_multiplier:
        raise BinanceExpansionPlanError("invalid storage multipliers")
    return rows_per_full_market_year, bytes_per_row, staging_multiplier, stress_multiplier


def validate_existing_2025(payload: dict[str, object]) -> None:
    if payload.get("status") != "PASS" or payload.get("stage") != "BINANCE_2025_R2_PILOT_PASS":
        raise BinanceExpansionPlanError("existing 2025 materialization authority must PASS")
    if int(payload.get("year") or 0) != 2025:
        raise BinanceExpansionPlanError("existing materialization authority must be 2025")
    if int(payload.get("object_count") or 0) != 206:
        raise BinanceExpansionPlanError("existing 2025 authority object count mismatch")
    if payload.get("pionex_namespace_touched") is not False:
        raise BinanceExpansionPlanError("existing Binance materialization touched Pionex namespace")


def _last_complete_month(payload: dict[str, object]) -> tuple[int, int]:
    protocol = payload.get("protocol") or {}
    text = str(protocol.get("last_complete_month_scanned") or "")
    try:
        year_text, month_text = text.split("-", 1)
        year, month = int(year_text), int(month_text)
    except ValueError as exc:
        raise BinanceExpansionPlanError("invalid last_complete_month_scanned") from exc
    if month < 1 or month > 12:
        raise BinanceExpansionPlanError("invalid last complete month")
    return year, month


def months_for_year(window: CoverageWindow, year: int, *, last_complete: tuple[int, int]) -> tuple[int, ...]:
    earliest = window.earliest
    latest = window.latest
    if year < earliest.year or year > latest.year:
        return ()
    start_month = earliest.month if year == earliest.year else 1
    end_month = latest.month if year == latest.year else 12
    last_year, last_month = last_complete
    if year > last_year:
        return ()
    if year == last_year:
        end_month = min(end_month, last_month)
    if start_month > end_month:
        return ()
    return tuple(range(start_month, end_month + 1))


def build_waves(
    coverage_payload: dict[str, object],
    windows: tuple[CoverageWindow, ...],
    *,
    already_materialized_years: Iterable[int],
    rows_per_full_market_year: int,
    bytes_per_row: float,
) -> tuple[WavePlan, ...]:
    last_complete = _last_complete_month(coverage_payload)
    complete_year_ceiling = last_complete[0] - 1 if last_complete[1] < 12 else last_complete[0]
    materialized = set(int(year) for year in already_materialized_years)
    earliest_observed_year = min(window.earliest.year for window in windows)

    candidate_years = [
        year
        for year in range(complete_year_ceiling, earliest_observed_year - 1, -1)
        if year not in materialized
    ]
    waves: list[WavePlan] = []
    for index, year in enumerate(candidate_years, start=1):
        symbol_years = tuple(
            SymbolYearPlan(symbol=window.symbol, year=year, months=months)
            for window in windows
            if (months := months_for_year(window, year, last_complete=last_complete))
        )
        if not symbol_years:
            continue
        symbol_months = sum(len(item.months) for item in symbol_years)
        estimated_rows = math.ceil(rows_per_full_market_year * symbol_months / 12)
        estimated_bytes = math.ceil(estimated_rows * bytes_per_row)
        waves.append(
            WavePlan(
                wave_id=f"W{index}",
                year=year,
                symbol_years=symbol_years,
                estimated_rows=estimated_rows,
                estimated_parquet_bytes=estimated_bytes,
            )
        )
    return tuple(waves)


def days_covered(item: SymbolYearPlan) -> int:
    return sum(calendar.monthrange(item.year, month)[1] for month in item.months)
