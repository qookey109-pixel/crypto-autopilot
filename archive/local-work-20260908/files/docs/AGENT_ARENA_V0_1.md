# Agent Arena V0.1

Status: **PREPARED RESEARCH UTILITY / NOT SCHEDULED / ZERO AUTHORITY**

This is a small deterministic ranking view inspired by the Agent Challenge idea
in HKUDS/AI-Trader. It reuses the existing immutable
`crypto_autopilot.experiment_registry` records. It does not import AI-Trader,
execute external agents, fetch providers, access the holdout, write R2, change
the strategy, promote a model, or create a trade plan.

## Purpose

Compare already-produced challenger evidence under one fixed comparison key:

```text
same provider + universe + intervals + features + evaluation fingerprint
  -> candidate records
  -> fold / trade-count / drawdown eligibility
  -> deterministic ranking
```

This prevents a leaderboard from comparing different data windows or providers
as if they were one experiment. Rejected and incomplete candidates remain in
the decision output but never appear in the eligible ranking.

## Initial use

The arena is intended for offline research candidates such as:

- technical baseline;
- volume / breakout challenger;
- volatility-regime challenger;
- TimesFM shadow forecast, once separately implemented and licensed for the
  intended use.

Candidate labels are metadata only. They do not grant execution authority.

## Safety contract

- inputs are immutable experiment evidence, not live provider data;
- only completed evidence with the same comparison fingerprint is comparable;
- the default gate requires four completed folds and a recorded maximum
  drawdown;
- holdout access is always false;
- promotion authority is always `0`;
- trade-plan and live-trading authority are always false;
- no automatic winner-to-strategy promotion exists;
- no GitHub Actions schedule is added by this utility.

## Deliberate non-goals

Do not copy AI-Trader's external Agent Skill downloader, Copy Trading API,
Telegram/LLM execution path, SQLite authority, or exchange execution modules.
The current project keeps Repository/config/receipt authority, provider
separation, Cloudflare R2 persistence and the Repository Paper Broker boundary.

## Future activation gate

Activation requires a separate versioned authority that names the candidate
set, comparison key, metric contract, retention destination and schedule. A
future activation must still preserve `PAPER-ONLY`, frozen holdout rules and
manual human review for any strategy change.
