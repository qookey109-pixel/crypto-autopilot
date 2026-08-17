from __future__ import annotations

from typing import Protocol

from ..models import Candle


class LiveTradingDisabledError(RuntimeError):
    pass


class ExchangeMarketData(Protocol):
    def list_perpetual_symbols(self) -> list[str]: ...

    def get_klines(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
        end_time_ms: int | None = None,
    ) -> list[Candle]: ...
