"""Provider-neutral research context contracts.

The context layer stores descriptive evidence from multi-timeframe technical,
market-force and cycle-radar sources.  It is deliberately a pure, offline
adapter: it does not fetch a website, infer a direction from prose, or emit a
trade plan.  A future, separately authorized ingestion job may materialize
these observations after validating source freshness and timestamps.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence
from urllib.parse import urlsplit


class ResearchContextError(ValueError):
    """Raised when a context observation is malformed or time-unsafe."""


ALLOWED_HORIZONS = frozenset(
    {"intraday", "daily", "weekly", "monthly", "quarterly", "annual"}
)
ALLOWED_FRESHNESS = frozenset({"VERIFIED", "CACHED", "PARTIAL", "UNAVAILABLE"})


@dataclass(frozen=True, slots=True)
class ContextObservation:
    """One timestamped descriptive observation from one declared source."""

    source_id: str
    symbol: str
    horizon: str
    as_of_ms: int
    source_urls: tuple[str, ...]
    values: tuple[tuple[str, float | None], ...]
    freshness_status: str = "VERIFIED"

    @classmethod
    def from_mapping(
        cls,
        *,
        source_id: str,
        symbol: str,
        horizon: str,
        as_of_ms: int,
        source_urls: Sequence[str],
        values: Mapping[str, float | None],
        freshness_status: str = "VERIFIED",
    ) -> "ContextObservation":
        return cls(
            source_id=source_id,
            symbol=symbol,
            horizon=horizon,
            as_of_ms=as_of_ms,
            source_urls=tuple(source_urls),
            values=tuple(sorted((str(name), value) for name, value in values.items())),
            freshness_status=freshness_status,
        )

    def payload(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "symbol": self.symbol,
            "horizon": self.horizon,
            "as_of_ms": self.as_of_ms,
            "source_urls": list(self.source_urls),
            "values": {name: value for name, value in self.values},
            "freshness_status": self.freshness_status,
        }


def _require_text(value: str, label: str) -> str:
    text = str(value).strip()
    if not text:
        raise ResearchContextError(f"{label} is required")
    return text


def validate_context_observation(observation: ContextObservation) -> None:
    _require_text(observation.source_id, "source_id")
    _require_text(observation.symbol, "symbol")
    if observation.horizon not in ALLOWED_HORIZONS:
        raise ResearchContextError("unsupported context horizon")
    if observation.as_of_ms < 0:
        raise ResearchContextError("context as_of_ms must be non-negative")
    if not observation.source_urls:
        raise ResearchContextError("context source_urls are required")
    for source_url in observation.source_urls:
        parts = urlsplit(_require_text(source_url, "source_url"))
        if parts.scheme != "https" or not parts.netloc:
            raise ResearchContextError("context source_url must be an HTTPS URL")
    if observation.freshness_status not in ALLOWED_FRESHNESS:
        raise ResearchContextError("unsupported context freshness status")
    names: set[str] = set()
    for name, value in observation.values:
        field_name = _require_text(name, "context field name")
        if field_name in names:
            raise ResearchContextError("context field names must be unique")
        names.add(field_name)
        if value is not None and not math.isfinite(float(value)):
            raise ResearchContextError("context values must be finite or null")
    if observation.freshness_status == "UNAVAILABLE" and any(
        value is not None for _, value in observation.values
    ):
        raise ResearchContextError("UNAVAILABLE context cannot contain numeric values")


def summarize_context(
    observations: Sequence[ContextObservation], *, as_of_ms: int
) -> dict[str, object]:
    """Return deterministic descriptive evidence without a composite score."""

    if as_of_ms < 0:
        raise ResearchContextError("summary as_of_ms must be non-negative")
    validated: list[ContextObservation] = []
    for observation in observations:
        validate_context_observation(observation)
        if observation.as_of_ms > as_of_ms:
            raise ResearchContextError("future context observation is not allowed")
        validated.append(observation)
    ordered = sorted(
        validated,
        key=lambda item: (item.as_of_ms, item.source_id, item.symbol, item.horizon),
    )
    field_names = sorted(
        {name for observation in ordered for name, value in observation.values if value is not None}
    )
    return {
        "schema": "research-context-observation-v0.1",
        "status": "READY" if ordered else "NOT_READY",
        "as_of_ms": as_of_ms,
        "observation_count": len(ordered),
        "source_count": len({item.source_id for item in ordered}),
        "fields_available": field_names,
        "observations": [item.payload() for item in ordered],
        "research_only": True,
        "composite_score": None,
        "automatic_model_promotion_authorized": False,
        "direct_trade_trigger_authorized": False,
        "trade_plan_authorized": False,
        "live_trading_authorized": False,
    }
