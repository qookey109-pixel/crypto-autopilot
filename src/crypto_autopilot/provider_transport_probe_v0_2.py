from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .binance_historical import pionex_perp_to_binance_usdm


PROTOCOL = Path("config/provider_equivalence_v0_2_transport_probe_v0_1.json")
BLOCKER = Path(
    "research/receipts/2026-08-19-provider-equivalence-v0-2-transport-blocked.json"
)
M1A = Path("research/receipts/2026-08-17-m1a-pionex.json")

EXPECTED_BLOCKER_STAGE = (
    "PROVIDER_EQUIVALENCE_V0_2_METADATA_TRANSPORT_BLOCKED_CAPTURE_SUSPENDED"
)
EXPECTED_NEXT_STAGE = "EXECUTION_TRANSPORT_CONNECTIVITY_PASS_BEFORE_NEW_FORWARD_HOLDOUT_FREEZE"


@dataclass(frozen=True)
class ProbeError(Exception):
    kind: str
    provider: str
    detail: str
    http_status: int | None = None

    def __str__(self) -> str:
        return f"{self.provider}: {self.kind}: {self.detail}"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def load_probe_authority() -> tuple[dict[str, Any], tuple[str, ...], tuple[str, ...]]:
    protocol = _load_json(PROTOCOL)
    blocker = _load_json(BLOCKER)
    m1a = _load_json(M1A)

    if protocol.get("status") != "PROTOCOL_FROZEN_BEFORE_TRANSPORT_EVIDENCE":
        raise RuntimeError("local transport probe protocol is not frozen")
    if blocker.get("status") != "PASS" or blocker.get("stage") != EXPECTED_BLOCKER_STAGE:
        raise RuntimeError("transport blocker authority is not frozen PASS")
    if blocker.get("next_required_stage") != EXPECTED_NEXT_STAGE:
        raise RuntimeError("transport blocker next stage changed")

    holdout = blocker.get("holdout_state") or {}
    boundary = blocker.get("authorization_boundary") or {}
    if holdout.get("replacement_holdout_frozen") is not False:
        raise RuntimeError("replacement holdout unexpectedly frozen")
    for key in (
        "metadata_capture_execution_authorized",
        "metadata_only_r2_writes_authorized",
        "holdout_candle_access_authorized",
        "holdout_evaluation_authorized",
        "source_switch_authorized",
        "staged_trade_kline_w1_materialization_authorized",
        "live_trading_authorized",
    ):
        if boundary.get(key) is not False:
            raise RuntimeError(f"blocked authorization boundary changed: {key}")

    probe_boundary = protocol.get("authorization_boundary") or {}
    if probe_boundary.get("transport_probe_execution_authorized") is not True:
        raise RuntimeError("local transport probe execution is not authorized")
    for key in (
        "metadata_capture_execution_authorized",
        "metadata_only_r2_writes_authorized",
        "holdout_candle_access_authorized",
        "holdout_evaluation_authorized",
        "replacement_holdout_freeze_authorized",
        "source_switch_authorized",
        "staged_trade_kline_w1_materialization_authorized",
        "live_trading_authorized",
    ):
        if probe_boundary.get(key) is not False:
            raise RuntimeError(f"probe authorization boundary changed: {key}")

    selected = m1a.get("selected_universe") or []
    if not isinstance(selected, list) or len(selected) != 15:
        raise RuntimeError("frozen M1A 15-symbol universe changed")
    pionex_symbols = tuple(str(row["symbol"]) for row in selected)
    if len(set(pionex_symbols)) != 15:
        raise RuntimeError("duplicate symbol in frozen Pionex universe")
    binance_symbols = tuple(pionex_perp_to_binance_usdm(symbol) for symbol in pionex_symbols)
    if len(set(binance_symbols)) != 15:
        raise RuntimeError("duplicate Binance mapping in frozen universe")
    return protocol, pionex_symbols, binance_symbols


def _fetch_json_bytes(
    *,
    provider: str,
    url: str,
    max_bytes: int,
    timeout_seconds: float = 20.0,
) -> tuple[bytes, str]:
    request = Request(url, headers={"User-Agent": "qookey-v0.2-local-transport-probe/0.1"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            status = int(getattr(response, "status", 200))
            if status != 200:
                raise ProbeError("TRANSPORT_BLOCKED", provider, f"HTTP {status}", status)
            raw = response.read(max_bytes + 1)
            if len(raw) > max_bytes:
                raise ProbeError(
                    "CONTRACT_FAIL",
                    provider,
                    f"response exceeds frozen max bytes ({max_bytes})",
                    status,
                )
            content_type = str(response.headers.get("Content-Type", ""))
    except HTTPError as exc:
        raise ProbeError("TRANSPORT_BLOCKED", provider, f"HTTP {exc.code}", exc.code) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise ProbeError("TRANSPORT_BLOCKED", provider, str(exc)) from exc

    try:
        json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProbeError("CONTRACT_FAIL", provider, "response is not UTF-8 JSON", status) from exc
    return raw, content_type


def validate_pionex_transport(raw: bytes, expected_symbols: tuple[str, ...]) -> int:
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ProbeError("CONTRACT_FAIL", "pionex", "payload is not object")
    data = payload.get("data")
    rows = data.get("symbols") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise ProbeError("CONTRACT_FAIL", "pionex", "data.symbols is not list")

    expected = set(expected_symbols)
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol", ""))
        if symbol not in expected:
            continue
        if symbol in seen:
            raise ProbeError("CONTRACT_FAIL", "pionex", f"duplicate selected symbol: {symbol}")
        if "quoteStep" not in row:
            raise ProbeError("CONTRACT_FAIL", "pionex", f"quoteStep missing: {symbol}")
        seen.add(symbol)

    missing = expected - seen
    if missing:
        raise ProbeError(
            "CONTRACT_FAIL",
            "pionex",
            f"missing frozen symbols: {sorted(missing)}",
        )
    return len(seen)


def validate_binance_transport(raw: bytes, expected_symbols: tuple[str, ...]) -> int:
    payload = json.loads(raw.decode("utf-8"))
    rows = payload.get("symbols") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise ProbeError("CONTRACT_FAIL", "binance_usdm", "symbols is not list")

    expected = set(expected_symbols)
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol", ""))
        if symbol not in expected:
            continue
        if symbol in seen:
            raise ProbeError(
                "CONTRACT_FAIL",
                "binance_usdm",
                f"duplicate selected symbol: {symbol}",
            )
        filters = row.get("filters")
        if not isinstance(filters, list):
            raise ProbeError("CONTRACT_FAIL", "binance_usdm", f"filters missing: {symbol}")
        price_filters = [
            item
            for item in filters
            if isinstance(item, dict) and item.get("filterType") == "PRICE_FILTER"
        ]
        if len(price_filters) != 1 or "tickSize" not in price_filters[0]:
            raise ProbeError(
                "CONTRACT_FAIL",
                "binance_usdm",
                f"PRICE_FILTER.tickSize contract missing: {symbol}",
            )
        seen.add(symbol)

    missing = expected - seen
    if missing:
        raise ProbeError(
            "CONTRACT_FAIL",
            "binance_usdm",
            f"missing frozen symbols: {sorted(missing)}",
        )
    return len(seen)


def _safe_boundary() -> dict[str, bool]:
    return {
        "increment_values_emitted": False,
        "r2_client_constructed": False,
        "r2_writes_performed": False,
        "r2_deletes_performed": False,
        "holdout_candles_accessed": False,
        "holdout_evaluated": False,
        "replacement_holdout_frozen": False,
        "source_switch_authorized": False,
        "provider_splicing_authorized": False,
        "w1_materialization_authorized": False,
        "backtest_admission_authorized": False,
        "automatic_trade_plan_authorized": False,
        "live_trading_authorized": False,
    }


def run_local_transport_probe() -> dict[str, Any]:
    protocol, pionex_symbols, binance_symbols = load_probe_authority()
    providers = protocol["providers"]
    result: dict[str, Any] = {
        "schema": "provider-equivalence-v0-2-local-transport-probe-result-v0.1",
        "status": "IN_PROGRESS",
        "stage": "PROVIDER_EQUIVALENCE_V0_2_LOCAL_TRANSPORT_CONNECTIVITY_PROBE",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "executor": {
            "class": "operator_controlled_local_host",
            "platform_system": platform.system(),
            "platform_machine": platform.machine(),
            "python_version": platform.python_version(),
            "hostname_recorded": False,
            "ip_address_recorded": False,
        },
        "providers": {},
        **_safe_boundary(),
    }

    for provider, expected, validator in (
        ("pionex", pionex_symbols, validate_pionex_transport),
        ("binance_usdm", binance_symbols, validate_binance_transport),
    ):
        cfg = providers[provider]
        try:
            raw, content_type = _fetch_json_bytes(
                provider=provider,
                url=str(cfg["public_endpoint"]),
                max_bytes=int(cfg["max_response_bytes"]),
            )
            selected_count = validator(raw, expected)
            result["providers"][provider] = {
                "status": "PASS",
                "http_status": 200,
                "json_parse": True,
                "selected_symbol_count": selected_count,
                "required_metadata_field_present": True,
                "raw_bytes": len(raw),
                "raw_sha256": hashlib.sha256(raw).hexdigest(),
                "content_type": content_type,
                "increment_values_emitted": False,
            }
        except ProbeError as exc:
            result["providers"][provider] = {
                "status": exc.kind,
                "http_status": exc.http_status,
                "detail": exc.detail,
                "increment_values_emitted": False,
            }
            result["status"] = "BLOCKED" if exc.kind == "TRANSPORT_BLOCKED" else "FAIL"
            result["stage"] = (
                "PROVIDER_EQUIVALENCE_V0_2_LOCAL_TRANSPORT_CONNECTIVITY_BLOCKED"
                if exc.kind == "TRANSPORT_BLOCKED"
                else "PROVIDER_EQUIVALENCE_V0_2_LOCAL_TRANSPORT_CONNECTIVITY_FAIL"
            )
            return result

    result["status"] = "PASS"
    result["stage"] = "PROVIDER_EQUIVALENCE_V0_2_LOCAL_TRANSPORT_CONNECTIVITY_PASS"
    return result


def result_exit_code(result: dict[str, Any]) -> int:
    return 0 if result.get("status") == "PASS" else 2
