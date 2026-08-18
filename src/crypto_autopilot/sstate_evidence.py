from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from enum import Enum

from .historical import INTERVAL_MS
from .historical_sstate import HistoricalSStatePoint
from .models import SStateContext


RECORD_SCHEMA = "historical-sstate-records-v0.1"


class SStateEvidenceError(RuntimeError):
    pass


class EvidenceKind(str, Enum):
    REAL_RECORDED = "REAL_RECORDED"
    FIXTURE = "FIXTURE"


class AvailabilityBasis(str, Enum):
    RECORDED_RUNTIME = "RECORDED_RUNTIME"
    RECONSTRUCTED = "RECONSTRUCTED"


class EvidenceStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


def _validate_sha256(value: str, field_name: str) -> str:
    digest = value.strip().lower()
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError(f"{field_name} must be a 64-character hex digest")
    return digest


@dataclass(frozen=True, slots=True)
class SStateEvidenceRecord:
    symbol: str
    bar_time_ms: int
    available_at_ms: int
    state: str
    probability: float | None
    samples: int
    available: bool

    def __post_init__(self) -> None:
        if not self.symbol.strip() or not self.state.strip():
            raise ValueError("symbol and state are required")
        if self.bar_time_ms < 0 or self.available_at_ms < 0:
            raise ValueError("timestamps cannot be negative")
        if self.samples < 0:
            raise ValueError("samples cannot be negative")
        if self.probability is not None:
            if not math.isfinite(self.probability) or not 0.0 <= self.probability <= 1.0:
                raise ValueError("probability must be finite and within [0, 1]")

    @property
    def identity(self) -> tuple[str, int]:
        return (self.symbol, self.bar_time_ms)


@dataclass(frozen=True, slots=True)
class SStateEvidenceManifest:
    evidence_id: str
    status: EvidenceStatus
    evidence_kind: EvidenceKind
    availability_basis: AvailabilityBasis
    interval: str
    producer_ref: str
    producer_sha256: str
    source_ref: str
    payload_sha256: str
    record_count: int
    generated_at_ms: int

    def __post_init__(self) -> None:
        required = (
            self.evidence_id,
            self.interval,
            self.producer_ref,
            self.source_ref,
        )
        if any(not value.strip() for value in required):
            raise ValueError("evidence id, interval, producer ref and source ref are required")
        if self.interval not in INTERVAL_MS:
            raise ValueError(f"unsupported interval: {self.interval}")
        _validate_sha256(self.producer_sha256, "producer_sha256")
        _validate_sha256(self.payload_sha256, "payload_sha256")
        if self.record_count < 0:
            raise ValueError("record_count cannot be negative")
        if self.generated_at_ms < 0:
            raise ValueError("generated_at_ms cannot be negative")


@dataclass(frozen=True, slots=True)
class VerifiedSStateEvidence:
    evidence_id: str
    payload_sha256: str
    point_count: int
    first_bar_time_ms: int | None
    last_bar_time_ms: int | None
    points: tuple[HistoricalSStatePoint, ...]


def _record_dict(record: SStateEvidenceRecord) -> dict[str, object]:
    return {
        "available": record.available,
        "available_at_ms": record.available_at_ms,
        "bar_time_ms": record.bar_time_ms,
        "probability": record.probability,
        "samples": record.samples,
        "state": record.state,
        "symbol": record.symbol,
    }


def _canonical_records(
    records: list[SStateEvidenceRecord] | tuple[SStateEvidenceRecord, ...],
) -> tuple[SStateEvidenceRecord, ...]:
    source = tuple(records)
    identities = [record.identity for record in source]
    if len(set(identities)) != len(identities):
        raise SStateEvidenceError("duplicate symbol/bar identity in SState evidence")
    return tuple(sorted(source, key=lambda record: (record.bar_time_ms, record.symbol)))


def encode_sstate_evidence_records(
    records: list[SStateEvidenceRecord] | tuple[SStateEvidenceRecord, ...],
) -> bytes:
    canonical = _canonical_records(records)
    payload = {
        "records": [_record_dict(record) for record in canonical],
        "schema": RECORD_SCHEMA,
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return text.encode("utf-8")


def payload_sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _strict_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise SStateEvidenceError(f"{field_name} must be an integer")
    return value


def _decode_record(value: object) -> SStateEvidenceRecord:
    if not isinstance(value, dict):
        raise SStateEvidenceError("each evidence record must be an object")
    expected = {
        "available",
        "available_at_ms",
        "bar_time_ms",
        "probability",
        "samples",
        "state",
        "symbol",
    }
    if set(value) != expected:
        raise SStateEvidenceError("evidence record fields do not match the frozen schema")
    if not isinstance(value["symbol"], str) or not isinstance(value["state"], str):
        raise SStateEvidenceError("symbol and state must be strings")
    if not isinstance(value["available"], bool):
        raise SStateEvidenceError("available must be boolean")
    probability_raw = value["probability"]
    probability: float | None
    if probability_raw is None:
        probability = None
    elif isinstance(probability_raw, (int, float)) and not isinstance(probability_raw, bool):
        probability = float(probability_raw)
    else:
        raise SStateEvidenceError("probability must be numeric or null")
    return SStateEvidenceRecord(
        symbol=value["symbol"],
        bar_time_ms=_strict_int(value["bar_time_ms"], "bar_time_ms"),
        available_at_ms=_strict_int(value["available_at_ms"], "available_at_ms"),
        state=value["state"],
        probability=probability,
        samples=_strict_int(value["samples"], "samples"),
        available=value["available"],
    )


def decode_sstate_evidence_records(payload: bytes) -> tuple[SStateEvidenceRecord, ...]:
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SStateEvidenceError("invalid historical SState evidence JSON") from exc
    if not isinstance(decoded, dict) or set(decoded) != {"records", "schema"}:
        raise SStateEvidenceError("evidence payload root does not match the frozen schema")
    if decoded["schema"] != RECORD_SCHEMA:
        raise SStateEvidenceError(f"unsupported evidence schema: {decoded['schema']!r}")
    if not isinstance(decoded["records"], list):
        raise SStateEvidenceError("records must be an array")
    records = tuple(_decode_record(value) for value in decoded["records"])
    return _canonical_records(records)


def ingest_sstate_evidence_bundle(
    *,
    payload: bytes,
    manifest: SStateEvidenceManifest,
    ingestion_time_ms: int,
) -> VerifiedSStateEvidence:
    """Verify real, recorded SState evidence and convert it to replay points.

    V0.1 accepts only contemporaneously recorded runtime authority. Fixtures and
    after-the-fact reconstructed outputs remain non-authoritative for historical
    replay until a separate reconstruction proof is designed and approved.
    """

    if ingestion_time_ms < 0:
        raise ValueError("ingestion_time_ms cannot be negative")
    if manifest.status is not EvidenceStatus.PASS:
        raise SStateEvidenceError("manifest status must be PASS")
    if manifest.evidence_kind is not EvidenceKind.REAL_RECORDED:
        raise SStateEvidenceError("fixture SState evidence cannot become historical authority")
    if manifest.availability_basis is not AvailabilityBasis.RECORDED_RUNTIME:
        raise SStateEvidenceError("reconstructed SState availability is not authoritative in V0.1")
    if manifest.interval != "4H":
        raise SStateEvidenceError("SState Intraday Wave V0.1 historical context requires 4H evidence")
    if manifest.generated_at_ms > ingestion_time_ms:
        raise SStateEvidenceError("manifest generated_at_ms cannot be in the ingestion future")

    actual_payload_sha = payload_sha256(payload)
    if actual_payload_sha != manifest.payload_sha256.lower():
        raise SStateEvidenceError("historical SState payload SHA-256 mismatch")

    records = decode_sstate_evidence_records(payload)
    if encode_sstate_evidence_records(records) != payload:
        raise SStateEvidenceError("historical SState payload must use canonical encoding")
    if len(records) != manifest.record_count:
        raise SStateEvidenceError("historical SState record_count mismatch")

    interval_ms = INTERVAL_MS[manifest.interval]
    points: list[HistoricalSStatePoint] = []
    source_ref = f"{manifest.source_ref}#evidence={manifest.evidence_id}"
    for record in records:
        if record.bar_time_ms % interval_ms != 0:
            raise SStateEvidenceError(
                f"SState bar is not aligned to {manifest.interval}: {record.identity}"
            )
        earliest_available = record.bar_time_ms + interval_ms
        if record.available_at_ms < earliest_available:
            raise SStateEvidenceError(
                "SState output cannot be historically available before its 4H bar closes: "
                f"{record.identity}"
            )
        if record.available_at_ms > manifest.generated_at_ms:
            raise SStateEvidenceError(
                "record availability cannot be later than manifest generation time"
            )
        points.append(
            HistoricalSStatePoint(
                symbol=record.symbol,
                bar_time_ms=record.bar_time_ms,
                available_at_ms=record.available_at_ms,
                context=SStateContext(
                    state=record.state,
                    probability=record.probability,
                    samples=record.samples,
                    available=record.available,
                ),
                source_ref=source_ref,
                source_sha256=actual_payload_sha,
            )
        )

    first = records[0].bar_time_ms if records else None
    last = records[-1].bar_time_ms if records else None
    return VerifiedSStateEvidence(
        evidence_id=manifest.evidence_id,
        payload_sha256=actual_payload_sha,
        point_count=len(points),
        first_bar_time_ms=first,
        last_bar_time_ms=last,
        points=tuple(points),
    )
