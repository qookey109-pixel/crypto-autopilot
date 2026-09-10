# Pionex Bounded Capacity Pilot V0.2

This successor changes the completion contract to a **fixed 27-day capacity
sample**, 2026-08-01 inclusive through 2026-08-28 exclusive, BTC_USDT_PERP only.
Expected complete rows: 15M = 2592, 60M = 648, 4H = 162. It is not complete
listing history, 150-market materialization, backtest admission or training.

## Why the rule changes

Run [34494612014](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34494612014)
on b1acbf4 failed at 15M request 22 with MARKET_INVALID_TIME, after 10,500
returned rows **including bootstrap overlap**. Those are not unique rows.
The [official endpoint reference](https://pionex-doc.gitbook.io/apidocs/restful/markets/get-klines)
documents a 10,000-record retrieval horizon. Evidence supports a horizon
constraint; it does not prove the exact available unique-bar count.

V0.1 also requests backwards across the protected holdout dates and emits a
constant holdout_accessed=false. That assertion is not proof of non-access.
Prior raw candles must not be retrieved or evaluated to investigate this.
The original artifacts and V0.1 config/receipt remain unchanged. This is an
incident requiring review, not a retrospective declaration of an unopened
sample. Existing global frozen-holdout markers are historical claims pending
review; do not use them as evidence that the pilot avoided those dates.

## Effective only after reviewed main merge

The new config and SHA-bound authority receipt authorize this limited sample.
The existing manual workflow filename/concurrency group is retained; its
command switches atomically to V0.2 and V0.1's CLI is retired. No new cron,
automatic retry, paid service or provider is added. Git fetch and isolated
engineering changes are permitted for this delivery under the user's renewed
permission; that does not widen production access.

Every request specifies an end timestamp before holdout, a limit confined to
the sample, and a decreasing cursor. No latest-page bootstrap occurs.
Check wall-clock expiry and a conservative 9,000-bar lookback before each
request. Maximum ten requests total. Gaps, duplicates, endpoint omissions,
out-of-range responses and errors all fail; an error never becomes EOF.
An out-of-range response reports non-access as unverified, not false.

Raw data remains runner-ephemeral until complete range validation. R2 uses
the independent V0.2 namespace. Whole-bucket 8 GB headroom is checked before
provider access and each write. Parquet roundtrip, exact SHA readback,
receipt-bound object hashes and pointer-last publication remain required.
A valid prior PASS pointer stops provider requests. Partial target conflicts
need review. Failed writes report attempted/confirmed writes truthfully.

PAPER-ONLY, FREE-ONLY, source separation and the frozen metadata authorities
are unchanged. This proposal grants no holdout, live trading, strategy,
training, automatic scheduling or 150+ market authority. Dispatch only after
protected-main merge and review of cloud CI. Next expansion must bind this
pilot's real output sizes and continuity evidence.
