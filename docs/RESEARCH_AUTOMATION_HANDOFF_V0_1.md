# Research Automation Handoff V0.1

Status date: `2026-09-03` (`Asia/Taipei`).

This handoff is an operations guide, not execution authority. Repository
`main`, versioned configs and receipts remain authoritative. It does not
independently enable provider access, R2 access, holdout access, model
promotion, trade plans, real-money orders or live trading.

## Project information

Project: `Qookey Crypto Autopilot`

Repository: `https://github.com/qookey109-pixel/crypto-autopilot`

Public dashboard: `https://qookey109-pixel.github.io/crypto-autopilot/`

Formal Repository authority at this observation:
`0f1c7675f15301c248b64bbaa4a10bc956f3fdf6` on `main`, merged by PR #213.
If `main` has advanced, use the newer Repository authority instead of this
observation.

## Current state

- GitHub Automatic Research Operations V0.1 is merged and effective on `main`.
  PR #213 merged at `0f1c7675f15301c248b64bbaa4a10bc956f3fdf6`.
- Research Automation Health V0.2 is the single current cron control plane. Its
  configured cadence is `57 */2 * * *` UTC, and it monitors all seven current
  scheduled workflows using GitHub Actions metadata only.
- Current scheduled Health V0.2, Research Signal Layer V0.2 and Research Signal
  Quality V0.1 runs have been observed completing successfully on the current
  `main`. Manual and pull-request events do not count as cron-health evidence.
- V0.10 scheduled metadata capture is retired. Runs #36 through #41 remain
  immutable fail-closed evidence after the Pionex `type=PERP` query reached the
  frozen scope but failed the required `status` / `contractType` parser
  contract before R2 client construction.
- V0.10 cannot be replayed, backfilled or regraded. Its observed missing/failed
  slots already block complete 194-slot PASS eligibility.
- V0.12 is the separately versioned successor metadata authority and the only
  current metadata-capture schedule. Its exact execution window is
  `2026-09-04T02:00:00Z` through `2026-09-12T03:59:59.999Z`, with `:17` and
  `:47` attempts across 194 UTC hourly slots. At this handoff timestamp the
  V0.12 window has not started yet.
- V0.11 production R2 stability evaluation remains unauthorized and
  `NOT_YET_RUN`.
- Replacement holdout `2026-08-28` through `2026-09-03` remains
  `FROZEN_UNOPENED`. Calendar passage does not authorize candle access.
- `source_switch_authorized=false`, automatic model promotion remains false,
  and all trade-plan / real-money / live-trading authority remains false.
- Project runtime budget remains `0 USD/month`; paid fallback is forbidden.

## Current automation schedule

| State | Workflow | UTC cadence / window | Boundary |
| --- | --- | --- | --- |
| Current bounded successor | Provider Equivalence V0.12 metadata capture | `:17` and `:47`, only `2026-09-04T02:00:00Z` through `2026-09-12T03:59:59.999Z` | metadata-only; separate R2 namespace; no holdout or production evaluation |
| Continuous | Research Signal Layer V0.2 | daily `02:17` | bounded structured-signal ingestion |
| Continuous | Research Signal Quality V0.1 | daily `02:47` | allowlisted R2 lineage reads only |
| Continuous / alerting | Research Automation Health V0.2 | every two hours at `:57` | GitHub Actions metadata only; all seven current crons monitored |
| Post-window | Binance USD-M Crypto Core 100 V0.1.2 | every six hours at `:23` during the bounded September materialization window | fixed pre-holdout source range; 10 serialized R2-only shards |
| Conditional post-window | Binance USD-M Crypto Core 100 Training V0.1.2 | Sunday `04:37` | skips until all 100-market shards exist; research-only |
| Post-window | Pionex Alternative Assets Observability V0.2 | first `2026-09-04T02:53:00Z`, then bounded weekly September observations | Pionex metadata only; no historical candles/funding/trades/order books |

The current machine-readable schedule view remains
`docs/AUTOMATION_INDEX_V0_1.md` and
`config/github_automatic_research_operations_v0_1.json`.

## Preserved V0.5 evidence

The first V0.5 bootstrap evidence remains historical and must not be re-run as
new authority:

- Monthly governance run `32589005957`: `PASS`, commit `b371b96`, artifact
  digest
  `1960647b1e7a511d71a1ec6cf8dcf3d3f3ad86acae827377f2409ba71fbce2ad`.
- Weekly training run `32615608243`: pipeline `PASS`, model quality `REJECT`,
  artifact digest
  `69d45bc55f846d17ce8ff79a55aa2fa974dd67eec9d11903e67a1319bc41081e`.
- First weekly dataset: 748 requested markets, 723 audited markets and 702,023
  rows.
- The model-quality rejection remains useful negative evidence. It is not a
  failed pipeline and does not authorize strategy changes or model promotion.

## V0.6 Shadow and research model state

The V0.6 Shadow implementation was merged to `main` by PR #177. It remains a
research-only challenger and provides:

- baseline, trend, price/volume and volatility feature-group ablations;
- ECE/MCE calibration and descriptive ATR/ADX/volume regime slices;
- immutable dataset/config/trainer/environment experiment fingerprints;
- bounded search with zero automatic retries or automatic promotion;
- explicit false authority for provider reads, production R2 writes, holdout,
  trade plans, real-money orders and live trading.

Real-data Shadow execution still requires the exact downstream authority and
eligible data lineage. The existence of the code does not grant that authority.

## Completed items

- [x] Preserve first monthly V0.5 baseline evidence without repeating manual activation.
- [x] Preserve first weekly V0.5 pipeline `PASS` and model `REJECT` separately.
- [x] Merge V0.6 Shadow research implementation through PR #177.
- [x] Retire post-cutoff V0.5/Pionex automatic provider reads.
- [x] Preserve V0.10 runs #36–#41 as immutable fail-closed evidence.
- [x] Retire the remaining V0.10 schedule without replay or backfill.
- [x] Merge V0.12 successor metadata authority through PR #212 and preserve its append-only binding.
- [x] Merge GitHub Automatic Research Operations V0.1 through PR #213.
- [x] Make Research Automation Health V0.2 the single current health cron.
- [x] Keep all current automation under the existing 0 USD / no-trading boundaries.

## Pending / time-gated items

- [ ] Do not manually start V0.12 early. Its first eligible time is
  `2026-09-04T02:00:00Z` (`2026-09-04 10:00 Asia/Taipei`).
- [ ] Preserve scheduled V0.12 evidence exactly as produced. Do not manufacture
  replacement captures for failed or missing slots.
- [ ] Do not read/evaluate production V0.12 R2 receipts until a separate
  versioned production-evaluation authority exists.
- [ ] Keep replacement-holdout candles unopened until a separately versioned
  holdout-access authority exists.
- [ ] Let Crypto Core 100 V0.1.2 and Pionex Alternative Assets V0.2 obey their
  existing not-before and scope gates; do not create a second execution path.

## Known issues and risks

- V0.10 is scientifically incomplete and cannot produce a complete 194-slot
  PASS dataset. That result is immutable evidence, not something to repair.
- V0.12 evidence is `NOT_YET_RUN` at this observation; future success must not
  be assumed before scheduled evidence exists.
- The replacement holdout is still unopened even though its calendar range ends
  on 2026-09-03. Time passing is not access authority.
- Historical Markdown may still describe superseded schedules. Use
  `PROJECT_STATUS.md`, `docs/AUTOMATION_INDEX_V0_1.md`, current versioned
  configs/receipts and this handoff for current operations; preserve historical
  contracts instead of rewriting them into new semantics.
- Any provider freshness, lineage, exact config binding, R2 FREE-ONLY headroom
  or schedule-integrity failure must fail closed.

## Next step

Continue normal schedule-driven research operations on GitHub. The next
scientific execution boundary is the V0.12 window opening at
`2026-09-04T02:00:00Z`. Do not manually backfill V0.10, manually pre-run V0.12,
open the replacement holdout or run production stability evaluation. After the
V0.12 window completes, freeze the exact observed lineage first and create a
separate production-evaluation authority before reading/evaluating production
V0.12 receipts.

## Stop conditions

Stop and record evidence rather than bypassing a gate when any of these occurs:

- model quality is `REJECT` or `NOT_READY`;
- a V0.12 slot is missing, stale or internally inconsistent;
- R2 headroom, provider freshness, lineage or exact config binding fails;
- an action would replay/regrade V0.10, open the replacement holdout, switch
  providers, relabel Binance as Pionex-native, enable promotion or change
  trading authority;
- a task requires paid cloud capacity or secret disclosure.

## New-chat continuation

Copy this into a new task:

> Continue `qookey109-pixel/crypto-autopilot` from latest Repository `main`.
> Re-read `PROJECT_STATUS.md`, `README.md`, `AGENTS.md`,
> `docs/AUTOMATION_INDEX_V0_1.md`,
> `docs/RESEARCH_AUTOMATION_HANDOFF_V0_1.md` and the current V0.12
> config/receipt before acting. At the 2026-09-03 observation, PR #213 is merged
> at `0f1c7675f15301c248b64bbaa4a10bc956f3fdf6`; GitHub Automatic Research
> Operations V0.1 is effective; Research Automation Health V0.2 is the single
> health cron and current scheduled health/signal jobs are succeeding. V0.10 is
> retired incomplete fail-closed evidence and must not be replayed/backfilled.
> V0.12 is the only current metadata schedule but cannot start before
> `2026-09-04T02:00:00Z`. Preserve production evaluation `NOT_YET_RUN`,
> replacement holdout `FROZEN_UNOPENED`, provider separation, PAPER-ONLY and
> 0 USD. Do not read production V0.12 receipts without separate authority.