"""Fail-closed adapter for TradingAgents research output.

The adapter deliberately does not import or execute TradingAgents, call an LLM,
fetch market data, or submit an order.  It normalizes a secret-free export into
descriptive Research Context evidence so the upstream rating can be evaluated as
a challenger without becoming strategy or execution authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

from crypto_autopilot.lineage import assert_no_secret_fields, sha256_bytes, sha256_json
from crypto_autopilot.research.context import ContextObservation


class TradingAgentsChallengerError(ValueError):
    """Raised when an upstream export is incomplete or crosses a boundary."""


SCHEMA = "tradingagents-research-candidate-v0.1"
UPSTREAM_REPOSITORY = "https://github.com/TauricResearch/TradingAgents"
ALLOWED_RATINGS = {
    "BUY": 2.0,
    "OVERWEIGHT": 1.0,
    "HOLD": 0.0,
    "UNDERWEIGHT": -1.0,
    "SELL": -2.0,
}
REQUIRED_REPORTS = (
    "market_report",
    "bull_case",
    "bear_case",
    "investment_plan",
    "risk_report",
    "final_trade_decision",
)
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_TOP_LEVEL_FIELDS = frozenset(
    {
        "schema",
        "run_id",
        "upstream",
        "symbol",
        "upstream_ticker",
        "data_provider",
        "analysis_date",
        "decision_at_ms",
        "data_cutoff_ms",
        "rating",
        "point_in_time_verified",
        "reports",
        "evidence_urls",
        "authority",
    }
)


@dataclass(frozen=True, slots=True)
class TradingAgentsCandidate:
    run_id: str
    upstream_version: str
    upstream_commit: str
    symbol: str
    upstream_ticker: str
    data_provider: str
    analysis_date: str
    decision_at_ms: int
    data_cutoff_ms: int
    rating: str
    report_sha256: tuple[tuple[str, str], ...]
    evidence_urls: tuple[str, ...]
    payload_sha256: str

    def evidence(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "status": "RESEARCH_CANDIDATE_READY",
            "run_id": self.run_id,
            "upstream": {
                "repository": UPSTREAM_REPOSITORY,
                "version": self.upstream_version,
                "commit": self.upstream_commit,
            },
            "symbol": self.symbol,
            "upstream_ticker": self.upstream_ticker,
            "data_provider": self.data_provider,
            "analysis_date": self.analysis_date,
            "decision_at_ms": self.decision_at_ms,
            "data_cutoff_ms": self.data_cutoff_ms,
            "rating": self.rating,
            "rating_ordinal": ALLOWED_RATINGS[self.rating],
            "report_sha256": dict(self.report_sha256),
            "report_count": len(self.report_sha256),
            "evidence_urls": list(self.evidence_urls),
            "payload_sha256": self.payload_sha256,
            "research_only": True,
            "upstream_reports_are_untrusted": True,
            "composite_score": None,
            "source_switch_authorized": False,
            "holdout_accessed": False,
            "automatic_model_promotion_authorized": False,
            "direct_trade_trigger_authorized": False,
            "trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        }

    def context_observation(self) -> ContextObservation:
        """Project the candidate into the existing descriptive context layer."""

        return ContextObservation.from_mapping(
            source_id="tradingagents_research_challenger_v0_1",
            symbol=self.symbol,
            horizon="daily",
            as_of_ms=self.decision_at_ms,
            source_urls=self.evidence_urls,
            values={
                "upstream_rating_ordinal": ALLOWED_RATINGS[self.rating],
                "upstream_report_count": float(len(self.report_sha256)),
            },
            freshness_status="VERIFIED",
        )


def _text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise TradingAgentsChallengerError(f"{label} is required")
    return text


def _timestamp(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise TradingAgentsChallengerError(f"{label} must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise TradingAgentsChallengerError(f"{label} must be an integer") from exc
    if parsed < 0:
        raise TradingAgentsChallengerError(f"{label} must be non-negative")
    return parsed


def _https_urls(values: Sequence[Any]) -> tuple[str, ...]:
    urls = tuple(_text(value, "evidence_url") for value in values)
    if not urls:
        raise TradingAgentsChallengerError("at least one evidence_url is required")
    for url in urls:
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.netloc:
            raise TradingAgentsChallengerError("evidence URLs must use HTTPS")
    return urls


def ingest_tradingagents_candidate(
    payload: Mapping[str, Any],
    *,
    as_of_ms: int,
    allowed_symbols: Sequence[str] | None = None,
    expected_data_provider: str | None = None,
) -> TradingAgentsCandidate:
    """Validate one upstream export without performing I/O.

    Reports are reduced to SHA-256 digests.  Their prose remains untrusted and
    cannot become a score, strategy mutation, trade plan, or provider evidence.
    """

    if not isinstance(payload, Mapping):
        raise TradingAgentsChallengerError("payload must be an object")
    assert_no_secret_fields(payload, path="tradingagents_candidate")
    unexpected = sorted(str(name) for name in payload if name not in _TOP_LEVEL_FIELDS)
    if unexpected:
        raise TradingAgentsChallengerError(
            f"unexpected top-level fields are forbidden: {', '.join(unexpected)}"
        )
    if payload.get("schema") != SCHEMA:
        raise TradingAgentsChallengerError("unsupported TradingAgents candidate schema")

    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise TradingAgentsChallengerError("authority object is required")
    forbidden_true = (
        "holdout_accessed",
        "source_switch_authorized",
        "trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    )
    if any(authority.get(name) is not False for name in forbidden_true):
        raise TradingAgentsChallengerError("all protected authority flags must be explicitly false")
    if payload.get("point_in_time_verified") is not True:
        raise TradingAgentsChallengerError("point_in_time_verified must be true")

    upstream = payload.get("upstream")
    if not isinstance(upstream, Mapping):
        raise TradingAgentsChallengerError("upstream object is required")
    if upstream.get("repository") != UPSTREAM_REPOSITORY:
        raise TradingAgentsChallengerError("unexpected upstream repository")
    upstream_version = _text(upstream.get("version"), "upstream.version")
    upstream_commit = _text(upstream.get("commit"), "upstream.commit").lower()
    if not _COMMIT.fullmatch(upstream_commit):
        raise TradingAgentsChallengerError("upstream.commit must be a 40-character Git SHA")

    run_id = _text(payload.get("run_id"), "run_id")
    symbol = _text(payload.get("symbol"), "symbol")
    upstream_ticker = _text(payload.get("upstream_ticker"), "upstream_ticker")
    data_provider = _text(payload.get("data_provider"), "data_provider")
    if allowed_symbols is not None and symbol not in set(allowed_symbols):
        raise TradingAgentsChallengerError("symbol is outside the allowed research universe")
    if expected_data_provider is not None and data_provider != expected_data_provider:
        raise TradingAgentsChallengerError("data provider does not match the expected lineage")

    analysis_date = _text(payload.get("analysis_date"), "analysis_date")
    try:
        parsed_analysis_date = date.fromisoformat(analysis_date)
    except ValueError as exc:
        raise TradingAgentsChallengerError("analysis_date must use YYYY-MM-DD") from exc
    decision_at_ms = _timestamp(payload.get("decision_at_ms"), "decision_at_ms")
    data_cutoff_ms = _timestamp(payload.get("data_cutoff_ms"), "data_cutoff_ms")
    if decision_at_ms > _timestamp(as_of_ms, "as_of_ms"):
        raise TradingAgentsChallengerError("future TradingAgents decision is not allowed")
    if data_cutoff_ms > decision_at_ms:
        raise TradingAgentsChallengerError("data cutoff cannot be after the decision")
    cutoff_date = datetime.fromtimestamp(data_cutoff_ms / 1000, tz=timezone.utc).date()
    if cutoff_date > parsed_analysis_date:
        raise TradingAgentsChallengerError("data cutoff cannot be after the analysis date")

    rating = _text(payload.get("rating"), "rating").upper()
    if rating not in ALLOWED_RATINGS:
        raise TradingAgentsChallengerError("rating must use the five-tier contract")
    reports = payload.get("reports")
    if not isinstance(reports, Mapping):
        raise TradingAgentsChallengerError("reports object is required")
    unexpected_reports = sorted(str(name) for name in reports if name not in REQUIRED_REPORTS)
    if unexpected_reports:
        raise TradingAgentsChallengerError(
            f"unexpected report fields are forbidden: {', '.join(unexpected_reports)}"
        )
    report_digests: list[tuple[str, str]] = []
    for name in REQUIRED_REPORTS:
        report = _text(reports.get(name), f"reports.{name}")
        if len(report) > 50_000:
            raise TradingAgentsChallengerError(f"reports.{name} exceeds the 50000 character cap")
        report_digests.append((name, sha256_bytes(report.encode("utf-8"))))

    evidence_urls = _https_urls(payload.get("evidence_urls") or ())
    payload_sha256 = sha256_json(payload)
    return TradingAgentsCandidate(
        run_id=run_id,
        upstream_version=upstream_version,
        upstream_commit=upstream_commit,
        symbol=symbol,
        upstream_ticker=upstream_ticker,
        data_provider=data_provider,
        analysis_date=analysis_date,
        decision_at_ms=decision_at_ms,
        data_cutoff_ms=data_cutoff_ms,
        rating=rating,
        report_sha256=tuple(report_digests),
        evidence_urls=evidence_urls,
        payload_sha256=payload_sha256,
    )
