# Project Map V0.1

This is the short current-entry map. It does not replace `PROJECT_STATUS.md` or
any versioned authority.

## Read in this order

1. `PROJECT_STATUS.md` — current formal stage and safety boundary.
2. `docs/AUTOMATION_INDEX_V0_1.md` — the schedules that can still run.
3. `docs/STRATEGY_INDEX_V0_1.md` — baseline, technical analysis and research layers.
4. The exact config and receipt named by the stage being changed.

## Current bounded data and Paper stages

| Stage | Current contract | State |
| --- | --- | --- |
| Binance USD-M Crypto Core | `config/binance_usdm_detailed_history_v0_1_2.json` | 100 Crypto markets, 10 resumable R2 shards; authorized only after the V0.10 window |
| Pionex alternative assets | `config/pionex_alternative_assets_observability_v0_2.json` | V0.1 supplies the 125-candidate registry; V0.2 authorizes one post-window metadata validation/diff/capacity path; historical candles still need separate authority |
| Pionex Paper successor | `config/post_window_paper_training_v0_2.json` | prepared, but no workflow or provider access until V0.11 and a separate holdout-access authority |

The Paper successor reuses the existing Repository Paper Broker and Pionex
public adapter. It does not create a second broker, force a trade count or add a
live-order path.

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
