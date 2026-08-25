# Integrated Paper Strategy Challenger V0.2

## Status

`PREPARED_LOCAL_REPLAY_ONLY`. This is an isolated research integration. It
does not replace `SState Intraday Wave V0.1`, change the formal LONG-only
strategy, authorize a provider request, read or write R2, open the replacement
holdout, schedule a job, promote a model, create a formal trade plan or place
an order.

## Integrated evidence flow

```text
closed provider-separated candles
  -> technical / advanced technical features
  -> SState adapter
       LONG: governed V0.1 decision is required
       SHORT: context-only research gate; no formal short score exists
  -> directional technical candidate
  -> crypto or tokenized-equity asset adapter
  -> structural stop adapter
  -> one-position Repository paper replay
  -> partial / runner / hard-time exit evidence
  -> chronological challenger promotion evidence gate
```

The SState and technical scores are deliberately not added together. SState
remains a market/admission decision and the technical score remains an entry
candidate score. This removes the prior ambiguity between the formal 80-point
minimum and the technical 65-point minimum without inventing a composite
weight.

## Direction bridge

- LONG requires the unmodified `strategy.evaluate_opportunity` V0.1 decision
  and an eligible directional technical candidate.
- SHORT is still a challenger. It applies only the allowed SState state,
  availability, minimum-sample and minimum-probability context gates. The
  long-specific setup/entry score is not mirrored or mislabeled as a formal
  short score.
- LONG and SHORT retain side-specific EMA, directional-index, VWAP, RSI, MACD
  and Donchian semantics from Paper LONG/SHORT Challenger V0.2.

## Asset adapters

Crypto candidates require Pionex public-futures provenance, `TRADING` status,
all required closed-candle intervals and the configured spread gate.

Tokenized-equity candidates reuse the same technical strategy only after the
existing tokenized adapter verifies:

- explicit `tokenized_stock_candidate` classification;
- Pionex public-futures provenance and `TRADING` status;
- 15m, 1h, 4h, 8h and 1d coverage;
- session-model evidence;
- corporate-action policy evidence; and
- spread no greater than 40 bps.

A heuristic tokenized label is never proof of tradability or historical
availability. Tokenized results remain isolated from the crypto portfolio.

## Risk and structural stop

The reference paper risk budget is at most 1% of current paper equity. Position
notional is derived from the actual stop distance. If the required leverage is
above 3x, the plan is rejected; the engine does not silently reduce the
position or widen the risk budget. The output records evaluated leverage,
leverage-cap rejections and accepted effective-risk fractions.

The structural stop adapter compares the directional ATR stop, EMA20 and
Bollinger midline when each is valid for the side. It selects the widest valid
invalidation and bounds its distance to 0.75–2.5 ATR. No fixed-percentage stop
is authorized.

Portfolio scope remains conservative:

- one open paper position at a time;
- at most three new positions per UTC day;
- new entries stop after realized daily PnL reaches -3R; and
- no martingale, averaging down or leverage-cap bypass.

## Partial, runner and time exit

V0.2 makes the previously descriptive exit contract executable in the
challenger:

- at +1R, realize 30%;
- retain 70% as the runner;
- move the runner stop to a fee/slippage-adjusted breakeven level;
- trail by one initial-risk distance, updated only for the next candle;
- retain the directional fixed target as an additional runner exit; and
- hard-exit at the first candle open at or after 12 hours.

OHLC same-bar ambiguity remains adverse-path conservative: a stop wins when a
stop and favorable level are both touched. Signals still fill no earlier than
the next candle open.

## Research context

Timestamped KOL or sentiment context can be attached as `UNAVAILABLE`,
`NEUTRAL`, `ALIGNED` or `CONTRADICTORY`. It is evidence only and cannot change
candidate eligibility or bypass a deterministic gate.

## Promotion

`config/challenger_promotion_protocol_v0_1.json` freezes the quantitative
evidence contract before real challenger results are read. Even a complete
PASS is labeled `EVIDENCE_READY_FOR_HUMAN_REVIEW`; it never promotes a model or
changes trading authority.

## Files

- `config/integrated_paper_strategy_v0_2.json`
- `src/crypto_autopilot/integrated_paper_strategy_v0_2.py`
- `tests/test_integrated_paper_strategy_v0_2.py`
- `config/challenger_promotion_protocol_v0_1.json`
- `src/crypto_autopilot/challenger_promotion_v0_1.py`
- `docs/CHALLENGER_PROMOTION_PROTOCOL_V0_1.md`

