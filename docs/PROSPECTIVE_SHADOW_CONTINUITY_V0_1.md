# Prospective Shadow Cross-Batch Continuity V0.1 — Research-only Preparation

## Actual existing two-Artifact audit — 2026-10-09 Asia/Taipei

**Evidence:** [GitHub Actions run 37882460289](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/37882460289) from temporary, **closed-unmerged** [PR #783](https://github.com/qookey109-pixel/crypto-autopilot/pull/783). The PR-only workflow used a read-only GitHub token to fetch **only** the previously recorded artifacts 11561747502 and 11579982145. ZIP SHA-256 matched the GitHub metadata digests for **both**. Embedded report Run IDs 37802372751 / 37846141319, attempts, schedule/main source SHA, and run/capture time bounds matched. The pure merged v0.1 validator accepted their 5-market/240-closed-60M-candle coverage, hashes, causality bounds and research-only authority, finding **936 identical overlapping candles**, no observed inter-capture gap over 6 hours, and maximum source lag **38 minutes**.

**Interpretation:** `PARTIAL_OBSERVATION_ONLY` / `PASS_PARTIAL_ONLY_NOT_PRODUCTION`. Distinct context observations remain **2 of required 21** (`INSUFFICIENT`). The two captures do not prove every cron slot, continuous collection for 30–90 days, prospective future outcome measurement, strategy quality, execution readiness or any production `NO_TRADE`. The validator's stand-alone `source_archive_digests_authenticated=false` / `github_run_metadata_authenticated=false` are honest for caller-supplied JSON; the *surrounding temporary GitHub audit job* independently verified the original two ZIP digests and expected identities. These proof layers are not interchangeable.

Temporary workflow PR #783 was deliberately **closed without merge**, so no extra scheduled or registered workflow was introduced to main and no convergence guard relaxed. No provider/API/Cloudflare/holdout access, R2/D1 write, train, promotion or trading occurred. This evidence may be projected read-only on the Dashboard but **does not authorize** real or Cloud Paper orders. Core100 quality remains REJECT and Cloud Paper NOT_WIRED / NOT_RUN / NOT_CONFIGURED.

---


**Date:** 2026-10-09 (Asia/Taipei). **Execution:** CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER. **Authority:** this batch is deterministic, pure and synthetic-tested only. No new GitHub workflow, provider call, GitHub artifact download, R2/D1, holdout, training, promotion or trading operation.

## Verified GitHub metadata versus content proof

Two existing naturally scheduled Shadow runs were checked through GitHub Actions **metadata** only:

| UTC creation | Run / attempt | Result | Artifact | Archive SHA-256 (GitHub metadata) |
| --- | --- | --- | --- | --- |
| 2026-10-08 15:38:05 | [37802372751](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/37802372751), 1 | workflow success | 11561747502 | `01c0c62cff750a41a02e8f2d7dcf26c481327135cff8fcd38610874140a54891` |
| 2026-10-08 21:21:03 | [37846141319](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/37846141319), 1 | workflow success | 11579982145 | `adcfc5e1382b1b248bae0e14f5a9acbd305c88b30fca7931dbcf0b0a2b6862df` |

Both runs were schedule events on `cad0aea7273acc1cb1eaa138955b6381e30bd5a6`. Both artifacts were present and unexpired at inspection. **Only the newer artifact** has its actual ZIP and embedded record/candle contents checked via cloud-only GitHub Actions [37878449661](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/37878449661); the earlier one has **no content verification claim**. Artifact metadata is not equivalent to integrity/content or causal acceptance. The observed run creation times differ by 5 h 43 m, but that alone is not proof of exactly one full 4-hour scheduled slot; GitHub schedules may be delayed.

## New bounded pure validator

`src/crypto_autopilot/research/prospective_shadow_continuity_v0_1.py` accepts caller-supplied already-read report dictionaries, with a ceiling of 100 reports and no external access. It fails closed on:

- invalid scheduled-main provenance or unexpected run attempt; wrong provider request counts, collector/report/candle/record hashes, false production claims or changed authority;
- duplicate run IDs, capture timestamps or content IDs; invalid five-market/240-bar coverage, 60M sequence gaps, not-yet-closed candles and future feature timestamps;
- **revised overlapping historical candles** across successive batches for the same symbol and candle timestamp. Top-five symbol rotation is permitted and cannot be mistaken for five stable symbols.

It reports observed capture intervals over 6 hours as review gaps, records source lag, distinguishes `INSUFFICIENT` from count-only 21 context observations, and always keeps eligibility, archive authentication, full schedule completeness and predictive outcome claims **false**. This code does **not** authenticate caller-provided reports against external GitHub artifact identity or independently verify archive SHA-256; that requires a separately governed read-only cloud operation.

## Acceptance sequence and limitations

First make this pure review and its mutation tests green in the existing GitHub CI; then separately verify the earlier artifact ZIP and report, with no new workflow registration that bypasses `project_convergence`/workflow inventory guards. Only then feed authenticated and chronologically governed report content to this validator in a cloud-only bounded review. `REVIEW_REQUIRED` results must remain visible and must never be silently filled with `NO_TRADE`, `LONG`, `SHORT` or strategy-rank claims.

**Still blocked:** production Core100 quality REJECT; Shadow has no strategy/holdout/promotion authority, signal-outcome study remains insufficient, Cloud Paper NOT_WIRED / NOT_RUN / NOT_CONFIGURED, and billing/D1/account-wide writer admission are incomplete. This PR does not modify active collection schedules, versioned execution authority, or application UI.
