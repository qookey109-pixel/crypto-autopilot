# Optimization and schedule review — 2026-09-22

Status: engineering review and implementation plan; **not execution authority**.
Observed at approximately 09:00 UTC / 17:00 Asia/Taipei.
Evidence basis: Repository main `4767ae2651d80b9465affc416ac71efa1022d6b4`.
Resolve live main again before implementation or merge; this is a dated audit.

## Verified state and completed work

- Main post-merge [CI](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/35706926631), [CodeQL](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/35706926670), and [Freeze Guard](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/35706926672) succeeded.
- [PR #441](https://github.com/qookey109-pixel/crypto-autopilot/pull/441) is open/mergeable at head `509baa911054ea2c1ebb695152b2d3a1f201110e`, base equal to the evidence-basis main. CI `35707076210` and CodeQL `35707076009` succeeded. Python 3.13 CI reports 1,599 tests and 561 subtests passed; informational type errors are 216. Merge remains a human gate.
- Six dependency PRs remain open: #326–#331. Review them independently; major-version changes need compatibility checks, with pyarrow last. PR #437 was closed without merging because its target was receipt-bound.
- Signal Quality upstream chaining, exact-evidence reuse, desktop/mobile browser checks, npm locking, safe workflow source routing, and Paper atomic slot claims already exist. Do not reimplement these completed changes.
- Core100 History is complete; model quality remains REJECT. ZEC V0.3 and V0.4 completed without an eligible development candidate. Current completion receipts override earlier preparation paragraphs.
- Latest observed Pages workflow `35702250343` succeeded. This audit uses run metadata; it does not independently claim that a new browser session verified the deployed site.

## Concrete defects addressed in this change

1. `package-lock.json` was missing from both Pages push and pull-request path filters. A lockfile-only dependency update could bypass the workflow that installs the locked dependencies and validates the browser. Include it in both filters, with a regression check for each event.
2. The cloud projection used `now > active_until`, while Health uses `now >= active_until` and Pionex Observability declares `catalog_stop_exclusive_utc`. At exactly `2026-10-01T00:00:00Z`, the old projection reported seven effective schedules and could show fresh evidence even though the bounded authorization had ended. Use the exclusive-end comparison in both freshness and schedule counts. Keep all workflow/config/receipt authority bytes unchanged except the unrelated Pages path filters.

The expiry tests fail on the original implementation and pass with the corrected comparison. Lockfile event tests likewise fail before the path-filter change. These are engineering fixes; they add no market-data or Paper execution path.

## Schedule inventory and observation

Sources: `config/github_automatic_research_operations_v0_5.json`,
`config/research_automation_health_v0_2.json`, and actual workflow declarations.
Eight workflow files declare cron; seven are effective at the observation time.
The eighth is the expired, frozen V0.12 declaration and stays immutable.

| Task | Declared Asia/Taipei schedule | Latest observed scheduled run | Decision |
| --- | --- | --- | --- |
| Resource Hub change watch | Daily 09:13 | 35693414972, success | Keep; candidate review only |
| Research Signal | Daily 10:17 | 35701209856, success | Keep |
| Signal Quality | Upstream success + daily 10:47 backstop | 35702215222, success | Keep chaining and exact-evidence dedup |
| Automation Health | Every two hours at :57 | 35690943484, success | Keep; metadata only |
| Core100 Training | Sunday 12:37 | 35502249846, success | Keep fingerprint NO_CHANGE gate; workflow success does not prove accepted model |
| Pionex alternative-assets observability | September 4 at 10:53; September 6/13/20/27 at 11:53 | 35500652150, success | Ends exclusively October 1 at 08:00; no automatic renewal |
| Dashboard | Upstream events + daily 12:43 backstop | 35587393103, success | Keep; content dedup and post-deploy browser validation |

Run links use `https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/<run_id>`.
The last Dashboard row refers specifically to the scheduled backstop, not the newer event-triggered deployment.
Scheduled runs may start later than declared time. For example, September 22 Signal was created at 07:45:28 UTC against a 02:17 UTC cron. This observation is not evidence of a code failure or permission to rerun it.
[GitHub documents delayed and potentially dropped scheduled runs](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

Do not increase production frequency from one day's observations. Collect at least seven days of scheduled-run starts, gaps, durations, conclusions, and event-chain cancellations. Evaluate freshness using current policy. Manual/event-triggered success must not hide a missing scheduled run. Provider/R2 usage and business outcomes stay UNKNOWN without separately permitted evidence.

## Proposed work order and acceptance

These are delivery targets and review checkpoints, not new GitHub cron jobs.

| Priority / target | Work | Acceptance and gate |
| --- | --- | --- |
| P0 / this change | Pages lockfile coverage and exclusive expiry | Focused regressions, CI, workflow lint, Pages PR browser checks; human merge |
| P1 / September 23–24 | Reconcile current navigation and local work inventory | Compare dirty files with exact main; classify local-only/already-merged/conflicting; preserve local work and receipt bytes; no cleanup/delete without exact scope |
| P1 / September 23–25 | VWAP offline feature specification and synthetic prototype | Single-provider causal features, boundary/warm-up tests, unchanged training feature contract; separate small PR |
| P2 / September 24–28 | Dependency and remaining type debt review | One low-risk module or dependency per PR; frozen-byte binding scan first; no blanket ignores or coupled runtime upgrades |
| P2 / September 29 onward | Review seven days of operations evidence | Decide whether a versioned cadence proposal is warranted; no change solely because a run is late |
| Fixed checkpoint / October 1 08:00 Taipei | Verify observability expiration | Effective schedule count becomes six, two declarations are expired; frozen V0.12 and ended Pionex path do not reactivate |
| Separate authority gate | Hourly Paper / external Context / new research training | Versioned scope, budgets, provenance, failure recovery, input selection and tests reviewed before execution |

The existing Codex heartbeat `crypto` is repurposed from its paused, expired September 15 readiness watch into a six-hour read-only project/schedule review. It checks current Repository and Actions metadata and notifies only on a meaningful change, failure, completion or decision. It does not execute this implementation backlog. Its app configuration is separate from Repository production schedule authority.

## VWAP integration decision

Current code already has a **20-bar** rolling VWAP and normalized distance in
`src/crypto_autopilot/features/advanced.py`, used by training and Paper code.
Twenty bars are not twenty days. Preserve the existing behavior and feature order.

The [VWAP+ publication](https://www.tradingview.com/script/2aNKQLeh-VWAP-Y-Algo/)
describes anchored/rolling VWAPs and deviation bands. Its source is advertised as
CC BY-NC-SA 4.0; full Pine source was not audited in this review. Direct code reuse
needs license compatibility review. An independent implementation of standard
VWAP mathematics can be specified without copying the Pine script or adding a
TradingView runtime dependency.

Recommended first slice:

- Add an isolated research feature module under the existing `features/` package; no new framework or second pipeline.
- UTC day/week/month anchors plus 7-day and 30-day trailing windows, with explicit window endpoint and week-start semantics.
- Closed bars only, explicit `available_at`, HLC3 price and a declared volume unit from one provider/instrument.
- Return normalized price distance and volume-weighted standard-deviation position; zero volume, zero variance, insufficient history and gaps have explicit not-ready/error semantics.
- Require tests for day/week/month reset, prefix invariance (future bars cannot change earlier output), trailing-window eviction, invalid data and incomplete warm-up.
- Preserve existing feature order and model-input fingerprints. Integration into training/ablation needs a new versioned experiment contract with an approved dataset and chronological evaluation.

Defer cross-venue volume aggregation, 90/365-day expansion, Tokyo Initial Balance,
automatic signal/route changes and production scheduling until the first slice
has a demonstrated research need. No existing holdout or consumed ZEC execution
authority is reusable for this experiment.

## Tool integration decision

Use the already-established GitHub interface, Actions, Ruff, mypy visibility,
CodeQL, unittest/pytest, pinned Playwright, actionlint and ShellCheck. No new
paid service or MCP runtime is needed for the defects or the VWAP first slice.

`docs/EXTERNAL_CAPABILITY_REGISTRY_V0_1.md` already indexes downstream evaluations
for TradingView MCP, market-data tools, Tradingcalc, AgentFeed and infrastructure
tools. Reopen a candidate only for a concrete missing capability or a deliberately
reviewed upstream change. Resource Hub discovery does not authorize installation.

## Verification and limits

- Local verification uses bundled Python 3.12 with `PYTHONPATH=src:tests`; no installation into the old checkout is required.
- The earlier chat's Python 3.9 import failures were environment/collection failures, not evidence that current main's tests fail.
- Targeted tests cover cloud projection, Pages workflow contract and Health evaluation; PR CI supplies supported runtime and workflow/browser validation.
- The original local checkout remains on `codex/research-context-v0-1` at `7acfd6c7e1c1a9803520281e64970387f70695e8` with pre-existing changes preserved. This review used an isolated clone.
- No provider/R2/holdout access, research execution, strategy/risk changes, promotion, private exchange API or real trading is performed by this review. FREE-ONLY remains binding.
