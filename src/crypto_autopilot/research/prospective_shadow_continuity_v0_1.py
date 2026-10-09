"""Pure, fail-closed cross-batch continuity checks for Shadow collection reports.

No GitHub API, artifact download, local checkout, network, R2, D1 or trading.
Callers must authenticate original artifact ZIP digests and run identities
independently; self-consistent JSON is not external source attestation.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence

HOUR_MS = 3_600_000
MAX_REPORTS = 100
EXPECTED_CANDLES = 240
EXPECTED_MARKETS = 5
CONTEXT_WARMUP_OBSERVATIONS = 21
_REPORT_SCHEMA = "qookey-prospective-shadow-collection-execution-report-v0.1"
_RECORD_SCHEMA = "qookey-prospective-shadow-collection-run-v0.1"
_FORBIDDEN = (
    "r2_accessed", "d1_accessed", "holdout_accessed", "training_performed",
    "model_promotion_performed", "paper_submission_performed",
    "real_money_order_performed", "live_trading_performed",
)


class ContinuityReviewRequired(ValueError):
    """Unsafe or inconsistent caller-supplied Shadow batch data."""


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise ContinuityReviewRequired(reason)


def _canonical_hash(value: object) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _integer(value: object) -> bool:
    return type(value) is int


def _validate_report(report: object) -> dict[str, object]:
    _require(isinstance(report, Mapping), "INVALID_REPORT")
    _require(report.get("schema") == _REPORT_SCHEMA, "REPORT_SCHEMA")
    _require(report.get("status") == "PASS", "COLLECTOR_STATUS")
    github = report.get("github")
    _require(isinstance(github, Mapping), "MISSING_GITHUB_PROVENANCE")
    _require(
        github.get("event_name") == "schedule"
        and github.get("ref") == "refs/heads/main"
        and isinstance(github.get("sha"), str)
        and len(github["sha"]) == 40
        and all(c in "0123456789abcdef" for c in github["sha"]),
        "UNEXPECTED_GITHUB_CONTEXT",
    )
    run_id = github.get("run_id")
    _require(
        isinstance(run_id, str) and run_id.isdecimal()
        and int(run_id) > 0 and github.get("run_attempt") == "1",
        "UNEXPECTED_RUN_ATTEMPT",
    )
    requests = report.get("provider_requests")
    _require(
        isinstance(requests, Mapping)
        and tuple(requests.get(k) for k in ("pionex", "coinpaprika", "total"))
        == (8, 2, 10),
        "PROVIDER_REQUEST_BUDGET",
    )
    authority = report.get("authority")
    _require(
        isinstance(authority, Mapping)
        and authority.get("artifact_only_persistence") is True
        and all(authority.get(k) is False for k in _FORBIDDEN),
        "EXECUTION_AUTHORITY",
    )
    record = report.get("collection")
    _require(
        isinstance(record, Mapping) and record.get("schema") == _RECORD_SCHEMA,
        "COLLECTION_SCHEMA",
    )
    identity = record.get("record_id")
    _require(
        isinstance(identity, str)
        and identity == _canonical_hash({k: v for k, v in record.items() if k != "record_id"}),
        "RECORD_HASH",
    )
    capture = record.get("capture_timestamp_ms")
    _require(_integer(capture) and capture > 0, "CAPTURE_TIMESTAMP")
    summary = record.get("universe_summary")
    markets = record.get("market_evidence")
    _require(
        isinstance(summary, Mapping) and isinstance(markets, list)
        and len(markets) == EXPECTED_MARKETS,
        "MARKET_COVERAGE",
    )
    symbols = summary.get("top5_symbols")
    _require(
        isinstance(symbols, list) and len(symbols) == EXPECTED_MARKETS
        and all(isinstance(s, str) and s for s in symbols)
        and len(set(symbols)) == EXPECTED_MARKETS,
        "SYMBOL_COVERAGE",
    )
    _require([x.get("symbol") if isinstance(x, Mapping) else None for x in markets] == symbols, "SYMBOL_LINEAGE")
    _require(isinstance(record.get("context_snapshot"), Mapping), "MISSING_CONTEXT")
    regime = record.get("regime_observation_input")
    _require(
        isinstance(regime, Mapping)
        and regime.get("breadth_scope") == "TOP5_GOVERNED_SCAN_RESEARCH_PROXY"
        and regime.get("production_regime_equivalence_claimed") is False
        and regime.get("time_ms") == capture
        and regime.get("available_at_ms") == capture,
        "REGIME_PROXY_SCOPE",
    )
    replay = record.get("replay_state")
    _require(
        isinstance(replay, Mapping)
        and replay.get("signal_selection_performed_in_collector") is False
        and replay.get("outcome_evaluation_performed_in_collector") is False
        and replay.get("future_replay_must_use_only_artifacts_available_at_signal_time") is True,
        "REPLAY_BOUNDARY",
    )
    comp = record.get("comparison_source")
    _require(
        isinstance(comp, Mapping)
        and comp.get("status") == "UNAVAILABLE",
        "UNAUTHORIZED_COMPARISON",
    )
    scope = record.get("authority")
    _require(
        isinstance(scope, Mapping)
        and scope.get("research_collection_only") is True
        and all(scope.get(k) is False for k in _FORBIDDEN)
        and all(scope.get(k) is False for k in (
            "candidate_reranking_changed", "strategy_router_threshold_changed",
            "raw_provider_payload_persisted",
        )),
        "COLLECTION_AUTHORITY",
    )
    validated_markets: dict[str, dict[int, str]] = {}
    closed_ends: list[int] = []
    for row in markets:
        candles = row.get("candles_60m")
        _require(
            isinstance(candles, list) and len(candles) == EXPECTED_CANDLES,
            "CANDLE_COVERAGE",
        )
        times = [
            c.get("time_ms") if isinstance(c, Mapping) else None for c in candles
        ]
        _require(all(_integer(t) for t in times), "CANDLE_TIME_TYPE")
        _require(
            all(b - a == HOUR_MS for a, b in zip(times, times[1:])),
            "CANDLE_GAP_OR_DUPLICATE",
        )
        _require(times[-1] + HOUR_MS <= capture, "UNCLOSED_OR_FUTURE_CANDLE")
        _require(row.get("candles_sha256") == _canonical_hash(candles), "CANDLE_HASH")
        _require(
            all(isinstance(row.get(k), Mapping) for k in (
                "technical", "structure", "patterns", "market_event_radar",
                "universe_market",
            )),
            "FEATURE_COVERAGE",
        )
        for feature in ("technical", "structure", "patterns"):
            available = row[feature].get("available_at_ms")
            _require(
                available is None or (_integer(available) and available <= capture),
                "FUTURE_FEATURE",
            )
        symbol = row["symbol"]
        validated_markets[symbol] = {
            c["time_ms"]: _canonical_hash(c) for c in candles
        }
        closed_ends.append(times[-1] + HOUR_MS)
    return {
        "run_id": int(run_id),
        "capture_timestamp_ms": capture,
        "record_id": identity,
        "symbols": tuple(symbols),
        "candles": validated_markets,
        "max_source_lag_ms": capture - min(closed_ends),
    }


def inspect_shadow_batch_continuity(
    reports: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Inspect caller-supplied reports; never confer production or provider authority.

    The observations are NOT authenticated GitHub artifacts. The caller must
    separately verify the archive digest, exact run identity and available time.
    All results are research diagnostics, never a model-quality gate.
    """
    _require(
        isinstance(reports, (tuple, list))
        and 1 <= len(reports) <= MAX_REPORTS,
        "BATCH_COUNT",
    )
    records = [_validate_report(record) for record in reports]
    records.sort(key=lambda row: row["capture_timestamp_ms"])
    ids = [row["run_id"] for row in records]
    captures = [row["capture_timestamp_ms"] for row in records]
    _require(len(set(ids)) == len(ids), "DUPLICATE_RUN_ID")
    _require(len(set(captures)) == len(captures), "DUPLICATE_CAPTURE_TIME")
    _require(
        len(set(row["record_id"] for row in records)) == len(records),
        "DUPLICATE_RECORD_ID",
    )
    # Identical historical candles must not mutate between immutable reports.
    shared_candles = 0
    for earlier, later in zip(records, records[1:]):
        for symbol in set(earlier["symbols"]) & set(later["symbols"]):
            c1, c2 = earlier["candles"][symbol], later["candles"][symbol]
            for stamp in c1.keys() & c2.keys():
                shared_candles += 1
                _require(c1[stamp] == c2[stamp], "REVISED_OVERLAPPING_CANDLE")
    gaps = [
        {"before_run": earlier["run_id"], "after_run": later["run_id"],
         "elapsed_minutes": (later["capture_timestamp_ms"] - earlier["capture_timestamp_ms"]) // 60_000}
        for earlier, later in zip(records, records[1:])
        if later["capture_timestamp_ms"] - earlier["capture_timestamp_ms"] > 6 * HOUR_MS
    ]
    max_source_lag = max(row["max_source_lag_ms"] for row in records)
    return {
        "schema": "qookey-shadow-batch-continuity-diagnostic-v0.1",
        "status": "REVIEW_REQUIRED" if gaps or max_source_lag > 3 * HOUR_MS else "PARTIAL_OBSERVATION_ONLY",
        "mode": "CALLER_SUPPLIED_CONTENT_SELF_CONSISTENCY_ONLY",
        "source_archive_digests_authenticated": False,
        "github_run_metadata_authenticated": False,
        "research_only": True,
        "execution_authority": False,
        "production_eligibility_proven": False,
        "model_quality_promotion_authorized": False,
        "outcome_predictive_edge_proven": False,
        "report_count": len(records),
        "run_ids": ids,
        "observed_first_capture_timestamp_ms": captures[0],
        "observed_last_capture_timestamp_ms": captures[-1],
        "distinct_context_observations": len(captures),
        "context_warmup_state": (
            "COUNT_REACHED_NOT_VALIDATED" if len(captures) >= CONTEXT_WARMUP_OBSERVATIONS
            else "INSUFFICIENT"
        ),
        "shared_overlapping_candles_consistent": shared_candles,
        "symbol_rotation_allowed": True,
        "observed_gap_count": len(gaps),
        "observed_gaps": gaps,
        "maximum_source_lag_minutes": max_source_lag // 60_000,
        "full_schedule_coverage_proven": False,
        "signal_outcome_evaluation_performed": False,
    }
