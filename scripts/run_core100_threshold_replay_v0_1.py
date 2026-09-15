#!/usr/bin/env python3
"""Reproduce Core100 folds and emit threshold diagnostics without publishing training artifacts."""
from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRAINING_ENTRY = ROOT / "scripts/train_binance_detailed_history_models_v0_2.py"
DEFAULT_CONFIG = ROOT / "config/binance_usdm_detailed_history_v0_1_2.json"
DEFAULT_AUTHORITY = (
    ROOT
    / "research/receipts/2026-08-29-binance-usdm-crypto-core-100-v0-1-2-authority.json"
)
DEFAULT_SCOPE = (
    ROOT
    / "research/receipts/2026-09-15-core100-threshold-sweep-one-shot-authority.json"
)


def _load_training_entry():
    spec = importlib.util.spec_from_file_location("core100_threshold_training_entry", TRAINING_ENTRY)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay the completed Core100 training dataset for diagnostic threshold sweeps only."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument("--scope", type=Path, default=DEFAULT_SCOPE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    scope = json.loads(args.scope.read_text(encoding="utf-8"))
    if scope.get("schema") != "qookey-core100-threshold-sweep-one-shot-authority-v0.1":
        raise ValueError("unexpected threshold replay authority schema")
    if scope.get("status") != "AUTHORIZED_READ_ONLY_ONE_SHOT":
        raise ValueError("threshold replay authority is not active")
    execution = scope["execution"]
    assert execution["one_shot"] is True
    assert execution["r2_reads_authorized"] is True
    assert execution["r2_writes_authorized"] is False
    assert execution["provider_requests_authorized"] is False
    assert execution["holdout_access_authorized"] is False
    assert execution["training_publication_authorized"] is False
    assert execution["automatic_model_promotion_authorized"] is False
    assert execution["live_trading_authorized"] is False

    training_entry = _load_training_entry()
    runner = training_entry.runner
    config, _authority, _config_bytes = runner.load_authority_pair(args.config, args.authority)
    observed = datetime.now(UTC)
    runner.require_execution_window(config, observed_at=observed, operation="training")

    store = runner.create_store()
    catalog, state, object_records, fingerprint = runner.load_dataset_index(store, config)
    if fingerprint != scope["source_dataset_fingerprint"]:
        raise RuntimeError("threshold replay dataset fingerprint drift")
    if int(state["total_partition_objects"]) != int(scope["source_partition_objects"]):
        raise RuntimeError("threshold replay partition count drift")
    if int(state["total_rows"]) != int(scope["source_dataset_rows"]):
        raise RuntimeError("threshold replay row count drift")

    examples = training_entry.build_examples_from_r2(
        store,
        catalog=catalog,
        object_records=object_records,
        config=config,
    )
    generated_at = observed.isoformat().replace("+00:00", "Z")
    model, metrics = training_entry.run_intraday_training_with_threshold_diagnostics(
        examples,
        config=config,
        dataset_fingerprint=fingerprint,
        generated_at_utc=generated_at,
    )

    gate = metrics["model_quality_gate"]
    if gate.get("status") != scope["expected_model_quality_gate"]:
        raise RuntimeError("threshold replay quality gate drift")
    if int(metrics["example_count"]) != int(scope["source_example_count"]):
        raise RuntimeError("threshold replay example count drift")
    boundary = model["authority"]
    for key in (
        "pionex_native_relabel_authorized",
        "source_switch_authorized",
        "automatic_model_promotion_authorized",
        "formal_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if boundary.get(key) is not False:
            raise RuntimeError(f"threshold replay authority regression: {key}")

    report = {
        "schema": "qookey-core100-threshold-sweep-replay-v0.1",
        "status": "PASS",
        "observed_at_utc": generated_at,
        "source_training_run_id": scope["source_training_run_id"],
        "source_dataset_fingerprint": fingerprint,
        "dataset_partition_objects": state["total_partition_objects"],
        "dataset_rows": state["total_rows"],
        "example_count": metrics["example_count"],
        "symbol_count": metrics["symbol_count"],
        "model_quality_gate": gate,
        "threshold_diagnostics_v0_1": metrics["threshold_diagnostics_v0_1"],
        "diagnostic_only": True,
        "r2_writes_performed": False,
        "provider_requests_performed": 0,
        "holdout_accessed": False,
        "training_publication_performed": False,
        "automatic_model_promotion_authorized": False,
        "formal_trade_plan_authorized": False,
        "real_money_order_authorized": False,
        "live_trading_authorized": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
