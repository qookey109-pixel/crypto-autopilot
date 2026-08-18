# Binance Long-Horizon Funding V0.1

## Purpose

Add a provider-separated Binance USD-M Funding Rate evidence path for future long-horizon research and backtesting without changing the frozen Pionex execution authority.

This phase starts with a **read-only source proof**. It does not write Funding data to R2 and does not authorize backtest admission.

## Existing authority reused

The Repository already has:

- public Binance USD-M Funding REST support in `src/crypto_autopilot/exchanges/binance_usdm_public.py`;
- paginated historical Funding acquisition in `src/crypto_autopilot/binance_historical.py`;
- conversion support into Backtest funding points;
- Cloudflare R2 storage primitives;
- provider separation requiring Binance data to remain `provider=binance_usdm`.

V0.1 does not replace or rewrite those components.

## Bulk source

Funding uses Binance Vision USD-M monthly `fundingRate` archives.

Logical archive shape:

```text
data/futures/um/monthly/fundingRate/{SYMBOL}/
  {SYMBOL}-fundingRate-{YYYY-MM}.zip
```

Every consumed archive requires its paired `.CHECKSUM` and exact SHA-256 verification before parsing.

Funding is not treated as a Kline interval. There is no artificial `1h` / `4h` archive subdirectory.

## Frozen source schema

V0.1 resolves the published Funding archive to these canonical fields:

- `calc_time`
- `funding_interval_hours`
- `last_funding_rate`

The parser accepts either the explicit header or the exact three-column positional representation. Unknown or extra headerless layouts fail closed.

The source-declared funding interval is retained. V0.1 never assumes funding must always be eight hours.

## Timestamp and cadence audit

The first live execution used exact millisecond equality between adjacent `calc_time` values and the declared Funding interval. Run `32128779729` was superseded before any PASS authority because the source data showed bounded millisecond jitter rather than a missing Funding observation.

A separate read-only diagnostic measured BTCUSDT, ETHUSDT and SOLUSDT for `2024-01`:

- 93 rows per symbol;
- all declared intervals = 8 hours;
- 28 non-zero residuals per symbol under exact-millisecond comparison;
- residuals were only `+/-1`, `+/-2` or `+/-3` ms;
- maximum absolute residual = **3 ms** for all three symbols.

The protocol was then re-frozen **before a PASS authority** with a bounded `+/-10 ms` cadence-jitter tolerance.

Important: this tolerance is audit-only. The original `calc_time` is preserved exactly. Timestamps are never rounded, shifted, interpolated or synthesized.

For every source archive:

- archive SHA-256 must match Binance `.CHECKSUM`;
- ZIP must contain exactly the expected CSV member;
- timestamps must be strictly increasing and unique;
- rate must be finite;
- declared funding interval must be positive and bounded to 24 hours;
- each observed timestamp delta must match either the preceding or following source-declared interval within `+/-10 ms`;
- a residual larger than 10 ms fails closed as an unexplained cadence gap;
- a changed archive SHA or changed logical metadata requires explicit revision review.

No interpolation or synthetic funding point is allowed.

## Proof scope

The source-proof scope remains:

- BTCUSDT
- ETHUSDT
- SOLUSDT
- period `2024-01`

The valid proof execution confirms the Binance Vision Funding path, checksum contract, archive schema and bounded timestamp-jitter behavior for this scope.

It does **not** prove all 15 symbols have the same long-horizon Funding availability.

## Future R2 layout

After a separate coverage authority and explicit R2-write authority exist, canonical Funding storage is annual per symbol:

```text
market-data/binance_usdm/perp/{SYMBOL}/funding/year={YYYY}/funding.parquet
```

Parquet fields:

- `symbol`
- `funding_time_ms`
- `funding_interval_hours`
- `funding_rate`

Compression: Zstd.

Annual aggregation must preserve the original Funding timestamps/rates exactly and must re-run monotonicity, uniqueness and bounded cadence audits across month boundaries.

## Required next evidence before long-horizon materialization

1. Bounded Funding source proof PASS.
2. 15-symbol Funding monthly coverage discovery PASS.
3. Funding-specific observed R2 cost/budget review if the discovered scope materially changes storage/operation assumptions.
4. Explicit Funding R2 materialization authority naming the exact years/symbols.

Funding data remains independent of the Trade-Kline W1 authorization path.

## Provenance boundary

Funding data is:

- provider: `binance_usdm`
- delivery: `binance_vision`
- execution exchange: `pionex`
- native to Pionex: **false**

Symbol mapping does not convert provenance.

Funding evidence cannot silently create Pionex-native Historical Universe membership or authorize Binance -> Pionex source substitution.

## Safety boundary

V0.1 does not authorize:

- R2 writes;
- Funding long-horizon materialization;
- source switching;
- provider splicing;
- Pionex-native relabeling;
- backtest admission;
- strategy parameter changes;
- automatic trade plans;
- real-money orders;
- live trading.
