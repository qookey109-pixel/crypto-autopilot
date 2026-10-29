# Cloud Paper bounded journal — implementation decision map (planning only)

Evidence basis: main parent `c4bb61941044d1f925b2b772a612b6c0303ced88`. Resolve live main before acting. This document grants no authority or external access.

## Problem

The existing successor calls `latest_committed_slot` to list four entire object kinds on each non-replay slot. Each listing has a finite page and per-run request ceiling. The bounded recovery successor scans at most four keys per kind and repairs only coordinator result seals. A missing cloud-result pointer, orphan evidence, old settlement, concurrent changes or larger inventory cannot safely be assumed recovered. Strict list parsing (#843/#845) prevents some ambiguous evidence from passing, but is not a stable snapshot or complete namespace proof.

## Destination

Replace recurring whole-history scans with a bounded, independently verified, append-only Cloud Paper journal and a single conditional head. Preserve exact prior result, account state and tick/step/seal readback. Do not delete history or rely on a caller-provided list of object IDs as evidence that no orphan exists.

## Decisions and dependencies

1. **Exclusive writer boundary.** Specify and enforce a finite, account/bucket/prefix-bound single-writer contract covering every process, including recovery, operator/manual paths and retained credentials. Without this proof or on a concurrent actor, block; a GitHub concurrency group alone does not establish account-wide exclusivity.
2. **Journal and commit protocol.** Define a versioned, bounded manifest per slot binding the canonical slot, predecessor digest, state, step, tick, seal, report and already observed pre-commit evidence. Post-manifest, head and settlement attempts require a separate bounded accounting/recovery record; failed or unknown operations retain the full reservation. Read back each immutable object and verify all references before conditionally advancing a single head. The head's conditional-write identity and immutable claim must prevent two successors of one predecessor. A HEAD update is never an authorization to trade.
3. **Crash states.** Enumerate interruption after every admission, claim, object write/readback and head update, including lost successful responses. A pending or ambiguous slot retains the full prepaid reservation and blocks new state changes. A fresh separately admitted recovery workload may inspect bounded evidence, but does not infer a write failed from a timeout, refund budgets, or invent a report. Prior D1 settlement recovery and cloud-result pointer repair need explicit successor contracts.
4. **Bounded discovery and orphan coverage.** The design must prove every authorized side effect is registered before it can occur, including crash-created objects. It must detect unknown/unregistered writes or block when that cannot be proved. An append-only linked journal by itself is insufficient to prove absence of a fork or orphan. Establish bounded recovery lookup without silently filtering unexpected keys.
5. **Existing history.** Establish a deterministic, independently reviewed migration/anchor over existing Cloud Paper evidence. No writes, deletions, legacy mutation or activation follow from this planning document. If history or exclusive ownership cannot be proven, preserve evidence and remain blocked. Genesis is valid only with separately proven clean namespace and authority.
6. **Cost and growth.** Account for every D1 read/write/row/storage operation, claim controller debit, R2 GET/LIST/PUT, bytes and retries, including failed attempts and recovery. Specify per-slot, daily, rolling and worst-case limits from fresh complete account evidence; show checkpoint/index growth and audit costs. Do not equate hypothetical free-tier ceilings with zero-fee proof.
7. **Production integration.** Integrate a default-disabled successor with actual prepaid runtime, lifecycle, NO_TRADE, guarded active position and Dashboard projection. Finish all-writer admission, actual D1 calibration, provisioning and finite versioned execution authority before controlled main acceptance or natural scheduling.

## Verification gates

GitHub-hosted deterministic tests must cover genesis and multiple resumed slots, open and empty positions, replay without duplicate writes, fork and conflicting identity, unregistered writer, modified/missing pointer or object, every crash boundary, concurrent claims, lost write and readback responses, expired or exhausted budget, bounded history growth, and retention of failed-attempt reservations. Run Python 3.12/3.13, Ruff, governance and existing regressions. Demonstrate actual integration, not only an isolated fake journal.

Real D1/R2 semantics, complete current account usage/cost and writer coverage require separately versioned authority and evidence. Synthetic SQLite and S3 tests are not production proof. Production acceptance records exact main SHA, run, attempt, slot, report and readbacks; natural schedule evidence is separate.

## Frontier

- Resolve the durable atomic ownership/claim mechanism and account-bound writer inventory.
- Design and test the journal transition and crash model against the existing runtime and recovery paths.
- Design a bounded migration and accounting envelope only after the first two decisions.

Holdout, source switch, promotion and real-money/live trading remain closed. CLOUD_ONLY / FREE-ONLY / PAPER-LIVE-PAPER ONLY.
