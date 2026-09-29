"""Secret-free, zero-network Cloud Paper usage credential-name readiness."""
from __future__ import annotations

import json
import os


def classify_configuration(account_present: bool, token_present: bool) -> dict[str, object]:
    """Check configuration presence only; never inspect or report credential values."""
    if account_present and token_present:
        state = "READY"
        reason = "CONFIGURATION_PRESENT"
    elif not account_present and not token_present:
        state = "BLOCKED_MISSING_ACCOUNT_ID_AND_TOKEN"
        reason = "ACCOUNT_ID_VARIABLE_AND_TOKEN_SECRET_MISSING"
    elif not account_present:
        state = "BLOCKED_MISSING_ACCOUNT_ID"
        reason = "ACCOUNT_ID_VARIABLE_MISSING"
    else:
        state = "BLOCKED_MISSING_READ_ONLY_TOKEN"
        reason = "READ_ONLY_TOKEN_SECRET_MISSING"
    return {
        "state": state,
        "reason_code": reason,
        "account_id_variable_present": account_present,
        "read_only_token_secret_present": token_present,
        "api_permission_state": "NOT_CHECKED_NO_NETWORK",
        "usage_evidence_state": "NOT_CHECKED_BY_READINESS",
        "budget_activation_state": "NOT_AUTHORIZED_BY_READINESS",
        "cloudflare_requests_performed": 0,
        "secret_values_printed": False,
        "one_time_authority_consumed": False,
    }


def main() -> None:
    print(json.dumps(classify_configuration(
        os.environ.get("CF_ACCOUNT_ID_PRESENT") == "true",
        os.environ.get("CF_READONLY_TOKEN_PRESENT") == "true",
    ), sort_keys=True))


if __name__ == "__main__":
    main()
