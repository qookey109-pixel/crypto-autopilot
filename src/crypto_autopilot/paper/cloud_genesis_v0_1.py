"""Cash-only initialization compatible with the existing paper checkpoint core.

GENESIS identifiers explicitly mean no predecessor batch/advance exists. This
adapter creates no order, fill, profit or strategy validation evidence.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

from crypto_autopilot.paper.account_v0_1 import (
    PaperAccountPolicy, materialize_paper_account,
)
from crypto_autopilot.paper.checkpoint_v0_1 import (
    paper_loop_checkpoint_report_id_from_mapping,
)
from crypto_autopilot.paper.live_v0_1 import initialize_live_paper_state


def _sha(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def cash_genesis_checkpoint() -> dict[str, object]:
    account_input = {
        "schema": "qookey-paper-account-state-input-v0.1",
        "initial_equity_usd": 10000.0, "records": [], "marks": [],
    }
    policy = PaperAccountPolicy()
    snapshot = materialize_paper_account(
        initial_equity_usd=10000.0, records=(), marks=(), policy=policy,
    )
    account = json.loads(json.dumps(asdict(snapshot)))
    genesis_id = "paper-cash-genesis-v0-1-" + _sha(account_input)
    report = {
        "schema": "qookey-paper-loop-checkpoint-report-v0.1",
        "state": "PAPER_LOOP_CHECKPOINT_READY",
        "checkpoint_id": "PENDING_RECOMPUTATION",
        "advance_id": genesis_id,
        "batch_id": "GENESIS_NO_BATCH",
        "previous_snapshot_id": "GENESIS_NO_PREVIOUS_SNAPSHOT",
        "next_snapshot_id": snapshot.snapshot_id,
        "next_account_input_sha256": _sha(account_input),
        "portfolio_exposures_sha256": _sha({"exposures": []}),
        "account_policy_sha256": _sha(asdict(policy)),
        "account_policy": asdict(policy),
        "next_cycle_allowed": True,
        "next_account_input": account_input,
        "account_snapshot": account,
        "portfolio_existing_exposures": [],
        "provider_requests_performed": 0,
        "persistent_state_writes_performed": 0,
        "origin": {
            "schema": "qookey-paper-cash-genesis-v0.1",
            "genesis_id": genesis_id, "previous_batch_exists": False,
            "previous_advance_exists": False, "trade_count": 0,
            "contract": "config/cloud_paper_loop_v0_1.json",
        },
        "authority": {
            "portable_handoff_only": True,
            **{key: False for key in (
                "provider_requests_performed", "r2_accessed", "holdout_accessed",
                "persistent_state_write_authorized", "automatic_cycle_authorized",
                "automatic_submission_authorized", "scheduled_execution_authorized",
                "short_paper_execution_authorized", "formal_trade_plan_authorized",
                "real_money_order_authorized", "live_trading_authorized",
            )},
        },
        "limitations": ["Cash genesis only; GENESIS markers are not trade evidence."],
    }
    report["checkpoint_id"] = paper_loop_checkpoint_report_id_from_mapping(report)
    return report


def initialize_cloud_paper_state() -> dict[str, object]:
    return initialize_live_paper_state(checkpoint_report=cash_genesis_checkpoint())
