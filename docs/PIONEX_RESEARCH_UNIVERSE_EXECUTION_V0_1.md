# Pionex Research Universe Snapshot Execution V0.1

Status: **AUTHORIZED AFTER PROTECTED-MAIN MERGE — AWAITING WORKFLOW WIRING**

## Purpose

Authorize one bounded public Pionex snapshot that feeds the already prepared
150+ research-universe selector. This stage does not add a scheduler and does
not persist the selected universe to R2.

The snapshot consists of exactly three public market-data requests, in order:

1. live PERP symbols;
2. PERP tickers;
3. PERP book tickers.

The resulting snapshot is passed directly into
`pionex_universe_v0_1.build_universe()` and written as a secret-free JSON report.

## Execution window

- not before: `2026-09-10T19:00:00Z`
- stop exclusive: `2026-09-16T00:00:00Z`
- GitHub Actions main only
- manual `workflow_dispatch` only
- run attempt 1 only
- exact provider request count: 3
- automatic retries: 0
- request pace: 3 requests/second
- request timeout: 15 seconds

The workflow itself is intentionally not introduced in this stacked stage. A
later minimal wiring change may expose the runner from the default branch after
the selection and execution contracts are reviewed together.

## Data boundary

All three endpoints are public Pionex market-data endpoints. No API key,
signature, account balance, position, order, transfer or private funding-fee
history is required or allowed.

The output may contain normalized public market metrics and the selected
universe. Raw provider payloads are not retained.

No R2 client is constructed. No holdout object is listed or read.

## 150+ selection behavior

The exact selector is SHA-bound to:

`config/pionex_research_universe_v0_1.json`

The selector requires:

- 100 quality-valid liquidity-ranked Pionex crypto perpetuals;
- all quality-valid live meme-watchlist matches;
- all quality-valid live tokenized alternative-asset registry matches;
- deterministic fill from remaining crypto until at least 150 markets exist.

The selection remains a research universe. It is not a claim of global
market-cap Top 100 and it does not admit any market to live trading.

## Historical acquisition profiles

The selection report preserves the tiered history profile:

- `FULL_INTRADAY`: at most 30 markets → `15M / 60M / 4H / 1D / 1W`;
- `MULTISCALE_RESEARCH`: remaining core/meme markets → `60M / 4H / 1D / 1W`;
- `BREADTH_BACKGROUND`: remaining markets → `1D / 1W`.

This execution stage does not download those histories. It only freezes which
markets would receive each profile under a later materialization authority.

## Failure behavior

The runner fails closed when:

- it is not a fresh GitHub main manual dispatch;
- the execution window is closed;
- selection/registry bytes no longer match the SHA-bound contract;
- any of the three provider requests fails;
- fewer than 100 quality-valid Pionex crypto markets exist;
- the final quality-valid research universe cannot reach 150 markets;
- deterministic selector validation rejects the snapshot.

No provider fallback, source switch, fabricated market metric, automatic retry,
R2 fallback or private API fallback is allowed.

## Explicit non-authority

This stage does not authorize:

- historical K-line/funding materialization;
- R2 reads/writes;
- replacement-holdout access;
- training or formal backtest admission;
- strategy changes;
- source switching;
- trade plans;
- real-money orders;
- live trading.

Execution config SHA-256: `a7c898d24e4cc5a6685746559fc1aeb49a6841b471f1dd6a78d1d8ff84262d4a`
Selection config SHA-256: `3c70bab735b76f59766cfbea9f2c1e8cbb24305359f5f877eb2782a1445b6309`
