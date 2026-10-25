# Qookey VNext V3 evidence-gated delivery — design (2026-10-25)

## Intent and current authority
The product is a **zero-incremental-cost** cloud market/research dashboard plus a recoverable PAPER/LIVE-PAPER simulator, not a live order terminal. Its formal authority is always the freshly resolved GitHub `main`, versioned contracts, actual completed cloud run data and required distinct user approvals. CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER applies; no local checkout, terminal, R2/D1/secret access or off-platform account action. No live orders, holdout use, model promotion, new training or source switch.

Current reviewed main is `805c43d687a37366f53c50c453679bb179222512` after #810. Baseline site passed post-merge 66/66 Pages tests, but V3 is not yet deployed. Existing #807 has valid PR CI on its old head but `mergeable=false` against latest main; this successor starts from the **new** main, keeps #807 unmerged and does not erase its evidence.

## Alternatives and chosen approach
1. **Continue PR #807 despite base conflict**: risks accidental loss of merged #810 hash checks; reject until reconciled.
2. **Rebuild frontend independently with live market API**: expensive to govern, may mislabel Binance signals as Pionex, missing cost/source authority; defer.
3. **Chosen:** evidence-gated successor against exact merged main. Preserve existing site and cards, add minimum read-only provenance/time projection and safe empty-registry reason display, test it with both Python and desktop/mobile Playwright, and progressively reconcile earlier PRs without merging them silently.

## Immediate independently verifiable slice
- Show existing *authenticated historical Shadow 16/21* separately from **latest naturally observed GitHub run metadata** (2026-10-25 schedule run `40162915838`, attempt 1, artifact `12586364157`, original artifact digest `sha256:191fa626fbddd7f4a2a639618157605ab382a343936584fa2755ec2f6c08f03d`). This fresh metadata does NOT authenticate internal ZIP bytes, candle intervals or feature availability. Never increase 16/21 or call a workflow success research validation.
- Versioned metadata input must include exact UTC run/artifact timestamps and explicit `false` flags; invalid/untrusted input displays `UNKNOWN` and no invented fresh run.
- Keep separate source candle time `UNKNOWN`, research run created UTC, artifact created UTC, site publication independent; these are different time semantics.
- The production strategy registry is `EMPTY_NO_ELIGIBLE_STRATEGIES`; with confirmed quality `REJECT` and production NOT_WIRED/NOT_RUN, show `NO_ELIGIBLE_STRATEGY` **as design-time hypothetical refusal reason only**, never `NO_TRADE` actual run result. If registry changes, fail closed to UNKNOWN until new validation.
- Existing top-level EasyRead, Yaozi, Cloudflare Clef and MMT are **manual research links only**, already above VNext panel. No API embedding or credit to market provenance.
- Existing V3 cards: Market Pulse, Current Decision, Candidate Funnel, Research Radar, Context, Decision Trace and System. Unknown price, volume, fees, eligibility or time must remain unknown. Preserve `$10,000` initial *prepared* virtual account, with no fabricated resulting balance/fill/return.
- Preserve dark charcoal/navy, semantic states, phone vertical stacking, keyboard disclosure and no horizontal body overflow. Exact Pages publication hash gate must continue working after merged #810.

## Later acceptance batches (each scoped, separately tested and authorized)
1. Existing Shadow artifacts: original ZIP identity, inner hashes, snapshot schema, causal availability, gaps, multi-timeframe coverage. Only authenticated archives advance the verified count; PR #809 currently pure synthetic feature coverage.
2. Health/Core100 drift, Maintenance `DELIVERY_BRANCH_NOT_AHEAD_OF_MAIN`, Dependabot/failing stale PR review: preserve historical fail evidence, never regrade by a newer green unrelated workflow. PR #811 prepared read-only diagnostic; latest scheduled Core100 #40180181401 remains `RUNTIME_CHANGED` despite Python+Runner drift evidence.
3. Research-to-Dashboard schema with provider/symbol/unit/source time, validation-stage names, freshness, trace lineage and explicit missing fields. Engineering fixture vs archive-audited vs production PAPER are distinct.
4. Shared writer admission, actual billable usage, D1 prepayment meter, slot dedup, limited recovery, account state continuity. Current D1/account-wide capacity/zero-cost remain **UNCONFIRMED**, even if synthetic SQL CI tests pass.
5. Formal main PAPER loop + 10,000 USD virtual account and NO_TRADE reason, only after exact *merged* versioned scope, budget evidence and separately authorized external/cloud action. A configured schedule still requires its own natural result.
6. Rolling Shadow/replay/no-lookahead using existing authorized data, not a 30/60/90-day engineering wait; research evidence never automatically changes qualified candidate ranking, risk limits or source equivalence. P2: Clef shadow, Vibe-Trading selective patterns, derivatives liquidity and trading-control panel.

## Failure / safety acceptance
Malformed metadata, digest, schedule event, incorrect source SHA, new run not authenticated, stale archive, invalid registry or missing site build must not be interpreted as success or zero. Never cite CI/PR mock results as production account or a new Shadow batch. Do not relax #810's exact-published-hash check. Store only minimally needed versioned provenance, not full market snapshots on the website.
