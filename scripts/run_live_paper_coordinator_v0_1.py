from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from crypto_autopilot.paper.live_v0_1 import (
    PionexLivePaperFeed,
    live_paper_policy_from_config,
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
        default=Path("config/live_paper_run_coordinator_v0_1.json"),
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

    try:
        coordinator_policy = live_paper_run_coordinator_policy_from_config(
            _load_json(args.coordinator_config)
        )
        live_policy = live_paper_policy_from_config(_load_json(args.live_config))
        store = _build_store(
            args.store_backend,
            local_root=args.local_root,
            store_config=_load_json(args.store_config),
        )
        (
            run_name,
            tick_time_ms,
            candidate_specs,
            initial_state,
            previous_step_id,
        ) = live_paper_run_coordinator_input_from_dict(_load_json(args.input))

        previous_step = None
        if previous_step_id is not None:
            previous_step = store.get_json("live-run-step", previous_step_id)
            if previous_step is None:
                raise ValueError(
                    f"previous run step not found in store: {previous_step_id}"
                )

        report = coordinate_live_paper_run_step(
            run_name=run_name,
            tick_time_ms=tick_time_ms,
            candidate_specs=candidate_specs,
            feed=PionexLivePaperFeed(policy=live_policy),
            store=store,
            initial_state=initial_state,
            previous_step=previous_step,
            policy=coordinator_policy,
            live_policy=live_policy,
        )
        code = 0
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as error:
        report = {
            "schema": "qookey-live-paper-run-coordinator-report-v0.1",
            "state": "REJECT",
            "reason": f"input_policy_store_or_runtime_invalid:{error}",
            "provider_requests_performed": 0,
            "persistent_objects_created": 0,
            "authority": {
                "public_live_market_data_authorized": True,
                "live_paper_simulation_authorized": True,
                "paper_state_persistence_authorized": True,
                "append_only_run_ledger": True,
                "automatic_schedule_authorized": False,
                "automatic_candidate_generation_authorized": False,
                "scorecard_auto_selection_authorized": False,
                "private_exchange_api_authorized": False,
                "holdout_access_authorized": False,
                "real_money_order_authorized": False,
                "live_real_trading_authorized": False
            }
        }
        code = 2

    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
