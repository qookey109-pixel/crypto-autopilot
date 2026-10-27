# VNext Shadow causal feature-coverage review V0.1 — successor to #809

**Checkpoint:** 2026-10-26 Asia/Taipei. **Reviewed starting main:** `d7f45deadbfe0a835e33a79747ddc854b74f1067` (merged V3 #812). This is a dated branch note; re-resolve actual main before any further change. CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER / 0 USD / PAPER-LIVE-PAPER ONLY. No new execution authority.

## 2026-10-27 correction: timestamp checks are not computation proof

The dated discussion below uses “causally attested” for a source-bar and availability timestamp ordering check. That phrase was too strong: the timestamps are caller-reported and the checker does not independently recompute the feature or prove which inputs were used. Plausible timestamps alone cannot establish that the feature calculation avoided future information. The successor checker records timestamp-order validation separately and leaves computation-level no-lookahead verification false. The frozen 2026-10-26 archive receipt and its legacy `no_lookahead_verified_for_attested_feature_snapshots` flag are preserved as historical outputs of the earlier checker; that flag is not proof of causal computation or of availability at an earlier signal cutoff. Historical replay still requires separately validated point-in-time inputs and calculation logic.

## Delivery identity and existing evidence

Earlier [PR #809](https://github.com/qookey109-pixel/crypto-autopilot/pull/809) implemented the pure feature-coverage checker, but GitHub now reports its pre-V3 branch as **not mergeable**. This successor ports the code, original synthetic regression tests and additional strict decision-time boundaries on **post-#812 main**, rather than rebasing frozen receipts, forcing a merge or overwriting the V3 dashboard. #809 stays an unmerged historical record.

The current merged V3 website already distinguishes:
- Frozen historical **16 authenticated original ZIPs / 21 target context observations**, **15,604** overlapping identical 60-minute candles, nine >6-hour observation gaps, maximum source lag 55 minutes, `REVIEW_REQUIRED / INSUFFICIENT`; this is not continuous readiness.
- A **separate, later** natural run [#40162915838](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/40162915838), artifact #12586364157, original ZIP **independently authenticated** by [PR-only audit #40183609493](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/40183609493). It does **not** establish 17 consecutive observations.
- Still later natural [#40196502726](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/40196502726), artifact #12599619291, **metadata-only**, NOT authenticated original ZIP bytes, candle time or feature contents; must not be added to verified counts.
- Latest checked Health [#40191745309](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/40191745309) `ALERT` on Core100 training, Maintenance [#40191790370](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/40191790370) `STALE_DRAFT_REVIEW_REQUIRED` on older #808. Older incidents remain immutable. No current Core100 quality promotion: `REJECT`.

## Scope of pure checker

`src/crypto_autopilot/research/shadow_feature_coverage_v0_1.py` accepts **caller-supplied normalized report objects** and invokes the existing `inspect_shadow_batch_continuity` first. It has no I/O, cannot download or authenticate GitHub ZIP files, and does not change current dashboard behavior. It examines 15 preregistered feature fields across four collector families (technical, structure, patterns, event radar), with strict categorical states and finite numeric types.

For an observation to be causally attested **as of its research capture**, the reported source bar must exactly match the last closed 60-minute input candle's start, and `available_at_ms` must fall between **that bar's close** and **capture**. Missing source/availability time is `unattested_time`; missing field is `missing`; present `null` is `explicit_null`; legitimate zero and `NONE` are observed values rather than inferred positive signals. Malformed/out-of-range values, future/premature features, revised overlapping candles, tampered record hashes or unsafe authority states raise `ContinuityReviewRequired`.

The output counts **all report snapshots** separately from **unique (market, 60M candle start) pairs** to prevent duplicated source candle evidence from inflating distinct history. A feature `point_in_time_coverage_fraction` is `null` if missing keys or unattested times make the denominator noncomparable. `15M` and `4H` remain `NOT_COLLECTED_IN_THIS_REPORT`. Fees, funding, slippage, net return and production eligibility remain UNKNOWN/false. The feature diagnostic only proves code-path acceptance of *synthetic caller data* until original archive-level source authentication is separately performed.

**Critical temporal distinction:** a feature whose observed availability is before the collector's capture is not necessarily available at an earlier hypothetical historical **signal/entry cutoff**. Accordingly `historical_signal_cutoff_no_lookahead_proven=false` and `signal_outcome_predictive_edge_proven=false` are immutable in this diagnostic. Full historical replay requires a separately bound signal decision time, point-in-time source timeline, known costs and overlap logic. Passing capture-level tests must never be treated as a validated backtest or training authorization.

## Acceptance gates and boundary

Regression tests use synthetic normalized 5-market, 240-candle reports and exercise timestamp/identity mismatch, absent and null, wrong categorical/numeric types, unavailable sources, genuine zero, revised overlap, continuous-count ambiguity and exact gate propagation. Run through GitHub-hosted Python 3.12/3.13, Ruff/workflow-static and security checks. No raw real-market ZIPs were downloaded in this successor, and no historical replay, rolling Shadow, PAPER decisions, D1/R2/provider calls, holdout/promotion/source switch, billing/bootstrap retry, Cron dispatch or live-money access was performed.

**Not a release by itself:** new code remains PR-only until owner authorizes a merge and exact-head gates pass. Defer genuine authenticated rolling/replay availability, timing, fees/funding/slippage, market source provenance, budget/writer/D1 and formally authorized PAPER cycle to separately gated work.
