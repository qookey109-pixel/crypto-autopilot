from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from crypto_autopilot.binance_expansion_plan import load_coverage_windows, months_for_year


class HistoricalUniverseLongHorizonReviewError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ReviewedSymbolScope:
    symbol: str
    year: int
    months: tuple[int, ...]

    @property
    def full_year(self) -> bool:
        return self.months == tuple(range(1, 13))


@dataclass(frozen=True, slots=True)
class LongHorizonReviewResult:
    target_wave: str
    target_year: int
    scopes: tuple[ReviewedSymbolScope, ...]
    excluded_symbols: tuple[str, ...]

    @property
    def symbol_count(self) -> int:
        return len(self.scopes)

    @property
    def symbol_months(self) -> int:
        return sum(len(scope.months) for scope in self.scopes)

    @property
    def full_year_symbol_count(self) -> int:
        return sum(scope.full_year for scope in self.scopes)


def validate_review_config(config: dict[str, Any]) -> None:
    if config.get("status") != "PROTOCOL_FROZEN_BEFORE_REVIEW":
        raise HistoricalUniverseLongHorizonReviewError("review protocol must be frozen before review")
    if config.get("execution_exchange") != "pionex":
        raise HistoricalUniverseLongHorizonReviewError("execution exchange must remain pionex")
    if config.get("research_provider") != "binance_usdm":
        raise HistoricalUniverseLongHorizonReviewError("research provider must remain binance_usdm")
    if config.get("market_type") != "perp":
        raise HistoricalUniverseLongHorizonReviewError("market type must remain perp")
    if tuple(config.get("required_intervals") or ()) != ("15M", "60M", "4H"):
        raise HistoricalUniverseLongHorizonReviewError("required intervals changed")

    review_policy = config.get("review_policy") or {}
    required_false = (
        "coverage_receipt_is_backtest_membership_authority",
        "first_observed_candle_is_listing_authority",
        "future_binance_partition_records_native_to_pionex",
        "pionex_current_universe_backprojection_allowed",
        "provider_splicing_allowed",
        "silent_interpolation_allowed",
    )
    for field in required_false:
        if review_policy.get(field) is not False:
            raise HistoricalUniverseLongHorizonReviewError(f"review policy {field} must remain false")
    required_true = (
        "verified_partition_receipts_required_before_membership",
        "all_three_intervals_required_before_default_membership",
        "acquisition_scope_may_be_reviewed_before_partition_materialization",
    )
    for field in required_true:
        if review_policy.get(field) is not True:
            raise HistoricalUniverseLongHorizonReviewError(f"review policy {field} must remain true")

    record_policy = config.get("post_materialization_record_policy") or {}
    if record_policy.get("provider") != "binance_usdm":
        raise HistoricalUniverseLongHorizonReviewError("future record provider must remain binance_usdm")
    if record_policy.get("market_type") != "perp":
        raise HistoricalUniverseLongHorizonReviewError("future record market type must remain perp")
    if record_policy.get("native") is not False:
        raise HistoricalUniverseLongHorizonReviewError("Binance research records must remain proxy/non-native to Pionex")
    if record_policy.get("evidence_type") != "verified_partition_receipt":
        raise HistoricalUniverseLongHorizonReviewError("future membership evidence must be verified partition receipts")
    for field in ("audit_ok_required", "actual_first_last_required", "source_sha256_required"):
        if record_policy.get(field) is not True:
            raise HistoricalUniverseLongHorizonReviewError(f"record policy {field} must remain true")

    for field in (
        "source_switch_authorized",
        "wave_materialization_authorized",
        "backtest_admission_authorized",
        "pionex_native_relabel_authorized",
        "trade_plan_authorized",
        "live_trading_authorized",
    ):
        if config.get(field) is not False:
            raise HistoricalUniverseLongHorizonReviewError(f"{field} must remain false")


def validate_staged_plan_authority(payload: dict[str, Any], *, target_wave: str, target_year: int) -> dict[str, Any]:
    if payload.get("status") != "PASS" or payload.get("stage") != "BINANCE_STAGED_MULTIYEAR_EXPANSION_PLAN_PASS":
        raise HistoricalUniverseLongHorizonReviewError("staged plan authority must PASS")
    if payload.get("provider") != "binance_usdm" or payload.get("execution_exchange") != "pionex":
        raise HistoricalUniverseLongHorizonReviewError("staged plan provider/execution boundary mismatch")
    boundary = payload.get("authority_boundary") or {}
    if boundary.get("authorizes_any_wave_materialization") is not False:
        raise HistoricalUniverseLongHorizonReviewError("staged plan must not already authorize materialization")
    waves = (payload.get("planning_result") or {}).get("waves") or []
    matches = [wave for wave in waves if wave.get("wave_id") == target_wave]
    if len(matches) != 1:
        raise HistoricalUniverseLongHorizonReviewError("target wave must exist exactly once")
    wave = matches[0]
    if int(wave.get("year") or 0) != target_year:
        raise HistoricalUniverseLongHorizonReviewError("target wave year mismatch")
    if wave.get("materialization_authorized") is not False:
        raise HistoricalUniverseLongHorizonReviewError("target wave must remain unauthorized")
    return wave


def review_target_wave(
    coverage_payload: dict[str, Any],
    staged_plan_payload: dict[str, Any],
    config: dict[str, Any],
) -> LongHorizonReviewResult:
    validate_review_config(config)
    target_wave = str(config["target_wave"])
    target_year = int(config["target_year"])
    planned_wave = validate_staged_plan_authority(
        staged_plan_payload,
        target_wave=target_wave,
        target_year=target_year,
    )

    windows = load_coverage_windows(coverage_payload)
    protocol = coverage_payload.get("protocol") or {}
    text = str(protocol.get("last_complete_month_scanned") or "")
    try:
        last_year_text, last_month_text = text.split("-", 1)
        last_complete = (int(last_year_text), int(last_month_text))
    except ValueError as exc:
        raise HistoricalUniverseLongHorizonReviewError("invalid coverage last_complete_month_scanned") from exc

    scopes: list[ReviewedSymbolScope] = []
    excluded: list[str] = []
    for window in windows:
        months = months_for_year(window, target_year, last_complete=last_complete)
        if months:
            scopes.append(ReviewedSymbolScope(window.symbol, target_year, months))
        else:
            excluded.append(window.symbol)

    result = LongHorizonReviewResult(
        target_wave=target_wave,
        target_year=target_year,
        scopes=tuple(sorted(scopes, key=lambda item: item.symbol)),
        excluded_symbols=tuple(sorted(excluded)),
    )
    if result.symbol_count != int(planned_wave.get("symbol_count") or -1):
        raise HistoricalUniverseLongHorizonReviewError("review symbol count disagrees with staged plan authority")
    if result.symbol_months != int(planned_wave.get("symbol_months") or -1):
        raise HistoricalUniverseLongHorizonReviewError("review symbol-month count disagrees with staged plan authority")
    return result


def build_membership_contract(config: dict[str, Any]) -> dict[str, Any]:
    validate_review_config(config)
    record_policy = config["post_materialization_record_policy"]
    return {
        "provider": record_policy["provider"],
        "market_type": record_policy["market_type"],
        "required_intervals": list(config["required_intervals"]),
        "native": record_policy["native"],
        "evidence_type": record_policy["evidence_type"],
        "audit_ok_required": record_policy["audit_ok_required"],
        "actual_first_last_required": record_policy["actual_first_last_required"],
        "source_sha256_required": record_policy["source_sha256_required"],
        "coverage_receipt_can_create_membership": False,
        "first_observed_candle_can_create_listing_authority": False,
        "pionex_provider_record_creation_allowed": False,
        "native_pionex_backtest_admission_authorized": False,
    }
