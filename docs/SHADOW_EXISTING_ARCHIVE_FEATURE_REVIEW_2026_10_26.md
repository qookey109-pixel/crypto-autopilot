# Existing Shadow archive feature review — 2026-10-26

CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER / 0 USD / PAPER-LIVE-PAPER ONLY.

This is an empirical inspection of **one existing capture**, performed after the
pure checker merged in #814. It adds no collection, context observation, strategy
qualification or runtime authority.

## Evidence

GitHub-hosted [audit run 40334628272](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/40334628272),
job 121612783213, succeeded. Temporary [PR #815](https://github.com/qookey109-pixel/crypto-autopilot/pull/815)
is CLOSED_UNMERGED. The original ZIP was downloaded inside the cloud runner,
hashed and checked against exact run/job/artifact identity by the merged verifier.

- Source natural run: 40162915838, attempt 1, source SHA
  `944895170f80af21e8f9b544ec42b279c45c0d6e`.
- Existing artifact: 12586364157.
- Original ZIP SHA-256:
  `191fa626fbddd7f4a2a639618157605ab382a343936584fa2755ec2f6c08f03d`.
- Capture: 2026-10-25T04:43:38.396000Z.
- Five market snapshots, 240 closed 60M candles each: 1,200 unique
  symbol/candle-start pairs within this report; maximum source lag 43 minutes.
- [Append-only receipt](../research/receipts/2026-10-26-shadow-existing-archive-feature-coverage-v0-1.json)
  retains the exact safe JSON output and the separate outer audit identity.

## Actual feature coverage in this capture

| Field group | Observed across these five markets |
| --- | --- |
| Technical | EMA20, EMA50, ATR14, volume ratio, MACD histogram: 5/5 each |
| Structure | Previous rolling high/low, market structure state: 5/5 each |
| Patterns | Liquidity event, FVG bias, order-block bias, MACD divergence: 5/5 each |
| Event radar | Relative volume: 5/5 |
| Event radar gaps | OI change and liquidation imbalance: keys absent in all five |
| Other timeframes | 15M and 4H not collected in this report |
| Trading costs | Fees, slippage, funding and net return remain UNKNOWN |

Thus 13 of 15 preregistered field names have values with reported source-bar
and capture-time availability lineage in all five market snapshots. The other
two are missing, not zero or neutral. Categorical NONE remains a valid recorded
observation and does not create a positive signal. These counts describe only
this capture; they are not a global feature success rate or continuous history.

The pure checker correctly leaves its own archive/source-authentication flags
false. The surrounding cloud audit independently authenticates original bytes
and exact GitHub identities. Those proof layers are retained separately in the
receipt. Neither layer independently recomputes every indicator from exchange
truth or proves availability at an earlier historical entry cutoff.

## What this changes next

Use the observed 60M technical/structure/pattern fields as the bounded input
scope for subsequent research. Historical decision cutoffs, rolling outcomes,
cross-capture overlap, costs and missing timeframes still require evidence.
OI and liquidation cannot be used as required positive or negative conditions
until a governed source exists. No unavailable source may be filled with zero.

This is the already authenticated later singleton, not a new eighteenth archive,
a seventeenth consecutive observation, 21/21 readiness or PAPER NO_TRADE.

## Preserved failure and boundaries

The independent archive/feature audit job passed. Whole-PR Python CI separately
failed the unchanged writer inventory check: recorded 100 workflows versus 101
with the temporary workflow. No guard was weakened; #815 was closed without
merging the temporary workflow. The receipt does not claim whole-PR CI passed.

No new provider request, R2/D1 access, collection dispatch, training, bootstrap,
Billing/Usage rerun, holdout, source switch, promotion or trading occurred.
Cloud Paper remains NOT_WIRED / NOT_RUN / NOT_CONFIGURED and model quality REJECT.
