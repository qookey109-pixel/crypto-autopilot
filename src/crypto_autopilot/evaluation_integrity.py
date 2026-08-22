"""Fail-closed evaluation partition evidence for offline research."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .lineage import assert_sha256, canonical_json


class PartitionRole(str, Enum):
    UPDATE = "update"
    VALIDATION = "validation"
    HOLDOUT = "holdout"


class EvaluationIntegrityError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PartitionEvidence:
    name: str
    role: PartitionRole
    dataset_sha256: str
    record_fingerprints: tuple[str, ...]
    source_fingerprints: tuple[str, ...]
    seeds: tuple[int, ...]
    frozen: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise EvaluationIntegrityError("partition name is required")
        assert_sha256(self.dataset_sha256, "dataset_sha256")
        if len(set(self.record_fingerprints)) != len(self.record_fingerprints):
            raise EvaluationIntegrityError("record fingerprints must be unique")
        if len(set(self.source_fingerprints)) != len(self.source_fingerprints):
            raise EvaluationIntegrityError("source fingerprints must be unique")
        if len(set(self.seeds)) != len(self.seeds):
            raise EvaluationIntegrityError("seeds must be unique")
        for label, values in (("record", self.record_fingerprints), ("source", self.source_fingerprints)):
            for value in values:
                assert_sha256(value, f"{label}_fingerprint")
        if self.role is PartitionRole.HOLDOUT and not self.frozen:
            raise EvaluationIntegrityError("holdout partition must be frozen")

    @property
    def record_count(self) -> int:
        return len(self.record_fingerprints)

    def evidence(self) -> dict[str, object]:
        return {
            "name": self.name,
            "role": self.role.value,
            "datasetSha256": self.dataset_sha256.lower(),
            "recordCount": self.record_count,
            "recordFingerprints": list(self.record_fingerprints),
            "sourceFingerprints": list(self.source_fingerprints),
            "seeds": list(self.seeds),
            "frozen": self.frozen,
        }


@dataclass(frozen=True, slots=True)
class EvaluationIntegrityPolicy:
    required_roles: tuple[PartitionRole, ...] = (
        PartitionRole.UPDATE,
        PartitionRole.VALIDATION,
        PartitionRole.HOLDOUT,
    )
    max_record_overlap_fraction: float = 0.0
    max_source_overlap_fraction: float = 0.0
    require_disjoint_seeds: bool = True
    require_distinct_dataset_fingerprints: bool = True

    def __post_init__(self) -> None:
        for label, value in (
            ("max_record_overlap_fraction", self.max_record_overlap_fraction),
            ("max_source_overlap_fraction", self.max_source_overlap_fraction),
        ):
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise EvaluationIntegrityError(f"{label} must be within [0, 1]")


@dataclass(frozen=True, slots=True)
class EvaluationUsage:
    update: tuple[str, ...] = ()
    validation: tuple[str, ...] = ()
    holdout: tuple[str, ...] = ()

    def evidence(self) -> dict[str, list[str]]:
        return {
            "update": list(self.update),
            "validation": list(self.validation),
            "holdout": list(self.holdout),
        }


class PartitionAccessGuard:
    """Expose partition metadata while denying holdout access by default."""

    def __init__(self, partitions: Iterable[PartitionEvidence], *, holdout_authorized: bool = False):
        rows = tuple(partitions)
        self._by_name = {row.name: row for row in rows}
        if len(self._by_name) != len(rows):
            raise EvaluationIntegrityError("partition names must be unique")
        self._holdout_authorized = bool(holdout_authorized)
        self._used: dict[PartitionRole, list[str]] = {role: [] for role in PartitionRole}

    def access(self, name: str, *, stage: PartitionRole) -> PartitionEvidence:
        row = self._by_name.get(str(name))
        if row is None:
            raise KeyError(name)
        if stage is PartitionRole.HOLDOUT and not self._holdout_authorized:
            raise PermissionError("frozen holdout access is not authorized")
        if row.role is not stage:
            raise PermissionError(f"{row.name} role {row.role.value} cannot be used for {stage.value}")
        if row.name not in self._used[stage]:
            self._used[stage].append(row.name)
        return row

    def usage(self) -> EvaluationUsage:
        return EvaluationUsage(
            update=tuple(self._used[PartitionRole.UPDATE]),
            validation=tuple(self._used[PartitionRole.VALIDATION]),
            holdout=tuple(self._used[PartitionRole.HOLDOUT]),
        )


@dataclass(frozen=True, slots=True)
class EvaluationIntegrityResult:
    passed: bool
    failures: tuple[str, ...]
    overlaps: tuple[dict[str, object], ...]
    usage: EvaluationUsage

    def evidence(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "failures": list(self.failures),
            "overlaps": list(self.overlaps),
            "usage": self.usage.evidence(),
        }


def build_partition_evidence(
    *,
    name: str,
    role: PartitionRole,
    record_fingerprints: Iterable[str],
    source_fingerprints: Iterable[str],
    seeds: Iterable[int],
    frozen: bool = False,
) -> PartitionEvidence:
    records = tuple(sorted(set(record_fingerprints)))
    sources = tuple(sorted(set(source_fingerprints)))
    seed_values = tuple(sorted(set(int(seed) for seed in seeds)))
    dataset_payload = {"records": records, "sources": sources, "seeds": seed_values}
    dataset_sha256 = hashlib.sha256(canonical_json(dataset_payload).encode("utf-8")).hexdigest()
    return PartitionEvidence(
        name=str(name),
        role=role,
        dataset_sha256=dataset_sha256,
        record_fingerprints=records,
        source_fingerprints=sources,
        seeds=seed_values,
        frozen=frozen,
    )


def evaluate_partition_integrity(
    partitions: Iterable[PartitionEvidence],
    *,
    usage: EvaluationUsage = EvaluationUsage(),
    policy: EvaluationIntegrityPolicy = EvaluationIntegrityPolicy(),
) -> EvaluationIntegrityResult:
    rows = tuple(partitions)
    failures: list[str] = []
    overlaps: list[dict[str, object]] = []
    by_role = {role: [row for row in rows if row.role is role] for role in PartitionRole}

    for role in policy.required_roles:
        if not by_role[role]:
            failures.append(f"missing-required-role:{role.value}")
    if policy.require_distinct_dataset_fingerprints:
        digests = [row.dataset_sha256 for row in rows]
        if len(digests) != len(set(digests)):
            failures.append("dataset-fingerprint-collision")

    for index, left in enumerate(rows):
        for right in rows[index + 1 :]:
            record_overlap = set(left.record_fingerprints) & set(right.record_fingerprints)
            source_overlap = set(left.source_fingerprints) & set(right.source_fingerprints)
            seed_overlap = set(left.seeds) & set(right.seeds)
            record_fraction = len(record_overlap) / max(1, min(left.record_count, right.record_count))
            source_fraction = len(source_overlap) / max(
                1, min(len(left.source_fingerprints), len(right.source_fingerprints))
            )
            if record_overlap or source_overlap or seed_overlap:
                overlaps.append(
                    {
                        "left": left.name,
                        "right": right.name,
                        "recordOverlap": sorted(record_overlap),
                        "sourceOverlap": sorted(source_overlap),
                        "seedOverlap": sorted(seed_overlap),
                        "recordOverlapFraction": record_fraction,
                        "sourceOverlapFraction": source_fraction,
                    }
                )
            if record_fraction > policy.max_record_overlap_fraction:
                failures.append(f"record-overlap:{left.name}:{right.name}")
            if source_fraction > policy.max_source_overlap_fraction:
                failures.append(f"source-overlap:{left.name}:{right.name}")
            if policy.require_disjoint_seeds and seed_overlap:
                failures.append(f"seed-overlap:{left.name}:{right.name}")
    holdouts = by_role[PartitionRole.HOLDOUT]
    if holdouts and any(not row.frozen for row in holdouts):
        failures.append("holdout-not-frozen")
    if usage.holdout:
        failures.append("holdout-usage-recorded-before-separate-authority")
    return EvaluationIntegrityResult(
        passed=not failures,
        failures=tuple(sorted(set(failures))),
        overlaps=tuple(overlaps),
        usage=usage,
    )
