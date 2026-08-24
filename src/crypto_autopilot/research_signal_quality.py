"""Read-only lineage and usability checks for public research signals."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol

from .research_signal_layer import KOLForecast, ResearchSignalLayerError, validate_kol_forecast


class ResearchSignalQualityError(ValueError):
    """Raised when research-signal evidence is absent or malformed."""


class ReadOnlyObjectStore(Protocol):
    def get_bytes_if_exists(self, key: str) -> bytes | None: ...

    def get_bytes_verified(self, key: str, *, expected_sha256: str) -> bytes: ...


def _object(payload: bytes, *, label: str) -> dict[str, Any]:
    try:
        decoded = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResearchSignalQualityError(f"{label} is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise ResearchSignalQualityError(f"{label} must be a JSON object")
    return decoded


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _validated_key(value: Any, *, prefix: str, suffix: str, label: str) -> str:
    key = str(value or "")
    if not key.startswith(prefix) or not key.endswith(suffix) or ".." in key:
        raise ResearchSignalQualityError(f"{label} is outside the authorized namespace")
    return key


def _validated_sha256(value: Any, *, label: str) -> str:
    digest = str(value or "")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ResearchSignalQualityError(f"{label} is not a SHA-256 digest")
    return digest


def evaluate_research_signal_quality(
    store: ReadOnlyObjectStore,
    *,
    namespace: str,
    now: datetime,
    max_age_seconds: int = 129_600,
) -> dict[str, Any]:
    """Read and verify exactly latest -> manifest -> payload without listing R2."""

    namespace = namespace.strip("/")
    if not namespace:
        raise ResearchSignalQualityError("research signal namespace is required")
    if max_age_seconds <= 0:
        raise ResearchSignalQualityError("max_age_seconds must be positive")
    prefix = f"{namespace}/runs/run="
    latest_key = f"{namespace}/latest.json"
    latest_bytes = store.get_bytes_if_exists(latest_key)
    if latest_bytes is None:
        raise ResearchSignalQualityError("latest research signal pointer does not exist")
    latest = _object(latest_bytes, label="latest pointer")
    if latest.get("schema") != "research-signal-layer-latest-v0.2":
        raise ResearchSignalQualityError("unexpected latest pointer schema")

    manifest_key = _validated_key(
        latest.get("manifest_key"),
        prefix=prefix,
        suffix="/manifest.json",
        label="manifest key",
    )
    manifest_sha256 = _validated_sha256(
        latest.get("manifest_sha256"), label="manifest SHA-256"
    )
    manifest_bytes = store.get_bytes_verified(
        manifest_key, expected_sha256=manifest_sha256
    )
    if _sha256(manifest_bytes) != manifest_sha256:
        raise ResearchSignalQualityError("manifest content does not match latest pointer")
    manifest = _object(manifest_bytes, label="manifest")
    if manifest.get("schema") != "research-signal-layer-manifest-v0.2":
        raise ResearchSignalQualityError("unexpected manifest schema")

    run_id = str(latest.get("run_id") or "")
    if not run_id or manifest.get("run_id") != run_id:
        raise ResearchSignalQualityError("latest and manifest run IDs disagree")
    payload_key = _validated_key(
        manifest.get("payload_key"),
        prefix=f"{namespace}/runs/run={run_id}/",
        suffix="/signals.json",
        label="payload key",
    )
    payload_sha256 = _validated_sha256(
        manifest.get("payload_sha256"), label="payload SHA-256"
    )
    payload_bytes = store.get_bytes_verified(payload_key, expected_sha256=payload_sha256)
    if _sha256(payload_bytes) != payload_sha256:
        raise ResearchSignalQualityError("payload content does not match manifest")
    payload = _object(payload_bytes, label="signal payload")
    if payload.get("schema") != "research-signal-layer-run-v0.2":
        raise ResearchSignalQualityError("unexpected signal payload schema")
    if payload.get("mode") != "RESEARCH_ONLY" or payload.get("run_id") != run_id:
        raise ResearchSignalQualityError("signal payload authority or run ID is invalid")
    observed_authority = payload.get("authority")
    if not isinstance(observed_authority, Mapping):
        raise ResearchSignalQualityError("signal payload authority is missing")
    for forbidden in (
        "automatic_model_promotion",
        "direct_trade_trigger",
        "real_money_order",
        "live_trading",
    ):
        if observed_authority.get(forbidden) is not False:
            raise ResearchSignalQualityError(f"signal payload unexpectedly authorizes {forbidden}")

    snapshots = payload.get("source_snapshots")
    forecasts = payload.get("kol_forecasts")
    if not isinstance(snapshots, list) or not isinstance(forecasts, list):
        raise ResearchSignalQualityError("signal payload collections are malformed")
    generated_at = str(payload.get("generated_at_utc") or "")
    if latest.get("generated_at_utc") != generated_at:
        raise ResearchSignalQualityError("latest and payload generation timestamps disagree")
    try:
        generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ResearchSignalQualityError("payload generation timestamp is invalid") from exc
    if generated.tzinfo is None:
        raise ResearchSignalQualityError("payload generation timestamp needs an offset")
    now = now.astimezone(timezone.utc)
    generated = generated.astimezone(timezone.utc)
    age_seconds = int((now - generated).total_seconds())
    if age_seconds < -300:
        raise ResearchSignalQualityError("signal payload is dated in the future")
    now_ms = int(now.timestamp() * 1000)
    for row in forecasts:
        if not isinstance(row, Mapping):
            raise ResearchSignalQualityError("forecast entry is not an object")
        try:
            forecast = KOLForecast(
                forecast_id=str(row["forecast_id"]),
                source=str(row["source"]),
                source_url=str(row["source_url"]),
                symbol=str(row["symbol"]),
                direction=str(row["direction"]),
                confidence=float(row["confidence"]),
                published_at_ms=int(row["published_at_ms"]),
                target_time_ms=int(row["target_time_ms"]),
                ingested_at_ms=int(row["ingested_at_ms"]),
                content_sha256=str(row["content_sha256"]),
            )
            validate_kol_forecast(forecast)
        except (KeyError, TypeError, ValueError, ResearchSignalLayerError) as exc:
            raise ResearchSignalQualityError("forecast entry is invalid") from exc
        if forecast.ingested_at_ms > now_ms + 300_000:
            raise ResearchSignalQualityError("forecast ingestion is dated in the future")
    parsed = sum(
        1 for row in snapshots if isinstance(row, Mapping) and row.get("status") == "PARSED"
    )
    failed = sum(
        1
        for row in snapshots
        if isinstance(row, Mapping) and row.get("status") == "FETCH_FAILED"
    )
    if forecasts:
        quality = "FORECAST_READY"
    elif parsed:
        quality = "METADATA_ONLY"
    else:
        quality = "NO_DATA"
    return {
        "schema": "research-signal-quality-v0.1",
        "status": "ALERT" if age_seconds > max_age_seconds else "PASS",
        "quality": quality,
        "evaluated_at_utc": now.isoformat().replace("+00:00", "Z"),
        "run_id": run_id,
        "lineage": "PASS",
        "generated_at_utc": generated_at,
        "age_seconds": max(0, age_seconds),
        "max_age_seconds": max_age_seconds,
        "objects_read": [latest_key, manifest_key, payload_key],
        "source_count": len(snapshots),
        "parsed_source_count": parsed,
        "failed_source_count": failed,
        "forecast_count": len(forecasts),
        "authority": {
            "r2_exact_object_read_only": True,
            "r2_list": False,
            "r2_write": False,
            "provider_access": False,
            "holdout_access": False,
            "automatic_model_promotion": False,
            "direct_trade_trigger": False,
            "real_money_order": False,
            "live_trading": False,
        },
    }
