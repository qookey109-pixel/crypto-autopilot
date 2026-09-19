from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

from crypto_autopilot.storage.r2 import R2Store





@dataclass(frozen=True, slots=True)
class PaperRunStorePolicy:
    local_json_authorized: bool = True
    r2_authorized: bool = True
    github_artifact_secondary_export_authorized: bool = True
    stored_object_becomes_execution_authority: bool = False
    holdout_access_authorized: bool = False
    real_money_order_authorized: bool = False
    live_real_trading_authorized: bool = False

    def __post_init__(self) -> None:
        flags = (
            self.local_json_authorized,
            self.r2_authorized,
            self.github_artifact_secondary_export_authorized,
            self.stored_object_becomes_execution_authority,
            self.holdout_access_authorized,
            self.real_money_order_authorized,
            self.live_real_trading_authorized,
        )
        if any(not isinstance(value, bool) for value in flags):
            raise ValueError("paper run store policy flags must be booleans")
        if not self.local_json_authorized or not self.r2_authorized:
            raise ValueError("Paper Run Store V0.1 requires local and R2 backends")
        if not self.github_artifact_secondary_export_authorized:
            raise ValueError("GitHub Artifact secondary export must remain permitted")
        if (
            self.stored_object_becomes_execution_authority
            or self.holdout_access_authorized
            or self.real_money_order_authorized
            or self.live_real_trading_authorized
        ):
            raise ValueError("Paper Run Store V0.1 storage cannot grant trading authority")


@dataclass(frozen=True, slots=True)
class PaperRunStoreReceipt:
    backend: str
    kind: str
    object_id: str
    location: str
    bytes: int
    replayed: bool


class PaperRunObjectAlreadyExistsError(ValueError):
    """Raised when an atomic create-if-absent precondition loses the race."""


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

    def put_json_if_absent(
        self,
        kind: str,
        object_id: str,
        payload: Mapping[str, object],
    ) -> PaperRunStoreReceipt:
        """Atomically create one local JSON object and never replay/overwrite it."""

        destination = self._path(kind, object_id)
        body = _canonical_bytes(payload)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(
                destination,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError as exc:
            raise PaperRunObjectAlreadyExistsError(
                f"paper run conditional create conflict: {kind}/{object_id}"
            ) from exc

        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(body)
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            if destination.exists():
                destination.unlink()
            raise

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

    def list_json_ids(self, kind: str) -> tuple[str, ...]:
        clean_kind = _clean_component(kind, "kind")
        directory = self.root / clean_kind
        if not directory.exists():
            return ()
        if not directory.is_dir():
            raise ValueError("paper run store kind path must be a directory")
        identifiers: list[str] = []
        for path in directory.iterdir():
            if not path.is_file() or path.suffix != ".json":
                continue
            identifiers.append(_clean_component(path.stem, "object_id"))
        return tuple(sorted(set(identifiers)))


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

    def put_json_if_absent(
        self,
        kind: str,
        object_id: str,
        payload: Mapping[str, object],
    ) -> PaperRunStoreReceipt:
        """Create one R2 JSON object only when the exact key does not exist."""

        key = self._key(kind, object_id)
        body = _canonical_bytes(payload)
        client = getattr(self.store, "client", None)
        bucket = getattr(self.store, "bucket", None)
        if client is None or not isinstance(bucket, str) or not bucket:
            raise ValueError(
                "R2 paper run conditional create requires the S3-compatible client"
            )

        sha256 = hashlib.sha256(body).hexdigest()
        try:
            client.put_object(
                Bucket=bucket,
                Key=key,
                Body=body,
                ContentType="application/json",
                Metadata={
                    "sha256": sha256,
                    "paper-run-kind": _clean_component(kind, "kind"),
                    "paper-run-id": _clean_component(object_id, "object_id"),
                },
                IfNoneMatch="*",
            )
        except Exception as exc:
            response_payload = getattr(exc, "response", {}) or {}
            code = str(response_payload.get("Error", {}).get("Code", ""))
            status = response_payload.get("ResponseMetadata", {}).get(
                "HTTPStatusCode"
            )
            if code in {"PreconditionFailed", "412"} or status == 412:
                raise PaperRunObjectAlreadyExistsError(
                    f"paper run conditional create conflict: {kind}/{object_id}"
                ) from exc
            raise

        return PaperRunStoreReceipt(
            backend="R2_JSON",
            kind=kind,
            object_id=object_id,
            location=key,
            bytes=len(body),
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

    def list_json_ids(self, kind: str) -> tuple[str, ...]:
        clean_kind = _clean_component(kind, "kind")
        prefix = f"{self.prefix}/{clean_kind}/"
        identifiers: list[str] = []

        list_keys = getattr(self.store, "list_keys", None)
        if callable(list_keys):
            keys = tuple(list_keys(prefix))
        else:
            client = getattr(self.store, "client", None)
            bucket = getattr(self.store, "bucket", None)
            if client is None or not isinstance(bucket, str) or not bucket:
                raise ValueError("R2 paper run store cannot list object ids")
            paginator = client.get_paginator("list_objects_v2")
            discovered: list[str] = []
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                contents = page.get("Contents", [])
                if not isinstance(contents, list):
                    raise ValueError("R2 list response Contents must be an array")
                for row in contents:
                    if not isinstance(row, dict):
                        raise ValueError("R2 list response object must be a mapping")
                    key = row.get("Key")
                    if not isinstance(key, str) or not key:
                        raise ValueError("R2 list response key is invalid")
                    discovered.append(key)
            keys = tuple(sorted(set(discovered)))

        for key in keys:
            if not isinstance(key, str):
                raise ValueError("R2 paper run store key must be a string")
            if not key.startswith(prefix) or not key.endswith(".json"):
                continue
            suffix = key[len(prefix):-5]
            if "/" in suffix or not suffix:
                continue
            identifiers.append(_clean_component(suffix, "object_id"))
        return tuple(sorted(set(identifiers)))


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


def paper_run_store_policy_from_config(
    payload: Mapping[str, object],
) -> PaperRunStorePolicy:
    if payload.get("schema") != "qookey-paper-run-store-v0.1":
        raise ValueError("unsupported paper run store config")
    backends = payload.get("backends")
    authority = payload.get("authority")
    if not isinstance(backends, Mapping) or not isinstance(authority, Mapping):
        raise ValueError("paper run store backends/authority objects are required")
    local = backends.get("local_json")
    r2 = backends.get("cloudflare_r2")
    artifact = backends.get("github_artifact")
    if not isinstance(local, Mapping) or not isinstance(r2, Mapping) or not isinstance(
        artifact, Mapping
    ):
        raise ValueError("paper run store backend configs are required")
    fields = {
        "local_json_authorized": local.get("authorized"),
        "r2_authorized": r2.get("authorized"),
        "github_artifact_secondary_export_authorized": artifact.get(
            "authorized_as_secondary_export"
        ),
        "stored_object_becomes_execution_authority": authority.get(
            "stored_object_becomes_execution_authority"
        ),
        "holdout_access_authorized": authority.get("holdout_access_authorized"),
        "real_money_order_authorized": authority.get("real_money_order_authorized"),
        "live_real_trading_authorized": authority.get(
            "live_real_trading_authorized"
        ),
    }
    for key, value in fields.items():
        if not isinstance(value, bool):
            raise ValueError(f"{key} must be a JSON boolean")
    return PaperRunStorePolicy(**fields)
