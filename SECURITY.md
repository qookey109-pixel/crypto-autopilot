# Security Policy

## Secret handling

Never commit, print, log, upload as an artifact, paste into issues/PRs/chat, or place in fixtures:

- `PIONEX_API_KEY`
- `PIONEX_API_SECRET`
- any future Binance API key/secret
- `DIAGNOSTIC_TOKEN`
- `METADATA_RELAY_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`
- `R2_BUCKET_NAME` when treated as deployment configuration
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- Cloudflare API tokens
- account credentials, private keys, session tokens, or recovery codes

Repository files contain names/placeholders only. Use GitHub Actions Secrets, Render Environment, or another separately authorized deployment secret store.

Do not echo secret values for debugging. Presence checks must be boolean/length-only and must not reveal the value. If a secret is ever committed or exposed in logs/artifacts, revoke/rotate it immediately; deleting the file is not sufficient because Git history and cached artifacts may retain it.

## Runtime separation

- Render Free / Frankfurt is a public Binance metadata transport only. **Render must never receive R2 credentials.**
- R2 credentials remain in the authorized GitHub Actions/local secret boundary only.
- `METADATA_RELAY_TOKEN` is the out-of-band shared secret used by GitHub Actions to authenticate the versioned Render metadata relay. Never persist its value in Repository authority evidence.
- `DIAGNOSTIC_TOKEN` is diagnostic-only and must not be reused as a trading credential.
- Public Binance `exchangeInfo` does not require a Binance API key. This is not a project-wide API-key ban; any future authenticated Binance scope requires a separate security/authority version and may not be used as a transport-blocker bypass.

## Workflow safety

Historical proof/materialization workflows whose evidence is already frozen must remain validation-only. They must not silently regain schedules, push-triggered production execution, self-hosted runners, provider calls, R2 secret bindings, or write commands.

The only current scheduled metadata-capture execution path is the versioned V0.10 workflow. V0.11 production R2 stability evaluation remains unauthorized until a separate post-window authority exists.

Production-critical GitHub Actions are supply-chain hardened:

- `actions/checkout`, `actions/setup-python`, artifact, and Pages actions on critical workflows execute from reviewed immutable 40-character commit SHAs rather than mutable major tags;
- checkout keeps `persist-credentials: false`;
- CI/test dependency resolution uses `requirements/ci-constraints.txt`, while `pyproject.toml` keeps public compatibility ranges;
- the V0.10 scheduled capture job explicitly sets Python 3.13 before freshness checks, constrained dependency installation, provider access, or R2 access;
- changes that weaken these boundaries are covered by Repository regression tests.

Repository branch protection/ruleset state is an external GitHub setting, not a file-based authority. Do not assume `main` is protected unless GitHub settings are verified directly.

## Trading and holdout safety

Current mode is **PAPER-ONLY**. No real-money or live order path is authorized.

Replacement holdout candles remain `FROZEN_UNOPENED`; metadata capture/evaluator preparation does not authorize holdout access or evaluation. Provider substitution, provenance rewriting, and source switching remain unauthorized.
