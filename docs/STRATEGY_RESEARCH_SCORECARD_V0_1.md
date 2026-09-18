# Strategy Research Scorecard / Ranking V0.1

Status date: 2026-09-19

Status: **PREPARED RESEARCH-RANKING-ONLY / NO STRATEGY SELECTION AUTHORITY**

## Purpose

Strategy Research Scorecard V0.1 adds a deterministic ranking layer on top of
existing `Strategy Family Validation V0.1` reports.

It answers:

> Which strategy-family evidence set should researchers inspect or strengthen
> first?

It does **not** answer:

> Which strategy should be traded?

The ranking is therefore a research workflow ordering, not a trading
recommendation, portfolio allocation or execution selector.

## Inputs

Every input must be a complete
`qookey-strategy-family-validation-report-v0.1`.

The Scorecard rechecks:

- registered family id;
- allowed family-validation state;
- receipt/asset/regime/direction coverage;
- provider count;
- failed child Edge report count;
- lineage counts and SHA-256 shape;
- research-only authority;
- no holdout, promotion, sizing, paper execution or live execution authority.

A malformed or authority-escalated family report fails closed.

## Score dimensions

V0.1 uses fixed frozen weights:

- receipt coverage: **20%**
- distinct asset breadth: **25%**
- distinct regime breadth: **20%**
- supported direction breadth: **10%**
- child Edge consistency: **25%**

Coverage dimensions saturate at 2× the family validation minimum, so additional
evidence can differentiate two review-ready families without treating raw sample
count as unlimited proof.

State multipliers:

- `FAMILY_EVIDENCE_READY_FOR_HUMAN_REVIEW` → 1.00
- `INSUFFICIENT_GENERALIZATION_COVERAGE` → 0.65
- `REJECT` → unranked / score 0

The score is named `research_score` intentionally. It is not an expected
return, win probability, Sharpe estimate or profitability forecast.

## Ranking semantics

V0.1 produces:

- `research_priority_order`
- one `research_rank` for each non-rejected family
- deterministic family-name ascending tie break

A rank of 1 means:

> first evidence set to inspect in the research workflow

It does not mean:

- strategy winner;
- best strategy;
- execution selection;
- Paper Cycle input;
- Live Paper selection;
- real-money recommendation.

Binding fields remain:

```text
ranking_performed = true
winner_selected = false
execution_selection_performed = false
```

## Deterministic id and tamper resistance

The Scorecard id binds:

- all family validation report SHA-256 values;
- complete versioned Scorecard policy;
- research priority order;
- SHA-256 of the complete scored rows.

Changing a score, rank, dimension or family lineage therefore invalidates
verification.

## CLI

Input:

```json
{
  "schema": "qookey-strategy-research-scorecard-input-v0.1",
  "family_reports": []
}
```

Run:

```bash
PYTHONPATH=src python scripts/build_strategy_research_scorecard_v0_1.py \
  --input /tmp/strategy-family-reports.json
```

The CLI performs no provider, R2, broker or exchange operation.

## Relationship to Router and Paper execution

The intended architecture is:

```text
Strategy Family Validation
        ↓
Research Scorecard / Ranking
        ↓
human/research prioritization only

separate execution path:
Daily Opportunity → Router → Portfolio/Risk → Paper execution
```

V0.1 deliberately does not connect the Scorecard output to Portfolio Admission
or Paper Cycle candidate inputs.

A future version would need separate reviewed authority before research rank
could influence automated paper strategy selection.

## Authority

Authorized:

- deterministic research ranking of already-governed family evidence.

Not authorized:

- winner selection;
- automatic strategy selection;
- registry mutation;
- position sizing;
- paper execution;
- private exchange API;
- replacement holdout;
- real-money orders;
- real live trading.
