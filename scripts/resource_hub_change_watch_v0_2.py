#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Mapping

from crypto_autopilot.toolkit.resource_hub_supply_chain import build_candidate_registry


_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _validate_policy(policy: Mapping[str, object]) -> None:
    if policy.get("schema") != "qookey-resource-hub-supply-chain-policy-v0.2":
        raise ValueError("Resource Hub change watch requires policy v0.2")
    if policy.get("status") != "AUTHORIZED_READ_ONLY_CHANGE_WATCH_ON_MAIN_MERGE":
        raise ValueError("Resource Hub v0.2 policy is not authorized for scheduled read-only watch")
    schedule = policy.get("schedule")
    safety = policy.get("safety")
    if not isinstance(schedule, Mapping) or schedule.get("cron_utc") != "13 1 * * *":
        raise ValueError("Resource Hub v0.2 schedule drifted")
    if not isinstance(safety, Mapping):
        raise ValueError("Resource Hub v0.2 safety object is required")
    allowed_true = {
        "schedule_authorized",
        "public_catalog_read_authorized",
    }
    for key, value in safety.items():
        if key in allowed_true:
            if value is not True:
                raise ValueError(f"{key} must remain true")
        elif key == "workflow_dispatch_only":
            if value is not False:
                raise ValueError("workflow_dispatch_only must remain false")
        elif value is not False:
            raise ValueError(f"unsafe Resource Hub v0.2 authority enabled: {key}")


def _previous_state(policy: Mapping[str, object], path: Path | None) -> dict[str, object]:
    if path is not None and path.is_file():
        payload = _load(path)
        if payload.get("schema") != "qookey-resource-hub-change-watch-state-v0.2":
            raise ValueError("previous Resource Hub state schema is unsupported")
        return payload
    baseline = policy.get("baseline")
    if not isinstance(baseline, Mapping):
        raise ValueError("Resource Hub v0.2 baseline is required")
    source_commit = str(baseline.get("source_commit") or "")
    if not _SHA_RE.fullmatch(source_commit):
        raise ValueError("Resource Hub baseline source commit is invalid")
    return {
        "schema": "qookey-resource-hub-change-watch-state-v0.2",
        "source": {"current_commit": source_commit},
        "evaluation": {"candidate_fingerprint": None, "candidate_count": None},
    }


def _candidate_fingerprint(registry: Mapping[str, object]) -> str:
    payload = {
        "policy": registry.get("policy"),
        "candidates": registry.get("candidates"),
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def build_change_watch(
    *,
    catalog: Mapping[str, object],
    policy: Mapping[str, object],
    source_commit: str,
    previous_state: Mapping[str, object],
) -> tuple[dict[str, object], dict[str, object] | None]:
    _validate_policy(policy)
    if not _SHA_RE.fullmatch(source_commit):
        raise ValueError("source_commit must be a lowercase 40-character Git SHA")

    previous_source = previous_state.get("source")
    if not isinstance(previous_source, Mapping):
        raise ValueError("previous Resource Hub state source is missing")
    previous_commit = str(previous_source.get("current_commit") or "")
    if not _SHA_RE.fullmatch(previous_commit):
        raise ValueError("previous Resource Hub state commit is invalid")

    previous_evaluation = previous_state.get("evaluation")
    if not isinstance(previous_evaluation, Mapping):
        previous_evaluation = {}
    previous_fingerprint = previous_evaluation.get("candidate_fingerprint")
    previous_count = previous_evaluation.get("candidate_count")

    source_changed = source_commit != previous_commit
    registry: dict[str, object] | None = None
    fingerprint = previous_fingerprint if isinstance(previous_fingerprint, str) else None
    candidate_count = previous_count if isinstance(previous_count, int) else None
    candidate_changed: bool | None = False if not source_changed else None

    if source_changed:
        registry = build_candidate_registry(catalog, policy, source_commit=source_commit)
        fingerprint = _candidate_fingerprint(registry)
        candidate_count = int(registry.get("candidate_count") or 0)
        if isinstance(previous_fingerprint, str):
            candidate_changed = fingerprint != previous_fingerprint

    if not source_changed:
        status = "NO_CHANGE"
        decision = "NO_CHANGE"
    elif candidate_changed is False:
        status = "SOURCE_CHANGED_CANDIDATES_UNCHANGED"
        decision = "NO_CHANGE"
    else:
        status = "SOURCE_CHANGED_REVIEW_REQUIRED"
        decision = "REVIEW_REQUIRED"

    safety = policy["safety"]
    assert isinstance(safety, Mapping)
    state = {
        "schema": "qookey-resource-hub-change-watch-state-v0.2",
        "status": status,
        "decision": decision,
        "source": {
            "repository": "qookey109-pixel/ai-resource-hub",
            "catalog_path": "data/resources.json",
            "previous_commit": previous_commit,
            "current_commit": source_commit,
            "source_changed": source_changed,
            "catalog_schema_version": catalog.get("schema_version"),
            "catalog_updated_at": catalog.get("updated_at"),
        },
        "evaluation": {
            "candidate_evaluation_performed": source_changed,
            "candidate_count": candidate_count,
            "candidate_fingerprint": fingerprint,
            "candidate_changed_vs_previous": candidate_changed,
            "automatic_pull_request_created": False,
        },
        "authority": {
            "scheduled_public_catalog_read_authorized": True,
            "automatic_install_authorized": False,
            "automatic_execution_authorized": False,
            "automatic_adapter_creation_authorized": False,
            "automatic_pull_request_authorized": False,
            "provider_access_authorized": False,
            "r2_access_authorized": False,
            "holdout_access_authorized": False,
            "source_switch_authorized": False,
            "automatic_strategy_mutation_authorized": False,
            "automatic_model_promotion_authorized": False,
            "formal_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }
    if safety.get("schedule_authorized") is not True:
        raise ValueError("Resource Hub scheduled read authority unexpectedly closed")
    return state, registry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path("config/resource_hub_supply_chain_v0_2.json"),
    )
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--previous-state", type=Path)
    parser.add_argument("--state-output", type=Path, required=True)
    parser.add_argument("--candidates-output", type=Path)
    args = parser.parse_args()

    policy = _load(args.policy)
    catalog = _load(args.catalog)
    previous = _previous_state(policy, args.previous_state)
    state, registry = build_change_watch(
        catalog=catalog,
        policy=policy,
        source_commit=args.source_commit,
        previous_state=previous,
    )

    args.state_output.parent.mkdir(parents=True, exist_ok=True)
    args.state_output.write_text(
        json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if registry is not None and args.candidates_output is not None:
        args.candidates_output.parent.mkdir(parents=True, exist_ok=True)
        args.candidates_output.write_text(
            json.dumps(registry, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    print(json.dumps(state, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
