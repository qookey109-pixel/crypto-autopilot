from __future__ import annotations

from dataclasses import dataclass

from .binance_funding import funding_partition_receipt_key, funding_r2_key


class BinanceFundingMaterializationPlanError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class FundingAnnualScope:
    symbol: str
    year: int
    months: tuple[int, ...]
    canonical_key: str
    receipt_key: str

    @property
    def source_archive_count(self) -> int:
        return len(self.months)


@dataclass(frozen=True, slots=True)
class FundingMaterializationScope:
    annual_scopes: tuple[FundingAnnualScope, ...]

    @property
    def symbol_count(self) -> int:
        return len({item.symbol for item in self.annual_scopes})

    @property
    def symbol_months(self) -> int:
        return sum(item.source_archive_count for item in self.annual_scopes)

    @property
    def canonical_objects(self) -> int:
        return len(self.annual_scopes)


def _month_range(first: str, last: str) -> tuple[tuple[int, int], ...]:
    try:
        first_year, first_month = (int(part) for part in first.split("-", 1))
        last_year, last_month = (int(part) for part in last.split("-", 1))
    except ValueError as exc:
        raise BinanceFundingMaterializationPlanError("Funding month bounds must be YYYY-MM") from exc
    if not 1 <= first_month <= 12 or not 1 <= last_month <= 12:
        raise BinanceFundingMaterializationPlanError("Funding month bounds contain invalid month")
    if (first_year, first_month) > (last_year, last_month):
        raise BinanceFundingMaterializationPlanError("Funding first month is after last month")
    rows: list[tuple[int, int]] = []
    year, month = first_year, first_month
    while (year, month) <= (last_year, last_month):
        rows.append((year, month))
        month += 1
        if month == 13:
            year += 1
            month = 1
    return tuple(rows)


def validate_plan_config(config: dict[str, object]) -> None:
    if config.get("status") != "PROTOCOL_FROZEN_BEFORE_EXPLICIT_MATERIALIZATION_AUTHORITY":
        raise BinanceFundingMaterializationPlanError("materialization planning protocol must be frozen")
    if config.get("provider") != "binance_usdm" or config.get("delivery") != "binance_vision":
        raise BinanceFundingMaterializationPlanError("Funding materialization provider/delivery mismatch")
    if config.get("dataset") != "fundingRate":
        raise BinanceFundingMaterializationPlanError("Funding materialization dataset changed")
    if int(config.get("candidate_count") or 0) != 15:
        raise BinanceFundingMaterializationPlanError("Funding materialization requires the frozen 15-symbol scope")
    if int(config.get("expected_available_symbol_months") or 0) != 1010:
        raise BinanceFundingMaterializationPlanError("Funding symbol-month scope changed")
    if int(config.get("expected_annual_canonical_objects") or 0) != 95:
        raise BinanceFundingMaterializationPlanError("Funding annual object scope changed")
    if config.get("canonical_partition") != "annual_per_symbol":
        raise BinanceFundingMaterializationPlanError("Funding partition policy changed")
    if config.get("source_checksum_required") is not True:
        raise BinanceFundingMaterializationPlanError("Funding source checksums must remain mandatory")
    if config.get("all_source_archives_must_pass_preflight_before_first_r2_write") is not True:
        raise BinanceFundingMaterializationPlanError("all Funding source archives must pass preflight before writes")
    if config.get("source_archive_revision_policy") != "FAIL_CLOSED_REQUIRE_EXPLICIT_REVIEW":
        raise BinanceFundingMaterializationPlanError("Funding archive revision policy changed")
    if config.get("existing_canonical_object_policy") != "VERIFY_EXACT_OR_FAIL_NO_OVERWRITE":
        raise BinanceFundingMaterializationPlanError("Funding existing canonical object policy changed")
    if config.get("existing_receipt_policy") != "VERIFY_EXACT_OR_FAIL_NO_OVERWRITE":
        raise BinanceFundingMaterializationPlanError("Funding existing receipt policy changed")
    if config.get("raw_funding_timestamp_policy") != "PRESERVE_EXACT_SOURCE_CALC_TIME":
        raise BinanceFundingMaterializationPlanError("Funding raw timestamp policy changed")
    if config.get("source_declared_interval_policy") != "PRESERVE_EXACT_SOURCE_FUNDING_INTERVAL_HOURS":
        raise BinanceFundingMaterializationPlanError("Funding interval policy changed")
    if int(config.get("materialization_cadence_jitter_tolerance_ms") or -1) != 50:
        raise BinanceFundingMaterializationPlanError("Funding materialization cadence tolerance changed")
    if config.get("annual_cross_month_cadence_audit_required") is not True:
        raise BinanceFundingMaterializationPlanError("Funding annual cross-month audit must remain required")
    if config.get("parquet_compression") != "zstd":
        raise BinanceFundingMaterializationPlanError("Funding Parquet compression changed")
    if config.get("preflight_source_archives_stored_in_r2") is not False:
        raise BinanceFundingMaterializationPlanError("Funding source archives must not be retained in R2 by V0.1")
    if int(config.get("planned_global_metadata_objects") or 0) != 4:
        raise BinanceFundingMaterializationPlanError("Funding global metadata object count changed")
    if config.get("writer_must_require_explicit_authority_receipt") is not True:
        raise BinanceFundingMaterializationPlanError("Funding writer must require explicit authority receipt")
    for field in (
        "planning_r2_writes_authorized",
        "funding_materialization_authorized",
        "source_switch_authorized",
        "pionex_native_relabel_authorized",
        "provider_splicing_authorized",
        "historical_universe_membership_authorized",
        "backtest_admission_authorized",
        "trade_plan_authorized",
        "live_trading_authorized",
    ):
        if config.get(field) is not False:
            raise BinanceFundingMaterializationPlanError(f"{field} must remain false during authority planning")


def validate_authorities(
    coverage: dict[str, object],
    budget: dict[str, object],
    source_proof: dict[str, object],
) -> None:
    if coverage.get("status") != "PASS" or coverage.get("stage") != "BINANCE_FUNDING_COVERAGE_DISCOVERY_PASS":
        raise BinanceFundingMaterializationPlanError("Funding coverage authority must PASS")
    if budget.get("status") != "PASS" or budget.get("stage") != "BINANCE_FUNDING_R2_BUDGET_NO_MATERIAL_CHANGE":
        raise BinanceFundingMaterializationPlanError("Funding budget authority must be PASS / NO_MATERIAL_CHANGE")
    if budget.get("determination") != "NO_MATERIAL_BUDGET_CHANGE":
        raise BinanceFundingMaterializationPlanError("Funding budget determination changed")
    if source_proof.get("status") != "PASS" or source_proof.get("stage") != "BINANCE_FUNDING_SOURCE_PROOF_PASS":
        raise BinanceFundingMaterializationPlanError("Funding source proof authority must PASS")
    for authority in (coverage, budget, source_proof):
        boundary = authority.get("authority_boundary") or {}
        if boundary.get("authorizes_live_trading") is not False:
            raise BinanceFundingMaterializationPlanError("upstream Funding authority unexpectedly authorizes live trading")


def build_materialization_scope(coverage: dict[str, object]) -> FundingMaterializationScope:
    scan = coverage.get("scan") or {}
    if int(scan.get("monthly_available_checks") or 0) != 1010:
        raise BinanceFundingMaterializationPlanError("Funding coverage aggregate changed")
    if scan.get("symbols_with_internal_monthly_presence_gap") != []:
        raise BinanceFundingMaterializationPlanError("Funding coverage has internal monthly gaps")
    boundaries = coverage.get("symbol_boundaries") or {}
    if len(boundaries) != 15:
        raise BinanceFundingMaterializationPlanError("Funding coverage must contain 15 symbol boundaries")

    scopes: list[FundingAnnualScope] = []
    total_months = 0
    for symbol in sorted(boundaries):
        boundary = boundaries[symbol]
        if boundary.get("internal_missing_months") != []:
            raise BinanceFundingMaterializationPlanError(f"Funding coverage contains internal gap for {symbol}")
        months = _month_range(
            str(boundary.get("first_available_period") or ""),
            str(boundary.get("last_available_period") or ""),
        )
        if len(months) != int(boundary.get("available_months") or 0):
            raise BinanceFundingMaterializationPlanError(f"Funding available-month count changed for {symbol}")
        total_months += len(months)
        by_year: dict[int, list[int]] = {}
        for year, month in months:
            by_year.setdefault(year, []).append(month)
        for year, year_months in sorted(by_year.items()):
            scopes.append(
                FundingAnnualScope(
                    symbol=symbol,
                    year=year,
                    months=tuple(year_months),
                    canonical_key=funding_r2_key(symbol, year),
                    receipt_key=funding_partition_receipt_key(symbol, year),
                )
            )
    result = FundingMaterializationScope(tuple(scopes))
    if total_months != 1010 or result.symbol_months != 1010:
        raise BinanceFundingMaterializationPlanError("Funding exact symbol-month scope changed")
    if result.canonical_objects != 95:
        raise BinanceFundingMaterializationPlanError("Funding exact annual-object scope changed")
    if result.symbol_count != 15:
        raise BinanceFundingMaterializationPlanError("Funding exact symbol count changed")
    return result
