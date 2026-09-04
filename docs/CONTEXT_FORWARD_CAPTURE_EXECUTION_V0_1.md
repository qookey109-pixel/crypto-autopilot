# Context Forward Capture Execution V0.1

Status: **AUTHORIZED ON PROTECTED-MAIN MERGE / MANUAL ONE-SHOT / NOT BEFORE 2026-09-12 04:00 UTC / NO CRON**

## Purpose

This authority advances the prepared Context Forward Capture V0.1 by allowing exactly one real CoinPaprika current-snapshot capture after the active Provider Equivalence V0.12 metadata window ends.

It is deliberately a one-shot end-to-end proof before any 4H automation is considered. A successful result proves the public provider transport, deterministic parser, timestamp-quality gates, immutable R2 write path, whole-bucket FREE-ONLY headroom gate, and post-write SHA-256 readback together.

## Why execution waits until September 12

Provider Equivalence V0.12 is the current bounded metadata operation from `2026-09-04T02:00:00Z` through `2026-09-12T03:59:59.999Z`.

Context Forward Capture Execution V0.1 therefore has:

- `not_before_utc = 2026-09-12T04:00:00Z`;
- `expires_utc = 2026-09-19T04:00:00Z`;
- manual `workflow_dispatch` only;
- no `schedule` block and no cron;
- exactly one successful capture allowed.

Before the not-before boundary the runner must stop before R2 client construction or any CoinPaprika request.

## Source contract

The execution authority is bound to the exact Git blob of:

`config/context_forward_capture_v0_1.json`

That prepared contract remains `PREPARED_NOT_ACTIVE`; it is not rewritten to pretend that preparation itself had runtime authority.

The execution layer grants the separately versioned runtime permission after the not-before boundary.

Provider request order is frozen as:

1. `https://api.coinpaprika.com/v1/global`
2. `https://api.coinpaprika.com/v1/tickers/eth-ethereum`

There are zero automatic retries and no provider fallback. The request timeout is 20 seconds and each response is capped at 1 MiB.

## Data-quality contract

The existing Context Forward Capture V0.1 parser remains authoritative for semantic validation. It requires:

- current total crypto market capitalization;
- BTC dominance;
- same-provider ETH USD market capitalization;
- provider timestamps for both components;
- no future provider timestamp;
- no component older than 15 minutes;
- no cross-component timestamp skew greater than 10 minutes;
- finite positive derived `total3_value`;
- exact raw-payload SHA-256 fingerprints.

The semantic formula remains:

```text
BTC market cap = total market cap * BTC dominance / 100
TOTAL3 semantic value = total market cap - BTC market cap - ETH market cap
```

Raw provider payload bytes are not persisted.

## One-shot R2 evidence

The execution writes only two normalized immutable objects:

```text
context/market-regime/v0_1/forward-execution-v0_1/first-success/snapshot.json
context/market-regime/v0_1/forward-execution-v0_1/first-success/receipt.json
```

The snapshot is written first. The receipt is written last.

Both objects require exact-byte immutability and post-write SHA-256 readback. A fresh whole-bucket inventory is required before provider access and again before writes. The existing project hard stop remains 8,000,000,000 bytes.

If a PASS receipt already exists and matches the frozen snapshot, a later manual dispatch returns `ALREADY_COMPLETE` without performing another provider request.

If a snapshot exists without its receipt, or a receipt exists without its snapshot, execution fails closed for manual review. It must not silently overwrite partial evidence.

## Secret boundary

Only GitHub Actions receives the existing R2 secrets:

- `CLOUDFLARE_ACCOUNT_ID`
- `R2_BUCKET_NAME`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`

No secret is written to the report artifact. CoinPaprika Free requires no API key for this path.

## GitHub Actions boundary

Workflow:

`.github/workflows/context-forward-capture-execution-v0-1.yml`

The workflow has `workflow_dispatch` only. It is intentionally not part of the Repository's seven-cron automation-health inventory.

The workflow uploads one secret-free execution report for 90 days and deletes disposable runner output afterward.

## What this authority does not grant

This authority does **not** grant:

- a 4H or any other cron schedule;
- historical backfill;
- raw provider payload persistence;
- replacement holdout access or tuning;
- strategy parameter or score changes;
- risk or leverage changes;
- SHORT execution;
- model promotion;
- trade-plan authority;
- real-money orders;
- live trading.

The replacement holdout remains frozen and unopened.

## Next-stage gate

A future **Context Forward Capture V0.2 4H Schedule Authority** is eligible for review only after this V0.1 one-shot capture produces valid PASS evidence.

That future authority must separately update the cron inventory and Research Automation Health control plane. V0.1 cannot self-promote into a schedule merely because the calendar passes or the one-shot capture succeeds.

## Authority files

- config: `config/context_forward_capture_execution_v0_1.json`
- authority receipt: `research/receipts/2026-09-04-context-forward-capture-execution-v0-1-authority.json`
- runtime contract: `src/crypto_autopilot/providers/context_forward_capture_execution.py`
- runner: `scripts/run_context_forward_capture_execution.py`
- workflow: `.github/workflows/context-forward-capture-execution-v0-1.yml`
