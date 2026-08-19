from __future__ import annotations

import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

UPSTREAM_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"
USER_AGENT = "qookey-provider-equivalence-koyeb-free-preflight/0.1"
MAX_BODY_BYTES = 8_000_000


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
        "transport": "koyeb_free_web_service",
        "runtime_platform": "koyeb",
        "runtime_region": os.environ.get("KOYEB_REGION", "fra"),
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


class Handler(BaseHTTPRequestHandler):
    server_version = "QookeyKoyebFreeTransport/0.1"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            body = b'{"status":"ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
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
        body = json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: object) -> None:
        return


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
