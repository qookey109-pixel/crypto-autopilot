# R2 Cost & Budget Gate V0.1

Updated: 2026-08-18

## Purpose

Freeze a cost boundary for the historical-data plan before expanding beyond the bounded pilot. This gate covers Cloudflare R2 Standard storage and R2 operations only. It does not authorize live trading and it does not authorize the full historical backfill by itself.

## Source of truth

- Capacity basis: `research/estimates/2026-08-18-historical-capacity.json`
- Budget estimate: `research/estimates/2026-08-18-r2-cost-budget.json`
- Budget policy: `config/r2_budget_v0_1.json`
- Gate implementation: `src/crypto_autopilot/r2_budget.py`
- CI CLI: `scripts/check_r2_budget.py`

## Current Cloudflare R2 Standard pricing snapshot

Pricing was checked against Cloudflare's official R2 pricing documentation on 2026-08-18.

- Included storage: 10 GB-month / month
- Included Class A operations: 1,000,000 / month
- Included Class B operations: 10,000,000 / month
- Standard storage overage: USD 0.015 / GB-month
- Class A overage: USD 4.50 / million operations
- Class B overage: USD 0.36 / million operations
- Internet egress: free
- Billable overage is rounded up to the next billing unit.

Pricing source: `https://developers.cloudflare.com/r2/pricing/`

## Capacity basis

The estimate is derived from the verified M1B seven-day payload:

- 15 symbols
- 3 native intervals: `15M`, `60M`, `4H`
- 13,230 rows
- 45 Parquet objects
- 425,161 total Parquet bytes

Linear sizing for the target design:

| Scenario | Estimated storage | R2 Standard storage cost |
| --- | ---: | ---: |
| 250 markets × 8 years, canonical only | 2.956 GB | USD 0/month |
| Canonical + retained staging | 5.912 GB | USD 0/month |
| 3× capacity stress | 8.868 GB | USD 0/month, but budget WARN |
| 15 GB | 15 GB | about USD 0.075/month |
| 20 GB | 20 GB | about USD 0.15/month |
| 50 GB | 50 GB | about USD 0.60/month |
| 100 GB | 100 GB | about USD 1.35/month |
| 500 GB | 500 GB | about USD 7.35/month |
| 1,000 GB | 1,000 GB | about USD 14.85/month |

The project deliberately budgets retained staging because the current resumable implementation keeps staged Parquet objects after canonical finalization.

## Operation model

The current fresh successful partition path is budgeted at approximately:

- 8 Class A operations per partition
- 5 Class B operations per partition

For the 28,000-partition upper design target this is approximately:

- 224,000 Class A operations
- 140,000 Class B operations

A 3× transient/retry factor produces approximately:

- 672,000 Class A operations
- 420,000 Class B operations

Both remain inside the current R2 Standard included monthly operation envelope.

## Gate policy

### Storage

- `<= 8 GB-month`: PASS
- `> 8 GB-month` and `<= 10 GB-month`: WARN
- `> 10 GB-month`: BLOCK / explicit cost review required

The 8 GB warning preserves 2 GB of project headroom below the current 10 GB free storage allowance.

### Class A

- `<= 750,000/month`: PASS
- `> 750,000` and `<= 1,000,000/month`: WARN
- `> 1,000,000/month`: BLOCK / explicit cost review required

### Class B

- `<= 7,500,000/month`: PASS
- `> 7,500,000` and `<= 10,000,000/month`: WARN
- `> 10,000,000/month`: BLOCK / explicit cost review required

## Current gate result

The planned 250-market × 8-year candle design with canonical + retained staging is expected to be:

**PASS — estimated R2 cost USD 0/month**

The 3× storage stress scenario is:

**WARN — still estimated USD 0/month, but inside the reserved-headroom review zone**

This result does not account for unrelated R2 usage in the same Cloudflare account. Before a large expansion, the actual account-level R2 usage must be reviewed because Cloudflare's included usage is shared at the account level.

## CI enforcement

CI executes:

```bash
python scripts/check_r2_budget.py
```

The command recomputes the planned usage against the frozen policy. A `BLOCK` result exits non-zero. A mismatch between the frozen expected result and the computed result also fails CI.

## Authorization boundary

This gate authorizes continuing the bounded historical backfill proof under the current R2 budget envelope. It does **not** authorize:

- live-money trading;
- private Pionex API use;
- silently changing the historical data provenance;
- bypassing audit/canonical-conflict gates;
- automatic expansion above a WARN/BLOCK boundary;
- Cloudflare Workers / Workflows / Queues / D1 spend without a separate cost gate.
