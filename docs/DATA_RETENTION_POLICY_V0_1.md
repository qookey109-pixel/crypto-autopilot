# Data Retention Policy V0.1

Status: **PARTIALLY ACTIVE / DETAILED V0.1 AUTHORIZED AFTER V0.10 WINDOW**.

This policy records the requested storage split. The executable Binance Spot
V0.5 authority remains the current authority for its daily dataset. The
separate Binance USD-M Detailed History V0.1 authority now authorizes a fixed
48-month, 250-market backfill beginning only after the V0.10 window; this policy
alone still does not authorize another provider read, R2 write, deletion,
compaction, model run or trading action.

## Retention split

| Data family | Scope | Retention |
| --- | --- | --- |
| Binance Spot training candles | `1d`, provider-separated Spot | `2020-01-01` through latest complete UTC day |
| Detailed candles | `15m`, `1h`, `4h`, provider-separated Binance USD-M research namespace | fixed 2022-08 through 2026-07 under Detailed History V0.1; future rolling compaction needs another authority |
| Derivative state | funding, mark-index basis, open interest | rolling four years |
| Derived indicators | ADX, VWAP, Bollinger, Donchian, ATR and related features | recompute from canonical inputs; no permanent duplicate copy |

The detailed four-year window is calculated at execution time as four years
before the latest complete UTC day. A market may start later than the window;
the system must preserve its actual listing/onset timestamp and must not pad
history.

## Boundaries

- Pionex-native perp evidence, Binance USD-M proxy evidence and Binance Spot
  evidence remain separate. Provider splicing and Pionex-native relabeling are
  forbidden.
- Existing frozen evidence is historical and immutable. This policy does not
  delete or rewrite it.
- Raw/detailed history remains R2-only and is not projected to GitHub Pages.
- Detailed History V0.1 supplies the first versioned execution authority for
  its exact 250-market / 48-month scope. Any rolling update, deletion,
  compaction, different provider or wider dataset still needs another authority.
- No part of this policy authorizes model promotion, formal backtest admission,
  automatic trade plans, real-money orders or live trading.

The prepared capacity estimate is in
`research/estimates/2026-08-23-four-year-detailed-data-retention.json`.
Using the existing eight-year sizing basis, four years of detailed native
intervals are approximately 1.48 GB canonical, 2.96 GB including retained
staging, and 4.43 GB at the three-times stress factor. These are planning
figures, not proof of provider availability or an authorization to backfill.
