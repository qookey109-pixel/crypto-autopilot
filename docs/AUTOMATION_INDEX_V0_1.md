# Automation Index V0.1

This is the current schedule view. Workflow files that preserve historical or
regression evidence are classified in `config/project_convergence_v0_1.json`
and should not be read as active production schedules.

## Scheduled workflows after convergence

Current observation (`2026-08-31`): PR #210's Pionex `type=PERP` query is
effective, but scheduled captures #36 through #41 all failed closed on the
required `status` / `contractType` parser contract before R2 client creation.
The V0.12 successor authority retires that schedule atomically and freezes an
explicit preferred/legacy Pionex normalization contract. It never replays,
backfills or regrades the incomplete V0.10 evidence.

| State | Workflow | UTC cadence | Effective behavior |
| --- | --- | --- | --- |
| Current bounded successor | Provider Equivalence V0.12 metadata capture | `:17` and `:47`, only 2026-09-04 02:00 through 2026-09-12 03:59:59.999 | only current metadata schedule after exact protected-main merge; normalized Pionex schema must validate before R2 construction |
| Continuous | Research Signal Layer V0.2 | daily 02:17 | bounded public structured-signal ingestion |
| Continuous | Research Signal Quality V0.1 | daily 02:47 | allowlisted R2 lineage read only |
| Continuous / alerting | Research Automation Health V0.2 | every 2 hours at :57 | GitHub Actions metadata read only; covers every current cron and ignores manual/PR runs when judging automatic health |
| Post-window | Binance USD-M Crypto Core 100 V0.1.2 | every 6 hours at :23 during 2026-09-04 through 09-30 | starts only after V0.10; 10 R2-only shards; fixed pre-holdout source range |
| Conditional post-window | Binance USD-M Crypto Core 100 Training V0.1.2 | Sunday 04:37 | skips until all 100-market detailed-history shards exist |
| Post-window | Pionex Alternative Assets Observability V0.2 | 2026-09-04 02:53, then 09-06/13/20/27 at 03:53 | Pionex `PERP + TRADING` metadata only; validates the 125-candidate catalog, compares it with the prior SHA-bound catalog, estimates four-year capacity and writes R2 evidence plus a safe aggregate artifact |

## Retired cron triggers

The following three workflows reached their binding provider-read cutoff at
`2026-08-27T00:00:00Z`. Their cron triggers are removed by
`config/post_cutoff_schedule_retirement_v0_1.json`; manual dispatch remains
only to prove the fail-closed stop:

- Pionex Public Paper Training V0.1
- Binance Spot R2 Training Governance V0.5
- Binance Spot R2 Monthly Governance V0.5

Their original config/receipt schedule strings remain immutable historical
evidence. They do not automatically resume.

The Research Automation Health V0.1 cron is also retired by V0.2. Its manual
entry remains regression-only, while V0.2 is the single automatic control
plane. Normal execution for all seven current schedules is GitHub `schedule`;
manual dispatch is never required and never counts as cron-health evidence.

## Non-scheduled current checks

- CI and dashboard build/static smoke.
- V0.10/V0.12 critical-path freeze guard and successor-window validation.
- V0.10 scheduled-capture observer retained as historical run-metadata inspection only.

## Prepared but not scheduled

- Pionex Post-window Paper Training V0.2 preserves the existing public adapter
  and Repository Paper Broker, but remains `WAITING_FOR_HOLDOUT_AUTHORITY`.
  Latest-lookback requests may include the frozen 2026-08-28 through 09-03
  candles, so no workflow or cron is created until V0.11 and a separate
  holdout/paper-read authority are complete.
- No automatic Paper Broker simulation is currently running. The V0.1 cron is
  retired after its cutoff, and V0.2 remains prepared without a workflow.
- Pionex Alternative Assets historical candles (`15M / 60M / 4H`) remain
  unauthorized. The active observability schedule reads symbol metadata only;
  K-lines, funding, trades and order books require V0.11 plus a separate
  holdout/candle authority.
- V0.11 synthetic evaluator validation; production R2 evaluation remains unauthorized.

Everything else under `.github/workflows/` is historical, planning-only,
manual regression or explicitly retired. The convergence test requires every
workflow and every cron to have exactly one classification, so a new hidden
schedule cannot be added accidentally.

The machine-readable normal-operation contract is
`config/github_automatic_research_operations_v0_1.json`. It does not let a
workflow grant itself provider, R2, holdout, promotion or trading authority.
