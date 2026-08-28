# Binance USD-M Detailed History V0.1

Status: **AUTHORIZED AFTER V0.10 WINDOW / NOT YET MATERIALIZED**.

This stage expands research coverage beyond the original 15-contract evidence
basket. It creates a provider-separated Binance USD-M dataset for intraday
strategy-model research without relabeling Binance evidence as Pionex-native.

## Scope

- target: 250 USDT-quoted historical markets;
- source: official Binance Vision monthly USD-M trade-Kline archives;
- window: 2022-08 through 2026-07, exactly 48 complete months;
- native intervals: 15m, 1h and 4h;
- persistent store: Cloudflare R2 only;
- repository and Pages: no raw Kline projection or persistent generated copy.

The source window ends before the replacement holdout. Execution is blocked
until `2026-09-04T02:00:00Z`, after the frozen V0.10 metadata-capture window.
This permits the backfill to run later without reading replacement-holdout
candles.

The stage stores OHLCV trade Klines, not tick-by-tick individual trades. The
three native intervals are sufficient for the current technical, trend,
volatility and price/volume research features while keeping the FREE-ONLY R2
envelope bounded.

## Historical universe construction

The workflow lists the official anonymous Binance Vision archive bucket. It
does not depend only on a current exchange catalog. A market is eligible only
for months whose 15m, 1h and 4h archives and official checksum objects are all
present.

The deterministic 250-market selection preserves:

- the original 15 continuity symbols;
- at least 20 heuristic tokenized-stock or ETF candidates;
- all 19 currently observed eligible markets that do not reach the end of the
  historical window, for survivorship-bias evidence;
- at least 175 markets that do reach the window end.

Tokenized-stock classification is a research heuristic. It does not prove
legal, economic or redemption equivalence with a US equity, and it cannot
promote a market into a trading universe.

A read-only 2026-08-24 directory verification observed 829 eligible-format
USDT prefixes, 817 markets with common three-interval coverage, 39 heuristic
tokenized-stock candidates, 19 historical-absence candidates and 798 markets
reaching 2026-07. The design retains all 19 historical-absence candidates
instead of inventing a larger quota.

## Materialization

The catalog is split into 25 serialized shards of 10 markets. A scheduled run
executes at most one incomplete shard every six hours. Each monthly archive is
checksum-verified, decoded, candle-audited and stored in a versioned
`market-data/binance_usdm/detailed-v0.1/` namespace. Existing objects must be
exact-candle equal; conflicts fail closed.

Every authorized run applies the fresh whole-bucket 8 GB hard stop before
provider access and again before writes. Immutable shard receipts are written
after data objects and the mutable progress pointer is written last. An
interrupted shard is therefore safely resumable without overwriting conflicting
history.

## Training

After all shards are complete, the weekly training job reads the governed R2
receipts and raw partitions, then builds causal 15m examples with already-closed
1h and 4h context. The frozen feature contract includes:

- short-horizon returns and EMA structure;
- RSI and MACD;
- ADX, +DI and -DI;
- rolling VWAP distance and relative-volume Z-score;
- Donchian position;
- ATR and Bollinger bandwidth percentiles;
- realized and Parkinson volatility;
- Kaufman efficiency, choppiness and volatility-adjusted momentum.

The trainer performs chronological walk-forward evaluation, naive-baseline
comparison, fee/slippage scenarios, maximum-drawdown diagnostics and symbol
concentration checks. A model-quality `REJECT` remains valid research evidence
and is never promoted automatically.

## GitHub versus R2

GitHub contains the versioned strategy and training authority:

- baseline strategy: `docs/STRATEGY_V0_1.md`, `config/strategy_v0_1.json` and
  `src/crypto_autopilot/strategy.py`;
- public paper candidate engine: `config/paper_training_v0_1.json`,
  `src/crypto_autopilot/paper/training.py` and
  `src/crypto_autopilot/features/advanced.py`;
- Spot daily research model: `src/crypto_autopilot/training/online.py` and
  `src/crypto_autopilot/training/quality.py`;
- detailed intraday research model: `src/crypto_autopilot/training/detailed.py`;
- orchestration: `.github/workflows/binance-usdm-detailed-history-v0-1.yml` and
  `.github/workflows/binance-usdm-detailed-training-v0-1.yml`.

R2 contains generated catalogs, Parquet history, receipts, model parameters and
metrics. Secrets remain GitHub Actions secrets and are never committed.

## Authority boundary

This stage does not authorize replacement-holdout access, historical-universe
membership, formal backtest admission, Pionex-native relabeling, provider
switching, model promotion, trade plans, private API use, real-money orders or
live trading. It does not modify the frozen V0.10 production-critical path.
