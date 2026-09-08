# Data Overview

Updated: 2026-08-27

This file is the single human-readable index of the project's current data
lanes. It is a normalized view, not execution authority. When this index and a
versioned config or receipt disagree, follow `PROJECT_STATUS.md`, the current
config and its receipt in that order. Historical receipts remain immutable.

## Current inventory

| Data lane | Provider and coverage | Resolution / scope | Persistent store | Current evidence state | May train a model? |
| --- | --- | --- | --- | --- | --- |
| Binance Spot daily | Binance public Spot, `2020-01-01` through the latest complete UTC day | `1d`; USDT/USDC catalog; 748 requested and 723 continuity-audited markets in the verified V0.3 baseline | Cloudflare R2 only | 701,275 rows verified by the V0.3 receipt; the first V0.5 weekly pipeline completed but its model-quality gate was `REJECT`; scheduled provider/R2 reads stopped at `2026-08-27T00:00:00Z` | Research training was authorized under bounded V0.5; no automatic promotion or trading |
| Binance USD-M detailed history V0.1.1 | Binance Vision, fixed `2022-08` through `2026-07` | Target 250 USDT markets; native `15m`, `1h`, `4h`; no raw ticks | Cloudflare R2 only after execution | **Authorized but not started**; earliest execution `2026-09-04T02:00:00Z`; backfill authority stops `2026-10-01T00:00:00Z` | Only after the complete dataset exists; research-only four-fold walk-forward |
| Binance Funding V0.2 | Binance USD-M / Binance Vision | 15 continuity symbols; 94 annual canonical objects | Cloudflare R2 | Materialization PASS: 1,003 source archives, 192/192 authorized R2 identities and 91,747 observations; HYPEUSDT 2026 deferred | Provider-separated research evidence only |
| Historical foundations | Pionex M1/M1A/M1B and Binance 2025 pilot | M1B: 13,230 candles; Binance pilot: 206 canonical R2 objects | Cloudflare R2 | Frozen PASS evidence | Historical research only; no source relabeling |
| Pionex current paper research | Pionex public futures | 15 PERP candidates; `15M`, `60M`, `4H`, `8H`, `1D`; public K-lines, funding, trades, depth and basis | Repository evidence / Pages summary; no production R2 | Bounded workflow stopped provider access at `2026-08-27T00:00:00Z` as designed | Candidate generation and Repository Paper Broker replay only |
| Paper Exploration V0.2 | Local deterministic replay inputs | Up to 12 independent samples/day, at most 2 per symbol | Local ephemeral evidence only | Prepared research harness; not a scheduled portfolio | No promotion; cannot be presented as formal portfolio performance |
| Research signal layer V0.2 | Capafy structured JSON plus X metadata-only source | Three bounded sources; daily collection at `02:17 UTC` | Dedicated Cloudflare R2 namespace | Active research collector; raw provider payloads are not persisted | Context/challenger evidence only; never a direct trade trigger |
| V0.10 provider metadata | Pionex public metadata plus authenticated Render relay for Binance USD-M metadata | 15 candidates / 45 pairs; 194 UTC hourly slots; attempts at `:17` and `:47` | Three immutable R2 objects per complete capture | Authority is effective, but the live GitHub observation below shows scheduled execution is currently missing | No. Metadata-only; not candles, backtest or strategy data |
| Replacement holdout | `2026-08-28` through `2026-09-03` | Candle holdout | Not opened | `FROZEN_UNOPENED` | No access or evaluation is authorized |

## Live operational observation

At `2026-08-27T02:53:17Z`, GitHub's public Actions API reported the V0.10
workflow as `active`, and `main` contained the frozen `:17/:47` schedule. The
same API returned 17 historical pull-request runs and **zero scheduled runs**.
Six attempts (`00:17`, `00:47`, `01:17`, `01:47`, `02:17`, `02:47`) were due
before the observation.

Current classification: **P0 operational incident / missing scheduled
execution**. This does not change the V0.10 authority, and it is not evidence
that any R2 object exists or is missing because production R2 was not read.
The frozen operations policy requires missed slots to remain observed failures:
manual capture, retroactive backfill, threshold changes, a second capture path,
holdout access and silent provider switching remain forbidden.

The read-only automation-health monitor allows a two-hour startup grace from
the window boundary. It therefore could report PASS during the initial grace;
after the grace expired, the repository's health evaluator classified this
exact no-run state as `STALE_NO_RUN`. The next scheduled monitor run is allowed
to surface the alert, but it cannot repair it.

Public workflow metadata:

- workflow: <https://github.com/qookey109-pixel/crypto-autopilot/actions/workflows/provider-equivalence-v0-10-render-metadata-capture.yml>
- authority/config: `config/provider_equivalence_v0_10_final_atomic_cutover_v0_1.json`
- frozen operating response: `config/v0_10_capture_window_operations_v0_1.json`

## What is and is not stored locally

- No project-generated market-history Parquet, CSV, JSONL or ZIP dataset was
  found in the repository worktree during this update.
- The local checkout was approximately 211 MB, primarily source code, Git
  history and the ignored Python virtual environment. Package test fixtures
  inside `.venv` are not project market data.
- `web/data/` contains only small normalized dashboard summaries. Raw K-lines,
  training datasets, model artifacts and R2 evidence are intentionally not
  published through GitHub Pages.
- GitHub Actions runner workspaces are ephemeral. Authorized persistent market
  history belongs in provider-separated R2 namespaces only.

## Retention rules, converged

1. Binance Spot daily history is the existing long-horizon lane: fixed start
   `2020-01-01`, append through the latest complete UTC day when an active
   authority permits execution.
2. USD-M detailed V0.1.1 is a **fixed** four-year source window (`2022-08`
   through `2026-07`), not an active rolling-retention job.
3. `config/data_retention_policy_v0_1.json` remains
   `PREPARED_NOT_ACTIVE`. Its proposed rolling policy must not be mistaken for
   current provider-read or R2-write authority.
4. Funding and historical foundations retain their frozen evidence; new
   interpolation, provider splicing or relabeling is not permitted.
5. Website projections remain aggregate-only. Internal history does not need
   to appear on Pages to be available for authorized R2-backed research.

## Remaining problems, in priority order

1. **P0 — V0.10 scheduled runs are absent.** Preserve the missing-slot
   evidence and let the authorized read-only health/observer paths report it.
   Do not manually backfill.
2. **P1 — 250-market intraday history is not present yet.** It is an authorized
   future backfill, not current training data. Calling the dashboard target
   “250 markets” must not imply completion.
3. **P1 — the current Spot model failed its quality gate.** Five simple daily
   features are not enough evidence for promotion. V0.6 ablation remains
   prepared research, not an active self-improving model.
4. **P1 — there is no complete continuous-learning loop.** Current collection,
   training, evaluation and paper replay are separated intentionally; no model
   can automatically replace another model.
5. **P2 — KOL evidence is sparse and asymmetric.** Structured forecasts may be
   scored; X is metadata-only and cannot be converted from prose into a market
   direction.
6. **P2 — current-market paper research is paused at the frozen boundary.** A
   new post-window authority is required before provider reads resume.
7. **P2 — repository work is not converged to one clean branch yet.** The
   current checkout contains substantial uncommitted work and unique local
   branches. Preserve it; reconcile by reviewed PR rather than deleting or
   force-merging evidence.

## Source files

- `PROJECT_STATUS.md`
- `config/binance_spot_r2_training_governance_v0_5.json`
- `research/receipts/2026-08-22-binance-spot-r2-automated-training-v0-3-pass.json`
- `config/binance_usdm_detailed_history_v0_1_1.json`
- `research/receipts/2026-08-19-binance-funding-r2-v0-2-materialization.json`
- `config/paper_training_v0_1.json`
- `config/research_signal_layer_v0_2.json`
- `config/provider_equivalence_v0_10_final_atomic_cutover_v0_1.json`
- `config/v0_10_capture_window_operations_v0_1.json`
- `config/data_retention_policy_v0_1.json`
