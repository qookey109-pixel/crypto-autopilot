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

## Local Quality authority-gate hardening — 2026-09-07

Status: **LOCAL IMPLEMENTATION / OFFLINE VALIDATION ONLY**. This section records
the bounded local change; it is not a claim of a merge, deployment, production
validation or a new execution authority. The frozen configs, receipt and
workflows remain unchanged.

The payload authority validator recognizes 18 prohibition names from
`config/research_signal_layer_v0_2.json` and the `explicitly_not_authorized`
section of
`research/receipts/2026-08-24-research-automation-health-v0-1-authority.json`:

| Rule | Fields |
| --- | --- |
| Required, exactly boolean `false` | `automatic_model_promotion`, `direct_trade_trigger`, `real_money_order`, `live_trading` |
| Optional, exactly boolean `false` when present | `holdout_access`, `trade_plan`, `provider_relabeling` |
| Optional receipt spellings, exactly boolean `false` when present | `v0_10_production_critical_path_change_authorized`, `v0_11_production_receipt_read_authorized`, `replacement_holdout_access_authorized`, `provider_source_switch_authorized`, `historical_universe_membership_authorized`, `formal_backtest_admission_authorized`, `automatic_model_promotion_authorized`, `formal_trade_plan_authorized`, `private_api_authorized`, `real_money_order_authorized`, `live_trading_authorized` |
| Optional producer descriptions, boolean only | `external_source_fetch`, `production_r2_write` |

Optional denials preserve compatibility with the existing six-field V0.2
producer payload. Absence grants no permission. Receipt spellings cannot replace
the four required fields or override a conflicting declaration. Numeric `0`,
strings, `null`, arrays and objects cannot stand in for boolean `false`.
Unknown authority fields fail closed, even when their values are false; new
fields require explicit contract review. Error reports do not echo unknown
field names or values.

Producer descriptions concern the collector, not the Quality evaluator. A
producer's `production_r2_write=true` never permits this evaluator to write R2.
The output `authority` continues to describe the evaluator's own restrictions;
successful SHA verification alone cannot make contradictory input authority
acceptable. The latest/manifest/payload read path and report schema are unchanged.

Regression tests use in-memory objects with recalculated SHA links, so rejected
authority cases reach the actual authority gate. They cover all prohibition
names, malformed values, missing required fields, unknown fields and legacy
compatibility without constructing an R2 client or reading production evidence.
Production payload compatibility remains unverified. Collector parsing,
per-write headroom checks, run-path binding, automation-health freshness and
dashboard integration findings from the broader audit are outside this change.

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
