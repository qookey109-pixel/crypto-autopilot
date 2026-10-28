"""Research-only closed-bar prefix replay; no data access or trading authority.

Caller-supplied candles and their source identity are not authenticated here.
A prefix calculation is not proof of predictive edge or original archive provenance.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import asdict

from crypto_autopilot.models import Candle
from crypto_autopilot.research.technical_pattern_detectors_v0_1 import (
    build_technical_pattern_series,
)
from crypto_autopilot.technical import TechnicalDataError, build_technical_series

HOUR_MS = 3_600_000
MAX_CANDLES = 10_000
MIN_CANDLES = 50


def replay_60m_at_cutoff(candles: Sequence[Candle], cutoff_ms: int) -> dict[str, object]:
    """Compute a research snapshot using only bars closed at the decision cutoff."""
    if type(cutoff_ms) is not int or cutoff_ms <= 0:
        raise ValueError("invalid cutoff")
    if not 0 < len(candles) <= MAX_CANDLES:
        raise ValueError("invalid candle count")
    previous = -1
    prefix: list[Candle] = []
    for candle in candles:
        if (
            not isinstance(candle, Candle)
            or type(candle.time_ms) is not int
            or candle.time_ms < 0
            or candle.time_ms <= previous
        ):
            raise ValueError("unordered, invalid or duplicate candle")
        previous = candle.time_ms
        if candle.time_ms + HOUR_MS <= cutoff_ms:
            prefix.append(candle)
    if len(prefix) < MIN_CANDLES:
        raise ValueError("insufficient closed bars")
    try:
        technical = build_technical_series(prefix, "60M")
        if not technical[-1].ready:
            raise ValueError("indicators not warmed")
        patterns = build_technical_pattern_series(prefix, "60M", technical_series=technical)
    except TechnicalDataError as exc:
        raise ValueError("invalid or non-contiguous closed bars") from exc

    source_bytes = json.dumps(
        [asdict(row) for row in prefix], sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return {
        "schema": "qookey-causal-prefix-replay-v0.1",
        "status": "RESEARCH_ONLY",
        "decision_cutoff_ms": cutoff_ms,
        "source": {
            "provider": None,
            "symbol": None,
            "externally_authenticated": False,
            "candle_count": len(prefix),
            "last_closed_bar_start_ms": prefix[-1].time_ms,
            "prefix_sha256": hashlib.sha256(source_bytes).hexdigest(),
        },
        "technical": asdict(technical[-1]),
        "technical_v0_2_fully_warmed": technical[-1].ready_v0_2,
        "patterns": asdict(patterns[-1]),
        "timeframes": {"15M": "UNKNOWN", "4H": "UNKNOWN"},
        "costs": {"fees": None, "slippage": None, "funding": None, "net_return": None},
        "authority": {
            "strategy_qualification": False,
            "paper_submission": False,
            "model_promotion": False,
            "real_money": False,
        },
    }
