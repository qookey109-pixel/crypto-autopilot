from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from crypto_autopilot.paper.live_v0_1 import (
    PionexLivePaperFeed,
    live_paper_policy_from_config,
)
from crypto_autopilot.paper.run_claim_v0_1 import (
    live_paper_run_claim_policy_from_config,
)
from crypto_autopilot.paper.run_coordinator_v0_1 import (
    coordinate_live_paper_run_step,
    live_paper_run_coordinator_input_from_dict,
    live_paper_run_coordinator_policy_from_config,
)
from crypto_autopilot.paper.run_store_v0_1 import (
    LocalPaperRunStore,
    R2PaperRunStore,
    paper_run_store_policy_from_config,
)
from crypto_autopilot.storage.r2 import R2Store


@dataclass(slots=True)
class _OperationJournal:
    provider_requests_known: int = 0
    provider_status: str = "KNOWN"
    store_write_attempts: int = 0
    store_objects_created_known: int = 0
    store_objects_replayed_known: int = 0
    store_status: str = "KNOWN"

    def evidence(self) -> dict[str, object]:
        return {
            "provider_requests": {
                "status": self.provider_status,
                "known_performed": self.provider_requests_known,
            },
            "persistence_writes": {
                "status": self.store_status,
                "attempted": self.store_write_attempts,
                "known_created": self.store_objects_created_known,
                "known_replayed": self.store_objects_replayed_known,
            },
        }


class _TrackedFeed:
    def __init__(self, feed: Any, journal: _OperationJournal) -> None:
        self.feed = feed
        self.journal = journal

    def fetch_frame(
        self,
        symbol: str,
        *,
        tick_time_ms: int,
        since_ms: int,
    ):
        try:
            frame = self.feed.fetch_frame(
                symbol,
                tick_time_ms=tick_time_ms,
                since_ms=since_ms,
            )
        except Exception:
            self.journal.provider_status = "UNKNOWN_OR_PARTIAL"
            raise
        self.journal.provider_requests_known += int(frame.provider_request_count)
        return frame


class _TrackedStore:
    def __init__(self, store: Any, journal: _OperationJournal) -> None:
        self.store = store
        self.journal = journal

    def get_json(self, kind: str, object_id: str):
        return self.store.get_json(kind, object_id)

    def put_json(self, kind: str, object_id: str, payload):
        self.journal.store_write_attempts += 1
        try:
            receipt = self.store.put_json(kind, object_id, payload)
        except Exception:
            self.journal.store_status = "UNKNOWN_OR_PARTIAL"
            raise
        if bool(getattr(receipt, "replayed", False)):
            self.journal.store_objects_replayed_known += 1
        else:
            self.journal.store_objects_created_known += 1
        return receipt

    def put_json_if_absent(self, kind: str, object_id: str, payload):
        self.journal.store_write_attempts += 1
        try:
            receipt = self.store.put_json_if_absent(kind, object_id, payload)
        except Exception:
            self.journal.store_status = "UNKNOWN_OR_PARTIAL"
            raise
        if bool(getattr(receipt, "replayed", False)):
            self.journal.store_objects_replayed_known += 1
        else:
            self.journal.store_objects_created_known += 1
        return receipt


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _build_store(
    backend: str,
    *,
    local_root: Path | None,
    store_config: dict[str, object],
):
    policy = paper_run_store_policy_from_config(store_config)
    if backend == "local":
        if not policy.local_json_authorized:
            raise ValueError("local Paper Run Store backend is not authorized")
        if local_root is None:
            raise ValueError("--local-root is required for local persistence")
        return LocalPaperRunStore(local_root.resolve())
    if backend == "r2":
        if not policy.r2_authorized:
            raise ValueError("R2 Paper Run Store backend is not authorized")
        required = {
            "R2_ACCOUNT_ID": os.environ.get("R2_ACCOUNT_ID"),
            "R2_BUCKET": os.environ.get("R2_BUCKET"),
            "R2_ACCESS_KEY_ID": os.environ.get("R2_ACCESS_KEY_ID"),
            "R2_SECRET_ACCESS_KEY": os.environ.get("R2_SECRET_ACCESS_KEY"),
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise ValueError(
                "missing R2 environment variables: " + ",".join(sorted(missing))
            )
        return R2PaperRunStore(
            R2Store(
                account_id=str(required["R2_ACCOUNT_ID"]),
                bucket=str(required["R2_BUCKET"]),
                access_key_id=str(required["R2_ACCESS_KEY_ID"]),
                secret_access_key=str(required["R2_SECRET_ACCESS_KEY"]),
            )
        )
    raise ValueError("Live Paper Run Coordinator requires local or r2 store")


def _failure_report(
    *,
    stage: str,
    error: Exception,
    journal: _OperationJournal,
    claim_required: bool,
) -> dict[str, object]:
    provider_known = journal.provider_status == "KNOWN"
    store_known = journal.store_status == "KNOWN"
    return {
        "schema": "qookey-live-paper-run-coordinator-report-v0.1",
        "state": "REJECT",
        "reason": f"{stage.lower()}_failed",
        "error_stage": stage,
        "error_type": type(error).__name__,
        "provider_requests_performed": (
            journal.provider_requests_known if provider_known else None
        ),
        "provider_requests_status": journal.provider_status,
        "persistent_objects_created": (
            journal.store_objects_created_known if store_known else None
        ),
        "persistent_writes_status": journal.store_status,
        "operation_accounting": journal.evidence(),
        "authority": {
            "public_live_market_data_authorized": True,
            "live_paper_simulation_authorized": True,
            "paper_state_persistence_authorized": True,
            "append_only_run_ledger": True,
            "paper_run_slot_claim_authorized": claim_required,
            "claim_conflict_auto_retry_authorized": False,
            "automatic_schedule_authorized": False,
            "automatic_candidate_generation_authorized": False,
            "scorecard_auto_selection_authorized": False,
            "private_exchange_api_authorized": False,
            "holdout_access_authorized": False,
            "real_money_order_authorized": False,
            "live_real_trading_authorized": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Commit one restartable append-only Live Paper run step using public "
            "Pionex market data. No real exchange order path is present."
        )
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--store-backend",
        choices=("local", "r2"),
        required=True,
    )
    parser.add_argument("--local-root", type=Path)
    parser.add_argument(
        "--coordinator-config",
        type=Path,
        default=Path("config/live_paper_run_coordinator_v0_2.json"),
    )
    parser.add_argument(
        "--claim-config",
        type=Path,
        default=Path("config/live_paper_run_claim_v0_1.json"),
    )
    parser.add_argument(
        "--live-config",
        type=Path,
        default=Path("config/live_paper_simulation_v0_1.json"),
    )
    parser.add_argument(
        "--store-config",
        type=Path,
        default=Path("config/paper_run_store_v0_1.json"),
    )
    args = parser.parse_args()

    journal = _OperationJournal()
    claim_required = False
    stage = "LOAD_POLICY"
    try:
        coordinator_policy = live_paper_run_coordinator_policy_from_config(
            _load_json(args.coordinator_config)
        )
        claim_required = coordinator_policy.run_slot_claim_required
        claim_policy = (
            live_paper_run_claim_policy_from_config(_load_json(args.claim_config))
            if claim_required
            else None
        )
        live_policy = live_paper_policy_from_config(_load_json(args.live_config))

        stage = "BUILD_STORE"
        store = _TrackedStore(
            _build_store(
                args.store_backend,
                local_root=args.local_root,
                store_config=_load_json(args.store_config),
            ),
            journal,
        )

        stage = "LOAD_INPUT"
        (
            run_name,
            tick_time_ms,
            candidate_specs,
            initial_state,
            previous_step_id,
        ) = live_paper_run_coordinator_input_from_dict(_load_json(args.input))

        stage = "LOAD_PREVIOUS_STEP"
        previous_step = None
        if previous_step_id is not None:
            previous_step = store.get_json("live-run-step", previous_step_id)
            if previous_step is None:
                raise ValueError("previous run step not found in store")

        stage = "COORDINATE_RUN_STEP"
        report = coordinate_live_paper_run_step(
            run_name=run_name,
            tick_time_ms=tick_time_ms,
            candidate_specs=candidate_specs,
            feed=_TrackedFeed(PionexLivePaperFeed(policy=live_policy), journal),
            store=store,
            initial_state=initial_state,
            previous_step=previous_step,
            policy=coordinator_policy,
            live_policy=live_policy,
            claim_policy=claim_policy,
        )
        report = dict(report)
        report["operation_accounting"] = journal.evidence()
        code = 0
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as error:
        report = _failure_report(
            stage=stage,
            error=error,
            journal=journal,
            claim_required=claim_required,
        )
        code = 2

    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
