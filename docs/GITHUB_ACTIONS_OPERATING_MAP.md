# GitHub Actions operating map

Navigation snapshot: 2026-09-23, observed against main `87ad32fd8f29a0c34bbf61ad11694fe4ef29df51`. Resolve main and Actions live before acting. This map is not execution authority and does not add schedules, dispatches or provider/R2 permissions.

For the separate Codex check cadence, shared evidence fields and model handoff procedure, see the [continuation runbook](PROJECT_CONTINUATION_RUNBOOK.md).

## What the numbers mean

GitHub's paginated workflow API returned **108 registrations**: **82 workflow files present on main**, **25 registrations whose files are absent from main**, and **1 dynamic Dependabot Updates** entry. Every registration reported `active` at observation time; that API state does not imply a schedule, a currently valid execution window or authorization.

At the 2026-09-25 review, the cloud maintenance completion listener is a new non-cron workflow, bringing the main-source inventory to 83 after its merge. The historical 108-registration counts below are a 2026-09-23 snapshot, not current state.

Among the 82 source workflows, 55 declare workflow_dispatch (32 are manual-only), 42 declare pull_request, 9 push, 3 workflow_run and 8 schedule. Event types overlap. The eight schedule files contain 11 cron expressions; seven are current-effective inside their versioned windows, while V0.12 is expired.

## Scheduled operations

Nominal times below are Asia/Taipei (UTC+8), not an execution-time guarantee.

| Workflow | Nominal time | Scope / expiry |
| --- | --- | --- |
| [Resource Hub V0.2](../.github/workflows/resource-hub-supply-chain-v0-2.yml) | Daily 09:13 | Governed read-only supply-chain watch |
| [Research Signal V0.2](../.github/workflows/research-signal-layer-v0-2.yml) | Daily 10:17 | Existing versioned signal scope |
| [Signal Quality V0.1](../.github/workflows/research-signal-quality-v0-1.yml) | Daily 10:47 + upstream completion | Read-only lineage/freshness check |
| [Health V0.2](../.github/workflows/research-automation-health-v0-2.yml) | Even hours at :57 | Actions metadata health |
| [Cloud Maintenance V0.1](../.github/workflows/cloud-project-maintenance-v0-1.yml) | After Health completion; no cron | Same-repository natural schedule only; after reviewed merge, fixed metadata checks and two documentation blocks / one draft PR |
| [Pages](../.github/workflows/dashboard-github-pages.yml) | Daily 12:43 + relevant events | Build; deploy only changed/fresh content |
| [Core100 Training](../.github/workflows/binance-usdm-detailed-training-v0-1.yml) | Sunday 12:37 | Fingerprint match returns NO_CHANGE without retraining/R2 write |
| [Pionex alternative observability](../.github/workflows/pionex-alternative-assets-observability-v0-2.yml) | Sep 4 10:53; Sep 6/13/20/27 11:53 | Metadata-only; expires Oct 1 08:00 Taipei; no automatic extension |
| [V0.12 successor metadata](../.github/workflows/provider-equivalence-v0-12-successor-metadata-capture.yml) | Historical bounded September window | EXPIRED; preserve frozen declaration and fail-closed window gates |

Authority references: [Operations V0.5](../config/github_automatic_research_operations_v0_5.json), [Health V0.2](../config/research_automation_health_v0_2.json), and each workflow's exact versioned contract. [Schedule projection V0.1](../config/automation_schedule_projection_v0_1.json) is derived navigation only.

## Event chains and CI

- Research Signal Layer V0.2 completion can trigger Signal Quality, subject to same-repository main/success lineage checks. Quality retains its daily fallback and exact-evidence deduplication.
- Pages listens to selected upstream workflow completions as well as relevant pushes and its daily fallback. Each run must satisfy the workflow's explicit event filters. PR builds do not deploy.
- Pages PR #478 shares one production concurrency group with `queue: max`, `cancel-in-progress: false` (up to 100 pending runs). Deployment rechecks current main SHA and content hash; production browser checks run after a real deployment.
- CI, CodeQL and Freeze Guard are engineering checks. Workflow success, deployment success, schedule health and research acceptance are separate claims. Non-blocking type/security visibility does not become a required gate through this map.
- Dependabot is review-only; the historical dependency batch is recorded in [September 22 triage](OPEN_PR_TRIAGE_2026_09_22.md).

## Manual and historical workflows

A workflow_dispatch declaration means a manual entrypoint exists; it does not authorize using it. Live Paper coordinator/recovery stay manual and bounded. Completed one-shot ZEC development does not become rerunnable. Historical frozen proof workflows remain validation-only. See [PROJECT_STATUS.md](../PROJECT_STATUS.md#retired-historical-workflow-inventory) and the exact receipt before any action.

The 25 entries below are API registrations with no corresponding workflow file on the observed main. They are distinct from the 17 retired validation workflows still preserved in source. All 25 removed-file registrations were disabled through the GitHub UI on 2026-09-25 and individually read back as disabled; run history was preserved. PR #497 records the change. This dated evidence does not replace a new live check. Preserve history and do not re-enable automatically. The dynamic `dynamic/dependabot/dependabot-updates` entry is excluded.

| Workflow ID | Removed main path under `.github/workflows/` |
| --- | --- |
| 336906612 | `binance-funding-cadence-diagnostic.yml` |
| 337137959 | `binance-funding-r2-cadence-diagnostic.yml` |
| 337135578 | `binance-funding-r2-preflight.yml` |
| 336101880 | `binance-history-probe.yml` |
| 361014554 | `bitget-macd-zec-binance-vision-readonly-v0-2.yml` |
| 361005403 | `bitget-macd-zec-real-readonly-v0-1.yml` |
| 358459967 | `core100-threshold-sweep-replay-v0-1.yml` |
| 358440452 | `core100-training-reject-diagnosis-v0-1.yml` |
| 337161619 | `dashboard-cloudflare-temporary-preview.yml` |
| 337197514 | `dashboard-cloudflare-zh-hant-latest-preview.yml` |
| 337191590 | `dashboard-cloudflare-zh-hant-preview.yml` |
| 337430992 | `dashboard-cloudflare-zh-redeploy-preview.yml` |
| 358937858 | `dashboard-current-operations-v0-2.yml` |
| 337481003 | `diagnose-binance-usdm-runner-transport-matrix.yml` |
| 337444504 | `diagnose-equivalence-runs.yml` |
| 337205959 | `diagnose-funding-v0-2-materialization-run.yml` |
| 337434886 | `diagnose-pages-main-run.yml` |
| 337221087 | `diagnose-r2-bucket-usage.yml` |
| 337478343 | `diagnose-v0-2-cloudflare-binance-transport.yml` |
| 337476507 | `diagnose-v0-2-metadata-main.yml` |
| 336920073 | `hype-funding-edge-diagnostic.yml` |
| 337664273 | `one-time-check-cloudflare-secret-presence.yml` |
| 336107067 | `pionex-binance-compare-v2.yml` |
| 336105935 | `pionex-binance-compare.yml` |
| 358982435 | `quality-visibility.yml` |

## Verification order

1. Re-resolve main, then inspect the exact natural schedule event/run and head SHA.
2. Check queue/build/deploy/browser conclusions separately; a skipped job is not a successful execution of that job.
3. Check the subsequent Health result and its evidence. Keep a missing/delayed slot visible instead of relabeling push or workflow_run as schedule success.
4. Before altering cadence, collect at least seven days of schedule metadata, including missing observations and nominal-slot ambiguity. Run count alone does not prove provider/R2 usage or cost.
5. Keep existing versions and expiry gates. New runtime scope or a successor window requires its exact versioned authority.
