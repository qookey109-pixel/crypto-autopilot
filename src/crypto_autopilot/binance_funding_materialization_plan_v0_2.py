from __future__ import annotations

import hashlib
import json

from .binance_funding_materialization_plan import (
    BinanceFundingMaterializationPlanError,
    FundingMaterializationScope,
    build_materialization_scope,
    validate_authorities,
)


class BinanceFundingMaterializationPlanV02Error(BinanceFundingMaterializationPlanError):
    pass


def validate_v0_2_config(config: dict[str, object]) -> None:
    if config.get("version") != "0.2.0":
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 config version changed")
    if config.get("status") != "PROTOCOL_FROZEN_BEFORE_EXPLICIT_MATERIALIZATION_AUTHORITY":
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 protocol must be frozen")
    if config.get("provider") != "binance_usdm" or config.get("delivery") != "binance_vision":
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 provider/delivery changed")
    if config.get("dataset") != "fundingRate":
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 dataset changed")
    if int(config.get("candidate_count") or 0) != 15:
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 candidate count changed")
    if int(config.get("coverage_available_symbol_months") or 0) != 1010:
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 coverage count changed")
    if int(config.get("expected_materialized_symbol_months") or 0) != 1003:
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 materialized month target changed")
    if int(config.get("expected_annual_canonical_objects") or 0) != 94:
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 annual object target changed")
    if int(config.get("expected_annual_partition_receipts") or 0) != 94:
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 receipt target changed")
    if int(config.get("planned_global_metadata_objects") or 0) != 4:
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 metadata object count changed")
    if int(config.get("expected_total_r2_object_identities") or 0) != 192:
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 R2 identity target changed")
    if config.get("canonical_partition") != "annual_per_symbol":
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 canonical partition changed")
    deferred = config.get("deferred_annual_partitions") or []
    if deferred != [
        {
            "symbol": "HYPEUSDT",
            "year": 2026,
            "source_months": [1, 2, 3, 4, 5, 6, 7],
            "reason": "unresolved provider-archive declared-cadence discontinuity in HYPEUSDT 2026-06",
        }
    ]:
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 deferred partition policy changed")
    if config.get("expected_canonical_scope_sha256") != "1e0ff54daeec8e5e47376fedb631c663687dd6fb6a4c297d269c33acdf99ad58":
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 expected scope SHA changed")
    if config.get("expected_source_checksum_set_sha256") != "881c14d3b3c780b8a0d56ca2f7fd57d2abff310fcd7cb4b13dc01f506b9b64f3":
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 expected checksum-set SHA changed")
    if int(config.get("materialization_cadence_jitter_tolerance_ms") or -1) != 50:
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 cadence tolerance changed")
    if config.get("source_archive_revision_policy") != "FAIL_CLOSED_REQUIRE_EXPLICIT_REVIEW":
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 revision policy changed")
    if config.get("existing_canonical_object_policy") != "VERIFY_EXACT_OR_FAIL_NO_OVERWRITE":
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 canonical object policy changed")
    if config.get("existing_receipt_policy") != "VERIFY_EXACT_OR_FAIL_NO_OVERWRITE":
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 receipt policy changed")
    if config.get("raw_funding_timestamp_policy") != "PRESERVE_EXACT_SOURCE_CALC_TIME":
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 raw timestamp policy changed")
    if config.get("source_declared_interval_policy") != "PRESERVE_EXACT_SOURCE_FUNDING_INTERVAL_HOURS":
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 interval policy changed")
    if config.get("parquet_compression") != "zstd":
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 Parquet compression changed")
    for field in (
        "planning_r2_writes_authorized",
        "funding_materialization_authorized",
        "source_switch_authorized",
        "pionex_native_relabel_authorized",
        "provider_splicing_authorized",
        "interpolation_authorized",
        "historical_universe_membership_authorized",
        "backtest_admission_authorized",
        "trade_plan_authorized",
        "live_trading_authorized",
    ):
        if config.get(field) is not False:
            raise BinanceFundingMaterializationPlanV02Error(f"{field} must remain false during V0.2 planning")


def validate_v0_2_authorities(
    coverage: dict[str, object],
    budget: dict[str, object],
    source_proof: dict[str, object],
    continuity_review: dict[str, object],
) -> None:
    validate_authorities(coverage, budget, source_proof)
    if continuity_review.get("status") != "PASS":
        raise BinanceFundingMaterializationPlanV02Error("Funding continuity review must PASS")
    if continuity_review.get("stage") != "BINANCE_FUNDING_INTERIOR_CONTINUITY_REVIEW_SCOPE_REDUCTION_REQUIRED":
        raise BinanceFundingMaterializationPlanV02Error("Funding continuity review stage changed")
    if continuity_review.get("review_outcome") != "SCOPE_REDUCTION_REQUIRED":
        raise BinanceFundingMaterializationPlanV02Error("Funding continuity review outcome changed")
    effect = continuity_review.get("v0_1_materialization_effect") or {}
    if effect.get("v0_1_write_execution_must_remain_blocked") is not True:
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.1 must remain blocked")
    scope_change = continuity_review.get("required_scope_change") or {}
    if scope_change.get("deferred_symbol") != "HYPEUSDT" or scope_change.get("deferred_year") != 2026:
        raise BinanceFundingMaterializationPlanV02Error("Funding continuity scope-reduction target changed")
    if scope_change.get("deferred_source_months") != [1, 2, 3, 4, 5, 6, 7]:
        raise BinanceFundingMaterializationPlanV02Error("Funding deferred source months changed")
    if scope_change.get("remaining_expected_source_months") != 1003:
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 source-month target changed")
    if scope_change.get("remaining_expected_annual_canonical_objects") != 94:
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 annual-object target changed")


def build_v0_2_scope(coverage: dict[str, object]) -> FundingMaterializationScope:
    v0_1 = build_materialization_scope(coverage)
    filtered = tuple(
        item
        for item in v0_1.annual_scopes
        if not (item.symbol == "HYPEUSDT" and item.year == 2026)
    )
    result = FundingMaterializationScope(filtered)
    if result.symbol_count != 15:
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 must retain all 15 symbols where valid history exists")
    if result.symbol_months != 1003:
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 exact source-month count changed")
    if result.canonical_objects != 94:
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 exact annual-object count changed")
    if any(item.symbol == "HYPEUSDT" and item.year == 2026 for item in result.annual_scopes):
        raise BinanceFundingMaterializationPlanV02Error("HYPEUSDT 2026 escaped V0.2 defer policy")
    hype = [item for item in result.annual_scopes if item.symbol == "HYPEUSDT"]
    if len(hype) != 1 or hype[0].year != 2025 or hype[0].months != (5, 6, 7, 8, 9, 10, 11, 12):
        raise BinanceFundingMaterializationPlanV02Error("Funding V0.2 HYPE scope changed")
    return result


def canonical_scope_rows(scope: FundingMaterializationScope) -> list[dict[str, object]]:
    return [
        {
            "symbol": item.symbol,
            "year": item.year,
            "months": list(item.months),
            "source_archive_count": item.source_archive_count,
            "canonical_key": item.canonical_key,
            "partition_receipt_key": item.receipt_key,
        }
        for item in scope.annual_scopes
    ]


def canonical_scope_sha256(scope: FundingMaterializationScope) -> str:
    payload = json.dumps(canonical_scope_rows(scope), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
