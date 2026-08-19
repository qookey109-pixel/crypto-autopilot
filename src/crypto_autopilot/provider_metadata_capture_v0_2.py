from __future__ import annotations

import gzip
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .binance_historical import pionex_perp_to_binance_usdm
from .storage.r2 import R2Store


PROTOCOL = Path("config/provider_equivalence_v0_2_metadata_capture_v0_2.json")
AUTHORITY = Path(
    "research/receipts/2026-08-19-provider-equivalence-v0-2-forward-metadata-capture-authority-v0-2.json"
)
M1A = Path("research/receipts/2026-08-17-m1a-pionex.json")

EXPECTED_AUTHORITY_STAGE = (
    "PROVIDER_EQUIVALENCE_V0_2_FORWARD_METADATA_CAPTURE_AUTHORIZED_HOLDOUT_CANDLES_FORBIDDEN"
)


@dataclass(frozen=True)
class ProviderPayload:
    provider: str
    raw: bytes
    content_type: str
    vector: tuple[dict[str, str], ...]

    @property
    def raw_sha256(self) -> str:
        return hashlib.sha256(self.raw).hexdigest()

    @property
    def vector_sha256(self) -> str:
        payload = json.dumps(self.vector, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected object: {path}")
    return payload


def load_and_validate_authority() -> tuple[dict[str, Any], tuple[str, ...], tuple[str, ...]]:
    protocol = _load_json(PROTOCOL)
    authority = _load_json(AUTHORITY)
    m1a = _load_json(M1A)

    if protocol.get("status") != "PROTOCOL_FROZEN_BEFORE_METADATA_EVIDENCE":
        raise RuntimeError("metadata capture protocol is not frozen")
    if authority.get("status") != "PASS" or authority.get("stage") != EXPECTED_AUTHORITY_STAGE:
        raise RuntimeError("metadata capture authority is not PASS")
    blocked = authority.get("explicitly_not_authorized") or {}
    if not isinstance(blocked, dict):
        raise RuntimeError("authority boundary shape changed")
    for key in (
        "holdout_candle_access_authorized",
        "holdout_evaluation_authorized",
        "source_switch_authorized",
        "provider_splicing_authorized",
        "staged_trade_kline_w1_materialization_authorized",
        "live_trading_authorized",
    ):
        if blocked.get(key) is not False:
            raise RuntimeError(f"forbidden authority changed: {key}")

    selected = m1a.get("selected_universe") or []
    if not isinstance(selected, list) or len(selected) != 15:
        raise RuntimeError("frozen M1A 15-symbol universe changed")
    pionex_symbols = tuple(str(row["symbol"]) for row in selected)
    if len(set(pionex_symbols)) != 15:
        raise RuntimeError("duplicate Pionex symbol in frozen universe")
    binance_symbols = tuple(pionex_perp_to_binance_usdm(symbol) for symbol in pionex_symbols)
    if len(set(binance_symbols)) != 15:
        raise RuntimeError("duplicate Binance mapping in frozen universe")
    return protocol, pionex_symbols, binance_symbols


def _positive_decimal_source_string(value: object, *, field: str) -> str:
    if not isinstance(value, (str, int, float)):
        raise RuntimeError(f"{field} is not scalar")
    text = str(value)
    try:
        parsed = Decimal(text)
    except InvalidOperation as exc:
        raise RuntimeError(f"{field} is not decimal: {text}") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise RuntimeError(f"{field} must be finite and positive: {text}")
    return text


def parse_pionex_symbols(raw: bytes, expected_symbols: tuple[str, ...]) -> tuple[dict[str, str], ...]:
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Pionex payload is not object")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("Pionex payload missing data object")
    rows = data.get("symbols")
    if not isinstance(rows, list):
        raise RuntimeError("Pionex payload missing data.symbols list")

    expected = set(expected_symbols)
    found: dict[str, dict[str, str]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError("Pionex symbol row is not object")
        symbol = str(row.get("symbol", ""))
        if symbol not in expected:
            continue
        if symbol in found:
            raise RuntimeError(f"duplicate Pionex symbol: {symbol}")
        quote_step = _positive_decimal_source_string(row.get("quoteStep"), field=f"{symbol}.quoteStep")
        status = str(row.get("status", ""))
        contract_type = str(row.get("contractType", ""))
        if not status or not contract_type:
            raise RuntimeError(f"Pionex status/contractType missing: {symbol}")
        found[symbol] = {
            "symbol": symbol,
            "price_increment": quote_step,
            "status": status,
            "contract_type": contract_type,
            "source_field": "data.symbols[].quoteStep",
        }

    missing = expected - set(found)
    if missing:
        raise RuntimeError(f"Pionex metadata missing frozen symbols: {sorted(missing)}")
    return tuple(found[symbol] for symbol in sorted(found))


def parse_binance_exchange_info(
    raw: bytes, expected_symbols: tuple[str, ...]
) -> tuple[dict[str, str], ...]:
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Binance payload is not object")
    rows = payload.get("symbols")
    if not isinstance(rows, list):
        raise RuntimeError("Binance payload missing symbols list")

    expected = set(expected_symbols)
    found: dict[str, dict[str, str]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError("Binance symbol row is not object")
        symbol = str(row.get("symbol", ""))
        if symbol not in expected:
            continue
        if symbol in found:
            raise RuntimeError(f"duplicate Binance symbol: {symbol}")
        filters = row.get("filters")
        if not isinstance(filters, list):
            raise RuntimeError(f"Binance filters missing: {symbol}")
        price_filters = [
            item for item in filters if isinstance(item, dict) and item.get("filterType") == "PRICE_FILTER"
        ]
        if len(price_filters) != 1:
            raise RuntimeError(f"expected exactly one PRICE_FILTER: {symbol}")
        tick_size = _positive_decimal_source_string(
            price_filters[0].get("tickSize"), field=f"{symbol}.PRICE_FILTER.tickSize"
        )
        status = str(row.get("status", ""))
        contract_type = str(row.get("contractType", ""))
        if not status or not contract_type:
            raise RuntimeError(f"Binance status/contractType missing: {symbol}")
        found[symbol] = {
            "symbol": symbol,
            "price_increment": tick_size,
            "status": status,
            "contract_type": contract_type,
            "source_field": "symbols[].filters[filterType=PRICE_FILTER].tickSize",
        }

    missing = expected - set(found)
    if missing:
        raise RuntimeError(f"Binance metadata missing frozen symbols: {sorted(missing)}")
    return tuple(found[symbol] for symbol in sorted(found))


def _fetch_json_bytes(url: str, *, max_bytes: int, timeout_seconds: float = 30.0) -> tuple[bytes, str]:
    request = Request(url, headers={"User-Agent": "qookey-provider-equivalence-metadata/0.2"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            status = int(getattr(response, "status", 200))
            if status != 200:
                raise RuntimeError(f"HTTP {status}: {url}")
            raw = response.read(max_bytes + 1)
            if len(raw) > max_bytes:
                raise RuntimeError(f"provider payload exceeds frozen max bytes: {url}")
            content_type = str(response.headers.get("Content-Type", ""))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"provider metadata request failed: {url}: {exc}") from exc
    json.loads(raw.decode("utf-8"))
    return raw, content_type


def fetch_provider_payloads() -> tuple[ProviderPayload, ProviderPayload, dict[str, Any]]:
    protocol, pionex_symbols, binance_symbols = load_and_validate_authority()
    providers = protocol["providers"]
    pionex_cfg = providers["pionex"]
    binance_cfg = providers["binance_usdm"]

    pionex_raw, pionex_content_type = _fetch_json_bytes(
        str(pionex_cfg["public_endpoint"]),
        max_bytes=int(pionex_cfg["raw_uncompressed_response_max_bytes"]),
    )
    binance_raw, binance_content_type = _fetch_json_bytes(
        str(binance_cfg["public_endpoint"]),
        max_bytes=int(binance_cfg["raw_uncompressed_response_max_bytes"]),
    )

    pionex = ProviderPayload(
        provider="pionex",
        raw=pionex_raw,
        content_type=pionex_content_type,
        vector=parse_pionex_symbols(pionex_raw, pionex_symbols),
    )
    binance = ProviderPayload(
        provider="binance_usdm",
        raw=binance_raw,
        content_type=binance_content_type,
        vector=parse_binance_exchange_info(binance_raw, binance_symbols),
    )
    return pionex, binance, protocol


def connectivity_preflight() -> dict[str, Any]:
    pionex, binance, _ = fetch_provider_payloads()
    return {
        "status": "PASS",
        "stage": "PROVIDER_EQUIVALENCE_V0_2_METADATA_CONNECTIVITY_PREFLIGHT_PASS",
        "pionex_http_json_parse": True,
        "pionex_selected_symbol_count": len(pionex.vector),
        "pionex_raw_bytes": len(pionex.raw),
        "pionex_raw_sha256": pionex.raw_sha256,
        "binance_http_json_parse": True,
        "binance_selected_symbol_count": len(binance.vector),
        "binance_raw_bytes": len(binance.raw),
        "binance_raw_sha256": binance.raw_sha256,
        "increment_values_emitted": False,
        "r2_client_constructed": False,
        "r2_writes_performed": False,
        "holdout_candles_accessed": False,
        "source_switch_authorized": False,
        "live_trading_authorized": False,
    }


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def capture_slot(now: datetime, protocol: dict[str, Any]) -> datetime | None:
    if now.tzinfo is None:
        raise ValueError("capture time must be timezone-aware")
    now = now.astimezone(timezone.utc)
    window = protocol["metadata_capture_window"]
    start = _parse_utc(str(window["start_utc"]))
    end = _parse_utc(str(window["end_utc"]))
    if now < start or now > end:
        return None
    return now.replace(minute=0, second=0, microsecond=0)


def _gzip(raw: bytes) -> bytes:
    return gzip.compress(raw, compresslevel=9, mtime=0)


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def capture_to_r2(*, now: datetime | None = None) -> dict[str, Any]:
    protocol, _, _ = load_and_validate_authority()
    observed = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    slot = capture_slot(observed, protocol)
    if slot is None:
        return {
            "status": "SKIP",
            "stage": "OUTSIDE_FROZEN_METADATA_CAPTURE_WINDOW",
            "observed_at_utc": observed.isoformat(),
            "provider_requests_performed": 0,
            "r2_client_constructed": False,
            "r2_writes_performed": False,
            "holdout_candles_accessed": False,
        }

    pionex, binance, protocol = fetch_provider_payloads()
    run_id = os.environ.get("GITHUB_RUN_ID")
    if not run_id or not run_id.isdigit():
        raise RuntimeError("GITHUB_RUN_ID is required for immutable run-scoped R2 keys")

    slot_id = slot.strftime("%Y%m%dT%H0000Z")
    root = str(protocol["storage"]["namespace"]).rstrip("/")
    prefix = f"{root}/capture/slot={slot_id}/run={run_id}"
    pionex_key = f"{prefix}/pionex-symbols.json.gz"
    binance_key = f"{prefix}/binance-usdm-exchange-info.json.gz"
    receipt_key = f"{prefix}/receipt.json"

    pionex_gz = _gzip(pionex.raw)
    binance_gz = _gzip(binance.raw)
    receipt = {
        "schema": "provider-equivalence-v0-2-metadata-capture-receipt-v0.1",
        "status": "PASS",
        "slot_utc": slot.isoformat().replace("+00:00", "Z"),
        "observed_at_utc": observed.isoformat(),
        "github_run_id": int(run_id),
        "github_sha": os.environ.get("GITHUB_SHA"),
        "holdout_candles_accessed": False,
        "provider_splicing_used": False,
        "providers": {
            "pionex": {
                "raw_key": pionex_key,
                "raw_uncompressed_bytes": len(pionex.raw),
                "raw_sha256": pionex.raw_sha256,
                "gzip_bytes": len(pionex_gz),
                "gzip_sha256": hashlib.sha256(pionex_gz).hexdigest(),
                "content_type": pionex.content_type,
                "normalized_vector_sha256": pionex.vector_sha256,
                "normalized_vector": list(pionex.vector),
            },
            "binance_usdm": {
                "raw_key": binance_key,
                "raw_uncompressed_bytes": len(binance.raw),
                "raw_sha256": binance.raw_sha256,
                "gzip_bytes": len(binance_gz),
                "gzip_sha256": hashlib.sha256(binance_gz).hexdigest(),
                "content_type": binance.content_type,
                "normalized_vector_sha256": binance.vector_sha256,
                "normalized_vector": list(binance.vector),
            },
        },
        "authorization_boundary": {
            "metadata_only": True,
            "holdout_candle_access_authorized": False,
            "holdout_evaluation_authorized": False,
            "source_switch_authorized": False,
            "w1_materialization_authorized": False,
            "live_trading_authorized": False,
        },
    }
    receipt_bytes = _json_bytes(receipt)

    store = R2Store(
        account_id=os.environ["CLOUDFLARE_ACCOUNT_ID"],
        bucket=os.environ["R2_BUCKET_NAME"],
        access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    )
    for key in (pionex_key, binance_key, receipt_key):
        if store.exists(key):
            raise RuntimeError(f"immutable capture key already exists; overwrite forbidden: {key}")

    p_receipt = store.put_bytes(
        pionex_key,
        pionex_gz,
        content_type="application/gzip",
        metadata={"provider": "pionex", "slot": slot_id, "run": run_id},
    )
    b_receipt = store.put_bytes(
        binance_key,
        binance_gz,
        content_type="application/gzip",
        metadata={"provider": "binance_usdm", "slot": slot_id, "run": run_id},
    )
    r_receipt = store.put_bytes(
        receipt_key,
        receipt_bytes,
        content_type="application/json",
        metadata={"dataset": "provider_equivalence_v0_2_metadata", "slot": slot_id, "run": run_id},
    )

    store.get_bytes_verified(pionex_key, expected_sha256=p_receipt.sha256)
    store.get_bytes_verified(binance_key, expected_sha256=b_receipt.sha256)
    store.get_bytes_verified(receipt_key, expected_sha256=r_receipt.sha256)

    return {
        "status": "PASS",
        "stage": "PROVIDER_EQUIVALENCE_V0_2_METADATA_CAPTURE_PASS",
        "slot_utc": receipt["slot_utc"],
        "observed_at_utc": receipt["observed_at_utc"],
        "github_run_id": int(run_id),
        "object_count": 3,
        "receipt_key": receipt_key,
        "pionex_vector_sha256": pionex.vector_sha256,
        "binance_vector_sha256": binance.vector_sha256,
        "postwrite_sha256_verification": True,
        "r2_writes_performed": True,
        "r2_deletes_performed": False,
        "holdout_candles_accessed": False,
        "source_switch_authorized": False,
        "live_trading_authorized": False,
    }
