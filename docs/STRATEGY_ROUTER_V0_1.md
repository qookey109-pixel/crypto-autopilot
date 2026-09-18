# Strategy Router V0.1

Status date: 2026-09-18

## Role

Strategy Router is the second product-stage selector in Qookey Crypto Autopilot.

It answers:

> Given this already-selected asset and the causally available market state, which research strategy families are technically compatible right now?

It does **not** answer:

> Which order should be sent?

The router is deterministic, research-only and no-I/O. It consumes a selected Daily Opportunity candidate plus already-computed technical, market-structure and cross-market regime evidence.

## Why this layer exists

The platform is deliberately:

**multi-asset + multi-strategy + dynamic pairing**

rather than:

**one strategy for every market**

The Router allows one candidate to match zero strategies (NO_TRADE), one strategy family, or multiple strategy families at the same time.

Multiple matches are preserved. A later portfolio/risk layer decides whether to keep one, allocate across more than one, reduce exposure, or reject all of them.

## V0.1 strategy-family registry

The first research registry contains:

- TREND_FOLLOWING
- BREAKOUT
- MOMENTUM
- MEAN_REVERSION
- HIGH_VOLATILITY_TREND
- LOW_VOLATILITY_RANGE

These are **research compatibility families**, not profitability claims and not execution authority.

Future families may add microstructure, funding-rate, cross-market, basis, order-book or execution-aware logic under separate versioned research.

## Inputs

For one candidate:

- DailyOpportunityDecision
- TechnicalSnapshot
- MarketRegimeSnapshot
- optional MarketStructureSnapshot
- explicit as_of_ms

Structure is optional globally because momentum can be evaluated without it, but trend, breakout and range families fail closed when the structure evidence they need is unavailable.

All evidence must be available by as_of_ms. Future technical or regime data causes NO_TRADE. Future/unready structure is ignored rather than leaked backward into strategy matching.

## Directional families

### Trend following

Requires:

- Daily Opportunity profile = DIRECTIONAL
- LONG or SHORT descriptive bias
- aligned EMA20 / EMA50 / EMA200 stack
- absolute EMA20 slope/ATR >= 0.15 in the matching direction
- MACD histogram in the matching direction
- per-asset market structure = UP for LONG or DOWN for SHORT
- no conservative macro conflict

### Momentum

Requires:

- Daily Opportunity profile = DIRECTIONAL
- directional EMA20 slope
- directional MACD histogram
- RSI >= 60 for LONG or <= 40 for SHORT
- volume ratio >= 1.10
- no conservative macro conflict

### Breakout

Requires:

- causally available ready market structure
- closed-bar breakout above the previous range for LONG or breakdown below it for SHORT
- volume ratio >= 1.0
- descriptive directional bias aligned with the break
- no conservative macro conflict

### High-volatility trend

Requires:

- Daily Opportunity profile = DIRECTIONAL
- ATR14 / close >= 3%
- directional EMA20 slope
- directional MACD histogram
- volume participation
- UP / DOWN asset structure aligned with direction
- no conservative macro conflict

## Range families

### Mean reversion

Requires:

- Daily Opportunity profile = RANGE_EXTREMITY
- per-asset market structure = RANGE
- oversold pair: RSI <= 35 and Bollinger position <= 0.20 -> research LONG route
- or overbought pair: RSI >= 65 and Bollinger position >= 0.80 -> research SHORT route
- no conservative macro conflict

This is intentionally independent from the upstream descriptive bias. For example, an oversold range can have a descriptive bearish bias while the compatible mean-reversion direction is LONG.

### Low-volatility range

Adds ATR14 / close <= 1.5% to the same range/extremity logic.

Therefore one range candidate may simultaneously match MEAN_REVERSION + LOW_VOLATILITY_RANGE.

## Cross-market regime handling

The current cross-market regime states are ALT_EXPANSION, BTC_CONCENTRATION, BROAD_RISK_OFF, and MIXED.

V0.1 uses only a conservative directional-conflict rule:

- LONG routes are blocked in BROAD_RISK_OFF
- SHORT routes are blocked in ALT_EXPANSION

BTC_CONCENTRATION and MIXED are not treated as universal direction signals for every asset.

These rules are preregistered engineering defaults for research routing. They are not evidence that a strategy has edge in a regime.

## Examples

Illustrative only:

~~~text
SOL + upside breakout + volume + compatible macro
    -> BREAKOUT
    -> MOMENTUM
    -> possibly TREND_FOLLOWING

ZEC + high-volatility directional trend
    -> TREND_FOLLOWING
    -> MOMENTUM
    -> HIGH_VOLATILITY_TREND

BTC + range + oversold extreme
    -> MEAN_REVERSION
    -> possibly LOW_VOLATILITY_RANGE

ETH + no compatible family
    -> NO_TRADE
~~~

The examples are architecture illustrations, not current trade recommendations.

## Single-asset strategy boundary

An asset-specific strategy experiment such as ZEC Strategy V0.3 remains a module/evidence source.

It does not become a reusable Router family merely because it worked on one asset.

Before platform-wide registration it requires a separate multi-asset/generalization validation path with declared scope and evidence.

## Anti-leakage and fail-closed behavior

- future technical evidence -> NO_TRADE
- future regime evidence -> NO_TRADE
- future/unready structure cannot create a structure-based route
- ineligible Daily Opportunity candidate -> NO_TRADE
- no compatible family -> NO_TRADE
- no provider fallback or hidden data fetch
- no holdout lookup

## Downstream boundary

A match means:

> this strategy family is technically compatible under the V0.1 research rules

It does **not** mean validated statistical edge, strategy promotion, position size, target leverage, order plan, paper order, or live order.

The intended downstream flow remains:

~~~text
Daily Opportunity Engine
        ↓
Strategy Router
        ↓
zero or more research-compatible strategy families
        ↓
strategy validation / portfolio selection
        ↓
Risk & Position Sizing
        ↓
Paper Execution
~~~

## Authority

Strategy Router V0.1 authorizes no provider access, R2 access, holdout access, source switch, strategy promotion, model promotion, SHORT execution, formal trade plan, real-money order, or live trading.
