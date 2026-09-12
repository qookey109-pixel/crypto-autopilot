#!/usr/bin/env python3
"""Fresh-manual BNX repair entry point using the v0.3 three-interval repair bundle."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

from crypto_autopilot.history import bnx_repair_bundle_v0_3 as repair_bundle

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_binance_detailed_history.py"
spec = importlib.util.spec_from_file_location("bnx_repair_detailed_history_runner_v0_3", RUNNER)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)

# Keep the existing writer authoritative for serialization, R2 headroom,
# immutable writes, readback verification, shard receipts, and state ordering.
runner.bnx_repair = repair_bundle
_original_canonical_json_bytes = runner.canonical_json_bytes


def canonical_json_bytes(value):
    """Correct repair receipt source-row fields from pinned lineage before serialization."""
    if not isinstance(value, dict) or value.get("schema") != "binance-usdm-detailed-history-shard-receipt-v0.1":
        return _original_canonical_json_bytes(value)
    normalized = copy.deepcopy(value)
    repaired = 0
    for record in normalized.get("objects", []):
        lineage = record.get("repair_lineage") if isinstance(record, dict) else None
        if not isinstance(lineage, dict):
            continue
        if lineage.get("schema") not in {
            "bnx-archive-repair-lineage-v0.1",
            "bnx-archive-repair-lineage-v0.2",
            "bnx-archive-repair-lineage-v0.3",
        }:
            raise repair_bundle.RepairAuthorityError("BNX_REPAIR_BUNDLE_V0_3_UNKNOWN_LINEAGE")
        original_rows = lineage.get("original_monthly_rows")
        original_audit = lineage.get("original_monthly_audit_ok")
        if type(original_rows) is not int or original_rows <= 0 or original_audit is not False:
            raise repair_bundle.RepairAuthorityError("BNX_REPAIR_BUNDLE_V0_3_LINEAGE_FIELDS_INVALID")
        record["source_archive_rows"] = original_rows
        record["source_archive_audit_ok"] = original_audit
        repaired += 1
    if repaired > 3:
        raise repair_bundle.RepairAuthorityError("BNX_REPAIR_BUNDLE_V0_3_REPAIR_COUNT_EXCEEDED")
    return _original_canonical_json_bytes(normalized)


runner.canonical_json_bytes = canonical_json_bytes


def main():
    return runner.main()


if __name__ == "__main__":
    raise SystemExit(main())
