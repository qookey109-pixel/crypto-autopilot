# Automation Index V0.1

Current review: 2026-09-19. [Verified operations and handoff](OPERATIONS_HANDOFF_2026_09_13.md).
History is every two hours under `config/history_cadence_v0_1.json`.
V0.12's window has ended; fixed BTC simulation V0.1 is PASS and retired.
After this reviewed merge, eight workflow files retain cron declarations; bounded/expired entries remain classified separately from current execution.

Core100 History is now **10/10 COMPLETE**. The completed training run
`34918219864` passed operational execution, while the downstream Model Quality
gate is **REJECT**. Threshold replay `34936331199` found no supported threshold
change. Do not restart completed History or loosen model-quality gates from this
index.
Pionex alternative assets `34747992983` succeeded as metadata observability only.
The local Codex `crypto` monitor prompt was refreshed to resolve current main
and its latest handoff at every run. It remains PAUSED; no monitor was resumed
or duplicated. It is separate from the active GitHub runtime schedules.

This is the current schedule view. Workflow files that preserve historical or
regression evidence are classified in `config/project_convergence_v0_1.json`
and should not be read as active production schedules.

## Scheduled workflows after convergence (bounded dates still apply)

Current observation (`2026-08-31`): PR #210's Pionex `type=PERP` query is
effective, but scheduled captures #36 through #41 all failed closed on the
required `status` / `contractType` parser contract before R2 client creation.
The V0.12 successor authority retires that schedule atomically and freezes an
explicit preferred/legacy Pionex normalization contract. It never replays,
backfills or regrades the incomplete V0.10 evidence.

| State | Workflow | UTC cadence | Effective behavior |
| --- | --- | --- | --- |
| Expired bounded successor | Provider Equivalence V0.12 metadata capture | `:17` and `:47`, only 2026-09-04 02:00 through 2026-09-12 03:59:59.999 | only current metadata schedule after exact protected-main merge; normalized Pionex schema must validate before R2 construction |
| Continuous | Research Signal Layer V0.2 | daily 02:17 | bounded public structured-signal ingestion |
| Continuous | Research Signal Quality V0.1 | daily 02:47 | allowlisted R2 lineage read only |
| Continuous / alerting | Research Automation Health V0.2 | every 2 hours at :57 | GitHub Actions metadata read only; covers every current cron and ignores manual/PR runs when judging automatic health |
| Continuous / read-only | Resource Hub Supply Chain V0.2 | daily 01:13 | public catalog commit change-watch only; unchanged source returns NO_CHANGE; no auto install/runtime/PR |
| Website backstop | Dashboard GitHub Pages | daily 04:43 plus approved upstream completion events | authority=false projection; business-content hash suppresses duplicate deploys |
| Conditional post-window | Binance USD-M Crypto Core 100 Training V0.1.2 | Sunday 04:37 | dataset + model-input fingerprint is checked first; exact match returns NO_CHANGE with no retraining or R2 write |
| Post-window | Pionex Alternative Assets Observability V0.2 | 2026-09-04 02:53, then 09-06/13/20/27 at 03:53 | Pionex `PERP + TRADING` metadata only; validates the 125-candidate catalog, compares it with the prior SHA-bound catalog, estimates four-year capacity and writes R2 evidence plus a safe aggregate artifact |

## Retired cron triggers

Core100 History V0.1.2 cron is retired by
`config/core100_history_retirement_v0_1.json` after the governed dataset
reached 10/10 COMPLETE. Generic auto/discover/backfill execution is retired;
only the pre-existing bounded diagnosis and repair modes remain. The original
2026-09-12 cadence config/receipt and exact workflow bytes are preserved as
historical evidence.


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
plane. Normal execution for the current schedule inventory is GitHub `schedule`;
manual dispatch is never required and never counts as cron-health evidence.

## Non-scheduled current checks

- CI and dashboard build/static smoke.
- V0.10/V0.12 critical-path freeze guard and successor-window validation.
- V0.10 scheduled-capture observer retained as historical run-metadata inspection only.
- Context Forward Capture Execution V0.1 is a separately authorized manual one-shot
  after `2026-09-12T04:00:00Z`. It has no cron, does not change the seven-workflow
  health inventory, and may freeze at most one normalized CoinPaprika forward
  snapshot plus receipt in its dedicated R2 namespace. A future 4H schedule
  requires a separate V0.2 authority.

## Prepared but not scheduled

- Pionex Post-window Paper Training V0.2 preserves the existing public adapter
  and Repository Paper Broker, but remains `WAITING_FOR_HOLDOUT_AUTHORITY`.
  Latest-lookback requests may include the frozen 2026-08-28 through 09-03
  candles, so no workflow or cron is created until V0.11 and a separate
  holdout/paper-read authority are complete.
- Fixed BTC simulation V0.1 passed run 34615465566 and is retired. Current
  Live Paper V0.1 has an explicit manual run coordinator, but **no continuous
  Live Paper cron exists**. The older public-paper V0.1 cron remains retired.
- Pionex Alternative Assets historical candles (`15M / 60M / 4H`) remain
  unauthorized. The active observability schedule reads symbol metadata only;
  K-lines, funding, trades and order books require V0.11 plus a separate
  holdout/candle authority.
- V0.11 synthetic evaluator validation; production R2 evaluation remains unauthorized.

Everything else under `.github/workflows/` is historical, planning-only,
manual regression or explicitly retired. The convergence test requires every
workflow and every cron to have exactly one classification, so a new hidden
schedule cannot be added accidentally.

The current machine-readable normal-operation contract is
`config/github_automatic_research_operations_v0_4.json`; V0.2 remains frozen for the History Cadence authority binding and V0.3 records the prior 9-workflow state. It does not let a
workflow grant itself provider, R2, holdout, promotion or trading authority.


## Manual-only audit/export workflows

- `paper-loop-run-package-artifact-v0-1.yml` — verifies an existing Paper Loop Run Package and uploads a GitHub Artifact secondary audit copy. It has no schedule, provider access, holdout access or execution authority.

- `live-paper-run-coordinator-v0-1.yml` — runs exactly one persistent Live Paper step against R2 from an explicit input JSON. It is manual-only, has no cron, and cannot enable private exchange APIs, Scorecard auto-selection, real-money orders or real live trading.
- `live-paper-run-recovery-v0-1.yml` — audits one persisted Live Paper run and may repair only a missing immutable request-result seal after full state/tick/step verification. It is manual-only, performs no provider call, has no cron and never rewrites state/tick/step evidence.
