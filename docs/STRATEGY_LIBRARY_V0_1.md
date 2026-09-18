# Multi-Strategy Library V0.1

Status date: 2026-09-18

## Purpose

The Multi-Strategy Library is the governed registry behind Strategy Router V0.1.

It exists so the platform has one explicit inventory of reusable strategy families rather than scattering family names across router code, documentation and future portfolio logic.

V0.1 is still research-only. A registry entry means:

> this family exists as a reusable product module and has a prepared routing rule

It does **not** mean:

> this family has validated edge or may place an order

## Registered families

| Family | Category | Attention profile | Structure required |
| --- | --- | --- | --- |
| TREND_FOLLOWING | DIRECTIONAL | DIRECTIONAL | yes |
| BREAKOUT | STRUCTURE | DIRECTIONAL | yes |
| MOMENTUM | DIRECTIONAL | DIRECTIONAL | no |
| MEAN_REVERSION | RANGE | RANGE_EXTREMITY | yes |
| HIGH_VOLATILITY_TREND | VOLATILITY_DIRECTIONAL | DIRECTIONAL | yes |
| LOW_VOLATILITY_RANGE | VOLATILITY_RANGE | RANGE_EXTREMITY | yes |

Every V0.1 family supports research LONG and SHORT directions. That registry metadata does not itself authorize SHORT execution.

## Lifecycle

Each V0.1 entry currently has:

- validation state: ROUTING_RULE_PREPARED
- reusable scope: MULTI_ASSET_RESEARCH
- generalization required: true
- strategy edge claimed: false
- position sizing authorized: false
- paper execution authorized: false
- live execution authorized: false

The next maturity path for one family should be explicit:

1. routing rule prepared
2. non-holdout multi-asset research dataset defined
3. family-specific evidence produced
4. out-of-sample/generalization validation
5. cost/risk robustness review
6. paper eligibility decision
7. only under later authority, execution integration

No step may be skipped because one coin performed well.

## Router relationship

Strategy Router imports the canonical family identifiers from
`src/crypto_autopilot/strategy_library.py`.

The Router may return zero, one or multiple registered families.

A runtime guard rejects any route family that is not in the registry. This prevents a new hard-coded strategy name from silently bypassing library governance.

## Machine-readable contract

`config/strategy_library_v0_1.json` mirrors the code registry.

CI verifies the family records match exactly for:

- family name
- category
- attention profiles
- directions
- structure requirement
- validation state
- reusable scope
- generalization requirement

A code-only or config-only family addition therefore fails CI.

## Single-asset boundary

Asset-specific research such as ZEC Strategy V0.3 remains outside the reusable library until a separate generalization review explicitly supports a declared multi-asset scope.

A single-asset module may provide:

- hypotheses
- indicator combinations
- risk observations
- regime-specific findings
- failure cases

but it may not silently become the system-wide family implementation.

## What comes next

The next engineering stage after this registry is family-specific research/validation modules.

That stage should attach evidence to the family registry without changing the Daily Opportunity Engine or Router into execution systems.

Risk / Position Sizing remains downstream and separate.

## Authority

Multi-Strategy Library V0.1 authorizes no:

- provider access
- R2 access
- replacement holdout access
- source switch
- strategy promotion
- model promotion
- position sizing
- paper order
- formal trade plan
- real-money order
- live trading
