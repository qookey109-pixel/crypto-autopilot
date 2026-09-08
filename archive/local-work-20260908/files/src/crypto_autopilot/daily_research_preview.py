"""Offline shortlist prototype; deliberately rejects production reports."""
from __future__ import annotations

from datetime import datetime, timezone
from math import isfinite
from typing import Any, Mapping


PROVIDER = "pionex_public_futures"
INTERVAL_MS = 15 * 60 * 1000
# Engineering preview policy, not an approved production freshness threshold.
MAX_AGE_MS = 60 * 60 * 1000
DENIALS = (
    "formalTradePlanAuthorized", "pionexDemoAutomationAuthorized", "privateApiUsed",
    "r2ReadsPerformed", "r2WritesPerformed", "holdoutAccessed",
    "sourceSwitchAuthorized", "realMoneyOrderAuthorized", "liveTradingAuthorized",
)


def _time_ms(value: Any) -> int:
    if not isinstance(value, str):
        raise ValueError("timestamp_required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp_timezone_required")
    return int(parsed.timestamp() * 1000)


def build_daily_research_preview(
    report: Mapping[str, Any],
    universe: Mapping[str, Any],
    *,
    as_of_utc: str,
    minimum_score: float,
    limit: int = 5,
) -> dict[str, Any]:
    """Rank only the latest candidates, without creating plans or orders.

    Inputs use the existing paper report's latestCandidates fields. Both the
    report and universe must explicitly be synthetic fixtures. Production
    lineage, membership and execution-authority verification are not implemented.
    """
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError("invalid_display_limit")
    if type(minimum_score) not in (int, float) or not isfinite(minimum_score):
        raise ValueError("invalid_minimum_score")
    if not 0 <= minimum_score <= 100:
        raise ValueError("invalid_minimum_score")
    now = _time_ms(as_of_utc)
    output: dict[str, Any] = {
        "schema": "daily-research-preview-v0.1",
        "status": "BLOCKED",
        "mode": "SYNTHETIC_PREVIEW_ONLY",
        "asOfUtc": datetime.fromtimestamp(now / 1000, timezone.utc).isoformat(),
        "provider": PROVIDER,
        "productionReady": False,
        "authority": {key: False for key in DENIALS},
        "rankings": [],
        "excluded": [],
        "blockers": [],
        "interpretation": "合成資料流程預覽；不是今日推薦、勝率預測或交易指令。",
    }
    try:
        if report.get("dataClass") != "SYNTHETIC_FIXTURE" or universe.get(
            "dataClass"
        ) != "SYNTHETIC_FIXTURE":
            raise ValueError("production_input_not_authorized")
        if report.get("provider") != PROVIDER or universe.get("provider") != PROVIDER:
            raise ValueError("provider_mismatch")
        if report.get("schema") != "pionex-public-paper-training-run-v0.1":
            raise ValueError("unsupported_paper_report")
        if report.get("status") != "PASS" or report.get("mode") != "PAPER_TRAINING_ONLY":
            raise ValueError("paper_report_not_ready")
        authority = report.get("authority")
        if not isinstance(authority, Mapping) or any(
            authority.get(key) is not False for key in DENIALS
        ):
            raise ValueError("unsafe_or_missing_authority")
        observed = _time_ms(report.get("observedAtUtc"))
        catalog_time = _time_ms(universe.get("observedAtUtc"))
        if any(not 0 <= now - timestamp <= MAX_AGE_MS for timestamp in (observed, catalog_time)):
            raise ValueError("stale_or_future_snapshot")
        symbols = universe.get("symbols")
        if not isinstance(symbols, list) or not symbols or any(
            not isinstance(symbol, str) or not symbol.endswith("_USDT_PERP")
            for symbol in symbols
        ) or len(set(symbols)) != len(symbols):
            raise ValueError("invalid_universe")
        candidates = report.get("latestCandidates")
        if not isinstance(candidates, list):
            raise ValueError("latest_candidates_missing")
        seen: set[str] = set()
        eligible = []
        excluded = []
        for item in candidates:
            if not isinstance(item, Mapping):
                raise ValueError("malformed_candidate")
            symbol = item.get("symbol")
            if not isinstance(symbol, str) or not symbol or symbol in seen:
                raise ValueError("invalid_or_duplicate_symbol")
            seen.add(symbol)
            score = item.get("score")
            timestamp = item.get("signal_time_ms")
            reasons = item.get("reasons")
            if type(score) not in (int, float) or not isfinite(score) or not 0 <= score <= 100:
                raise ValueError("invalid_score")
            if type(timestamp) is not int or timestamp < 0 or timestamp % INTERVAL_MS:
                raise ValueError("invalid_signal_time")
            if type(item.get("eligible")) is not bool or not isinstance(reasons, (list, tuple)):
                raise ValueError("invalid_candidate_gate")
            if not reasons or any(not isinstance(reason, str) or not reason for reason in reasons):
                raise ValueError("candidate_reasons_required")
            rejection = None
            closed = timestamp + INTERVAL_MS
            if symbol not in symbols:
                rejection = "outside_pionex_preview_universe"
            elif closed > observed:
                rejection = "candle_not_closed_at_observation"
            elif now - closed > MAX_AGE_MS:
                rejection = "stale_signal"
            elif item["eligible"] is not True:
                rejection = "latest_candidate_ineligible"
            elif tuple(reasons) != ("eligible_paper_candidate",):
                rejection = "inconsistent_candidate_reasons"
            elif score < minimum_score:
                rejection = "below_existing_candidate_score_gate"
            if rejection:
                excluded.append({"symbol": symbol, "reason": rejection})
                continue
            eligible.append({
                "symbol": symbol, "score": score,
                "signalTimeMs": timestamp, "availableAtMs": closed,
                "reasons": list(reasons), "action": "RESEARCH_REVIEW_ONLY",
            })
        eligible.sort(key=lambda item: (-item["score"], item["symbol"]))
        output.update({
            "status": "PREVIEW_READY" if eligible else "WAIT_NO_ELIGIBLE_CANDIDATES",
            "rankings": [dict(item, rank=index + 1) for index, item in enumerate(eligible[:limit])],
            "eligibleCount": len(eligible),
            "omittedByDisplayLimit": max(0, len(eligible) - limit),
            "excluded": sorted(excluded, key=lambda item: item["symbol"]),
        })
    except (ValueError, TypeError, OverflowError) as error:
        output["blockers"] = [str(error)]
    return output
