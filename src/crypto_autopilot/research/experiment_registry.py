"""Immutable local experiment registry for strategy research evidence."""

from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

from crypto_autopilot.lineage import assert_no_secret_fields, assert_sha256, canonical_json, sha256_json


class ExperimentRegistryError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ExperimentComparisonKey:
    provider: str
    symbol_universe_sha256: str
    interval_set: tuple[str, ...]
    feature_config_sha256: str
    evaluation_fingerprint: str
    primary_metric: str
    direction: str = "higher"

    def __post_init__(self) -> None:
        if not self.provider.strip() or not self.primary_metric.strip():
            raise ExperimentRegistryError("provider and primary_metric are required")
        if self.direction not in {"higher", "lower"}:
            raise ExperimentRegistryError("direction must be higher or lower")
        if not self.interval_set or len(set(self.interval_set)) != len(self.interval_set):
            raise ExperimentRegistryError("interval_set must be non-empty and unique")
        assert_sha256(self.symbol_universe_sha256, "symbol_universe_sha256")
        assert_sha256(self.feature_config_sha256, "feature_config_sha256")
        assert_sha256(self.evaluation_fingerprint, "evaluation_fingerprint")

    @property
    def fingerprint(self) -> str:
        return sha256_json(asdict(self))


@dataclass(frozen=True, slots=True)
class ExperimentCost:
    wall_clock_seconds: float = 0.0
    decisions: int = 0
    r2_bytes_read: int = 0
    r2_bytes_written: int = 0

    def __post_init__(self) -> None:
        if not math.isfinite(self.wall_clock_seconds) or self.wall_clock_seconds < 0:
            raise ExperimentRegistryError("wall_clock_seconds must be finite and >= 0")
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in (self.decisions, self.r2_bytes_read, self.r2_bytes_written)
        ):
            raise ExperimentRegistryError("cost counters must be non-negative integers")


@dataclass(frozen=True, slots=True)
class ExperimentRecord:
    experiment_id: str
    run_id: str
    comparison: ExperimentComparisonKey
    strategy_config_sha256: str
    lineage_fingerprint: str
    candidate_score: float
    baseline_score: float
    outcome: str
    cost: ExperimentCost = ExperimentCost()
    metrics: Mapping[str, Any] = field(default_factory=dict)
    artifact_refs: tuple[str, ...] = ()
    holdout_accessed: bool = False
    promotion_authority: int = 0
    trade_plan_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.experiment_id.strip() or not self.run_id.strip():
            raise ExperimentRegistryError("experiment_id and run_id are required")
        if self.outcome not in {"completed", "rejected", "failed"}:
            raise ExperimentRegistryError("unsupported experiment outcome")
        for label, value in (
            ("strategy_config_sha256", self.strategy_config_sha256),
            ("lineage_fingerprint", self.lineage_fingerprint),
        ):
            assert_sha256(value, label)
        if not math.isfinite(self.candidate_score) or not math.isfinite(self.baseline_score):
            raise ExperimentRegistryError("scores must be finite")
        if self.holdout_accessed:
            raise ExperimentRegistryError("experiment registry cannot authorize holdout access")
        if int(self.promotion_authority) != 0:
            raise ExperimentRegistryError("experiment registry has zero promotion authority")
        if self.trade_plan_authorized:
            raise ExperimentRegistryError("experiment registry has zero trade-plan authority")
        assert_no_secret_fields(self.metrics or {})
        if any(not str(ref).strip() for ref in self.artifact_refs):
            raise ExperimentRegistryError("artifact references must be non-empty")

    @property
    def improvement(self) -> float:
        delta = self.candidate_score - self.baseline_score
        return delta if self.comparison.direction == "higher" else -delta

    @property
    def fingerprint(self) -> str:
        return sha256_json(self.evidence())

    def evidence(self) -> dict[str, Any]:
        return {
            "experimentId": self.experiment_id,
            "runId": self.run_id,
            "comparison": asdict(self.comparison),
            "strategyConfigSha256": self.strategy_config_sha256.lower(),
            "lineageFingerprint": self.lineage_fingerprint.lower(),
            "candidateScore": self.candidate_score,
            "baselineScore": self.baseline_score,
            "improvement": self.improvement,
            "outcome": self.outcome,
            "cost": asdict(self.cost),
            "metrics": dict(self.metrics or {}),
            "artifactRefs": list(self.artifact_refs),
            "holdoutAccessed": False,
            "promotionAuthority": 0,
            "tradePlanAuthorized": False,
        }

    @classmethod
    def from_evidence(cls, payload: Mapping[str, Any]) -> "ExperimentRecord":
        comparison = dict(payload["comparison"])
        comparison["interval_set"] = tuple(comparison.get("interval_set", comparison.get("intervalSet", ())))
        if "symbol_universe_sha256" not in comparison:
            comparison["symbol_universe_sha256"] = comparison.pop("symbolUniverseSha256")
        if "feature_config_sha256" not in comparison:
            comparison["feature_config_sha256"] = comparison.pop("featureConfigSha256")
        if "evaluation_fingerprint" not in comparison:
            comparison["evaluation_fingerprint"] = comparison.pop("evaluationFingerprint")
        return cls(
            experiment_id=str(payload["experimentId"]),
            run_id=str(payload["runId"]),
            comparison=ExperimentComparisonKey(**comparison),
            strategy_config_sha256=str(payload["strategyConfigSha256"]),
            lineage_fingerprint=str(payload["lineageFingerprint"]),
            candidate_score=float(payload["candidateScore"]),
            baseline_score=float(payload["baselineScore"]),
            outcome=str(payload["outcome"]),
            cost=ExperimentCost(**dict(payload.get("cost") or {})),
            metrics=dict(payload.get("metrics") or {}),
            artifact_refs=tuple(str(item) for item in payload.get("artifactRefs", ())),
        )


@dataclass(frozen=True, slots=True)
class ExperimentComparison:
    comparable: bool
    reason: str | None
    winner_experiment_id: str | None
    score_delta: float | None


class JsonExperimentRegistry:
    """Small atomic JSON reference registry; production storage remains Host-owned."""

    schema_version = "0.1.0"

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self._read()
        else:
            self._write({"schemaVersion": self.schema_version, "experiments": []})

    def register(self, record: ExperimentRecord) -> ExperimentRecord:
        payload = self._read()
        rows = [ExperimentRecord.from_evidence(item) for item in payload["experiments"]]
        for existing in rows:
            if existing.experiment_id == record.experiment_id:
                if existing.fingerprint != record.fingerprint:
                    raise ExperimentRegistryError("immutable experiment id cannot be rewritten")
                return existing
            if existing.run_id == record.run_id and existing.fingerprint != record.fingerprint:
                raise ExperimentRegistryError("run_id already points to a different experiment")
        rows.append(record)
        rows.sort(key=lambda item: item.experiment_id)
        self._write({"schemaVersion": self.schema_version, "experiments": [row.evidence() for row in rows]})
        return record

    def get(self, experiment_id: str) -> ExperimentRecord | None:
        for item in self._read()["experiments"]:
            if item.get("experimentId") == str(experiment_id):
                return ExperimentRecord.from_evidence(item)
        return None

    def list(self) -> tuple[ExperimentRecord, ...]:
        return tuple(ExperimentRecord.from_evidence(item) for item in self._read()["experiments"])

    def compare(self, left_id: str, right_id: str) -> ExperimentComparison:
        left = self.get(left_id)
        right = self.get(right_id)
        if left is None or right is None:
            raise KeyError("both experiment ids must exist")
        if left.comparison.fingerprint != right.comparison.fingerprint:
            return ExperimentComparison(False, "comparison-key-mismatch", None, None)
        direction = left.comparison.direction
        left_better = left.candidate_score >= right.candidate_score if direction == "higher" else left.candidate_score <= right.candidate_score
        winner = left if left_better else right
        loser = right if left_better else left
        return ExperimentComparison(True, None, winner.experiment_id, winner.candidate_score - loser.candidate_score)

    def _read(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ExperimentRegistryError(f"invalid registry JSON: {exc}") from exc
        if payload.get("schemaVersion") != self.schema_version or not isinstance(payload.get("experiments"), list):
            raise ExperimentRegistryError("unsupported experiment registry schema")
        return payload

    def _write(self, payload: Mapping[str, Any]) -> None:
        encoded = canonical_json(payload) + "\n"
        fd, temporary = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def build_experiment_registry_entry(
    *,
    comparison_key: str,
    dataset_sha256: str,
    config_sha256: str,
    trainer: dict[str, str],
    environment: dict[str, str],
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    """Build a content-addressed registry entry without any write side effect.

    Rejected or weak experiments remain recordable as evidence. The registry
    never contains a promotion or deployment capability.
    """

    if not comparison_key or comparison_key.strip() != comparison_key:
        raise ValueError("comparison_key must be a non-empty trimmed string")
    if not trainer.get("name") or not trainer.get("version"):
        raise ValueError("trainer name and version are required")
    if not environment:
        raise ValueError("environment fingerprint inputs are required")
    assert_no_secret_fields({"trainer": trainer, "environment": environment, "evaluation": evaluation})
    identity = {
        "schema": "crypto-autopilot-experiment-registry-v0.1",
        "comparison_key": comparison_key,
        "dataset_sha256": assert_sha256(dataset_sha256, "dataset_sha256"),
        "config_sha256": assert_sha256(config_sha256, "config_sha256"),
        "trainer": dict(sorted(trainer.items())),
        "environment": dict(sorted(environment.items())),
        "evaluation": evaluation,
    }
    experiment_id = sha256_json(identity)
    environment_sha256 = sha256_json(identity["environment"])
    lineage_sha256 = sha256_json(identity)
    return {
        **identity,
        "experiment_id": experiment_id,
        "environment_sha256": environment_sha256,
        "lineage_sha256": lineage_sha256,
        "status": "RECORDED",
        "retention": "IMMUTABLE_RESEARCH_EVIDENCE",
        "challenger_only": True,
        "promotion_eligible": False,
        "deployment_authorized": False,
        "trading_authorized": False,
        "rejected_runs_retained": True,
    }


def validate_experiment_registry_entry(entry: dict[str, Any]) -> None:
    """Fail closed on fields that make an experiment comparable and safe."""

    if entry.get("schema") != "crypto-autopilot-experiment-registry-v0.1":
        raise ValueError("experiment registry schema mismatch")
    assert_sha256(str(entry.get("dataset_sha256", "")), "dataset_sha256")
    assert_sha256(str(entry.get("config_sha256", "")), "config_sha256")
    for key in ("challenger_only", "promotion_eligible", "deployment_authorized", "trading_authorized"):
        expected = True if key == "challenger_only" else False
        if entry.get(key) is not expected:
            raise ValueError(f"experiment registry safety field {key} is unsafe")
    expected = build_experiment_registry_entry(
        comparison_key=str(entry.get("comparison_key", "")),
        dataset_sha256=str(entry["dataset_sha256"]),
        config_sha256=str(entry["config_sha256"]),
        trainer=dict(entry.get("trainer", {})),
        environment=dict(entry.get("environment", {})),
        evaluation=dict(entry.get("evaluation", {})),
    )
    if entry.get("experiment_id") != expected["experiment_id"]:
        raise ValueError("experiment registry experiment_id mismatch")
    if entry.get("environment_sha256") != expected["environment_sha256"]:
        raise ValueError("experiment registry environment fingerprint mismatch")
    if entry.get("lineage_sha256") != expected["lineage_sha256"]:
        raise ValueError("experiment registry lineage fingerprint mismatch")
