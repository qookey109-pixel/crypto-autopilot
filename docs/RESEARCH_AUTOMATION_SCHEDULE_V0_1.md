# Research Automation Schedule V0.1

This document is an operations index, not execution authority. Repository
configs, receipts and workflows remain authoritative. It does not change the
frozen V0.10 production-critical path, open the replacement holdout, promote a
model or authorize trading.

## Current active schedule

| Cadence | Current job | Evidence boundary |
| --- | --- | --- |
| Pull request / push | Repository CI and synthetic fault tests | No provider, production R2, holdout or trading access |
| Sunday 02:37 UTC | Binance Spot R2 training governance V0.5 | First run completed; pipeline `PASS`, model quality `REJECT`; no push trigger |
| Day 1 03:37 UTC | Binance Spot monthly governance V0.5 | One-time manual baseline completed; repeat manual activation is forbidden |
| Hourly at `:07` | Pionex public paper training V0.1 | Repository Paper Broker only; Pionex Demo stays manual |
| Every 6 hours at `:23`, 2026-09-04 through 2026-09-30 | Binance USD-M Detailed History V0.1.1 | One serialized incomplete 10-market shard; 250-market / 48-month target; R2-only |
| Sunday 04:37 UTC | Binance USD-M Detailed Training V0.1.1 | Skips until all detailed-history shards are complete; research evidence only |

The Binance weekly and monthly jobs stop before provider or R2 access at
`2026-08-27T00:00:00Z`; the Pionex paper job also stops provider requests at
that boundary. A green post-stop skip is intentional. No automatic resume is
authorized.

The Detailed History cron syntax recurs annually because GitHub cron has no
year field. A frozen `2026-10-01T00:00:00Z` backfill stop makes every later
occurrence exit before provider or R2 access. The separate completed-dataset
weekly trainer is not subject to that backfill-only expiration.

The initial V0.5 monthly baseline was created successfully by run `32589005957`
at `2026-08-23 01:51 Asia/Taipei`. The first weekly run `32615608243` completed
at `2026-08-23 11:32 Asia/Taipei`; the evidence pipeline passed while the model
quality gate rejected the candidate. Do not repeat the monthly manual activation
or reinterpret the model rejection as an execution failure. Repository push is
not a production workflow trigger. The current execution handoff is recorded in
`docs/RESEARCH_AUTOMATION_HANDOFF_V0_1.md`.

## Data retention split (partially active)

The requested retention policy is recorded in
`config/data_retention_policy_v0_1.json` and
`docs/DATA_RETENTION_POLICY_V0_1.md`:

- Binance Spot `1d` training history remains `2020-01-01` through the latest
  complete UTC day under the existing V0.5 authority.
- Detailed History V0.1.1 authorizes a fixed 2022-08 through 2026-07 Binance USD-M
  `15m` / `1h` / `4h` dataset for 250 markets after the V0.10 window.
- Future rolling updates and the broader derivative-state series still need a
  separately authorized materialization path.
- Derived indicators are recomputed from canonical inputs rather than stored as
  another full duplicate dataset.

The detailed backfill is versioned separately in
`config/binance_usdm_detailed_history_v0_1_1.json`. It does not authorize
deletion/compaction of frozen evidence, holdout access, source switching or
trading.

The prepared V0.6 Shadow Model is likewise local-only. Its bounded ablation
runner may consume an already available Parquet fixture, compare four feature
groups, and emit calibration/regime evidence. It must not be added to the
production schedule until a separate post-window authority names its exact
config and namespace.

## Evidence-correctness hardening

The current implementation applies the following fail-closed checks:

- exact ordered daily-direction feature contract; label/order drift is rejected;
- exact-byte V0.5 config / authority-receipt pairing and a SHA-256-bound V0.3
  748 / 723 / 701,275-row first-run comparison baseline;
- catalog and Parquet SHA/size binding, plus Parquet provider, schema, OHLCV,
  row/symbol/audit, historical-depth and tail-evidence checks before R2 writes;
- complete-tail validation for each Binance Spot series, while allowing markets
  that listed after 2020;
- train/validation record fingerprints, strict chronological separation and an
  explicit `FROZEN_UNOPENED_NOT_ACCESSED` holdout state;
- a train-prevalence naive baseline for every ready walk-forward fold;
- a research-only model-quality gate using log loss, Brier score, configured
  costs, net growth, maximum drawdown and symbol concentration;
- separate pipeline and model semantics: `status=PASS` means the evidence job
  completed, while `model_quality_gate.status=REJECT` is preserved and published;
- allowlisted monthly R2 pointer schema/provider/namespace/run-id/SHA checks;
- exact current-review governance binding and contract validation before monthly
  R2 writes;
- truthful `fetched` versus `cached` operational logging.

Even a model-quality `PASS` has zero promotion, backtest-admission or trading
authority.

## Recommended post-window successor schedule (not activated)

1. Every training run: authority, R2 headroom, catalog/audited/row-depth collapse,
   tail completeness, OHLCV bounds, feature contract and partition-integrity gates.
2. Weekly, inside the existing job: calibration (ECE/MCE), fixed volatility /
   trend / volume / liquidity regime diagnostics, immutable experiment lineage,
   bounded retry/stop reasons and resource-duration evidence.
3. Monthly, alongside universe review: compare the latest 4-8 weekly runs for
   feature/distribution drift, duplicate experiments, model staleness, R2
   manifest/pointer consistency and a retention dry-run.
4. Quarterly or after enough new chronological data: human-reviewed shadow
   challenger and R2 rehydration drill. Never automatic promotion.

Any post-window online version must be separately authorized after the frozen window.
It should compare catalog size and audited coverage against the preceding valid
R2 snapshot rather than rely only on fixed thresholds.

## Reference architecture use

GameAI and OODA were treated as untrusted reference material. Only general
patterns were reimplemented: bounded/fail-closed evaluation, immutable evidence,
exact feature contracts, lineage, baseline comparison and fault containment.
No GameAI reinforcement-learning runtime, OODA Frozen Core, local artifact
store, pre-trained model or provider dataset was copied into this public
repository.
