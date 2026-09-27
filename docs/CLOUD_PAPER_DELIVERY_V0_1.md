# Cloud Paper Loop delivery V0.1

CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER. Target: full public-market → opportunity → qualified strategy → risk → paper execution → persistent state → dashboard cycle.

## Completed contract
PR #536 merged the inactive bounded contract and empty production registry. Runtime activation remains disabled. The contract proposes at most 18 provider requests per run (3 universe, 5 hourly candle requests, 10 execution-frame requests), 96 slots/day, and per-operation budget checks. These are ceilings, not permission to spend without current shared-account headroom.

## Public-market adapter
The adapter intersects the curated crypto-only pool in `config/crypto_universe_v0_1.json` with live Pionex symbols and current valid quotes, then applies the existing spread/liquidity rules with a five-market bound. It requests 240 closed hourly bars only, rejects holdout-overlapping request windows before I/O, and rejects missing, duplicate, stale, nonfinite or out-of-window returns. A caller-supplied budget check runs before every request. No source fallback or historical acquisition is added.

Technical features, opportunity scoring and strategy routing reuse the existing implementations. The adapter emits source/time/hash evidence and does not itself submit orders or write R2.

## Discovered integration blockers
1. The existing required macro regime needs canonical TOTAL3, BTC dominance and aligned breadth. The official Pionex public market endpoint list covers exchange market data and does not list these global market-cap metrics. A Pionex API key grants access to authenticated account/API scopes; it does not add global metrics to Pionex market data. The prior CoinPaprika one-shot authority expired on September 19 and does not authorize a new schedule. Missing context remains REGIME_UNAVAILABLE; no fake neutral snapshot or weakened regime gate is allowed.
2. The production strategy registry is empty and Core100 remains REJECT. A research ranking is not execution eligibility.
3. Existing checkpoint creation assumes a preceding account advance; new cash-only genesis must not fabricate a trade.
4. Shared-account R2 allowance evidence and implementation-bound activation are required before enabling the proposed cron.

These are explicit product dependencies, not reasons to reinstate the cancelled seven-day/October 1 manual audits. Engineering integration tests use synthetic inputs only on GitHub CI; they must never be presented as production strategy evidence.

## Persistent coordinator primitive

The cloud step adapter now binds a valid quarter-hour slot to a prior verified committed step, atomically creates a slot claim, and verifies the account/state/step/result readbacks. Replays return the existing report with zero market calls. With the approved strategy registry empty, production candidate injection is rejected and the valid no-trade path is exercised in CI. This adapter is not connected to an Actions schedule or R2 credentials; full live-frame completeness, controlled activation and dashboard work remain outstanding.

Before an open paper session advances, the successor feed requests at most 500 recent public trades and requires the returned page to cover the prior lifecycle timestamp. Saturated, gapped, stale, future-dated or invalid tape evidence blocks the slot for review; the older V0.1 feed's 100-record slice is not treated as complete lifecycle history.

## Budget reservation primitive

`src/crypto_autopilot/paper/cloud_budget_v0_1.py` validates account-wide usage evidence timestamps, measured-through freshness, complete reservation coverage, monthly/daily/rolling-31-day operation ceilings, object/run/day byte ceilings and the 8 GB storage hard stop before allowing a provider or R2 reservation. Synthetic tests cover stale, missing, incomplete, negative, over-limit and successful reservations.

This is only a policy primitive. It does not collect Cloudflare analytics, create an atomic account-wide reservation ledger, wrap the Pionex/R2 clients, or prove that unrelated account writers are included. The production path has not wired it before every access. Shared-account usage evidence remains missing; no deployment, controlled main acceptance, provider/R2 operation, or natural schedule is authorized by this code change.

## Delivery status (2026-09-28)

The contract, bounded Pionex market adapter and persistent slot coordinator are merged. GitHub CI covers both the production-safe empty-registry `NO_TRADE` path and a separate synthetic full lifecycle (risk admission, paper entry, target exit, account update and next slot). Synthetic fixtures are never registered as production strategies.

The Dashboard projects `NOT_RUN`, `REGIME_UNAVAILABLE`, the empty production strategy registry and the 10,000 USD planned genesis without claiming that an account or position exists. The strategy registry remains empty and model quality remains `REJECT`.

Activation remains blocked: the fresh shared-account R2 usage evidence is missing, the reservation primitive is not wired or backed by a complete account-wide ledger, and the controlled main acceptance has not run. No provider/R2 operation or natural schedule has been started for this loop.
