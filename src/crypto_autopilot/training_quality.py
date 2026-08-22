"""Fail-closed quality contracts for the online Binance Spot research pipeline."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .lineage import sha256_json


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
V0_5_CONFIG_PATH = "config/binance_spot_r2_training_governance_v0_5.json"
V0_5_AUTHORITY_RECEIPT_PATH = (
    "research/receipts/"
    "2026-08-23-binance-spot-r2-training-governance-v0-5-authority.json"
)
V0_3_BASELINE_EVIDENCE_PATH = (
    "research/receipts/"
    "2026-08-22-binance-spot-r2-automated-training-v0-3-pass.json"
)
V0_3_BASELINE_EVIDENCE_SHA256 = (
    "c319dd3a721b58f9db216d24e2bdee739bcc5853251de1c3c2eb750ef1576deb"
)
_V0_5_STORAGE_CONTRACT = {
    "schema_version": "v0.5",
    "dataset_runs_namespace": "market-data/binance_spot/internal-training/v0.5/runs",
    "training_namespace": "training/binance_spot/daily-direction/v0.5",
    "latest_training_pointer_key": "training/binance_spot/daily-direction/v0.5/latest.json",
}
_V0_5_MONTHLY_CONTRACT = {
    "schema_version": "v0.5",
    "namespace": "research/binance_spot/universe-review/v0.5",
    "latest_pointer_key": "research/binance_spot/universe-review/v0.5/latest.json",
}
_V0_5_MONTHLY_INITIAL_ACTIVATION_CONTRACT = {
    "mode": "ONE_TIME_MANUAL_WORKFLOW_DISPATCH",
    "purpose": "CREATE_INITIAL_V0_5_MONTHLY_BASELINE",
    "required": True,
    "must_complete_before_utc": "2026-08-27T00:00:00Z",
    "push_trigger_authorized": False,
    "repeat_manual_activation_authorized": False,
}
_FORBIDDEN_CATALOG_AUTHORITIES = (
    "production_r2_access_authorized",
    "provider_splicing_authorized",
    "pionex_native_relabel_authorized",
    "source_switch_authorized",
    "holdout_access_authorized",
    "trade_kline_w1_materialization_authorized",
    "formal_trade_plan_authorized",
    "real_money_order_authorized",
    "live_trading_authorized",
)
_FORBIDDEN_MODEL_AUTHORITIES = (
    "source_switch_authorized",
    "holdout_accessed",
    "automatic_model_promotion_authorized",
    "automatic_trade_plan_authorized",
    "real_money_order_authorized",
    "live_trading_authorized",
)


class TrainingQualityError(ValueError):
    pass


def _require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise TrainingQualityError(f"{label} must be a lowercase SHA-256")
    return value


def _require_non_negative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise TrainingQualityError(f"{label} must be a non-negative integer")
    return value


def _require_fraction(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise TrainingQualityError(f"{label} must be within [0, 1]")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise TrainingQualityError(f"{label} must be within [0, 1]") from exc
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise TrainingQualityError(f"{label} must be within [0, 1]")
    return result


def validate_v0_5_authority_pair(
    config: dict[str, Any],
    authority: dict[str, Any],
    *,
    config_sha256: str,
) -> dict[str, Any]:
    """Bind the executable V0.5 config to its exact versioned authority receipt."""

    _require_sha256(config_sha256, "config_sha256")
    if (
        config.get("version") != "0.5.0"
        or config.get("status")
        != "R2_ONLY_TRAINING_GOVERNANCE_V0_5_AUTHORIZED_ON_MAIN_MERGE"
        or config.get("provider") != "binance_spot"
        or config.get("delivery") != "binance_public_rest"
        or config.get("dataset") != "spot_1d_internal_training"
        or config.get("authority_receipt") != V0_5_AUTHORITY_RECEIPT_PATH
    ):
        raise TrainingQualityError("V0.5 configuration identity mismatch")

    storage = config.get("storage")
    monthly = config.get("monthly_universe_review")
    schedule = config.get("schedule")
    source = config.get("source")
    training = config.get("training")
    data_quality = config.get("data_quality")
    if not isinstance(storage, dict) or any(
        storage.get(key) != value for key, value in _V0_5_STORAGE_CONTRACT.items()
    ):
        raise TrainingQualityError("V0.5 storage namespace contract mismatch")
    if (
        storage.get("backend") != "cloudflare_r2"
        or storage.get("persistent_store") != "cloudflare_r2_only"
        or storage.get("local_persistent_artifacts_authorized") is not False
        or storage.get("fresh_whole_bucket_inventory_before_write") is not True
        or storage.get("round_trip_sha256_verification_required") is not True
        or storage.get("credentials_location") != "github_actions_secrets_only"
        or storage.get("free_only_hard_stop_bytes") != 8_000_000_000
        or storage.get("publish_pass_stage")
        != "BINANCE_SPOT_R2_TRAINING_GOVERNANCE_PUBLISHED_V0_5"
    ):
        raise TrainingQualityError("V0.5 R2-only storage policy mismatch")
    if not isinstance(monthly, dict) or any(
        monthly.get(key) != value for key, value in _V0_5_MONTHLY_CONTRACT.items()
    ):
        raise TrainingQualityError("V0.5 monthly namespace contract mismatch")
    if (
        monthly.get("initial_activation")
        != _V0_5_MONTHLY_INITIAL_ACTIVATION_CONTRACT
    ):
        raise TrainingQualityError("V0.5 monthly initial activation contract mismatch")
    if not isinstance(schedule, dict):
        raise TrainingQualityError("V0.5 schedule contract is missing")
    if (
        schedule.get("cron_utc") != "37 2 * * 0"
        or schedule.get("provider_read_stop_utc") != "2026-08-27T00:00:00Z"
        or schedule.get("automatic_resume_after_stop") is not False
    ):
        raise TrainingQualityError("V0.5 schedule contract mismatch")
    if (
        not isinstance(source, dict)
        or source.get("market_data_base_url") != "https://data-api.binance.vision"
        or source.get("start_utc") != "2020-01-01T00:00:00Z"
        or source.get("end_policy") != "LAST_COMPLETE_UTC_DAY"
        or source.get("interval") != "1d"
        or source.get("quotes") != ["USDT", "USDC"]
    ):
        raise TrainingQualityError("V0.5 provider source contract mismatch")
    if (
        not isinstance(training, dict)
        or training.get("output_schema_version") != "v0.5"
        or training.get("model_family") != "deterministic_logistic_regression"
        or training.get("target") != "next_complete_daily_close_up"
    ):
        raise TrainingQualityError("V0.5 training identity contract mismatch")
    if (
        not isinstance(data_quality, dict)
        or data_quality.get("minimum_row_count_fraction_of_previous") != 0.8
    ):
        raise TrainingQualityError("V0.5 dataset depth policy mismatch")

    config_authority = config.get("authority")
    if not isinstance(config_authority, dict):
        raise TrainingQualityError("V0.5 configuration authority is missing")
    for key in (
        "github_actions_weekly_sync_authorized",
        "github_actions_monthly_universe_review_authorized",
        "binance_public_market_reads_authorized",
        "production_r2_client_construction_authorized",
        "production_r2_reads_authorized",
        "production_r2_writes_authorized_for_exact_namespaces",
        "automated_research_model_training_authorized",
        "dataset_quality_gates_authorized",
        "walk_forward_research_diagnostics_authorized",
        "cost_drawdown_exposure_diagnostics_authorized",
        "monthly_classification_review_authorized",
    ):
        if config_authority.get(key) is not True:
            raise TrainingQualityError(f"V0.5 required online authority missing: {key}")
    for key in (
        "source_switch_authorized",
        "holdout_access_authorized",
        "formal_backtest_admission_authorized",
        "automatic_model_promotion_authorized",
        "automatic_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if config_authority.get(key) is not False:
            raise TrainingQualityError(f"unsafe V0.5 configuration authority: {key}")

    expected_namespaces = {
        "dataset_runs_namespace": storage["dataset_runs_namespace"],
        "training_namespace": storage["training_namespace"],
        "latest_training_pointer_key": storage["latest_training_pointer_key"],
        "monthly_namespace": monthly["namespace"],
        "monthly_latest_pointer_key": monthly["latest_pointer_key"],
    }
    authorized_config = authority.get("authorized_config")
    expected_bootstrap = {
        "path": V0_3_BASELINE_EVIDENCE_PATH,
        "sha256": V0_3_BASELINE_EVIDENCE_SHA256,
        "schema": "binance-spot-r2-automated-training-pass-v0.3",
        "provider": "binance_spot",
        "market_count_requested": 748,
        "market_count_audited": 723,
        "row_count": 701275,
    }
    if (
        authority.get("schema")
        != "binance-spot-r2-training-governance-authority-v0.5"
        or authority.get("status")
        != "TRAINING_GOVERNANCE_V0_5_AUTHORIZED_ON_MAIN_MERGE"
        or authority.get("config_version") != config["version"]
        or authorized_config
        != {
            "path": V0_5_CONFIG_PATH,
            "sha256": config_sha256,
        }
        or authority.get("provider") != config["provider"]
        or authority.get("storage_schema_version") != storage["schema_version"]
        or authority.get("exact_namespaces") != expected_namespaces
        or authority.get("weekly_schedule_utc") != schedule.get("cron_utc")
        or authority.get("monthly_schedule_utc") != monthly.get("cron_utc")
        or authority.get("provider_read_stop_utc")
        != schedule.get("provider_read_stop_utc")
        or authority.get("automatic_resume_after_stop")
        is not schedule.get("automatic_resume_after_stop")
        or authority.get("monthly_initial_activation")
        != monthly.get("initial_activation")
        or authority.get("bootstrap_baseline") != expected_bootstrap
    ):
        raise TrainingQualityError("V0.5 authority receipt does not match configuration")
    receipt_authority = authority.get("authority")
    if not isinstance(receipt_authority, dict):
        raise TrainingQualityError("V0.5 authority receipt boundary is missing")
    for key in (
        "v0_4_execution_retirement_authorized",
        "v0_5_exact_namespaces_authorized",
        "pre_publish_contract_validation_authorized",
        "dataset_tail_and_collapse_gates_authorized",
        "weekly_baseline_cost_drawdown_exposure_gate_authorized",
        "monthly_catalog_collapse_gate_authorized",
        "monthly_one_time_manual_activation_authorized",
    ):
        if receipt_authority.get(key) is not True:
            raise TrainingQualityError(f"V0.5 receipt authority missing: {key}")
    for key in (
        "formal_backtest_admission_authorized",
        "automatic_model_promotion_authorized",
        "historical_universe_membership_authorized",
        "holdout_access_authorized",
        "source_switch_authorized",
        "automatic_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
        "v0_10_production_critical_path_mutation",
    ):
        if receipt_authority.get(key) is not False:
            raise TrainingQualityError(f"unsafe V0.5 receipt authority: {key}")
    return {
        "status": "PASS",
        "config_version": config["version"],
        "config_sha256": config_sha256,
        "authority_receipt": V0_5_AUTHORITY_RECEIPT_PATH,
        "provider": "binance_spot",
    }


def load_v0_5_authority_pair(
    config: dict[str, Any],
    *,
    config_path: Path,
    config_payload: bytes,
    repository_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    expected_config_path = (repository_root / V0_5_CONFIG_PATH).resolve()
    if config_path.resolve() != expected_config_path:
        raise TrainingQualityError("only the canonical V0.5 config path is executable")
    if config.get("authority_receipt") != V0_5_AUTHORITY_RECEIPT_PATH:
        raise TrainingQualityError("V0.5 authority receipt path mismatch")
    authority_path = repository_root / V0_5_AUTHORITY_RECEIPT_PATH
    authority = json.loads(authority_path.read_bytes())
    evidence = validate_v0_5_authority_pair(
        config,
        authority,
        config_sha256=sha256_payload(config_payload),
    )
    return authority, evidence


def load_v0_3_bootstrap_baseline(
    config: dict[str, Any], *, repository_root: Path
) -> dict[str, Any]:
    policy = config.get("data_quality")
    if not isinstance(policy, dict):
        raise TrainingQualityError("V0.5 data-quality policy is missing")
    if (
        policy.get("baseline_evidence") != V0_3_BASELINE_EVIDENCE_PATH
        or policy.get("baseline_evidence_sha256")
        != V0_3_BASELINE_EVIDENCE_SHA256
    ):
        raise TrainingQualityError("V0.5 bootstrap baseline identity mismatch")
    payload = (repository_root / V0_3_BASELINE_EVIDENCE_PATH).read_bytes()
    if sha256_payload(payload) != V0_3_BASELINE_EVIDENCE_SHA256:
        raise TrainingQualityError("V0.5 bootstrap baseline SHA-256 mismatch")
    baseline = json.loads(payload)
    dataset = baseline.get("dataset")
    if (
        baseline.get("schema") != "binance-spot-r2-automated-training-pass-v0.3"
        or baseline.get("status") != "PASS"
        or baseline.get("stage")
        != "BINANCE_SPOT_R2_AUTOMATED_TRAINING_PUBLISHED_V0_3"
        or baseline.get("provider") != "binance_spot"
        or not isinstance(dataset, dict)
    ):
        raise TrainingQualityError("V0.5 bootstrap baseline contract mismatch")
    requested = _require_non_negative_int(
        dataset.get("market_count_requested"), "baseline.market_count_requested"
    )
    audited = _require_non_negative_int(
        dataset.get("market_count_audited"), "baseline.market_count_audited"
    )
    row_count = _require_non_negative_int(
        dataset.get("row_count"), "baseline.row_count"
    )
    if requested <= 0 or audited > requested:
        raise TrainingQualityError("V0.5 bootstrap baseline counts are invalid")
    workflow = baseline.get("workflow_run")
    r2_publish = baseline.get("r2_publish")
    if (
        requested != 748
        or audited != 723
        or row_count != 701275
        or not isinstance(workflow, dict)
        or workflow.get("head_branch") != "main"
        or workflow.get("conclusion") != "success"
        or not isinstance(r2_publish, dict)
        or r2_publish.get("all_objects_round_trip_sha256_verified") is not True
        or r2_publish.get("latest_pointer_written_last") is not True
        or r2_publish.get("r2_writes_performed") is not True
    ):
        raise TrainingQualityError("V0.5 bootstrap baseline evidence is incomplete")
    baseline_authority = baseline.get("authority")
    if not isinstance(baseline_authority, dict):
        raise TrainingQualityError("V0.5 bootstrap baseline authority is missing")
    for key in (
        "source_switch_authorized",
        "holdout_accessed",
        "automatic_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if baseline_authority.get(key) is not False:
            raise TrainingQualityError(f"unsafe V0.5 bootstrap authority: {key}")
    return baseline


def validate_catalog_quality(
    catalog: dict[str, Any],
    *,
    policy: dict[str, Any],
    previous_market_count: int | None = None,
) -> dict[str, Any]:
    if catalog.get("schema") != "binance-internal-training-market-catalog-v0.2":
        raise TrainingQualityError("catalog schema mismatch")
    if (
        catalog.get("status") != "EPHEMERAL_BUILD_FOR_R2_AUTHORIZED"
        or catalog.get("provider") != "binance_spot"
        or catalog.get("market_type") != "spot"
        or catalog.get("source_endpoint")
        != "https://data-api.binance.vision/api/v3/exchangeInfo"
        or catalog.get("quote_filter")
        != {"all_quotes": False, "quotes": ["USDT", "USDC"]}
    ):
        raise TrainingQualityError("catalog provider or market type mismatch")
    authority = catalog.get("authority")
    if not isinstance(authority, dict) or any(
        authority.get(key) is not False for key in _FORBIDDEN_CATALOG_AUTHORITIES
    ):
        raise TrainingQualityError("catalog authority crossed a safety boundary")
    markets = catalog.get("markets")
    if not isinstance(markets, list):
        raise TrainingQualityError("catalog markets must be a list")
    symbols = [item.get("symbol") for item in markets if isinstance(item, dict)]
    if len(symbols) != len(markets) or any(not isinstance(symbol, str) for symbol in symbols):
        raise TrainingQualityError("catalog contains an invalid market record")
    for item in markets:
        if (
            item.get("status") != "TRADING"
            or item.get("market_type") != "spot"
            or item.get("is_spot_trading_allowed") is not True
            or item.get("quote_asset") not in {"USDT", "USDC"}
            or not all(
                isinstance(item.get(key), str) and item[key]
                for key in (
                    "base_asset",
                    "quote_asset",
                    "asset_class",
                    "classification_method",
                    "classification_confidence",
                )
            )
        ):
            raise TrainingQualityError("catalog contains an invalid market contract")
    if len(set(symbols)) != len(symbols):
        raise TrainingQualityError("catalog contains duplicate symbols")

    market_count = len(markets)
    minimum_count = _require_non_negative_int(
        policy.get("minimum_catalog_market_count"), "minimum_catalog_market_count"
    )
    failures = []
    if market_count < minimum_count:
        failures.append("CATALOG_MARKET_COUNT_BELOW_ABSOLUTE_MINIMUM")
    previous_fraction = None
    if previous_market_count is not None:
        previous_market_count = _require_non_negative_int(
            previous_market_count, "previous_market_count"
        )
        ratio = _require_fraction(
            policy["minimum_market_count_fraction_of_previous"],
            "minimum_market_count_fraction_of_previous",
        )
        previous_fraction = market_count / max(1, previous_market_count)
        if previous_fraction < ratio:
            failures.append("CATALOG_MARKET_COUNT_COLLAPSED_VS_PREVIOUS")
    evidence = {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "market_count": market_count,
        "minimum_catalog_market_count": minimum_count,
        "previous_market_count": previous_market_count,
        "market_count_fraction_of_previous": previous_fraction,
        "minimum_market_count_fraction_of_previous": _require_fraction(
            policy["minimum_market_count_fraction_of_previous"],
            "minimum_market_count_fraction_of_previous",
        ),
    }
    if failures:
        raise TrainingQualityError(";".join(failures))
    return evidence


def validate_dataset_receipt_quality(
    receipt: dict[str, Any],
    *,
    catalog: dict[str, Any],
    policy: dict[str, Any],
    expected_catalog_sha256: str,
    expected_catalog_bytes: int,
    expected_dataset_sha256: str,
    expected_dataset_bytes: int,
    expected_last_open_time_ms: int | None,
    provider_read_stop_time_ms: int,
    previous_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if receipt.get("schema") != "binance-internal-training-run-v0.2":
        raise TrainingQualityError("dataset receipt schema mismatch")
    if (
        receipt.get("status") != "PASS"
        or receipt.get("provider") != "binance_spot"
        or receipt.get("market_type") != "spot"
        or receipt.get("interval") != "1d"
    ):
        raise TrainingQualityError("dataset receipt is not a Binance Spot PASS")
    expected_catalog_sha256 = _require_sha256(
        expected_catalog_sha256, "expected_catalog_sha256"
    )
    expected_dataset_sha256 = _require_sha256(
        expected_dataset_sha256, "expected_dataset_sha256"
    )
    expected_catalog_bytes = _require_non_negative_int(
        expected_catalog_bytes, "expected_catalog_bytes"
    )
    expected_dataset_bytes = _require_non_negative_int(
        expected_dataset_bytes, "expected_dataset_bytes"
    )
    provider_read_stop_time_ms = _require_non_negative_int(
        provider_read_stop_time_ms, "provider_read_stop_time_ms"
    )
    if expected_last_open_time_ms is not None:
        expected_last_open_time_ms = _require_non_negative_int(
            expected_last_open_time_ms, "expected_last_open_time_ms"
        )
    catalog_binding = receipt.get("catalog")
    parquet_binding = receipt.get("parquet")
    if (
        not isinstance(catalog_binding, dict)
        or catalog_binding.get("sha256") != expected_catalog_sha256
        or catalog_binding.get("bytes") != expected_catalog_bytes
    ):
        raise TrainingQualityError("dataset receipt catalog binding mismatch")
    if (
        not isinstance(parquet_binding, dict)
        or parquet_binding.get("sha256") != expected_dataset_sha256
        or parquet_binding.get("bytes") != expected_dataset_bytes
    ):
        raise TrainingQualityError("dataset receipt Parquet binding mismatch")
    if receipt.get("authority") != catalog.get("authority"):
        raise TrainingQualityError("dataset receipt authority does not match catalog")
    requested = _require_non_negative_int(
        receipt.get("market_count_requested"), "market_count_requested"
    )
    with_rows = _require_non_negative_int(
        receipt.get("market_count_with_rows"), "market_count_with_rows"
    )
    audited = _require_non_negative_int(
        receipt.get("market_count_audited"), "market_count_audited"
    )
    row_count = _require_non_negative_int(receipt.get("row_count"), "row_count")
    if row_count <= 0:
        raise TrainingQualityError("dataset receipt row count must be positive")
    errors = receipt.get("errors")
    if not isinstance(errors, dict):
        raise TrainingQualityError("dataset receipt errors must be an object")
    if len(errors) > _require_non_negative_int(
        policy.get("maximum_provider_error_count"), "maximum_provider_error_count"
    ):
        raise TrainingQualityError("PROVIDER_ERROR_COUNT_ABOVE_POLICY")
    if requested != len(catalog["markets"]):
        raise TrainingQualityError("dataset receipt market count does not match catalog")
    if not 0 <= audited <= with_rows <= requested:
        raise TrainingQualityError("dataset receipt market counts are inconsistent")

    audit_evidence = receipt.get("market_audit_evidence")
    if not isinstance(audit_evidence, dict) or set(audit_evidence) != {
        str(item["symbol"]) for item in catalog["markets"]
    }:
        raise TrainingQualityError("dataset market audit evidence does not match catalog")
    try:
        if (
            receipt.get("requested_start_utc") != "2020-01-01T00:00:00Z"
            or not isinstance(receipt.get("captured_through_utc"), str)
            or not receipt["captured_through_utc"].endswith("Z")
        ):
            raise ValueError("unexpected coverage timestamps")
        captured_through_ms = int(
            datetime.fromisoformat(
                str(receipt["captured_through_utc"]).replace("Z", "+00:00")
            )
            .astimezone(UTC)
            .timestamp()
            * 1000
        )
        requested_start_ms = int(
            datetime.fromisoformat(
                str(receipt["requested_start_utc"]).replace("Z", "+00:00")
            )
            .astimezone(UTC)
            .timestamp()
            * 1000
        )
        generated_at_utc = receipt.get("generated_at_utc")
        if not isinstance(generated_at_utc, str) or not generated_at_utc.endswith("Z"):
            raise ValueError("unexpected generated timestamp")
        generated_at_ms = int(
            datetime.fromisoformat(generated_at_utc.replace("Z", "+00:00"))
            .astimezone(UTC)
            .timestamp()
            * 1000
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise TrainingQualityError("dataset receipt UTC coverage is invalid") from exc
    day_ms = 86_400_000
    if (
        captured_through_ms % day_ms != 0
        or requested_start_ms > captured_through_ms
        or generated_at_ms < captured_through_ms
        or generated_at_ms >= provider_read_stop_time_ms
        or captured_through_ms >= provider_read_stop_time_ms
        or (
            expected_last_open_time_ms is not None
            and captured_through_ms != expected_last_open_time_ms
        )
    ):
        raise TrainingQualityError("dataset receipt UTC coverage is not daily aligned")
    if receipt.get("website_projection") != {"authorized": False, "written": False}:
        raise TrainingQualityError("dataset receipt website projection boundary mismatch")

    evidence_audited = 0
    evidence_with_rows = 0
    with_row_symbols: list[str] = []
    for symbol, item in audit_evidence.items():
        if not isinstance(item, dict):
            raise TrainingQualityError(f"invalid market audit evidence: {symbol}")
        expected_last = item.get("expected_last_open_time_ms")
        actual_first = item.get("actual_first_open_time_ms")
        actual_last = item.get("actual_last_open_time_ms")
        tail_missing = item.get("tail_missing_bars")
        if expected_last != captured_through_ms:
            raise TrainingQualityError(f"market expected tail is invalid: {symbol}")
        if (actual_first is None) != (actual_last is None):
            raise TrainingQualityError(f"market actual coverage is inconsistent: {symbol}")
        if actual_last is None:
            expected_missing = (captured_through_ms - requested_start_ms) // day_ms + 1
        else:
            if (
                isinstance(actual_first, bool)
                or isinstance(actual_last, bool)
                or not isinstance(actual_first, int)
                or not isinstance(actual_last, int)
                or actual_first < requested_start_ms
                or actual_first > actual_last
                or actual_last > captured_through_ms
                or actual_first % day_ms != 0
                or actual_last % day_ms != 0
            ):
                raise TrainingQualityError(f"market actual coverage is invalid: {symbol}")
            evidence_with_rows += 1
            with_row_symbols.append(symbol)
            expected_missing = (captured_through_ms - actual_last) // day_ms
        if (
            isinstance(tail_missing, bool)
            or not isinstance(tail_missing, int)
            or tail_missing != expected_missing
            or item.get("tail_complete") is not (actual_last == expected_last)
        ):
            raise TrainingQualityError(f"market tail evidence is inconsistent: {symbol}")
        audit_ok = item.get("audit_ok") is True
        if audit_ok and (item.get("tail_complete") is not True or tail_missing != 0):
            raise TrainingQualityError(f"audited market has an incomplete tail: {symbol}")
        evidence_audited += int(audit_ok)
    if evidence_with_rows != with_rows:
        raise TrainingQualityError("market row coverage does not match receipt count")
    if evidence_audited != audited:
        raise TrainingQualityError("audited market count does not match market evidence")
    catalog_by_symbol = {
        str(item["symbol"]): item for item in catalog["markets"]
    }
    expected_asset_class_counts: dict[str, int] = {}
    expected_quote_asset_counts: dict[str, int] = {}
    for symbol in with_row_symbols:
        market = catalog_by_symbol[symbol]
        asset_class = str(market["asset_class"])
        quote_asset = str(market["quote_asset"])
        expected_asset_class_counts[asset_class] = (
            expected_asset_class_counts.get(asset_class, 0) + 1
        )
        expected_quote_asset_counts[quote_asset] = (
            expected_quote_asset_counts.get(quote_asset, 0) + 1
        )
    if (
        receipt.get("asset_class_counts") != expected_asset_class_counts
        or receipt.get("quote_asset_counts") != expected_quote_asset_counts
    ):
        raise TrainingQualityError("dataset receipt classification counts mismatch")
    audit_failures = receipt.get("audit_failures")
    if (
        not isinstance(audit_failures, list)
        or len(audit_failures) != len(set(audit_failures))
        or any(
            not isinstance(symbol, str)
            or symbol not in audit_evidence
            or audit_evidence[symbol].get("audit_ok") is not False
            for symbol in audit_failures
        )
        or len(audit_failures) != with_rows - audited
    ):
        raise TrainingQualityError("dataset audit failures are inconsistent")

    audited_fraction = audited / max(1, requested)
    failures = []
    if requested < int(policy["minimum_catalog_market_count"]):
        failures.append("DATASET_MARKET_COUNT_BELOW_ABSOLUTE_MINIMUM")
    if audited_fraction < _require_fraction(
        policy["minimum_audited_market_fraction"],
        "minimum_audited_market_fraction",
    ):
        failures.append("AUDITED_MARKET_FRACTION_BELOW_POLICY")

    previous_requested = None
    previous_audited = None
    previous_row_count = None
    if previous_receipt is not None:
        if previous_receipt.get("schema") == "binance-internal-training-run-v0.2":
            if (
                previous_receipt.get("status") != "PASS"
                or previous_receipt.get("provider") != "binance_spot"
            ):
                raise TrainingQualityError("previous dataset receipt contract mismatch")
            previous_dataset = previous_receipt
        elif (
            previous_receipt.get("schema")
            == "binance-spot-r2-automated-training-pass-v0.3"
        ):
            if (
                previous_receipt.get("status") != "PASS"
                or previous_receipt.get("stage")
                != "BINANCE_SPOT_R2_AUTOMATED_TRAINING_PUBLISHED_V0_3"
                or previous_receipt.get("provider") != "binance_spot"
                or not isinstance(previous_receipt.get("dataset"), dict)
            ):
                raise TrainingQualityError("bootstrap dataset receipt contract mismatch")
            previous_dataset = previous_receipt["dataset"]
        else:
            raise TrainingQualityError("previous dataset receipt contract mismatch")
        previous_requested = _require_non_negative_int(
            previous_dataset.get("market_count_requested"),
            "previous.market_count_requested",
        )
        previous_audited = _require_non_negative_int(
            previous_dataset.get("market_count_audited"),
            "previous.market_count_audited",
        )
        previous_row_count = _require_non_negative_int(
            previous_dataset.get("row_count"),
            "previous.row_count",
        )
        if requested / max(1, previous_requested) < _require_fraction(
            policy["minimum_market_count_fraction_of_previous"],
            "minimum_market_count_fraction_of_previous",
        ):
            failures.append("DATASET_MARKET_COUNT_COLLAPSED_VS_PREVIOUS")
        if audited / max(1, previous_audited) < _require_fraction(
            policy["minimum_audited_count_fraction_of_previous"],
            "minimum_audited_count_fraction_of_previous",
        ):
            failures.append("AUDITED_MARKET_COUNT_COLLAPSED_VS_PREVIOUS")
        if row_count / max(1, previous_row_count) < _require_fraction(
            policy["minimum_row_count_fraction_of_previous"],
            "minimum_row_count_fraction_of_previous",
        ):
            failures.append("DATASET_ROW_COUNT_COLLAPSED_VS_PREVIOUS")

    evidence = {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "market_count_requested": requested,
        "market_count_audited": audited,
        "audited_market_fraction": audited_fraction,
        "previous_market_count_requested": previous_requested,
        "previous_market_count_audited": previous_audited,
        "row_count": row_count,
        "previous_row_count": previous_row_count,
        "holdout_accessed": False,
    }
    if failures:
        raise TrainingQualityError(";".join(failures))
    return evidence


def validate_model_contract(
    model: dict[str, Any],
    *,
    training_config: dict[str, Any],
    expected_data_sha256: str,
    provider_read_start_time_ms: int,
    provider_read_stop_time_ms: int,
) -> dict[str, Any]:
    expected_data_sha256 = _require_sha256(
        expected_data_sha256, "expected_data_sha256"
    )
    provider_read_start_time_ms = _require_non_negative_int(
        provider_read_start_time_ms, "provider_read_start_time_ms"
    )
    provider_read_stop_time_ms = _require_non_negative_int(
        provider_read_stop_time_ms, "provider_read_stop_time_ms"
    )
    try:
        generated_at_utc = model.get("generated_at_utc")
        if not isinstance(generated_at_utc, str) or not generated_at_utc.endswith("Z"):
            raise ValueError("model timestamp is not explicit UTC")
        generated_at = datetime.fromisoformat(
            generated_at_utc.replace("Z", "+00:00")
        )
        generated_at_ms = int(generated_at.astimezone(UTC).timestamp() * 1000)
    except (TypeError, ValueError) as exc:
        raise TrainingQualityError("V0.5 model generated timestamp is invalid") from exc
    if generated_at_ms >= provider_read_stop_time_ms:
        raise TrainingQualityError("V0.5 model generated after the provider stop")
    expected_features = training_config.get("feature_names")
    if not isinstance(expected_features, list) or not all(
        isinstance(value, str) for value in expected_features
    ):
        raise TrainingQualityError("configured feature contract is invalid")
    if (
        model.get("schema") != "binance-spot-daily-direction-model-v0.5"
        or model.get("status") != "PASS"
        or model.get("mode") != "RESEARCH_TRAINING_ONLY"
        or model.get("provider") != "binance_spot"
        or model.get("data_sha256") != expected_data_sha256
        or model.get("target") != training_config.get("target")
    ):
        raise TrainingQualityError("V0.5 model identity or lineage mismatch")
    feature_contract = model.get("feature_contract")
    if (
        not isinstance(feature_contract, dict)
        or feature_contract.get("schema")
        != "binance-spot-daily-direction-features-v0.3"
        or feature_contract.get("ordered_names") != expected_features
    ):
        raise TrainingQualityError("V0.5 model feature contract mismatch")
    models = model.get("models")
    expected_classes = [str(value) for value in training_config.get("asset_classes", ())]
    if (
        not isinstance(models, dict)
        or list(models) != expected_classes
        or not isinstance(models.get("crypto"), dict)
        or models["crypto"].get("status") != "PASS"
    ):
        raise TrainingQualityError("V0.5 model crypto class is not ready")
    for asset_class, class_model in models.items():
        if not isinstance(class_model, dict):
            raise TrainingQualityError(f"V0.5 model class is invalid: {asset_class}")
        if class_model.get("status") == "PASS":
            split_time_ms = _require_non_negative_int(
                class_model.get("split_time_ms"),
                f"model.{asset_class}.split_time_ms",
            )
            if (
                split_time_ms % 86_400_000 != 0
                or split_time_ms < provider_read_start_time_ms
                or split_time_ms >= provider_read_stop_time_ms
            ):
                raise TrainingQualityError(
                    f"V0.5 model split timestamp is invalid: {asset_class}"
                )
            arrays = (
                class_model.get("feature_means"),
                class_model.get("feature_standard_deviations"),
                class_model.get("weights"),
            )
            if (
                class_model.get("feature_names") != expected_features
                or any(
                    not isinstance(values, list)
                    or len(values) != len(expected_features)
                    or any(
                        isinstance(value, bool)
                        or not isinstance(value, (int, float))
                        or not math.isfinite(float(value))
                        for value in values
                    )
                    for values in arrays
                )
                or any(float(value) <= 0 for value in arrays[1])
                or isinstance(class_model.get("bias"), bool)
                or not isinstance(class_model.get("bias"), (int, float))
                or not math.isfinite(float(class_model["bias"]))
            ):
                raise TrainingQualityError(
                    f"V0.5 model class feature payload is invalid: {asset_class}"
                )
        elif (
            class_model.get("status") != "NOT_READY"
            or not isinstance(class_model.get("reason"), str)
        ):
            raise TrainingQualityError(f"V0.5 model class status is invalid: {asset_class}")
    authority = model.get("authority")
    if not isinstance(authority, dict):
        raise TrainingQualityError("V0.5 model authority is missing")
    for key in _FORBIDDEN_MODEL_AUTHORITIES:
        if authority.get(key) is not False:
            raise TrainingQualityError(f"unsafe V0.5 model authority: {key}")
    return {
        "status": "PASS",
        "schema": model["schema"],
        "provider": "binance_spot",
        "data_sha256": expected_data_sha256,
        "feature_contract": feature_contract,
        "live_trading_authorized": False,
    }


def _validate_probability_metrics(value: Any, label: str) -> None:
    if not isinstance(value, dict):
        raise TrainingQualityError(f"{label} must be an object")
    samples = _require_non_negative_int(value.get("samples"), f"{label}.samples")
    if samples <= 0:
        raise TrainingQualityError(f"{label}.samples must be positive")
    for key in ("positive_rate", "accuracy", "brier_score"):
        _require_fraction(value.get(key), f"{label}.{key}")
    log_loss = value.get("log_loss")
    if (
        isinstance(log_loss, bool)
        or not isinstance(log_loss, (int, float))
        or not math.isfinite(float(log_loss))
        or float(log_loss) < 0.0
    ):
        raise TrainingQualityError(f"{label}.log_loss must be finite and non-negative")


def validate_metrics_contract(
    metrics: dict[str, Any],
    *,
    model: dict[str, Any],
    expected_data_sha256: str,
    expected_model_file_sha256: str,
) -> dict[str, Any]:
    expected_data_sha256 = _require_sha256(
        expected_data_sha256, "expected_data_sha256"
    )
    expected_model_file_sha256 = _require_sha256(
        expected_model_file_sha256, "expected_model_file_sha256"
    )
    expected_canonical_sha = sha256_payload(
        (json.dumps(model, sort_keys=True, separators=(",", ":")) + "\n").encode()
    )
    if (
        metrics.get("schema")
        != "binance-spot-daily-direction-training-metrics-v0.5"
        or metrics.get("status") != "PASS"
        or metrics.get("mode") != "RESEARCH_DIAGNOSTICS_ONLY"
        or metrics.get("provider") != "binance_spot"
        or metrics.get("data_sha256") != expected_data_sha256
        or metrics.get("model_file_sha256") != expected_model_file_sha256
        or metrics.get("model_canonical_sha256") != expected_canonical_sha
        or metrics.get("generated_at_utc") != model.get("generated_at_utc")
        or metrics.get("interpretation")
        != "Research diagnostics only; no strategy promotion or trading authority."
    ):
        raise TrainingQualityError("V0.5 metrics identity or lineage mismatch")
    classes = metrics.get("classes")
    if (
        not isinstance(classes, dict)
        or list(classes) != list(model["models"])
        or not isinstance(classes.get("crypto"), dict)
        or classes["crypto"].get("status") != "PASS"
    ):
        raise TrainingQualityError("V0.5 metrics crypto class is not ready")
    for asset_class, class_metrics in classes.items():
        if (
            not isinstance(class_metrics, dict)
            or class_metrics.get("status") != model["models"][asset_class].get("status")
        ):
            raise TrainingQualityError(
                f"V0.5 metrics class status mismatch: {asset_class}"
            )
        examples = _require_non_negative_int(
            class_metrics.get("examples"), f"metrics.{asset_class}.examples"
        )
        if class_metrics["status"] == "PASS":
            _validate_probability_metrics(
                class_metrics.get("train"), f"metrics.{asset_class}.train"
            )
            _validate_probability_metrics(
                class_metrics.get("test"), f"metrics.{asset_class}.test"
            )
            if (
                int(class_metrics["train"]["samples"])
                + int(class_metrics["test"]["samples"])
                > examples
            ):
                raise TrainingQualityError(
                    f"V0.5 metrics sample counts are inconsistent: {asset_class}"
                )
    authority = metrics.get("authority")
    if not isinstance(authority, dict):
        raise TrainingQualityError("V0.5 metrics authority is missing")
    for key in _FORBIDDEN_MODEL_AUTHORITIES:
        if authority.get(key) is not False:
            raise TrainingQualityError(f"unsafe V0.5 metrics authority: {key}")
    return {
        "status": "PASS",
        "schema": metrics["schema"],
        "provider": "binance_spot",
        "data_sha256": expected_data_sha256,
        "model_file_sha256": expected_model_file_sha256,
        "live_trading_authorized": False,
    }


def validate_monthly_review_contract(
    review: dict[str, Any],
    *,
    catalog: dict[str, Any],
    previous_review: dict[str, Any] | None,
    governance_contract: dict[str, Any],
    comparison_baseline: dict[str, Any],
    expected_generated_at_utc: str,
) -> dict[str, Any]:
    markets = catalog.get("markets")
    if not isinstance(markets, list):
        raise TrainingQualityError("monthly review catalog markets are invalid")
    snapshot = {
        str(item["symbol"]): {
            "base_asset": str(item["base_asset"]),
            "quote_asset": str(item["quote_asset"]),
            "asset_class": str(item["asset_class"]),
            "classification_method": str(item["classification_method"]),
            "classification_confidence": str(item["classification_confidence"]),
        }
        for item in markets
    }
    previous_snapshot = (
        previous_review.get("market_snapshot", {})
        if isinstance(previous_review, dict)
        else {}
    )
    baseline_created = previous_review is None
    added = (
        []
        if baseline_created
        else sorted(set(snapshot) - set(previous_snapshot))
    )
    absent = (
        []
        if baseline_created
        else sorted(set(previous_snapshot) - set(snapshot))
    )
    changes = []
    for symbol in sorted(set(snapshot) & set(previous_snapshot)):
        before = previous_snapshot[symbol]
        after = snapshot[symbol]
        if (
            before.get("asset_class") != after["asset_class"]
            or before.get("classification_method")
            != after["classification_method"]
        ):
            changes.append(
                {
                    "symbol": symbol,
                    "previous_asset_class": before.get("asset_class"),
                    "current_asset_class": after["asset_class"],
                    "previous_method": before.get("classification_method"),
                    "current_method": after["classification_method"],
                }
            )
    tokenized = sorted(
        symbol
        for symbol, item in snapshot.items()
        if item["asset_class"] == "tokenized_stock_candidate"
    )
    previous_tokenized = (
        set(tokenized)
        if baseline_created
        else {
            symbol
            for symbol, item in previous_snapshot.items()
            if item.get("asset_class") == "tokenized_stock_candidate"
        }
    )
    expected_tokenized = {
        "count": len(tokenized),
        "symbols": tokenized,
        "added": sorted(set(tokenized) - previous_tokenized),
        "removed": sorted(previous_tokenized - set(tokenized)),
        "classification_is_heuristic": True,
    }
    expected_asset_class_counts: dict[str, int] = {}
    expected_quote_asset_counts: dict[str, int] = {}
    for item in snapshot.values():
        expected_asset_class_counts[item["asset_class"]] = (
            expected_asset_class_counts.get(item["asset_class"], 0) + 1
        )
        expected_quote_asset_counts[item["quote_asset"]] = (
            expected_quote_asset_counts.get(item["quote_asset"], 0) + 1
        )
    expected_asset_class_counts = dict(sorted(expected_asset_class_counts.items()))
    expected_quote_asset_counts = dict(sorted(expected_quote_asset_counts.items()))
    try:
        if (
            not isinstance(expected_generated_at_utc, str)
            or not expected_generated_at_utc.endswith("Z")
            or review.get("generated_at_utc") != expected_generated_at_utc
        ):
            raise ValueError("timestamp mismatch")
        generated_at = datetime.fromisoformat(
            expected_generated_at_utc.replace("Z", "+00:00")
        )
        if generated_at.tzinfo is None or generated_at.utcoffset() != UTC.utcoffset(
            generated_at
        ):
            raise ValueError("timestamp is not UTC")
    except (TypeError, ValueError) as exc:
        raise TrainingQualityError("current monthly review timestamp mismatch") from exc
    if (
        review.get("schema") != "binance-spot-monthly-universe-review-v0.5"
        or review.get("status") != "PASS"
        or review.get("mode") != "RESEARCH_CATALOG_REVIEW_ONLY"
        or review.get("provider") != "binance_spot"
        or review.get("current_catalog_retrieved_at_utc")
        != catalog.get("retrieved_at_utc")
        or review.get("baseline_created") is not baseline_created
        or review.get("market_count") != len(snapshot)
        or review.get("asset_class_counts") != expected_asset_class_counts
        or review.get("quote_asset_counts") != expected_quote_asset_counts
        or review.get("market_snapshot") != snapshot
        or review.get("added_since_previous_monthly_review") != added
        or review.get("absent_from_current_active_catalog") != absent
        or review.get("classification_changes") != changes
        or review.get("tokenized_stock_candidates") != expected_tokenized
        or review.get("interpretation")
        != (
            "Monthly active-catalog and heuristic-classification review only. "
            "A missing symbol is not labeled as delisted without separate provider evidence."
        )
    ):
        raise TrainingQualityError("current monthly review contract mismatch")
    survivorship = review.get("survivorship_bias_review")
    if survivorship != {
        "status": "REVIEW_REQUIRED",
        "current_active_catalog_can_reconstruct_historical_membership": False,
        "absence_from_current_catalog_is_delisting_proof": False,
        "listing_or_delisting_claims_made": False,
        "historical_universe_membership_authorized": False,
    }:
        raise TrainingQualityError("monthly survivorship boundary mismatch")
    authority = review.get("authority")
    if not isinstance(authority, dict):
        raise TrainingQualityError("current monthly review authority is missing")
    for key in (
        "formal_delisting_determination_authorized",
        "historical_universe_membership_authorized",
        "formal_backtest_admission_authorized",
        "automatic_model_promotion_authorized",
        "automatic_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if authority.get(key) is not False:
            raise TrainingQualityError(f"unsafe current monthly review authority: {key}")
    if review.get("governance") != {
        "config": governance_contract,
        "comparison_baseline": comparison_baseline,
    }:
        raise TrainingQualityError("monthly review governance evidence mismatch")
    return {
        "status": "PASS",
        "schema": review["schema"],
        "market_count": len(snapshot),
        "baseline_created": baseline_created,
        "live_trading_authorized": False,
    }


def validate_weekly_review_contract(
    review: dict[str, Any],
    *,
    expected_data_sha256: str,
    training_config: dict[str, Any],
    review_config: dict[str, Any],
) -> dict[str, Any]:
    if not _SHA256_RE.fullmatch(expected_data_sha256):
        raise TrainingQualityError("expected dataset SHA-256 is invalid")
    if review.get("schema") != "binance-spot-weekly-model-review-v0.5":
        raise TrainingQualityError("weekly review schema mismatch")
    if (
        review.get("status") != "PASS"
        or review.get("status_semantics")
        != "PIPELINE_EVIDENCE_COMPLETED_NOT_MODEL_APPROVAL"
        or review.get("mode") != "RESEARCH_DIAGNOSTICS_ONLY"
        or review.get("provider") != "binance_spot"
        or review.get("data_sha256") != expected_data_sha256
    ):
        raise TrainingQualityError("weekly review identity or lineage mismatch")
    walk_forward = review.get("walk_forward")
    classes = walk_forward.get("classes") if isinstance(walk_forward, dict) else None
    expected_classes = [str(value) for value in training_config.get("asset_classes", ())]
    if (
        not isinstance(walk_forward, dict)
        or walk_forward.get("method")
        != "expanding_train_non_overlapping_forward_validation"
        or not isinstance(classes, dict)
        or list(classes) != expected_classes
    ):
        raise TrainingQualityError("weekly review walk-forward contract mismatch")
    expected_fold_count = len(review_config.get("walk_forward_train_fractions", ()))
    baseline_rejected_classes: list[str] = []
    integrity_failed_classes: list[str] = []
    for asset_class, class_result in classes.items():
        if not isinstance(class_result, dict):
            raise TrainingQualityError(
                f"weekly review class result is invalid: {asset_class}"
            )
        _require_non_negative_int(
            class_result.get("example_count"),
            f"weekly_review.{asset_class}.example_count",
        )
        folds = class_result.get("folds")
        if not isinstance(folds, list) or len(folds) not in {0, expected_fold_count}:
            raise TrainingQualityError(
                f"weekly review fold count mismatch: {asset_class}"
            )
        ready = 0
        integrity_fail = 0
        baseline_statuses = []
        previous_train_end: int | None = None
        previous_validation_end: int | None = None
        seen_partition_fingerprints: set[tuple[str, str]] = set()
        for index, fold in enumerate(folds):
            if not isinstance(fold, dict):
                raise TrainingQualityError(
                    f"weekly review fold is invalid: {asset_class}[{index}]"
                )
            status = fold.get("status")
            if status == "NOT_READY":
                _require_non_negative_int(
                    fold.get("train_samples"),
                    f"weekly_review.{asset_class}.fold[{index}].train_samples",
                )
                _require_non_negative_int(
                    fold.get("validation_samples"),
                    f"weekly_review.{asset_class}.fold[{index}].validation_samples",
                )
                continue
            integrity = fold.get("partition_integrity")
            if not isinstance(integrity, dict):
                raise TrainingQualityError(
                    f"weekly review partition evidence is missing: {asset_class}[{index}]"
                )
            if status == "INTEGRITY_FAIL":
                integrity_fail += 1
                train_samples = _require_non_negative_int(
                    fold.get("train_samples"),
                    f"weekly_review.{asset_class}.fold[{index}].train_samples",
                )
                validation_samples = _require_non_negative_int(
                    fold.get("validation_samples"),
                    f"weekly_review.{asset_class}.fold[{index}].validation_samples",
                )
                if (
                    integrity.get("status") != "FAIL"
                    or integrity.get("train_record_count") != train_samples
                    or integrity.get("validation_record_count")
                    != validation_samples
                    or not isinstance(integrity.get("failures"), list)
                    or not integrity.get("failures")
                ):
                    raise TrainingQualityError(
                        f"weekly review integrity failure is inconsistent: {asset_class}[{index}]"
                    )
                continue
            if status != "PASS":
                raise TrainingQualityError(
                    f"weekly review fold status is invalid: {asset_class}[{index}]"
                )
            ready += 1
            if (
                integrity.get("status") != "PASS"
                or integrity.get("failures") != []
                or integrity.get("record_overlap_count") != 0
                or integrity.get("strictly_chronological") is not True
                or integrity.get("holdout_status")
                != "FROZEN_UNOPENED_NOT_ACCESSED"
                or integrity.get("holdout_accessed") is not False
            ):
                raise TrainingQualityError(
                    f"weekly review partition integrity mismatch: {asset_class}[{index}]"
                )
            for key in ("train_records_sha256", "validation_records_sha256"):
                _require_sha256(
                    integrity.get(key),
                    f"weekly_review.{asset_class}.fold[{index}].{key}",
                )
            train_end = _require_non_negative_int(
                fold.get("train_end_exclusive_ms"),
                f"weekly_review.{asset_class}.fold[{index}].train_end_exclusive_ms",
            )
            validation_end = _require_non_negative_int(
                fold.get("validation_end_exclusive_ms"),
                f"weekly_review.{asset_class}.fold[{index}].validation_end_exclusive_ms",
            )
            if (
                train_end >= validation_end
                or (
                    previous_train_end is not None
                    and train_end <= previous_train_end
                )
                or (
                    previous_validation_end is not None
                    and train_end < previous_validation_end
                )
                or (
                    previous_validation_end is not None
                    and validation_end <= previous_validation_end
                )
            ):
                raise TrainingQualityError(
                    f"weekly review fold windows overlap or do not advance: {asset_class}[{index}]"
                )
            previous_train_end = train_end
            previous_validation_end = validation_end
            fingerprint = (
                str(integrity["train_records_sha256"]),
                str(integrity["validation_records_sha256"]),
            )
            if fingerprint in seen_partition_fingerprints:
                raise TrainingQualityError(
                    f"weekly review fold partition was duplicated: {asset_class}[{index}]"
                )
            seen_partition_fingerprints.add(fingerprint)
            train_samples = _require_non_negative_int(
                fold.get("train_samples"),
                f"weekly_review.{asset_class}.fold[{index}].train_samples",
            )
            _validate_probability_metrics(
                fold.get("validation"),
                f"weekly_review.{asset_class}.fold[{index}].validation",
            )
            baseline = fold.get("baseline_comparison")
            if (
                not isinstance(baseline, dict)
                or baseline.get("status") not in {"PASS", "REJECT"}
                or baseline.get("baseline")
                != "train_prevalence_constant_probability"
                or baseline.get("required_positive_improvements")
                != review_config["quality_gate"]["required_baseline_improvements"]
                or baseline.get("candidate_metrics") != fold.get("validation")
            ):
                raise TrainingQualityError(
                    f"weekly review baseline contract mismatch: {asset_class}[{index}]"
                )
            _validate_probability_metrics(
                baseline.get("baseline_metrics"),
                f"weekly_review.{asset_class}.fold[{index}].baseline",
            )
            if (
                train_samples != integrity.get("train_record_count")
                or fold["validation"].get("samples")
                != integrity.get("validation_record_count")
                or baseline["baseline_metrics"].get("samples")
                != fold["validation"].get("samples")
            ):
                raise TrainingQualityError(
                    f"weekly review fold sample lineage mismatch: {asset_class}[{index}]"
                )
            baseline_probability = baseline["baseline_metrics"].get(
                "train_positive_rate_probability"
            )
            _require_fraction(
                baseline_probability,
                f"weekly_review.{asset_class}.fold[{index}].baseline_probability",
            )
            improvements = baseline.get("improvements")
            if not isinstance(improvements, dict) or set(improvements) != {
                "accuracy",
                "log_loss",
                "brier_score",
            }:
                raise TrainingQualityError(
                    f"weekly review improvement contract mismatch: {asset_class}[{index}]"
                )
            for name, value in improvements.items():
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                ):
                    raise TrainingQualityError(
                        f"weekly review improvement is invalid: {asset_class}[{index}].{name}"
                    )
            candidate_metrics = baseline["candidate_metrics"]
            baseline_metrics = baseline["baseline_metrics"]
            expected_improvements = {
                "accuracy": float(candidate_metrics["accuracy"])
                - float(baseline_metrics["accuracy"]),
                "log_loss": float(baseline_metrics["log_loss"])
                - float(candidate_metrics["log_loss"]),
                "brier_score": float(baseline_metrics["brier_score"])
                - float(candidate_metrics["brier_score"]),
            }
            if any(
                not math.isclose(
                    float(improvements[name]),
                    expected_value,
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                )
                for name, expected_value in expected_improvements.items()
            ):
                raise TrainingQualityError(
                    f"weekly review improvement arithmetic mismatch: {asset_class}[{index}]"
                )
            required_improvements = review_config["quality_gate"][
                "required_baseline_improvements"
            ]
            expected_baseline_fold_status = (
                "PASS"
                if all(expected_improvements[name] > 0.0 for name in required_improvements)
                else "REJECT"
            )
            baseline_brier = float(baseline_metrics["brier_score"])
            expected_brier_skill = (
                1.0 - float(candidate_metrics["brier_score"]) / baseline_brier
                if baseline_brier > 0.0
                else 0.0
            )
            brier_skill = baseline.get("brier_skill_score")
            if (
                baseline.get("status") != expected_baseline_fold_status
                or isinstance(brier_skill, bool)
                or not isinstance(brier_skill, (int, float))
                or not math.isfinite(float(brier_skill))
                or not math.isclose(
                    float(brier_skill),
                    expected_brier_skill,
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                )
            ):
                raise TrainingQualityError(
                    f"weekly review baseline arithmetic mismatch: {asset_class}[{index}]"
                )
            baseline_statuses.append(baseline["status"])
        expected_class_status = (
            "FAIL" if integrity_fail else "PASS" if ready else "NOT_READY"
        )
        expected_baseline_status = (
            "PASS"
            if ready == expected_fold_count
            and all(value == "PASS" for value in baseline_statuses)
            else "REJECT"
            if ready
            else "NOT_READY"
        )
        if (
            class_result.get("status") != expected_class_status
            or class_result.get("baseline_quality_status")
            != expected_baseline_status
        ):
            raise TrainingQualityError(
                f"weekly review class summary mismatch: {asset_class}"
            )
        if expected_class_status == "FAIL":
            integrity_failed_classes.append(asset_class)
        if expected_class_status == "PASS" and expected_baseline_status != "PASS":
            baseline_rejected_classes.append(asset_class)
    if classes.get("crypto", {}).get("status") != "PASS":
        raise TrainingQualityError("weekly review crypto walk-forward is not ready")

    cost_scenarios = review.get("cost_and_drawdown_sensitivity")
    configured_costs = review_config.get("cost_scenarios")
    if (
        not isinstance(cost_scenarios, list)
        or not isinstance(configured_costs, list)
        or len(cost_scenarios) != len(configured_costs)
    ):
        raise TrainingQualityError("weekly review cost scenarios are missing")
    for actual, configured in zip(cost_scenarios, configured_costs):
        if (
            not isinstance(actual, dict)
            or actual.get("name") != configured.get("name")
            or actual.get("taker_fee_bps_each_side")
            != float(configured["taker_fee_bps_each_side"])
            or actual.get("slippage_bps_each_fill")
            != float(configured["slippage_bps_each_fill"])
        ):
            raise TrainingQualityError("weekly review cost scenario identity mismatch")
        signal_count = _require_non_negative_int(
            actual.get("signal_count"), "weekly_review.cost.signal_count"
        )
        active_days = _require_non_negative_int(
            actual.get("active_days"), "weekly_review.cost.active_days"
        )
        if active_days > signal_count:
            raise TrainingQualityError("weekly review active-day count is inconsistent")
        for key in (
            "mean_net_signal_return",
            "diagnostic_final_equity_usd",
            "diagnostic_net_growth_pct",
            "diagnostic_max_drawdown_pct",
        ):
            value = actual.get(key)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
            ):
                raise TrainingQualityError(f"weekly review cost metric is invalid: {key}")
        if (
            float(actual["diagnostic_final_equity_usd"]) < 0.0
            or not 0.0 <= float(actual["diagnostic_max_drawdown_pct"]) <= 100.0
        ):
            raise TrainingQualityError("weekly review drawdown evidence is invalid")
        initial_equity = review_config.get("diagnostic_initial_equity_usd")
        if (
            isinstance(initial_equity, bool)
            or not isinstance(initial_equity, (int, float))
            or not math.isfinite(float(initial_equity))
            or float(initial_equity) <= 0.0
        ):
            raise TrainingQualityError("configured diagnostic equity is invalid")
        expected_growth = round(
            (float(actual["diagnostic_final_equity_usd"]) / float(initial_equity) - 1.0)
            * 100.0,
            8,
        )
        if not math.isclose(
            float(actual["diagnostic_net_growth_pct"]),
            expected_growth,
            rel_tol=1e-12,
            abs_tol=1e-8,
        ):
            raise TrainingQualityError(
                "weekly review final equity and net growth do not reconcile"
            )

    exposure = review.get("asset_exposure")
    if not isinstance(exposure, dict):
        raise TrainingQualityError("weekly review exposure evidence is missing")
    exposure_signal_count = _require_non_negative_int(
        exposure.get("signal_count"), "weekly_review.exposure.signal_count"
    )
    maximum_concurrent = _require_non_negative_int(
        exposure.get("maximum_concurrent_symbols"),
        "weekly_review.exposure.maximum_concurrent_symbols",
    )
    maximum_share = _require_fraction(
        exposure.get("maximum_symbol_signal_share"),
        "weekly_review.exposure.maximum_symbol_signal_share",
    )
    if (
        maximum_concurrent > exposure_signal_count
        or any(item["signal_count"] != exposure_signal_count for item in cost_scenarios)
    ):
        raise TrainingQualityError("weekly review exposure counts are inconsistent")
    for name in ("symbol_signal_shares", "asset_class_signal_shares"):
        shares = exposure.get(name)
        if not isinstance(shares, dict):
            raise TrainingQualityError(f"weekly review {name} is missing")
        for label, value in shares.items():
            if not isinstance(label, str):
                raise TrainingQualityError(f"weekly review {name} key is invalid")
            _require_fraction(value, f"weekly_review.{name}.{label}")
    symbol_shares = exposure["symbol_signal_shares"]
    asset_class_shares = exposure["asset_class_signal_shares"]
    if exposure_signal_count == 0:
        if (
            maximum_share != 0.0
            or maximum_concurrent != 0
            or symbol_shares
            or asset_class_shares
        ):
            raise TrainingQualityError(
                "weekly review zero-signal exposure is inconsistent"
            )
    elif (
        maximum_concurrent <= 0
        or not symbol_shares
        or not asset_class_shares
        or not math.isclose(sum(symbol_shares.values()), 1.0, abs_tol=1e-9)
        or not math.isclose(sum(asset_class_shares.values()), 1.0, abs_tol=1e-9)
        or not math.isclose(max(symbol_shares.values()), maximum_share, abs_tol=1e-12)
    ):
        raise TrainingQualityError("weekly review exposure shares are inconsistent")

    quality = review.get("model_quality_gate")
    if not isinstance(quality, dict) or quality.get("status") not in {"PASS", "REJECT"}:
        raise TrainingQualityError("weekly review model-quality result is missing")
    if quality.get("promotion_eligible") is not False:
        raise TrainingQualityError("weekly review must have zero promotion eligibility")
    failures = quality.get("failures")
    if (
        not isinstance(failures, list)
        or any(not isinstance(value, str) for value in failures)
        or len(failures) != len(set(failures))
        or quality.get("policy") != review_config.get("quality_gate")
        or (quality.get("status") == "PASS" and failures)
        or (quality.get("status") == "REJECT" and not failures)
    ):
        raise TrainingQualityError("weekly review model-quality evidence is inconsistent")
    configured_scenario = next(
        (
            item
            for item in cost_scenarios
            if item["name"] == review_config["quality_gate"]["cost_scenario_name"]
        ),
        None,
    )
    if quality.get("evaluated_cost_scenario") != configured_scenario:
        raise TrainingQualityError("weekly review evaluated cost scenario mismatch")
    expected_failures: list[str] = []
    baseline_rejected_classes = sorted(baseline_rejected_classes)
    integrity_failed_classes = sorted(integrity_failed_classes)
    if baseline_rejected_classes:
        expected_failures.append(
            "READY_CLASSES_DID_NOT_BEAT_NAIVE_BASELINE_IN_EVERY_FOLD"
        )
    if integrity_failed_classes:
        expected_failures.append("CLASS_PARTITION_INTEGRITY_FAILED")
    quality_policy = review_config["quality_gate"]
    if configured_scenario is None:
        expected_failures.append("CONFIGURED_COST_SCENARIO_MISSING")
    else:
        if int(configured_scenario["signal_count"]) <= 0:
            expected_failures.append("NO_OUT_OF_FOLD_LONG_SIGNALS")
        if float(configured_scenario["diagnostic_net_growth_pct"]) <= float(
            quality_policy["minimum_net_growth_pct"]
        ):
            expected_failures.append("NET_GROWTH_BELOW_POLICY")
        if float(configured_scenario["diagnostic_max_drawdown_pct"]) > float(
            quality_policy["maximum_diagnostic_drawdown_pct"]
        ):
            expected_failures.append("DRAWDOWN_ABOVE_POLICY")
    if maximum_share > float(quality_policy["maximum_symbol_signal_share"]):
        expected_failures.append("SYMBOL_SIGNAL_CONCENTRATION_ABOVE_POLICY")
    expected_quality_status = "PASS" if not expected_failures else "REJECT"
    if (
        quality.get("status") != expected_quality_status
        or quality.get("failures") != expected_failures
        or quality.get("baseline_rejected_asset_classes")
        != baseline_rejected_classes
        or quality.get("integrity_failed_asset_classes")
        != integrity_failed_classes
        or quality.get("interpretation")
        != (
            "Research evidence gate only. PASS does not authorize model promotion, "
            "backtest admission or trading."
        )
    ):
        raise TrainingQualityError("weekly review model-quality semantics mismatch")
    lineage = review.get("lineage")
    expected_features = training_config.get("feature_names")
    if (
        not isinstance(lineage, dict)
        or lineage.get("schema") != "binance-spot-weekly-training-lineage-v0.5"
        or lineage.get("provider") != "binance_spot"
        or lineage.get("dataset_sha256") != expected_data_sha256
        or lineage.get("feature_contract_sha256") != sha256_json(expected_features)
        or lineage.get("training_config_sha256") != sha256_json(training_config)
        or lineage.get("review_config_sha256") != sha256_json(review_config)
        or lineage.get("holdout_status") != "FROZEN_UNOPENED_NOT_ACCESSED"
        or lineage.get("holdout_accessed") is not False
        or lineage.get("source_switch_authorized") is not False
    ):
        raise TrainingQualityError("weekly review lineage crossed a safety boundary")
    authority = review.get("authority")
    if not isinstance(authority, dict):
        raise TrainingQualityError("weekly review authority is missing")
    for key in (
        "formal_backtest_admission_authorized",
        "automatic_model_promotion_authorized",
        "automatic_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if authority.get(key) is not False:
            raise TrainingQualityError(f"unsafe weekly review authority: {key}")
    return {
        "status": "PASS",
        "schema": review["schema"],
        "model_quality_status": quality["status"],
        "dataset_sha256": expected_data_sha256,
        "holdout_accessed": False,
        "promotion_eligible": False,
    }


def sha256_payload(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()
