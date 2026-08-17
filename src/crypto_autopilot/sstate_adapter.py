from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import SStateContext


class SStateProvider(Protocol):
    """Read-only boundary to the existing validated SState system."""

    def get_context(self, symbol: str) -> SStateContext: ...


@dataclass(slots=True)
class StaticSStateProvider:
    """Deterministic fixture/provider for tests and early backtests."""

    contexts: dict[str, SStateContext]

    def get_context(self, symbol: str) -> SStateContext:
        try:
            return self.contexts[symbol]
        except KeyError as exc:
            raise LookupError(f"No SState context for {symbol}") from exc
