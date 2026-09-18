from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

from crypto_autopilot.storage.r2 import R2Store


@dataclass(frozen=True, slots=True)
class PaperRunStoreReceipt:
    backend: str
    kind: str
    object_id: str
    location: str
    bytes: int
    replayed: bool


def _canonical_bytes(payload: Mapping[str, object]) -> bytes:
    return json.dumps(
        dict(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _clean_component(value: str, label: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{label} is required")
    if "/" in cleaned or "\\" in cleaned or cleaned in {".", ".."}:
        raise ValueError(f"{label} must be one path component")
    return cleaned


class LocalPaperRunStore:
    """Explicit local persistent JSON store for paper-only run evidence.

    The root must be supplied explicitly. The repository is never selected as a
    default and this backend stores no credentials.
    """

    def __init__(self, root: str | Path) -> None:
        candidate = Path(root).expanduser()
        if not candidate.is_absolute():
            raise ValueError("LocalPaperRunStore root must be an absolute path")
        self.root = candidate

    def _path(self, kind: str, object_id: str) -> Path:
        clean_kind = _clean_component(kind, "kind")
        clean_id = _clean_component(object_id, "object_id")
        return self.root / clean_kind / f"{clean_id}.json"

    def put_json(
        self,
        kind: str,
        object_id: str,
        payload: Mapping[str, object],
    ) -> PaperRunStoreReceipt:
        destination = self._path(kind, object_id)
        body = _canonical_bytes(payload)
        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists():
            existing = destination.read_bytes()
            if existing != body:
                raise ValueError(
                    "paper run store id collision: existing local payload differs"
                )
            return PaperRunStoreReceipt(
                backend="LOCAL_JSON",
                kind=kind,
                object_id=object_id,
                location=str(destination),
                bytes=len(body),
                replayed=True,
            )

        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())

        try:
            os.replace(temporary, destination)
        finally:
            if temporary.exists():
                temporary.unlink()

        return PaperRunStoreReceipt(
            backend="LOCAL_JSON",
            kind=kind,
            object_id=object_id,
            location=str(destination),
            bytes=len(body),
            replayed=False,
        )

    def get_json(self, kind: str, object_id: str) -> dict[str, object] | None:
        path = self._path(kind, object_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("stored paper run JSON must be an object")
        return payload


class R2PaperRunStore:
    """Content-addressed paper-run JSON store over the existing R2 adapter."""

    def __init__(
        self,
        store: R2Store,
        *,
        prefix: str = "paper-run-store/v0.1",
    ) -> None:
        clean = prefix.strip().strip("/")
        if not clean:
            raise ValueError("R2 paper run store prefix is required")
        self.store = store
        self.prefix = clean

    def _key(self, kind: str, object_id: str) -> str:
        clean_kind = _clean_component(kind, "kind")
        clean_id = _clean_component(object_id, "object_id")
        return f"{self.prefix}/{clean_kind}/{clean_id}.json"

    def put_json(
        self,
        kind: str,
        object_id: str,
        payload: Mapping[str, object],
    ) -> PaperRunStoreReceipt:
        key = self._key(kind, object_id)
        body = _canonical_bytes(payload)
        existing = self.store.get_bytes_if_exists(key)
        if existing is not None:
            if existing != body:
                raise ValueError(
                    "paper run store id collision: existing R2 payload differs"
                )
            return PaperRunStoreReceipt(
                backend="R2_JSON",
                kind=kind,
                object_id=object_id,
                location=key,
                bytes=len(body),
                replayed=True,
            )

        receipt = self.store.put_bytes(
            key,
            body,
            content_type="application/json",
            metadata={
                "paper-run-kind": _clean_component(kind, "kind"),
                "paper-run-id": _clean_component(object_id, "object_id"),
            },
        )
        return PaperRunStoreReceipt(
            backend="R2_JSON",
            kind=kind,
            object_id=object_id,
            location=key,
            bytes=receipt.bytes,
            replayed=False,
        )

    def get_json(self, kind: str, object_id: str) -> dict[str, object] | None:
        key = self._key(kind, object_id)
        body = self.store.get_bytes_if_exists(key)
        if body is None:
            return None
        payload = json.loads(body.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("stored paper run JSON must be an object")
        return payload


def run_store_receipt_evidence(receipt: PaperRunStoreReceipt) -> dict[str, object]:
    return {
        "schema": "qookey-paper-run-store-receipt-v0.1",
        "receipt": asdict(receipt),
        "authority": {
            "paper_evidence_storage_only": True,
            "contains_exchange_credentials": False,
            "provider_requests_performed": False,
            "holdout_accessed": False,
            "real_money_order_authorized": False,
            "live_real_trading_authorized": False,
        },
    }
