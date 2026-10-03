"""Finite prepaid admission tickets with durable GitHub reference claims.

A whole ticket is charged before D1 access. An immutable remote claim prevents
a new process from reclaiming unused allowance after failure. This controller
does not obtain account usage evidence, authorize D1, or start a workflow.
"""
from __future__ import annotations

import base64
import json
import re
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Literal, Protocol
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.shared_writer_budget_gate_v0_4 import (
    Query,
    QueryOperation,
    SharedWriterReservation,
    reserve_shared_writer_envelope,
)

CONFIG_PATH = "config/cloudflare_prepaid_query_controller_v0_1.json"
_SCHEMA = "qookey-cloudflare-prepaid-query-controller-v0.1"
_ALIAS = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
_WRITER = re.compile(r"^[a-z0-9][a-z0-9:._/-]{0,127}$")
_REPO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$")
_SHA = re.compile(r"^[0-9a-f]{40}$")
_METRICS = ("queries", "rows_read", "rows_written", "storage_bytes")
_MAX_GITHUB_REQUESTS = 8
_MAX_BODY_BYTES = 131_072
_CLAIM_CONFIRMED = object()


def _blocked(reason: str) -> BudgetBlocked:
    return BudgetBlocked("BLOCKED_PREPAID_" + reason)


def _int(value: object, *, positive: bool = False) -> int:
    if type(value) is not int or value < (1 if positive else 0):
        raise _blocked("POLICY_INVALID")
    return value


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise _blocked("POLICY_INVALID")
    return value


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise _blocked("POLICY_INVALID")
    return value


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise _blocked("RUN_INVALID")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise _blocked("RUN_INVALID") from None
    if result.utcoffset() is None:
        raise _blocked("RUN_INVALID")
    return result.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class QueryCost:
    queries: int
    rows_read: int
    rows_written: int
    storage_bytes: int

    def validate(self) -> None:
        for name in _METRICS:
            _int(getattr(self, name))
        if self.queries != 1:
            raise _blocked("STATEMENT_COST_INVALID")

    @classmethod
    def parse(cls, raw: object) -> QueryCost:
        values = _mapping(raw)
        cost = cls(**{name: _int(values.get(name)) for name in _METRICS})
        cost.validate()
        return cost


@dataclass(frozen=True, slots=True)
class WriterAllocation:
    writer_id: str
    alias: str
    workflow_id: int
    workflow_path: str
    daily_tickets: int
    queries_per_ticket: int


@dataclass(frozen=True, slots=True)
class PoolAuthority:
    scope_id: str
    repository: str
    starts_on: date
    ends_on: date
    ruleset_id: int
    max_evidence_age_ms: int
    max_run_age_ms: int
    costs: Mapping[QueryOperation, QueryCost]
    writers: tuple[WriterAllocation, ...]

    @classmethod
    def parse(cls, raw: object) -> PoolAuthority:
        data = _mapping(raw)
        # Disabled checked first: default main cannot initiate even GitHub claims.
        if data.get("activation_enabled") is not True:
            raise _blocked("CONTROLLER_DISABLED")
        if (
            data.get("schema") != _SCHEMA
            or data.get("github_claims_authorized") is not True
            or data.get("account_allocation_verified") is not True
        ):
            raise _blocked("AUTHORITY_UNVERIFIED")
        scope = _text(data.get("scope_id"))
        repo = _text(data.get("repository"))
        if not _ALIAS.fullmatch(scope) or not _REPO.fullmatch(repo):
            raise _blocked("POLICY_INVALID")
        try:
            start = date.fromisoformat(_text(data.get("starts_on")))
            end = date.fromisoformat(_text(data.get("ends_on")))
        except ValueError:
            raise _blocked("POLICY_INVALID") from None
        if not 1 <= (end - start).days + 1 <= 31:
            raise _blocked("POLICY_INVALID")
        raw_costs = _mapping(data.get("statement_costs"))
        costs: dict[QueryOperation, QueryCost] = {
            "RESERVATION": QueryCost.parse(raw_costs.get("RESERVATION")),
            "REPLAY_READ": QueryCost.parse(raw_costs.get("REPLAY_READ")),
        }
        entries = data.get("writers")
        if not isinstance(entries, list) or not 1 <= len(entries) <= 32:
            raise _blocked("POLICY_INVALID")
        writers = []
        for entry in entries:
            item = _mapping(entry)
            writer = WriterAllocation(
                writer_id=_text(item.get("writer_id")),
                alias=_text(item.get("alias")),
                workflow_id=_int(item.get("workflow_id"), positive=True),
                workflow_path=_text(item.get("workflow_path")),
                daily_tickets=_int(item.get("daily_tickets"), positive=True),
                queries_per_ticket=_int(item.get("queries_per_ticket"), positive=True),
            )
            if (
                not _WRITER.fullmatch(writer.writer_id)
                or not _ALIAS.fullmatch(writer.alias)
                or not re.fullmatch(r"\.github/workflows/[a-z0-9-]+\.yml", writer.workflow_path)
                or writer.daily_tickets > 288 or writer.queries_per_ticket > 32
            ):
                raise _blocked("POLICY_INVALID")
            writers.append(writer)
        if (
            len({w.writer_id for w in writers}) != len(writers)
            or len({w.alias for w in writers}) != len(writers)
            or len({w.workflow_id for w in writers}) != len(writers)
        ):
            raise _blocked("POLICY_INVALID")
        age = _int(data.get("max_evidence_age_ms"), positive=True)
        run_age = _int(data.get("max_run_age_ms"), positive=True)
        if age > 60_000 or run_age > 600_000:
            raise _blocked("POLICY_INVALID")
        return cls(
            scope, repo, start, end, _int(data.get("ruleset_id"), positive=True),
            age, run_age, costs, tuple(writers),
        )

    @property
    def ref_prefix(self) -> str:
        return "refs/tags/cloud-budget-query-v0-1/" + self.scope_id + "/"

    def ticket_envelope(self, writer: WriterAllocation) -> dict[str, int]:
        return {
            name: max(getattr(cost, name) for cost in self.costs.values())
            * writer.queries_per_ticket for name in _METRICS
        }

    def daily_envelope(self) -> dict[str, int]:
        return {
            name: sum(
                self.ticket_envelope(writer)[name] * writer.daily_tickets
                for writer in self.writers
            ) for name in _METRICS
        }


@dataclass(frozen=True, slots=True)
class AllocationEvidence:
    """Headroom after other workloads, writers, scopes and controller overhead.

    Evidence production is a separate governed operation. This type cannot
    establish account completeness or cost by assertion alone.
    """

    account_coverage_complete: bool
    zero_cost_verified: bool
    observed_at_ms: int
    measured_through_ms: int
    available: Mapping[str, int]

    def validate(self, authority: PoolAuthority, now_ms: int) -> None:
        if self.account_coverage_complete is not True or self.zero_cost_verified is not True:
            raise _blocked("ACCOUNT_EVIDENCE_INCOMPLETE")
        now = _clock(now_ms)
        for value in (self.observed_at_ms, self.measured_through_ms):
            _int(value)
            if (
                not 0 <= now_ms - value <= authority.max_evidence_age_ms
                or datetime.fromtimestamp(value / 1000, UTC).date() != now.date()
            ):
                raise _blocked("ACCOUNT_EVIDENCE_STALE")
        envelope = authority.daily_envelope()
        # Storage is cumulative, so pre-fund every possible ticket in this scope.
        envelope["storage_bytes"] *= (authority.ends_on - authority.starts_on).days + 1
        for name, required in envelope.items():
            available = _int(self.available.get(name))
            if required > available:
                raise _blocked("ACCOUNT_ALLOCATION_EXCEEDED")


def _clock(now_ms: int) -> datetime:
    _int(now_ms, positive=True)
    try:
        return datetime.fromtimestamp(now_ms / 1000, UTC)
    except (ValueError, OverflowError, OSError):
        raise _blocked("CLOCK_INVALID") from None


@dataclass(frozen=True, slots=True)
class GitHubResponse:
    status: int
    payload: dict[str, object]


class GitHubTransport(Protocol):
    def __call__(
        self, method: str, path: str, body: dict[str, object] | None = None,
    ) -> GitHubResponse: ...


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GitHubJSONClient:
    """Single-attempt bounded GitHub-only transport; never logs response bodies."""

    def __init__(self, *, token: str) -> None:
        if not isinstance(token, str) or not token or "\n" in token or "\r" in token:
            raise _blocked("GITHUB_CREDENTIAL_UNAVAILABLE")
        self._token = token

    def __call__(
        self, method: str, path: str, body: dict[str, object] | None = None,
    ) -> GitHubResponse:
        if method not in ("GET", "POST") or not path.startswith("/repos/"):
            raise _blocked("GITHUB_REQUEST_INVALID")
        request = Request(
            "https://api.github.com" + path, method=method,
            data=None if body is None else json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + self._token,
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with build_opener(_NoRedirect()).open(request, timeout=10) as response:
                raw = response.read(_MAX_BODY_BYTES + 1)
                if len(raw) > _MAX_BODY_BYTES:
                    raise _blocked("GITHUB_RESPONSE_INVALID")
                payload = json.loads(raw)
                if not isinstance(payload, dict):
                    raise _blocked("GITHUB_RESPONSE_INVALID")
                return GitHubResponse(response.status, payload)
        except HTTPError as error:
            # A 422 can mean conflict, validation or spam. None allows reclaim.
            return GitHubResponse(error.code, {})
        except Exception:
            raise _blocked("GITHUB_TRANSPORT_UNVERIFIED") from None


class PrepaidQueryMeter:
    """Spend inside one fully charged remote ticket; no refunds or reclaims."""

    def __init__(
        self, *, authority: PoolAuthority, writer: WriterAllocation,
        ticket_ref: str, slot_id: str, charged_day: date,
        claim_confirmation: object,
        evidence: AllocationEvidence, clock_ms: Callable[[], int],
    ) -> None:
        if claim_confirmation is not _CLAIM_CONFIRMED:
            raise _blocked("CLAIM_REQUIRED")
        self._authority = authority
        self._writer = writer
        self._ref = ticket_ref
        self._slot_id = slot_id
        self._day = charged_day
        self._evidence = evidence
        self._clock_ms = clock_ms
        self._queries_used = 0
        self._lock = threading.Lock()

    def charge_before_query(
        self, *, writer_id: str, slot_id: str, operation: QueryOperation,
    ) -> Literal["CHARGED"]:
        with self._lock:
            now_ms = self._clock_ms()
            now = _clock(now_ms)
            if now.date() != self._day or not self._authority.starts_on <= now.date() <= self._authority.ends_on:
                raise _blocked("TICKET_EXPIRED")
            self._evidence.validate(self._authority, now_ms)
            if writer_id != self._writer.writer_id or slot_id != self._slot_id:
                raise _blocked("TICKET_IDENTITY_MISMATCH")
            if operation not in self._authority.costs:
                raise _blocked("STATEMENT_UNSUPPORTED")
            if self._queries_used >= self._writer.queries_per_ticket:
                raise _blocked("QUERY_POOL_EXHAUSTED")
            self._queries_used += 1
            return "CHARGED"

    def report(self) -> dict[str, object]:
        with self._lock:
            return {
                "ticket_ref": self._ref,
                "utc_day": self._day.isoformat(),
                "ticket_envelope_charged_in_full": self._authority.ticket_envelope(self._writer),
                "query_attempts_charged": self._queries_used,
                "queries_per_ticket": self._writer.queries_per_ticket,
                "unused_allowance_refunded": False,
            }


def claim_prepaid_query_meter(
    *, authority_document: dict[str, object], writer_id: str, slot_id: str,
    run_id: int, transport: GitHubTransport, evidence: AllocationEvidence,
    clock_ms: Callable[[], int],
) -> PrepaidQueryMeter:
    """Validate current main/run/protection, atomically claim, then read back.

    Every failure blocks before D1. No existing claim is resumed. An ambiguous
    POST can consume the ticket even if its response is lost. Claims must never
    be deleted, force-updated or silently replaced with a new scope.
    """
    authority = PoolAuthority.parse(authority_document)
    _int(run_id, positive=True)
    if not re.fullmatch(r"slot:(0|[1-9][0-9]{0,15})", slot_id):
        raise _blocked("SLOT_INVALID")
    writer = next((w for w in authority.writers if w.writer_id == writer_id), None)
    if writer is None:
        raise _blocked("WRITER_UNREGISTERED")
    started = _clock(clock_ms())
    if not authority.starts_on <= started.date() <= authority.ends_on:
        raise _blocked("SCOPE_EXPIRED")
    evidence.validate(authority, int(started.timestamp() * 1000))
    root = "/repos/" + authority.repository
    requests = 0

    def request(method: str, path: str, body: dict[str, object] | None = None, *, expected: int = 200) -> dict[str, object]:
        nonlocal requests
        if requests >= _MAX_GITHUB_REQUESTS:
            raise _blocked("GITHUB_REQUEST_LIMIT")
        requests += 1
        try:
            response = transport(method, root + path, body)
        except Exception:
            raise _blocked("GITHUB_TRANSPORT_UNVERIFIED") from None
        if response.status != expected or not isinstance(response.payload, dict):
            raise _blocked("GITHUB_RESULT_UNVERIFIED")
        return response.payload

    def main_sha() -> str:
        sha = _mapping(request("GET", "/git/ref/heads/main").get("object")).get("sha")
        if not isinstance(sha, str) or not _SHA.fullmatch(sha):
            raise _blocked("MAIN_UNVERIFIED")
        return sha

    sha = main_sha()
    content = request("GET", "/contents/" + CONFIG_PATH + "?ref=" + sha)
    try:
        if content.get("encoding") != "base64":
            raise ValueError
        encoded = _text(content.get("content")).replace("\n", "")
        approved = json.loads(base64.b64decode(encoded, validate=True))
    except (ValueError, TypeError):
        raise _blocked("AUTHORITY_UNVERIFIED") from None
    if approved != authority_document:
        raise _blocked("AUTHORITY_NOT_CURRENT_MAIN")
    run = request("GET", "/actions/runs/" + str(run_id))
    if (
        type(run.get("id")) is not int or run["id"] != run_id
        or type(run.get("workflow_id")) is not int or run["workflow_id"] != writer.workflow_id
        or run.get("path") != writer.workflow_path
        or run.get("head_sha") != sha or run.get("head_branch") != "main"
        or run.get("event") not in ("schedule", "workflow_dispatch")
        or run.get("status") != "in_progress"
        or type(run.get("run_attempt")) is not int or run["run_attempt"] != 1
    ):
        raise _blocked("RUN_UNVERIFIED")
    number = _int(run.get("run_number"), positive=True)
    run_started = _timestamp(run.get("run_started_at"))
    run_created = _timestamp(run.get("created_at"))
    if (
        run_started.date() != started.date() or run_created > run_started
        or not 0 <= (started - run_created).total_seconds() * 1000 <= authority.max_run_age_ms
        or run_started > started
    ):
        raise _blocked("RUN_STALE")

    def protection() -> None:
        ruleset = request("GET", "/rulesets/" + str(authority.ruleset_id))
        conditions = _mapping(ruleset.get("conditions"))
        refs = _mapping(conditions.get("ref_name"))
        rules = ruleset.get("rules")
        if (
            ruleset.get("target") != "tag" or ruleset.get("enforcement") != "active"
            or ruleset.get("bypass_actors") != []
            or refs.get("include") != [authority.ref_prefix + "**"]
            or refs.get("exclude") != []
            or not isinstance(rules, list)
            or {item.get("type") for item in rules if isinstance(item, dict)} != {"update", "deletion"}
        ):
            raise _blocked("CLAIM_PROTECTION_UNVERIFIED")

    protection()
    # A bounded ring may reject more than the daily allocation. This is safe:
    # never search another ticket or reuse the claim after rejection.
    ticket = (number - 1) % writer.daily_tickets + 1
    ref = authority.ref_prefix + started.date().isoformat() + "/" + writer.alias + "/" + str(ticket)
    now_ms = clock_ms()
    if _clock(now_ms).date() != started.date():
        raise _blocked("TICKET_EXPIRED")
    evidence.validate(authority, now_ms)
    created = request("POST", "/git/refs", {"ref": ref, "sha": sha}, expected=201)

    def verify_ref(payload: dict[str, object]) -> None:
        obj = _mapping(payload.get("object"))
        if payload.get("ref") != ref or obj.get("sha") != sha or obj.get("type") != "commit":
            raise _blocked("CLAIM_READBACK_UNVERIFIED")

    verify_ref(created)
    verify_ref(request("GET", "/git/ref/" + quote(ref.removeprefix("refs/"), safe="/")))
    protection()
    if main_sha() != sha:
        raise _blocked("MAIN_CHANGED_AFTER_CLAIM")
    if _clock(clock_ms()).date() != started.date():
        raise _blocked("TICKET_EXPIRED")
    return PrepaidQueryMeter(
        authority=authority, writer=writer, ticket_ref=ref, slot_id=slot_id,
        charged_day=started.date(), claim_confirmation=_CLAIM_CONFIRMED,
        evidence=evidence, clock_ms=clock_ms,
    )


def claim_and_reserve_shared_writer_envelope(
    *, authority_document: dict[str, object], run_id: int,
    transport: GitHubTransport, evidence: AllocationEvidence,
    clock_ms: Callable[[], int], execute: Query,
    reservation: SharedWriterReservation,
) -> tuple[Literal["RESERVED", "EXISTING_RESERVATION"], dict[str, object]]:
    """Connect a new durable ticket to the existing V0.4 admission path."""
    reservation.validate()
    meter = claim_prepaid_query_meter(
        authority_document=authority_document, writer_id=reservation.writer_id,
        slot_id=reservation.slot_id, run_id=run_id, transport=transport,
        evidence=evidence, clock_ms=clock_ms,
    )
    result = reserve_shared_writer_envelope(
        execute=execute, query_meter=meter, reservation=reservation,
    )
    return result, meter.report()
