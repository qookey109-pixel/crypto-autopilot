"""Prepare a complete offline 4H regime warmup; no external I/O or authority."""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from crypto_autopilot.features.regime import build_alt_breadth_series
from crypto_autopilot.models import Candle
from crypto_autopilot.paper.cloud_multiframe_inputs_v0_1 import (
    MultiframeInputs,
    _closed_bars,
    validate_multiframe_inputs as validate_short_window,
)


def validate_multiframe_inputs(
    *, as_of_ms: int, breadth: Mapping[str, Sequence[Candle]],
    references: Mapping[str, Sequence[Candle]], candidates: Mapping[str, Sequence[Candle]],
) -> MultiframeInputs:
    """Return 21 aligned ready breadth observations from 40 closed 4H bars.

    This is in-memory preparation. Caller data is neither authenticated nor
    approved for strategy use, and the old 21-bar shape is not silently padded.
    """
    if type(as_of_ms) is not int or as_of_ms < 0 or not isinstance(breadth, Mapping):
        raise ValueError("INPUT_INVALID")
    checked = {
        symbol: _closed_bars(rows, interval_ms=14_400_000, count=40, as_of_ms=as_of_ms)
        for symbol, rows in breadth.items()
    }
    short = validate_short_window(
        as_of_ms=as_of_ms,
        breadth={symbol: rows[-21:] for symbol, rows in checked.items()},
        references=references,
        candidates=candidates,
    )
    ready = build_alt_breadth_series(checked, "4H")[-21:]
    if len(ready) != 21 or any(not snapshot.ready for snapshot in ready):
        raise ValueError("REGIME_WARMUP_INCOMPLETE")
    times = tuple(snapshot.bar_time_ms for snapshot in ready)
    if any(tuple(bar.time_ms for bar in bars) != times for bars in short.reference_bars.values()):
        raise ValueError("REFERENCE_GRID_MISMATCH")
    return MultiframeInputs(
        breadth_series=ready,
        reference_bars=short.reference_bars,
        candidate_technical=short.candidate_technical,
    )
