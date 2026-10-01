"""Inactive assembly of the existing Cloud Paper production adapters.

The factory performs no provider/store/query operation. Calling it is not
activation authority: a future reviewed workflow must enforce the merged
execution receipt and supply independently verified account-wide snapshots.
"""
from __future__ import annotations

import os
from collections.abc import Callable, Mapping

from crypto_autopilot.paper.cloud_budget_ledger_v0_1 import (
    CloudflareD1QueryClient,
    D1CloudBudgetLedger,
    D1SharedRowsBudgetGuard,
    D1UsageGuard,
    D1UsageSnapshot,
)
from crypto_autopilot.paper.cloud_budget_v0_1 import (
    BudgetBlocked,
    CloudBudgetGuard,
    R2UsageSnapshot,
)
from crypto_autopilot.paper.cloud_candidate_adapter_v0_1 import validate_strategy_registry
from crypto_autopilot.paper.cloud_composition_v0_1 import CloudPaperNoTradeComposition
from crypto_autopilot.paper.cloud_pionex_client_v0_1 import CloudPaperPionexPublicClient
from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Store
from crypto_autopilot.paper.live_v0_1 import LivePaperPolicy
from crypto_autopilot.paper.run_store_v0_1 import R2PaperRunStore

CLOUD_PAPER_PREFIX = "paper-run-store/cloud-loop-v0.1"


def build_runtime_composition(
    *, r2_snapshot: R2UsageSnapshot, d1_snapshot: D1UsageSnapshot,
    strategy_registry: Mapping[str, object],
    allowed_base_assets: frozenset[str],
    clock_ms: Callable[[], int],
    construction_enabled: bool = False,
) -> CloudPaperNoTradeComposition | None:
    """Construct guarded adapters only after checking the supplied evidence.

    Defaults off before credentials or clients are touched. No usage snapshot
    timestamp is refreshed here. Both snapshots remain exactly as supplied.
    The returned composition still defaults to activation_enabled=False.
    """
    if type(construction_enabled) is not bool:
        raise ValueError("construction_enabled must be boolean")
    if not construction_enabled:
        return None
    if not isinstance(r2_snapshot, R2UsageSnapshot) or not isinstance(
        d1_snapshot, D1UsageSnapshot,
    ):
        raise ValueError("typed R2 and D1 evidence is required")
    if (
        not isinstance(allowed_base_assets, frozenset)
        or not allowed_base_assets
        or any(not isinstance(asset, str) or not asset for asset in allowed_base_assets)
    ):
        raise ValueError("a governed base-asset allowlist is required")
    validate_strategy_registry(strategy_registry)
    r2_guard = CloudBudgetGuard(snapshot=r2_snapshot, clock_ms=clock_ms)
    d1_guard = D1UsageGuard(snapshot=d1_snapshot, clock_ms=clock_ms)

    def check_freshness() -> None:
        if r2_guard.storage_capacity_state() == "HARD_STOP":
            raise BudgetBlocked("BLOCKED_BUDGET_STORAGE_HARD_STOP")
        d1_guard.validate_evidence()

    # Stop before credential reads and SDK/client construction on bad evidence.
    check_freshness()
    r2 = BudgetedR2Store.from_credentials(
        account_id=os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""),
        bucket=os.environ.get("R2_BUCKET_NAME", ""),
        access_key_id=os.environ.get("R2_ACCESS_KEY_ID", ""),
        secret_access_key=os.environ.get("R2_SECRET_ACCESS_KEY", ""),
        budget_guard=r2_guard,
        freshness_check=check_freshness,
    )
    d1 = CloudflareD1QueryClient.from_environment(
        usage_guard=d1_guard, shared_rows_guard=D1SharedRowsBudgetGuard(),
    )
    return CloudPaperNoTradeComposition(
        client=CloudPaperPionexPublicClient(before_send=check_freshness),
        store=R2PaperRunStore(r2, prefix=CLOUD_PAPER_PREFIX),
        strategy_registry=strategy_registry,
        allowed_base_assets=allowed_base_assets,
        paper_policy=LivePaperPolicy(),
        budget_guard=r2_guard,
        before_external=check_freshness,
        completion_clock_ms=clock_ms,
        reservation_ledger=D1CloudBudgetLedger(d1),
        d1_usage_guard=d1_guard,
    )
