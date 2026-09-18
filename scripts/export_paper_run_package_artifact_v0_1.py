from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.paper.artifact_export_v0_1 import (
    artifact_export_policy_from_config,
    export_paper_loop_run_package_artifact,
)


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify one Paper Loop Run Package and export canonical secondary "
            "evidence files suitable for GitHub Actions upload-artifact."
        )
    )
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/paper_run_package_artifact_export_v0_1.json"),
    )
    args = parser.parse_args()

    try:
        policy = artifact_export_policy_from_config(_load_json(args.config))
        receipt = export_paper_loop_run_package_artifact(
            package=_load_json(args.package),
            output_dir=args.output_dir,
            policy=policy,
        )
        code = 0
    except (OSError, json.JSONDecodeError, ValueError) as error:
        receipt = {
            "schema": "qookey-paper-run-package-artifact-export-receipt-v0.1",
            "state": "REJECT",
            "reason": f"package_or_policy_invalid:{error}",
            "provider_requests_performed": 0,
            "r2_accessed": False,
            "holdout_accessed": False,
            "account_state_mutations_performed": 0,
            "executions_performed": 0,
            "authority": {
                "secondary_audit_export_only": True,
                "github_artifact_upload_allowed": True,
                "artifact_is_execution_authority": False,
                "provider_access_authorized": False,
                "r2_access_authorized": False,
                "holdout_access_authorized": False,
                "account_state_mutation_authorized": False,
                "automatic_execution_authorized": False,
                "real_money_order_authorized": False,
                "live_real_trading_authorized": False,
            },
        }
        code = 2

    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
