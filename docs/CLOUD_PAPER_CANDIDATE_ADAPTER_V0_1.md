# Cloud Paper Qualified Candidate Adapter V0.1

## Purpose

This adapter connects a strategy output that already has explicit paper eligibility to the existing Cloud Paper coordinator. It does not create strategy signals, select a strategy, derive entry/stop/target levels, or change risk parameters.

## Input gate

The current registry remains `EMPTY_NO_ELIGIBLE_STRATEGIES`; this produces zero candidates and a normal `NO_TRADE`. A non-empty registry must be the versioned `QUALIFIED_PAPER_STRATEGIES_AVAILABLE` state. Each entry binds the strategy family, Pionex provider, allowed symbols and regimes, implementation SHA-256, and a paper qualification receipt. The receipt must explicitly authorize paper execution and keep holdout, source switch, promotion, real-money orders, and live trading closed. A Core100 dependent strategy requires a model-quality PASS.

Each strategy output must match the current market report's exact `as_of_ms`, Pionex market-evidence hash and router-route hash. The qualification receipt and implementation hashes must match the registry. Entry, stop, target and position sizing must be supplied by the qualified strategy output and be internally consistent. This layer validates those values; it does not calculate or repair them.

## Failure behavior

The adapter rejects an invalid basket as a whole with `REVIEW_REQUIRED`; it never drops bad candidates or ranks a partial set. The Cloud Paper report preserves the review reason and the full shared-budget reservation remains held. Empty registry or no matching qualified output returns `NO_TRADE` with its reason.

## Current status and limits

- Registry remains empty and Core100 quality remains `REJECT`; this PR adds no eligible strategy.
- The production activation flag remains false, no execution workflow or Cloud Paper schedule is enabled, and no runtime provider/R2/D1 access is authorized.
- CI positive-path fixtures exercise only the adapter/orchestration contract; they are not production strategy evidence.
- Actual zero-cost acceptance remains blocked on account-wide usage/freshness evidence, complete writer coverage, D1/R2 capacity calibration and an authorized controlled main run.

Contract: [`config/cloud_paper_candidate_adapter_v0_1.json`](../config/cloud_paper_candidate_adapter_v0_1.json).
