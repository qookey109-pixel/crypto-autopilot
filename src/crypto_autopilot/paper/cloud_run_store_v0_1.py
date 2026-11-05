"""Strict namespace inventory for the disabled Cloud Paper runtime."""
from __future__ import annotations

from collections.abc import Mapping

from crypto_autopilot.paper.run_store_v0_1 import (
    PaperRunObjectAlreadyExistsError,
    PaperRunStoreReceipt,
    R2PaperRunStore,
    _canonical_bytes,
    _clean_component,
)


class CloudPaperRunStore(R2PaperRunStore):
    """Never silently filter unexpected objects from a scanned namespace."""

    def put_json(
        self, kind: str, object_id: str, payload: Mapping[str, object],
    ) -> PaperRunStoreReceipt:
        """Create atomically; identical existing objects are read-only replays."""
        key = self._key(kind, object_id)
        body = _canonical_bytes(payload)

        def replay(existing: bytes | None) -> PaperRunStoreReceipt:
            if existing is None or existing != body:
                raise ValueError("paper run store id collision or unverified object")
            return PaperRunStoreReceipt(
                backend="R2_JSON", kind=kind, object_id=object_id,
                location=key, bytes=len(body), replayed=True,
            )

        existing = self.store.get_bytes_if_exists(key)
        if existing is not None:
            return replay(existing)
        try:
            return self.put_json_if_absent(kind, object_id, payload)
        except PaperRunObjectAlreadyExistsError:
            # Only a definitive 412 permits readback. A timeout or other
            # ambiguous write outcome propagates and is never retried here.
            return replay(self.store.get_bytes_if_exists(key))

    def list_json_ids(self, kind: str) -> tuple[str, ...]:
        clean_kind = _clean_component(kind, "kind")
        if clean_kind != kind:
            raise ValueError("Cloud Paper inventory kind is noncanonical")
        prefix = f"{self.prefix}/{clean_kind}/"
        list_keys = getattr(self.store, "list_keys", None)
        if not callable(list_keys):
            raise ValueError("Cloud Paper inventory requires complete bounded listing")
        identities: set[str] = set()
        for key in list_keys(prefix):
            if not isinstance(key, str) or not key.startswith(prefix) or not key.endswith(".json"):
                raise ValueError("Cloud Paper inventory key is outside the canonical format")
            identity = key[len(prefix):-5]
            if _clean_component(identity, "object_id") != identity or identity in identities:
                raise ValueError("Cloud Paper inventory identity is noncanonical or repeated")
            identities.add(identity)
        return tuple(sorted(identities))
