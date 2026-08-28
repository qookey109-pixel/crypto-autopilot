# Binance Vision Bulk Source V0.1

Updated: 2026-08-18

## Purpose

Use Binance's official public archive at `data.binance.vision` as the preferred bulk-delivery path for long-horizon Binance USDⓈ-M trade Klines and Mark Price Klines.

This is a **Binance-native research source**. It does not replace or relabel the existing Pionex-native M1/M1A/M1B authority.

## Why bulk archives

The official `binance/binance-public-data` project documents daily and monthly public data packages. USD-M Futures Kline files are derived from `/fapi/v1/klines`; dedicated futures downloaders also exist for `markPriceKlines`.

For hundreds of markets over many years, monthly archive objects reduce REST pagination pressure and provide an official integrity sidecar for every ZIP.

## Coverage boundary

The official Python download helpers describe Futures data availability from `2020-01-01` onward. V0.1 treats that date as the archive-helper baseline, **not** a guarantee that every individual symbol existed from that date.

The project target remains "maximum available history, capped at eight years." It must never synthesize 2018/2019 perpetual history by substituting Spot data or by extrapolating before a market existed.

Actual first/last observations are discovered and receipted per symbol and dataset.

## Approved V0.1 bulk datasets

### Trade Klines

Archive path shape:

```text
data/futures/um/<monthly|daily>/klines/<SYMBOL>/<INTERVAL>/<SYMBOL>-<INTERVAL>-<PERIOD>.zip
```

V0.1 intervals: `15m`, `1h`, `4h`.

### Mark Price Klines

Archive path shape:

```text
data/futures/um/<monthly|daily>/markPriceKlines/<SYMBOL>/<INTERVAL>/<SYMBOL>-<INTERVAL>-<PERIOD>.zip
```

V0.1 intervals: `15m`, `1h`, `4h`.

### Not approved as bulk authority yet

- Funding: use the verified REST `/fapi/v1/fundingRate` path until an official bulk funding archive is independently established.
- Open Interest: the V0.1 bulk layer does not promote Vision `metrics` archives to canonical OI. Binance's official REST OI history remains limited to the latest one month, so long-term OI requires forward accumulation or a separately reviewed source.

## Integrity gate

Every admitted archive must pass all of these gates:

1. deterministic logical archive key;
2. matching official `<zip>.CHECKSUM` file;
3. checksum filename matches the expected ZIP filename;
4. ZIP SHA-256 exactly matches the official checksum;
5. ZIP contains exactly the expected CSV member;
6. rows parse successfully;
7. timestamps are strictly ordered and unique;
8. trade Klines pass the existing project candle audit;
9. Mark Price bars have exact close boundaries and no gaps;
10. no interpolation or silent repair.

A file merely existing on the archive is **not** sufficient authority.

## Archive revisions

The official Binance public-data README explicitly notes that archived files may later be updated after issues are discovered and publishes examples of replaced archives/checksums.

Therefore a logical archive identity is not assumed immutable forever. The project freezes the observed archive SHA-256. If the same logical archive later appears with a different SHA-256, V0.1 fails closed with a revision conflict and requires explicit review before replacing prior evidence.

This prevents upstream corrections from silently changing a historical backtest dataset.

## Monthly vs daily policy

- Completed historical months: prefer monthly archives.
- Current/incomplete month: daily archives may be used.
- Do not mix monthly and daily versions of the same logical time range without a deterministic reconciliation receipt.

## No-data policy

Missing archive / HTTP 404 must become explicit `NO_DATA` acquisition evidence. It must not be silently skipped and it must not be interpreted as market inactivity unless separately supported by listing/universe authority.

## R2 namespace

Future materialization must remain provider-separated, for example:

```text
market-data/binance_usdm/perp/BTCUSDT/15m/...
```

Never write Binance archive data to:

```text
market-data/pionex/...
```

The two providers may later be compared by an overlap/equivalence gate, but they remain independent evidence authorities.

## Implementation

`src/crypto_autopilot/binance/vision.py` provides:

- deterministic archive URL/key generation;
- CHECKSUM parsing and SHA-256 verification;
- in-memory ZIP/CSV ingestion;
- strict trade-Kline and Mark-Price audit;
- provider-separated archive receipts;
- archive-revision conflict detection.

`config/binance_vision_v0_1.json` freezes this policy.

## Next proof

Run a small credential-free live proof against fixed completed archives, for example BTC/ETH/SOL:

1. one completed monthly `15m` trade-Kline archive per symbol;
2. one completed monthly Mark Price archive per symbol;
3. download each official `.CHECKSUM`;
4. verify ZIP SHA-256;
5. parse and audit all rows;
6. freeze source URLs, checksums, row counts and first/last timestamps in a GitHub artifact/receipt;
7. only after that PASS, design the large Binance Vision → R2 backfill.

No live trading or private API access is authorized by this work.
