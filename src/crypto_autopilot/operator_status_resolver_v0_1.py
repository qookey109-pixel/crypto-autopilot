from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from crypto_autopilot.operator_messaging_v0_1 import COMMAND_SCHEMA

CURRENT_OPERATIONS_SCHEMA = "qookey-current-operations-v0.3"
RESPONSE_SCHEMA = "qookey-operator-status-response-v0.1"
SUPPORTED_COMMANDS = frozenset({"HELP", "STATUS", "PAPER_STATUS"})


@dataclass(frozen=True, slots=True)
class OperatorStatusResolverPolicy:
    offline_status_resolution_authorized: bool = True
    network_access_authorized: bool = False
    secret_access_authorized: bool = False
    command_execution_authorized: bool = False
    state_mutation_authorized: bool = False
    strategy_router_integration_authorized: bool = False
    portfolio_admission_authorized: bool = False
    real_money_order_authorized: bool = False
    live_real_trading_authorized: bool = False

    def __post_init__(self) -> None:
        values = (
            self.offline_status_resolution_authorized,
            self.network_access_authorized,
            self.secret_access_authorized,
            self.command_execution_authorized,
            self.state_mutation_authorized,
            self.strategy_router_integration_authorized,
            self.portfolio_admission_authorized,
            self.real_money_order_authorized,
            self.live_real_trading_authorized,
        )
        if any(not isinstance(value, bool) for value in values):
            raise ValueError("operator status resolver policy flags must be booleans")
        if not self.offline_status_resolution_authorized:
            raise ValueError("V0.1 requires offline status resolution authority")
        if any(values[1:]):
            raise ValueError(
                "Operator Status Resolver V0.1 cannot grant network, secret, "
                "execution, mutation, routing, portfolio or trading authority"
            )


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _validate_command_request(command_request: Mapping[str, object]) -> str:
    if command_request.get("schema") != COMMAND_SCHEMA:
        raise ValueError("unsupported operator command-request schema")
    if command_request.get("recognized") is not True:
        raise ValueError("operator command request must already be recognized")
    if command_request.get("read_only") is not True:
        raise ValueError("operator command request must be read-only")
    if command_request.get("execution_authorized") is not False:
        raise ValueError("operator command request cannot authorize execution")

    command = command_request.get("command")
    if not isinstance(command, str) or command not in SUPPORTED_COMMANDS:
        raise ValueError("unsupported operator status command")
    return command


def _validate_current_operations(
    current_operations: Mapping[str, object],
) -> tuple[Mapping[str, object], Mapping[str, object], Mapping[str, object]]:
    if current_operations.get("schema") != CURRENT_OPERATIONS_SCHEMA:
        raise ValueError("unsupported current-operations schema")
    if current_operations.get("repository_authority") != "RESOLVE_MAIN_LIVE_AT_READ_TIME":
        raise ValueError("current-operations repository authority mismatch")

    core100 = _require_mapping(current_operations.get("core100"), "core100")
    gates = _require_mapping(current_operations.get("gates"), "gates")
    live_paper = _require_mapping(current_operations.get("live_paper"), "live_paper")
    return core100, gates, live_paper


def _authority() -> dict[str, bool]:
    return {
        "offline_status_only": True,
        "network_access_authorized": False,
        "secret_access_authorized": False,
        "command_execution_authorized": False,
        "state_mutation_authorized": False,
        "strategy_router_integration_authorized": False,
        "portfolio_admission_authorized": False,
        "real_money_order_authorized": False,
        "live_real_trading_authorized": False,
    }


def resolve_operator_status(
    *,
    command_request: Mapping[str, object],
    current_operations: Mapping[str, object],
    policy: OperatorStatusResolverPolicy = OperatorStatusResolverPolicy(),
) -> dict[str, object]:
    """Resolve an already-parsed read-only command from an offline status snapshot."""

    if not policy.offline_status_resolution_authorized:
        raise ValueError("offline operator status resolution is not authorized")

    command = _validate_command_request(command_request)
    core100, gates, live_paper = _validate_current_operations(current_operations)

    updated_date = current_operations.get("updated_date")
    if not isinstance(updated_date, str) or not updated_date:
        raise ValueError("current-operations updated_date is required")

    common = {
        "schema": RESPONSE_SCHEMA,
        "command": command,
        "snapshot_schema": CURRENT_OPERATIONS_SCHEMA,
        "snapshot_updated_date": updated_date,
        "snapshot_is_latest_main_claim": False,
        "repository_authority": "RESOLVE_MAIN_LIVE_AT_READ_TIME",
        "read_only": True,
        "execution_authorized": False,
        "authority": _authority(),
    }

    if command == "HELP":
        return {
            **common,
            "text": (
                "Available read-only commands: help, status, paper_status. "
                "No command executes trades or mutates project state."
            ),
            "data": {
                "commands": ["help", "status", "paper_status"],
                "write_commands_available": False,
            },
        }

    model_quality = _require_mapping(
        core100.get("model_quality_gate"),
        "core100.model_quality_gate",
    )

    if command == "STATUS":
        data = {
            "mode": current_operations.get("mode"),
            "core100_history": core100.get("history_status"),
            "model_quality": model_quality.get("status"),
            "strategy_validation": gates.get("strategy_validation"),
            "holdout": gates.get("holdout"),
            "automatic_model_promotion": gates.get("automatic_model_promotion"),
            "source_switch_authorized": gates.get("source_switch_authorized"),
            "real_money_orders": gates.get("real_money_orders"),
            "live_trading": gates.get("live_trading"),
            "live_paper_simulation": gates.get("live_paper_simulation"),
        }
        return {
            **common,
            "text": (
                f"Mode: {data['mode']} | Core100 history: {data['core100_history']} | "
                f"model quality: {data['model_quality']} | "
                f"strategy validation: {data['strategy_validation']} | "
                f"holdout: {data['holdout']} | live paper: "
                f"{data['live_paper_simulation']} | real-money orders: "
                f"{data['real_money_orders']} | real live trading: {data['live_trading']}."
            ),
            "data": data,
        }

    data = {
        "status": live_paper.get("status"),
        "public_live_market_data": live_paper.get("public_live_market_data"),
        "live_paper_simulation": live_paper.get("live_paper_simulation"),
        "paper_state_persistence": live_paper.get("paper_state_persistence"),
        "private_exchange_api": live_paper.get("private_exchange_api"),
        "replacement_holdout_access": live_paper.get("replacement_holdout_access"),
        "real_money_orders": live_paper.get("real_money_orders"),
        "live_real_trading": live_paper.get("live_real_trading"),
    }
    return {
        **common,
        "text": (
            f"Paper status: {data['status']} | public live market data: "
            f"{data['public_live_market_data']} | live-paper simulation: "
            f"{data['live_paper_simulation']} | paper persistence: "
            f"{data['paper_state_persistence']} | private exchange API: "
            f"{data['private_exchange_api']} | real-money orders: "
            f"{data['real_money_orders']} | real live trading: "
            f"{data['live_real_trading']}."
        ),
        "data": data,
    }
