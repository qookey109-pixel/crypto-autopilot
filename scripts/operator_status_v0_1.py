from __future__ import annotations

import argparse
import json
from pathlib import Path

from crypto_autopilot.operator_messaging_v0_1 import parse_operator_command_request
from crypto_autopilot.operator_status_resolver_v0_1 import resolve_operator_status


DEFAULT_STATUS_FILE = Path("research/status/current-operations-v0-3.json")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve a read-only operator command from the offline current-operations "
            "snapshot. Performs no network, provider or trading action."
        )
    )
    parser.add_argument("command", help="help, status, or paper_status")
    parser.add_argument(
        "--status-file",
        type=Path,
        default=DEFAULT_STATUS_FILE,
        help="Offline qookey-current-operations-v0.3 JSON snapshot",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format",
    )
    args = parser.parse_args()

    try:
        payload = json.loads(args.status_file.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("status file must contain a JSON object")

        request = parse_operator_command_request(args.command)
        response = resolve_operator_status(
            command_request=request,
            current_operations=payload,
        )
    except (OSError, json.JSONDecodeError, ValueError) as error:
        failure = {
            "schema": "qookey-operator-status-cli-result-v0.1",
            "status": "REJECTED",
            "reason": str(error),
            "read_only": True,
            "execution_authorized": False,
            "network_access_performed": False,
            "state_mutation_performed": False,
        }
        print(json.dumps(failure, sort_keys=True, separators=(",", ":")))
        return 2

    if args.format == "json":
        print(json.dumps(response, sort_keys=True, separators=(",", ":")))
    else:
        print(response["text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
