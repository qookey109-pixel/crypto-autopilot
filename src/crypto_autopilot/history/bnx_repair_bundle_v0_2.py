"""Manual-only BNX repair bundle preserving the existing 15m contract and adding 1h v0.2."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from crypto_autopilot.history import bnx_repair as repair_v0_1
from crypto_autopilot.history import bnx_repair_v0_2 as repair_v0_2

CONFIG_SHA = "fa39fbb90659c7bd56f0b66d16e08217df2bfe36eea11ac5679f4f26f77a6d88"
BASE_SHA = repair_v0_1.BASE_SHA
SHARD_INDEX = 3
TARGETS = (repair_v0_1.TARGET, repair_v0_2.TARGET)


class RepairAuthorityError(ValueError):
    pass


def require_clock(now=None):
    now = now or datetime.now(timezone.utc)
    repair_v0_1.require_clock(now)
    repair_v0_2.require_clock(now)


def _root_from_config(config_path: Path) -> Path:
    path = Path(config_path).resolve()
    if path.name != "bnx_archive_repair_bundle_v0_2.json" or path.parent.name != "config":
        raise RepairAuthorityError("BNX_REPAIR_BUNDLE_CONFIG_PATH_MISMATCH")
    return path.parent.parent


def load_contract(config_path, receipt_path, base_bytes, now=None, env=None):
    require_clock(now)
    env = os.environ if env is None else env
    if (
        env.get("GITHUB_REPOSITORY") != "qookey109-pixel/crypto-autopilot"
        or env.get("GITHUB_REF") != "refs/heads/main"
        or env.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
        or env.get("GITHUB_RUN_ATTEMPT") != "1"
    ):
        raise RepairAuthorityError("BNX_REPAIR_BUNDLE_FRESH_MAIN_MANUAL_REQUIRED")
    raw = Path(config_path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != CONFIG_SHA:
        raise RepairAuthorityError("BNX_REPAIR_BUNDLE_CONFIG_BINDING_MISMATCH")
    if hashlib.sha256(base_bytes).hexdigest() != BASE_SHA:
        raise RepairAuthorityError("BNX_REPAIR_BUNDLE_BASE_BINDING_MISMATCH")
    receipt = json.loads(Path(receipt_path).read_bytes())
    if receipt != {'schema': 'bnx-archive-repair-bundle-authority-v0.2', 'status': 'AUTHORIZED_ON_PROTECTED_MAIN_MERGE', 'config': 'config/bnx_archive_repair_bundle_v0_2.json', 'config_sha256': 'fa39fbb90659c7bd56f0b66d16e08217df2bfe36eea11ac5679f4f26f77a6d88', 'shard_index': 3, 'fresh_manual_only': True, 'existing_v0_1_authority_reused': True, 'new_v0_2_authority_bound': True, 'existing_partition_overwrite_authorized': False, 'new_schedule_authorized': False, 'original_authorities_mutated': False}:
        raise RepairAuthorityError("BNX_REPAIR_BUNDLE_RECEIPT_BINDING_MISMATCH")

    root = _root_from_config(Path(config_path))
    bundle = json.loads(raw)
    expected_contracts = [
        {
            "name": "bnx-15m-repair-v0.1",
            "config": "config/bnx_archive_repair_v0_1.json",
            "config_sha256": repair_v0_1.CONFIG_SHA,
            "authority": "research/receipts/2026-09-09-bnx-archive-repair-v0-1-authority.json",
            "target": list(repair_v0_1.TARGET),
        },
        {
            "name": "bnx-1h-repair-v0.2",
            "config": "config/bnx_archive_repair_v0_2.json",
            "config_sha256": repair_v0_2.CONFIG_SHA,
            "authority": "research/receipts/2026-09-12-bnx-archive-repair-v0-2-authority.json",
            "target": list(repair_v0_2.TARGET),
        },
    ]
    if (
        bundle.get("contracts") != expected_contracts
        or bundle.get("shard_index") != SHARD_INDEX
        or bundle.get("repair_receipt_source_rows_from_lineage") is not True
        or bundle.get("existing_partition_overwrite_authorized") is not False
        or bundle.get("new_schedule_authorized") is not False
    ):
        raise RepairAuthorityError("BNX_REPAIR_BUNDLE_SCOPE_MISMATCH")

    v0_1 = repair_v0_1.load_contract(
        root / expected_contracts[0]["config"],
        root / expected_contracts[0]["authority"],
        base_bytes,
        now=now,
        env=env,
    )
    v0_2 = repair_v0_2.load_contract(
        root / expected_contracts[1]["config"],
        root / expected_contracts[1]["authority"],
        base_bytes,
        now=now,
        env=env,
    )
    return {"v0_1": v0_1, "v0_2": v0_2}


def matches(partition):
    identity = (partition.symbol, partition.interval, partition.period)
    return identity in TARGETS


def reconstruct(partition, contract):
    identity = (partition.symbol, partition.interval, partition.period)
    if identity == repair_v0_1.TARGET:
        return repair_v0_1.reconstruct(partition, contract["v0_1"])
    if identity == repair_v0_2.TARGET:
        return repair_v0_2.reconstruct(partition, contract["v0_2"])
    raise RepairAuthorityError("BNX_REPAIR_BUNDLE_TARGET_MISMATCH")
