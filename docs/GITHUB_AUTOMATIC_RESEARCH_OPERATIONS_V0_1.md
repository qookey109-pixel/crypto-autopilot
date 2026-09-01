# GitHub Automatic Research Operations V0.1

Status: **AUTHORIZED ON PROTECTED MAIN MERGE**

## Outcome

GitHub Actions schedule events are the normal execution path for every
currently authorized online research operation. An operator no longer needs to
press `Run workflow` for routine metadata capture, structured-signal collection,
quality checks, Crypto Core 100 history/training, alternative-asset metadata or
automation health.

Manual dispatch remains present only where it is useful for bounded regression
or a separately authorized emergency. A manual run never counts as evidence
that a cron is healthy and cannot bypass a time, provider, R2, holdout, budget,
model or trading gate.

## Current online control plane

`Research Automation Health V0.2` runs every two hours at `:57` UTC. It reads
GitHub Actions metadata only, requires exact coverage of every Repository cron,
and uploads a secret-free `health.json` artifact for 90 days. A passing pull
request or manual run cannot mask a missing scheduled run.

The exact seven scheduled workflows and their cron expressions are frozen in
`config/github_automatic_research_operations_v0_1.json`. The older V0.1 health
cron is retired in the same change to avoid duplicate control planes; its
manual regression entry and historical authority receipt remain preserved.

## Waiting scopes

Automation does not create authority. The following still require a separate
versioned authority merged through protected `main`:

- V0.12 production metadata-stability evaluation after the complete window;
- replacement holdout access;
- Post-window Paper Training V0.2;
- Pionex alternative-asset candles and training;
- model promotion, trade plans, real-money orders or live trading.

A date, a successful workflow or a model-quality PASS cannot self-authorize any
of those scopes. The control plane reports them as waiting instead of inventing
a fallback or requesting manual execution.

## Cost and security boundary

- Runtime budget remains `0 USD/month`.
- Render remains Free and receives no R2 credentials.
- Existing R2 authorities retain their fresh 8 GB hard stop.
- No provider or R2 authority is added by this control-plane version.
- Replacement holdout remains `FROZEN_UNOPENED`.
- `source_switch_authorized=false` remains binding.
- Live trading remains disabled.
