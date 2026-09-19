from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

NOTIFICATION_SCHEMA: Final[str] = "qookey-operator-notification-v0.1"
COMMAND_SCHEMA: Final[str] = "qookey-operator-command-request-v0.1"
ALLOWED_SEVERITIES: Final[frozenset[str]] = frozenset({"INFO", "WARNING", "ERROR"})
READ_ONLY_COMMANDS: Final[dict[str, str]] = {
    "help": "HELP",
    "status": "STATUS",
    "paper_status": "PAPER_STATUS",
}


@dataclass(frozen=True, slots=True)
class OperatorMessagingPolicy:
    notifications_authorized: bool = True
    read_only_command_requests_authorized: bool = True
    write_command_requests_authorized: bool = False
    automatic_command_execution_authorized: bool = False
    network_delivery_authorized: bool = False
    telegram_bot_runtime_authorized: bool = False
    telegram_user_session_authorized: bool = False
    secret_access_authorized: bool = False
    strategy_router_integration_authorized: bool = False
    portfolio_admission_authorized: bool = False
    real_money_order_authorized: bool = False
    live_real_trading_authorized: bool = False

    def __post_init__(self) -> None:
        values = (
            self.notifications_authorized,
            self.read_only_command_requests_authorized,
            self.write_command_requests_authorized,
            self.automatic_command_execution_authorized,
            self.network_delivery_authorized,
            self.telegram_bot_runtime_authorized,
            self.telegram_user_session_authorized,
            self.secret_access_authorized,
            self.strategy_router_integration_authorized,
            self.portfolio_admission_authorized,
            self.real_money_order_authorized,
            self.live_real_trading_authorized,
        )
        if any(not isinstance(value, bool) for value in values):
            raise ValueError("operator messaging policy flags must be booleans")
        if not self.notifications_authorized:
            raise ValueError("V0.1 requires notification construction authority")
        if not self.read_only_command_requests_authorized:
            raise ValueError("V0.1 requires read-only command-request authority")
        if any(values[2:]):
            raise ValueError(
                "Operator Messaging V0.1 cannot grant write-command, automatic "
                "execution, network, secret, routing, portfolio or trading authority"
            )


def _required_text(value: object, label: str, *, max_length: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    clean = value.strip()
    if not clean:
        raise ValueError(f"{label} is required")
    if len(clean) > max_length:
        raise ValueError(f"{label} exceeds {max_length} characters")
    return clean


def _timestamp_ms(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("created_at_ms must be a non-negative integer")
    return value


def _safe_metadata(metadata: Mapping[str, object] | None) -> dict[str, object]:
    if metadata is None:
        return {}
    if not isinstance(metadata, Mapping):
        raise ValueError("metadata must be a mapping")

    result: dict[str, object] = {}
    for raw_key, value in metadata.items():
        key = _required_text(raw_key, "metadata key", max_length=64)
        lowered = key.lower()
        if any(
            marker in lowered
            for marker in ("token", "secret", "password", "api_key", "api-key", "session")
        ):
            raise ValueError("metadata keys cannot contain secret-bearing fields")
        if value is None or isinstance(value, (str, int, float, bool)):
            result[key] = value
            continue
        raise ValueError("metadata values must be scalar JSON values")
    return result


def build_operator_notification(
    *,
    source: str,
    topic: str,
    title: str,
    body: str,
    severity: str,
    created_at_ms: int,
    dedupe_key: str | None = None,
    metadata: Mapping[str, object] | None = None,
    policy: OperatorMessagingPolicy = OperatorMessagingPolicy(),
) -> dict[str, object]:
    """Build a provider-neutral notification envelope without performing I/O."""

    if not policy.notifications_authorized:
        raise ValueError("operator notification construction is not authorized")

    clean_severity = _required_text(severity, "severity", max_length=16).upper()
    if clean_severity not in ALLOWED_SEVERITIES:
        raise ValueError("unsupported notification severity")

    envelope = {
        "schema": NOTIFICATION_SCHEMA,
        "source": _required_text(source, "source", max_length=96),
        "topic": _required_text(topic, "topic", max_length=96),
        "title": _required_text(title, "title", max_length=160),
        "body": _required_text(body, "body", max_length=4000),
        "severity": clean_severity,
        "created_at_ms": _timestamp_ms(created_at_ms),
        "dedupe_key": (
            _required_text(dedupe_key, "dedupe_key", max_length=160)
            if dedupe_key is not None
            else None
        ),
        "metadata": _safe_metadata(metadata),
        "delivery": {
            "provider": None,
            "destination": None,
            "network_delivery_authorized": False,
            "delivered": False,
        },
        "authority": {
            "notification_only": True,
            "write_command_requests_authorized": False,
            "automatic_command_execution_authorized": False,
            "secret_access_authorized": False,
            "strategy_router_integration_authorized": False,
            "portfolio_admission_authorized": False,
            "real_money_order_authorized": False,
            "live_real_trading_authorized": False,
        },
    }
    return envelope


def parse_operator_command_request(
    text: str,
    *,
    policy: OperatorMessagingPolicy = OperatorMessagingPolicy(),
) -> dict[str, object]:
    """Parse exact read-only operator commands without executing them."""

    if not policy.read_only_command_requests_authorized:
        raise ValueError("read-only operator command requests are not authorized")

    clean = _required_text(text, "command text", max_length=128).lower()
    if clean.startswith("/"):
        clean = clean[1:]
    normalized = clean.replace("-", "_")

    command = READ_ONLY_COMMANDS.get(normalized)
    if command is None:
        return {
            "schema": COMMAND_SCHEMA,
            "recognized": False,
            "command": None,
            "read_only": True,
            "execution_authorized": False,
            "reason": "UNKNOWN_OR_NON_EXACT_COMMAND",
        }

    return {
        "schema": COMMAND_SCHEMA,
        "recognized": True,
        "command": command,
        "read_only": True,
        "execution_authorized": False,
        "reason": "READ_ONLY_REQUEST_REQUIRES_SEPARATE_STATUS_RESOLVER",
    }


def operator_messaging_policy_from_config(
    payload: Mapping[str, object],
) -> OperatorMessagingPolicy:
    if payload.get("schema") != "qookey-operator-messaging-policy-v0.1":
        raise ValueError("unsupported operator messaging config")
    commands = payload.get("read_only_commands")
    if not isinstance(commands, list) or tuple(commands) != tuple(READ_ONLY_COMMANDS):
        raise ValueError("operator read-only command registry mismatch")

    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("operator messaging policy is required")

    keys = (
        "notifications_authorized",
        "read_only_command_requests_authorized",
        "write_command_requests_authorized",
        "automatic_command_execution_authorized",
        "network_delivery_authorized",
        "telegram_bot_runtime_authorized",
        "telegram_user_session_authorized",
        "secret_access_authorized",
        "strategy_router_integration_authorized",
        "portfolio_admission_authorized",
        "real_money_order_authorized",
        "live_real_trading_authorized",
    )
    values: dict[str, bool] = {}
    for key in keys:
        value = policy.get(key)
        if not isinstance(value, bool):
            raise ValueError(f"policy.{key} must be a JSON boolean")
        values[key] = value

    return OperatorMessagingPolicy(**values)
