from __future__ import annotations

import math
from dataclasses import dataclass

from .historical_universe import HistoricalUniverseIndex


class HistoricalLiquidityConflictError(RuntimeError):
    pass


class HistoricalLiquidityEvidenceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class HistoricalLiquidityPolicy:
    """Versionable point-in-time liquidity selection policy."""

    target_size: int = 15
    max_spread_bps: float = 30.0
    max_snapshot_age_ms: int = 86_400_000
    required_intervals: tuple[str, ...] = ("15M", "60M", "4H")
    native_only: bool = True
    require_complete_universe: bool = True

    def __post_init__(self) -> None:
        if not 1 <= self.target_size <= 20:
            raise ValueError("target_size must be between 1 and 20")
        if not math.isfinite(self.max_spread_bps) or self.max_spread_bps <= 0:
            raise ValueError("max_spread_bps must be finite and positive")
        if self.max_snapshot_age_ms <= 0:
            raise ValueError("max_snapshot_age_ms must be positive")
        if not self.required_intervals or any(not interval.strip() for interval in self.required_intervals):
            raise ValueError("required_intervals must contain non-empty interval names")
        if len(set(self.required_intervals)) != len(self.required_intervals):
            raise ValueError("required_intervals cannot contain duplicates")


@dataclass(frozen=True, slots=True)
class HistoricalLiquidityMarket:
    symbol: str
    quote_amount_24h: float
    spread_bps: float
    close: float
    trade_count_24h: int

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        for name, value in (
            ("quote_amount_24h", self.quote_amount_24h),
            ("spread_bps", self.spread_bps),
            ("close", self.close),
        ):
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.quote_amount_24h <= 0:
            raise ValueError("quote_amount_24h must be positive")
        if self.spread_bps < 0:
            raise ValueError("spread_bps cannot be negative")
        if self.close <= 0:
            raise ValueError("close must be positive")
        if self.trade_count_24h < 0:
            raise ValueError("trade_count_24h cannot be negative")


@dataclass(frozen=True, slots=True)
class HistoricalLiquidityBatch:
    """One provider-native point-in-time 24h ticker + BBO snapshot batch."""

    provider: str
    market_type: str
    snapshot_id: str
    snapshot_time_ms: int
    available_at_ms: int
    markets: tuple[HistoricalLiquidityMarket, ...]
    source_ref: str
    source_sha256: str | None = None
    native: bool = True

    def __post_init__(self) -> None:
        for name, value in (
            ("provider", self.provider),
            ("market_type", self.market_type),
            ("snapshot_id", self.snapshot_id),
            ("source_ref", self.source_ref),
        ):
            if not value.strip():
                raise ValueError(f"{name} is required")
        if self.snapshot_time_ms < 0 or self.available_at_ms < 0:
            raise ValueError("timestamps cannot be negative")
        if self.available_at_ms < self.snapshot_time_ms:
            raise ValueError("available_at_ms cannot be earlier than snapshot_time_ms")
        if not self.markets:
            raise ValueError("markets cannot be empty")
        symbols = [market.symbol for market in self.markets]
        if len(set(symbols)) != len(symbols):
            raise ValueError("markets cannot contain duplicate symbols")
        if self.source_sha256 is not None:
            digest = self.source_sha256.strip().lower()
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise ValueError("source_sha256 must be a 64-character hex digest")

    @property
    def identity(self) -> tuple[str, str, str]:
        return (self.provider, self.market_type, self.snapshot_id)


@dataclass(frozen=True, slots=True)
class HistoricalLiquidityRankedMarket:
    rank: int
    symbol: str
    quote_amount_24h: float
    spread_bps: float
    close: float
    trade_count_24h: int


@dataclass(frozen=True, slots=True)
class HistoricalLiquiditySnapshot:
    as_of_ms: int
    provider: str
    market_type: str
    target_size: int
    max_spread_bps: float
    max_snapshot_age_ms: int
    batch_id: str
    batch_snapshot_time_ms: int
    batch_available_at_ms: int
    ranked_markets: tuple[HistoricalLiquidityRankedMarket, ...]
    historical_universe_symbols: tuple[str, ...]
    historical_universe_authority_refs: tuple[str, ...]
    liquidity_authority_ref: str
    liquidity_authority_sha256: str | None

    @property
    def symbols(self) -> tuple[str, ...]:
        return tuple(market.symbol for market in self.ranked_markets)


class HistoricalLiquidityIndex:
    """Point-in-time liquidity ranking without current-universe backprojection."""

    def __init__(self, batches: list[HistoricalLiquidityBatch] | tuple[HistoricalLiquidityBatch, ...]) -> None:
        grouped: dict[tuple[str, str, str], list[HistoricalLiquidityBatch]] = {}
        for batch in batches:
            grouped.setdefault(batch.identity, []).append(batch)

        canonical: list[HistoricalLiquidityBatch] = []
        for identity, candidates in grouped.items():
            unique = set(candidates)
            if len(unique) > 1:
                refs = sorted(batch.source_ref for batch in unique)
                raise HistoricalLiquidityConflictError(
                    f"conflicting historical liquidity authority for {identity}: {refs}"
                )
            canonical.append(next(iter(unique)))

        self.batches = tuple(
            sorted(
                canonical,
                key=lambda batch: (
                    batch.snapshot_time_ms,
                    batch.available_at_ms,
                    batch.provider,
                    batch.market_type,
                    batch.snapshot_id,
                    batch.source_ref,
                ),
            )
        )

    def _latest_batch(
        self,
        *,
        as_of_ms: int,
        provider: str,
        market_type: str,
        policy: HistoricalLiquidityPolicy,
    ) -> HistoricalLiquidityBatch:
        eligible = [
            batch
            for batch in self.batches
            if batch.provider == provider
            and batch.market_type == market_type
            and (batch.native or not policy.native_only)
            and batch.snapshot_time_ms <= as_of_ms
            and batch.available_at_ms <= as_of_ms
            and as_of_ms - batch.snapshot_time_ms <= policy.max_snapshot_age_ms
        ]
        if not eligible:
            raise HistoricalLiquidityEvidenceError(
                "no fresh historical liquidity batch was available at the requested timestamp"
            )
        return max(
            eligible,
            key=lambda batch: (
                batch.snapshot_time_ms,
                batch.available_at_ms,
                batch.snapshot_id,
            ),
        )

    def snapshot(
        self,
        as_of_ms: int,
        *,
        historical_universe: HistoricalUniverseIndex,
        provider: str,
        market_type: str = "perp",
        policy: HistoricalLiquidityPolicy = HistoricalLiquidityPolicy(),
    ) -> HistoricalLiquiditySnapshot:
        if as_of_ms < 0:
            raise ValueError("as_of_ms cannot be negative")
        if not provider.strip() or not market_type.strip():
            raise ValueError("provider and market_type are required")

        universe = historical_universe.snapshot(
            as_of_ms,
            provider=provider,
            market_type=market_type,
            required_intervals=policy.required_intervals,
            native_only=policy.native_only,
        )
        if not universe.symbols:
            raise HistoricalLiquidityEvidenceError(
                "historical universe contains no evidence-eligible symbols at the requested timestamp"
            )

        batch = self._latest_batch(
            as_of_ms=as_of_ms,
            provider=provider,
            market_type=market_type,
            policy=policy,
        )
        by_symbol = {market.symbol: market for market in batch.markets}
        missing = tuple(symbol for symbol in universe.symbols if symbol not in by_symbol)
        if missing and policy.require_complete_universe:
            raise HistoricalLiquidityEvidenceError(
                "historical liquidity batch does not cover the complete evidence-bounded universe: "
                + ", ".join(missing)
            )

        candidates = [
            by_symbol[symbol]
            for symbol in universe.symbols
            if symbol in by_symbol and by_symbol[symbol].spread_bps <= policy.max_spread_bps
        ]
        candidates.sort(key=lambda market: (-market.quote_amount_24h, market.spread_bps, market.symbol))
        ranked = tuple(
            HistoricalLiquidityRankedMarket(
                rank=index,
                symbol=market.symbol,
                quote_amount_24h=market.quote_amount_24h,
                spread_bps=market.spread_bps,
                close=market.close,
                trade_count_24h=market.trade_count_24h,
            )
            for index, market in enumerate(candidates[: policy.target_size], start=1)
        )

        return HistoricalLiquiditySnapshot(
            as_of_ms=as_of_ms,
            provider=provider,
            market_type=market_type,
            target_size=policy.target_size,
            max_spread_bps=policy.max_spread_bps,
            max_snapshot_age_ms=policy.max_snapshot_age_ms,
            batch_id=batch.snapshot_id,
            batch_snapshot_time_ms=batch.snapshot_time_ms,
            batch_available_at_ms=batch.available_at_ms,
            ranked_markets=ranked,
            historical_universe_symbols=universe.symbols,
            historical_universe_authority_refs=universe.authority_refs,
            liquidity_authority_ref=batch.source_ref,
            liquidity_authority_sha256=batch.source_sha256,
        )
