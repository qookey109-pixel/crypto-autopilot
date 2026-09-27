# Cloud Paper Loop delivery V0.1

CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER. Target: full public-market → opportunity → qualified strategy → risk → paper execution → persistent state → dashboard cycle.

## Completed contract
PR #536 merged the inactive bounded contract and empty production registry. Runtime activation remains disabled. The contract proposes at most 18 provider requests per run (3 universe, 5 hourly candle requests, 10 execution-frame requests), 96 slots/day, and per-operation budget checks. These are ceilings, not permission to spend without current shared-account headroom.

## Public-market adapter
The adapter intersects the curated crypto-only pool in `config/crypto_universe_v0_1.json` with live Pionex symbols and current valid quotes, then applies the existing spread/liquidity rules with a five-market bound. It requests 240 closed hourly bars only, rejects holdout-overlapping request windows before I/O, and rejects missing, duplicate, stale, nonfinite or out-of-window returns. A caller-supplied budget check runs before every request. No source fallback or historical acquisition is added.

Technical features, opportunity scoring and strategy routing reuse the existing implementations. The adapter emits source/time/hash evidence and does not itself submit orders or write R2.

## Discovered integration blockers
1. The existing required macro regime needs canonical TOTAL3, BTC dominance and aligned breadth. Pionex public quotes/candles cannot supply global capitalization. The prior CoinPaprika one-shot authority expired on September 19 and does not authorize a new schedule. Missing context remains REGIME_UNAVAILABLE; no fake neutral snapshot or weakened regime gate is allowed.
2. The production strategy registry is empty and Core100 remains REJECT. A research ranking is not execution eligibility.
3. Existing checkpoint creation assumes a preceding account advance; new cash-only genesis must not fabricate a trade.
4. Shared-account R2 allowance evidence and implementation-bound activation are required before enabling the proposed cron.

These are explicit product dependencies, not reasons to reinstate the cancelled seven-day/October 1 manual audits. Engineering integration tests use synthetic inputs only on GitHub CI; they must never be presented as production strategy evidence.
