from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .binance_funding import BinanceVisionFundingArchiveKey
from .binance_funding_materialization_plan import FundingMaterializationScope
from .binance_funding_materialization_plan_v0_2 import canonical_scope_sha256


AUTHORITY_PATH = "research/receipts/2026-08-19-binance-funding-materialization-authority-v0-2.json"
CONFIG_PATH = "config/binance_funding_materialization_authority_v0_2.json"
EXPECTED_SCOPE_SHA256 = "1e0ff54daeec8e5e47376fedb631c663687dd6fb6a4c297d269c33acdf99ad58"
EXPECTED_CHECKSUM_SET_SHA256 = "881c14d3b3c780b8a0d56ca2f7fd57d2abff310fcd7cb4b13dc01f506b9b64f3"
CADENCE_TOLERANCE_MS = 50


class BinanceFundingMaterializerV02Error(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class FundingChecksumRecord:
    symbol: str
    period: str
    archive_sha256: str

    def canonical_line(self) -> bytes:
        return f"{self.symbol}\t{self.period}\t{self.archive_sha256}\n".encode("utf-8")


def checksum_set_sha256(records: tuple[FundingChecksumRecord, ...]) -> str:
    ordered = sorted(records, key=lambda row: (row.symbol, row.period))
    identities = [(row.symbol, row.period) for row in ordered]
    if len(identities) != len(set(identities)):
        raise BinanceFundingMaterializerV02Error("duplicate Funding checksum identity")
    return hashlib.sha256(b"".join(row.canonical_line() for row in ordered)).hexdigest()


def source_keys_from_scope(scope: FundingMaterializationScope) -> tuple[BinanceVisionFundingArchiveKey, ...]:
    keys = tuple(
        BinanceVisionFundingArchiveKey(item.symbol, f"{item.year:04d}-{month:02d}")
        for item in scope.annual_scopes
        for month in item.months
    )
    identities = [key.identity for key in keys]
    if len(keys) != 1003 or len(identities) != len(set(identities)):
        raise BinanceFundingMaterializerV02Error(
            f"Funding V0.2 source identity count must be exactly 1,003; got {len(keys)}"
        )
    if any(key.symbol == "HYPEUSDT" and key.period.startswith("2026-") for key in keys):
        raise BinanceFundingMaterializerV02Error("HYPEUSDT 2026 escaped V0.2 deferred scope")
    return keys


def validate_runtime_authority(
    *,
    config: dict[str, object],
    authority: dict[str, object],
    scope: FundingMaterializationScope,
) -> tuple[str, str]:
    if authority.get("status") != "PASS":
        raise BinanceFundingMaterializerV02Error("Funding V0.2 authority must PASS")
    if authority.get("stage") != "BINANCE_FUNDING_R2_MATERIALIZATION_V0_2_AUTHORIZED":
        raise BinanceFundingMaterializerV02Error("Funding V0.2 authority stage changed")
    if authority.get("authority_type") != "STORAGE_MATERIALIZATION_ONLY":
        raise BinanceFundingMaterializerV02Error("Funding V0.2 authority type changed")
    if authority.get("provider") != "binance_usdm" or authority.get("dataset") != "fundingRate":
        raise BinanceFundingMaterializerV02Error("Funding V0.2 provider/dataset changed")

    scope_sha = canonical_scope_sha256(scope)
    if scope_sha != EXPECTED_SCOPE_SHA256:
        raise BinanceFundingMaterializerV02Error(f"Funding V0.2 scope SHA mismatch: {scope_sha}")
    if config.get("expected_canonical_scope_sha256") != EXPECTED_SCOPE_SHA256:
        raise BinanceFundingMaterializerV02Error("Funding V0.2 config scope SHA changed")
    if config.get("expected_source_checksum_set_sha256") != EXPECTED_CHECKSUM_SET_SHA256:
        raise BinanceFundingMaterializerV02Error("Funding V0.2 config checksum-set SHA changed")
    if int(config.get("materialization_cadence_jitter_tolerance_ms") or -1) != CADENCE_TOLERANCE_MS:
        raise BinanceFundingMaterializerV02Error("Funding V0.2 cadence tolerance changed")

    authorized_scope = authority.get("authorized_scope") or {}
    actions = authority.get("authorized_actions") or {}
    blocked = authority.get("explicitly_not_authorized") or {}
    deferred = authority.get("deferred_scope") or {}
    if not all(isinstance(value, dict) for value in (authorized_scope, actions, blocked, deferred)):
        raise BinanceFundingMaterializerV02Error("Funding V0.2 authority shape changed")

    expected_scope_fields = {
        "canonical_scope_sha256": EXPECTED_SCOPE_SHA256,
        "source_checksum_set_sha256": EXPECTED_CHECKSUM_SET_SHA256,
        "source_archive_count": 1003,
        "materialized_symbol_months": 1003,
        "annual_canonical_objects": 94,
        "annual_partition_receipts": 94,
        "run_level_metadata_objects": 4,
        "planned_total_r2_object_identities": 192,
        "canonical_partition": "annual_per_symbol",
    }
    for field, expected in expected_scope_fields.items():
        if authorized_scope.get(field) != expected:
            raise BinanceFundingMaterializerV02Error(
                f"Funding V0.2 authority field changed: {field}={authorized_scope.get(field)!r}"
            )

    for field in (
        "funding_materialization_authorized",
        "r2_writes_authorized",
        "write_exact_94_canonical_funding_parquet_objects",
        "write_exact_94_partition_receipts",
        "write_exact_4_run_metadata_objects",
        "post_write_download_sha_and_parquet_verification_required",
        "post_write_exact_funding_observation_equality_required",
    ):
        if actions.get(field) is not True:
            raise BinanceFundingMaterializerV02Error(f"Funding V0.2 action must remain true: {field}")

    for field in (
        "v0_1_scope_reactivation_authorized",
        "hypeusdt_2026_funding_materialization_authorized",
        "interpolation_authorized",
        "source_switch_authorized",
        "provider_splicing_authorized",
        "pionex_native_relabel_authorized",
        "historical_universe_membership_authorized",
        "backtest_admission_authorized",
        "strategy_parameter_change_authorized",
        "automatic_trade_plan_authorized",
        "private_pionex_api_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
        "trade_kline_w1_materialization_authorized",
        "mark_price_materialization_authorized",
        "open_interest_materialization_authorized",
    ):
        if blocked.get(field) is not False:
            raise BinanceFundingMaterializerV02Error(f"Funding V0.2 forbidden permission changed: {field}")

    if deferred.get("symbol") != "HYPEUSDT" or deferred.get("year") != 2026:
        raise BinanceFundingMaterializerV02Error("Funding V0.2 deferred partition changed")
    if deferred.get("materialization_authorized") is not False:
        raise BinanceFundingMaterializerV02Error("HYPEUSDT 2026 must remain deferred")

    source_keys_from_scope(scope)
    return scope_sha, EXPECTED_CHECKSUM_SET_SHA256
