# Pionex Validation Dataset V0.1

Status: **PREPARED / EXECUTION ONLY AFTER REVIEWED MAIN MERGE / MANUAL ONLY**

Date: 2026-09-15

## Architecture rule

The project now treats the two providers as intentionally different layers:

- **Binance = large-scale learning database.**
- **Pionex = final calibration and real trading environment.**

Pionex V0.1 does not replace Binance Core100 training. It builds provider-native
validation evidence for the venue where the system is intended to trade.

## Frozen source universe

The materializer is bound to the successful Pionex Research Universe 150+ V0.1
snapshot:

- workflow run: `34563615657`
- artifact: `10185197916`
- artifact digest: `sha256:997c99f495e423673e8550da083b15dfc1a2f146833f64efc3d7da227bda8c47`
- selected markets: **197**
- snapshot observed at: `2026-09-11T04:49:20.492233Z`

The old snapshot remains immutable evidence. V0.1 does **not** rewrite its
selection rank or history profile.

## Asset-class overlay

The original selection logic used a conservative fallback of `crypto` whenever a
market was not present in the older alternative-asset registry. That was safe for
selection, but it is too coarse for execution-domain analysis.

V0.1 therefore applies an explicit classification overlay while preserving the
old selection evidence. The 197 selected markets are classified as:

| Class | Markets |
| --- | ---: |
| Crypto | 96 |
| Equity-linked token | 67 |
| ETF / fund-linked token | 20 |
| Company-reference perpetual | 4 |
| Energy commodity reference | 3 |
| Industrial metal reference | 1 |
| Precious metal reference | 4 |
| Tokenized precious metal | 2 |
| **Total** | **197** |

Examples corrected from the old fallback include WTI, Brent and natural gas as
energy references; copper as an industrial-metal reference; XAU/XAG/XPT/XPD as
precious-metal references; PAXG/XAUT as tokenized precious metals; and verified
stock/ETF/company-reference perpetuals such as TSMX, IBMX, DELLX, KORUX, SOXSX,
URNMX, OPENAI, ANTHROPIC and SPCX.

An `X` suffix alone is never used as proof of a stock or ETF classification.
Unverified future candidates must remain review-required rather than being
guessed into a non-crypto class.

## Materialization profiles

The historical work preserves the original 197-market profile assignment:

| Profile | Markets | Intervals |
| --- | ---: | --- |
| `FULL_INTRADAY` | 30 | 15M, 60M, 4H, 1D, 1W |
| `MULTISCALE_RESEARCH` | 99 | 60M, 4H, 1D, 1W |
| `BREADTH_BACKGROUND` | 68 | 1D, 1W |

This produces **682 symbol × interval partitions**.

Each partition is acquired directly from Pionex and receives:

- one Parquet candle object;
- one JSON receipt;
- exact provider/symbol/interval lineage;
- asset class and preserved source history profile;
- row count and first/last timestamp;
- SHA-256 for the Parquet payload;
- explicit coverage status.

## Historical reach policy

The run is bounded to at most **9,000 records per symbol / interval**, with Pionex
public K-lines paged at at most 500 records per request.

The 9,000-record ceiling intentionally means different native spans by interval.
For a continuously available market it is roughly:

- 15M: up to about 93.75 days before provider/cutoff constraints;
- 60M: up to about 375 days;
- 4H: up to about 1,500 days (~4.1 years);
- 1D / 1W: up to the provider/listing boundary, subject to the same 9,000-row cap.

Pionex may expose less history for newer markets or because of provider-side
historical limits. A verified contiguous partial partition may be stored, but it
must be labeled partial and can never be reported as complete multi-year history.

No synthetic candles, silent interpolation or Binance-to-Pionex splicing are
allowed.

## Holdout boundary

All requests are frozen to a cutoff of:

`2026-08-28T00:00:00Z` exclusive.

A candle is accepted only when it belongs before that protected boundary. If a
provider response crosses the frozen cutoff, the run fails closed and the
unexpected response is not persisted.

## Storage and FREE-ONLY boundary

Persistent generated data goes only to Cloudflare R2 under:

`market-data/pionex/validation-dataset-v0.1`

The existing project FREE-ONLY policy remains controlling:

- monthly project budget: 0 USD;
- R2 operational hard stop: 8 GB;
- V0.1 reserves at most 2 GiB for the materialization run;
- raw provider responses are never persisted;
- every written object receives SHA-256 readback verification;
- the completion pointer is written last.

The workflow has no automatic schedule. It is a manual GitHub `workflow_dispatch`
on reviewed `main` only.

## Private API

**A private Pionex API key is not required for this historical materialization.**
The data source is the public Pionex futures market API.

A future private-API stage may be useful for account, fill, position, realized
slippage and execution calibration. That is a separate authority and is not
introduced here.

## Explicit non-effects

V0.1 does not authorize or perform:

- Core100 training on Pionex data;
- model training of any kind;
- source switching;
- Binance evidence relabeling;
- replacement holdout access;
- formal backtest admission;
- automatic model promotion;
- trade plans;
- real-money orders;
- live trading.

Completion of this dataset means only that the bounded Pionex-native validation
partitions were materialized and audited under the frozen V0.1 contract. It does
not mean all 197 markets have complete multi-year history.
