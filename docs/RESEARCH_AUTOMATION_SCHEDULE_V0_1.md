# Research Automation Schedule V0.1

This document is an operations index, not execution authority. Repository
configs, receipts and workflows remain authoritative. It does not change the
frozen V0.10 production-critical path, open the replacement holdout, promote a
model or authorize trading.

## Current scheduled execution after 2026-08-29 convergence

| Cadence | Current job | Evidence boundary |
| --- | --- | --- |
| Pull request / push | Repository CI and dashboard validation | No provider, production R2, holdout or trading access |
| `:17` / `:47` inside 2026-09-04 02:00 through 2026-09-12 03:59:59.999 UTC | Provider Equivalence V0.12 successor metadata capture | Only current metadata schedule; V0.10 is retired, no replay/backfill or holdout candle access |
| Daily 02:17 UTC | Research Signal Layer V0.2 | Public HTTPS source metadata and structured KOL challenger evidence to dedicated R2 namespace; no trading |
| Daily 02:47 UTC | Research Signal Quality V0.1 | Exact latest/manifest/payload R2 reads with SHA/time/authority checks; no list or write |
| Every three hours at `:47` | Research Automation Health V0.1 | GitHub Actions metadata-only stale/failure/missing-run monitor; no provider or R2 access |
| Every 6 hours at `:23`, 2026-09-04 through 2026-09-30 | Binance USD-M Crypto Core 100 V0.1.2 | One serialized incomplete 10-market shard; 100-market / 48-month target; R2-only |
| Sunday 04:37 UTC | Binance USD-M Crypto Core 100 Training V0.1.2 | Skips until all 10 detailed-history shards are complete; research evidence only |
| 2026-09-04 02:53 UTC, then Sep 6/13/20/27 at 03:53 UTC | Pionex Alternative Assets Observability V0.2 | Validates the 125-candidate equity/ETF/metal catalog, compares prior SHA-bound evidence and estimates capacity; metadata-only R2 evidence |

The expired Binance V0.5 weekly/monthly and Pionex Paper cron triggers are no
longer active. Their binding provider cutoff was
`2026-08-27T00:00:00Z`; `config/post_cutoff_schedule_retirement_v0_1.json`
removes only the cron triggers and leaves manual fail-closed regression
entrypoints. No automatic resume is authorized, and the historical config and
receipt schedule strings are not rewritten.

Research Signal Layer V0.2 is independent of the frozen Binance/Pionex stop
window. Its collector performs a fresh FREE-ONLY R2 headroom gate before any
source fetch and before every write. A source that exposes only HTML prose is
recorded as metadata evidence; it is never converted into a guessed direction.
The daily quality job starts 30 minutes after collection and reports metadata-
only evidence truthfully instead of treating prose as a forecast. The health
job filters allowed workflow events so pull-request checks cannot satisfy a
formal scheduled-run expectation.

The Detailed History cron syntax recurs annually because GitHub cron has no
year field. A frozen `2026-10-01T00:00:00Z` backfill stop makes every later
occurrence exit before provider or R2 access. The separate completed-dataset
weekly trainer is not subject to that backfill-only expiration.

The historical V0.5 monthly baseline was created successfully by run `32589005957`
at `2026-08-23 01:51 Asia/Taipei`. The first weekly run `32615608243` completed
at `2026-08-23 11:32 Asia/Taipei`; the evidence pipeline passed while the model
quality gate rejected the candidate. Do not reinterpret the model rejection as
an execution failure. Repository push is not a production workflow trigger.
The concise current index is `docs/AUTOMATION_INDEX_V0_1.md`; the historical
execution handoff remains in `docs/RESEARCH_AUTOMATION_HANDOFF_V0_1.md`.

## Data retention split (partially active)

The requested retention policy is recorded in
`config/data_retention_policy_v0_1.json` and
`docs/DATA_RETENTION_POLICY_V0_1.md`:

- Binance Spot `1d` training history remains `2020-01-01` through the latest
  complete UTC day under the existing V0.5 authority.
- Crypto Core 100 V0.1.2 authorizes a fixed 2022-08 through 2026-07 Binance USD-M
  `15m` / `1h` / `4h` dataset for 100 unique Crypto markets after the V0.10
  window. Pionex Alternative Assets V0.1 now supplies the separate metadata
  catalog; its historical candles and training remain unauthorized.
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

The exact proposal is machine-readable in
`config/post_window_research_successor_schedule_v0_1.json`: closed-candle
roll-forward every four hours at UTC `01:17/05:17/09:17/13:17/17:17/21:17`,
weekly Shadow ablation Sunday `05:17 UTC`, and monthly drift/universe review on
day 2 at `03:17 UTC`. It has no workflow and is not execution authority.

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
