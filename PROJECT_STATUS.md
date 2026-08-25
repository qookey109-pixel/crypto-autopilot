# Project Status

Updated: 2026-08-24

## Project

Qookey Crypto Autopilot

Repository: `qookey109-pixel/crypto-autopilot`

Public dashboard: `https://qookey109-pixel.github.io/crypto-autopilot/`

Repository branch `main` is the live formal authority and is intentionally not self-pinned to a moving commit SHA in this file. Frozen receipts/configs remain immutable detailed evidence; this file is only the current status index.

## Current formal stage

**PIONEX M1/M1A PASS / M1B R2 PASS / BINANCE 2025 R2 PILOT PASS / BINANCE FUNDING V0.2 R2 MATERIALIZATION PASS / BINANCE SPOT R2 TRAINING GOVERNANCE V0.5 AUTHORIZED / BINANCE USD-M DETAILED HISTORY V0.1.1 AUTHORIZED AFTER V0.10 WINDOW NOT_STARTED / DETAILED HISTORY V0.1 SUPERSEDED BEFORE EXECUTION / V0.4 WEEKLY AND MONTHLY EXECUTION RETIRED / V0.3 DAILY TRAINING RETIRED / RESEARCH SIGNAL LAYER V0.2 ACTIVE / RESEARCH SIGNAL QUALITY V0.1 AUTHORIZED READ_ONLY / RESEARCH AUTOMATION HEALTH V0.1 AUTHORIZED READ_ONLY / POST-WINDOW RESEARCH SUCCESSOR SCHEDULE V0.1 PREPARED_NOT_ACTIVE / PIONEX-BINANCE EQUIVALENCE V0.1 DEFINITIVE FAIL / PIONEX PUBLIC PAPER TRAINING V0.1 AUTHORIZED BOUNDED / V0.5 RENDER FREE TRANSPORT PASS / V0.6 RENDER TRANSPORT TRANSITION PASS / V0.7 RENDER METADATA PROTOCOL HISTORICAL / V0.8 SHARED SECRET HANDSHAKE PASS FROZEN / V0.9 RENDER RELAY SMOKE PASS FROZEN / V0.10 FINAL ATOMIC METADATA CAPTURE CUTOVER EFFECTIVE / V0.2 SELF-HOSTED SCHEDULE RETIRED / V0.10 GITHUB-HOSTED SCHEDULE CURRENT / V0.10 CAPTURE-WINDOW OPERATIONS PREPARED PASS / V0.10 MID-WINDOW EMERGENCY TEMPLATE PREPARED NOT_AUTHORITY / V0.10 RENDER FINAL PRE-WINDOW READONLY RECHECK PASS / V0.11 SYNTHETIC FAILURE REHEARSAL 12/12 PASS / V0.11 POST-WINDOW EXECUTION PACKAGE PREPARED EXECUTION NOT_AUTHORIZED / V0.11 PRODUCTION EVALUATION AUTHORITY TEMPLATE PREPARED EXECUTION NOT_AUTHORIZED / V0.11 METADATA STABILITY EVALUATOR PREPARED EXECUTION NOT_AUTHORIZED / REPLACEMENT HOLDOUT FROZEN_UNOPENED / METADATA STABILITY NOT_YET_RUN / HISTORICAL UNIVERSE MEMBERSHIP NOT_READY / TRADE-KLINE W1 MATERIALIZATION NOT_AUTHORIZED / PAPER-ONLY**

### Binance USD-M Detailed History V0.1.1 — AUTHORIZED AFTER WINDOW / NOT STARTED

- A separate provider-separated research path expands detailed coverage from
  the original 15-contract basket to a deterministic 250-market target.
- The fixed source window is 2022-08 through 2026-07, with native 15m, 1h and
  4h Binance Vision trade-Kline archives. It ends before the replacement
  holdout and performs no holdout candle access.
- Execution cannot begin before `2026-09-04T02:00:00Z`, after the frozen V0.10
  metadata-capture window. Before that instant its workflow exits without
  provider or R2 access. Backfill authority expires at
  `2026-10-01T00:00:00Z`; later annual cron occurrences also stop before any
  provider or R2 access, while completed-dataset weekly training remains active.
- Selection preserves the original 15 continuity symbols, at least 20
  heuristic tokenized-stock/ETF candidates, all 19 currently observed eligible historical-absence
  candidates and at least 175 markets reaching the window end. These labels do
  not authorize historical-universe membership or trading.
- Twenty-five serialized, resumable R2 shards run at most once every six hours.
  Every run applies a fresh whole-bucket 8 GB hard stop before provider access
  and again before writes; exact existing-object equality and post-write
  SHA-256 readback are mandatory.
- After the complete dataset exists, a weekly research trainer calculates
  causal multi-timeframe technical features and performs chronological
  walk-forward, baseline, cost, drawdown and exposure diagnostics. `REJECT`
  remains evidence and cannot promote a model.
- Raw history remains R2-only and is not projected to Pages. GitHub contains
  the strategy/config/training source and versioned authority.
- V0.1.1 supersedes V0.1 before the first provider request or R2 access. V0.1
  config/receipt remain immutable, and V0.1.1 adds only the version change and
  bounded backfill stop.
- Authority/config: `config/binance_usdm_detailed_history_v0_1_1.json` and
  `research/receipts/2026-08-24-binance-usdm-detailed-history-v0-1-1-bounded-authority.json`.
- Current addendum: `docs/BINANCE_USDM_DETAILED_HISTORY_V0_1_1.md`; the full
  data design remains in `docs/BINANCE_USDM_DETAILED_HISTORY_V0_1.md`.
- This stage does not change V0.10, relabel Binance as Pionex, switch sources,
  open the holdout, admit a formal backtest, promote a model or trade.

### Binance Spot R2 Training Governance V0.5 — AUTHORIZED

- V0.3 daily and V0.4 weekly/monthly execution are retired. V0.5 trains once per week at Sunday
  `02:37 UTC` (`10:37 Asia/Taipei`).
- The first scheduled V0.5 weekly run `32615608243` completed successfully at
  `2026-08-23 11:32 Asia/Taipei` on `main`; the evidence pipeline passed while
  `model_quality_gate.status=REJECT`. The rejection remains research evidence
  and authorizes no promotion or trading.
- Each weekly run rebuilds the provider-separated dataset, checks complete tails,
  catalog/audited coverage, feature order and chronological partitions, trains the
  deterministic daily-direction model, and writes immutable V0.5 evidence.
- Monthly universe review runs on day 1 at `03:37 UTC` (`11:37 Asia/Taipei`). It
  compares active-market snapshots, catalog absences and heuristic tokenized-stock
  classification changes. Catalog absence is not treated as proof of delisting.
- The initial V0.5 monthly baseline was created successfully by manual run
  `32589005957` at `2026-08-23 01:51 Asia/Taipei`. This consumed the one-time
  activation; another manual activation is unauthorized and fails before
  publication. Scheduled reviews remain separate, and the workflow has no push
  trigger.
- The current-active catalog cannot authorize historical universe membership;
  survivorship bias remains `REVIEW_REQUIRED` and formal backtest admission remains
  false.
- Both schedules stop before provider or R2 access at
  `2026-08-27T00:00:00Z`. Automatic post-window resume is not authorized.
- Cloudflare R2 remains the only persistent generated-data store. Secret-free
  evidence is retained online and runner workspaces are removed at the end.
- Model promotion, source switching, holdout access, trade plans, real-money orders
  and live trading remain unauthorized.
- Pre-publish validation completes before any R2 client is constructed. A missing
  or unsafe review contract cannot update R2 or its latest pointer.
- The executable V0.5 config is exact-byte bound to its versioned authority
  receipt. The first V0.5 weekly/monthly comparison uses the SHA-256-verified
  V0.3 online PASS counts (748 requested / 723 audited / 701,275 rows); a malformed existing
  V0.5 pointer fails closed instead of falling back.
- Dataset receipts bind the exact catalog and Parquet SHA/size; Parquet provider,
  schema, OHLCV bounds, row/symbol/audit and tail evidence are checked before any
  R2 write. Total rows must retain at least 80% of the comparison baseline.
  Model/metrics provider, feature, target, authority and raw/canonical hash
  contracts are likewise checked before publication.
- Evidence-correctness hardening rejects stale-tail series, enforces the exact
  ordered feature contract, records chronological train/validation fingerprints,
  compares every configured class with ready folds against a train-prevalence
  baseline, and separates
  successful pipeline execution from the research-only model-quality result.
- The quality gate checks configured costs, net growth, maximum drawdown and symbol
  concentration. A rejected model is still published as evidence; it is never
  promoted automatically.
- Monthly R2 pointer reads are namespace/schema/provider/run-id/SHA allowlisted.
  Monthly catalog collapse is blocked; the current review is governance-bound and
  contract-validated before R2 writes, and the stop window is checked again before
  every actual upload. Push execution is absent so changes do not replace the
  prior-month comparison baseline.
- Operations index and post-window recommendations:
  `docs/RESEARCH_AUTOMATION_SCHEDULE_V0_1.md`.
- Current owner/timeline handoff:
  `docs/RESEARCH_AUTOMATION_HANDOFF_V0_1.md`.
- Data retention is partially active: Binance Spot `1d` remains `2020-01-01`
  through the latest complete UTC day. Detailed History V0.1.1 separately
  authorizes a fixed 2022-08 through 2026-07, 250-market `15m`/`1h`/`4h`
  Binance USD-M backfill after the V0.10 window. Rolling updates and the broader
  derivative-state materializations still require another authority. See
  `docs/DATA_RETENTION_POLICY_V0_1.md`.
- V0.6 Shadow Model ablation is prepared but not active after the first V0.5
  quality `REJECT`: it compares baseline, trend, price/volume and volatility
  groups locally with calibration and descriptive regime slices. It has no
  provider reads, R2 writes, holdout access, promotion or trading authority.
  See `docs/BINANCE_SPOT_SHADOW_V0_6.md`.
- Research Signal Layer V0.1 is now prepared as a separate, research-only
  contract for appending only closed latest candles and evaluating timestamped
  KOL forecasts without lookahead. It is idempotent, rejects historical
  revisions and provider mixing, and cannot write production R2, promote a
  model or trigger a trade. External KOL ingestion remains disabled until a
  separately versioned authority names sources, retention and rate limits.
  See `docs/RESEARCH_SIGNAL_LAYER_V0_1.md`.
- Research Signal Layer V0.2 is active on merge: a daily `02:17 UTC` GitHub
  Actions collector reads only the three configured public HTTPS sources,
  accepts structured JSON forecasts without prose inference, and publishes
  immutable source metadata/forecast evidence to the dedicated R2 namespace.
  It performs fresh 8 GB FREE-ONLY headroom gates before fetch and write. It
  cannot append historical candles, promote a model or trigger a trade. See
  `docs/RESEARCH_SIGNAL_LAYER_V0_2.md` and
  `.github/workflows/research-signal-layer-v0-2.yml`.
- Research Signal Quality V0.1 runs daily at `02:47 UTC`. It reads only the
  allowlisted latest, manifest and payload objects from the dedicated signal
  namespace, verifies both SHA-256 links and reports `FORECAST_READY`,
  `METADATA_ONLY` or `NO_DATA`. It cannot list/write R2 or access providers.
- Research Automation Health V0.1 runs every three hours at `:47`. It reads
  GitHub Actions run metadata only, filters formal schedule/manual events from
  pull-request checks, and alerts on stale, failed or missing expected jobs.
  Time-bounded and dependency-waiting states remain explicit rather than false
  failures. See `docs/RESEARCH_AUTOMATION_HEALTH_V0_1.md`.
- A post-window four-hour/weekly/monthly successor cadence is recorded as
  `PREPARED_NOT_ACTIVE`. It has no workflow and grants zero provider, R2,
  holdout, model-promotion or trading authority.
- Tokenized Equity Challenger V0.1 is prepared as a separate
  `PREPARED_LOCAL_REPLAY_ONLY` path that reuses the crypto technical scorer
  only after explicit tokenized-stock asset-class, session, corporate-action,
  interval and spread gates pass. It remains outside the formal crypto
  universe, has no schedule or R2 access, and cannot promote a model or create
  a trade plan. See `config/tokenized_equity_challenger_v0_1.json` and
  `docs/TOKENIZED_EQUITY_CHALLENGER_V0_1.md`.
- The research-only continuous-learning completion target is documented in
  `docs/CONTINUOUS_LEARNING_ROADMAP_V0_1.md`. Its `2026-09-30` engineering
  target is a roadmap, not execution authority or a profitability promise.

### Binance Spot R2 Weekly Training and Review V0.4 — HISTORICAL / EXECUTION RETIRED

- V0.4 config, receipt, namespaces and prior R2 objects remain immutable historical
  evidence. They were not rewritten into V0.5 semantics.
- V0.4 workflow files are manual validation-only retirement checks: no schedule,
  provider access, R2 secrets or R2 writes.
- V0.5 uses separate config, authority receipt, workflow names and R2 namespaces.

### Binance Spot R2 Automated Training V0.3 — HISTORICAL ONLINE PASS / DAILY RETIRED

- Cloudflare R2 is the only persistent generated-data store for immutable Binance
  Spot 1D internal-training snapshots. GitHub runner files are ephemeral and are
  explicitly removed after online evidence upload; local repository artifacts
  are forbidden.
- Its successful online runs remain immutable evidence. V0.5 is now the current
  weekly training and monthly catalog-governance execution path.
- R2 credentials remain in GitHub Actions secrets only. Raw history is not
  projected to GitHub Pages.
- The latest training pointer is written only after immutable dataset,
  catalog, receipt, model, metrics and manifest objects all pass round-trip
  verification, preserving the prior valid run if a publish is interrupted.
- The frozen replacement-holdout guard stops the workflow before provider or R2
  access at `2026-08-27T00:00:00Z`; automatic resume is not authorized.
- Model output remains research evidence. Source switching, Historical Universe
  membership, backtest admission, trade plans and trading remain unauthorized.
- GitHub Actions run
  [`32564110756`](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/32564110756)
  completed successfully on `main`: 748 markets, 701,275 rows through 2026-08-21,
  seven R2 objects uploaded and round-trip verified, with `latest.json` written
  last. The secret-free evidence is frozen in
  `research/receipts/2026-08-22-binance-spot-r2-automated-training-v0-3-pass.json`.

### Binance Internal Training Universe V0.2 — HISTORICAL BASELINE / LOCAL COPY RETIRED

- The V0.2 result remains historical evidence; its ignored local generated copy
  was removed after the R2 V0.3 snapshot passed exact SHA-256 round-trip checks.
- The 2026-08-22 local pass discovered 748 USDT/USDC markets and wrote 701,275
  daily rows through 2026-08-21 UTC; 723 markets pass continuity audit and 25
  are retained with `audit_ok=false` for explicit downstream filtering.
- Crypto, tokenized-stock candidates and other assets are classified explicitly;
  heuristic classifications never promote an asset into a trading universe.
- Historical records remain internal-only in R2 and are not projected to GitHub
  Pages. V0.3 forbids persistent local generated artifacts while preserving
  Pionex-native relabeling, source switching, W1, holdout-access and trading
  prohibitions.

### Pionex Public Paper Training V0.1

- Hourly GitHub Actions may read only Pionex public futures market endpoints.
- It computes causal multi-timeframe technical, volatility, volume,
  microstructure and derivatives market-state features.
- Fixed candidate gates feed only the deterministic Repository Paper Broker;
  metrics, trades, lineage and training rows are retained as run artifacts and
  projected to the read-only GitHub Pages dashboard.
- Pionex Demo is manual sampling only. Private API use, demo automation, formal
  trade plans, R2 access, replacement-holdout access, provider switching,
  real-money orders and live trading remain unauthorized.
- The job performs zero provider requests from `2026-08-27T00:00:00Z` onward;
  resumption requires a new versioned authority after the frozen window.

No live-money authorization exists. `trade_plan_authorized=false`, `real_money_order_authorized=false`, and `live_trading_authorized=false` remain mandatory.

## Current execution / transport authority

V0.10 activation merge commit from PR #127: `8fce944da479dbda0e2899f9b30b9de62351fa27`.

Current metadata-capture path:

- workflow: `.github/workflows/provider-equivalence-v0-10-render-metadata-capture.yml`;
- runner: `ubuntu-latest`;
- Pionex metadata leg: GitHub-hosted direct public HTTPS;
- Binance USD-M metadata leg: authenticated Render Free / Frankfurt path `/metadata/v0-10/binance-exchange-info`;
- old V0.2 `[self-hosted, macOS, ARM64]` scheduled path: **RETIRED**;
- concurrent old/new metadata paths: forbidden;
- automatic fallback to V0.2: forbidden;
- Render receives R2 credentials: false.

Render remains FREE / Frankfurt. Current runtime budget is `0 USD/month`.

Final read-only pre-window Render recheck on 2026-08-21 confirms:

- service Auto-Deploy: **OFF** (`autoDeploy=no`, trigger `off`);
- service plan: **free**;
- service region: **frankfurt**;
- service maintenance mode: disabled;
- service suspension: none;
- current/latest live deploy: `dep-da35gfoae00c73fpff8g`;
- current/latest live deploy commit: `8fce944da479dbda0e2899f9b30b9de62351fa27` (the V0.10 activation merge);
- no unexpected redeploy occurred after V0.10 activation despite later maintenance/docs merges.

Authority receipt: `research/receipts/2026-08-21-v0-10-render-final-pre-window-readonly-recheck.json`.

This recheck was observation-only: it did not trigger a Render deploy, read/change Render environment values, hit providers, construct/read/write production R2, read capture artifacts, open holdout data, or run V0.11 production evaluation.

## Frozen metadata scope

Inherited scientific scope is unchanged:

- metadata capture: `2026-08-27T00:00:00Z` through `2026-09-04T01:59:59.999Z`;
- 194 UTC hourly slots;
- attempts at UTC `:17` and `:47`;
- 388 scheduled attempts total;
- first scheduled attempt: `2026-08-27T00:17:00Z`;
- last scheduled attempt: `2026-09-04T01:47:00Z`;
- current date-scoped schedules:
  - `17,47 * 27-31 8 *`
  - `17,47 * 1-3 9 *`
  - `17,47 0-1 4 9 *`
- required coverage: at least one complete valid capture per UTC hourly slot;
- 15 candidate symbols / 45 mapped pairs;
- replacement holdout: `2026-08-28T00:00:00Z` through `2026-09-03T23:59:59.999Z`;
- replacement holdout state: **FROZEN_UNOPENED**.

Each complete V0.10 capture uses 3 immutable run-scoped R2 objects. Receipt is written last, post-write SHA-256 readback is required, and every authorized write must pass a fresh whole-bucket 8,000,000,000-byte FREE-ONLY headroom gate.

No provider/R2 metadata capture is authorized outside the exact frozen window.

## Pre-window readiness and capture-window operations — PREPARED PASS

PRs #153–#161 completed the remaining pre-window testing, failure rehearsal, post-window preparation, read-only operational dashboard projection, capture-window incident policy, mid-window emergency template, and future V0.11 production-evaluation authority template without consuming production metadata evidence.

Key authorities and evidence:

- `research/receipts/2026-08-20-pre-window-readiness-v0-1.json`
- `research/receipts/2026-08-20-v0-10-scheduled-capture-observer-prepared.json`
- `config/v0_10_critical_path_freeze_v0_1.json`
- `config/v0_10_capture_window_operations_v0_1.json`
- `docs/V0_10_CAPTURE_WINDOW_OPERATIONS_RUNBOOK.md`
- `research/receipts/2026-08-21-v0-10-capture-window-operations-prepared.json`
- `config/v0_10_mid_window_emergency_change_template_v0_1.json`
- `docs/V0_10_MID_WINDOW_EMERGENCY_CHANGE_TEMPLATE.md`
- `research/receipts/2026-08-21-v0-10-mid-window-emergency-template-prepared.json`
- `research/receipts/2026-08-21-v0-10-render-final-pre-window-readonly-recheck.json`
- `config/provider_equivalence_v0_11_synthetic_failure_rehearsal_v0_1.json`
- `research/receipts/2026-08-21-provider-equivalence-v0-11-synthetic-failure-rehearsal-pass.json`
- `config/provider_equivalence_v0_11_post_window_execution_package_v0_1.json`
- `config/provider_equivalence_v0_11_production_evaluation_authority_template_v0_1.json`
- `docs/V0_11_PRODUCTION_EVALUATION_AUTHORITY_TEMPLATE.md`
- `research/receipts/2026-08-21-provider-equivalence-v0-11-production-evaluation-authority-template-prepared.json`
- `web/data/operational-status.json`

Frozen operational rules:

- the existing V0.10 scheduled workflow remains the only normal production metadata-capture execution path;
- manual metadata-capture backfill is **NOT_AUTHORIZED**;
- retroactive hourly-slot backfill is **NOT_AUTHORIZED**;
- if the `:17` attempt fails, preserve the failure and allow the frozen `:47` scheduled attempt to run normally;
- if both attempts in one UTC hour fail, preserve both failures and keep that hour as a potential missing slot for post-window V0.11 evaluation; do not manufacture replacement evidence;
- an R2 FREE-ONLY headroom `BLOCKED` result must stop before write and may not be bypassed by raising the 8 GB gate, deleting evidence, or performing partial writes;
- a stale scheduled run over the frozen freshness limit remains a skip and may not bypass the freshness guard;
- observer scope remains GitHub Actions run/job/step metadata only; it does not read capture artifacts, production R2, provider payloads, Render payloads, or holdout data;
- automatic repair, automatic redeploy, automatic secret rotation, and automatic budget override remain unauthorized;
- default mid-window state is **NO PRODUCTION-CRITICAL MUTATION**;
- any unavoidable production-critical mid-window intervention requires a separate versioned emergency authority plus protected-main PR, must record pre/post-change lineage, and may not change frozen thresholds/scope, open holdout, or retroactively validate prior missing slots;
- the prepared emergency-change template is `TEMPLATE_PREPARED_NOT_AUTHORITY`; it does not itself authorize any intervention or Render redeploy.

The PR #153 synthetic rehearsal covered 12/12 scenarios and passed in CI. That PASS proves fail-closed behavior only; it is not production metadata-stability evidence and grants no downstream authority.

## V0.11 metadata stability evaluator — PREPARED ONLY

PR #131 froze the evaluator rules and implementation before production stability evidence is read. PR #154 prepared the exact post-window execution sequence without granting execution authority. PR #161 additionally prepared and validated the exact future production-evaluation authority template while leaving the runtime hard-disabled.

Authorities:

- `config/provider_equivalence_v0_11_metadata_stability_evaluation_v0_1.json`
- `research/receipts/2026-08-20-provider-equivalence-v0-11-metadata-stability-evaluator-prepared.json`
- `config/provider_equivalence_v0_11_post_window_execution_package_v0_1.json`
- `config/provider_equivalence_v0_11_production_evaluation_authority_template_v0_1.json`
- `docs/V0_11_PRODUCTION_EVALUATION_AUTHORITY_TEMPLATE.md`
- `research/receipts/2026-08-21-provider-equivalence-v0-11-production-evaluation-authority-template-prepared.json`
- `src/crypto_autopilot/provider_metadata_stability_v0_11.py`
- `.github/workflows/validate-v0-11-metadata-stability-evaluator.yml`

Frozen evaluator semantics:

- require at least one complete valid V0.10 receipt for each of all 194 hourly slots;
- duplicate captures inside a slot are valid only if each provider's normalized 15-symbol vector matches exactly;
- Pionex and Binance USD-M vectors must each remain exactly stable across the entire capture window;
- missing slot, invalid receipt, normalized-vector SHA mismatch, same-slot disagreement, or cross-window drift => FAIL CLOSED;
- no post-hoc deadband, provider splicing, symbol-scope shrink, or retroactive slot backfill.

Current execution boundary:

- `V0_11_R2_EVALUATION_EXECUTION_AUTHORIZED=false`;
- production R2 client construction/read is not authorized;
- production receipt listing/reading has not run under V0.11;
- provider and Render requests are not authorized by the prepared evaluator;
- raw provider objects and holdout objects may not be listed/read;
- the prepared post-window package is not execution authority;
- the prepared production-evaluation authority template is not execution authority;
- no actual V0.11 production evaluation authority may be created or merged before the full metadata capture window ends at `2026-09-04T01:59:59.999Z`;
- metadata stability remains **NOT_YET_RUN**.

The future authority template locks the only eligible execution delta after a separate post-window protected-main authority merge to a one-shot reviewed path: construct the R2 client, list/read allowlisted V0.10 `receipt.json` objects, and run the already-frozen evaluator. It must remain receipt-only/read-only: no R2 writes/deletes, no raw provider-object reads, no provider/Render requests, no `METADATA_RELAY_TOKEN`, no holdout listing/access, no scheduled/automatic evaluation, and no source-switch/W1/backtest/strategy/trading authority.

After the full window ends, the frozen sequence is: verify window completion and critical-path lineage without reading production R2; create a separate versioned V0.11 production-evaluation execution authority from the prepared template; merge it through protected `main` after required CI; only then list/read allowlisted V0.10 `receipt.json` objects and run the exact evaluator.

Even a future metadata-stability PASS will not itself authorize holdout access. A separate versioned holdout-access authority is required.

## Frozen historical results

### Pionex M1 / M1A — PASS

Authority: `research/receipts/2026-08-17-m1a-pionex.json`

- 15 frozen candidates;
- intervals `15M` / `60M` / `4H`;
- 13,230 candles;
- no gaps, duplicate timestamps, or invalid candles.

### M1B R2 — PASS

Authority: `research/receipts/2026-08-18-m1b-r2.json`

- 45 objects;
- 13,230 rows;
- 425,161 Parquet bytes;
- SHA-256 verified upload/download and exact candle round trip.

### Binance 2025 R2 pilot — PASS

Authority: `research/receipts/2026-08-18-binance-2025-r2-pilot.json`

- 528 source archives;
- 206 canonical R2 objects;
- 671,022 candles;
- provider remains `binance_usdm`;
- no Pionex-native relabeling authority.

### Funding V0.2 — PASS

Authorities:

- `research/receipts/2026-08-19-binance-funding-materialization-authority-v0-2.json`
- `research/receipts/2026-08-19-binance-funding-r2-v0-2-full-preflight.json`
- `research/receipts/2026-08-19-binance-funding-r2-v0-2-materialization.json`

Result: 1,003 official source archives, 94 annual canonical objects, 192/192 authorized R2 identities verified, 91,747 Funding observations. HYPEUSDT 2026 remains deferred; no interpolation/provider splice is authorized.

### Equivalence V0.1 — DEFINITIVE FAIL

Authorities:

- `config/provider_equivalence_v0_1.json`
- `research/receipts/2026-08-19-pionex-binance-equivalence-v0-1.json`
- `research/receipts/2026-08-19-pionex-binance-equivalence-v0-1-direction-forensics.json`

Frozen result: 45 pairs = 18 PASS / 18 REVIEW / 9 FAIL. Direction forensics is descriptive only. `source_switch_authorized=false`. Thresholds/scope must not be changed after evidence to manufacture PASS.

### Render successor line — V0.5 through V0.10

Key authorities:

- `research/receipts/2026-08-19-provider-equivalence-v0-5-render-free-transport-pass.json`
- `research/receipts/2026-08-19-provider-equivalence-v0-6-render-transport-authority-transition.json`
- `config/provider_equivalence_v0_7_render_metadata_capture_protocol_v0_1.json`
- `research/receipts/2026-08-19-provider-equivalence-v0-8-shared-relay-secret-handshake-pass.json`
- `research/receipts/2026-08-20-provider-equivalence-v0-9-render-relay-smoke-pass.json`
- `config/provider_equivalence_v0_10_final_atomic_cutover_v0_1.json`
- `research/receipts/2026-08-20-provider-equivalence-v0-10-final-atomic-cutover-authority.json`
- `research/receipts/2026-08-21-v0-10-render-final-pre-window-readonly-recheck.json`

V0.8 remains **HISTORICAL** preparation evidence; it must not be rewritten to look like current V0.10 execution authority.

## Historical workflow retirement hygiene

Frozen proof/materialization evidence must not be routinely re-executed just because its historical workflow file still exists.

The following **17 historical workflows** are validation-only / `RETIRED_NO_EXECUTION`:

- `historical-backfill-pilot.yml`;
- `diagnose-v0-2-self-hosted-mac-binance-transport.yml`;
- `binance-2025-r2-pilot.yml`;
- `binance-vision-live-proof.yml`;
- `binance-vision-r2-proof.yml`;
- `binance-funding-r2-v0-2-preflight.yml`;
- `binance-funding-r2-v0-2-materialize.yml`;
- `m1b-m1a-dataset-upload.yml`;
- `m1b-r2-roundtrip.yml`;
- `binance-2025-coverage-scan.yml`;
- `binance-funding-source-proof.yml`;
- `binance-funding-coverage.yml`;
- `binance-max-coverage-discovery.yml`;
- `m1a-acquisition.yml`;
- `pionex-binance-equivalence-proof.yml`;
- `pionex-binance-equivalence-v0-1-forensics.yml`;
- `historical-universe-long-horizon-review.yml`.

They must have no schedule, no push-triggered production execution, no manual production rerun, no R2 secret binding, no self-hosted runner, and no real provider/materializer command. Reactivation requires a new versioned authority.

This retirement does not delete or invalidate their historical scripts/configs/receipts.

## Workflow reproducibility and supply-chain hardening

PRs #136–#161 include maintenance authorities for execution-environment reproducibility, repository hygiene, CI/supply-chain hardening, repository ruleset validation, pre-window rehearsal, post-window preparation, Dashboard operational projection, capture-window incident-response preparation, mid-window emergency-template preparation, and future V0.11 authority-template preparation. They do not change scientific thresholds, metadata scope, provider authority, holdout authority or trading authority.

Current hardening:

- PR #136 added `requirements/ci-constraints.txt`, freezing the reviewed CI/test dependency snapshot while leaving public `pyproject.toml` compatibility ranges unchanged;
- V0.10 scheduled capture explicitly selects **Python 3.13** before freshness checks, constrained dependency installation, provider access, or R2 access;
- PR #137 pins production-critical GitHub Actions to reviewed **immutable 40-character commit SHAs** rather than mutable major tags;
- critical checkout steps keep `persist-credentials: false`;
- the critical artifact / GitHub Pages stack uses the reviewed Node 24 generation;
- PR #140 removed the unused stale `D1_DATABASE_ID` placeholder from `.env.example`; regression prevents that retired D1 placeholder from reappearing as current configuration;
- PR #141 made Ruff a real read-only CI gate with `ruff==0.16.0` and explicit core correctness rules `E4` / `E7` / `E9` / `F`; its first run exposed four pre-existing lint findings, each manually reviewed and fixed without changing frozen scientific semantics;
- PR #142 limited the main CI `push` trigger to `main` while preserving all `pull_request` validation, preventing an extra broad-push CI run on ordinary feature-branch updates;
- PR #143 expanded full main CI to **Python 3.12 and Python 3.13** with `fail-fast: false`; both `test (3.12)` and `test (3.13)` were observed PASS with constrained install, Ruff, full unit tests and R2 budget gates;
- the active `Protect main` ruleset targets the default branch, requires pull requests, requires the always-running `test (3.12)` and `test (3.13)` checks, restricts deletion, blocks force pushes, and has no configured bypass list;
- ruleset validation on 2026-08-20 confirmed a direct `main` contents write is rejected with a rule violation requiring a pull request and 2/2 required checks; PR #145 then exercised the docs-only PR path with both required CI matrix jobs;
- PR #153 froze and executed a 12-scenario synthetic V0.11 failure rehearsal; 12/12 passed without production metadata evidence;
- PR #154 prepared the exact post-window V0.11 execution sequence while keeping production R2 evaluation hard-disabled;
- PR #155 added a read-only `authority=false` operational Dashboard projection;
- PR #156 froze capture-window incident-response rules, including no manual/retroactive backfill and separate emergency authority for any production-critical mid-window mutation;
- PR #157 froze the exact #156 PASS evidence as a Repository receipt and validated that receipt in CI;
- PR #158 synchronized the pre-window operational authority index;
- PR #159 prepared a machine-readable/human-readable mid-window emergency-change template while keeping it `NOT_AUTHORITY`;
- PR #160 froze the exact #159 template-preparation PASS as Repository evidence;
- PR #161 prepared and validated the exact future V0.11 production-evaluation authority template while keeping current V0.11 production R2 evaluation hard-disabled;
- path-scoped V0.10/V0.11/Dashboard checks remain intentionally excluded from global required checks;
- regression tests protect these boundaries from silent downgrade.

Repository branch protection/ruleset configuration is external GitHub state, not a file-based scientific authority. Direct GitHub verification continues to report `main` as `protected=true`; the active ruleset and PR #145 provide the repository-level security validation tracked by Issue #139.

## Non-negotiable provider and safety boundaries

- Pionex remains execution target/provenance authority for Pionex-native evidence.
- Binance USD-M/Binance Vision remains provider-separated research evidence.
- Provider mapping never converts provenance.
- No provider splicing, silent interpolation, Pionex-native relabeling, or post-hoc provenance rewrite.
- V0.10 metadata authority is not strategy/backtest/trade/live authority.
- V0.10 capture-window operations preparation is not new capture authority and does not authorize manual/retroactive backfill.
- V0.10 emergency-change template is not authority and does not authorize a mid-window mutation or Render redeploy.
- V0.11 prepared evaluator, post-window package, and production-evaluation authority template are not production stability authority.
- No staged Trade-Kline W1 materialization yet.
- Historical Universe membership remains NOT_READY.
- SState frozen core must not be modified by this phase.
- No martingale, loss doubling, unlimited averaging, or liquidation-as-stop.
- Public Binance `exchangeInfo` on this path uses no Binance API key; this is not a project-wide API-key ban. A future authenticated Binance scope needs separate authority and may not be used as a transport-blocker bypass.

## Current blockers

1. Metadata stability: production 194-slot evidence has not run yet.
2. Holdout access: replacement holdout is `FROZEN_UNOPENED` and requires separate authority after stability PASS.
3. Provider substitution: Equivalence V0.1 remains definitive FAIL.
4. Trade-Kline W1 materialization: NOT_AUTHORIZED.
5. Historical Universe membership: NOT_READY.
6. Strategy replay/backtest admission: still blocked by authority.
7. HYPE Funding 2026: deferred; no interpolation/provider splice.
8. Live execution: forbidden; project remains PAPER-ONLY.

## Next formal milestone

Before `2026-08-27T00:00:00Z`: readiness/maintenance validation only. Do not manually consume production metadata evidence.

During the frozen window:

1. Let the existing V0.10 schedule run at `:17/:47`; do not create a second execution path.
2. Preserve the exact 194-slot / 388-attempt / 15-symbol / 45-pair scope.
3. Preserve every failed, blocked, skipped, stale, or missing attempt as evidence; do not manually or retroactively backfill it.
4. If `:17` fails, let the existing frozen `:47` attempt run normally rather than manually retrying.
5. Keep the replacement holdout unopened.
6. Require the exact window/freshness gate and authenticated Render transport.
7. Require fresh R2 headroom before each write; never overwrite, delete, or bypass evidence to force a capture through.
8. Keep production-critical code/runtime/secrets frozen by default; any unavoidable intervention requires a separate versioned emergency authority and protected-main PR.
9. After the full window has ended at `2026-09-04T01:59:59.999Z`, verify critical-path lineage without production R2 reads, then create a separate versioned V0.11 production evaluation authority from the prepared template **before any R2 receipt read for stability evaluation**.

## Explicitly forbidden next actions

- Do not manually run V0.10 production metadata capture before the frozen window.
- Do not manually or retroactively backfill failed/missing V0.10 attempts or hourly slots during or after the frozen window.
- Do not bypass the 30-minute freshness guard or 8 GB FREE-ONLY R2 headroom gate.
- Do not make an unreviewed production-critical mid-window code, runtime, secret, transport, or provider change.
- Do not treat the prepared emergency-change template as an intervention authority.
- Do not create or merge the actual V0.11 production-evaluation authority before `2026-09-04T01:59:59.999Z`.
- Do not manually run V0.11 production R2 stability evaluation under the prepared protocol/template.
- Do not list/read production V0.10 R2 receipts for stability evaluation before a separate post-window authority is merged.
- Do not reactivate retired historical proof/materialization workflows without new authority.
- Do not re-enable the V0.2 self-hosted schedule or create a second concurrent metadata path.
- Do not access/evaluate replacement holdout candles.
- Do not alter Equivalence V0.1 thresholds/scope or add a post-hoc deadband.
- Do not source-switch, provider-splice, interpolate missing provider values, or relabel Binance evidence as Pionex-native.
- Do not expose relay/R2/exchange secrets in Repository, issues, logs, artifacts, tests, or chat.
- Do not give Render R2 credentials.
- Do not use third-party proxies, alternate endpoints, API keys, or a paid tier as a transport-blocker bypass.
- Do not authorize W1, strategy changes, automatic trade plans, real-money orders, or live trading.
