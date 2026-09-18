from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from crypto_autopilot.paper.live_v0_1 import (
    PionexLivePaperFeed,
    live_paper_policy_from_config,
    live_paper_tick_input_from_dict,
    run_live_paper_tick,
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
    if backend == "none":
        return None
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
        r2 = R2Store(
            account_id=str(required["R2_ACCOUNT_ID"]),
            bucket=str(required["R2_BUCKET"]),
            access_key_id=str(required["R2_ACCESS_KEY_ID"]),
            secret_access_key=str(required["R2_SECRET_ACCESS_KEY"]),
        )
        return R2PaperRunStore(r2)
    raise ValueError(f"unsupported store backend: {backend}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Advance one Pionex-public live-paper tick. Public market data and "
            "paper simulation are allowed; real exchange orders are never sent."
        )
    )
    parser.add_argument("--input", type=Path, required=True)
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
    parser.add_argument(
        "--store-backend",
        choices=("none", "local", "r2"),
        default="none",
    )
    parser.add_argument("--local-root", type=Path)
    arguments = parser.parse_args()

    try:
        live_policy = live_paper_policy_from_config(
            _load_json(arguments.live_config)
        )
        store_config = _load_json(arguments.store_config)
        store = _build_store(
            arguments.store_backend,
            local_root=arguments.local_root,
            store_config=store_config,
        )
        state, tick_time_ms, candidates = live_paper_tick_input_from_dict(
            _load_json(arguments.input)
        )
        report = run_live_paper_tick(
            state=state,
            tick_time_ms=tick_time_ms,
            candidate_specs=candidates,
            feed=PionexLivePaperFeed(policy=live_policy),
            policy=live_policy,
            store=store,
        )
        exit_code = 0
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as error:
        report = {
            "schema": "qookey-live-paper-tick-report-v0.1",
            "state": "REJECT",
            "reason": f"input_policy_or_runtime_invalid:{error}",
            "provider_requests_performed": 0,
            "persistent_state_writes_performed": 0,
            "authority": {
                "public_live_market_data_authorized": True,
                "live_paper_simulation_authorized": True,
                "persistent_paper_state_authorized": True,
                "private_exchange_api_authorized": False,
                "holdout_access_authorized": False,
                "real_money_order_authorized": False,
                "live_real_trading_authorized": False,
            },
        }
        exit_code = 2

    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
