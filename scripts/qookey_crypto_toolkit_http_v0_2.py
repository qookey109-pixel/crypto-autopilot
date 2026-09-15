#!/usr/bin/env python3
from __future__ import annotations

import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from crypto_autopilot.toolkit.http_api import MAX_REQUEST_BYTES, dispatch_request

PUBLIC_PATHS = {"/healthz", "/openapi.json", "/v0/capabilities"}


def _is_loopback(host: str) -> bool:
    return host in {"127.0.0.1", "::1", "localhost"}


def _authorized(handler: BaseHTTPRequestHandler, token: str | None) -> bool:
    if not token:
        return True
    supplied = handler.headers.get("Authorization", "")
    prefix = "Bearer "
    if not supplied.startswith(prefix):
        return False
    return hmac.compare_digest(supplied[len(prefix) :], token)


class ToolkitHandler(BaseHTTPRequestHandler):
    server_version = "QookeyCryptoToolkitHTTP/0.2"

    def _request_path(self) -> str:
        return self.path.split("?", 1)[0].rstrip("/") or "/"

    def _allowed_cors_origin(self) -> str:
        configured = os.getenv("QOOKEY_TOOLKIT_CORS_ORIGIN", "").strip()
        requested = self.headers.get("Origin", "")
        return configured if configured and requested == configured else ""

    def _write_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        cors_origin = self._allowed_cors_origin()
        if cors_origin:
            self.send_header("Access-Control-Allow-Origin", cors_origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(body)

    def _auth_required(self) -> bool:
        return self._request_path() not in PUBLIC_PATHS

    def _check_auth(self) -> bool:
        token = os.getenv("QOOKEY_TOOLKIT_API_TOKEN", "").strip() or None
        if not self._auth_required() or _authorized(self, token):
            return True
        self._write_json(
            401,
            {
                "schema": "qookey-crypto-toolkit-api-error-v0.2",
                "status": "ERROR",
                "error": {"code": "UNAUTHORIZED", "message": "valid bearer token required"},
            },
        )
        return False

    def _read_payload(self) -> dict[str, Any] | None:
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            return None
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
        if length < 0 or length > MAX_REQUEST_BYTES:
            raise ValueError(f"request body exceeds {MAX_REQUEST_BYTES} bytes")
        raw = self.rfile.read(length)
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("request body must contain valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def do_OPTIONS(self) -> None:  # noqa: N802
        configured = os.getenv("QOOKEY_TOOLKIT_CORS_ORIGIN", "").strip()
        requested = self.headers.get("Origin", "")
        if not configured or requested != configured:
            self.send_response(403)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", configured)
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization,Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Vary", "Origin")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if not self._check_auth():
            return
        status, response = dispatch_request("GET", self.path)
        self._write_json(status, response)

    def do_POST(self) -> None:  # noqa: N802
        if not self._check_auth():
            return
        try:
            payload = self._read_payload()
        except ValueError as exc:
            self._write_json(
                400,
                {
                    "schema": "qookey-crypto-toolkit-api-error-v0.2",
                    "status": "ERROR",
                    "error": {"code": "INVALID_REQUEST_BODY", "message": str(exc)},
                },
            )
            return
        status, response = dispatch_request("POST", self.path, payload)
        self._write_json(status, response)

    def log_message(self, fmt: str, *args: object) -> None:
        # Never log request bodies or Authorization headers.
        client_ip = self.client_address[0] if self.client_address else "unknown"
        print(f"toolkit-http {client_ip} {fmt % args}")


def main() -> int:
    host = os.getenv("QOOKEY_TOOLKIT_HOST", "127.0.0.1").strip()
    port = int(os.getenv("PORT", os.getenv("QOOKEY_TOOLKIT_PORT", "8788")))
    token = os.getenv("QOOKEY_TOOLKIT_API_TOKEN", "").strip()
    if not _is_loopback(host) and not token:
        raise SystemExit(
            "refusing non-loopback bind without QOOKEY_TOOLKIT_API_TOKEN; "
            "configure a bearer token before cloud exposure"
        )
    server = ThreadingHTTPServer((host, port), ToolkitHandler)
    print(f"Qookey Crypto Toolkit API V0.2 listening on http://{host}:{port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
