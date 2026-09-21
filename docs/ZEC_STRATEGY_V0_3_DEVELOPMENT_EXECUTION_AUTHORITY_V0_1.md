# ZEC Strategy V0.3 — One-Shot Development Execution Authority V0.1

Status date: 2026-09-21

## Purpose

This package prepares exactly one real ZEC V0.3 **development-only** execution.

It does not execute on PR creation or merge. The authority becomes effective only
when the exact authority PR is explicitly merged to protected `main`, and the
actual study still requires a separate manual `workflow_dispatch`.

The frozen development contract itself remains unchanged and continues to state:

`offline_development_runner_authorized = false`

Execution is opened only through the separate versioned authority receipt:

`research/receipts/2026-09-21-zec-v0-3-development-one-shot-authority.json`

## Why Binance Vision is used

The governed Core100 catalog does not contain ZECUSDT. A prior R2-backed attempt
therefore failed closed before reading any ZEC history.

A separate read-only execution on 2026-09-18 already verified the exact public
Binance Vision source required by V0.3:

- provider: Binance USD-M
- delivery: public Binance Vision monthly archives
- symbol: ZECUSDT
- interval: 15m
- period: 2022-08 through 2026-07
- 48 archives
- 140,256 rows
- no R2 access
- no raw-candle persistence

That period has already been viewed, so V0.3 treats it strictly as development
evidence. It cannot be used as fresh confirmation.

## Exact execution

The one-shot workflow may read only those 48 completed monthly archives and
their 48 checksum files: at most 96 public provider requests.

The data stays in disposable GitHub-hosted runner memory. The workflow does not
write the raw candles to Repository, R2, Pages or the uploaded artifact.

The development engine evaluates the complete frozen matrix:

- 64 candidates
- 4 chronological folds
- 256 candidate/fold cells
- 5 bps per-side development slippage
- 6 bps taker fee per side
- funding is `UNAVAILABLE_NOT_FABRICATED` unless explicit point-in-time funding
  is separately supplied; this authority does not supply it

The aggregate artifact contains per-cell metrics, deterministic ranking and the
frozen selection-policy result. It deliberately omits raw candles and individual
trade lists.

## Merge-gated authority

Before the first Binance request, the runner verifies:

1. event is `workflow_dispatch`;
2. ref is protected `main`;
3. repository is exactly `qookey109-pixel/crypto-autopilot`;
4. run attempt is exactly 1;
5. the authority ID exactly matches the receipt;
6. the authority PR is merged into `main`;
7. current `main` descends from that merge commit;
8. no prior workflow run exists for the same authority ID;
9. every reviewed contract, policy, runner, script, workflow and prior-source
   evidence file still has the exact Git blob SHA bound in the authority receipt.

Any mismatch fails before provider data is read.

A failed or cancelled first dispatch consumes the one-shot authority. Re-running
the same workflow attempt or dispatching a second run requires a new versioned
authority.

## Fresh-confirmation boundary

The interval below remains unopened:

`2026-08-01T00:00:00Z <= t < 2026-09-16T00:00:00Z`

This authority does not permit monthly or daily reads that overlap it.

Selection is completed using development evidence only. A future confirmation
read requires a separate explicit authority after the development champion (if
any) is frozen.

## Explicit non-authority

This package authorizes no:

- R2 reads or writes;
- raw candle persistence;
- raw trade artifact;
- fresh-confirmation read;
- formal holdout access;
- source switch;
- model or strategy promotion;
- formal trade plan;
- real-money order;
- live trading.

A successful workflow means the 256-cell development execution completed. It
does not mean the strategy passed. The selection result may still be
`NO_ELIGIBLE_DEVELOPMENT_CANDIDATE` or
`ISOLATED_DEVELOPMENT_PEAK_REJECTED`.
