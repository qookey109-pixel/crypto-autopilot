"""Bounded Pionex public transport for the Cloud Paper composition.

Reuse the existing parsers while making one reserved request mean one HTTP
attempt. This module performs no I/O on import or construction.
"""
from __future__ import annotations

import json
import math
from collections.abc import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from crypto_autopilot.exchanges.pionex_public import (
    PionexAPIError,
    PionexPublicClient,
)

PUBLIC_BASE_URL = "https://api.pionex.com"
MAX_RESPONSE_BYTES = 1_048_576
CLOUD_PAPER_PATHS = frozenset({
    "/api/v1/common/symbols",
    "/api/v1/market/tickers",
    "/api/v1/market/bookTickers",
    "/api/v1/market/klines",
    "/api/v1/market/depth",
    "/api/v1/market/trades",
})


class CloudPaperTransportBlocked(PionexAPIError):
    """Fixed reason code; never include a URL, response body or credentials."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        fp.close()
        raise CloudPaperTransportBlocked("PIONEX_REDIRECT_REJECTED")


def _reject_nonfinite(value: str) -> None:
    raise ValueError("nonfinite JSON")


class CloudPaperPionexPublicClient(PionexPublicClient):
    """One bounded GET with a freshness recheck after rate-limit waiting.

    The composition reserves the request before invoking an inherited method.
    before_send rechecks evidence at the actual send boundary without making
    another reservation. Transport errors never retry or switch sources.
    """

    def __init__(
        self, *, before_send: Callable[[], None],
        timeout_seconds: float = 10.0, requests_per_second: float = 3.0,
    ) -> None:
        if not callable(before_send):
            raise ValueError("a pre-send evidence check is required")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or not 0 < timeout_seconds <= 10
        ):
            raise ValueError("timeout_seconds must be within (0, 10]")
        if (
            isinstance(requests_per_second, bool)
            or not isinstance(requests_per_second, (int, float))
            or not math.isfinite(requests_per_second)
            or not 0 < requests_per_second <= 3
        ):
            raise ValueError("requests_per_second must be within (0, 3]")
        super().__init__(
            timeout_seconds=timeout_seconds,
            requests_per_second=requests_per_second,
        )
        self._before_send = before_send

    def _get_json(self, path: str, params: dict[str, object]) -> dict:
        if path not in CLOUD_PAPER_PATHS:
            raise CloudPaperTransportBlocked("PIONEX_ENDPOINT_NOT_ALLOWED")
        query = urlencode({key: value for key, value in params.items() if value is not None})
        # Use the fixed module authority, not a mutable inherited BASE_URL.
        url = f"{PUBLIC_BASE_URL}{path}?{query}" if query else f"{PUBLIC_BASE_URL}{path}"
        request = Request(
            url, method="GET",
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "identity",
                "User-Agent": "crypto-autopilot-cloud-paper-v0.1",
            },
        )
        self._pace()
        self._before_send()
        try:
            with build_opener(_NoRedirect).open(
                request, timeout=self.timeout_seconds,
            ) as response:
                if response.getcode() != 200:
                    raise CloudPaperTransportBlocked("PIONEX_HTTP_STATUS_REJECTED")
                encoding = response.headers.get("Content-Encoding", "identity").strip().lower()
                if encoding not in {"", "identity"}:
                    raise CloudPaperTransportBlocked("PIONEX_CONTENT_ENCODING_REJECTED")
                body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise CloudPaperTransportBlocked("PIONEX_RESPONSE_TOO_LARGE")
            payload = json.loads(body, parse_constant=_reject_nonfinite)
        except CloudPaperTransportBlocked:
            raise
        except (HTTPError, URLError, TimeoutError, OSError, ValueError):
            raise CloudPaperTransportBlocked("PIONEX_REQUEST_FAILED") from None
        if (
            not isinstance(payload, dict)
            or payload.get("result") is not True
            or not isinstance(payload.get("data"), dict)
        ):
            raise CloudPaperTransportBlocked("PIONEX_RESPONSE_INVALID")
        return payload
