from __future__ import annotations

import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

UPSTREAM_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"
USER_AGENT = "qookey-provider-equivalence-render-free-preflight/0.1"
METADATA_RELAY_USER_AGENT = "qookey-provider-equivalence-render-metadata-relay/0.1"
METADATA_RELAY_PATH = "/metadata/binance-exchange-info"
MAX_BODY_BYTES = 8_000_000

# V0.7 deliberately ships the relay implementation disabled in code. A later,
# separately versioned execution/cutover authority must change this constant.
METADATA_RELAY_EXECUTION_AUTHORIZED = False


def summarize_exchange_info(upstream_status: int, payload: Any) -> dict[str, Any]:
    json_ok = isinstance(payload, dict)
    symbols = payload.get("symbols") if json_ok else None
    symbols_array = isinstance(symbols, list)
    symbol_count = len(symbols) if symbols_array else None
    passed = (
        upstream_status == 200
        and json_ok
        and symbols_array
        and isinstance(symbol_count, int)
        and symbol_count > 0
    )
    return {
        "status": "PASS" if passed else "BLOCKED",
        "transport": "render_free_web_service",
        "runtime_platform": "render",
        "runtime_region": os.environ.get("RENDER_REGION", "frankfurt"),
        "upstream_url": UPSTREAM_URL,
        "upstream_status": upstream_status,
        "json_ok": json_ok,
        "symbols_array": symbols_array,
        "symbol_count": symbol_count,
        "api_key_used": False,
        "increment_values_emitted": False,
        "raw_exchange_info_persisted": False,
        "r2_client_constructed": False,
        "r2_writes_performed": False,
        "holdout_candles_accessed": False,
        "holdout_evaluated": False,
        "source_switch_performed": False,
        "live_trading_performed": False,
    }


def run_probe() -> dict[str, Any]:
    request = Request(UPSTREAM_URL, headers={"User-Agent": USER_AGENT})
    upstream_status = 0
    payload: Any = None
    try:
        with urlopen(request, timeout=15) as response:
            upstream_status = int(response.status)
            body = response.read(MAX_BODY_BYTES + 1)
            if len(body) > MAX_BODY_BYTES:
                return summarize_exchange_info(upstream_status, None)
            payload = json.loads(body.decode("utf-8"))
    except HTTPError as exc:
        upstream_status = int(exc.code)
    except (URLError, TimeoutError, ValueError, json.JSONDecodeError):
        upstream_status = 0
    return summarize_exchange_info(upstream_status, payload)


def is_authorized(header_value: str | None, expected_token: str | None) -> bool:
    if not expected_token or not header_value:
        return False
    prefix = "Bearer "
    if not header_value.startswith(prefix):
        return False
    supplied = header_value[len(prefix) :]
    return hmac.compare_digest(supplied, expected_token)


def metadata_relay_enabled() -> bool:
    if not METADATA_RELAY_EXECUTION_AUTHORIZED:
        return False
    return os.environ.get("METADATA_RELAY_ENABLED", "").strip().lower() == "true"


def fetch_exchange_info_raw() -> tuple[int, bytes | None, str, int | None]:
    """Fetch exact Binance exchangeInfo bytes for the future authorized relay.

    The body is parsed only to validate the frozen transport contract. On PASS,
    the exact upstream bytes are returned without reserialization. Nothing is
    persisted and no R2 client is constructed here.
    """

    request = Request(UPSTREAM_URL, headers={"User-Agent": METADATA_RELAY_USER_AGENT})
    upstream_status = 0
    try:
        with urlopen(request, timeout=15) as response:
            upstream_status = int(response.status)
            body = response.read(MAX_BODY_BYTES + 1)
            content_type = str(response.headers.get("Content-Type", "application/json"))
    except HTTPError as exc:
        return int(exc.code), None, "application/json", None
    except (URLError, TimeoutError, ValueError):
        return 0, None, "application/json", None

    if upstream_status != 200 or len(body) > MAX_BODY_BYTES:
        return upstream_status, None, content_type, None

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return upstream_status, None, content_type, None

    if not isinstance(payload, dict):
        return upstream_status, None, content_type, None
    symbols = payload.get("symbols")
    if not isinstance(symbols, list) or len(symbols) == 0:
        return upstream_status, None, content_type, None
    return upstream_status, body, content_type, len(symbols)


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "QookeyRenderFreeTransport/0.2"

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json(200, {"status": "ok"})
            return

        if self.path == METADATA_RELAY_PATH:
            # V0.7 must not perform a provider request. This hard code gate stays
            # false until a separate versioned execution/cutover authority.
            if not metadata_relay_enabled():
                self._send_json(
                    503,
                    {
                        "status": "DISABLED",
                        "stage": "V0_7_METADATA_RELAY_EXECUTION_NOT_AUTHORIZED",
                        "provider_requests_performed": 0,
                        "raw_exchange_info_persisted": False,
                        "r2_client_constructed": False,
                        "r2_writes_performed": False,
                        "holdout_candles_accessed": False,
                        "source_switch_performed": False,
                        "live_trading_performed": False,
                    },
                )
                return

            expected = os.environ.get("METADATA_RELAY_TOKEN")
            if not is_authorized(self.headers.get("Authorization"), expected):
                self._send_json(401, {"status": "UNAUTHORIZED"})
                return

            upstream_status, raw, content_type, symbol_count = fetch_exchange_info_raw()
            if raw is None or upstream_status != 200 or not symbol_count:
                self._send_json(
                    502,
                    {
                        "status": "BLOCKED",
                        "upstream_status": upstream_status,
                        "raw_exchange_info_persisted": False,
                        "r2_client_constructed": False,
                        "r2_writes_performed": False,
                        "holdout_candles_accessed": False,
                        "source_switch_performed": False,
                        "live_trading_performed": False,
                    },
                )
                return

            self.send_response(200)
            self.send_header("Content-Type", content_type or "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Qookey-Upstream-Status", str(upstream_status))
            self.send_header("X-Qookey-Symbol-Count", str(symbol_count))
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return

        if self.path != "/check":
            self.send_response(404)
            self.end_headers()
            return

        expected = os.environ.get("DIAGNOSTIC_TOKEN")
        if not is_authorized(self.headers.get("Authorization"), expected):
            self.send_response(401)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return

        result = run_probe()
        body = _json_bytes(result)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        return


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
