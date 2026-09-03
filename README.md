# Qookey Crypto Autopilot

Cloud-first, exchange-agnostic crypto trading research and automation platform.

> **Current mode: PAPER-ONLY.** No real-money order path is authorized. `trade_plan_authorized=false` and `live_trading_authorized=false` remain mandatory. For the detailed current authority index, always read [`PROJECT_STATUS.md`](PROJECT_STATUS.md) first.

## Start here

- [`PROJECT_STATUS.md`](PROJECT_STATUS.md) — formal current authority.
- [`docs/PROJECT_MAP_V0_1.md`](docs/PROJECT_MAP_V0_1.md) — concise repository map.
- [`docs/AUTOMATION_INDEX_V0_1.md`](docs/AUTOMATION_INDEX_V0_1.md) — only the schedules that can still run.
- [`docs/STRATEGY_INDEX_V0_1.md`](docs/STRATEGY_INDEX_V0_1.md) — one view of the Paper baseline and research layers.

Historical configs, receipts and CLI paths remain for evidence, but these four
files are the current operating surface.

## Current authority snapshot — 2026-09-03

The repository has moved beyond the original V0.1 implementation baseline while preserving its scientific history:

- Pionex M1/M1A historical-data foundation: **PASS**.
- Cloudflare R2 historical storage and Binance 2025 pilot: **PASS**.
- Binance Funding V0.2 R2 materialization: **PASS** — 192/192 authorized object identities verified after write.
- Binance USD-M Crypto Core 100 V0.1.2: **AUTHORIZED AFTER V0.10 WINDOW / NOT STARTED** — 100 unique Crypto markets, fixed 2022-08 through 2026-07 window, native 15m/1h/4h archives, 10 R2-only shards and bounded intraday research training. V0.1.1 was superseded before execution and remains immutable; tokenized-equity historical K-line data requires a separate future dataset authority.
- Pionex Alternative Assets Observability V0.2: **AUTHORIZED AFTER V0.10 WINDOW / NOT STARTED** — the unexecuted V0.1 schedule was superseded before provider/R2 access. A separate 125-candidate registry (90 equity/stock-linked, 31 ETF/fund-linked and 4 metal references) is validated against live Pionex `PERP + TRADING` metadata, compared weekly with its prior SHA-bound catalog and given a planning-only four-year capacity estimate. K-lines, funding, history/training and trading remain unauthorized.
- Pionex ↔ Binance Equivalence V0.1: **definitive FAIL** — 45 pairs = 18 PASS / 18 REVIEW / 9 FAIL. The frozen result must not be regraded by changing thresholds or scope.
- `source_switch_authorized=false`; Binance evidence remains `provider=binance_usdm` and must never be relabeled as Pionex-native evidence.
- V0.5 Render Free / Frankfurt Binance public-metadata transport: **PASS**.
- V0.6 Render transport authority transition: **PASS**, while historical V0.2 Self-Hosted Mac transport authority remains preserved.
- V0.7 successor Render metadata-capture protocol: historical **PREPARED / EXECUTION_NOT_AUTHORIZED** authority, preserved unchanged.
- V0.8 shared relay secret handshake: **PASS**; V0.8 prepared cutover contract and hard-disabled scaffold remain historical preparation authorities.
- V0.9 authenticated Render relay smoke: **PASS** — HTTP 200 / valid JSON / `symbol_count=872` / zero R2 writes / zero holdout access.
- V0.10 final atomic metadata-capture cutover: historical **EFFECTIVE / AUTHORIZED** after merged PR #127 at `8fce944da479dbda0e2899f9b30b9de62351fa27`.
- PR #210's exact Pionex `type=PERP` query remains **EFFECTIVE HISTORICAL
  LINEAGE** on `main` at
  `a34cf471876971a97200de4974906743642ed61f`, but observed scheduled runs #36
  through #41 failed closed because the returned perpetual symbol record did
  not preserve the frozen required `status` / `contractType` contract. The
  failure occurred before R2 client construction; no R2 or holdout access occurred.
- V0.2 self-hosted scheduled metadata capture is now **RETIRED AS EXECUTION PATH**; its receipts remain immutable historical evidence.
- V0.10 GitHub-hosted schedule is **RETIRED ON THE EXACT V0.12 MAIN MERGE**;
  its failures and missing slots remain immutable evidence and cannot be
  replayed, backfilled or regraded.
- V0.12 successor metadata window is **AUTHORIZED ON THE EXACT REVIEWED MAIN
  MERGE**. It is the only scheduled metadata-capture path, covering
  `2026-09-04T02:00:00Z` through `2026-09-12T03:59:59.999Z` with 194 hourly
  slots and an independent R2 namespace. At the 2026-09-03 observation the
  window has not started yet.
- PR #212 and minimum operational commit
  `80732edee9a8954b53b4b56115ecb0d506591f0a` are recorded in a separate
  append-only binding amendment, preserving the pre-binding authority files.
- GitHub Automatic Research Operations V0.1 is **AUTHORIZED ON MAIN MERGE**.
  PR #213 is merged on `main` at
  `0f1c7675f15301c248b64bbaa4a10bc956f3fdf6`; all seven currently authorized
  online workflows use GitHub cron as their normal path. Research Automation
  Health V0.2 checks the complete schedule inventory every two hours at `:57`
  UTC, and manual/PR runs cannot count as cron health. Current scheduled Health
  V0.2, Signal Layer V0.2 and Signal Quality V0.1 runs have been observed
  completing successfully. This adds no holdout, model-promotion or trading
  authority.
- V0.11 metadata-stability evaluator: **PREPARED / PRODUCTION R2 EVALUATION NOT AUTHORIZED**. Its deterministic 194-slot rules were frozen before production stability evidence is read.
- Replacement holdout `2026-08-28` through `2026-09-03`: **FROZEN_UNOPENED**; candle access and evaluation remain unauthorized. Calendar passage does not grant access authority.
- Metadata stability evaluation: **NOT_YET_RUN**. Because failed or missing
  V0.10 slots cannot be backfilled, the historical V0.10 window is blocked
  from producing a complete 194-slot PASS dataset. V0.12 is the separately
  versioned successor decision; it does not repair or regrade V0.10.

The retired V0.10 authority remains historical evidence. V0.12 authorizes only
the successor public-provider metadata capture phase and metadata-only R2 writes
inside its exact window. Production stability evaluation is not authorized.
Neither stage authorizes replacement holdout candles, source switching,
Historical Universe membership, W1 materialization, backtest admission,
strategy changes, trade plans, real-money orders, or live trading.

The separate **Pionex Public Paper Training V0.1** path was authorized for bounded
public-market reads, fixed-rule candidate generation, deterministic Repository
Paper Broker replay, secret-free training evidence and a read-only GitHub Pages
projection. It stops all provider requests at `2026-08-27T00:00:00Z` to avoid the
frozen V0.10/holdout window. Pionex Demo remains manual sampling only; no private
API, automated demo order, formal trade plan, real-money order or live-trading
authority is introduced. Its hourly cron is retired after that cutoff; manual
dispatch remains only to validate the fail-closed stop.

The historical **Binance Spot R2 Training Governance V0.5** path discovered the active public
Spot catalog, built provider-separated daily history, trained deterministic
research models and published the canonical dataset/model lineage to Cloudflare
R2 on its bounded Sunday `02:37 UTC` (`10:37 Asia/Taipei`) schedule. The same run performed
expanding-window walk-forward diagnostics, fee/slippage sensitivity, diagnostic
maximum drawdown and model-signal exposure checks. Pipeline completion is now
reported separately from a baseline/cost/drawdown/concentration model-quality
gate, so rejected research remains evidence without looking approved. Payload
contracts and market/audited/row-depth collapse gates run before any R2 write.
A separate first-day monthly
review compares active markets, catalog absences, survivorship-bias limitations
and heuristic tokenized-stock classifications; repository pushes do not run
either production workflow. The initial monthly V0.5 baseline completed in run
`32589005957`, consuming the one-time manual activation. The first weekly run
`32615608243` also completed; its pipeline passed and its model-quality gate
returned `REJECT`. Repeated monthly manual activation and push activation are
not authorized. The generated review carries the exact
config/comparison governance evidence and is contract-validated before R2 writes.
R2 is the only persistent
generated-data store; raw training history is not projected to GitHub Pages.
V0.3 daily and V0.4 weekly/monthly execution are retired. V0.5 uses separate
authority and R2 namespaces. No source-switch, formal backtest admission,
automatic model promotion, W1, holdout or trading authority is introduced.
Its weekly/monthly cron triggers are now retired after the same binding cutoff;
manual dispatch remains fail-closed and cannot automatically resume.

Data retention is intentionally split: the V0.5 Binance Spot `1d` training
history remains from `2020-01-01` to the latest complete UTC day, while future
detailed `15m`/`1h`/`4h` and derivative-state materializations are planned as a
rolling four-year window. The prepared, inactive policy is documented in
[`docs/DATA_RETENTION_POLICY_V0_1.md`](docs/DATA_RETENTION_POLICY_V0_1.md).

The separate **Binance USD-M Crypto Core 100 V0.1.2** path expands detailed
research coverage beyond the original 15-contract basket. It discovers a broad
provider-separated catalog but materializes only 100 unique Crypto markets from
official Binance Vision archive coverage. Tokenized-stock/ETF and other-asset
candidates remain classified metadata for a separate future dataset. The Core
materializes 48 complete months of native 15m/1h/4h candles in 10 serialized
R2 shards. Execution begins only after
`2026-09-04T02:00:00Z`; its source ends at 2026-07 and cannot read the
replacement holdout. After all shards complete, a weekly research trainer runs
causal multi-timeframe walk-forward, cost, drawdown and exposure diagnostics.
See the current [`docs/BINANCE_USDM_CRYPTO_CORE_100_V0_1_2.md`](docs/BINANCE_USDM_CRYPTO_CORE_100_V0_1_2.md)
and the preserved superseded addendum in
[`docs/BINANCE_USDM_DETAILED_HISTORY_V0_1_1.md`](docs/BINANCE_USDM_DETAILED_HISTORY_V0_1_1.md), plus the historical full design in
[`docs/BINANCE_USDM_DETAILED_HISTORY_V0_1.md`](docs/BINANCE_USDM_DETAILED_HISTORY_V0_1.md).

The separate **Pionex Alternative Assets Observability V0.2** keeps tokenized stocks,
ETF/fund-linked contracts and direct metal references outside Crypto Core 100.
It contains 125 point-in-time candidates, but selects only exact symbols still
returned by Pionex public perpetual metadata. Its first catalog run is
`2026-09-04 02:53 UTC` (`10:53 Asia/Taipei`), followed by four bounded weekly
reviews in September. Each run adds structural validation, a prior-catalog diff
and a planning-only capacity estimate; the website receives only aggregate safe
summary fields. This is metadata-only discovery; the proposed Pionex-native
`15M / 60M / 4H` history remains waiting for V0.11 and a separate holdout/candle
authority. See [`docs/PIONEX_ALTERNATIVE_ASSETS_OBSERVABILITY_V0_2.md`](docs/PIONEX_ALTERNATIVE_ASSETS_OBSERVABILITY_V0_2.md).

The prepared V0.6 Shadow Model compares feature groups locally after the first
V0.5 quality gate rejected the current model. It records calibration and
descriptive regime evidence only; it cannot read providers, write R2, access
the holdout, promote a model or trade. See
[`docs/BINANCE_SPOT_SHADOW_V0_6.md`](docs/BINANCE_SPOT_SHADOW_V0_6.md).

The prepared Research Signal Layer keeps current closed candles, append-only
historical evidence and timestamped KOL forecasts separate. It enforces
close-time and publication-time boundaries, rejects revisions and provider
mixing, and evaluates KOL accuracy, Brier score and baseline lift as
descriptive challenger evidence only. It does not fetch external KOL sources,
write production R2, promote a model or trigger a trade. See
[`docs/RESEARCH_SIGNAL_LAYER_V0_1.md`](docs/RESEARCH_SIGNAL_LAYER_V0_1.md).
V0.2 connects this contract to a daily bounded public-source collector. It
stores source metadata and only explicitly structured JSON forecasts in a
dedicated R2 namespace, with fresh FREE-ONLY headroom gates and no prose
direction inference. It remains challenger evidence only; the existing
Pionex hourly paper path and Binance weekly historical trainer remain separate.
See [`docs/RESEARCH_SIGNAL_LAYER_V0_2.md`](docs/RESEARCH_SIGNAL_LAYER_V0_2.md).
Two current read-only guardrails sit beside that collector: Research Signal
Quality V0.1 runs daily at `02:47 UTC`, and Research Automation Health V0.2 runs
every two hours at `:57` UTC. Health V0.2 is the single complete cron control
plane, covers all seven current schedules and ignores manual/PR runs when
judging automatic health. The historical Health V0.1 workflow is retained for
manual regression only. These guardrails do not open the holdout, promote
models or affect trading. See
[`docs/GITHUB_AUTOMATIC_RESEARCH_OPERATIONS_V0_1.md`](docs/GITHUB_AUTOMATIC_RESEARCH_OPERATIONS_V0_1.md)
and [`docs/AUTOMATION_INDEX_V0_1.md`](docs/AUTOMATION_INDEX_V0_1.md).
The proposed rolling four-hour data refresh, weekly Shadow ablation and monthly
drift review remain prepared but inactive pending a separate post-window
authority.
The research-only continuous-learning implementation target and its exact
completion gates are recorded in
[`docs/CONTINUOUS_LEARNING_ROADMAP_V0_1.md`](docs/CONTINUOUS_LEARNING_ROADMAP_V0_1.md).
The `2026-09-30` target is a prepared engineering roadmap, not execution
authority, automatic model promotion or a profitability promise.
The prepared, research-only
[`Strategy Edge Validation V0.1`](docs/STRATEGY_EDGE_VALIDATION_V0_1.md)
adds deterministic anti-overfitting gates after UPDATE-only parameter
selection: stationary bootstrap, Deflated Sharpe, PBO/CSCV, Romano-Wolf
stepdown, disjoint-validation Sharpe retention and signal-alignment
permutation. It requires the complete trial family and partition-integrity
evidence, fails closed on missing inputs, and grants no provider, R2, holdout,
promotion or trading authority.
[`Strategy Research Loop V0.1`](docs/STRATEGY_RESEARCH_LOOP_V0_1.md) wraps that
gate with a deterministic 120-hypothesis registry and a cost-complete
Repository paper-ledger audit. It reports expectancy, profit factor,
drawdown, concentration and stationary-bootstrap Monte Carlo fragility while
binding exact candidate/provider/fingerprint lineage. It is synthetic-only,
creates no workflow or second broker, and can reach only human-review
eligibility with zero promotion or trading authority.
The current time-ordered operating handoff is
[`docs/RESEARCH_AUTOMATION_HANDOFF_V0_1.md`](docs/RESEARCH_AUTOMATION_HANDOFF_V0_1.md).

## FREE-ONLY cloud policy

The current cloud policy is frozen in [`config/cloud_free_tier_policy_v0_1.json`](config/cloud_free_tier_policy_v0_1.json):

- monthly project budget: **0 USD**;
- no paid fallback, automatic subscription change, or payment-method upgrade path;
- Cloudflare Containers are retired for this project because they require Workers Paid;
- Koyeb V0.4 is superseded and is not a current transport candidate;
- the current Mac-independent Binance public-metadata transport is **Render Free / Frankfurt**;
- every authorized metadata R2 write remains subject to a fresh whole-bucket FREE-ONLY **8 GB hard-stop/headroom gate**; V0.12 freezes the same `8,000,000,000` byte operational hard stop;
- Render must never receive R2 credentials; R2 credentials remain in GitHub Actions secrets only;
- historical proof/materialization workflows whose evidence is already frozen must be validation-only and must not silently regain schedules, push triggers, provider calls, self-hosted execution, or R2 credentials.

## V0.10 metadata capture historical boundary

Historical V0.10 orchestration is preserved as fail-closed evidence; its
schedule was removed atomically when V0.12 became effective:

- historical workflow: `.github/workflows/provider-equivalence-v0-10-render-metadata-capture.yml`;
- runner: `ubuntu-latest`;
- Pionex metadata leg: direct public HTTPS from GitHub Actions;
- Binance USD-M metadata leg: authenticated Render Free Frankfurt path `/metadata/v0-10/binance-exchange-info`;
- exact historical metadata window: `2026-08-27T00:00:00Z` through `2026-09-04T01:59:59.999Z`;
- frozen design: 194 UTC hourly slots with scheduled attempts at minute `:17` and `:47`;
- observed failed/missing slots are immutable; replay, manual capture and retroactive backfill are unauthorized;
- V0.7 historical raw relay path remains disabled;
- V0.2 self-hosted scheduled execution remains retired and is not an automatic fallback.

The shared `METADATA_RELAY_TOKEN` is provisioned out of band in Render and GitHub Actions. Its value must never be committed, logged, posted in issues, artifacts, or chat.

## V0.12 successor metadata boundary

The current successor authority is frozen in
`config/provider_equivalence_v0_12_successor_metadata_window_v0_1.json` and its
append-only binding. Current execution rules are:

- workflow: `.github/workflows/provider-equivalence-v0-12-successor-metadata-capture.yml`;
- runner: `ubuntu-latest`;
- exact window: `2026-09-04T02:00:00Z` through `2026-09-12T03:59:59.999Z`;
- 194 UTC hourly slots / 388 bounded attempts at `:17` and `:47`;
- independent R2 namespace: `metadata/provider-equivalence/v0_12/successor-window-20260904/`;
- Pionex normalization accepts the frozen modern `contractType/status` or legacy `type/enable` representations and fails closed before R2 construction when they are missing, unknown or conflicting;
- each complete capture remains immutable, writes its receipt last and requires post-write SHA-256 readback;
- fresh whole-bucket 8 GB FREE-ONLY headroom is required before every authorized write;
- no V0.10 fallback, replay or backfill is authorized;
- production stability evaluation, holdout access, source switching, automatic promotion and trading remain unauthorized.

At the 2026-09-03 status observation, this execution window is still waiting for
its exact not-before time; no V0.12 evidence result is assumed in advance.

## V0.11 metadata-stability evaluator boundary

The evaluator is frozen in `config/provider_equivalence_v0_11_metadata_stability_evaluation_v0_1.json` and `src/crypto_autopilot/provider_metadata_stability_v0_11.py`.

Current state:

- exact 194 UTC hourly slots are required for the evidence set being evaluated;
- duplicate captures within a slot are acceptable only when each provider's normalized 15-symbol vector matches exactly;
- Pionex and Binance USD-M vectors must each remain exactly stable across the full frozen evaluation window;
- missing slots, invalid receipts, SHA mismatch, intra-slot disagreement, or cross-window vector drift fail closed;
- `V0_11_R2_EVALUATION_EXECUTION_AUTHORIZED = False`;
- no production R2 client construction or receipt reads are authorized yet;
- no holdout object may be listed, read, or evaluated;
- a future stability PASS still requires a separate versioned holdout-access authority.

## V0.1 strategy scope

V0.1 remains **research + backtest + paper trading only**. Live trading is intentionally disabled until explicit safety gates are passed.

Primary execution target: **Pionex perpetual futures**. Future exchange adapters must plug into the same exchange interface without changing strategy or risk logic.

### SState Intraday Wave V0.1

- Universe: roughly 10–20 liquid perpetual markets
- 4H: SState market context
- 1H: trend/setup filter
- 15m: pullback/reclaim entry
- Direction: LONG-only for V0.1
- Frequency: 0–3 trades/day; never force a trade
- Default risk: 1% equity per trade
- Leverage cap: 3x, isolated-margin design target
- Daily loss gate: -3R disables new entries until next trading day

SState is treated as an upstream provider. Its validated core must not be rewritten by this repository.

## Architecture

```text
Provider-separated public market data
        |                    |
        |                    +--> Binance USD-M / Binance Vision research evidence
        |
        +--> Pionex native execution-target evidence
        |
        v
   Exchange Adapters -----> Historical Store / R2
        |
        +-----> SState Adapter
                   |
                   v
            Strategy Engine
                   |
                   v
               Risk Engine
                   |
                   v
              Paper Broker
                   |
                   v
              Performance

Future, separately gated only:
Paper Broker -> Private Execution Adapter
```

The Python source tree is grouped by responsibility under
`src/crypto_autopilot/`: `binance`, `features`, `history`, `paper`,
`providers`, `research`, `storage`, `training` and `exchanges`. A small set of
stable core APIs and versioned workflow/receipt-bound modules intentionally
remain at the package root. See
[`docs/PACKAGE_STRUCTURE_V0_1.md`](docs/PACKAGE_STRUCTURE_V0_1.md) for the
dependency rules and the complete exception list.

Current zero-cost infrastructure split:

- GitHub: source, CI, versioned authority, the V0.12 successor metadata schedule, validation jobs and R2 credentials; V0.10 is retained as historical fail-closed evidence only;
- Render Free / Frankfurt: authenticated Binance public-metadata transport leg only;
- Cloudflare R2 Standard Free: immutable historical/provider metadata storage under explicit metadata-only write authority;
- GitHub Pages / static assets: read-only Traditional Chinese dashboard;
- Cloudflare Free services may be used only within the frozen FREE-ONLY policy and only where they are not transport-blocked.

## M1 historical data foundation

M1 adds public-data-only tools for discovering active Pionex PERP symbols, ranking a controlled USDT-PERP universe, deterministic Kline pagination for `15M` / `60M` / `4H`, and duplicate/order/gap/alignment/OHLCV integrity audits.

Select a current 15-symbol candidate universe:

```bash
python scripts/select_pionex_universe.py --target-size 15
```

Backfill an explicit historical range:

```bash
python scripts/backfill_pionex_history.py BTC_USDT_PERP 15M \
  --start 2026-01-01T00:00:00Z \
  --end 2026-08-01T00:00:00Z \
  --output /tmp/BTC_USDT_PERP-15M.json
```

Bulk historical data is not stored in GitHub; canonical storage evidence is kept in R2 under versioned authorities and receipts.

## Safety boundary

- Never commit Pionex/Binance API keys, relay tokens, Cloudflare tokens, R2 credentials, or other secrets.
- `.env.example` contains variable names only.
- `METADATA_RELAY_TOKEN` is an out-of-band shared secret between Render and GitHub Actions; never expose its value.
- No martingale, loss-doubling, unlimited averaging down, cross-margin dependency, or liquidation-as-stop.
- Provider provenance remains explicit; provider splicing, silent interpolation and Pionex-native relabeling are forbidden.
- Historical V0.10 and current V0.12 metadata-capture authorization are **not** trading authorization.
- V0.11 evaluator preparation is **not** metadata-stability PASS or production evaluation authority.
- Replacement holdout candle access/evaluation remains forbidden until a separate post-stability authority exists.
- No live order path is authorized.

## Quick start

Python 3.11+ recommended.

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

Fetch a public Pionex sample (no API key required):

```bash
python scripts/fetch_pionex_sample.py BTC_USDT_PERP 15M
```

Binance history and model outputs are online-first. Cloudflare R2 is the only
persistent generated-data store; GitHub Actions builds in a disposable workspace
and deletes it after upload. A local diagnostic run must use a system temporary
directory and is not retained:

```bash
run_dir="$(mktemp -d)"
PYTHONPATH=src .venv/bin/python scripts/discover_binance_training_universe.py \
  --output "$run_dir/market-catalog.json"
PYTHONPATH=src .venv/bin/python scripts/fetch_binance_internal_training.py \
  --catalog "$run_dir/market-catalog.json" \
  --output-dir "$run_dir/dataset"
```

The online R2-first pipeline is defined by
[`config/binance_spot_r2_training_governance_v0_5.json`](config/binance_spot_r2_training_governance_v0_5.json),
[`.github/workflows/binance-spot-r2-training-governance-v0-5.yml`](.github/workflows/binance-spot-r2-training-governance-v0-5.yml),
and [`.github/workflows/binance-spot-r2-monthly-governance-v0-5.yml`](.github/workflows/binance-spot-r2-monthly-governance-v0-5.yml).
It uses GitHub Actions secrets for R2 credentials, never retains generated data
in the local repository, and never exposes raw history through the website.

## Authority and documentation

Read in this order for current work:

1. [`PROJECT_STATUS.md`](PROJECT_STATUS.md)
2. [`AGENTS.md`](AGENTS.md)
3. current versioned protocol/config and receipt for the stage being changed
4. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
5. [`docs/STRATEGY_V0_1.md`](docs/STRATEGY_V0_1.md) and [`config/strategy_v0_1.json`](config/strategy_v0_1.json)

The offline research governance extension is documented in
[`docs/RESEARCH_GOVERNANCE_V0_1.md`](docs/RESEARCH_GOVERNANCE_V0_1.md) and
configured by [`config/research_governance_v0_1.json`](config/research_governance_v0_1.json).

Current cadence and effective automation state are indexed in
[`docs/AUTOMATION_INDEX_V0_1.md`](docs/AUTOMATION_INDEX_V0_1.md) and the
machine-readable
[`config/github_automatic_research_operations_v0_1.json`](config/github_automatic_research_operations_v0_1.json).

Historical receipts remain immutable evidence even when a later version supersedes their execution role.

## Engineering agent tools

The Repository-local
[`change-walkthrough`](.agents/skills/change-walkthrough/SKILL.md) skill gives
PRs, commits and selected local diffs a paced, read-only explanation. It fixes
remote changes to immutable SHAs, keeps staged/unstaged/untracked evidence
separate and never edits, reviews, pushes, merges or grants authority.

New agent-facing interfaces follow three convergence rules:

- one canonical Python domain action owns validation and behavior;
- UI, CLI, HTTP or future agent adapters may expose that action but cannot
  bypass its Repository authority checks;
- every adapter preserves the same deterministic JSON evidence or receipt.

Interface parity by itself does not justify a second runtime, database,
framework or deployment surface. External agent frameworks remain design
references unless a separate bounded change demonstrates a concrete need.
This independent policy was informed by the read-only tour pattern in
[`sirius-skills/walkthrough-me`](https://github.com/sirius-cc-wu/sirius-skills/tree/main/skills/walkthrough-me)
and the shared-action idea in
[`BuilderIO/agent-native`](https://github.com/BuilderIO/agent-native); no
external instructions, source code or runtime dependency are vendored.