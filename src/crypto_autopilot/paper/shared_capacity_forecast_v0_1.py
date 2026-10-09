"""Synthetic-only shared-account Cloud Paper capacity and meter-cost forecast.

Never reads an account, calls Cloudflare, constructs an R2/D1 client, or
grants Paper/real-money authority. This models *demand*, not proven headroom.
Caller-supplied caps are hypothetical test inputs, never production policy.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

_METRICS = (
    "provider_requests",
    "r2_class_a",
    "r2_class_b",
    "r2_new_bytes",
    "d1_queries",
    "d1_rows_read",
    "d1_rows_written",
    "d1_storage_growth_bytes",
)
_ROLLING = ("r2_class_a", "r2_class_b", "r2_new_bytes")
_METRIC_LIMIT = 10**12


def _bounded_int(value: object, name: str, *, minimum: int = 0) -> int:
    if type(value) is not int or not minimum <= value <= _METRIC_LIMIT:
        raise ValueError(f"{name}: INVALID_NONNEGATIVE_INTEGER")
    return value


@dataclass(frozen=True, slots=True)
class SlotDemand:
    """Success-reservation V0.4 resource envelope, INCLUDING base ledger cost."""
    provider_requests: int
    r2_class_a: int
    r2_class_b: int
    r2_new_bytes: int
    d1_queries: int
    d1_rows_read: int
    d1_rows_written: int
    d1_storage_growth_bytes: int

    def validate(self) -> None:
        for key in _METRICS:
            _bounded_int(getattr(self, key), key)
        # Minimum V0.4 reservation envelope; not a real D1 query cost claim.
        if self.d1_queries < 2 or self.d1_rows_read < 1 or self.d1_rows_written < 7:
            raise ValueError("SUCCESS_SLOT_LEDGER_FLOOR_MISSING")


@dataclass(frozen=True, slots=True)
class WriterDemand:
    writer_id: str
    successful_slots_per_day: int
    replay_attempts_per_day: int
    rejected_attempts_per_day: int
    per_success_slot: SlotDemand

    def validate(self) -> None:
        if not isinstance(self.writer_id, str) or not self.writer_id.strip():
            raise ValueError("WRITER_ID_MISSING")
        for name in (
            "successful_slots_per_day", "replay_attempts_per_day",
            "rejected_attempts_per_day",
        ):
            _bounded_int(getattr(self, name), name)
        self.per_success_slot.validate()


@dataclass(frozen=True, slots=True)
class MeterAttemptDemand:
    """Uncalibrated synthetic control-plane charge for each attempted D1 query.

    A successful reservation is modeled as one admission statement; exact
    replay and policy rejection pessimistically require up to two statements.
    A debit is consumed before *each* attempt, even when it fails.
    """
    control_d1_queries: int
    control_d1_rows_read: int
    control_d1_rows_written: int
    control_d1_storage_growth_bytes: int
    readback_d1_rows_read_per_statement: int

    def validate(self) -> None:
        for name in (
            "control_d1_queries", "control_d1_rows_read",
            "control_d1_rows_written", "control_d1_storage_growth_bytes",
            "readback_d1_rows_read_per_statement",
        ):
            _bounded_int(getattr(self, name), name)
        if self.control_d1_queries < 1:
            raise ValueError("CONTROL_PLANE_COST_NOT_BOUNDED")


def _null_caps(caps: object) -> bool:
    if not isinstance(caps, Mapping):
        return True
    daily = caps.get("daily")
    rolling = caps.get("rolling_31_days")
    if not isinstance(daily, Mapping) or not isinstance(rolling, Mapping):
        return True
    for name in ("reservations", *_METRICS):
        if type(daily.get(name)) is not int or daily[name] < 0:
            return True
    for name in _ROLLING:
        if type(rolling.get(name)) is not int or rolling[name] < 0:
            return True
    return False


def forecast_shared_budget(
    *,
    writers: Sequence[WriterDemand],
    query_attempt_cost: MeterAttemptDemand,
    hypothetical_caps: Mapping[str, object] | None = None,
    window_days: int = 31,
) -> dict[str, object]:
    """Conservatively forecast accounting overhead for *all included writers*.

    Does not claim writer inventory completeness, D1 storage baseline,
    account-level headroom, or a production-capable prepaid controller.
    No capacities from caller inputs grant approval. Missing caps fail closed.
    """
    _bounded_int(window_days, "window_days", minimum=1)
    if window_days > 31:
        raise ValueError("WINDOW_EXCEEDS_31_DAYS")
    if not isinstance(writers, (tuple, list)) or not 1 <= len(writers) <= 100:
        raise ValueError("WRITER_COUNT_INVALID")
    query_attempt_cost.validate()
    seen: set[str] = set()
    daily = {key: 0 for key in _METRICS}
    successful_slots = 0
    replay_attempts = 0
    rejected_attempts = 0
    for writer in writers:
        if not isinstance(writer, WriterDemand):
            raise ValueError("WRITER_INVALID")
        writer.validate()
        if writer.writer_id in seen:
            raise ValueError("DUPLICATE_WRITER_ID")
        seen.add(writer.writer_id)
        successful_slots += writer.successful_slots_per_day
        replay_attempts += writer.replay_attempts_per_day
        rejected_attempts += writer.rejected_attempts_per_day
        for key in _METRICS:
            daily[key] += (
                writer.successful_slots_per_day * getattr(writer.per_success_slot, key)
            )

    # The V0.4 helper can execute a failed insert followed by a replay/read
    # query. We assume TWO statements for every replay or rejection.
    unsuccessful_query_calls = 2 * (replay_attempts + rejected_attempts)
    meter_debits = successful_slots + unsuccessful_query_calls
    daily["d1_queries"] += (
        unsuccessful_query_calls
        + meter_debits * query_attempt_cost.control_d1_queries
    )
    daily["d1_rows_read"] += (
        unsuccessful_query_calls * query_attempt_cost.readback_d1_rows_read_per_statement
        + meter_debits * query_attempt_cost.control_d1_rows_read
    )
    daily["d1_rows_written"] += (
        meter_debits * query_attempt_cost.control_d1_rows_written
    )
    daily["d1_storage_growth_bytes"] += (
        meter_debits * query_attempt_cost.control_d1_storage_growth_bytes
    )

    rolling = {name: daily[name] * window_days for name in _ROLLING}
    storage_growth = daily["d1_storage_growth_bytes"] * window_days
    reservations_in_window = successful_slots * window_days

    violations: list[str] = []
    if not _null_caps(hypothetical_caps):
        assert isinstance(hypothetical_caps, Mapping)
        capped_daily = hypothetical_caps["daily"]
        capped_rolling = hypothetical_caps["rolling_31_days"]
        assert isinstance(capped_daily, Mapping) and isinstance(capped_rolling, Mapping)
        if successful_slots > capped_daily["reservations"]:
            violations.append("daily.reservations")
        for key in _METRICS:
            if daily[key] > capped_daily[key]:
                violations.append(f"daily.{key}")
        for key in _ROLLING:
            if rolling[key] > capped_rolling[key]:
                violations.append(f"rolling_31_days.{key}")

    return {
        "schema": "qookey-cloud-paper-shared-capacity-forecast-v0.1",
        "mode": "SYNTHETIC_PLANNING_ONLY_NO_EXTERNAL_READ",
        "status": (
            "BLOCKED_UNKNOWN_CAPS"
            if _null_caps(hypothetical_caps)
            else "BLOCKED_SCENARIO_OVER_CAP" if violations
            else "SCENARIO_WITHIN_INPUT_CAPS_NOT_AUTHORIZED"
        ),
        "writer_ids": sorted(seen),
        "writer_inventory_complete_proven": False,
        "approved_account_caps_proven": False,
        "account_usage_and_headroom_fresh": False,
        "d1_provisioned": False,
        "durable_prepaid_controller_implemented_and_calibrated": False,
        "real_account_storage_baseline_known": False,
        "zero_usd_monthly_cost_proven": False,
        "production_execution_authority": False,
        "paper_activation_allowed": False,
        "real_money_order_authority": False,
        "window_days": window_days,
        "daily_successful_reservations": successful_slots,
        "daily_replay_attempts": replay_attempts,
        "daily_rejected_attempts": rejected_attempts,
        "daily_non_successful_d1_query_attempts": unsuccessful_query_calls,
        "daily_prepaid_meter_debits": meter_debits,
        "daily_resource_demand_including_meter": daily,
        "rolling_resource_demand": rolling,
        "projected_new_d1_storage_bytes_in_window_not_total": storage_growth,
        "reservations_retained_if_no_compaction": reservations_in_window,
        "assumed_statement_bound": "ONE_PER_SUCCESS_TWO_PER_REPLAY_OR_REJECTION",
        "hypothetical_cap_violations": violations,
        "note": (
            "Success-slot reservation amounts already include baseline shared-ledger cost; "
            "replay/rejection attempts and independent prepaid meter controller costs "
            "are added without refund. No live D1 query metadata or external writer "
            "usage is inferred. Existing storage and query-controller self funding "
            "remain unverified."
        ),
    }
