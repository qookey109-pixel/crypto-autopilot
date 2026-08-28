# Research Governance V0.1

This layer adapts the useful governance patterns from the supplied GameAI
reference package without importing its runtime, trainer, game-engine or
deployment stack.

## Scope

The implementation is offline and evidence-only:

```text
provider-separated inputs
        ↓
lineage manifest + SHA-256 fingerprints
        ↓
update / validation / frozen-holdout partition evidence
        ↓
immutable experiment registry
        ↓
bounded resource-aware proposal ordering
        ↓
research receipt
```

It does not fetch providers, construct an R2 client, write R2, open the
replacement holdout, create a trade plan, promote a strategy, deploy a model,
or alter the V0.10 production-critical path.

## Modules

- `src/crypto_autopilot/lineage.py` — canonical JSON, SHA-256 fingerprints,
  secret-like metadata rejection and zero-authority research manifests.
- `src/crypto_autopilot/research/evaluation_integrity.py` — partition metadata,
  overlap/seed checks and a guard that denies frozen-holdout access by default.
- `src/crypto_autopilot/research/experiment_registry.py` — atomic local JSON registry;
  experiment IDs are immutable and comparisons fail closed when provider,
  universe, intervals, features or evaluation fingerprints differ.
- `src/crypto_autopilot/research/resource_planning.py` — proposal ordering using bounded
  cost evidence. Adaptive utility remains at least 65%; missing estimates are
  neutral; no scheduler, promotion or trade authority is exposed.

The JSON registry is a local/reference catalog. Durable production metadata
storage remains a separately authorized Host/R2 concern, and bulk artifacts
should be referenced by URI plus digest rather than embedded in the registry.

## Safety contract

The configuration in `config/research_governance_v0_1.json` is intentionally
`RESEARCH_ONLY`. It preserves:

- `holdout_access_authorized=false`;
- `source_switch_authorized=false`;
- `trade_plan_authorized=false`;
- zero promotion/deployment/R2-write authority; and
- no mutation of V0.10 production-critical files or workflows.

This layer is evidence for later human-reviewed research decisions. It is not a
profitability claim, a provider-equivalence result, a backtest admission, or a
live-trading authorization.
