# AI Resource Hub Research Integrations V0.1

Status: `PREPARED_RESEARCH_ONLY`

This integration connects selected ideas and tools cataloged by
`qookey109-pixel/ai-resource-hub` to Qookey Crypto Autopilot without expanding
trading or data-access authority.

The catalog source is `data/resources.json` in the AI Resource Hub. That catalog
is discovery/navigation input only; Crypto Autopilot repository `main`, versioned
configs/receipts and immutable evidence remain the authority for this project.

## Implemented now: statistical edge validation

The first active integration is a native Qookey Toolkit capability inspired by
the statistical-validation patterns documented by `mars-tw/anti-gambling-trader-tw`.
No upstream runtime dependency or copied upstream implementation is introduced.
The implementation is standard-library Python and is explicitly research-only.

Toolkit function:

`validate_statistical_edge(payload)`

CLI:

```bash
python scripts/qookey_crypto_toolkit_v0_2.py edge \
  --input research/examples/qookey_toolkit_statistical_edge_v0_1.json
```

GitHub Actions:

`Qookey Crypto Toolkit V0.2 Cloud` -> command `edge`

The input `returns`, `train_returns`, and `test_returns` are fractional returns
per observation; for example `0.01` means +1% and `-0.005` means -0.5%.

The analysis can produce:

- descriptive mean/std/error/win-rate evidence;
- a deterministic centered non-parametric bootstrap of positive mean return;
- optional explicit train/test out-of-sample comparison;
- top-N absolute/profit concentration diagnostics;
- first-half versus recent-half edge-decay diagnostics;
- optional bounded empirical-return ruin simulation.

These outputs are evidence, not promotion authority. In particular:

- a positive or statistically significant result does not change the Core100
  model-quality gate;
- it does not select a threshold automatically;
- it does not mutate strategy rules;
- it does not publish/promote a model;
- it does not open the frozen holdout;
- it does not create a formal trade plan or order.

The ruin simulation uses IID empirical resampling and therefore does not preserve
serial dependence. Its output is a research stress signal, not a capital or
profit guarantee.

## Prepared but disabled integrations

### BAML

Purpose: a future typed schema/eval boundary for LLM research outputs.

Current status: `PREPARED_DISABLED`.

Activation requires a separate versioned review. V0.1 adds no BAML package,
model call, API key or LLM authority.

### Graft

Purpose: optional local codebase context for Coding Agents.

Current status: `PREPARED_DEVELOPER_TOOL_ONLY`.

It must remain outside the trading/runtime dependency graph. Activation is a
local developer opt-in and is not required by CI or production research runs.

### World Monitor

Purpose: possible future macro/geopolitical/commodity/news context through its
programmatic interface rather than vendoring its AGPL source tree.

Current status: `PREPARED_EXTERNAL_CONTEXT_DISABLED`.

Activation requires separate network, provenance and license review. Any future
historical use must enforce:

`published_at_or_observed_at <= decision_cutoff`

so later information cannot leak into earlier research decisions.

### Agent Reach

Purpose: possible future public-research ingestion from web/RSS/GitHub and,
under separately reviewed rules, other platforms.

Current status: `PREPARED_RESEARCH_INGESTION_DISABLED`.

No browser cookie, login token or authenticated social access is authorized by
this integration. Any future platform-specific use requires source/ToS/privacy
review and the same decision-cutoff leakage protection.

## Authority boundary

V0.1 does not authorize:

- provider requests;
- external-context network execution;
- authenticated social access;
- R2 reads or writes;
- replacement holdout access;
- source switching;
- automatic strategy mutation;
- automatic model promotion;
- formal trade plans;
- real-money orders;
- live trading.

Machine-readable registry:

`config/resource_hub_integrations_v0_1.json`

Toolkit config:

`config/qookey_crypto_toolkit_v0_2.json`
