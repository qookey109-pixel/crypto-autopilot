"""Secret-free Pionex provider-error diagnostics for validation materialization V0.1.

The adapter preserves fail-closed materialization behavior. It records only a
bounded provider error code/message derived from the existing public-client
exception text. Raw provider payloads, request URLs, headers and credentials
are never persisted.
"""
from __future__ import annotations

import re
from typing import Any

from ..exchanges.pionex_public import PionexAPIError
from . import pionex_validation_materialization_v0_1 as materialization

_PROVIDER_PREFIX = "Pionex request failed:"
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_SECRET_ASSIGNMENT_RE = re.compile(
    r"\b(api[-_]?key|secret|token|signature)\s*=\s*[^\s,;]+",
    re.IGNORECASE,
)
_MAX_CODE_CHARS = 64
_MAX_MESSAGE_CHARS = 256


def _bounded_public_text(value: object, *, limit: int) -> str | None:
    text = " ".join(str(value).split())
    if not text:
        return None
    text = _URL_RE.sub("[redacted-url]", text)
    text = _SECRET_ASSIGNMENT_RE.sub(
        lambda match: f"{match.group(1)}=[redacted]",
        text,
    )
    return text[:limit]


def pionex_api_error_diagnostics(exc: PionexAPIError) -> dict[str, object]:
    """Return bounded structured fields without retaining the raw response."""
    rendered = str(exc)
    if rendered.startswith(_PROVIDER_PREFIX):
        detail = rendered[len(_PROVIDER_PREFIX) :].strip()
    else:
        detail = rendered.strip()

    code_text, separator, message_text = detail.partition(" ")
    code = _bounded_public_text(code_text, limit=_MAX_CODE_CHARS)
    message = _bounded_public_text(
        message_text if separator else "",
        limit=_MAX_MESSAGE_CHARS,
    )
    diagnostics: dict[str, object] = {}
    if code:
        diagnostics["provider_error_code"] = code
    if message:
        diagnostics["provider_error_message"] = message
    return diagnostics


class ProviderErrorDiagnosticKlineClient:
    """Transparent kline adapter that remembers only safe provider diagnostics."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self._last_provider_error_diagnostics: dict[str, object] = {}

    @property
    def provider_error_diagnostics(self) -> dict[str, object]:
        return dict(self._last_provider_error_diagnostics)

    def get_klines(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
        end_time_ms: int | None = None,
    ):
        self._last_provider_error_diagnostics = {}
        try:
            return self._inner.get_klines(
                symbol,
                interval,
                limit=limit,
                end_time_ms=end_time_ms,
            )
        except PionexAPIError as exc:
            self._last_provider_error_diagnostics = pionex_api_error_diagnostics(exc)
            raise


def install_provider_error_diagnostics() -> None:
    """Add safe provider fields to fatal materialization diagnostics only."""
    original = materialization.collect_partition
    if getattr(original, "_pionex_provider_error_diagnostics_v0_1", False):
        return

    def wrapped(config, client, **kwargs):
        try:
            return original(config, client, **kwargs)
        except materialization.ValidationMaterializationRejected as exc:
            if exc.diagnostics.get("error_type") != "PionexAPIError":
                raise
            provider = getattr(client, "provider_error_diagnostics", {})
            if callable(provider):
                provider = provider()
            if not isinstance(provider, dict) or not provider:
                raise
            diagnostics = {**exc.diagnostics, **provider}
            raise materialization.ValidationMaterializationRejected(
                str(exc), diagnostics=diagnostics
            ) from None

    wrapped._pionex_provider_error_diagnostics_v0_1 = True  # type: ignore[attr-defined]
    materialization.collect_partition = wrapped
