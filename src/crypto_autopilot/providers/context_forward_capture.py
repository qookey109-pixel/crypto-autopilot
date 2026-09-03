from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


SNAPSHOT_SCHEMA = "context-forward-snapshot-v0.1"
PROVIDER = "coinpaprika"
GLOBAL_URL = "https://api.coinpaprika.com/v1/global"
ETH_TICKER_URL = "https://api.coinpaprika.com/v1/tickers/eth-ethereum"


class ContextForwardCaptureError(ValueError):
    """Raised when prepared context evidence violates the frozen V0.1 contract."""


class ContextForwardCaptureNotAuthorized(ContextForwardCaptureError):
    """Raised before transport when V0.1 provider execution remains unauthorized."""


@dataclass(frozen=True, slots=True)
class ContextForwardSnapshot:
    schema: str
    provider: str
    capture_timestamp_ms: int
    global_provider_timestamp_ms: int
    eth_provider_timestamp_ms: int
    provider_component_skew_ms: int
    global_provider_age_ms: int
    eth_provider_age_ms: int
    total_market_cap_usd: float
    btc_dominance_pct: float
    btc_market_cap_usd: float
    eth_market_cap_usd: float
    total3_value: float
    global_endpoint: str
    eth_ticker_endpoint: str
    global_raw_payload_sha256: str
    eth_raw_payload_sha256: str
    forward_only: bool = True
    historical_backfill_claim: bool = False
    authority: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_object(payload: bytes, *, label: str) -> Mapping[str, Any]:
    if not isinstance(payload, bytes) or not payload:
        raise ContextForwardCaptureError(f"{label} raw payload must be non-empty bytes")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ContextForwardCaptureError(f"{label} raw payload must be UTF-8") from exc

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ContextForwardCaptureError(f"{label} payload contains duplicate key: {key}")
            result[key] = value
        return result

    try:
        decoded = json.loads(text, object_pairs_hook=reject_duplicate_keys)
    except ContextForwardCaptureError:
        raise
    except (json.JSONDecodeError, TypeError) as exc:
        raise ContextForwardCaptureError(f"{label} raw payload must be valid JSON") from exc
    if not isinstance(decoded, Mapping):
        raise ContextForwardCaptureError(f"{label} payload must be a JSON object")
    return decoded


def _finite_number(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or value is None:
        raise ContextForwardCaptureError(f"{field} must be a finite number")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ContextForwardCaptureError(f"{field} must be a finite number") from exc
    if not math.isfinite(parsed):
        raise ContextForwardCaptureError(f"{field} must be a finite number")
    return parsed


def _positive_number(value: Any, *, field: str) -> float:
    parsed = _finite_number(value, field=field)
    if parsed <= 0.0:
        raise ContextForwardCaptureError(f"{field} must be positive")
    return parsed


def _unix_seconds_to_ms(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContextForwardCaptureError(f"{field} must be integer Unix seconds")
    if value <= 0:
        raise ContextForwardCaptureError(f"{field} must be positive Unix seconds")
    return value * 1000


def _iso8601_utc_to_ms(value: Any, *, field: str) -> int:
    if not isinstance(value, str) or not value:
        raise ContextForwardCaptureError(f"{field} must be an ISO-8601 UTC string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContextForwardCaptureError(f"{field} must be an ISO-8601 UTC string") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ContextForwardCaptureError(f"{field} must be explicit UTC")
    return int(parsed.timestamp() * 1000)


def _validate_capture_timestamp(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ContextForwardCaptureError("capture_timestamp_ms must be a positive integer")
    return value


def _validate_provider_time(
    *,
    provider_timestamp_ms: int,
    capture_timestamp_ms: int,
    max_provider_age_ms: int,
    label: str,
) -> int:
    if provider_timestamp_ms > capture_timestamp_ms:
        raise ContextForwardCaptureError(f"{label} provider timestamp cannot be in the future")
    age_ms = capture_timestamp_ms - provider_timestamp_ms
    if age_ms > max_provider_age_ms:
        raise ContextForwardCaptureError(f"{label} provider data is too stale")
    return age_ms


def validate_context_forward_capture_config(
    config: Mapping[str, Any], *, source_lineage_bytes: bytes
) -> None:
    if config.get("version") != "0.1.0":
        raise ContextForwardCaptureError("unexpected context forward capture version")
    if config.get("status") != "PREPARED_NOT_ACTIVE":
        raise ContextForwardCaptureError("V0.1 must remain PREPARED_NOT_ACTIVE")

    source = config.get("source_lineage") or {}
    if source.get("path") != "config/context_source_lineage_v0_1.json":
        raise ContextForwardCaptureError("source-lineage path changed")
    if source.get("sha256") != sha256_bytes(source_lineage_bytes):
        raise ContextForwardCaptureError("source-lineage SHA-256 mismatch")
    try:
        source_lineage = json.loads(source_lineage_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContextForwardCaptureError("source-lineage bytes are invalid") from exc
    if source_lineage.get("version") != source.get("required_version"):
        raise ContextForwardCaptureError("source-lineage version mismatch")
    candidate = source_lineage.get("forward_candidate") or {}
    if candidate.get("provider") != source.get("required_provider") or candidate.get(
        "candidate_use"
    ) != source.get("required_candidate_use"):
        raise ContextForwardCaptureError("source-lineage forward candidate drifted")
    if (source_lineage.get("authority") or {}).get("provider_fetch_authorized") is not False:
        raise ContextForwardCaptureError("source-lineage unexpectedly grants provider access")

    zero_cost = config.get("zero_cost_policy") or {}
    if zero_cost.get("monthly_budget_usd") != 0:
        raise ContextForwardCaptureError("monthly budget must remain zero")
    if zero_cost.get("paid_fallback_allowed") is not False:
        raise ContextForwardCaptureError("paid fallback must remain disabled")
    if zero_cost.get("provider_plan") != "Free":
        raise ContextForwardCaptureError("provider plan must remain Free")
    if int(zero_cost.get("documented_provider_request_limit_per_month") or 0) != 20000:
        raise ContextForwardCaptureError("provider free request allowance changed")

    provider = config.get("provider") or {}
    expected_provider = {
        "name": PROVIDER,
        "base_url": "https://api.coinpaprika.com/v1/",
        "authentication_required": False,
        "global_endpoint": "/global",
        "eth_ticker_endpoint": "/tickers/eth-ethereum",
        "global_last_updated_encoding": "unix_seconds",
        "eth_last_updated_encoding": "iso8601_utc",
    }
    if provider != expected_provider:
        raise ContextForwardCaptureError("CoinPaprika provider contract changed")

    capture = config.get("capture_contract") or {}
    required_capture_values = {
        "snapshot_schema": SNAPSHOT_SCHEMA,
        "forward_only": True,
        "historical_backfill_claim_allowed": False,
        "max_requests_per_capture": 2,
        "automatic_retries": 0,
        "max_component_skew_seconds": 600,
        "max_provider_age_seconds": 900,
        "raw_payload_sha256_required": True,
        "raw_payload_persistence_authorized": False,
        "capture_timestamp_required": True,
        "provider_timestamps_required": True,
        "same_provider_components_required": True,
        "missing_component_policy": "FAIL_CLOSED",
        "nonfinite_numeric_policy": "FAIL_CLOSED",
        "future_provider_timestamp_policy": "FAIL_CLOSED",
        "negative_or_zero_total3_policy": "FAIL_CLOSED",
        "interpolation_authorized": False,
        "carry_backward_authorized": False,
        "carry_forward_authorized": False,
    }
    if capture != required_capture_values:
        raise ContextForwardCaptureError("capture contract changed")

    transport = config.get("transport_preparation") or {}
    if transport != {
        "injected_transport_contract_prepared": True,
        "default_network_transport_implemented": False,
        "provider_request_entrypoint_enabled": False,
        "must_reject_before_first_request_when_unauthorized": True,
    }:
        raise ContextForwardCaptureError("transport preparation boundary changed")

    storage = config.get("storage") or {}
    if storage.get("production_r2_namespace") is not None:
        raise ContextForwardCaptureError("V0.1 cannot define a production R2 namespace")
    for key in (
        "local_raw_payload_persistence_authorized",
        "production_r2_read_authorized",
        "production_r2_write_authorized",
    ):
        if storage.get(key) is not False:
            raise ContextForwardCaptureError(f"storage.{key} must remain false")

    authority = config.get("authority") or {}
    if authority.get("research_only") is not True:
        raise ContextForwardCaptureError("V0.1 must remain research-only")
    for key, value in authority.items():
        if key != "research_only" and value is not False:
            raise ContextForwardCaptureError(f"authority.{key} must remain false")


def build_context_forward_snapshot(
    *,
    config: Mapping[str, Any],
    source_lineage_bytes: bytes,
    global_payload: bytes,
    eth_payload: bytes,
    capture_timestamp_ms: int,
) -> ContextForwardSnapshot:
    """Build deterministic synthetic/fixture evidence without performing network I/O."""

    validate_context_forward_capture_config(config, source_lineage_bytes=source_lineage_bytes)
    capture_ms = _validate_capture_timestamp(capture_timestamp_ms)
    capture_contract = config["capture_contract"]
    max_age_ms = int(capture_contract["max_provider_age_seconds"]) * 1000
    max_skew_ms = int(capture_contract["max_component_skew_seconds"]) * 1000

    global_data = _json_object(global_payload, label="global")
    eth_data = _json_object(eth_payload, label="eth ticker")

    total_market_cap = _positive_number(
        global_data.get("market_cap_usd"), field="global.market_cap_usd"
    )
    btc_dominance = _finite_number(
        global_data.get("bitcoin_dominance_percentage"),
        field="global.bitcoin_dominance_percentage",
    )
    if not 0.0 < btc_dominance < 100.0:
        raise ContextForwardCaptureError(
            "global.bitcoin_dominance_percentage must be strictly between 0 and 100"
        )
    global_provider_ms = _unix_seconds_to_ms(
        global_data.get("last_updated"), field="global.last_updated"
    )

    if eth_data.get("id") != "eth-ethereum" or eth_data.get("symbol") != "ETH":
        raise ContextForwardCaptureError("ETH ticker identity mismatch")
    eth_provider_ms = _iso8601_utc_to_ms(
        eth_data.get("last_updated"), field="eth ticker.last_updated"
    )
    quotes = eth_data.get("quotes")
    if not isinstance(quotes, Mapping) or not isinstance(quotes.get("USD"), Mapping):
        raise ContextForwardCaptureError("eth ticker quotes.USD is required")
    eth_market_cap = _positive_number(
        quotes["USD"].get("market_cap"), field="eth ticker.quotes.USD.market_cap"
    )

    global_age_ms = _validate_provider_time(
        provider_timestamp_ms=global_provider_ms,
        capture_timestamp_ms=capture_ms,
        max_provider_age_ms=max_age_ms,
        label="global",
    )
    eth_age_ms = _validate_provider_time(
        provider_timestamp_ms=eth_provider_ms,
        capture_timestamp_ms=capture_ms,
        max_provider_age_ms=max_age_ms,
        label="eth ticker",
    )
    skew_ms = abs(global_provider_ms - eth_provider_ms)
    if skew_ms > max_skew_ms:
        raise ContextForwardCaptureError("provider component timestamps are too far apart")

    btc_market_cap = total_market_cap * btc_dominance / 100.0
    total3_value = total_market_cap - btc_market_cap - eth_market_cap
    if not math.isfinite(total3_value) or total3_value <= 0.0:
        raise ContextForwardCaptureError("derived total3_value must be finite and positive")

    return ContextForwardSnapshot(
        schema=SNAPSHOT_SCHEMA,
        provider=PROVIDER,
        capture_timestamp_ms=capture_ms,
        global_provider_timestamp_ms=global_provider_ms,
        eth_provider_timestamp_ms=eth_provider_ms,
        provider_component_skew_ms=skew_ms,
        global_provider_age_ms=global_age_ms,
        eth_provider_age_ms=eth_age_ms,
        total_market_cap_usd=total_market_cap,
        btc_dominance_pct=btc_dominance,
        btc_market_cap_usd=btc_market_cap,
        eth_market_cap_usd=eth_market_cap,
        total3_value=total3_value,
        global_endpoint=GLOBAL_URL,
        eth_ticker_endpoint=ETH_TICKER_URL,
        global_raw_payload_sha256=sha256_bytes(global_payload),
        eth_raw_payload_sha256=sha256_bytes(eth_payload),
    )


def prepared_collect_context_forward_snapshot(
    *,
    config: Mapping[str, Any],
    source_lineage_bytes: bytes,
    transport: Callable[[str], bytes],
    capture_timestamp_ms: int,
) -> ContextForwardSnapshot:
    """Prepared transport boundary that must refuse before the first request in V0.1."""

    validate_context_forward_capture_config(config, source_lineage_bytes=source_lineage_bytes)
    _validate_capture_timestamp(capture_timestamp_ms)
    if (config.get("authority") or {}).get("provider_fetch_authorized") is not True:
        raise ContextForwardCaptureNotAuthorized(
            "Context Forward Capture V0.1 provider execution is not authorized"
        )

    # This branch is unreachable under the frozen V0.1 config. It intentionally
    # documents the future injected-transport shape without implementing a
    # default network client or granting execution authority.
    global_payload = transport(GLOBAL_URL)
    eth_payload = transport(ETH_TICKER_URL)
    return build_context_forward_snapshot(
        config=config,
        source_lineage_bytes=source_lineage_bytes,
        global_payload=global_payload,
        eth_payload=eth_payload,
        capture_timestamp_ms=capture_timestamp_ms,
    )
