from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping
from pathlib import Path

from crypto_autopilot.paper.run_recovery_v0_1 import (
    live_paper_run_recovery_policy_from_config,
    reconcile_live_paper_run,
)
from crypto_autopilot.paper.run_store_v0_1 import (
    LocalPaperRunStore,
    PaperRunStoreReceipt,
    R2PaperRunStore,
    paper_run_store_policy_from_config,
    run_store_receipt_evidence,
)
from crypto_autopilot.storage.r2 import R2Store


class _RecoveryWrites:
    """Keep acknowledged seal receipts and the identity of an uncertain write."""

    def __init__(self, store: LocalPaperRunStore | R2PaperRunStore) -> None:
        self.store = store
        self.receipts: list[PaperRunStoreReceipt] = []
        self.unconfirmed: str | None = None

    def get_json(self, kind: str, object_id: str) -> dict[str, object] | None:
        return self.store.get_json(kind, object_id)

    def list_json_ids(self, kind: str) -> tuple[str, ...]:
        return self.store.list_json_ids(kind)

    def put_json(
        self, kind: str, object_id: str, payload: Mapping[str, object],
    ) -> PaperRunStoreReceipt:
        if kind != "live-run-result":
            raise ValueError("recovery may write only a missing result seal")
        self.unconfirmed = object_id
        receipt = self.store.put_json(kind, object_id, payload)
        if (
            not isinstance(receipt, PaperRunStoreReceipt) or receipt.kind != kind
            or receipt.object_id != object_id or type(receipt.replayed) is not bool
        ):
            raise ValueError("recovery store returned an invalid seal receipt")
        self.receipts.append(receipt)
        self.unconfirmed = None
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
            raise ValueError("--local-root is required for local recovery")
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
    raise ValueError("unsupported recovery store backend")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit one persistent Live Paper run and optionally repair only "
            "missing immutable request-result seals. No provider call is made."
        )
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--store-backend",
        choices=("local", "r2"),
        required=True,
    )
    parser.add_argument("--local-root", type=Path)
    parser.add_argument(
        "--repair-missing-result-seals",
        action="store_true",
    )
    parser.add_argument(
        "--recovery-config",
        type=Path,
        default=Path("config/live_paper_run_recovery_v0_1.json"),
    )
    parser.add_argument(
        "--store-config",
        type=Path,
        default=Path("config/paper_run_store_v0_1.json"),
    )
    args = parser.parse_args()
    writes: _RecoveryWrites | None = None

    try:
        recovery_policy = live_paper_run_recovery_policy_from_config(
            _load_json(args.recovery_config)
        )
        store = _build_store(
            args.store_backend,
            local_root=args.local_root,
            store_config=_load_json(args.store_config),
        )
        writes = _RecoveryWrites(store)
        report = reconcile_live_paper_run(
            run_id=args.run_id,
            store=writes,
            repair_missing_result_seals=args.repair_missing_result_seals,
            policy=recovery_policy,
        )
        code = 0 if report["state"] != "REVIEW_REQUIRED" else 3
    except Exception as error:
        # The SDK can lose a response after committing a PUT. Keep enough
        # evidence for the operator even when reconciliation cannot finish.
        report = {
            "schema": "qookey-live-paper-run-recovery-report-v0.1",
            "state": "REJECT",
            "reason": f"input_policy_store_or_evidence_invalid:{error}",
            "provider_requests_performed": 0,
            "live_market_data_requests_performed": 0,
            "account_state_mutations_performed": 0,
            "step_state_tick_rewrites_performed": 0,
            "result_seal_writes_performed": 0,
            "authority": {
                "audit_and_result_seal_repair_only": True,
                "provider_access_authorized": False,
                "live_market_data_access_authorized": False,
                "account_state_mutation_authorized": False,
                "step_state_tick_rewrite_authorized": False,
                "automatic_schedule_authorized": False,
                "private_exchange_api_authorized": False,
                "holdout_access_authorized": False,
                "real_money_order_authorized": False,
                "live_real_trading_authorized": False
            }
        }
        code = 2
        if writes is not None and (writes.receipts or writes.unconfirmed is not None):
            known_created = sum(not item.replayed for item in writes.receipts)
            report.update({
                "state": "REVIEW_REQUIRED",
                "reason": f"result_seal_repair_incomplete:{type(error).__name__}",
                "run_id": args.run_id,
                "result_seal_writes_performed": known_created if writes.unconfirmed is None else None,
                "known_result_seal_writes": known_created,
                "unconfirmed_result_seal_request_id": writes.unconfirmed,
                "storage_receipts": [run_store_receipt_evidence(item) for item in writes.receipts],
            })
            code = 3
        elif not isinstance(error, (OSError, ValueError, RuntimeError)):
            report.update({
                "state": "REVIEW_REQUIRED",
                "reason": f"reconciliation_failed:{type(error).__name__}",
            })
            code = 3

    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
