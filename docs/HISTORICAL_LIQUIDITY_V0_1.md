# Historical Liquidity Evidence / Ranking V0.1

## Purpose

Prevent current-market and survivorship bias from entering historical universe selection.

A historical backtest must not use today's turnover, spread, or active-market ordering to decide which symbols would have been selected in the past. Historical liquidity ranking therefore consumes only point-in-time evidence that was already available at the queried timestamp.

This is a research/backtest boundary only. It does not authorize live trading or automatic historical trade-plan generation.

## Upstream authority

Historical liquidity ranking is downstream of `HistoricalUniverseIndex`.

For a requested timestamp, the system first asks the historical-universe layer which symbols have evidence-bounded native coverage for the required intervals. Only those symbols can enter liquidity ranking.

Default V0.1 required intervals:

- `15M`
- `60M`
- `4H`

This preserves the existing Historical Universe -> Backtest Admission rule and prevents a liquidity snapshot from resurrecting a symbol that lacks historical market-data authority.

## Evidence batch

`HistoricalLiquidityBatch` represents one recorded provider-native point-in-time 24h ticker + best-bid/ask snapshot batch.

Each batch freezes:

- provider
- market type
- snapshot id
- snapshot timestamp
- true availability timestamp
- complete per-symbol market values present in the batch
- source reference
- optional SHA-256
- explicit native/proxy provenance

Each market record freezes:

- symbol
- 24h quote turnover
- spread in basis points
- close
- 24h trade count

The batch is treated as one comparison set. V0.1 does not assemble a synthetic ranking by mixing unrelated latest-per-symbol snapshots.

## Point-in-time rules

A batch can be consumed at `as_of_ms` only when:

1. `snapshot_time_ms <= as_of_ms`;
2. `available_at_ms <= as_of_ms`;
3. the snapshot age is within the frozen freshness limit;
4. provider and market type match the query;
5. native-only policy is satisfied.

A later snapshot is never backprojected into an earlier timestamp.

A stale snapshot is not silently carried forward indefinitely.

## Frozen V0.1 policy

Machine-readable policy: `config/historical_liquidity_v0_1.json`.

Baseline values preserve the existing current-universe behavior where applicable:

- target size: 15
- maximum spread: 30 bps
- maximum snapshot age: 24 hours
- rank by 24h quote turnover descending
- then spread ascending
- then symbol ascending for deterministic tie-breaking
- native-only authority
- complete historical-universe coverage required

The target is not a quota. If the spread gate leaves fewer than 15 eligible markets, V0.1 returns fewer rather than forcing low-quality markets into the universe.

## Completeness gate

Selective historical coverage can create severe ranking bias. If only a subset of the evidence-bounded historical universe has liquidity observations, the apparent top markets may simply be the markets for which data happened to be retained.

Therefore V0.1 defaults to `require_complete_universe = true`.

If any symbol in the historical-universe snapshot is absent from the selected liquidity batch, ranking fails closed instead of ranking the partial subset.

Extra symbols that appear in the liquidity batch but are not in the historical-universe snapshot are ignored.

## Provenance boundary

Native/proxy provenance is explicit.

A proxy or external snapshot cannot authorize a Pionex-native ranking when `native_only = true`. Provider names are not used to infer provenance.

The returned `HistoricalLiquiditySnapshot` retains both:

- historical-universe authority references; and
- liquidity batch source reference / SHA-256.

## Current authority status

`config/historical_liquidity_v0_1.json` is `FRAMEWORK_ONLY`.

The ranking method and anti-bias gates are frozen, but no real historical Pionex liquidity evidence series has yet been frozen PASS. The implementation must not be interpreted as proof that historical turnover/BBO snapshots already exist for 2025 or the future eight-year target.

`trade_plan_authorized` remains false.

## Tests

Regression coverage includes:

- deterministic turnover/spread/symbol ranking;
- historical-universe filtering;
- complete-universe evidence requirement;
- later-snapshot backprojection rejection;
- true availability-time enforcement;
- stale-snapshot rejection;
- proxy/native separation;
- non-forced target size after the spread gate;
- conflicting snapshot authority rejection.

## Next evidence step

Real historical liquidity evidence must be acquired or produced with explicit provenance before this layer can become data-authoritative.

After real evidence exists, the next integration step is to require a plan's symbol to be present in the point-in-time Historical Liquidity ranked universe at its `signal_time_ms`, in addition to the existing Historical Universe admission gate.
