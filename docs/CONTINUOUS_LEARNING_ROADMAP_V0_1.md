# Continuous Learning Roadmap V0.1

Updated: 2026-09-01

Status: **PREPARED ROADMAP / NOT EXECUTION AUTHORITY**

## Outcome

The research-only continuous-learning loop is targeted for operational
completion by **2026-09-30**, provided every existing data, R2, scientific and
authority gate passes. This target does not authorize a workflow, provider
request, R2 read/write, holdout access, model promotion, trade plan or order.

The intended loop is:

```text
latest closed candles + append-only history + timestamped KOL evidence
  -> causal feature build
  -> bounded Shadow challengers and immutable candidate registry
  -> walk-forward / calibration / cost / drawdown / exposure / drift checks
  -> Strategy Edge Validation + cost-complete paper-performance audit
  -> immutable PASS, REJECT or REVIEW evidence
  -> Repository Paper Broker only
```

Automatic promotion and real-money execution are deliberately outside the
loop. A `REJECT` result is retained as evidence and cannot replace a model.

## Time-ordered stages

### 1. Current bounded research — through 2026-08-27 08:00 Asia/Taipei

- Pionex public paper training produces candidate and simulated-trade evidence.
- Binance Spot V0.5 was the bounded weekly historical research trainer; its
  cron is retired after the 2026-08-27 cutoff and it does not auto-resume.
- Research Signal Layer V0.2 collects only allowlisted structured public-source
  evidence; signal quality and automation health checks remain read-only.
- These paths are separate. They do not yet share an automatic rolling dataset,
  experiment registry and recurrent Challenger decision loop.

### 2. Metadata evidence transition — V0.10 retired; V0.12 successor window prepared

- V0.10 is incomplete historical evidence and no longer has a schedule.
- V0.12 is the only current production metadata-capture schedule after its exact protected-main merge, bounded to `2026-09-04T02:00:00Z` through `2026-09-12T03:59:59.999Z`.
- V0.10 failures are not replayed, backfilled or regraded into V0.12.
- No new learning or holdout-candle authority is implied.
- Replacement holdout candles remain `FROZEN_UNOPENED`.
- Production V0.12 receipt evaluation still requires a separate post-window authority.
- GitHub Automatic Research Operations V0.1 makes all seven currently
  authorized online workflows schedule-driven. Research Automation Health
  V0.2 checks the exact cron inventory every two hours; manual and PR runs do
  not count as automatic-health evidence.

### 3. Detailed-history start — first eligible run 2026-09-04 14:23 Asia/Taipei

- Binance USD-M Crypto Core 100 V0.1.2 starts only after its
  `2026-09-04T02:00:00Z` not-before gate.
- The `00:23 UTC` scheduled occurrence fails closed before provider/R2 access;
  the first eligible scheduled occurrence is `06:23 UTC` / `14:23 Asia/Taipei`.
- Twenty-five serialized resumable shards run at most once every six hours.
- A complete 100-Crypto-market, 48-month, native `15m` / `1h` / `4h` dataset is a
  prerequisite for its weekly research trainer.

### 4. Post-window successor authority — earliest after 2026-09-04 10:00 Asia/Taipei

A separate versioned authority must activate the already prepared cadence:

- every four hours: append only latest complete candles, with provider/time
  lineage and no historical revision;
- weekly: bounded V0.6 Shadow feature-group ablation, probability calibration,
  chronological walk-forward, fee/slippage/drawdown/exposure checks and the
  prepared Strategy Edge Validation V0.1 anti-overfitting battery;
- monthly: feature/label drift, market-universe review, catalog absence,
  survivorship limitations and tokenized-stock classification review;
- ongoing: immutable experiment registry and dataset/config/feature/environment
  fingerprints so failed experiments are not silently repeated.

## Completion definition

The research loop is considered operational only when all of the following are
true:

1. detailed-history dataset is complete and SHA-256 / lineage checks pass;
2. rolling closed-candle append authority is effective and idempotent;
3. Shadow training produces deterministic PASS or REJECT evidence on schedule;
4. calibration, cost, drawdown, exposure and drift outputs are persisted online;
5. the complete trial family and disjoint-validation evidence produce a
   deterministic Strategy Edge `PASS` or `REJECT` without automatic promotion;
6. selected-candidate, provider and SHA-256 lineage match a complete paper
   ledger whose fees, funding, slippage, expectancy, drawdown, concentration
   and Monte Carlo fragility remain visible;
7. automation health distinguishes expected waiting from stale or failed runs;
8. the dashboard projects the latest safe status without becoming authority;
9. model promotion, holdout access and trading remain separately gated.

Routine execution is automatic, but authority transitions are intentionally
not self-service. A workflow cannot merge its own new provider, R2, holdout,
model or trading scope; those remain protected-main review decisions.

The synthetic-only research-loop contract that prepares items 5 and 6 is
documented in `docs/STRATEGY_RESEARCH_LOOP_V0_1.md`. It does not activate the
post-window workflow or grant production-data execution.

The date `2026-09-30` is an engineering target, not a profitability promise.
No system can credibly target 100% predictive accuracy; the objective is better
calibrated, reproducible decisions with bounded risk and explicit rejection.

## Binding boundaries

- Repository `main` and versioned configs/receipts remain authority.
- This roadmap never changes frozen V0.10 or V0.11 evidence.
- `source_switch_authorized=false` remains binding.
- Binance evidence remains provider-separated from Pionex-native evidence.
- `trade_plan_authorized=false`, `real_money_order_authorized=false` and
  `live_trading_authorized=false` remain binding.
