from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..models import Candle


class PionexAPIError(RuntimeError):
    pass


class PionexPublicClient:
    """Public-only Pionex futures client for V0.1.

    No API key, signing, balance, position or order methods are present here.
    """

    BASE_URL = "https://api.pionex.com"
    ALLOWED_INTERVALS = {"1M", "5M", "15M", "30M", "60M", "4H", "8H", "12H", "1D", "1W", "1m"}

    def __init__(self, *, timeout_seconds: float = 15.0) -> None:
        self.timeout_seconds = timeout_seconds

    def _get_json(self, path: str, params: dict[str, object]) -> dict:
        query = urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{self.BASE_URL}{path}?{query}" if query else f"{self.BASE_URL}{path}"
        req = Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "qookey-crypto-autopilot/0.1"},
        )
        with urlopen(req, timeout=self.timeout_seconds) as response:  # noqa: S310 - fixed HTTPS host
            payload = json.loads(response.read().decode("utf-8"))
        if not payload.get("result"):
            raise PionexAPIError(
                f"Pionex request failed: {payload.get('code')} {payload.get('message')}"
            )
        return payload

    def list_perpetual_symbols(self) -> list[str]:
        payload = self._get_json(
            "/api/v1/common/symbols",
            {"type": "PERP", "status": "TRADING"},
        )
        rows = payload.get("data", {}).get("symbols", [])
        return sorted({str(row["symbol"]) for row in rows if row.get("symbol")})

    def get_klines(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
        end_time_ms: int | None = None,
    ) -> list[Candle]:
        if interval not in self.ALLOWED_INTERVALS:
            raise ValueError(f"Unsupported Pionex interval: {interval}")
        if not 1 <= limit <= 500:
            raise ValueError("Pionex futures kline limit must be between 1 and 500")

        payload = self._get_json(
            "/api/v1/market/klines",
            {
                "symbol": symbol,
                "interval": interval,
                "limit": limit,
                "endTime": end_time_ms,
            },
        )
        candles = [
            Candle(
                time_ms=int(row["time"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            )
            for row in payload.get("data", {}).get("klines", [])
        ]
        return sorted(candles, key=lambda candle: candle.time_ms)
