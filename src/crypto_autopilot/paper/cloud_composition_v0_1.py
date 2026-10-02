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
from crypto_autopilot.paper.cloud_candidate_adapter_v0_1 import (
    CloudCandidateRegistryBlocked,
    select_qualified_candidates,
    validate_strategy_registry,
)
from crypto_autopilot.paper.cloud_budget_ledger_v0_1 import (
    D1SlotReservation,
    SlotUsage,
)
from crypto_autopilot.paper.cloud_loop_v0_1 import (
    CompleteTapePionexFeed,
    committed_report,
    digest,
    validate_slot_start,
)
from crypto_autopilot.paper.cloud_loop_v0_2 import run_cloud_step
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

    def settle_slot(
        self, *, slot_id: str, completed_at_ms: int, usage: SlotUsage,
    ) -> None:
        """Settle an exactly observed completed slot or retain its reservation."""

    def get_slot_reservation(self, *, slot_id: str) -> D1SlotReservation | None:
        """Read the existing reservation without releasing its envelope."""

    def record_verified_result_recovery(
        self, *, slot_id: str, run_id: str, report_id: str,
        recovered_at_ms: int,
    ) -> None:
        """Record verified completion while retaining the full reservation."""


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
    completion_clock_ms: Callable[[], int]
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
        if not callable(self.completion_clock_ms):
            raise ValueError("a completion clock is required for settlement")
        store_guard = getattr(self.store, "budget_guard", None)
        if store_guard is None:
            store_guard = getattr(getattr(self.store, "store", None), "budget_guard", None)
        if store_guard is not self.budget_guard:
            raise CloudPaperCompositionBlocked("R2_BUDGET_GUARD_NOT_BOUND")
        if not isinstance(self.run_name, str) or not self.run_name:
            raise ValueError("run_name is required")

    def _validate_strategy_registry(self) -> dict[str, Mapping[str, object]]:
        try:
            return validate_strategy_registry(self.strategy_registry)
        except CloudCandidateRegistryBlocked:
            raise CloudPaperCompositionBlocked(
                "PRODUCTION_STRATEGY_AUTHORITY_UNAVAILABLE"
            ) from None

    def _select_candidates(
        self,
        market: Mapping[str, object],
        state: Mapping[str, object],
    ) -> tuple[Mapping[str, object], ...]:
        selection = select_qualified_candidates(
            market,
            state,
            self.strategy_registry,
            allowed_base_assets=self.allowed_base_assets,
        )
        # run_cloud_step materializes market as a dict before invoking this
        # callback, so selection state and rejection reasons are persisted with
        # the same immutable Paper report.
        if not isinstance(market, dict):
            raise CloudPaperCompositionBlocked("MARKET_REPORT_NOT_MUTABLE")
        selection_reasons = list(selection.reasons)
        if market.get("market_scan_skip_reason") == "NO_ELIGIBLE_STRATEGY":
            selection_reasons.insert(0, "MARKET_SCAN_SKIPPED_NO_ELIGIBLE_STRATEGY")
        market["execution_selection_status"] = selection.status
        market["execution_selection_reasons"] = selection_reasons
        return selection.candidates

    def _reserve_provider_request(self) -> None:
        self.before_external()
        self.budget_guard.reserve_provider_request()

    def recover_completed_slot(
        self, *,
        slot: str,
        recovery_enabled: bool = False,
    ) -> dict[str, object]:
        """Verify a completed immutable result after restart, keeping full reserve.

        This path is disabled by default. It never reruns a slot, calls a provider,
        rewrites R2, or releases unused budget. A verified result gets an audit
        receipt in D1; missing or conflicting evidence leaves the reservation
        untouched for review.
        """
        if type(recovery_enabled) is not bool:
            raise CloudPaperCompositionBlocked("RECOVERY_FLAG_INVALID")
        if not recovery_enabled:
            return {
                "state": "DISABLED",
                "reason": "SETTLEMENT_RECOVERY_NOT_AUTHORIZED",
                "slot_id": slot,
            }
        if not isinstance(slot, str) or not slot.isdigit() or str(int(slot)) != slot:
            raise CloudPaperCompositionBlocked("RECOVERY_SLOT_INVALID")
        if self.reservation_ledger is None or self.d1_usage_guard is None:
            raise CloudPaperCompositionBlocked("D1_BUDGET_EVIDENCE_OR_LEDGER_MISSING")

        self.before_external()
        self.d1_usage_guard.validate_evidence()
        reservation = self.reservation_ledger.get_slot_reservation(slot_id=slot)
        if reservation is None:
            return {"state": "NOT_FOUND", "slot_id": slot}
        if reservation.state == "SETTLED":
            return {"state": "ALREADY_SETTLED", "slot_id": slot}
        if reservation.state != "RESERVED":
            raise CloudPaperCompositionBlocked("RECOVERY_RESERVATION_STATE_INVALID")

        report = committed_report(
            self.store, slot, before_external=self.before_external,
        )
        if report is None:
            raise CloudPaperCompositionBlocked("RECOVERY_RESULT_MISSING")
        if report.get("state") not in {"COMMITTED", "NO_TRADE", "REVIEW_REQUIRED"}:
            raise CloudPaperCompositionBlocked("RECOVERY_RESULT_NOT_COMPLETE")
        # The D1 reservation is unique per canonical slot. The immutable,
        # digest-verified cloud-result pointer and its verified coordinator step
        # bind the report to this slot; keep the GitHub run id from the D1 row as
        # the recovery receipt's audit owner.
        report_id = digest(report)
        self.before_external()
        self.d1_usage_guard.validate_evidence()
        self.reservation_ledger.record_verified_result_recovery(
            slot_id=slot,
            run_id=reservation.run_id,
            report_id=report_id,
            recovered_at_ms=self.completion_clock_ms(),
        )
        return {
            "state": "RECOVERED_RESERVED_FULL",
            "slot_id": slot,
            "run_id": reservation.run_id,
            "report_id": report_id,
            "budget_released": False,
            "r2_writes_performed": 0,
        }

    def run_slot(
        self, *,
        tick_ms: int,
        previous_slot: str | None,
        activation_enabled: bool = False,
        run_id: str | None = None,
        scheduled_at_ms: int | None = None,
    ) -> dict[str, object]:
        """Run a slot using actual tick_ms for market, lifecycle and budget time.

        scheduled_at_ms identifies its canonical slot; delayed starts must pass
        it explicitly. Omission retains exact-tick compatibility. Default is off.
        """
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

        # Validate registry authority before any D1, provider, or R2 access.
        # The current empty registry remains a normal no-trade configuration.
        registrations = self._validate_strategy_registry()

        if self.reservation_ledger is None or self.d1_usage_guard is None:
            raise CloudPaperCompositionBlocked(
                "D1_BUDGET_EVIDENCE_OR_LEDGER_MISSING"
            )
        if not isinstance(run_id, str) or not run_id or len(run_id) > 100:
            raise CloudPaperCompositionBlocked("RUN_ID_INVALID")
        scheduled_at_ms = tick_ms if scheduled_at_ms is None else scheduled_at_ms
        slot = validate_slot_start(
            scheduled_at_ms=scheduled_at_ms, started_at_ms=tick_ms,
        )
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
            if not registrations:
                return {
                    "schema": "qookey-cloud-paper-market-report-v0.1",
                    "provider": "NOT_ACCESSED",
                    "configured_provider": "PIONEX_PUBLIC",
                    "market_status": "NOT_SCANNED",
                    "context_status": "NOT_EVALUATED",
                    "market_scan_skip_reason": "NO_ELIGIBLE_STRATEGY",
                    "as_of_ms": tick_ms,
                    "candidate_specs": [],
                    "provider_requests_performed": 0,
                }
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
        result = run_cloud_step(
            tick_ms=tick_ms,
            scheduled_at_ms=scheduled_at_ms,
            previous_slot=previous_slot,
            store=self.store,
            feed=feed,
            market_supplier=market_supplier,
            candidate_supplier=lambda market, state: self._select_candidates(
                market, state,
            ),
            strategy_registry=self.strategy_registry,
            before_external=self.before_external,
            run_name=self.run_name,
        )
        # Only a completely returned, immutable/readback-verified Paper result
        # may release unused reservation. Exceptions leave the full envelope in
        # RESERVED for explicit recovery; settlement errors propagate unchanged.
        if result.get("state") in {"REVIEW_REQUIRED", "REPLAYED"}:
            # Keep the complete D1 reservation when the report needs review or
            # the slot already committed. Never infer usage from a replay.
            return result
        if result.get("state") not in {"COMMITTED", "NO_TRADE"}:
            raise CloudPaperCompositionBlocked("PAPER_RESULT_NOT_SETTLEABLE")
        self.d1_usage_guard.validate_evidence()
        usage = self.budget_guard.attempted_usage()
        self.reservation_ledger.settle_slot(
            slot_id=slot,
            completed_at_ms=self.completion_clock_ms(),
            usage=SlotUsage(
                provider_requests=usage.provider_requests,
                class_a=usage.class_a_requests,
                class_b=usage.class_b_requests,
                new_bytes=usage.new_bytes,
            ),
        )
        return result
