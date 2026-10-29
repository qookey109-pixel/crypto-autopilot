"""Strict namespace inventory for the disabled Cloud Paper runtime."""
from __future__ import annotations

from crypto_autopilot.paper.run_store_v0_1 import R2PaperRunStore, _clean_component


class CloudPaperRunStore(R2PaperRunStore):
    """Never silently filter unexpected objects from a scanned namespace."""

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
