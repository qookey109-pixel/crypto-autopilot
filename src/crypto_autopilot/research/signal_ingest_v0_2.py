"""Bounded public research-signal ingestion for the V0.2 schedule.

The collector is intentionally conservative: it fetches only configured HTTPS
URLs, keeps raw source metadata/content hashes, and creates KOL forecasts only
when a source publishes an explicit structured ``forecasts`` array.  It never
infers a direction from prose and never produces a trade decision.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from crypto_autopilot.training.online_r2 import current_bucket_bytes
from crypto_autopilot.research.signal_layer import KOLForecast, deduplicate_kol_forecasts
from crypto_autopilot.storage.r2 import R2Store


class ResearchSignalIngestError(ValueError):
    """Raised when an ingestion contract is malformed or cannot be published."""


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    source_id: str
    source_url: str
    retrieved_at_ms: int
    status: str
    http_status: int | None
    content_type: str | None
    bytes: int
    body_sha256: str | None
    title: str | None
    description: str | None
    forecast_count: int
    error: str | None = None


def _now_ms() -> int:
    return int(time.time() * 1000)


def _safe_url(value: str) -> str:
    parts = urlsplit(str(value).strip())
    if parts.scheme != "https" or not parts.netloc:
        raise ResearchSignalIngestError("source URL must be HTTPS")
    return str(value).strip()


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _meta_value(text: str, *, key: str) -> str | None:
    pattern = re.compile(
        rf'<meta[^>]+(?:property|name)=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']*)["\']',
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return None
    return html.unescape(match.group(1)).strip() or None


def _structured_payload(body: bytes, content_type: str | None) -> Mapping[str, Any] | None:
    if content_type and "json" in content_type.lower():
        try:
            value = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return value if isinstance(value, Mapping) else None
    return None


def _forecast_from_payload(
    source_id: str,
    source_url: str,
    payload: Mapping[str, Any],
    *,
    retrieved_at_ms: int,
    content_sha256: str,
) -> tuple[KOLForecast, ...]:
    raw_forecasts = payload.get("forecasts")
    if not isinstance(raw_forecasts, list):
        return ()
    result: list[KOLForecast] = []
    for item in raw_forecasts:
        if not isinstance(item, Mapping):
            raise ResearchSignalIngestError(f"{source_id} forecast entry is not an object")
        published = int(item.get("published_at_ms", retrieved_at_ms))
        target = int(item["target_time_ms"])
        result.append(
            KOLForecast(
                forecast_id=str(item["forecast_id"]),
                source=source_id,
                source_url=source_url,
                symbol=str(item["symbol"]),
                direction=str(item["direction"]),
                confidence=float(item["confidence"]),
                published_at_ms=published,
                target_time_ms=target,
                ingested_at_ms=retrieved_at_ms,
                content_sha256=content_sha256,
            )
        )
    return tuple(result)


def parse_source_payload(
    *,
    source_id: str,
    source_url: str,
    body: bytes,
    content_type: str | None,
    retrieved_at_ms: int,
    http_status: int = 200,
) -> tuple[SourceSnapshot, tuple[KOLForecast, ...]]:
    """Parse one public response without inferring forecasts from prose."""

    url = _safe_url(source_url)
    digest = _sha256(body)
    title = description = None
    payload = _structured_payload(body, content_type)
    if payload is not None:
        title = str(payload.get("title") or "").strip() or None
        description = str(payload.get("description") or "").strip() or None
    else:
        text = body.decode("utf-8", errors="replace")
        title = _meta_value(text, key="og:title") or _meta_value(text, key="twitter:title")
        description = _meta_value(text, key="description")
    forecasts = _forecast_from_payload(
        source_id,
        url,
        payload or {},
        retrieved_at_ms=retrieved_at_ms,
        content_sha256=digest,
    )
    snapshot = SourceSnapshot(
        source_id=source_id,
        source_url=url,
        retrieved_at_ms=retrieved_at_ms,
        status="PARSED",
        http_status=http_status,
        content_type=content_type,
        bytes=len(body),
        body_sha256=digest,
        title=title,
        description=description,
        forecast_count=len(forecasts),
    )
    return snapshot, forecasts


def fetch_public_source(
    *,
    source_id: str,
    source_url: str,
    timeout_seconds: float,
    max_bytes: int,
    opener: Callable[..., Any] = urlopen,
    retrieved_at_ms: int | None = None,
) -> tuple[SourceSnapshot, tuple[KOLForecast, ...]]:
    """Fetch one source with strict size/time bounds and fail-closed errors."""

    url = _safe_url(source_url)
    retrieved = _now_ms() if retrieved_at_ms is None else retrieved_at_ms
    request = Request(
        url,
        headers={
            "Accept": "application/json,text/html;q=0.9,*/*;q=0.1",
            "User-Agent": "crypto-autopilot-research/0.2",
        },
    )
    try:
        with opener(request, timeout=timeout_seconds) as response:
            status = int(getattr(response, "status", 200))
            content_type = response.headers.get("Content-Type")
            body = response.read(max_bytes + 1)
            if len(body) > max_bytes:
                raise ResearchSignalIngestError("source response exceeds configured byte limit")
            return parse_source_payload(
                source_id=source_id,
                source_url=url,
                body=body,
                content_type=content_type,
                retrieved_at_ms=retrieved,
                http_status=status,
            )
    except Exception as exc:  # network/provider failures become evidence, not fallback
        snapshot = SourceSnapshot(
            source_id=source_id,
            source_url=url,
            retrieved_at_ms=retrieved,
            status="FETCH_FAILED",
            http_status=None,
            content_type=None,
            bytes=0,
            body_sha256=None,
            title=None,
            description=None,
            forecast_count=0,
            error=str(exc)[:240],
        )
        return snapshot, ()


def collect_sources(
    sources: Iterable[Mapping[str, Any]],
    *,
    timeout_seconds: float,
    max_bytes: int,
    opener: Callable[..., Any] = urlopen,
    retrieved_at_ms: int | None = None,
) -> tuple[tuple[SourceSnapshot, ...], tuple[KOLForecast, ...]]:
    snapshots: list[SourceSnapshot] = []
    forecasts: list[KOLForecast] = []
    for source in sources:
        if source.get("enabled", True) is not True:
            continue
        source_id = str(source.get("source_id", "")).strip()
        source_url = str(source.get("url", "")).strip()
        if not source_id or not source_url:
            raise ResearchSignalIngestError("enabled source requires source_id and url")
        snapshot, items = fetch_public_source(
            source_id=source_id,
            source_url=source_url,
            timeout_seconds=timeout_seconds,
            max_bytes=max_bytes,
            opener=opener,
            retrieved_at_ms=retrieved_at_ms,
        )
        snapshots.append(snapshot)
        forecasts.extend(items)
    return tuple(snapshots), deduplicate_kol_forecasts([], forecasts)


def build_signal_payload(
    *,
    run_id: str,
    generated_at_utc: str,
    snapshots: Iterable[SourceSnapshot],
    forecasts: Iterable[KOLForecast],
) -> dict[str, Any]:
    snapshot_rows = [asdict(item) for item in snapshots]
    forecast_rows = [asdict(item) for item in forecasts]
    return {
        "schema": "research-signal-layer-run-v0.2",
        "status": "PASS" if any(item["status"] == "PARSED" for item in snapshot_rows) else "NO_DATA",
        "mode": "RESEARCH_ONLY",
        "run_id": run_id,
        "generated_at_utc": generated_at_utc,
        "source_snapshots": snapshot_rows,
        "kol_forecasts": forecast_rows,
        "authority": {
            "external_source_fetch": True,
            "production_r2_write": True,
            "automatic_model_promotion": False,
            "direct_trade_trigger": False,
            "real_money_order": False,
            "live_trading": False,
        },
    }


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def publish_signal_payload(
    store: R2Store,
    *,
    payload: Mapping[str, Any],
    namespace: str,
    run_id: str,
    hard_stop_bytes: int,
    planned_reservation_bytes: int,
) -> dict[str, Any]:
    """Publish immutable run evidence and a mutable latest pointer after gates."""

    current = current_bucket_bytes(store)
    if current + planned_reservation_bytes > hard_stop_bytes:
        return {
            "status": "BLOCKED",
            "stage": "R2_FREE_ONLY_HEADROOM_GATE_BLOCKED_BEFORE_WRITE",
            "current_bucket_bytes": current,
            "planned_reservation_bytes": planned_reservation_bytes,
            "hard_stop_bytes": hard_stop_bytes,
            "r2_writes_performed": False,
        }
    prefix = f"{namespace.rstrip('/')}/runs/run={run_id}"
    payload_bytes = _json_bytes(payload)
    manifest = {
        "schema": "research-signal-layer-manifest-v0.2",
        "run_id": run_id,
        "payload_key": f"{prefix}/signals.json",
        "payload_sha256": _sha256(payload_bytes),
        "bytes": len(payload_bytes),
    }
    objects = {
        f"{prefix}/signals.json": payload_bytes,
        f"{prefix}/manifest.json": _json_bytes(manifest),
    }
    latest_key = f"{namespace.rstrip('/')}/latest.json"
    latest = {
        "schema": "research-signal-layer-latest-v0.2",
        "run_id": run_id,
        "manifest_key": f"{prefix}/manifest.json",
        "manifest_sha256": _sha256(objects[f"{prefix}/manifest.json"]),
        "generated_at_utc": payload.get("generated_at_utc"),
    }
    objects[latest_key] = _json_bytes(latest)
    planned = sum(len(item) for item in objects.values())
    current = current_bucket_bytes(store)
    if current + planned > hard_stop_bytes:
        return {
            "status": "BLOCKED",
            "stage": "R2_FREE_ONLY_HEADROOM_GATE_BLOCKED_BEFORE_WRITE",
            "current_bucket_bytes": current,
            "planned_write_bytes": planned,
            "hard_stop_bytes": hard_stop_bytes,
            "r2_writes_performed": False,
        }
    for key, body in objects.items():
        immutable = key != latest_key
        existing = store.get_bytes_if_exists(key) if immutable else None
        if immutable and existing is not None and existing != body:
            raise ResearchSignalIngestError(f"immutable signal object conflict: {key}")
        if existing == body:
            continue
        store.put_bytes(
            key,
            body,
            content_type="application/json",
            metadata={"provider": "public_research", "version": "v0.2"},
        )
    return {
        "status": "PUBLISHED",
        "stage": "RESEARCH_SIGNAL_LAYER_R2_PUBLISHED_V0_2",
        "r2_writes_performed": True,
        "run_id": run_id,
        "latest_key": latest_key,
        "objects": len(objects),
        "planned_write_bytes": planned,
    }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_config(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != "research-signal-layer-v0.2":
        raise ResearchSignalIngestError("unexpected research signal V0.2 config")
    return value
