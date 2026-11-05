"""Prepared in-process Paper run observation; not an execution authority.

No workflow, artifact upload, service request or credential is created here.
The runtime remains responsible for admission, settlement and result readback.
Counters measure SDK invocations and conservative reservations, not Cloudflare
billing. A terminated process may leave no receipt.
"""
from __future__ import annotations

import re
import threading

from crypto_autopilot.paper.cloud_loop_v0_1 import digest
from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Client, BudgetedR2Store
from crypto_autopilot.paper.cloud_run_store_v0_1 import CloudPaperRunStore
from crypto_autopilot.paper.cloud_runtime_v0_4 import V05PaperComposition


class PaperObservationError(RuntimeError):
    """Fixed error with safe partial observation; never includes raw exceptions."""

    def __init__(self, receipt):
        super().__init__("PAPER_RUN_OBSERVATION_REVIEW_REQUIRED")
        self.receipt = receipt


class _AttemptCounter:
    def __init__(self, delegate):
        self._delegate = delegate
        self._lock = threading.Lock()
        self._counts = {"PUT": 0, "GET": 0, "LIST": 0}

    def _call(self, name, operation, kwargs):
        with self._lock:
            self._counts[operation] += 1
        return getattr(self._delegate, name)(**kwargs)

    def put_object(self, **kwargs):
        return self._call("put_object", "PUT", kwargs)

    def get_object(self, **kwargs):
        return self._call("get_object", "GET", kwargs)

    def list_objects_v2(self, **kwargs):
        return self._call("list_objects_v2", "LIST", kwargs)

    def snapshot(self):
        with self._lock:
            return dict(self._counts)


def run_observed_slot(runtime, *, tick_ms, previous_slot, activation_enabled=False,
                      run_id, scheduled_at_ms=None):
    """Run the prepared composition once and return result plus safe observation.

    This must not be used as a trusted identity or cost authority. A caller must
    persist the observation through an independently authorized, bounded channel.
    """
    if (type(runtime) is not V05PaperComposition
            or type(activation_enabled) is not bool
            or not isinstance(run_id, str)
            or re.fullmatch(r"github-[1-9][0-9]{0,19}-[1-9][0-9]{0,9}", run_id) is None):
        raise ValueError("PAPER_OBSERVATION_INPUT_INVALID")
    kwargs = {
        "tick_ms": tick_ms, "previous_slot": previous_slot,
        "activation_enabled": activation_enabled, "run_id": run_id,
        "scheduled_at_ms": scheduled_at_ms,
    }
    if not activation_enabled:
        return runtime.run_slot(**kwargs), {"status": "DISABLED"}

    guarded = getattr(runtime.store, "_inner", None)
    store = getattr(guarded, "store", None)
    client = getattr(store, "client", None)
    ledger = runtime.reservation_ledger
    d1 = getattr(ledger, "client", None)
    meter = getattr(ledger, "_meter", None)
    if (not isinstance(guarded, CloudPaperRunStore)
            or not isinstance(store, BudgetedR2Store)
            or not isinstance(client, BudgetedR2Client)
            or store.budget_guard is not runtime.budget_guard
            or d1 is None or meter is None
            or getattr(ledger, "_admitted", None) is not False
            or getattr(ledger, "_closed", None) is not False):
        raise ValueError("PAPER_OBSERVATION_RUNTIME_UNVERIFIED")
    usage = runtime.budget_guard.attempted_usage()
    if (any((usage.provider_requests, usage.class_a_requests,
             usage.class_b_requests, usage.new_bytes))
            or d1.diagnostics()["http_attempts"] != 0
            or meter.report()["query_attempts_charged"] != 0
            or isinstance(client._client, _AttemptCounter)):
        raise ValueError("PAPER_OBSERVATION_RUNTIME_NOT_PRISTINE")
    counter = _AttemptCounter(client._client)
    client._client = counter

    def observation(status, report):
        reserved = runtime.budget_guard.attempted_usage()
        diagnostic = d1.diagnostics()
        return {
            "schema": "qookey-cloud-paper-usage-observation-v0.1",
            "status": status,
            "run_id_unattested": run_id,
            "slot_id": report.get("slot_id") if isinstance(report, dict) else None,
            "report_id": digest(report) if isinstance(report, dict) else None,
            "r2_sdk_attempts": counter.snapshot(),
            "r2_reserved_class_a": reserved.class_a_requests,
            "r2_reserved_class_b": reserved.class_b_requests,
            "r2_reserved_payload_bytes": reserved.new_bytes,
            "provider_reserved_attempts": reserved.provider_requests,
            "d1_http_attempts": diagnostic["http_attempts"],
            "d1_ticket_debits": meter.report()["query_attempts_charged"],
            "d1_rows_read": None,
            "d1_rows_written": None,
            "provider_confirmed_billing": False,
            "account_wide_coverage_proven": False,
            "identity_attested": False,
            "survives_process_loss": False,
        }

    try:
        report = runtime.run_slot(**kwargs)
        if (not isinstance(report, dict) or report.get("state") not in ("NO_TRADE", "COMMITTED")
                or report.get("schema") != "qookey-cloud-paper-loop-report-v0.3"):
            raise ValueError("PAPER_OBSERVATION_RESULT_UNVERIFIED")
        return report, observation("OBSERVED_RETURNED", report)
    except Exception:
        raise PaperObservationError(observation("REVIEW_REQUIRED", None)) from None
