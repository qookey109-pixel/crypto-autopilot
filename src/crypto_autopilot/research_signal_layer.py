"""Research-only contracts for rolling candles and external forecast evidence.

This module deliberately does not fetch providers, construct an R2 client, or
emit a strategy/trade decision.  It makes the two inputs safe to evaluate:
recent candles are accepted only after close and KOL forecasts are scored only
after their target time has passed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence
from urllib.parse import urlsplit

from .lineage import assert_sha256, canonical_json


class ResearchSignalLayerError(ValueError):
    """Raised when research evidence is malformed or crosses a time boundary."""


@dataclass(frozen=True, slots=True)
class ClosedCandleRecord:
    provider: str
    symbol: str
    interval: str
    open_time_ms: int
    close_time_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    def identity(self) -> tuple[str, str, str, int]:
        return (self.provider, self.symbol, self.interval, self.open_time_ms)

    def payload(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "symbol": self.symbol,
            "interval": self.interval,
            "open_time_ms": self.open_time_ms,
            "close_time_ms": self.close_time_ms,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


@dataclass(frozen=True, slots=True)
class KOLForecast:
    forecast_id: str
    source: str
    source_url: str
    symbol: str
    direction: str
    confidence: float
    published_at_ms: int
    target_time_ms: int
    ingested_at_ms: int
    content_sha256: str

    def identity(self) -> str:
        return self.forecast_id


def _require_nonempty(value: str, label: str) -> str:
    text = str(value).strip()
    if not text:
        raise ResearchSignalLayerError(f"{label} is required")
    return text


def _finite(value: float, label: str) -> float:
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ResearchSignalLayerError(f"{label} must be finite")
    return numeric


def validate_closed_candle(record: ClosedCandleRecord, *, ingested_at_ms: int) -> None:
    """Validate one provider-separated candle without allowing an open bar."""

    _require_nonempty(record.provider, "provider")
    _require_nonempty(record.symbol, "symbol")
    _require_nonempty(record.interval, "interval")
    if record.open_time_ms < 0 or record.close_time_ms <= record.open_time_ms:
        raise ResearchSignalLayerError("candle time bounds are invalid")
    if ingested_at_ms < 0 or record.close_time_ms > ingested_at_ms:
        raise ResearchSignalLayerError("candle is not closed at ingestion time")
    opened = _finite(record.open, "open")
    high = _finite(record.high, "high")
    low = _finite(record.low, "low")
    closed = _finite(record.close, "close")
    volume = _finite(record.volume, "volume")
    if min(opened, high, low, closed) < 0 or volume < 0:
        raise ResearchSignalLayerError("candle prices and volume cannot be negative")
    if high < max(opened, closed) or low > min(opened, closed) or high < low:
        raise ResearchSignalLayerError("candle OHLC bounds are inconsistent")


def append_closed_candles(
    existing: Sequence[ClosedCandleRecord],
    incoming: Sequence[ClosedCandleRecord],
    *,
    provider: str,
    ingested_at_ms: int,
) -> tuple[ClosedCandleRecord, ...]:
    """Return an idempotent append-only candle set for one provider stream.

    Exact duplicates are harmless.  A different payload for an existing
    identity is rejected instead of silently revising historical evidence.
    """

    provider = _require_nonempty(provider, "provider")
    by_identity: dict[tuple[str, str, str, int], ClosedCandleRecord] = {}
    for record in (*existing, *incoming):
        validate_closed_candle(record, ingested_at_ms=ingested_at_ms)
        if record.provider != provider:
            raise ResearchSignalLayerError("provider stream mixing is forbidden")
        identity = record.identity()
        previous = by_identity.get(identity)
        if previous is not None and previous.payload() != record.payload():
            raise ResearchSignalLayerError("historical candle revision requires explicit authority")
        by_identity[identity] = record
    return tuple(
        sorted(
            by_identity.values(),
            key=lambda item: (item.symbol, item.interval, item.open_time_ms),
        )
    )


def validate_kol_forecast(forecast: KOLForecast) -> None:
    _require_nonempty(forecast.forecast_id, "forecast_id")
    _require_nonempty(forecast.source, "source")
    _require_nonempty(forecast.symbol, "symbol")
    parts = urlsplit(forecast.source_url)
    if parts.scheme != "https" or not parts.netloc:
        raise ResearchSignalLayerError("KOL source_url must be an HTTPS URL")
    if forecast.published_at_ms < 0 or forecast.target_time_ms <= forecast.published_at_ms:
        raise ResearchSignalLayerError("KOL forecast time bounds are invalid")
    if forecast.ingested_at_ms < forecast.published_at_ms:
        raise ResearchSignalLayerError("KOL forecast was ingested before publication")
    if forecast.direction not in {"long", "short", "neutral"}:
        raise ResearchSignalLayerError("KOL direction must be long, short or neutral")
    confidence = _finite(forecast.confidence, "confidence")
    if not 0.0 <= confidence <= 1.0:
        raise ResearchSignalLayerError("KOL confidence must be between 0 and 1")
    assert_sha256(forecast.content_sha256, "content_sha256")


def deduplicate_kol_forecasts(
    existing: Sequence[KOLForecast], incoming: Sequence[KOLForecast]
) -> tuple[KOLForecast, ...]:
    """Merge forecast evidence while rejecting same-ID content changes."""

    by_id: dict[str, KOLForecast] = {}
    for forecast in (*existing, *incoming):
        validate_kol_forecast(forecast)
        previous = by_id.get(forecast.identity())
        if previous is not None and canonical_json(previous) != canonical_json(forecast):
            raise ResearchSignalLayerError("KOL forecast revision requires explicit authority")
        by_id[forecast.identity()] = forecast
    return tuple(sorted(by_id.values(), key=lambda item: (item.published_at_ms, item.forecast_id)))


def evaluate_kol_forecasts(
    forecasts: Sequence[KOLForecast],
    outcomes: Mapping[str, tuple[int, float]],
    *,
    as_of_ms: int,
    neutral_return_epsilon: float = 0.0,
) -> dict[str, object]:
    """Score only forecasts whose target outcome is already observable.

    ``outcomes`` maps forecast ID to ``(realized_at_ms, realized_return)``.
    The result is descriptive evidence only and can never authorize promotion
    or trading.
    """

    if as_of_ms < 0 or neutral_return_epsilon < 0:
        raise ResearchSignalLayerError("invalid KOL evaluation clock or epsilon")
    evaluated: list[tuple[KOLForecast, str, float]] = []
    for forecast in forecasts:
        validate_kol_forecast(forecast)
        outcome = outcomes.get(forecast.identity())
        if outcome is None:
            continue
        realized_at_ms, realized_return = outcome
        realized_return = _finite(realized_return, "realized_return")
        if (
            realized_at_ms < forecast.target_time_ms
            or realized_at_ms <= forecast.published_at_ms
            or realized_at_ms > as_of_ms
        ):
            continue
        actual = (
            "long"
            if realized_return > neutral_return_epsilon
            else "short"
            if realized_return < -neutral_return_epsilon
            else "neutral"
        )
        evaluated.append((forecast, actual, realized_return))
    if not evaluated:
        return {
            "status": "NOT_READY",
            "evaluated_count": 0,
            "coverage": 0.0,
            "research_only": True,
            "automatic_model_promotion_authorized": False,
            "direct_trade_trigger_authorized": False,
        }
    correct = [forecast.direction == actual for forecast, actual, _ in evaluated]
    accuracy = sum(correct) / len(correct)
    confidence_error = sum(
        (forecast.confidence - (1.0 if is_correct else 0.0)) ** 2
        for (forecast, _, _), is_correct in zip(evaluated, correct)
    ) / len(correct)
    actual_directions = [actual for _, actual, _ in evaluated]
    majority_accuracy = max(
        actual_directions.count(direction) / len(actual_directions)
        for direction in {"long", "short", "neutral"}
    )
    return {
        "status": "EVALUATED",
        "evaluated_count": len(evaluated),
        "accuracy": accuracy,
        "brier_score": confidence_error,
        "majority_baseline_accuracy": majority_accuracy,
        "accuracy_lift_vs_majority": accuracy - majority_accuracy,
        "coverage": len(evaluated) / len(forecasts) if forecasts else 0.0,
        "research_only": True,
        "automatic_model_promotion_authorized": False,
        "direct_trade_trigger_authorized": False,
    }
