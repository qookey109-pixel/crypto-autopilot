# Binance Funding R2 Scope & Budget Determination V0.1

## Purpose

Determine whether the frozen 15-symbol Binance Funding coverage materially changes the existing Cloudflare R2 capacity envelope **before any Funding data is written to R2**.

A PASS/NO-MATERIAL-CHANGE result is a budget decision only. It is not Funding materialization authority.

## Authorities

- Funding Coverage: `research/receipts/2026-08-18-binance-funding-coverage.json`
- Funding Source Proof: `research/receipts/2026-08-18-binance-funding-source-proof.json`
- Existing Binance Trade R2 budget: `research/receipts/2026-08-18-binance-observed-r2-budget.json`
- R2 pricing/guardrails: `config/r2_budget_v0_1.json`
- Protocol: `config/binance_funding_r2_budget_v0_1.json`

## Frozen coverage shape

The Funding Coverage authority contains:

- 1,010 available symbol-months;
- 30,735 calendar-days across those months;
- zero internal monthly archive-presence gaps;
- 95 symbol-year intersections, therefore 95 planned annual canonical Funding objects under the frozen partition scheme.

## Real Parquet calibration

The budget runner does not borrow Trade-Kline bytes-per-row.

It re-fetches the checksum-pinned BTCUSDT, ETHUSDT and SOLUSDT `2024-01` Funding archives from the frozen Funding Source Proof authority, runs the same Funding parser and writes each source month to Zstd Parquet **locally in the GitHub runner only**.

For conservative scaling, the budget uses the largest measured `Parquet bytes / row` among the three proof symbols.

No R2 upload occurs.

## Conservative row projection

The capacity projection deliberately does not assume the common eight-hour Funding cadence.

Every calendar hour in every available symbol-month is budgeted as if a Funding event could occur once per hour:

```text
projected rows = 30,735 calendar-days x 24 = 737,640 rows
```

This is a budget upper bound, not a claim that the source actually funds hourly.

Actual source-declared `funding_interval_hours` remains preserved by the Funding materializer.

## Storage projection

The frozen scenarios are:

- canonical Funding = projected rows x worst observed Funding Parquet bytes-per-row;
- canonical + retained staging = canonical x 2;
- Funding capacity stress = canonical x 3.

The Funding 3x storage result is then added to the existing observed Binance Trade 3x storage authority (`7.722336067 GB`) rather than evaluated in isolation.

The combined stress must remain below the project `8 GB` storage WARN guardrail to qualify as `NO_MATERIAL_BUDGET_CHANGE`.

## R2 operation projection

Canonical Funding is annual per symbol. The frozen coverage contains 95 annual objects.

Planned Funding R2 requests are conservatively modeled as:

- Class A: two writes per annual object plus four global metadata writes;
- Class B: two reads per annual object plus four global metadata reads;
- operation stress = planned x 3.

Funding stress operations are added to the existing Trade R2 operation-stress authority before comparison with the existing WARN guardrails.

Source HTTP downloads/checksum requests are not R2 operations.

## Determination

The live workflow emits one of:

- `NO_MATERIAL_BUDGET_CHANGE` — combined planned/stress usage remains PASS and below WARN thresholds;
- `MATERIAL_CHANGE_REVIEW_REQUIRED` — the added Funding scope reaches a WARN boundary and requires a separate budget review before materialization;
- `BLOCK` — a frozen R2 BLOCK boundary is reached.

The determination is evidence-driven from live Parquet calibration; it is not hard-coded.

## Safety boundary

This phase does not authorize:

- Funding R2 writes;
- Funding bulk materialization;
- provider splicing;
- Pionex-native relabeling;
- Binance -> Pionex source switching;
- Historical Universe membership;
- backtest admission;
- automatic trade plans;
- real-money orders;
- live trading.

Only after a frozen budget determination may a separate explicit Funding materialization authority be proposed.
