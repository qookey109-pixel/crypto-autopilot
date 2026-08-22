"""Research-only lineage manifests and stable fingerprints.

The manifest is deliberately an evidence object, not an execution authority.  It
binds a research run to its inputs and environment while keeping holdout,
source-switch and trading authority fail-closed.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Mapping


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_KEY = re.compile(
    r"(?:api[_-]?key|api[_-]?secret|password|private[_-]?key|credential|access[_-]?token|refresh[_-]?token)",
    re.IGNORECASE,
)


class LineageProtocolError(ValueError):
    """Raised when a lineage record is malformed or crosses an authority boundary."""


def canonical_json(value: Any) -> str:
    """Return deterministic JSON and reject non-finite numeric values."""

    if is_dataclass(value):
        value = asdict(value)
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            default=_json_default,
        )
    except (TypeError, ValueError) as exc:
        raise LineageProtocolError(f"value is not canonically serializable: {exc}") from exc


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def assert_sha256(value: str, label: str = "sha256") -> str:
    text = str(value or "").strip().lower()
    if not _SHA256.fullmatch(text):
        raise LineageProtocolError(f"{label} must be a lowercase SHA-256 hex digest")
    return text


def assert_no_secret_fields(value: Any, *, path: str = "metadata") -> None:
    """Reject credential-like metadata before it can enter a research receipt."""

    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            if _FORBIDDEN_KEY.search(key_text):
                raise LineageProtocolError(f"secret-like field is forbidden: {path}.{key_text}")
            assert_no_secret_fields(child, path=f"{path}.{key_text}")
    elif isinstance(value, (tuple, list)):
        for index, child in enumerate(value):
            assert_no_secret_fields(child, path=f"{path}[{index}]")


@dataclass(frozen=True, slots=True)
class ResearchLineageManifest:
    """Stable identity for one offline research run.

    ``generated_at`` is intentionally absent: timestamps belong in an external
    receipt and must not change the manifest fingerprint.
    """

    run_id: str
    provider: str
    symbol_universe_sha256: str
    interval_set: tuple[str, ...]
    dataset_fingerprints: tuple[tuple[str, str], ...]
    feature_config_sha256: str
    strategy_config_sha256: str
    environment: Mapping[str, Any]
    seed: int
    parent_run_id: str | None = None
    holdout_accessed: bool = False
    source_switch_authorized: bool = False
    trade_plan_authorized: bool = False
    schema_version: str = "0.1.0"

    def __post_init__(self) -> None:
        if not str(self.run_id).strip() or not str(self.provider).strip():
            raise LineageProtocolError("run_id and provider are required")
        if not self.interval_set or any(not str(item).strip() for item in self.interval_set):
            raise LineageProtocolError("interval_set must contain non-empty values")
        if len(set(self.interval_set)) != len(self.interval_set):
            raise LineageProtocolError("interval_set must not contain duplicates")
        assert_sha256(self.symbol_universe_sha256, "symbol_universe_sha256")
        assert_sha256(self.feature_config_sha256, "feature_config_sha256")
        assert_sha256(self.strategy_config_sha256, "strategy_config_sha256")
        if not isinstance(self.seed, int) or isinstance(self.seed, bool):
            raise LineageProtocolError("seed must be an integer")
        if not self.dataset_fingerprints:
            raise LineageProtocolError("at least one dataset fingerprint is required")
        roles: set[str] = set()
        for role, digest in self.dataset_fingerprints:
            if not str(role).strip() or role in roles:
                raise LineageProtocolError("dataset roles must be non-empty and unique")
            roles.add(role)
            assert_sha256(digest, f"dataset_fingerprints[{role}]")
        assert_no_secret_fields(self.environment)
        if self.holdout_accessed:
            raise LineageProtocolError("research lineage must not access the frozen holdout")
        if self.source_switch_authorized:
            raise LineageProtocolError("source switching requires a separate authority")
        if self.trade_plan_authorized:
            raise LineageProtocolError("lineage has zero trade-plan authority")

    @property
    def fingerprint(self) -> str:
        return sha256_json(self.evidence())

    def evidence(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "runId": self.run_id,
            "parentRunId": self.parent_run_id,
            "provider": self.provider,
            "symbolUniverseSha256": self.symbol_universe_sha256.lower(),
            "intervalSet": list(self.interval_set),
            "datasetFingerprints": {
                role: digest.lower() for role, digest in sorted(self.dataset_fingerprints)
            },
            "featureConfigSha256": self.feature_config_sha256.lower(),
            "strategyConfigSha256": self.strategy_config_sha256.lower(),
            "environment": dict(self.environment),
            "seed": self.seed,
            "holdoutAccessed": False,
            "sourceSwitchAuthorized": False,
            "tradePlanAuthorized": False,
        }


def build_lineage_manifest(
    *,
    run_id: str,
    provider: str,
    symbol_universe: Any,
    intervals: tuple[str, ...] | list[str],
    datasets: Mapping[str, Any],
    feature_config: Any,
    strategy_config: Any,
    environment: Mapping[str, Any],
    seed: int,
    parent_run_id: str | None = None,
) -> ResearchLineageManifest:
    """Build a manifest from canonical research inputs, never from credentials."""

    assert_no_secret_fields({"environment": environment, "strategy_config": strategy_config})
    dataset_fingerprints = tuple(
        sorted((str(role), sha256_json(value)) for role, value in datasets.items())
    )
    return ResearchLineageManifest(
        run_id=str(run_id),
        parent_run_id=str(parent_run_id) if parent_run_id is not None else None,
        provider=str(provider),
        symbol_universe_sha256=sha256_json(symbol_universe),
        interval_set=tuple(str(item) for item in intervals),
        dataset_fingerprints=dataset_fingerprints,
        feature_config_sha256=sha256_json(feature_config),
        strategy_config_sha256=sha256_json(strategy_config),
        environment=dict(environment),
        seed=seed,
    )


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite float")
    raise TypeError(f"unsupported value type: {type(value).__name__}")
