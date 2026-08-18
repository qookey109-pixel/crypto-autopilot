from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BinanceObservedCapacity:
    observed_rows: int
    observed_parquet_bytes: int
    observed_candidate_count: int
    rows_per_full_market_year: int
    full_candidate_year_rows: int
    missing_equivalent_rows: int
    observed_bytes_per_row: float
    full_candidate_year_equivalent_bytes: float
    target_markets: int
    target_years: int
    canonical_target_bytes: float
    canonical_target_gb: float
    canonical_plus_staging_gb: float
    three_x_capacity_stress_gb: float


def estimate_binance_observed_capacity(
    *,
    observed_rows: int,
    observed_parquet_bytes: int,
    observed_candidate_count: int = 15,
    rows_per_full_market_year: int = 45_990,
    target_markets: int = 250,
    target_years: int = 8,
) -> BinanceObservedCapacity:
    """Conservatively scale a mixed-coverage observed Binance year to target capacity.

    The observed 2025 pilot contains a partial HYPE year. To avoid allowing that
    partial coverage to depress the target estimate, missing rows up to a full
    `observed_candidate_count × rows_per_full_market_year` are imputed at the
    observed bytes-per-row before scaling to the target market/year envelope.
    """

    for name, value in (
        ("observed_rows", observed_rows),
        ("observed_parquet_bytes", observed_parquet_bytes),
        ("observed_candidate_count", observed_candidate_count),
        ("rows_per_full_market_year", rows_per_full_market_year),
        ("target_markets", target_markets),
        ("target_years", target_years),
    ):
        if int(value) <= 0:
            raise ValueError(f"{name} must be positive")

    full_candidate_rows = observed_candidate_count * rows_per_full_market_year
    if observed_rows > full_candidate_rows:
        raise ValueError(
            "observed_rows exceed the frozen full-candidate-year row envelope; "
            "the capacity basis must be reviewed instead of silently rescaled"
        )

    bytes_per_row = observed_parquet_bytes / observed_rows
    if not math.isfinite(bytes_per_row) or bytes_per_row <= 0:
        raise ValueError("observed bytes-per-row must be finite and positive")

    missing_rows = full_candidate_rows - observed_rows
    full_candidate_equivalent_bytes = observed_parquet_bytes + missing_rows * bytes_per_row
    target_scale = (target_markets * target_years) / observed_candidate_count
    canonical_target_bytes = full_candidate_equivalent_bytes * target_scale
    canonical_target_gb = canonical_target_bytes / 1_000_000_000.0

    return BinanceObservedCapacity(
        observed_rows=observed_rows,
        observed_parquet_bytes=observed_parquet_bytes,
        observed_candidate_count=observed_candidate_count,
        rows_per_full_market_year=rows_per_full_market_year,
        full_candidate_year_rows=full_candidate_rows,
        missing_equivalent_rows=missing_rows,
        observed_bytes_per_row=bytes_per_row,
        full_candidate_year_equivalent_bytes=full_candidate_equivalent_bytes,
        target_markets=target_markets,
        target_years=target_years,
        canonical_target_bytes=canonical_target_bytes,
        canonical_target_gb=canonical_target_gb,
        canonical_plus_staging_gb=canonical_target_gb * 2.0,
        three_x_capacity_stress_gb=canonical_target_gb * 3.0,
    )
