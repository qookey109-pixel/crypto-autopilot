"""Bounded public snapshot execution for Pionex Research Universe 150+ V0.1."""
from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from typing import Any, Mapping, Protocol

from ..models import BookTicker, MarketTicker
from .pionex_universe_v0_1 import build_universe, validate_config as validate_selection_config


class UniverseExecutionRejected(RuntimeError):
    pass


class SnapshotClient(Protocol):
    def list_perpetual_symbols(self) -> list[str]: ...
    def list_perpetual_tickers(self) -> list[MarketTicker]: ...
    def list_perpetual_book_tickers(self) -> list[BookTicker]: ...


def _parse_utc(value: str, *, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise UniverseExecutionRejected(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise UniverseExecutionRejected(f"{field} must be explicit UTC")
    return parsed


def validate_execution_config(
    config: Mapping[str, Any],
    *,
    selection_config_bytes: bytes,
    alternative_registry_bytes: bytes,
) -> dict[str, object]:
    if config.get("version") != "0.1.0":
        raise UniverseExecutionRejected("unexpected execution config version")
    if config.get("status") != "AUTHORIZED_AFTER_PROTECTED_MAIN_MERGE_AWAITING_WORKFLOW_WIRING":
        raise UniverseExecutionRejected("execution status changed")
    if config.get("provider") != "pionex_public_futures":
        raise UniverseExecutionRejected("provider changed")

    selection_contract = config.get("selection_contract")
    if not isinstance(selection_contract, Mapping):
        raise UniverseExecutionRejected("selection contract missing")
    selection_sha = hashlib.sha256(selection_config_bytes).hexdigest()
    if selection_contract.get("config") != "config/pionex_research_universe_v0_1.json":
        raise UniverseExecutionRejected("selection config path changed")
    if selection_contract.get("config_sha256") != selection_sha:
        raise UniverseExecutionRejected("selection config SHA-256 mismatch")
    alternative_sha = hashlib.sha256(alternative_registry_bytes).hexdigest()
    if selection_contract.get("alternative_registry") != "config/pionex_alternative_assets_v0_1.json":
        raise UniverseExecutionRejected("alternative registry path changed")
    if selection_contract.get("alternative_registry_sha256") != alternative_sha:
        raise UniverseExecutionRejected("alternative registry SHA-256 mismatch")

    try:
        selection_config = json.loads(selection_config_bytes)
    except (TypeError, ValueError) as exc:
        raise UniverseExecutionRejected("selection config is not valid JSON") from exc
    validate_selection_config(
        selection_config,
        alternative_registry_bytes=alternative_registry_bytes,
    )

    execution = config.get("execution")
    if not isinstance(execution, Mapping):
        raise UniverseExecutionRejected("execution contract missing")
    not_before = _parse_utc(str(execution.get("not_before_utc")), field="not_before_utc")
    stop = _parse_utc(str(execution.get("stop_exclusive_utc")), field="stop_exclusive_utc")
    if not_before >= stop:
        raise UniverseExecutionRejected("execution window is empty")
    if int(execution.get("provider_request_count_exact") or 0) != 3:
        raise UniverseExecutionRejected("provider request count must remain exactly three")
    if execution.get("endpoint_order") != [
        "/api/v1/common/symbols?type=PERP&status=TRADING",
        "/api/v1/market/tickers?type=PERP",
        "/api/v1/market/bookTickers?type=PERP",
    ]:
        raise UniverseExecutionRejected("provider endpoint order changed")
    if float(execution.get("requests_per_second") or 0.0) != 3.0:
        raise UniverseExecutionRejected("request pace changed")
    if float(execution.get("request_timeout_seconds") or 0.0) != 15.0:
        raise UniverseExecutionRejected("request timeout changed")
    if execution.get("automatic_retries") != 0:
        raise UniverseExecutionRejected("automatic retries must remain zero")
    for key in ("github_actions_main_only", "workflow_dispatch_only"):
        if execution.get(key) is not True:
            raise UniverseExecutionRejected(f"execution.{key} must remain true")
    if int(execution.get("accepted_run_attempt") or 0) != 1:
        raise UniverseExecutionRejected("only first workflow attempt is accepted")
    if execution.get("workflow_wiring_included_by_this_stage") is not False:
        raise UniverseExecutionRejected("workflow wiring must remain outside this stage")

    output = config.get("output")
    if not isinstance(output, Mapping):
        raise UniverseExecutionRejected("output contract missing")
    required_output_true = ("secret_free_json_report", "include_selected_market_metrics")
    if any(output.get(key) is not True for key in required_output_true):
        raise UniverseExecutionRejected("required output contract weakened")
    for key in ("persist_raw_provider_payloads", "persist_account_data", "r2_read", "r2_write"):
        if output.get(key) is not False:
            raise UniverseExecutionRejected(f"output.{key} must remain false")

    expected_authority = {
        "public_pionex_snapshot_reads_after_merge": True,
        "private_api": False,
        "api_key_required": False,
        "r2_read": False,
        "r2_write": False,
        "historical_materialization": False,
        "holdout_access": False,
        "training": False,
        "formal_backtest_admission": False,
        "strategy_change": False,
        "source_switch": False,
        "trade_plan": False,
        "real_money_orders": False,
        "live_trading": False,
    }
    if config.get("authority") != expected_authority:
        raise UniverseExecutionRejected("execution authority widened or changed")

    return selection_config


def require_execution_window(
    config: Mapping[str, Any],
    *,
    observed_at: datetime,
) -> None:
    if observed_at.tzinfo is None or observed_at.utcoffset() != UTC.utcoffset(observed_at):
        raise UniverseExecutionRejected("observed_at must be explicit UTC")
    execution = config["execution"]
    not_before = _parse_utc(str(execution["not_before_utc"]), field="not_before_utc")
    stop = _parse_utc(str(execution["stop_exclusive_utc"]), field="stop_exclusive_utc")
    if observed_at < not_before:
        raise UniverseExecutionRejected("execution is before not-before boundary")
    if observed_at >= stop:
        raise UniverseExecutionRejected("execution authority expired")


def capture_public_snapshot(
    config: Mapping[str, Any],
    *,
    selection_config_bytes: bytes,
    alternative_registry_bytes: bytes,
    client: SnapshotClient,
    observed_at: datetime,
) -> dict[str, object]:
    selection_config = validate_execution_config(
        config,
        selection_config_bytes=selection_config_bytes,
        alternative_registry_bytes=alternative_registry_bytes,
    )
    require_execution_window(config, observed_at=observed_at)

    symbols = client.list_perpetual_symbols()
    tickers = client.list_perpetual_tickers()
    books = client.list_perpetual_book_tickers()

    result = build_universe(
        selection_config,
        alternative_registry_bytes=alternative_registry_bytes,
        live_symbols=symbols,
        tickers=tickers,
        book_tickers=books,
    )
    return {
        **result,
        "schema": "pionex-research-universe-run-report-v0.1",
        "status": "PASS",
        "observed_at_utc": observed_at.isoformat().replace("+00:00", "Z"),
        "provider_request_count": 3,
        "provider_request_order": list(config["execution"]["endpoint_order"]),
        "api_key_used": False,
        "private_account_data_accessed": False,
        "raw_provider_payloads_persisted": False,
        "r2_accessed": False,
        "holdout_accessed": False,
        "historical_materialization_authorized": False,
        "formal_backtest_admission_authorized": False,
        "real_money_orders_authorized": False,
        "live_trading_authorized": False,
    }
