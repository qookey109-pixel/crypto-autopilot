# Live Paper Run Coordinator V0.2

Status date: 2026-09-22

Status: **AUTHORIZED ON EXPLICIT PROTECTED-MAIN MERGE / NO SCHEDULE**

Coordinator V0.2 preserves the V0.1 append-only run ledger, deterministic
request replay and explicit candidate inputs. Its only execution-path change is
a required Run Slot Claim V0.1 before a new provider call.

The V0.1 library policy remains supported for historical tests and evidence.
The GitHub manual execution workflow explicitly selects the V0.2 config.

## New gate

For an uncommitted request, V0.2 requires:

`run header/state persistence -> atomic slot claim -> public provider call`.

If a slot is already claimed, execution fails closed before provider access.
There is no automatic retry, expiry or takeover.

A fully committed identical request is replayed before the claim gate and still
performs zero new provider requests.

## Unchanged boundaries

V0.2 does not add:

- a cron schedule;
- candidate generation or strategy ranking;
- a second broker;
- private exchange/account/order access;
- holdout access;
- model promotion;
- real-money order authority;
- real live-trading authority.

See `docs/LIVE_PAPER_RUN_CLAIM_V0_1.md` for slot and crash semantics.
