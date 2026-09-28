"""Inactive production composition for the governed empty-registry path.

The module wires existing Pionex market analysis and Cloud Paper persistence but
starts no client, workflow, provider request, or store operation by itself. Its
runtime switch defaults off. A non-empty production registry is rejected until
a separately reviewed candidate builder and strategy authority exist.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol

from crypto_autopilot.paper.cloud_budget_v0_1 import (
    CloudBudgetGuard,
    R2UsageSnapshot,
)
from crypto_autopilot.paper.cloud_loop_v0_1 import (
    CompleteTapePionexFeed,
    run_cloud_step,
    slot_id,
)
from crypto_autopilot.paper.cloud_market_v0_1 import (
    PublicMarketClient,
    analyze_capture,
    capture_market,
)
from crypto_autopilot.paper.live_v0_1 import LivePaperPolicy
from crypto_autopilot.paper.run_coordinator_v0_1 import PaperRunStoreLike


class CloudPaperCompositionBlocked(RuntimeError):
    """Stable reason for a composition that lacks production authority."""


class BudgetSlotReservationLedger(Protocol):
    """Atomic shared ledger for one slot before any provider or R2 access."""

    def reserve_slot(
        self, *, slot_id: str, run_id: str, now_ms: int,
        snapshot: R2UsageSnapshot,
    ) -> None:
        """Reserve the bounded slot envelope or fail closed."""


class D1UsageBudgetGate(Protocol):
    """Account-wide D1 usage guard required before the atomic slot reservation."""

    def validate_evidence(self) -> None:
        """Check fresh evidence before the atomic slot reservation."""


@dataclass(frozen=True, slots=True)
class CloudPaperNoTradeComposition:
    """Compose Pionex scan, opportunity analysis, and a fail-closed paper step.

    The caller supplies an R2-backed store bound to the same reservation guard,
    a fresh-budget callback, and the existing versioned policy.
    Tests may inject deterministic fakes; this class contains no network or
    credential construction.
    """

    client: PublicMarketClient
    store: PaperRunStoreLike
    strategy_registry: Mapping[str, object]
    allowed_base_assets: frozenset[str]
    paper_policy: LivePaperPolicy
    budget_guard: CloudBudgetGuard
    before_external: Callable[[], None]
    reservation_ledger: BudgetSlotReservationLedger | None = None
    d1_usage_guard: D1UsageBudgetGate | None = None
    run_name: str = "cloud-paper-v0-1"

    def __post_init__(self) -> None:
        if not self.allowed_base_assets:
            raise ValueError("governed base-asset allowlist is required")
        if not isinstance(self.budget_guard, CloudBudgetGuard):
            raise ValueError("a cloud budget guard is required")
        if not callable(self.before_external):
            raise ValueError("an external-access guard is required")
        store_guard = getattr(self.store, "budget_guard", None)
        if store_guard is None:
            store_guard = getattr(getattr(self.store, "store", None), "budget_guard", None)
        if store_guard is not self.budget_guard:
            raise CloudPaperCompositionBlocked("R2_BUDGET_GUARD_NOT_BOUND")
        if not isinstance(self.run_name, str) or not self.run_name:
            raise ValueError("run_name is required")

    def _require_empty_production_registry(self) -> None:
        registry = self.strategy_registry
        if (
            registry.get("schema") != "qookey-cloud-paper-strategy-registry-v0.1"
            or registry.get("status") != "EMPTY_NO_ELIGIBLE_STRATEGIES"
            or registry.get("model_quality") != "REJECT"
            or registry.get("production_fixture_admission") is not False
            or registry.get("automatic_promotion") is not False
            or registry.get("strategies") != []
        ):
            raise CloudPaperCompositionBlocked(
                "PRODUCTION_STRATEGY_AUTHORITY_UNAVAILABLE"
            )

    def _reserve_provider_request(self) -> None:
        self.before_external()
        self.budget_guard.reserve_provider_request()

    def run_slot(
        self, *,
        tick_ms: int,
        previous_slot: str | None,
        activation_enabled: bool = False,
        run_id: str | None = None,
    ) -> dict[str, object]:
        """Run one explicitly enabled no-trade slot; default is side-effect free."""
        if type(activation_enabled) is not bool:
            raise CloudPaperCompositionBlocked("ACTIVATION_FLAG_INVALID")
        if not activation_enabled:
            return {
                "schema": "qookey-cloud-paper-loop-report-v0.1",
                "state": "DISABLED",
                "reason": "ACTIVATION_DISABLED",
                "tick_ms": tick_ms,
                "provider_requests_performed": 0,
                "persistent_state_writes_performed": 0,
            }

        # This composition may only exercise the currently approved empty
        # production registry. Synthetic positive-path candidates remain in CI.
        self._require_empty_production_registry()

        if self.reservation_ledger is None or self.d1_usage_guard is None:
            raise CloudPaperCompositionBlocked(
                "D1_BUDGET_EVIDENCE_OR_LEDGER_MISSING"
            )
        if not isinstance(run_id, str) or not run_id or len(run_id) > 100:
            raise CloudPaperCompositionBlocked("RUN_ID_INVALID")
        slot = slot_id(tick_ms)
        # D1 itself is an external access: require fresh account-wide D1 usage
        # evidence, then atomically reserve the R2/provider envelope before any
        # provider or R2 request. The disabled-by-default path never gets here.
        self.before_external()
        self.d1_usage_guard.validate_evidence()
        self.reservation_ledger.reserve_slot(
            slot_id=slot,
            run_id=run_id,
            now_ms=tick_ms,
            snapshot=self.budget_guard.snapshot,
        )

        def market_supplier() -> Mapping[str, object]:
            capture = capture_market(
                self.client,
                as_of_ms=tick_ms,
                allowed_base_assets=self.allowed_base_assets,
                before_request=self._reserve_provider_request,
            )
            report = analyze_capture(
                capture, allowed_base_assets=self.allowed_base_assets,
            )
            return {
                **report,
                "provider_requests_performed": capture.requests_attempted,
            }

        feed = CompleteTapePionexFeed(
            client=self.client,
            policy=self.paper_policy,
            before_request=self._reserve_provider_request,
        )
        return run_cloud_step(
            tick_ms=tick_ms,
            previous_slot=previous_slot,
            store=self.store,
            feed=feed,
            market_supplier=market_supplier,
            candidate_supplier=lambda market, state: (),
            strategy_registry=self.strategy_registry,
            before_external=self.before_external,
            run_name=self.run_name,
        )
