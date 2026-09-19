# Project Map V0.1

This is the short current-entry map. It does not replace `PROJECT_STATUS.md` or
any versioned authority.

## Read in this order

1. `PROJECT_STATUS.md` — current formal stage and safety boundary.
2. `docs/PRODUCT_ARCHITECTURE_V0_1.md` — multi-asset, daily-opportunity-first product architecture.
3. `docs/EXTERNAL_MARKET_CONTEXT_V0_1.md` — six pinned external crypto-context sources normalized from prefetched evidence; no network capture or Router behavior change.
4. `docs/DAILY_OPPORTUNITY_ENGINE_V0_1.md` — multi-asset attention candidate selector.
5. `docs/STRATEGY_ROUTER_V0_1.md` — dynamic multi-strategy compatibility router.
6. `docs/STRATEGY_LIBRARY_V0_1.md` — governed reusable strategy-family registry and lifecycle metadata.
7. `docs/STRATEGY_FAMILY_VALIDATION_V0_1.md` — cross-asset/cross-regime family generalization review layered on existing Edge Validation.
8. `docs/STRATEGY_RESEARCH_SCORECARD_V0_1.md` — deterministic research-priority ranking of family evidence; no strategy-selection authority.
9. `docs/RISK_POSITION_SIZING_V0_1.md` — stop-preserving account-risk and bounded position-sizing research layer.
10. `docs/PORTFOLIO_ADMISSION_V0_1.md` — explicit-basket total-risk, concentration and strategy-overlap admission gate.
11. `docs/PAPER_EXECUTION_V0_1.md` — deterministic handoff into the existing Repository Paper Broker after portfolio admission; LONG intent recording only, no automatic/live path.
12. `docs/PAPER_FILL_ORDER_LIFECYCLE_V0_1.md` — deterministic paper fills, partial fills, costs and stop/target lifecycle over normalized liquidity bars.
13. `docs/PAPER_ACCOUNT_POSITION_STATE_V0_1.md` — immutable paper cash/equity/open-position snapshot and Portfolio existing-exposure export.
14. `docs/PAPER_CYCLE_ORCHESTRATOR_V0_1.md` — manual deterministic account → portfolio → paper-intent preparation; no broker submission.
15. `docs/PAPER_SUBMISSION_SESSION_V0_1.md` — exact-cycle-id-confirmed complete-basket submission into the in-memory Repository Paper Broker.
16. `docs/PAPER_LIFECYCLE_BATCH_V0_1.md` — exact-session-id-confirmed complete-basket lifecycle simulation and Account-ready record emission.
17. `docs/PAPER_ACCOUNT_ADVANCE_V0_1.md` — exact-batch-id-confirmed latest-record replacement and next Account rematerialization.
18. `docs/PAPER_LOOP_CHECKPOINT_V0_1.md` — exact-advance-id-confirmed portable next-account handoff with rematerialization/exposure reconciliation.
19. `docs/PAPER_LOOP_RESUME_V0_1.md` — exact-checkpoint-id-confirmed checkpoint consumption into the existing manual Paper Cycle engine.
20. `docs/PAPER_LOOP_INTEGRITY_V0_1.md` — audit-only two-or-more-round lineage, Checkpoint chaining and deterministic replay verification.
21. `docs/PAPER_LOOP_RUN_PACKAGE_V0_1.md` — portable self-verifying transcript/proof package with per-stage SHA manifest; not execution authority.
22. `docs/PAPER_RUN_PACKAGE_ARTIFACT_EXPORT_V0_1.md` — verified canonical Run Package export plus manual GitHub Artifact secondary copy; not execution authority.
23. `docs/LIVE_PAPER_SIMULATION_V0_1.md` — public-live-market-data paper runtime with tick-by-tick lifecycle progress; no private or real order path.
24. `docs/LIVE_PAPER_RUN_COORDINATOR_V0_1.md` — restartable append-only Live Paper run-step coordination over Local/R2 Run Store; manual-only, no cron or real orders.
25. `docs/LIVE_PAPER_RUN_RECOVERY_V0_1.md` — persisted-run reconciliation plus missing-result-seal-only repair; no provider replay and no state/tick/step rewrite.
26. `docs/PAPER_RUN_STORE_V0_1.md` — explicit Local JSON / Cloudflare R2 content-addressed paper-state persistence and read-only object listing.
27. `docs/PAPER_RUN_CONDITIONAL_WRITE_V0_1.md` — storage-only atomic create-if-absent primitive for future run-slot claims; not wired into Coordinator.
28. `docs/AUTOMATION_INDEX_V0_1.md` — the schedules that can still run.
29. `docs/STRATEGY_INDEX_V0_1.md` — baseline, technical analysis and research layers.
30. The exact config and receipt named by the stage being changed.

## Current bounded data and Paper stages

| Stage | Current contract | State |
| --- | --- | --- |
| V0.12 successor provider metadata capture | `config/provider_equivalence_v0_12_successor_metadata_window_v0_1.json` plus its authority receipt | V0.10 runs #36–#41 remain incomplete fail-closed evidence; V0.10 schedule is retired and V0.12 is the only bounded metadata schedule after exact protected-main merge; no replay/backfill |
| Binance USD-M Crypto Core | `config/binance_usdm_detailed_history_v0_1_2.json` | 100 Crypto markets, 10 resumable R2 shards; authorized only after the V0.10 window |
| Pionex alternative assets | `config/pionex_alternative_assets_observability_v0_2.json` | V0.1 supplies the 125-candidate registry; V0.2 authorizes one post-window metadata validation/diff/capacity path; historical candles still need separate authority |
| Pionex Paper successor | `config/post_window_paper_training_v0_2.json` | prepared, but no workflow or provider access until V0.11 and a separate holdout-access authority |

The legacy Paper successor contract remains historical/prepared research
lineage. Current Live Paper V0.1 separately authorizes public Pionex market data,
simulated paper lifecycle/account advancement and explicit paper-state
persistence. It still does not create a private exchange order path, force a
trade count, open replacement holdout or authorize real-money trading.

## Current directory roles

| Path | Current role |
| --- | --- |
| `src/crypto_autopilot/` | reusable domain implementation; package layout is documented in `docs/PACKAGE_STRUCTURE_V0_1.md` |
| `scripts/` | stable CLI entrypoints used by Actions and frozen receipts; intentionally flat so historical command paths do not move |
| `config/` | versioned contracts and authorities; older versions remain immutable evidence |
| `research/receipts/` | immutable results and transitions; never a cleanup target |
| `.github/workflows/` | executable, manual or regression Action entrypoints; current classification is machine-checked by `config/project_convergence_v0_1.json` |
| `web/` | static read-only Pages shell and non-authoritative projections |
| `tests/` | fail-closed behavior, lineage and authority regression tests |
| `infra/render/` | current proven free transport implementation |
| `infra/cloudflare/`, `infra/koyeb/` | historical transport implementations retained only for regression/evidence |

## Website layout

```text
web/
├── index.html
├── assets/
│   ├── css/
│   ├── images/
│   └── js/
└── data/
```

`web/data/` remains flat because V0.10/V0.11 checks bind several exact paths.
Only one current large image remains. Removed design experiments are recoverable
from Git history and are not shipped to Pages.

## What “old” means here

- Removed from the current product surface: unused web design assets and expired cron triggers.
- Preserved but clearly classified: frozen configs, receipts, historical CLI paths, historical workflows and transport implementations.
- Never silently revived: retired provider access, R2 writes, source switching, holdout access or trading paths.
