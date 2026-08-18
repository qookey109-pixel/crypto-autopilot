from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable

from .binance_funding import BinanceVisionFundingArchiveKey
from .binance_funding_materialization_plan import FundingMaterializationScope


MATERIALIZATION_AUTHORITY_PATH = (
    "research/receipts/2026-08-18-binance-funding-materialization-authority.json"
)
MATERIALIZATION_AUTHORITY_AMENDMENT_PATH = (
    "research/receipts/2026-08-18-binance-funding-materialization-authority-amendment.json"
)
SOURCE_CHECKSUM_SET_AUTHORITY_PATH = (
    "research/receipts/2026-08-18-binance-funding-source-checksum-set.json"
)
EXPECTED_SCOPE_SHA256 = "81f64c4f07f1c77bf8391962e0ff7b3eb5f004d4a53bd0d9b8f50328c18c267c"
EXPECTED_CHECKSUM_SET_SHA256 = "7ed43292ecee61c358360b8a255fb7e7844bf7ac10626425c44292b4ad92963a"


class BinanceFundingMaterializationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class FundingChecksumRecord:
    symbol: str
    period: str
    archive_sha256: str

    def __post_init__(self) -> None:
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("Funding checksum symbol must be uppercase")
        if len(self.period) != 7 or self.period[4] != "-":
            raise ValueError("Funding checksum period must be YYYY-MM")
        digest = self.archive_sha256.lower()
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError("Funding archive SHA must be 64 lowercase/uppercase hex characters")


@dataclass(frozen=True, slots=True)
class FundingRunMetadataKeys:
    source_manifest: str
    canonical_manifest: str
    preflight_receipt: str
    result: str

    @property
    def all(self) -> tuple[str, str, str, str]:
        return (
            self.source_manifest,
            self.canonical_manifest,
            self.preflight_receipt,
            self.result,
        )


def canonical_json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


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
    payload = json.dumps(
        canonical_scope_rows(scope),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def checksum_set_sha256(records: Iterable[FundingChecksumRecord]) -> str:
    ordered = sorted(records, key=lambda item: (item.symbol, item.period))
    if len({(item.symbol, item.period) for item in ordered}) != len(ordered):
        raise BinanceFundingMaterializationError("duplicate Funding checksum identity")
    payload = "".join(
        f"{item.symbol}\t{item.period}\t{item.archive_sha256.lower()}\n"
        for item in ordered
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def source_keys_from_scope(scope: FundingMaterializationScope) -> tuple[BinanceVisionFundingArchiveKey, ...]:
    keys = [
        BinanceVisionFundingArchiveKey(item.symbol, f"{item.year:04d}-{month:02d}")
        for item in scope.annual_scopes
        for month in item.months
    ]
    keys.sort(key=lambda item: item.identity)
    if len(keys) != 1010 or len({key.identity for key in keys}) != 1010:
        raise BinanceFundingMaterializationError("Funding source-key scope must contain 1,010 unique months")
    return tuple(keys)


def run_metadata_keys(run_id: str) -> FundingRunMetadataKeys:
    value = str(run_id).strip()
    if not value or any(char not in "0123456789" for char in value):
        raise ValueError("GitHub run id must be numeric")
    root = f"manifests/historical/binance_usdm/funding/materialization/run={value}"
    receipt_root = f"receipts/historical/binance_usdm/funding/materialization/run={value}"
    return FundingRunMetadataKeys(
        source_manifest=f"{root}/source-manifest.json",
        canonical_manifest=f"{root}/canonical-manifest.json",
        preflight_receipt=f"{receipt_root}/preflight.json",
        result=f"{receipt_root}/result.json",
    )


def validate_authority_bundle(
    *,
    materialization_authority: dict[str, object],
    amendment: dict[str, object],
    checksum_set_authority: dict[str, object],
    scope: FundingMaterializationScope,
) -> tuple[str, str]:
    if materialization_authority.get("status") != "PASS":
        raise BinanceFundingMaterializationError("Funding materialization authority must PASS")
    if materialization_authority.get("stage") != "BINANCE_FUNDING_R2_MATERIALIZATION_AUTHORIZED":
        raise BinanceFundingMaterializationError("Funding materialization authority stage mismatch")
    if materialization_authority.get("authority_type") != "STORAGE_MATERIALIZATION_ONLY":
        raise BinanceFundingMaterializationError("Funding authority must remain storage-only")
    if materialization_authority.get("provider") != "binance_usdm" or materialization_authority.get("dataset") != "fundingRate":
        raise BinanceFundingMaterializationError("Funding authority provider/dataset mismatch")
    authorized_actions = materialization_authority.get("authorized_actions") or {}
    if authorized_actions.get("funding_materialization_authorized") is not True:
        raise BinanceFundingMaterializationError("Funding materialization is not authorized")
    if authorized_actions.get("r2_writes_authorized") is not True:
        raise BinanceFundingMaterializationError("Funding R2 writes are not authorized")
    forbidden = materialization_authority.get("explicitly_not_authorized") or {}
    for field in (
        "source_switch_authorized",
        "provider_splicing_authorized",
        "pionex_native_relabel_authorized",
        "historical_universe_membership_authorized",
        "backtest_admission_authorized",
        "automatic_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if forbidden.get(field) is not False:
            raise BinanceFundingMaterializationError(f"Funding authority unexpectedly permits {field}")

    scope_sha = canonical_scope_sha256(scope)
    authorized_scope = materialization_authority.get("authorized_scope") or {}
    if scope_sha != EXPECTED_SCOPE_SHA256:
        raise BinanceFundingMaterializationError("recomputed Funding scope SHA does not match implementation constant")
    if authorized_scope.get("canonical_scope_sha256") != scope_sha:
        raise BinanceFundingMaterializationError("Funding authority scope SHA mismatch")
    if int(authorized_scope.get("source_archive_count") or 0) != 1010:
        raise BinanceFundingMaterializationError("Funding authority source archive count mismatch")
    if int(authorized_scope.get("annual_canonical_objects") or 0) != 95:
        raise BinanceFundingMaterializationError("Funding authority annual object count mismatch")
    if int(authorized_scope.get("planned_total_r2_write_objects") or 0) != 194:
        raise BinanceFundingMaterializationError("Funding authority write-object count mismatch")

    if amendment.get("status") != "PASS" or amendment.get("stage") != "BINANCE_FUNDING_R2_MATERIALIZATION_AUTHORITY_CHECKSUM_SET_BOUND":
        raise BinanceFundingMaterializationError("Funding checksum-set authority amendment must PASS")
    if amendment.get("authorized_scope_sha256") != scope_sha:
        raise BinanceFundingMaterializationError("Funding amendment scope SHA mismatch")
    if int(amendment.get("authorized_source_archive_count") or 0) != 1010:
        raise BinanceFundingMaterializationError("Funding amendment source count mismatch")

    if checksum_set_authority.get("status") != "PASS" or checksum_set_authority.get("stage") != "BINANCE_FUNDING_SOURCE_CHECKSUM_SET_FROZEN":
        raise BinanceFundingMaterializationError("Funding checksum-set authority must PASS")
    if int(checksum_set_authority.get("available_archive_count") or 0) != 1010:
        raise BinanceFundingMaterializationError("Funding checksum-set authority count mismatch")
    checksum_sha = str(checksum_set_authority.get("checksum_set_sha256") or "")
    if checksum_sha != EXPECTED_CHECKSUM_SET_SHA256:
        raise BinanceFundingMaterializationError("Funding checksum-set SHA changed")
    if amendment.get("required_checksum_set_sha256") != checksum_sha:
        raise BinanceFundingMaterializationError("Funding amendment checksum-set SHA mismatch")

    permissions = amendment.get("permissions") or {}
    if permissions.get("funding_materialization_authorized") is not True:
        raise BinanceFundingMaterializationError("Funding amendment does not retain materialization authority")
    if permissions.get("r2_writes_authorized_for_original_exact_scope_only") is not True:
        raise BinanceFundingMaterializationError("Funding amendment does not retain scoped R2 authority")
    for field in (
        "source_switch_authorized",
        "provider_splicing_authorized",
        "pionex_native_relabel_authorized",
        "historical_universe_membership_authorized",
        "backtest_admission_authorized",
        "automatic_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if permissions.get(field) is not False:
            raise BinanceFundingMaterializationError(f"Funding amendment unexpectedly permits {field}")
    return scope_sha, checksum_sha


def validate_execution_marker(marker: dict[str, object], *, scope_sha256: str, checksum_set_sha256_value: str) -> None:
    if marker.get("status") != "EXECUTE_AUTHORIZED_FUNDING_R2_MATERIALIZATION":
        raise BinanceFundingMaterializationError("Funding execution marker status mismatch")
    if marker.get("execute") is not True:
        raise BinanceFundingMaterializationError("Funding execution marker must explicitly set execute=true")
    if marker.get("provider") != "binance_usdm" or marker.get("dataset") != "fundingRate":
        raise BinanceFundingMaterializationError("Funding execution marker provider/dataset mismatch")
    if marker.get("canonical_scope_sha256") != scope_sha256:
        raise BinanceFundingMaterializationError("Funding execution marker scope SHA mismatch")
    if marker.get("source_checksum_set_sha256") != checksum_set_sha256_value:
        raise BinanceFundingMaterializationError("Funding execution marker checksum-set SHA mismatch")
    if marker.get("materialization_authority") != MATERIALIZATION_AUTHORITY_PATH:
        raise BinanceFundingMaterializationError("Funding execution marker authority path mismatch")
    if marker.get("authority_amendment") != MATERIALIZATION_AUTHORITY_AMENDMENT_PATH:
        raise BinanceFundingMaterializationError("Funding execution marker amendment path mismatch")
    if marker.get("checksum_set_authority") != SOURCE_CHECKSUM_SET_AUTHORITY_PATH:
        raise BinanceFundingMaterializationError("Funding execution marker checksum authority path mismatch")
    for field in (
        "source_switch_authorized",
        "pionex_native_relabel_authorized",
        "backtest_admission_authorized",
        "trade_plan_authorized",
        "live_trading_authorized",
    ):
        if marker.get(field) is not False:
            raise BinanceFundingMaterializationError(f"Funding execution marker unexpectedly permits {field}")
