#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from crypto_autopilot.training.effective_signal_audit_v0_1 import (
    EffectiveSignalAuditError,
    run_effective_signal_audit,
)

ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = ROOT / "scripts/train_binance_detailed_history_models.py"
VALIDATED_RUNNER = ROOT / "scripts/train_binance_detailed_history_models_v0_2.py"
DEFAULT_TRAINING_CONFIG = ROOT / "config/binance_usdm_detailed_history_v0_1_2.json"
DEFAULT_TRAINING_AUTHORITY = (
    ROOT
    / "research/receipts/2026-08-29-binance-usdm-crypto-core-100-v0-1-2-authority.json"
)
DEFAULT_AUDIT_CONFIG = ROOT / "config/core100_effective_signal_audit_v0_1.json"
DEFAULT_AUDIT_AUTHORITY = (
    ROOT
    / "research/receipts/2026-09-15-core100-effective-signal-audit-v0-1-authority.json"
)


def _load_script(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


base = _load_script("core100_signal_audit_base_runner", BASE_RUNNER)
validated = _load_script("core100_signal_audit_validated_runner", VALIDATED_RUNNER)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise EffectiveSignalAuditError(f"{path} must contain a JSON object")
    return payload


def _validate_audit_authority(
    policy: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> None:
    if policy.get("schema") != "core100-effective-signal-audit-policy-v0.1":
        raise EffectiveSignalAuditError("unexpected effective signal audit policy schema")
    if receipt.get("schema") != "core100-effective-signal-audit-authority-v0.1":
        raise EffectiveSignalAuditError("unexpected effective signal audit authority schema")
    expected_status = "AUTHORIZED_ONE_SHOT_AFTER_REVIEWED_MAIN_MERGE"
    if policy.get("status") != expected_status or receipt.get("status") != expected_status:
        raise EffectiveSignalAuditError("effective signal audit is not authorized")
    user_authorization = receipt.get("user_authorization")
    if not isinstance(user_authorization, Mapping):
        raise EffectiveSignalAuditError("audit user authorization is missing")
    if user_authorization.get("effective_signal_audit_authorized") is not True:
        raise EffectiveSignalAuditError("effective signal audit user authorization is false")
    if user_authorization.get("merge_authority_granted_by_this_receipt") is not False:
        raise EffectiveSignalAuditError("audit receipt cannot grant merge authority")
    execution = receipt.get("execution")
    if not isinstance(execution, Mapping):
        raise EffectiveSignalAuditError("audit execution contract is missing")
    if execution.get("one_shot") is not True:
        raise EffectiveSignalAuditError("audit execution must remain one-shot")
    if execution.get("no_schedule") is not True or execution.get("no_manual_dispatch") is not True:
        raise EffectiveSignalAuditError("audit execution cannot gain recurring/manual triggers")
    boundary = receipt.get("safety_boundary")
    if not isinstance(boundary, Mapping) or not boundary:
        raise EffectiveSignalAuditError("audit safety boundary is missing")
    if any(value is not False for value in boundary.values()):
        raise EffectiveSignalAuditError("audit safety boundary must remain all false")
    if receipt.get("prepared_from_main") != policy.get("lineage", {}).get("prepared_from_main"):
        raise EffectiveSignalAuditError("audit prepared-main lineage mismatch")
    if execution.get("exact_dataset_fingerprint") != policy.get("lineage", {}).get(
        "expected_dataset_fingerprint"
    ):
        raise EffectiveSignalAuditError("audit dataset fingerprint authority mismatch")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the one-shot aggregate-only Core100 effective signal audit."
    )
    parser.add_argument("--training-config", type=Path, default=DEFAULT_TRAINING_CONFIG)
    parser.add_argument("--training-authority", type=Path, default=DEFAULT_TRAINING_AUTHORITY)
    parser.add_argument("--audit-config", type=Path, default=DEFAULT_AUDIT_CONFIG)
    parser.add_argument("--audit-authority", type=Path, default=DEFAULT_AUDIT_AUTHORITY)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--now-utc")
    args = parser.parse_args()

    output = base.require_ephemeral_output(args.output)
    training_config, _training_authority, _config_bytes = base.load_authority_pair(
        args.training_config, args.training_authority
    )
    policy = _load_json(args.audit_config)
    receipt = _load_json(args.audit_authority)
    _validate_audit_authority(policy, receipt)

    observed = (
        datetime.fromisoformat(args.now_utc.replace("Z", "+00:00"))
        if args.now_utc
        else datetime.now(UTC)
    )
    if observed.tzinfo is None:
        raise EffectiveSignalAuditError("--now-utc must be timezone-aware")
    generated_at = observed.astimezone(UTC).isoformat().replace("+00:00", "Z")

    store = base.create_store()
    catalog, state, object_records, fingerprint = base.load_dataset_index(store, training_config)

    lineage = policy["lineage"]
    expected_partitions = int(lineage["expected_partition_objects"])
    expected_rows = int(lineage["expected_source_rows"])
    actual_rows = sum(int(record["source_rows"]) for record in object_records)
    if len(object_records) != expected_partitions:
        raise EffectiveSignalAuditError("partition count does not match frozen audit lineage")
    if actual_rows != expected_rows:
        raise EffectiveSignalAuditError("source row count does not match frozen audit lineage")
    if fingerprint != str(lineage["expected_dataset_fingerprint"]):
        raise EffectiveSignalAuditError("dataset fingerprint does not match frozen audit lineage")
    if int(state["total_partition_objects"]) != expected_partitions:
        raise EffectiveSignalAuditError("backfill-state partition count does not match audit lineage")

    examples = validated.build_examples_from_r2(
        store,
        catalog=catalog,
        object_records=object_records,
        config=training_config,
    )
    report = run_effective_signal_audit(
        examples,
        training_config=training_config["training"],
        dataset_fingerprint=fingerprint,
        expected_dataset_fingerprint=str(lineage["expected_dataset_fingerprint"]),
        generated_at_utc=generated_at,
        policy=policy,
    )
    report["lineage"] = {
        "partition_objects": len(object_records),
        "source_rows": actual_rows,
        "backfill_status": state["status"],
        "source_training_run_id": lineage["source_training_run_id"],
        "threshold_replay_run_id": lineage["threshold_replay_run_id"],
        "prepared_from_main": lineage["prepared_from_main"],
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(base.canonical_json_bytes(report))
    print(
        json.dumps(
            {
                "status": report["status"],
                "stage": report["stage"],
                "dataset_fingerprint": report["dataset_fingerprint"],
                "example_count": report["example_count"],
                "symbol_count": report["symbol_count"],
                "global_positive_rate": report["global_label_balance"]["positive_rate"],
                "same_symbol_overlap_fraction": report["dependence_diagnostics"][
                    "same_symbol_overlap_fraction"
                ],
                "holdout_accessed": report["authority"]["holdout_accessed"],
                "r2_writes_performed": report["authority"]["r2_writes_performed"],
                "training_performed": report["authority"]["training_performed"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
