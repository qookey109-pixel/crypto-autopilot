from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Protocol

from crypto_autopilot.exchanges.paper import PaperBroker
from crypto_autopilot.exchanges.pionex_public import PionexPublicClient
from crypto_autopilot.paper.account_advance_v0_1 import advance_paper_account
from crypto_autopilot.paper.checkpoint_v0_1 import (
    create_paper_loop_checkpoint,
    paper_loop_checkpoint_report_id_from_mapping,
)
from crypto_autopilot.paper.lifecycle_batch_v0_1 import (
    simulate_paper_lifecycle_batch,
    paper_lifecycle_batch_report_id_from_mapping,
)
from crypto_autopilot.paper.lifecycle_v0_1 import PaperLifecyclePolicy
from crypto_autopilot.paper.resume_v0_1 import resume_paper_loop
from crypto_autopilot.paper.run_store_v0_1 import run_store_receipt_evidence
from crypto_autopilot.paper.session_v0_1 import (
    paper_submission_session_report_id_from_mapping,
    submit_paper_cycle_session,
)


@dataclass(frozen=True, slots=True)
class LivePaperPolicy:
    """Live public-market-data + paper-only simulation authority."""

    maximum_candidates: int = 5
    maximum_source_age_ms: int = 60_000
    order_book_depth_limit: int = 20
    recent_trade_limit: int = 100
    public_live_market_data_authorized: bool = True
    live_paper_simulation_authorized: bool = True
    persistent_paper_state_authorized: bool = True
    overlapping_active_sessions_authorized: bool = False
    private_exchange_api_authorized: bool = False
    holdout_access_authorized: bool = False
    real_money_order_authorized: bool = False
    live_real_trading_authorized: bool = False

    def __post_init__(self) -> None:
        for label, value in (
            ("maximum_candidates", self.maximum_candidates),
            ("maximum_source_age_ms", self.maximum_source_age_ms),
            ("order_book_depth_limit", self.order_book_depth_limit),
            ("recent_trade_limit", self.recent_trade_limit),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"{label} must be a positive integer")
        if self.maximum_candidates > 5:
            raise ValueError("Live Paper V0.1 maximum_candidates cannot exceed five")
        if self.order_book_depth_limit > 1_000:
            raise ValueError("order_book_depth_limit cannot exceed Pionex public limit")
        if not 10 <= self.recent_trade_limit <= 500:
            raise ValueError("recent_trade_limit must be between 10 and 500")

        flags = (
            self.public_live_market_data_authorized,
            self.live_paper_simulation_authorized,
            self.persistent_paper_state_authorized,
            self.overlapping_active_sessions_authorized,
            self.private_exchange_api_authorized,
            self.holdout_access_authorized,
            self.real_money_order_authorized,
            self.live_real_trading_authorized,
        )
        if any(not isinstance(value, bool) for value in flags):
            raise ValueError("Live Paper policy flags must be booleans")
        if not self.public_live_market_data_authorized:
            raise ValueError("Live Paper V0.1 requires public live market data")
        if not self.live_paper_simulation_authorized:
            raise ValueError("Live Paper V0.1 requires paper simulation authority")
        if not self.persistent_paper_state_authorized:
            raise ValueError("Live Paper V0.1 requires paper-state persistence authority")
        if self.overlapping_active_sessions_authorized:
            raise ValueError("Live Paper V0.1 allows only one active basket/session")
        if (
            self.private_exchange_api_authorized
            or self.holdout_access_authorized
            or self.real_money_order_authorized
            or self.live_real_trading_authorized
        ):
            raise ValueError("Live Paper V0.1 cannot authorize private/real trading paths")


@dataclass(frozen=True, slots=True)
class LivePaperMarketFrame:
    provider: str
    symbol: str
    time_ms: int
    source_time_ms: int
    open: float
    high: float
    low: float
    close: float
    mark_price: float
    available_notional_usd: float
    provider_request_count: int
    source_trade_count: int

    def __post_init__(self) -> None:
        if not self.provider.strip() or not self.symbol.strip():
            raise ValueError("live market frame provider and symbol are required")
        if (
            not isinstance(self.time_ms, int)
            or isinstance(self.time_ms, bool)
            or self.time_ms < 0
        ):
            raise ValueError("live market frame time_ms must be non-negative integer")
        if (
            not isinstance(self.source_time_ms, int)
            or isinstance(self.source_time_ms, bool)
            or self.source_time_ms < 0
            or self.source_time_ms > self.time_ms
        ):
            raise ValueError("live market frame source_time_ms is invalid")
        values = (
            self.open,
            self.high,
            self.low,
            self.close,
            self.mark_price,
            self.available_notional_usd,
        )
        if any(isinstance(value, bool) for value in values):
            raise ValueError("live market frame numeric values cannot be booleans")
        if not all(math.isfinite(value) for value in values):
            raise ValueError("live market frame numeric values must be finite")
        if min(self.open, self.high, self.low, self.close, self.mark_price) <= 0.0:
            raise ValueError("live market frame prices must be positive")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("live market frame low is invalid")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("live market frame high is invalid")
        if self.available_notional_usd < 0.0:
            raise ValueError("live market frame liquidity cannot be negative")
        if (
            not isinstance(self.provider_request_count, int)
            or isinstance(self.provider_request_count, bool)
            or self.provider_request_count < 0
        ):
            raise ValueError("provider_request_count must be non-negative integer")
        if (
            not isinstance(self.source_trade_count, int)
            or isinstance(self.source_trade_count, bool)
            or self.source_trade_count < 0
        ):
            raise ValueError("source_trade_count must be non-negative integer")

    def lifecycle_bar(self) -> dict[str, object]:
        return {
            "time_ms": self.time_ms,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "available_notional_usd": self.available_notional_usd,
        }

    def mark(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "time_ms": self.time_ms,
            "price": self.mark_price,
        }


class LivePaperMarketFeed(Protocol):
    def fetch_frame(
        self,
        symbol: str,
        *,
        tick_time_ms: int,
        since_ms: int,
    ) -> LivePaperMarketFrame: ...


class PionexLivePaperFeed:
    """Public-only Pionex quote/trade normalizer for paper simulation."""

    def __init__(
        self,
        client: PionexPublicClient | None = None,
        *,
        policy: LivePaperPolicy = LivePaperPolicy(),
    ) -> None:
        self.client = client or PionexPublicClient()
        self.policy = policy

    def fetch_frame(
        self,
        symbol: str,
        *,
        tick_time_ms: int,
        since_ms: int,
    ) -> LivePaperMarketFrame:
        if tick_time_ms <= since_ms:
            raise ValueError("live paper tick must be later than lifecycle history")
        book = self.client.get_order_book(
            symbol,
            limit=self.policy.order_book_depth_limit,
        )
        trades = self.client.get_recent_trades(
            symbol,
            limit=self.policy.recent_trade_limit,
        )
        if not book.bids or not book.asks:
            raise ValueError(f"Pionex live book is empty for {symbol}")

        best_bid = max(price for price, _ in book.bids)
        best_ask = min(price for price, _ in book.asks)
        if best_bid <= 0.0 or best_ask <= 0.0 or best_bid > best_ask:
            raise ValueError(f"Pionex live book is crossed/invalid for {symbol}")

        visible_ask_notional = sum(
            price * size
            for price, size in book.asks
            if price > 0.0 and size > 0.0
        )
        midpoint = (best_bid + best_ask) / 2.0
        causal_trades = [
            trade
            for trade in trades
            if since_ms < trade.time_ms <= tick_time_ms and trade.price > 0.0
        ]
        prices = [best_bid, best_ask, midpoint] + [
            trade.price for trade in causal_trades
        ]
        open_price = causal_trades[0].price if causal_trades else best_ask
        close_price = causal_trades[-1].price if causal_trades else midpoint

        source_times = [book.update_time_ms] + [
            trade.time_ms for trade in causal_trades
        ]
        source_time_ms = max(source_times)
        if source_time_ms <= 0 or source_time_ms > tick_time_ms:
            raise ValueError("Pionex live source timestamp is not causal")
        if tick_time_ms - source_time_ms > self.policy.maximum_source_age_ms:
            raise ValueError("Pionex live market frame is stale")

        return LivePaperMarketFrame(
            provider="PIONEX_PUBLIC",
            symbol=symbol,
            time_ms=tick_time_ms,
            source_time_ms=source_time_ms,
            open=open_price,
            high=max(prices),
            low=min(prices),
            close=close_price,
            mark_price=midpoint,
            available_notional_usd=visible_ask_notional,
            provider_request_count=2,
            source_trade_count=len(causal_trades),
        )


def _canonicalize(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize(item)
            for key, item in sorted(value.items())
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    return value


def _sha256(value: object) -> str:
    encoded = json.dumps(
        _canonicalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _lifecycle_policy_from_mapping(
    payload: Mapping[str, object],
) -> PaperLifecyclePolicy:
    numeric_keys = (
        "taker_fee_bps",
        "entry_slippage_bps",
        "exit_slippage_bps",
        "maximum_bar_participation_fraction",
    )
    for key in numeric_keys:
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"live paper lifecycle policy {key} must be numeric")
    maximum_entry_bars = payload.get("maximum_entry_bars")
    if not isinstance(maximum_entry_bars, int) or isinstance(maximum_entry_bars, bool):
        raise ValueError("live paper lifecycle maximum_entry_bars must be integer")
    boolean_keys = (
        "conservative_same_bar_exit",
        "cancel_if_stop_invalidated_before_first_fill",
        "cancel_if_target_crossed_before_first_fill",
        "close_at_end_of_data",
    )
    for key in boolean_keys:
        if not isinstance(payload.get(key), bool):
            raise ValueError(f"live paper lifecycle policy {key} must be boolean")
    return PaperLifecyclePolicy(
        taker_fee_bps=float(payload["taker_fee_bps"]),
        entry_slippage_bps=float(payload["entry_slippage_bps"]),
        exit_slippage_bps=float(payload["exit_slippage_bps"]),
        maximum_bar_participation_fraction=float(
            payload["maximum_bar_participation_fraction"]
        ),
        maximum_entry_bars=maximum_entry_bars,
        conservative_same_bar_exit=payload["conservative_same_bar_exit"],
        cancel_if_stop_invalidated_before_first_fill=payload[
            "cancel_if_stop_invalidated_before_first_fill"
        ],
        cancel_if_target_crossed_before_first_fill=payload[
            "cancel_if_target_crossed_before_first_fill"
        ],
        close_at_end_of_data=payload["close_at_end_of_data"],
    )


def _state_id(
    *,
    checkpoint_id: str,
    active_session: Mapping[str, object] | None,
    last_tick_ms: int,
    lifecycle_policy: PaperLifecyclePolicy,
) -> str:
    payload = {
        "schema": "qookey-live-paper-state-id-v0.1",
        "checkpoint_id": checkpoint_id,
        "active_session_sha256": (
            None if active_session is None else _sha256(active_session)
        ),
        "last_tick_ms": last_tick_ms,
        "lifecycle_policy": asdict(lifecycle_policy),
    }
    return f"live-paper-state-v0-1-{_sha256(payload)}"


def initialize_live_paper_state(
    *,
    checkpoint_report: Mapping[str, object],
    lifecycle_policy: PaperLifecyclePolicy = PaperLifecyclePolicy(),
) -> dict[str, object]:
    checkpoint_id = checkpoint_report.get("checkpoint_id")
    if not isinstance(checkpoint_id, str) or not checkpoint_id:
        raise ValueError("checkpoint_report checkpoint_id is required")
    if paper_loop_checkpoint_report_id_from_mapping(checkpoint_report) != checkpoint_id:
        raise ValueError("checkpoint report id does not match contents")
    snapshot = checkpoint_report.get("account_snapshot")
    if not isinstance(snapshot, Mapping):
        raise ValueError("checkpoint account_snapshot is required")
    as_of_ms = snapshot.get("as_of_ms")
    if not isinstance(as_of_ms, int) or isinstance(as_of_ms, bool):
        raise ValueError("checkpoint account as_of_ms must be integer")

    state = {
        "schema": "qookey-live-paper-state-v0.1",
        "mode": "LIVE_PAPER_SIMULATION",
        "checkpoint_report": _canonicalize(checkpoint_report),
        "active_session": None,
        "last_tick_ms": as_of_ms,
        "lifecycle_policy": asdict(lifecycle_policy),
        "authority": {
            "public_live_market_data_authorized": True,
            "live_paper_simulation_authorized": True,
            "persistent_paper_state_authorized": True,
            "private_exchange_api_authorized": False,
            "holdout_access_authorized": False,
            "real_money_order_authorized": False,
            "live_real_trading_authorized": False,
        },
    }
    state["state_id"] = _state_id(
        checkpoint_id=checkpoint_id,
        active_session=None,
        last_tick_ms=as_of_ms,
        lifecycle_policy=lifecycle_policy,
    )
    return state


def _proposal_execution_map(
    session_report: Mapping[str, object],
) -> dict[str, Mapping[str, object]]:
    rows = session_report.get("paper_execution_evidence")
    if not isinstance(rows, list):
        raise ValueError("live paper session execution evidence is required")
    output: dict[str, Mapping[str, object]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("live paper session evidence row must be object")
        proposal_id = row.get("proposal_id")
        evidence = row.get("paper_execution_evidence")
        if not isinstance(proposal_id, str) or not proposal_id:
            raise ValueError("live paper session proposal_id is required")
        if not isinstance(evidence, Mapping):
            raise ValueError("live paper session execution evidence must be object")
        output[proposal_id] = evidence
    return output


def _proposal_symbol(
    evidence: Mapping[str, object],
) -> str:
    decision = evidence.get("decision")
    if not isinstance(decision, Mapping):
        raise ValueError("live paper execution decision is required")
    intent = decision.get("intent")
    if not isinstance(intent, Mapping):
        raise ValueError("live paper execution intent is required")
    symbol = intent.get("symbol")
    if not isinstance(symbol, str) or not symbol:
        raise ValueError("live paper execution intent symbol is required")
    return symbol


def _batch_status_by_proposal(
    batch: Mapping[str, object],
) -> dict[str, str]:
    rows = batch.get("results")
    if not isinstance(rows, list):
        raise ValueError("live paper batch results are required")
    output: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("live paper batch result row must be object")
        proposal_id = row.get("proposal_id")
        status = row.get("status")
        if not isinstance(proposal_id, str) or not proposal_id:
            raise ValueError("live paper batch proposal_id is required")
        if status not in {"OPEN_POSITION", "CLOSED", "CANCELLED_UNFILLED"}:
            raise ValueError("live paper batch status is invalid")
        output[proposal_id] = str(status)
    return output


def verify_live_paper_state(
    payload: Mapping[str, object],
) -> str:
    if payload.get("schema") != "qookey-live-paper-state-v0.1":
        raise ValueError("unsupported live paper state schema")
    if payload.get("mode") != "LIVE_PAPER_SIMULATION":
        raise ValueError("live paper state mode is invalid")

    checkpoint = payload.get("checkpoint_report")
    if not isinstance(checkpoint, Mapping):
        raise ValueError("live paper checkpoint_report is required")
    checkpoint_id = checkpoint.get("checkpoint_id")
    if not isinstance(checkpoint_id, str) or not checkpoint_id:
        raise ValueError("live paper checkpoint_id is required")
    if paper_loop_checkpoint_report_id_from_mapping(checkpoint) != checkpoint_id:
        raise ValueError("live paper checkpoint id mismatch")

    last_tick_ms = payload.get("last_tick_ms")
    if (
        not isinstance(last_tick_ms, int)
        or isinstance(last_tick_ms, bool)
        or last_tick_ms < 0
    ):
        raise ValueError("live paper last_tick_ms must be non-negative integer")

    lifecycle_payload = payload.get("lifecycle_policy")
    if not isinstance(lifecycle_payload, Mapping):
        raise ValueError("live paper lifecycle_policy is required")
    lifecycle_policy = _lifecycle_policy_from_mapping(lifecycle_payload)

    active = payload.get("active_session")
    if active is not None:
        if not isinstance(active, Mapping):
            raise ValueError("live paper active_session must be object/null")
        session_report = active.get("session_report")
        inputs = active.get("lifecycle_inputs")
        latest_batch = active.get("latest_batch_report")
        if not isinstance(session_report, Mapping):
            raise ValueError("live paper active session report is required")
        if not isinstance(inputs, list) or not inputs:
            raise ValueError("live paper active lifecycle_inputs are required")
        if not isinstance(latest_batch, Mapping):
            raise ValueError("live paper latest batch report is required")
        session_id = session_report.get("session_id")
        batch_id = latest_batch.get("batch_id")
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("live paper active session id is required")
        if not isinstance(batch_id, str) or not batch_id:
            raise ValueError("live paper latest batch id is required")
        if paper_submission_session_report_id_from_mapping(session_report) != session_id:
            raise ValueError("live paper active session id mismatch")
        if paper_lifecycle_batch_report_id_from_mapping(latest_batch) != batch_id:
            raise ValueError("live paper latest batch id mismatch")
        replayed = simulate_paper_lifecycle_batch(
            session_report=session_report,
            confirmation_session_id=session_id,
            lifecycle_inputs=tuple(inputs),
            lifecycle_policy=lifecycle_policy,
        )
        if _canonicalize(replayed) != _canonicalize(latest_batch):
            raise ValueError("live paper active lifecycle history does not replay")
        statuses = _batch_status_by_proposal(latest_batch)
        if "OPEN_POSITION" not in statuses.values():
            raise ValueError("live paper active_session must contain an open position")

    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise ValueError("live paper state authority object is required")
    for key in (
        "public_live_market_data_authorized",
        "live_paper_simulation_authorized",
        "persistent_paper_state_authorized",
    ):
        if authority.get(key) is not True:
            raise ValueError(f"live paper state authority missing: {key}")
    for key in (
        "private_exchange_api_authorized",
        "holdout_access_authorized",
        "real_money_order_authorized",
        "live_real_trading_authorized",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"live paper real/private authority must remain closed: {key}")

    expected = _state_id(
        checkpoint_id=checkpoint_id,
        active_session=active if isinstance(active, Mapping) else None,
        last_tick_ms=last_tick_ms,
        lifecycle_policy=lifecycle_policy,
    )
    if payload.get("state_id") != expected:
        raise ValueError("live paper state id does not match contents")
    return expected


def _parse_candidate_specs(
    payload: Sequence[object],
    *,
    maximum: int,
) -> tuple[tuple[Mapping[str, object], float], ...]:
    if len(payload) > maximum:
        raise ValueError("live paper candidate count exceeds policy maximum")
    parsed: list[tuple[Mapping[str, object], float]] = []
    identities: set[tuple[str, str, int]] = set()
    for index, raw in enumerate(payload):
        if not isinstance(raw, Mapping):
            raise ValueError(f"candidate_specs[{index}] must be an object")
        candidate = raw.get("candidate")
        target = raw.get("target_price")
        if not isinstance(candidate, Mapping):
            raise ValueError(f"candidate_specs[{index}].candidate is required")
        if isinstance(target, bool) or not isinstance(target, (int, float)):
            raise ValueError(f"candidate_specs[{index}].target_price must be numeric")
        target_price = float(target)
        if not math.isfinite(target_price) or target_price <= 0.0:
            raise ValueError(f"candidate_specs[{index}].target_price must be positive")
        symbol = candidate.get("symbol")
        family = candidate.get("strategy_family")
        as_of_ms = candidate.get("as_of_ms")
        if not isinstance(symbol, str) or not symbol:
            raise ValueError(f"candidate_specs[{index}] candidate symbol is required")
        if not isinstance(family, str) or not family:
            raise ValueError(f"candidate_specs[{index}] candidate family is required")
        if not isinstance(as_of_ms, int) or isinstance(as_of_ms, bool):
            raise ValueError(f"candidate_specs[{index}] candidate as_of_ms must be integer")
        identity = (symbol, family, as_of_ms)
        if identity in identities:
            raise ValueError("live paper candidate identity must be unique")
        identities.add(identity)
        parsed.append((candidate, target_price))
    return tuple(parsed)


def _candidate_target_map(
    parsed: Sequence[tuple[Mapping[str, object], float]],
) -> dict[tuple[str, str, int], float]:
    return {
        (
            str(candidate["symbol"]),
            str(candidate["strategy_family"]),
            int(candidate["as_of_ms"]),
        ): target
        for candidate, target in parsed
    }


def _append_live_frames(
    *,
    active_session: Mapping[str, object],
    tick_time_ms: int,
    feed: LivePaperMarketFeed,
) -> tuple[list[dict[str, object]], dict[str, LivePaperMarketFrame], int]:
    session_report = active_session["session_report"]
    inputs = active_session["lifecycle_inputs"]
    latest_batch = active_session["latest_batch_report"]
    if not isinstance(session_report, Mapping):
        raise ValueError("active session report is invalid")
    if not isinstance(inputs, list):
        raise ValueError("active lifecycle inputs are invalid")
    if not isinstance(latest_batch, Mapping):
        raise ValueError("active latest batch is invalid")

    statuses = _batch_status_by_proposal(latest_batch)
    evidence_by_proposal = _proposal_execution_map(session_report)
    frames: dict[str, LivePaperMarketFrame] = {}
    updated: list[dict[str, object]] = []
    request_count = 0

    for raw in inputs:
        if not isinstance(raw, Mapping):
            raise ValueError("active lifecycle input must be object")
        proposal_id = raw.get("proposal_id")
        if not isinstance(proposal_id, str) or not proposal_id:
            raise ValueError("active lifecycle proposal_id is required")
        row = _canonicalize(raw)
        if not isinstance(row, dict):
            raise AssertionError("canonical lifecycle input must be dict")
        bars = row.get("bars")
        if not isinstance(bars, list) or not bars:
            raise ValueError("active lifecycle history bars are required")

        if statuses.get(proposal_id) == "OPEN_POSITION":
            last_bar = bars[-1]
            if not isinstance(last_bar, Mapping):
                raise ValueError("active lifecycle last bar must be object")
            since_ms = last_bar.get("time_ms")
            if not isinstance(since_ms, int) or isinstance(since_ms, bool):
                raise ValueError("active lifecycle last bar time must be integer")
            evidence = evidence_by_proposal.get(proposal_id)
            if evidence is None:
                raise ValueError("active lifecycle proposal evidence is missing")
            symbol = _proposal_symbol(evidence)
            frame = feed.fetch_frame(
                symbol,
                tick_time_ms=tick_time_ms,
                since_ms=since_ms,
            )
            if frame.time_ms <= since_ms:
                raise ValueError("live market frame did not advance lifecycle time")
            bars.append(frame.lifecycle_bar())
            frames[proposal_id] = frame
            request_count += frame.provider_request_count
        updated.append(row)
    return updated, frames, request_count


def _marks_for_open_results(
    *,
    batch_report: Mapping[str, object],
    frames_by_proposal: Mapping[str, LivePaperMarketFrame],
    session_report: Mapping[str, object],
    tick_time_ms: int,
) -> list[dict[str, object]]:
    statuses = _batch_status_by_proposal(batch_report)
    evidence = _proposal_execution_map(session_report)
    marks_by_symbol: dict[str, float] = {}
    for proposal_id, status in statuses.items():
        if status != "OPEN_POSITION":
            continue
        frame = frames_by_proposal.get(proposal_id)
        if frame is None:
            raise ValueError("open live paper result requires a current market frame")
        symbol = _proposal_symbol(evidence[proposal_id])
        previous = marks_by_symbol.get(symbol)
        if previous is not None and not math.isclose(
            previous, frame.mark_price, rel_tol=0.0, abs_tol=1e-8
        ):
            raise ValueError("same-symbol live paper marks disagree")
        marks_by_symbol[symbol] = frame.mark_price
    return [
        {"symbol": symbol, "time_ms": tick_time_ms, "price": price}
        for symbol, price in sorted(marks_by_symbol.items())
    ]


def _new_session_inputs(
    *,
    cycle_report: Mapping[str, object],
    session_report: Mapping[str, object],
    parsed_specs: Sequence[tuple[Mapping[str, object], float]],
    tick_time_ms: int,
    feed: LivePaperMarketFeed,
) -> tuple[list[dict[str, object]], dict[str, LivePaperMarketFrame], int]:
    prepared = cycle_report.get("prepared_intents")
    if not isinstance(prepared, list) or not prepared:
        raise ValueError("ready live paper cycle prepared_intents are required")
    targets = _candidate_target_map(parsed_specs)
    inputs: list[dict[str, object]] = []
    frames: dict[str, LivePaperMarketFrame] = {}
    request_count = 0
    session_evidence = _proposal_execution_map(session_report)

    for row in prepared:
        if not isinstance(row, Mapping):
            raise ValueError("prepared live paper intent must be object")
        proposal_id = row.get("proposal_id")
        symbol = row.get("symbol")
        family = row.get("strategy_family")
        as_of_ms = row.get("as_of_ms")
        if (
            not isinstance(proposal_id, str)
            or not isinstance(symbol, str)
            or not isinstance(family, str)
            or not isinstance(as_of_ms, int)
            or isinstance(as_of_ms, bool)
        ):
            raise ValueError("prepared live paper intent identity is invalid")
        key = (symbol, family, as_of_ms)
        if key not in targets:
            raise ValueError("prepared live paper intent has no target specification")
        if tick_time_ms <= as_of_ms:
            raise ValueError("live paper market tick must be later than candidate as_of")
        evidence = session_evidence.get(proposal_id)
        if evidence is None or _proposal_symbol(evidence) != symbol:
            raise ValueError("prepared live paper intent/session evidence mismatch")

        frame = feed.fetch_frame(
            symbol,
            tick_time_ms=tick_time_ms,
            since_ms=as_of_ms,
        )
        frames[proposal_id] = frame
        request_count += frame.provider_request_count
        inputs.append(
            {
                "proposal_id": proposal_id,
                "target_price": targets[key],
                "bars": [frame.lifecycle_bar()],
            }
        )
    return inputs, frames, request_count


def _next_state(
    *,
    checkpoint_report: Mapping[str, object],
    active_session: Mapping[str, object] | None,
    tick_time_ms: int,
    lifecycle_policy: PaperLifecyclePolicy,
) -> dict[str, object]:
    checkpoint_id = checkpoint_report.get("checkpoint_id")
    if not isinstance(checkpoint_id, str) or not checkpoint_id:
        raise ValueError("next live paper checkpoint id is required")
    state = {
        "schema": "qookey-live-paper-state-v0.1",
        "mode": "LIVE_PAPER_SIMULATION",
        "checkpoint_report": _canonicalize(checkpoint_report),
        "active_session": (
            None if active_session is None else _canonicalize(active_session)
        ),
        "last_tick_ms": tick_time_ms,
        "lifecycle_policy": asdict(lifecycle_policy),
        "authority": {
            "public_live_market_data_authorized": True,
            "live_paper_simulation_authorized": True,
            "persistent_paper_state_authorized": True,
            "private_exchange_api_authorized": False,
            "holdout_access_authorized": False,
            "real_money_order_authorized": False,
            "live_real_trading_authorized": False,
        },
    }
    state["state_id"] = _state_id(
        checkpoint_id=checkpoint_id,
        active_session=(
            active_session if isinstance(active_session, Mapping) else None
        ),
        last_tick_ms=tick_time_ms,
        lifecycle_policy=lifecycle_policy,
    )
    return state


def run_live_paper_tick(
    *,
    state: Mapping[str, object],
    tick_time_ms: int,
    candidate_specs: Sequence[object],
    feed: LivePaperMarketFeed,
    policy: LivePaperPolicy = LivePaperPolicy(),
    store: object | None = None,
) -> dict[str, object]:
    """Advance one live-paper tick using public market data and paper-only execution."""

    previous_state_id = verify_live_paper_state(state)
    last_tick_ms = state.get("last_tick_ms")
    if not isinstance(last_tick_ms, int) or isinstance(last_tick_ms, bool):
        raise ValueError("live paper state last_tick_ms is invalid")
    if tick_time_ms <= last_tick_ms:
        raise ValueError("live paper tick_time_ms must strictly advance")

    lifecycle_payload = state.get("lifecycle_policy")
    if not isinstance(lifecycle_payload, Mapping):
        raise ValueError("live paper lifecycle policy is required")
    lifecycle_policy = _lifecycle_policy_from_mapping(lifecycle_payload)
    parsed_specs = _parse_candidate_specs(
        tuple(candidate_specs),
        maximum=policy.maximum_candidates,
    )

    checkpoint = state.get("checkpoint_report")
    if not isinstance(checkpoint, Mapping):
        raise ValueError("live paper checkpoint_report is required")
    current_checkpoint: Mapping[str, object] = checkpoint
    active = state.get("active_session")
    current_active: Mapping[str, object] | None = (
        active if isinstance(active, Mapping) else None
    )

    provider_requests = 0
    progressed_batch_id: str | None = None
    progressed_advance_id: str | None = None
    new_cycle_id: str | None = None
    new_session_id: str | None = None
    new_batch_id: str | None = None
    new_advance_id: str | None = None
    cycle_state: str | None = None

    if current_active is not None:
        updated_inputs, frames, requests = _append_live_frames(
            active_session=current_active,
            tick_time_ms=tick_time_ms,
            feed=feed,
        )
        provider_requests += requests
        session_report = current_active.get("session_report")
        if not isinstance(session_report, Mapping):
            raise ValueError("active live paper session_report is invalid")
        session_id = session_report.get("session_id")
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("active live paper session_id is invalid")

        updated_batch = simulate_paper_lifecycle_batch(
            session_report=session_report,
            confirmation_session_id=session_id,
            lifecycle_inputs=tuple(updated_inputs),
            lifecycle_policy=lifecycle_policy,
        )
        marks = _marks_for_open_results(
            batch_report=updated_batch,
            frames_by_proposal=frames,
            session_report=session_report,
            tick_time_ms=tick_time_ms,
        )
        advance = advance_paper_account(
            previous_account_input=current_checkpoint["next_account_input"],  # type: ignore[arg-type,index]
            lifecycle_batch_report=updated_batch,
            confirmation_batch_id=updated_batch["batch_id"],
            next_marks=tuple(marks),
        )
        current_checkpoint = create_paper_loop_checkpoint(
            account_advance_report=advance,
            confirmation_advance_id=advance["advance_id"],
        )
        progressed_batch_id = str(updated_batch["batch_id"])
        progressed_advance_id = str(advance["advance_id"])

        statuses = _batch_status_by_proposal(updated_batch)
        if "OPEN_POSITION" in statuses.values():
            current_active = {
                "session_report": _canonicalize(session_report),
                "lifecycle_inputs": updated_inputs,
                "latest_batch_report": _canonicalize(updated_batch),
            }
        else:
            current_active = None

    if parsed_specs and current_active is not None:
        next_state = _next_state(
            checkpoint_report=current_checkpoint,
            active_session=current_active,
            tick_time_ms=tick_time_ms,
            lifecycle_policy=lifecycle_policy,
        )
        tick_state = "ACTIVE_SESSION_BLOCKS_NEW_CYCLE"
    elif parsed_specs:
        resume = resume_paper_loop(
            checkpoint_report=current_checkpoint,
            confirmation_checkpoint_id=current_checkpoint["checkpoint_id"],  # type: ignore[arg-type,index]
            candidate_inputs=tuple(candidate for candidate, _ in parsed_specs),
        )
        new_cycle_id = (
            str(resume["cycle_id"]) if resume.get("cycle_id") is not None else None
        )
        cycle_state = (
            str(resume["cycle_state"])
            if resume.get("cycle_state") is not None
            else str(resume["state"])
        )
        cycle_report = resume.get("cycle_report")
        if (
            resume.get("state") == "PAPER_LOOP_RESUMED"
            and isinstance(cycle_report, Mapping)
            and cycle_report.get("state")
            == "PAPER_INTENTS_READY_FOR_EXPLICIT_SUBMISSION"
        ):
            session = submit_paper_cycle_session(
                cycle_report=cycle_report,
                confirmation_cycle_id=cycle_report["cycle_id"],  # type: ignore[arg-type,index]
                broker=PaperBroker(),
            )
            new_session_id = str(session["session_id"])
            inputs, frames, requests = _new_session_inputs(
                cycle_report=cycle_report,
                session_report=session,
                parsed_specs=parsed_specs,
                tick_time_ms=tick_time_ms,
                feed=feed,
            )
            provider_requests += requests
            batch = simulate_paper_lifecycle_batch(
                session_report=session,
                confirmation_session_id=session["session_id"],
                lifecycle_inputs=tuple(inputs),
                lifecycle_policy=lifecycle_policy,
            )
            new_batch_id = str(batch["batch_id"])
            marks = _marks_for_open_results(
                batch_report=batch,
                frames_by_proposal=frames,
                session_report=session,
                tick_time_ms=tick_time_ms,
            )
            advance = advance_paper_account(
                previous_account_input=current_checkpoint["next_account_input"],  # type: ignore[arg-type,index]
                lifecycle_batch_report=batch,
                confirmation_batch_id=batch["batch_id"],
                next_marks=tuple(marks),
            )
            new_advance_id = str(advance["advance_id"])
            current_checkpoint = create_paper_loop_checkpoint(
                account_advance_report=advance,
                confirmation_advance_id=advance["advance_id"],
            )
            statuses = _batch_status_by_proposal(batch)
            current_active = (
                {
                    "session_report": _canonicalize(session),
                    "lifecycle_inputs": inputs,
                    "latest_batch_report": _canonicalize(batch),
                }
                if "OPEN_POSITION" in statuses.values()
                else None
            )
            tick_state = (
                "LIVE_PAPER_POSITION_OPEN"
                if current_active is not None
                else "LIVE_PAPER_ROUND_TERMINAL"
            )
        else:
            tick_state = f"LIVE_PAPER_CYCLE_{cycle_state}"
        next_state = _next_state(
            checkpoint_report=current_checkpoint,
            active_session=current_active,
            tick_time_ms=tick_time_ms,
            lifecycle_policy=lifecycle_policy,
        )
    else:
        next_state = _next_state(
            checkpoint_report=current_checkpoint,
            active_session=current_active,
            tick_time_ms=tick_time_ms,
            lifecycle_policy=lifecycle_policy,
        )
        tick_state = (
            "LIVE_PAPER_POSITION_UPDATED"
            if progressed_batch_id is not None
            else "LIVE_PAPER_HEARTBEAT"
        )

    storage_receipt = None
    persistent_writes = 0
    if store is not None:
        put_json = getattr(store, "put_json", None)
        if put_json is None:
            raise ValueError("paper run store must implement put_json()")
        receipt = put_json("live-state", next_state["state_id"], next_state)
        storage_receipt = run_store_receipt_evidence(receipt)
        persistent_writes = 0 if receipt.replayed else 1

    tick_payload = {
        "schema": "qookey-live-paper-tick-id-v0.1",
        "previous_state_id": previous_state_id,
        "next_state_id": next_state["state_id"],
        "tick_time_ms": tick_time_ms,
        "progressed_batch_id": progressed_batch_id,
        "progressed_advance_id": progressed_advance_id,
        "new_cycle_id": new_cycle_id,
        "new_session_id": new_session_id,
        "new_batch_id": new_batch_id,
        "new_advance_id": new_advance_id,
    }
    tick_id = f"live-paper-tick-v0-1-{_sha256(tick_payload)}"
    return {
        "schema": "qookey-live-paper-tick-report-v0.1",
        "tick_id": tick_id,
        "state": tick_state,
        "tick_time_ms": tick_time_ms,
        "previous_state_id": previous_state_id,
        "next_state_id": next_state["state_id"],
        "progressed_batch_id": progressed_batch_id,
        "progressed_advance_id": progressed_advance_id,
        "cycle_id": new_cycle_id,
        "cycle_state": cycle_state,
        "session_id": new_session_id,
        "batch_id": new_batch_id,
        "advance_id": new_advance_id,
        "checkpoint_id": current_checkpoint["checkpoint_id"],
        "provider_requests_performed": provider_requests,
        "persistent_state_writes_performed": persistent_writes,
        "storage_receipt": storage_receipt,
        "next_state": next_state,
        "authority": {
            "public_live_market_data_authorized": True,
            "live_paper_simulation_authorized": True,
            "persistent_paper_state_authorized": True,
            "overlapping_active_sessions_authorized": False,
            "private_exchange_api_authorized": False,
            "holdout_access_authorized": False,
            "real_money_order_authorized": False,
            "live_real_trading_authorized": False,
        },
        "limitations": [
            "V0.1 allows one active basket/session at a time.",
            "Candidate generation/ranking remains upstream and explicit.",
            "Pionex visible ask depth is normalized as paper entry liquidity.",
            "No private account/order endpoint is present or authorized.",
        ],
    }



def live_paper_tick_report_id_from_mapping(
    payload: Mapping[str, object],
) -> str:
    """Validate and recompute one serialized Live Paper tick report id."""

    if payload.get("schema") != "qookey-live-paper-tick-report-v0.1":
        raise ValueError("unsupported live paper tick report schema")
    tick_id = payload.get("tick_id")
    state_name = payload.get("state")
    previous_state_id = payload.get("previous_state_id")
    next_state_id = payload.get("next_state_id")
    if not isinstance(tick_id, str) or not tick_id:
        raise ValueError("live paper tick_id is required")
    if not isinstance(state_name, str) or not state_name:
        raise ValueError("live paper tick state is required")
    if not isinstance(previous_state_id, str) or not previous_state_id:
        raise ValueError("live paper previous_state_id is required")
    if not isinstance(next_state_id, str) or not next_state_id:
        raise ValueError("live paper next_state_id is required")

    tick_time_ms = payload.get("tick_time_ms")
    if (
        not isinstance(tick_time_ms, int)
        or isinstance(tick_time_ms, bool)
        or tick_time_ms < 0
    ):
        raise ValueError("live paper tick_time_ms must be non-negative integer")

    next_state = payload.get("next_state")
    if not isinstance(next_state, Mapping):
        raise ValueError("live paper tick next_state is required")
    if verify_live_paper_state(next_state) != next_state_id:
        raise ValueError("live paper tick next_state id mismatch")
    if next_state.get("last_tick_ms") != tick_time_ms:
        raise ValueError("live paper tick time does not match next state")

    checkpoint = next_state.get("checkpoint_report")
    if not isinstance(checkpoint, Mapping):
        raise ValueError("live paper tick checkpoint payload is required")
    if payload.get("checkpoint_id") != checkpoint.get("checkpoint_id"):
        raise ValueError("live paper tick checkpoint id mismatch")

    optional_ids = (
        "progressed_batch_id",
        "progressed_advance_id",
        "cycle_id",
        "session_id",
        "batch_id",
        "advance_id",
    )
    for key in optional_ids:
        value = payload.get(key)
        if value is not None and (not isinstance(value, str) or not value):
            raise ValueError(f"live paper tick {key} must be string/null")

    cycle_state = payload.get("cycle_state")
    if cycle_state is not None and (
        not isinstance(cycle_state, str) or not cycle_state
    ):
        raise ValueError("live paper tick cycle_state must be string/null")

    provider_requests = payload.get("provider_requests_performed")
    persistent_writes = payload.get("persistent_state_writes_performed")
    if (
        not isinstance(provider_requests, int)
        or isinstance(provider_requests, bool)
        or provider_requests < 0
    ):
        raise ValueError("live paper provider request count is invalid")
    if (
        not isinstance(persistent_writes, int)
        or isinstance(persistent_writes, bool)
        or persistent_writes < 0
    ):
        raise ValueError("live paper persistent write count is invalid")

    receipt = payload.get("storage_receipt")
    if receipt is None:
        if persistent_writes != 0:
            raise ValueError("live paper tick reports writes without storage receipt")
    elif not isinstance(receipt, Mapping):
        raise ValueError("live paper storage_receipt must be object/null")

    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise ValueError("live paper tick authority object is required")
    for key in (
        "public_live_market_data_authorized",
        "live_paper_simulation_authorized",
        "persistent_paper_state_authorized",
    ):
        if authority.get(key) is not True:
            raise ValueError(f"live paper tick authority missing: {key}")
    if authority.get("overlapping_active_sessions_authorized") is not False:
        raise ValueError("live paper overlapping sessions must remain closed")
    for key in (
        "private_exchange_api_authorized",
        "holdout_access_authorized",
        "real_money_order_authorized",
        "live_real_trading_authorized",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"live paper tick authority must remain closed: {key}")

    tick_payload = {
        "schema": "qookey-live-paper-tick-id-v0.1",
        "previous_state_id": previous_state_id,
        "next_state_id": next_state_id,
        "tick_time_ms": tick_time_ms,
        "progressed_batch_id": payload.get("progressed_batch_id"),
        "progressed_advance_id": payload.get("progressed_advance_id"),
        "new_cycle_id": payload.get("cycle_id"),
        "new_session_id": payload.get("session_id"),
        "new_batch_id": payload.get("batch_id"),
        "new_advance_id": payload.get("advance_id"),
    }
    return f"live-paper-tick-v0-1-{_sha256(tick_payload)}"


def live_paper_policy_from_config(
    payload: Mapping[str, object],
) -> LivePaperPolicy:
    if payload.get("schema") != "qookey-live-paper-simulation-v0.1":
        raise ValueError("unsupported live paper simulation config")
    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("policy object is required")
    integer_keys = (
        "maximum_candidates",
        "maximum_source_age_ms",
        "order_book_depth_limit",
        "recent_trade_limit",
    )
    for key in integer_keys:
        if not isinstance(policy.get(key), int) or isinstance(policy.get(key), bool):
            raise ValueError(f"policy.{key} must be a JSON integer")
    boolean_keys = (
        "public_live_market_data_authorized",
        "live_paper_simulation_authorized",
        "persistent_paper_state_authorized",
        "overlapping_active_sessions_authorized",
        "private_exchange_api_authorized",
        "holdout_access_authorized",
        "real_money_order_authorized",
        "live_real_trading_authorized",
    )
    for key in boolean_keys:
        if not isinstance(policy.get(key), bool):
            raise ValueError(f"policy.{key} must be a JSON boolean")
    return LivePaperPolicy(
        maximum_candidates=policy["maximum_candidates"],
        maximum_source_age_ms=policy["maximum_source_age_ms"],
        order_book_depth_limit=policy["order_book_depth_limit"],
        recent_trade_limit=policy["recent_trade_limit"],
        public_live_market_data_authorized=policy[
            "public_live_market_data_authorized"
        ],
        live_paper_simulation_authorized=policy[
            "live_paper_simulation_authorized"
        ],
        persistent_paper_state_authorized=policy[
            "persistent_paper_state_authorized"
        ],
        overlapping_active_sessions_authorized=policy[
            "overlapping_active_sessions_authorized"
        ],
        private_exchange_api_authorized=policy["private_exchange_api_authorized"],
        holdout_access_authorized=policy["holdout_access_authorized"],
        real_money_order_authorized=policy["real_money_order_authorized"],
        live_real_trading_authorized=policy["live_real_trading_authorized"],
    )


def live_paper_tick_input_from_dict(
    payload: Mapping[str, object],
) -> tuple[Mapping[str, object], int, tuple[object, ...]]:
    if payload.get("schema") != "qookey-live-paper-tick-input-v0.1":
        raise ValueError("unsupported live paper tick input schema")
    state = payload.get("state")
    tick_time_ms = payload.get("tick_time_ms")
    candidate_specs = payload.get("candidate_specs")
    if not isinstance(state, Mapping):
        raise ValueError("live paper tick state object is required")
    if (
        not isinstance(tick_time_ms, int)
        or isinstance(tick_time_ms, bool)
        or tick_time_ms < 0
    ):
        raise ValueError("live paper tick_time_ms must be non-negative integer")
    if not isinstance(candidate_specs, list):
        raise ValueError("live paper candidate_specs must be a JSON array")
    return state, tick_time_ms, tuple(candidate_specs)
