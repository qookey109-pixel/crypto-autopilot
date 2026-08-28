"""Causal taker-buy order-flow features for provider-separated Spot candles."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


class OrderFlowDataError(ValueError):
    """Raised when taker-buy evidence is partial or violates volume bounds."""


@dataclass(frozen=True, slots=True)
class OrderFlowSnapshot:
    taker_buy_base_volume: float | None
    taker_buy_quote_volume: float | None
    taker_buy_ratio: float | None
    buy_sell_quote_volume_delta: float | None
    buy_sell_volume_delta_fraction: float | None
    taker_buy_volume_zscore20: float | None
    rolling_cvd20_quote: float | None
    rolling_cvd20_fraction: float | None

    @property
    def ready(self) -> bool:
        return all(
            value is not None
            for value in (
                self.taker_buy_base_volume,
                self.taker_buy_quote_volume,
                self.taker_buy_ratio,
                self.buy_sell_quote_volume_delta,
                self.buy_sell_volume_delta_fraction,
                self.taker_buy_volume_zscore20,
                self.rolling_cvd20_quote,
                self.rolling_cvd20_fraction,
            )
        )

    @property
    def normalized_features(self) -> dict[str, float | None]:
        return {
            "taker_buy_ratio": self.taker_buy_ratio,
            "buy_sell_volume_delta_fraction": self.buy_sell_volume_delta_fraction,
            "taker_buy_volume_zscore20": self.taker_buy_volume_zscore20,
            "rolling_cvd20_fraction": self.rolling_cvd20_fraction,
        }


def _value(row: Mapping[str, Any] | object, name: str) -> Any:
    return row.get(name) if isinstance(row, Mapping) else getattr(row, name, None)


def _optional_finite(row: Mapping[str, Any] | object, name: str) -> float | None:
    value = _value(row, name)
    if value is None:
        return None
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0:
        raise OrderFlowDataError(f"{name} must be finite and non-negative")
    return numeric


def _zscore(values: Sequence[float]) -> float:
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return 0.0 if variance == 0 else (values[-1] - mean) / math.sqrt(variance)


def build_spot_orderflow_series(
    rows: Sequence[Mapping[str, Any] | object], *, period: int = 20
) -> tuple[OrderFlowSnapshot, ...]:
    """Build order-flow features using only the current and previous rows.

    Missing taker-buy fields remain explicit ``None`` so legacy datasets can
    still run baseline experiments without fabricating buyer-initiated flow.
    """

    if period < 2:
        raise ValueError("order-flow period must be at least 2")
    taker_base: list[float | None] = []
    taker_quote: list[float | None] = []
    quote_volume: list[float] = []
    deltas: list[float | None] = []
    ratios: list[float | None] = []
    for row in rows:
        total_base = _optional_finite(row, "base_volume")
        total_quote = _optional_finite(row, "quote_volume")
        buy_base = _optional_finite(row, "taker_buy_base_volume")
        buy_quote = _optional_finite(row, "taker_buy_quote_volume")
        if total_base is None or total_quote is None:
            raise OrderFlowDataError("base_volume and quote_volume are required")
        if (buy_base is None) != (buy_quote is None):
            raise OrderFlowDataError("taker-buy base and quote volume must be paired")
        if buy_base is not None and (
            buy_base > total_base + 1e-12 or float(buy_quote or 0.0) > total_quote + 1e-12
        ):
            raise OrderFlowDataError("taker-buy volume exceeds total volume")
        taker_base.append(buy_base)
        taker_quote.append(buy_quote)
        quote_volume.append(total_quote)
        if buy_quote is None:
            deltas.append(None)
            ratios.append(None)
        else:
            deltas.append(2.0 * buy_quote - total_quote)
            ratios.append(None if total_quote == 0 else buy_quote / total_quote)

    output: list[OrderFlowSnapshot] = []
    for index in range(len(rows)):
        delta_fraction = None
        if deltas[index] is not None and quote_volume[index] > 0:
            delta_fraction = float(deltas[index]) / quote_volume[index]
        zscore = None
        rolling_cvd = None
        rolling_cvd_fraction = None
        if index >= period - 1:
            start = index - period + 1
            buy_window = taker_quote[start : index + 1]
            delta_window = deltas[start : index + 1]
            if all(value is not None for value in buy_window) and all(
                value is not None for value in delta_window
            ):
                zscore = _zscore(
                    [float(value) for value in buy_window if value is not None]
                )
                rolling_cvd = sum(
                    float(value) for value in delta_window if value is not None
                )
                total_quote = sum(quote_volume[start : index + 1])
                if total_quote > 0:
                    rolling_cvd_fraction = rolling_cvd / total_quote
        output.append(
            OrderFlowSnapshot(
                taker_buy_base_volume=taker_base[index],
                taker_buy_quote_volume=taker_quote[index],
                taker_buy_ratio=ratios[index],
                buy_sell_quote_volume_delta=deltas[index],
                buy_sell_volume_delta_fraction=delta_fraction,
                taker_buy_volume_zscore20=zscore,
                rolling_cvd20_quote=rolling_cvd,
                rolling_cvd20_fraction=rolling_cvd_fraction,
            )
        )
    return tuple(output)
