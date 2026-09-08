# Continuous Learning Roadmap V0.1

Updated: 2026-08-24

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
  -> bounded Shadow challengers
  -> walk-forward / calibration / cost / drawdown / exposure / drift checks
  -> immutable PASS or REJECT evidence
  -> Repository Paper Broker only
```

Automatic promotion and real-money execution are deliberately outside the
loop. A `REJECT` result is retained as evidence and cannot replace a model.

## Time-ordered stages

### 1. Current bounded research — through 2026-08-27 08:00 Asia/Taipei

- Pionex public paper training produces candidate and simulated-trade evidence.
- Binance Spot V0.5 remains the current weekly historical research trainer.
- Research Signal Layer V0.2 collects only allowlisted structured public-source
  evidence; signal quality and automation health checks remain read-only.
- These paths are separate. They do not yet share an automatic rolling dataset,
  experiment registry and recurrent Challenger decision loop.

### 2. Frozen metadata window — 2026-08-27 08:00 through 2026-09-04 09:59:59.999 Asia/Taipei

- V0.10 metadata capture is the only current production metadata-capture path.
- No new learning or holdout-candle authority is implied.
- Replacement holdout candles remain `FROZEN_UNOPENED`.
- V0.11 production evaluation still requires a separate post-window authority.

### 3. Detailed-history start — first eligible run 2026-09-04 14:23 Asia/Taipei

- Binance USD-M Detailed History V0.1.1 starts only after its
  `2026-09-04T02:00:00Z` not-before gate.
- The `00:23 UTC` scheduled occurrence fails closed before provider/R2 access;
  the first eligible scheduled occurrence is `06:23 UTC` / `14:23 Asia/Taipei`.
- Twenty-five serialized resumable shards run at most once every six hours.
- A complete 250-market, 48-month, native `15m` / `1h` / `4h` dataset is a
  prerequisite for its weekly research trainer.

### 4. Post-window successor authority — earliest after 2026-09-04 10:00 Asia/Taipei

A separate versioned authority must activate the already prepared cadence:

- every four hours: append only latest complete candles, with provider/time
  lineage and no historical revision;
- weekly: bounded V0.6 Shadow feature-group ablation, probability calibration,
  chronological walk-forward and fee/slippage/drawdown/exposure checks;
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
5. automation health distinguishes expected waiting from stale or failed runs;
6. the dashboard projects the latest safe status without becoming authority;
7. model promotion, holdout access and trading remain separately gated.

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
