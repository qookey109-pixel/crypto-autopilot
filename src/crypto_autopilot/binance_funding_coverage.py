from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable


class BinanceFundingCoverageError(RuntimeError):
    pass


def validate_funding_coverage_config(config: dict[str, object]) -> None:
    if config.get("status") != "PROTOCOL_FROZEN_BEFORE_DISCOVERY":
        raise BinanceFundingCoverageError("Funding coverage protocol must be frozen before discovery")
    if config.get("provider") != "binance_usdm" or config.get("delivery") != "binance_vision":
        raise BinanceFundingCoverageError("Funding coverage provider/delivery mismatch")
    if config.get("dataset") != "fundingRate" or config.get("archive_frequency") != "monthly":
        raise BinanceFundingCoverageError("Funding coverage must remain monthly fundingRate")
    if int(config.get("candidate_count") or 0) != 15:
        raise BinanceFundingCoverageError("Funding coverage V0.1 requires the frozen 15-market universe")
    if int(config.get("project_history_cap_years") or 0) != 8:
        raise BinanceFundingCoverageError("Funding coverage history cap changed")
    if config.get("scan_floor_policy") != "PROJECT_HISTORY_CAP_ONLY":
        raise BinanceFundingCoverageError("Funding coverage may not assume a provider onset month")
    if config.get("provider_earliest_month_assumption") is not None:
        raise BinanceFundingCoverageError("provider earliest month must remain unassumed")
    if config.get("current_incomplete_month_policy") != "DEFER":
        raise BinanceFundingCoverageError("current incomplete month must remain deferred")
    if config.get("edge_content_audit_policy") != "FIRST_AND_LAST_AVAILABLE_MONTH_PER_SYMBOL":
        raise BinanceFundingCoverageError("Funding edge audit policy changed")
    if config.get("interior_policy") != "CHECKSUM_PRESENCE_ONLY":
        raise BinanceFundingCoverageError("Funding interior policy changed")
    if config.get("funding_onset_may_be_inferred_from_trade_onset") is not False:
        raise BinanceFundingCoverageError("Funding onset must not be inferred from Trade onset")
    if config.get("archive_presence_is_listing_authority") is not False:
        raise BinanceFundingCoverageError("archive presence must not be listing authority")
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
            raise BinanceFundingCoverageError(f"{field} must remain false during coverage discovery")


def validate_source_proof_authority(payload: dict[str, object]) -> None:
    if payload.get("status") != "PASS" or payload.get("stage") != "BINANCE_FUNDING_SOURCE_PROOF_PASS":
        raise BinanceFundingCoverageError("Funding source proof authority must PASS")
    if payload.get("provider") != "binance_usdm" or payload.get("delivery") != "binance_vision":
        raise BinanceFundingCoverageError("Funding source proof provider/delivery mismatch")
    if payload.get("dataset") != "fundingRate" or payload.get("frequency") != "monthly":
        raise BinanceFundingCoverageError("Funding source proof dataset/frequency mismatch")
    boundary = payload.get("authority_boundary") or {}
    for field in (
        "authorizes_funding_r2_writes",
        "authorizes_source_switch",
        "authorizes_provider_splicing",
        "authorizes_pionex_native_relabeling",
        "authorizes_backtest_admission",
        "authorizes_live_trading",
    ):
        if boundary.get(field) is not False:
            raise BinanceFundingCoverageError(f"source proof unexpectedly authorizes {field}")


def summarize_funding_presence(
    records: Iterable[dict[str, object]],
    *,
    symbol: str,
    ordered_periods: tuple[str, ...],
) -> dict[str, object]:
    selected = [record for record in records if record.get("symbol") == symbol]
    by_period: dict[str, dict[str, object]] = {}
    for record in selected:
        period = str(record.get("period") or "")
        if period in by_period:
            raise BinanceFundingCoverageError(f"duplicate Funding coverage record: {symbol} {period}")
        by_period[period] = record
    if set(by_period) != set(ordered_periods):
        missing = sorted(set(ordered_periods) - set(by_period))
        extra = sorted(set(by_period) - set(ordered_periods))
        raise BinanceFundingCoverageError(
            f"Funding coverage record period mismatch for {symbol}: missing={missing} extra={extra}"
        )
    statuses = {str(record.get("status")) for record in selected}
    if not statuses.issubset({"AVAILABLE", "NO_DATA"}):
        raise BinanceFundingCoverageError(f"unsupported Funding coverage status for {symbol}: {statuses}")

    available_periods = [
        period for period in ordered_periods if by_period[period]["status"] == "AVAILABLE"
    ]
    no_data_periods = [period for period in ordered_periods if by_period[period]["status"] == "NO_DATA"]
    if available_periods:
        first_index = ordered_periods.index(available_periods[0])
        last_index = ordered_periods.index(available_periods[-1])
        observed_span = ordered_periods[first_index : last_index + 1]
        missing_within_span = [
            period for period in observed_span if by_period[period]["status"] == "NO_DATA"
        ]
    else:
        missing_within_span = []

    return {
        "symbol": symbol,
        "dataset": "fundingRate",
        "frequency": "monthly",
        "available_periods": available_periods,
        "no_data_periods": no_data_periods,
        "available_count": len(available_periods),
        "no_data_count": len(no_data_periods),
        "first_available_period": available_periods[0] if available_periods else None,
        "last_available_period": available_periods[-1] if available_periods else None,
        "missing_periods_within_observed_span": missing_within_span,
        "continuous_archive_presence_within_observed_span": not missing_within_span,
    }


def ms_to_iso(value: int | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()


def attach_funding_boundaries(
    summary: dict[str, object],
    *,
    first_receipt: dict[str, object] | None,
    last_receipt: dict[str, object] | None,
) -> dict[str, object]:
    result = dict(summary)
    if first_receipt is None and last_receipt is None:
        result.update(
            {
                "earliest_funding_time_ms": None,
                "earliest_funding_time_utc": None,
                "latest_funding_time_ms": None,
                "latest_funding_time_utc": None,
                "observed_edge_interval_hours": [],
                "audited_first_archive": None,
                "audited_last_archive": None,
            }
        )
        return result
    if first_receipt is None or last_receipt is None:
        raise BinanceFundingCoverageError("available Funding span requires both first and last edge receipts")
    if first_receipt.get("audit_ok") is not True or last_receipt.get("audit_ok") is not True:
        raise BinanceFundingCoverageError("Funding edge receipts must pass content audit")
    first_ms = int(first_receipt["first_time_ms"])
    last_ms = int(last_receipt["last_time_ms"])
    if first_ms > last_ms:
        raise BinanceFundingCoverageError("Funding audited boundaries are reversed")
    intervals = sorted(
        {
            int(value)
            for receipt in (first_receipt, last_receipt)
            for value in (receipt.get("interval_hours") or [])
        }
    )
    result.update(
        {
            "earliest_funding_time_ms": first_ms,
            "earliest_funding_time_utc": ms_to_iso(first_ms),
            "latest_funding_time_ms": last_ms,
            "latest_funding_time_utc": ms_to_iso(last_ms),
            "observed_edge_interval_hours": intervals,
            "audited_first_archive": first_receipt,
            "audited_last_archive": last_receipt,
        }
    )
    return result
