from __future__ import annotations

from typing import Any, Callable

from .core import (
    evaluate_strategy,
    get_indicators,
    run_paper_backtest,
    size_long_trade_tool,
)
from .registry import SAFETY_BOUNDARY, list_capabilities_v0_2
from .research import (
    build_research_report,
    compare_backtests,
    stress_paper_backtest,
    validate_candles,
)

API_VERSION = "v0"
TOOLKIT_VERSION = "0.2"
SERVICE_NAME = "qookey-crypto-toolkit-api-v0-2"
MAX_REQUEST_BYTES = 2_000_000


def _error(status_code: int, code: str, message: str) -> tuple[int, dict[str, Any]]:
    return status_code, {
        "schema": "qookey-crypto-toolkit-api-error-v0.2",
        "status": "ERROR",
        "error": {"code": code, "message": message},
        "authority": dict(SAFETY_BOUNDARY),
    }


def health() -> dict[str, Any]:
    return {
        "schema": "qookey-crypto-toolkit-api-health-v0.2",
        "status": "PASS",
        "service": SERVICE_NAME,
        "mode": "RESEARCH_ONLY",
        "api_version": API_VERSION,
        "toolkit_version": TOOLKIT_VERSION,
        "authority": dict(SAFETY_BOUNDARY),
    }


def _indicators(payload: dict[str, Any]) -> dict[str, Any]:
    candles = payload.get("candles")
    interval = payload.get("interval")
    if not isinstance(candles, list):
        raise ValueError("indicators payload requires a candles list")
    if not isinstance(interval, str) or not interval.strip():
        raise ValueError("indicators payload requires a non-empty interval")
    return get_indicators(
        candles,
        interval=interval,
        include_series=bool(payload.get("include_series", False)),
    )


def _validate(payload: dict[str, Any]) -> dict[str, Any]:
    candles = payload.get("candles")
    interval = payload.get("interval")
    if not isinstance(candles, list):
        raise ValueError("validate payload requires a candles list")
    if not isinstance(interval, str) or not interval.strip():
        raise ValueError("validate payload requires a non-empty interval")
    return validate_candles(candles, interval=interval)


_POST_ROUTES: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "/v0/validate": _validate,
    "/v0/indicators": _indicators,
    "/v0/strategy": evaluate_strategy,
    "/v0/risk": size_long_trade_tool,
    "/v0/backtest": run_paper_backtest,
    "/v0/stress": stress_paper_backtest,
    "/v0/compare": compare_backtests,
    "/v0/report": build_research_report,
}


def openapi_document() -> dict[str, Any]:
    json_object = {"type": "object", "additionalProperties": True}
    paths: dict[str, Any] = {
        "/healthz": {
            "get": {
                "summary": "Research-only service health",
                "responses": {"200": {"description": "Healthy"}},
            }
        },
        "/v0/capabilities": {
            "get": {
                "summary": "List Toolkit V0.2 capabilities and authority boundary",
                "responses": {"200": {"description": "Capability registry"}},
            }
        },
    }
    for path, summary in (
        ("/v0/validate", "Audit supplied candles without repair or interpolation"),
        ("/v0/indicators", "Calculate deterministic technical indicators"),
        ("/v0/strategy", "Evaluate the deterministic strategy gate"),
        ("/v0/risk", "Calculate paper-only risk sizing"),
        ("/v0/backtest", "Run deterministic paper-only backtest"),
        ("/v0/stress", "Run bounded paper-backtest execution-cost stress scenarios"),
        ("/v0/compare", "Compare paper-backtest evidence descriptively"),
        ("/v0/report", "Build a deterministic research-only report"),
    ):
        paths[path] = {
            "post": {
                "summary": summary,
                "security": [{"bearerAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": json_object}},
                },
                "responses": {
                    "200": {"description": "Research result"},
                    "400": {"description": "Invalid request"},
                    "401": {"description": "Authentication required when configured"},
                },
            }
        }
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Qookey Crypto Toolkit API",
            "version": "0.2.0",
            "description": (
                "Research-only HTTP facade over deterministic Toolkit V0.2 functions. "
                "It grants no provider, holdout, promotion, order, or live-trading authority."
            ),
        },
        "paths": paths,
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer"}
            }
        },
    }


def dispatch_request(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    normalized_method = method.upper().strip()
    normalized_path = path.split("?", 1)[0].rstrip("/") or "/"

    if normalized_method == "GET" and normalized_path == "/healthz":
        return 200, health()
    if normalized_method == "GET" and normalized_path == "/v0/capabilities":
        return 200, list_capabilities_v0_2()
    if normalized_method == "GET" and normalized_path == "/openapi.json":
        return 200, openapi_document()

    if normalized_path in _POST_ROUTES and normalized_method != "POST":
        return _error(405, "METHOD_NOT_ALLOWED", "this route only accepts POST")
    if normalized_method == "POST" and normalized_path in _POST_ROUTES:
        if not isinstance(payload, dict):
            return _error(400, "INVALID_JSON_OBJECT", "request body must be a JSON object")
        try:
            return 200, _POST_ROUTES[normalized_path](payload)
        except (KeyError, TypeError, ValueError) as exc:
            return _error(400, "INVALID_TOOL_INPUT", str(exc))

    return _error(404, "NOT_FOUND", "unknown Toolkit API route")


__all__ = [
    "API_VERSION",
    "MAX_REQUEST_BYTES",
    "SERVICE_NAME",
    "TOOLKIT_VERSION",
    "dispatch_request",
    "health",
    "openapi_document",
]
