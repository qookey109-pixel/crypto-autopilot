from __future__ import annotations

from dataclasses import dataclass
from typing import Any


_ALLOWED_EVIDENCE_TYPES = {
    "verified_partition_receipt",
    "provider_declared_listing",
    "provider_declared_delisting",
    "external_proxy_observation",
}


class HistoricalUniverseConflictError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class HistoricalMarketRecord:
    provider: str
    market_type: str
    symbol: str
    interval: str
    available_from_ms: int
    available_to_ms: int
    evidence_type: str
    source_ref: str
    source_sha256: str | None = None
    native: bool = True

    def __post_init__(self) -> None:
        for name, value in (
            ("provider", self.provider),
            ("market_type", self.market_type),
            ("symbol", self.symbol),
            ("interval", self.interval),
            ("source_ref", self.source_ref),
        ):
            if not str(value).strip():
                raise ValueError(f"{name} is required")
        if self.available_from_ms < 0 or self.available_to_ms < 0:
            raise ValueError("availability timestamps cannot be negative")
        if self.available_from_ms > self.available_to_ms:
            raise ValueError("available_from_ms must be <= available_to_ms")
        if self.evidence_type not in _ALLOWED_EVIDENCE_TYPES:
            raise ValueError(f"unsupported evidence_type: {self.evidence_type}")
        if self.source_sha256 is not None:
            digest = self.source_sha256.strip().lower()
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise ValueError("source_sha256 must be a 64-character hex digest")

    @property
    def identity(self) -> tuple[str, str, str, str]:
        return (self.provider, self.market_type, self.symbol, self.interval)

    def contains(self, timestamp_ms: int) -> bool:
        return self.available_from_ms <= timestamp_ms <= self.available_to_ms


@dataclass(frozen=True, slots=True)
class HistoricalUniverseSnapshot:
    timestamp_ms: int
    provider: str
    market_type: str
    required_intervals: tuple[str, ...]
    native_only: bool
    symbols: tuple[str, ...]
    authority_refs: tuple[str, ...]


class HistoricalUniverseIndex:
    """Evidence-bounded historical market availability index.

    The index never extrapolates a market outside observed/declared coverage.
    This prevents today's active universe from being silently projected into
    older backtests.
    """

    def __init__(self, records: list[HistoricalMarketRecord] | tuple[HistoricalMarketRecord, ...]) -> None:
        deduped = tuple(
            sorted(
                set(records),
                key=lambda item: (
                    item.provider,
                    item.market_type,
                    item.symbol,
                    item.interval,
                    item.available_from_ms,
                    item.available_to_ms,
                    item.source_ref,
                    item.source_sha256 or "",
                    item.native,
                ),
            )
        )
        self._validate_no_conflicting_overlap(deduped)
        self.records = deduped

    @staticmethod
    def _validate_no_conflicting_overlap(records: tuple[HistoricalMarketRecord, ...]) -> None:
        grouped: dict[tuple[str, str, str, str], list[HistoricalMarketRecord]] = {}
        for record in records:
            grouped.setdefault(record.identity, []).append(record)
        for identity, items in grouped.items():
            ordered = sorted(items, key=lambda item: (item.available_from_ms, item.available_to_ms))
            for left, right in zip(ordered, ordered[1:]):
                if right.available_from_ms <= left.available_to_ms:
                    raise HistoricalUniverseConflictError(
                        "overlapping non-identical authority for "
                        f"{identity}: {left.source_ref} vs {right.source_ref}"
                    )

    def available_symbols_at(
        self,
        timestamp_ms: int,
        *,
        provider: str,
        market_type: str = "perp",
        required_intervals: tuple[str, ...] = ("15M", "60M", "4H"),
        native_only: bool = True,
    ) -> tuple[str, ...]:
        if timestamp_ms < 0:
            raise ValueError("timestamp_ms cannot be negative")
        if not provider.strip() or not market_type.strip():
            raise ValueError("provider and market_type are required")
        if not required_intervals or any(not interval.strip() for interval in required_intervals):
            raise ValueError("required_intervals must contain non-empty interval names")

        required = tuple(dict.fromkeys(required_intervals))
        coverage: dict[str, set[str]] = {}
        for record in self.records:
            if record.provider != provider or record.market_type != market_type:
                continue
            if native_only and not record.native:
                continue
            if record.interval not in required or not record.contains(timestamp_ms):
                continue
            coverage.setdefault(record.symbol, set()).add(record.interval)

        required_set = set(required)
        return tuple(sorted(symbol for symbol, intervals in coverage.items() if required_set <= intervals))

    def snapshot(
        self,
        timestamp_ms: int,
        *,
        provider: str,
        market_type: str = "perp",
        required_intervals: tuple[str, ...] = ("15M", "60M", "4H"),
        native_only: bool = True,
    ) -> HistoricalUniverseSnapshot:
        symbols = self.available_symbols_at(
            timestamp_ms,
            provider=provider,
            market_type=market_type,
            required_intervals=required_intervals,
            native_only=native_only,
        )
        symbol_set = set(symbols)
        interval_set = set(required_intervals)
        refs = {
            record.source_ref
            for record in self.records
            if record.provider == provider
            and record.market_type == market_type
            and record.symbol in symbol_set
            and record.interval in interval_set
            and record.contains(timestamp_ms)
            and (record.native or not native_only)
        }
        return HistoricalUniverseSnapshot(
            timestamp_ms=timestamp_ms,
            provider=provider,
            market_type=market_type,
            required_intervals=tuple(dict.fromkeys(required_intervals)),
            native_only=native_only,
            symbols=symbols,
            authority_refs=tuple(sorted(refs)),
        )


def record_from_partition_receipt(
    payload: dict[str, Any],
    *,
    source_ref: str,
    source_sha256: str | None = None,
    native: bool,
) -> HistoricalMarketRecord | None:
    """Convert a verified historical partition receipt into coverage evidence.

    `native` is intentionally explicit. Provider names are not used to infer
    provenance because proxy histories must never be mislabeled as native.
    """

    status = str(payload.get("status") or "")
    if status == "NO_DATA":
        return None
    if status != "PASS":
        raise ValueError(f"partition receipt must be PASS or NO_DATA, got {status!r}")
    if payload.get("audit_ok") is not True:
        raise ValueError("partition receipt audit_ok must be true")

    first_ms = payload.get("actual_first_ms")
    last_ms = payload.get("actual_last_ms")
    if not isinstance(first_ms, int) or not isinstance(last_ms, int):
        raise ValueError("partition receipt requires integer actual_first_ms/actual_last_ms")

    return HistoricalMarketRecord(
        provider=str(payload.get("provider") or ""),
        market_type=str(payload.get("market_type") or ""),
        symbol=str(payload.get("symbol") or ""),
        interval=str(payload.get("interval") or ""),
        available_from_ms=first_ms,
        available_to_ms=last_ms,
        evidence_type="verified_partition_receipt",
        source_ref=source_ref,
        source_sha256=source_sha256,
        native=native,
    )
