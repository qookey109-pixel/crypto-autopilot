# Research Automation Handoff V0.1

Status date: `2026-08-31` (`Asia/Taipei`).

This handoff is an operations guide, not execution authority. Repository
`main`, versioned configs and receipts remain authoritative. Detailed History
V0.1.2 has its own post-window R2 authority; this handoff does not independently
enable R2 access, holdout access, model promotion, trade plans, real-money
orders or live trading.

Project: `Qookey Crypto Autopilot`

Repository: `https://github.com/qookey109-pixel/crypto-autopilot`

Public dashboard: `https://qookey109-pixel.github.io/crypto-autopilot/`

## Current metadata transition

- PR #210 is merged at
  `a34cf471876971a97200de4974906743642ed61f`; the Pionex public symbols request
  now explicitly uses `type=PERP`.
- Scheduled V0.10 attempts #36 through #41 reached the frozen perpetual-symbol
  scope, then failed closed on the required provider-field contract. The latest
  observed error is `Pionex status/contractType missing: AAVE_USDT_PERP` in run
  [`33366572161`](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/33366572161).
- The failure occurs before R2 store construction. No R2 read/write, holdout
  access, V0.11 evaluation, trade plan or order occurred.
- Research Signal Layer and Signal Quality remain separate from this capture.
  Research Automation Health V0.1 records the historical V0.10 upstream
  failure; it is not evidence that V0.12 has executed.
- V0.11 remains `NOT_YET_RUN`; however, immutable missing/failed slots make the
  current frozen window ineligible to produce complete 194-slot PASS evidence.
- Exact observation:
  `research/receipts/2026-08-31-v0-10-post-perp-query-schema-mismatch-observation.json`.
  It is evidence only and grants no new execution authority.
- The user separately authorized retiring the remaining V0.10 schedule and
  creating V0.12. On the exact protected-main merge, V0.12 becomes the only
  metadata schedule for `2026-09-04T02:00:00Z` through
  `2026-09-12T03:59:59.999Z`; it does not replay or regrade V0.10.
- Delivery is PR #212. The append-only binding records minimum operational
  commit `80732edee9a8954b53b4b56115ecb0d506591f0a` without rewriting the
  pre-binding authority config or receipt.

## Executive decision

There is no longer a need to wait until noon. Both V0.5 bootstrap operations
have already completed on `main`:

- Monthly governance V0.5 run
  [`32589005957`](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/32589005957)
  completed successfully at `2026-08-23 01:51 Asia/Taipei`, commit `b371b96`,
  with artifact digest
  `1960647b1e7a511d71a1ec6cf8dcf3d3f3ad86acae827377f2409ba71fbce2ad`.
  This satisfies the one-time manual monthly-baseline activation. Do not
  dispatch it again under V0.5.
- Weekly training V0.5 run
  [`32615608243`](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/32615608243)
  completed successfully at `2026-08-23 11:32 Asia/Taipei`, commit `b371b96`,
  in 15 minutes 42 seconds, with artifact digest
  `69d45bc55f846d17ce8ff79a55aa2fa974dd67eec9d11903e67a1319bc41081e`.
  Pipeline completion is `PASS`; model quality is `REJECT`.

The first weekly evidence contains 748 requested markets, 723 audited markets
and 702,023 rows. The quality rejection must be retained because ready classes
did not beat the naive baseline in every fold, configured net growth was below
policy and diagnostic drawdown was above policy. Symbol concentration remained
inside its 10% cap. This is useful negative evidence, not a failed pipeline and
not a model eligible for promotion.

| First-run diagnostic | Observed result | Gate interpretation |
| --- | ---: | --- |
| Crypto walk-forward baseline comparison | 3 / 3 folds improved | Pass for the crypto class only |
| All ready classes improve in every fold | No | `REJECT` |
| Zero-cost net growth / drawdown | -97.236% / 98.825% | Diagnostic only; rejected |
| Configured-cost final equity | approximately USD 93.188 from USD 10,000 | `REJECT` |
| Configured-cost net growth / drawdown | -99.068% / 99.473% | `REJECT` |
| High-cost net growth / drawdown | -99.732% / 99.816% | Stress evidence; rejected |
| Maximum single-symbol signal share | 0.4324% | Passes the 10% concentration cap |

Stablecoin, `other` and tokenized-stock-candidate ready folds did not all beat
their naive baseline. None of these values authorizes a strategy change; they
identify what the Shadow challenger must improve under identical chronological
and cost contracts.

## Current implementation handoff

The prepared V0.6 Shadow implementation and historical Detailed History V0.1
were merged to Repository `main` by PR #177. Crypto Core 100 V0.1.2 now
supersedes V0.1.1 before either predecessor's first provider request or R2
access, preserves the bounded cron stop and narrows materialization to Crypto.

It provides:

- baseline, trend, price/volume and volatility feature-group ablations;
- ECE/MCE calibration and descriptive ATR/ADX/volume regime slices;
- immutable dataset/config/trainer/environment experiment fingerprints;
- bounded search with zero automatic retries or promotion;
- explicit false authority for provider reads, R2 writes, holdout, trade plans,
  real-money orders and live trading.

The runner may use only an already-authorized ephemeral Parquet input. The
prepared V0.6 config does not authorize downloading the production R2 dataset
or adding a GitHub Actions schedule.

Crypto Core 100 V0.1.2 separately provides:

- an official Binance Vision archive-directory catalog with 817 previously
  observed eligible markets and a deterministic 100-Crypto-market selection;
- tokenized-stock/ETF, other-asset and historical-absence candidates retained
  as discovery evidence but excluded from Core materialization;
- 10 serialized, resumable R2 shards covering 2022-08 through 2026-07 at
  15m/1h/4h;
- a weekly causal intraday trainer with chronological baseline, cost, drawdown
  and exposure diagnostics after dataset completion;
- an execution not-before guard at `2026-09-04T02:00:00Z`, so the frozen V0.10
  window and replacement holdout remain untouched;
- a backfill stop at `2026-10-01T00:00:00Z`, so future annual cron occurrences
  exit before provider or R2 access while weekly completed-dataset training can
  continue.

## Operational schedule

| Time (`Asia/Taipei`) | Action | State / gate |
| --- | --- | --- |
| 2026-08-23 01:51 | First monthly V0.5 governance baseline | **DONE / PASS**; never manually repeat under V0.5 |
| 2026-08-23 11:32 | First weekly V0.5 data, training and review | **DONE / PIPELINE PASS / MODEL REJECT**; retain all evidence |
| 2026-08-23 through 2026-08-26 | Finish local V0.6 review, PR delivery and documentation | Local/synthetic only; no V0.6 provider or R2 access |
| Hourly at `:07` until 2026-08-27 08:00 | Existing Pionex public paper training | Existing bounded paper authority only; Pionex Demo remains manual |
| Daily 10:17 | Public KOL research collection | Dedicated R2 namespace; structured forecasts only, prose stays metadata |
| Daily 10:47 | KOL research quality check | Three exact R2 reads; lineage/time/authority verification; no list/write |
| Every three hours at `:47` | Research automation health | GitHub Actions metadata only; alerts on stale, failed or missing jobs |
| 2026-08-27 08:00 | V0.5 Binance and Pionex provider-read stop | Automatic post-stop resume is forbidden |
| 2026-08-27 08:00 through V0.12 main merge | V0.10 frozen metadata capture evidence | Runs #36–#41 remain fail-closed evidence; remaining schedule is retired atomically, with no replay or manual backfill |
| 2026-09-04 10:00 through 2026-09-12 11:59:59.999 | V0.12 successor metadata window | Only current metadata schedule after exact main merge; 194 hourly slots / 388 attempts, separate R2 namespace, no holdout or production evaluation |
| 2026-09-04 14:23 first eligible cron, then every six hours through Sep 30 | Crypto Core 100 V0.1.2 catalog then next incomplete shard | 10 serialized R2-only shards; source ends 2026-07; expires Oct 1 08:00 |
| Sunday 12:37 after detailed dataset completion | Crypto Core 100 Training V0.1.2 | Walk-forward research; `REJECT` is retained and never promoted |
| 2026-09-04 10:53, then Sep 6/13/20/27 at 11:53 | Pionex Alternative Assets Observability V0.2 | validates the 125-candidate Pionex metadata catalog, compares prior SHA-bound evidence and estimates four-year capacity; no candle/funding/trade/order-book reads |
| After 2026-09-04 09:59:59.999 | Prepare and merge separate V0.11 production-evaluation authority | Do not read production V0.10 R2 receipts before authority exists |
| After V0.11 evaluation | Review exact 194-slot completeness and provider-vector stability | Any missing slot, disagreement or drift fails closed |
| Only after a future V0.11 PASS | Consider a separate replacement-holdout access authority | Stability PASS alone does not open holdout candles |
| Only after post-window V0.6 authority | Run real-data Shadow challenger and successor automation | Still research-only; no automatic promotion or trading |

## Post-window successor schedule — proposed, not active

The next online authority should chain jobs by validated evidence rather than
run independent crons that can race:

1. Weekly Sunday `02:37 UTC`: rebuild the canonical Binance Spot daily dataset,
   run V0.5-equivalent quality gates and publish the immutable R2 pointer last.
2. After the weekly pointer passes round-trip validation: run the four bounded
   V0.6 Shadow ablations, ECE/MCE and regime diagnostics against the exact same
   dataset fingerprint.
3. Weekly handoff output: publish only aggregate `PASS` / `REJECT`, sample
   counts, calibration, drawdown, exposure and experiment IDs. Retain failed
   experiments; never auto-promote a winner.
4. Monthly day 1 `03:37 UTC`: review market-list changes, classification,
   survivorship limitations, 4-8 week feature drift, model staleness, duplicate
   experiments, R2 pointer consistency and retention dry-run.
5. KOL/sentiment research: capture source/time/latency/duplicate metadata in a
   separate daily evidence layer and aggregate weekly. Keep it outside the
   price model until it independently beats its baseline without look-ahead.
6. GitHub Pages: show only system state, latest data date, Paper Broker equity,
   quality result, maximum drawdown, signal count and next schedule. Never
   publish raw Parquet, full training history or model objects.

## Immediate owner checklist

- [x] Preserve first monthly baseline evidence; do not repeat manual activation.
- [x] Preserve first weekly pipeline `PASS` and model `REJECT` separately.
- [x] Prepare V0.6 Shadow code, tests, config and experiment registry locally.
- [x] Merge PR #177 after all seven GitHub checks pass.
- [x] Preserve V0.6 as research-only; Crypto Core 100 V0.1.2 may use R2 only under
  its exact post-window authority.
- [x] Add event-aware automation health and daily KOL evidence quality schedules
  without changing V0.10, holdout or trading authority.
- [x] At `2026-08-27 08:00 Asia/Taipei`, verify V0.5/Pionex jobs fail closed
  before provider access and leave V0.10 as the only metadata capture path.
- [x] Confirm PR #210 merged and preserve post-merge runs #36–#41 as immutable
  fail-closed evidence.
- [x] Confirm the V0.10 parser failure precedes R2 store construction and did
  not open the replacement holdout.
- [x] Record explicit user authority to stop the remaining V0.10 schedule and
  create the separately versioned V0.12 successor contract.
- [ ] Merge the exact protected-main V0.12 change set only after CI and human
  review; no pre-merge provider or R2 execution is authorized.
- [ ] After the V0.12 metadata window ends, create a separate production
  evaluation authority before any V0.12 receipt read.

## Next decision

Review and merge the exact V0.12 protected-main change set only after all CI
checks pass. The merge atomically retires the V0.10 schedule and enables the
bounded V0.12 schedule; this handoff alone does not execute provider requests
or R2 access. After the window, freeze the observed lineage and create a
separate production-evaluation authority. Keep provider separation, the 0 USD
budget, no backfill, unopened holdout, zero model promotion and zero trading
authority.

## Stop conditions

Stop and record evidence rather than retrying when any of these occurs:

- model quality is `REJECT` or `NOT_READY`;
- a V0.10 slot is missing, stale or internally inconsistent;
- R2 headroom, provider freshness, lineage or exact config binding fails;
- an action would read the replacement holdout, switch providers, relabel
  Binance as Pionex-native, enable promotion or change trading authority;
- a task requires paid cloud capacity or secret disclosure.

## New-chat continuation

Copy this into a new task:

> Continue `qookey109-pixel/crypto-autopilot` from latest `main`. PR #210 is
> merged at `a34cf471876971a97200de4974906743642ed61f`; V0.10 runs #36–#41 fail
> closed with `Pionex status/contractType missing: AAVE_USDT_PERP` before R2
> client construction. The user authorized atomic V0.10 schedule retirement
> plus a bounded V0.12 successor window. Read `PROJECT_STATUS.md`,
> `docs/RESEARCH_AUTOMATION_HANDOFF_V0_1.md` and
> `config/provider_equivalence_v0_12_successor_metadata_window_v0_1.json`
> first. Preserve frozen V0.10 evidence, production evaluation `NOT_YET_RUN`, replacement
> holdout `FROZEN_UNOPENED`, provider separation, PAPER-ONLY and 0 USD. Do not
> replay/backfill V0.10 or read V0.12 R2 receipts without a separate authority.
> Verify the exact protected-main PR/commit binding and CI before asking for
> merge approval.
