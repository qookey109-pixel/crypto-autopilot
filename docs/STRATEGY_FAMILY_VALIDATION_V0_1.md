# Strategy Family Validation V0.1

Status date: 2026-09-18

Status: **PREPARED RESEARCH-ONLY / NO PROVIDER OR HOLDOUT AUTHORITY**

## Purpose

Strategy Family Validation V0.1 is the generalization layer between:

```text
Strategy Edge Validation V0.1
        ↓
family-level cross-asset / cross-regime evidence
        ↓
human family review
        ↓
future cost / portfolio / risk review
```

It deliberately reuses the existing Strategy Edge Validation statistical core.
It does not implement a second PBO, Deflated Sharpe, bootstrap, permutation or
disjoint-validation engine.

## Child evidence

Each family receipt binds one existing
`qookey-strategy-edge-validation-report-v0.1` to:

- one registered strategy family;
- one symbol;
- one regime state;
- one research direction;
- one provider provenance.

The exact child Edge report is canonically SHA-256 hashed and its
`input_fingerprint` is retained for lineage.

The child report must preserve:

- research-only authority;
- no replacement-holdout access;
- promotion authority = 0;
- no trade-plan authority;
- no real-money order authority;
- no live-trading authority.

Malformed or non-boolean authority fields fail closed.

## Frozen V0.1 generalization coverage

The initial family-level research gate requires:

- at least **6** distinct evidence receipts;
- at least **3** distinct assets;
- at least **2** distinct regime states;
- one provider provenance within one family review;
- every included Strategy Edge report must be PASS.

These are preregistered coverage rules, not profitability thresholds and not a
claim that three assets are enough for production deployment.

Provider mixing is rejected rather than silently merging evidence with different
provenance semantics.

## Outcomes

### REJECT

Used when:

- any child Strategy Edge report is REJECT; or
- provider provenance is mixed.

### INSUFFICIENT_GENERALIZATION_COVERAGE

Used when the available PASS evidence does not yet satisfy the frozen receipt,
asset or regime coverage requirements.

### FAMILY_EVIDENCE_READY_FOR_HUMAN_REVIEW

Used only when all frozen V0.1 family-generalization gates pass.

This state is intentionally **not** named PASS. It does not promote the family
registry entry and does not authorize execution.

## Multi-family summary

`validate_strategy_library_evidence()` can aggregate multiple family reports
into one library-level research view.

It explicitly records:

- `ranking_performed=false`
- `winner_selected=false`

The framework does not rank TREND_FOLLOWING against MOMENTUM, or select one
family as the universal winner.

## CLI

The CLI performs no network, provider, R2 or broker operation:

```bash
PYTHONPATH=src python scripts/validate_strategy_family.py \
  --input /tmp/trend-family-edge-receipts.json
```

Input shape:

```json
{
  "schema": "qookey-strategy-family-validation-input-v0.1",
  "family": "TREND_FOLLOWING",
  "receipts": [
    {
      "symbol": "BTC_USDT_PERP",
      "regime_state": "MIXED",
      "direction": "LONG",
      "edge_report": {
        "schema": "qookey-strategy-edge-validation-report-v0.1"
      }
    }
  ]
}
```

The abbreviated edge report above is illustrative only; real input must contain
the complete existing Strategy Edge Validation report and its zero-authority
fields.

Exit status is 0 only for `FAMILY_EVIDENCE_READY_FOR_HUMAN_REVIEW`; all other
states return status 2.

## Relationship to the strategy library

The family name must already exist in Multi-Strategy Library V0.1.

Current registered families are:

- TREND_FOLLOWING
- BREAKOUT
- MOMENTUM
- MEAN_REVERSION
- HIGH_VOLATILITY_TREND
- LOW_VOLATILITY_RANGE

Asset-specific modules such as ZEC V0.3 cannot use this layer to bypass
generalization. They must first map to a declared reusable family and supply
multi-asset evidence under the same frozen contract.

## What this stage does not do

This layer does not:

- fetch market data;
- read or write R2;
- open the replacement holdout;
- materialize candidate returns;
- mutate the strategy registry;
- change Router compatibility;
- choose a portfolio strategy;
- size positions;
- create paper orders;
- create live orders.

Cost, capacity, portfolio interaction, risk sizing and execution remain separate
downstream concerns.

## Authority

Strategy Family Validation V0.1 grants no provider access, R2 access, holdout
access, source switch, strategy promotion, model promotion, position sizing,
paper execution, formal trade plan, real-money order or live-trading authority.
