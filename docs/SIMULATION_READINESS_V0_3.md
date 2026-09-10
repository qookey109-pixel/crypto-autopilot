# Simulation Readiness V0.3

## Purpose

This stage removes the hand-written-plan loophole from simulation readiness.
It prepares one deterministic three-timeframe adapter that can consume the exact
Pionex V0.2 fixed sample and generate `LongTradePlan` objects from candles only.

It is **not** a profitability claim, model-quality PASS, formal backtest
admission, provider/R2 execution authority, trade-plan authority or live-trading
authority.

## Input contract

The adapter accepts only the V0.2 bounded-capacity shape:

- provider: `pionex_public_futures`
- symbol: `BTC_USDT_PERP`
- window: `2026-08-01T00:00:00Z` inclusive through
  `2026-08-28T00:00:00Z` exclusive
- intervals: `15M`, `60M`, `4H`
- exact rows: 2592 / 648 / 162
- coverage claim: `COMPLETE_FIXED_27_DAY_CAPACITY_SAMPLE_ONLY`
- receipt config SHA-256:
  `a66fdf7def02023590163091fbdd1eceabe5d96a774ffa0207e7b7a7f506f932`

Before candle decoding, each Parquet payload must match the V0.2 PASS receipt's
exact byte count and SHA-256. Decoded candles must then pass the Repository
continuity/validity audit and exact range checks. Missing intervals, gaps,
duplicates, out-of-range data, a forged receipt shape, or byte/hash mismatch
fail closed.

No production R2 read is authorized by this prepared stage.

## Candle-driven readiness strategy

This is a simulation-only adapter; it does not modify or impersonate formal
SState Intraday Wave V0.1 and it never fabricates SState probability/sample
values.

The provisional rule is deliberately simple and causal:

1. `4H` context: EMA20 > EMA50, positive EMA20 slope, close > EMA20.
2. `60M` setup: same trend gate plus extension from EMA20 <= 2.5 ATR.
3. `15M` entry: pullback near EMA20, close reclaims EMA20, close breaks the
   previous closed candle high, and volume ratio >= 1.0.
4. Stop: lower of the signal candle low / EMA20 minus 0.25 ATR.
5. Target: 2R from the signal close.
6. Fill: canonical backtest engine, first later candle open only.
7. Costs/risk: 5 bps taker fee each side, 2 bps adverse slippage each fill,
   1% equity risk, max 3x leverage, max 3 new trades/day, -3R daily gate.
8. Maximum holding time: 12 hours.

Gap-stop handling, kill-switch behavior and finite-number checks remain owned by
the canonical backtest/risk engine introduced in the preceding P0 hardening
commit; the adapter does not create a second broker.

## Readiness labels

`PIPELINE_PASS_KLINE_ONLY` means the cryptographically bound K-line payloads
were decoded, a candle-derived plan was generated, deterministic risk approved
at least one plan, and the canonical paper backtest exercised at least one
trade.

It explicitly does **not** mean `FULL_SIMULATION_READY`.

Historical perpetual funding evidence is not present in the V0.2 K-line sample.
Funding must not be silently assumed to zero or synthesized merely to produce a
READY label. Until separately sourced, versioned and validated funding evidence
exists, `full_simulation_ready=false` remains mandatory.

## Current authority

Config SHA-256: `75cbaf9c1a35d057bade9dd8e301dc14723a055d25ab453b15018928d0f12fd1`.

This PR stage is `PREPARED_SIMULATION_ONLY_NOT_DATA_ADMISSION_AUTHORITY`:

- synthetic fixture validation: allowed
- production V0.2 R2 reads: not authorized
- provider requests: not authorized
- R2 reads/writes: not authorized
- holdout access: not authorized
- formal backtest admission: not authorized
- formal V0.1 strategy mutation: not authorized
- trade plans / real-money orders / live trading: not authorized
- source switching: not authorized

A later production-data execution step requires a separate reviewed authority
after valid V0.2 PASS evidence exists. Historical failures remain unchanged.
