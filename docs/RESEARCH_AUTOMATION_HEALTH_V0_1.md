# Research Automation Health V0.1

Research Automation Health V0.1 adds two research-only guardrails without
changing the V0.10 metadata-capture path, replacement holdout state, model
promotion or trading authority.

## Active schedules on merge

| UTC schedule | Workflow | Purpose |
| --- | --- | --- |
| Every three hours at `:47` | `research-automation-health-v0-1.yml` | Read GitHub Actions metadata and alert on stale, failed or missing expected runs |
| Daily `02:47` | `research-signal-quality-v0-1.yml` | Verify latest KOL evidence lineage and report `FORECAST_READY`, `METADATA_ONLY` or `NO_DATA` |

The automation-health monitor reads only workflow-run metadata with the
repository `GITHUB_TOKEN`. It filters by the allowed event type, so a passing
pull-request validation cannot masquerade as a scheduled production run.
Jobs outside their authorized time window are reported as `WAITING_WINDOW` or
`EXPECTED_STOP`, not as false failures. A conditional trainer with no completed
dataset is `WAITING_DEPENDENCY`.

The signal-quality job reads exactly three allowlisted R2 objects without an
R2 list operation or write:

```text
research/signal-layer/v0-2/latest.json
  -> immutable manifest.json (verified SHA-256)
     -> immutable signals.json (verified SHA-256)
```

It also checks schema, run ID, generation time, research-only authority and
structured KOL forecast contracts. `METADATA_ONLY` is valid evidence: public
HTML prose is intentionally not converted into a guessed long/short signal.
Stale, future-dated, malformed or lineage-inconsistent evidence fails closed.

## Workflow inventory signal

The health report records the number of total, scheduled, pull-request and
retired-named workflows. This is an operations signal for later CI cleanup; it
does not automatically delete, disable or rewrite historical workflows.

## Prepared post-window cadence

`config/post_window_research_successor_schedule_v0_1.json` records a proposed
four-hour closed-candle roll-forward, weekly V0.6 Shadow ablation and monthly
drift/universe review. It is `PREPARED_NOT_ACTIVE`: there is no workflow for
these proposals and no provider or R2 access until a separate versioned
post-window execution authority is reviewed and merged.

Neither active monitor opens the replacement holdout, reads V0.10 production
receipts, changes a strategy, promotes a model, produces a trade plan, sends an
order or enables live trading.

