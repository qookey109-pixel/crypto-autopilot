# Render Relay 502 Remediation Review V0.1

Status: PREPARED_REVIEW_REQUIRED. This is a review contract, not execution authority.

## Observed issue

V0.12 capture [run 34424167855](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34424167855) passed its window and authority jobs, then received HTTP 502 from the existing Render relay while fetching Binance USD-M metadata. The exception occurred before the V0.12 capture code constructs its R2 store. No completed capture artifact or downstream boundary assertion exists for that run.

The earlier [2026-09-05 observation](../research/receipts/2026-09-05-v0-12-render-relay-502-observation.json) found a pattern consistent with cold start or edge wake failure, but it does not establish a root cause. This review must keep that distinction.

## Bounded review scope

The matching config permits a future reviewed main stage to inspect only:

- GitHub Actions metadata, secret-redacted job logs and secret-free artifacts.
- Service availability, deployment metadata, application/request logs and CPU, memory and HTTP metrics for the exact failure windows of qookey-binance-transport-v0-5 in Frankfurt.
- Current Repository relay code and V0.12 authority/config files.

Any recorded evidence must preserve timestamps and redact secrets and raw provider payloads. An observed failure must remain separate from an inferred cause.

## Explicitly outside scope

This review does not authorize Render deploy, restart, rollback, scaling, keepalive, warmup, plan, region, billing, endpoint, workflow or cron changes. It does not authorize reading, changing, rotating or requesting secrets; V0.12 manual dispatch or reruns; provider calls; R2 access; source switching; holdout access; strategy/model/risk changes; trade plans; or orders.

## Decision gate

If direct logs identify an application or upstream failure, a separate versioned remediation authority must name the exact files/service action, expected behavior, rollback, validation and expiry. If logs only preserve a cold-start hypothesis, the only allowed outcome is continued natural-schedule observation. A successful later scheduled run does not repair, backfill or regrade the frozen V0.12 window.

Config: config/render_relay_502_remediation_review_v0_1.json  
Config SHA-256: e17916ac451778811131454ed303d414b42bf3effe6f93be86d02ef470a4f332  
Prepared receipt: research/receipts/2026-09-10-render-relay-502-remediation-review-v0-1-prepared.json
