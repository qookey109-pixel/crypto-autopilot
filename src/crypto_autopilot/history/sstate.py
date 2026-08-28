from __future__ import annotations

import math
from dataclasses import dataclass

from crypto_autopilot.models import SStateContext


class HistoricalSStateConflictError(RuntimeError):
    pass


class HistoricalSStateNotAvailableError(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class HistoricalSStatePoint:
    """One recorded SState output with explicit historical availability time."""

    symbol: str
    bar_time_ms: int
    available_at_ms: int
    context: SStateContext
    source_ref: str
    source_sha256: str | None = None

    def __post_init__(self) -> None:
        if not self.symbol.strip() or not self.source_ref.strip():
            raise ValueError("symbol and source_ref are required")
        if self.bar_time_ms < 0 or self.available_at_ms < 0:
            raise ValueError("timestamps cannot be negative")
        if self.available_at_ms < self.bar_time_ms:
            raise ValueError("available_at_ms cannot be earlier than bar_time_ms")
        if not self.context.state.strip():
            raise ValueError("SState state is required")
        if self.context.samples < 0:
            raise ValueError("SState samples cannot be negative")
        if self.context.probability is not None:
            probability = self.context.probability
            if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
                raise ValueError("SState probability must be finite and within [0, 1]")
        if self.source_sha256 is not None:
            digest = self.source_sha256.strip().lower()
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise ValueError("source_sha256 must be a 64-character hex digest")

    @property
    def identity(self) -> tuple[str, int]:
        return (self.symbol, self.bar_time_ms)


class HistoricalSStateReplayProvider:
    """Read-only exact-bar replay boundary for previously recorded SState outputs.

    The provider deliberately does not carry a prior state forward to an
    unrecorded bar. Historical replay must supply authority for the exact bar.
    """

    def __init__(self, points: list[HistoricalSStatePoint] | tuple[HistoricalSStatePoint, ...]) -> None:
        grouped: dict[tuple[str, int], list[HistoricalSStatePoint]] = {}
        for point in points:
            grouped.setdefault(point.identity, []).append(point)

        canonical: list[HistoricalSStatePoint] = []
        for identity, candidates in grouped.items():
            unique = set(candidates)
            if len(unique) > 1:
                refs = sorted(point.source_ref for point in unique)
                raise HistoricalSStateConflictError(
                    f"conflicting SState authority for {identity}: {refs}"
                )
            canonical.append(next(iter(unique)))

        self.points = tuple(
            sorted(
                canonical,
                key=lambda point: (
                    point.bar_time_ms,
                    point.symbol,
                    point.available_at_ms,
                    point.source_ref,
                ),
            )
        )
        self._by_identity = {point.identity: point for point in self.points}

    def get_point_for_bar(
        self,
        symbol: str,
        bar_time_ms: int,
        *,
        as_of_ms: int,
    ) -> HistoricalSStatePoint:
        if not symbol.strip():
            raise ValueError("symbol is required")
        if bar_time_ms < 0 or as_of_ms < 0:
            raise ValueError("timestamps cannot be negative")

        try:
            point = self._by_identity[(symbol, bar_time_ms)]
        except KeyError as exc:
            raise HistoricalSStateNotAvailableError(
                f"No historical SState authority for {symbol} bar {bar_time_ms}"
            ) from exc

        if point.available_at_ms > as_of_ms:
            raise HistoricalSStateNotAvailableError(
                f"Historical SState for {symbol} bar {bar_time_ms} is not available until "
                f"{point.available_at_ms}; as_of={as_of_ms}"
            )
        return point

    def get_context_for_bar(
        self,
        symbol: str,
        bar_time_ms: int,
        *,
        as_of_ms: int,
    ) -> SStateContext:
        return self.get_point_for_bar(symbol, bar_time_ms, as_of_ms=as_of_ms).context

    def available_points_as_of(self, as_of_ms: int) -> tuple[HistoricalSStatePoint, ...]:
        if as_of_ms < 0:
            raise ValueError("as_of_ms cannot be negative")
        return tuple(point for point in self.points if point.available_at_ms <= as_of_ms)
