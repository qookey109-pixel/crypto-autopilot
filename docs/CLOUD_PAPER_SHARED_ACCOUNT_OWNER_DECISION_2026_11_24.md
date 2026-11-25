# Cloud Paper shared-account owner decision — 2026-11-24

## Decision

The project owner chose to continue using the existing shared Cloudflare account for Crypto Autopilot. This records the owner's choice in the current conversation; it does not establish a new execution authority.

The owner previously said they are unsure whether other programs or people use the existing broad R2 credentials and instructed us not to disable them. Preserve those credentials. Do not add a payment method, open another account, change credentials, or create resources on the basis of this decision.

## Consequences for delivery

- Account-wide writer coverage and usage/headroom remain unverified. A selected account is not proof of exclusive control, complete writer inventory, free-tier capacity, billing status, or a zero-cost guarantee.
- Existing and future writers can share the account. Identify and govern applicable write paths before claiming a complete shared budget gate. Do not assume the two broad credentials are unused outside this project.
- Keep production admission, R2/D1 access, provisioning and scheduling subject to the current versioned repository authorities and their evidence requirements. This record does not grant permission to run a consumed one-shot operation.
- Maintain 0 USD, PAPER/LIVE-PAPER only, closed real trading, holdout, source switch and automatic promotion. Preserve frozen evidence.

## Observed maintenance evidence

On the observed main commit `33cad8acdb69cd736189eb5eef4b20e144d863a8`, two distinct naturally scheduled Health runs triggered maintenance:

- [Health 45205197146](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/45205197146) failed; its [maintenance run 45205332582](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/45205332582) succeeded in inspect and propose, reporting `DRAFT_UPDATED` and one commit in [draft #934](https://github.com/qookey109-pixel/crypto-autopilot/pull/934).
- [Health 45316850678](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/45316850678) failed; its [maintenance run 45316953499](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/45316953499) succeeded in inspect and propose, reporting `NO_CHANGE` and `commits_created=0`.

These are maintenance-chain observations only. They do not indicate that Health passed, that the draft passed CI, or that Cloud Paper is running. The later Health failure reported the Binance USD-M Crypto Core 100 training failure; retain the existing REJECT and runtime-drift evidence without rerunning the consumed bootstrap.

## Next work

Reconcile the current writer inventory and legacy direct-write paths with a protected, durable shared-admission design. Establish trustworthy account-wide usage and headroom, including the admission mechanism's own costs, before an authorized production write or schedule can be enabled. A new bounded versioned scope and successful cloud validation are needed for any gated external operation.
