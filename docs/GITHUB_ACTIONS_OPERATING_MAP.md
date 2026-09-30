## Cloud Paper 工程與狀態接線 — 2026-09-30

查核 basis main：`095aba2c80b9ad710523875b1f45381646e61b75`，時間：`2026-09-30T05:53:15Z`。此 SHA 是修改前的證據基準；合併後仍須重新解析 main。以下舊查核段落保留為歷史，不取代本節。

- 完整目標與執行順序已由 [PR #652](https://github.com/qookey109-pixel/crypto-autopilot/pull/652) 合併至 [交付目標](CLOUD_PAPER_SHORT_TERM_DELIVERY_V0_1.md)。本次查核 open PR = 0；#644 已關閉且未合併，舊六個 dependency PR 不再是目前清單。
- basis main [CI 36667740375](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36667740375) Python 3.12/3.13 成功；3.13 為 1,855 tests / 996 subtests，required Ruff 成功。type visibility = 42 diagnostics（protected 18 / cleanup 24），nonblocking；261 / 33 為歷史基準。
- 本批將 Dashboard JSON、前端 renderer、static validator 及回歸測試同步至 V0.3，保留 V0.2 讀取。完整 run/attempt/head/artifact/digest 必須一致；區分投影查核時間與來源快照，不把部分 bucket bytes 當完整帳戶用量。雲端 CI、合併及新部署須各自取得本批證據，不能沿用舊 Pages 當作本批部署成功。
- V0.3 run **36593296360**：一個 returned bucket、16,304 objects、616,541,780 bytes；operations 125,309 次且 freshness UNKNOWN。D1、全帳戶 inventory/writers、費用與 headroom UNKNOWN。Billing 36513941565、Usage V0.1/V0.2、R2 Usage V0.3 及 bootstrap 已消耗，**禁止重跑**。
- 正式 activation=false、cycle=NOT_RUN、entrypoint=NOT_WIRED、natural schedule=NOT_CONFIGURED；registry 空、模型 REJECT、market context REGIME_UNAVAILABLE。尚未執行不能稱為正式 NO_TRADE。
- **下一批直接處理成本/freshness/保存增長與 ledger 自身費用可行性，再完成 budget/persistence/production 接線。** 不再另起獨立文件整理；外部查詢、provision、migration、寫入與 schedule 須先有精確新版本 authority 合併 main。七天等待與 10/1 額外人工時點不恢復，runtime expiry guard 保留。
- 全程 CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER、0 USD、PAPER/LIVE-PAPER ONLY；holdout、source switch、promotion、實盤關閉。 frozen 證據保持原樣。

### 歷史查核紀錄（依原日期與 SHA 解讀）

## Cloud Paper live checkpoint — schedule is not activation — 2026-09-30 10:50 Asia/Taipei

Evidence basis：main `31831113d6997779ee18fe8ee4d5eb67390855a2`（PR #647 合併提交）。以下是該 SHA 的查核快照，不宣稱更新文件合併後的 main SHA 或 checks。

- PR [#647](https://github.com/qookey109-pixel/crypto-autopilot/pull/647) 已合併。PR head `7b957c496782ad2f46aa08c436b6766c0816ecff` 的 CI run [36660991269](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36660991269)、CodeQL [36660991267](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36660991267)、Dependency/SBOM [36660991326](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36660991326) 均成功。對 merge SHA 的 combined status 未回傳 entries；post-merge 狀態為 `UNKNOWN_NOT_VERIFIED`。
- PR [#644](https://github.com/qookey109-pixel/crypto-autopilot/pull/644) 已關閉且未合併。其 head `3785d4e91a65e7fa870b7c2e4520eb5c10adccb2` 基於 `50cfd7ec4a23ef159bdc02df7fd7cdd2e1da13e1`，落後 main；CI、Dashboard snapshot、SBOM、CodeQL、Pages 的 exact-head runs 均為 `action_required`，不能當作通過。變更是過時的自動維護快照，保留 PR 歷史、不把它覆蓋到 main。
- Cloud Maintenance run [36648016165](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36648016165)：inspect／propose 成功；propose log 為 `NO_CHANGE`、`commits_created=0`，資料基準 SHA 是 `50cfd7e`。這證明該舊基準無文件變更，**不算最新 main 的自然驗收**。
- Pages run [36648016160](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36648016160) 的 build、deploy、production browser 成功，head 也是 `50cfd7e`。故它是可用的舊版部署證據，不是 PR #647 之後的新部署；PR #647 僅文件變更。
- Health run [36620936304](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36620936304) 成功，artifact [11057933924](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36620936304) 保留；其證據 head 為 `50cfd7e`。Cloud Paper activation 仍 `false`，正式循環／自然 Paper schedule `NOT_RUN / NOT_ESTABLISHED`；正式策略 registry 空、Core100 `REJECT`、macro `REGIME_UNAVAILABLE`。
- Billing V0.1、Usage V0.1／V0.2、R2 Usage V0.3 一次性權限均已消耗，不可重跑。帳戶零費用、D1 用量、完整 R2 bucket/writer 覆蓋與 headroom 仍 `UNKNOWN`。不呼叫 Cloudflare、不 provision／write、不訓練、不改排程。

接續順序：先合併本次狀態同步並回讀 main；之後完成預算可行性與資料缺口決策、Dashboard V0.2/V0.3 相容、共享預算／恢復及完整雲端 CI，達標後才評估新的版本化外部證據及受控 PAPER gate。Pionex observability 現行 authority 的到期時間是 2026-10-01 08:00 台北；到期前後均不得自動延長或補跑歷史 slot。

---

# GitHub Actions operating map

## Cloud Paper R2 Usage Audit V0.3 — consumed (2026-09-30)

Zero-network [readiness run 36592944801](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36592944801) reported `READY`. One-time [audit run 36593296360](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36593296360), attempt 1 on `2516a80c32fa04b9789bef379b108eb50c87fd49`, reported `READY_FOR_REVIEW / R2_METRICS_CAPTURED_REVIEW_ONLY` after exactly one accepted Cloudflare GraphQL request. The V0.3 authority is consumed; **never dispatch or rerun it again**. Preserve the [result receipt](../research/receipts/2026-09-29-cloud-paper-r2-usage-audit-v0-3-result.json).

The result is partial R2 analytics evidence. Billing/zero cost, D1 inventory/use, complete bucket inventory, shared-account writers, and headroom remain unproven. Cloud Paper activation and runtime scheduling remain disabled. Any further external evidence collection requires a separate versioned scope merged to main.

## Cloud Paper V0.1 / V0.2 manual diagnostics — historical and consumed

Billing V0.1 run `36513941565`, Usage Audit V0.1 run `36558934727`, and Usage Audit V0.2 run `36584465739` are consumed one-time executions. Keep their original success/failure reports. Do not dispatch or rerun them. Their zero-network readiness workflows do not renew execution authority. The [V0.2 protocol](CLOUD_PAPER_USAGE_AUDIT_V0_2.md) describes the historical contract, not a new permission to execute.

Navigation snapshot: 2026-09-23, observed against main `87ad32fd8f29a0c34bbf61ad11694fe4ef29df51`. Resolve main and Actions live before acting. This map is not execution authority and does not add schedules, dispatches or provider/R2 permissions.

For the separate Codex check cadence, shared evidence fields and model handoff procedure, see the [continuation runbook](PROJECT_CONTINUATION_RUNBOOK.md).

## What the numbers mean

GitHub's paginated workflow API returned **108 registrations**: **82 workflow files present on main**, **25 registrations whose files are absent from main**, and **1 dynamic Dependabot Updates** entry. Every registration reported `active` at observation time; that API state does not imply a schedule, a currently valid execution window or authorization.

At the 2026-09-26 review against main `25537c61b051d31002a576ec16bcb4a38aab9c31`, the source tree contains **84 workflow files**: the September 23 baseline of 82 plus the Cloud Maintenance completion listener and `security-visibility-dependencies.yml`. The historical 108-registration counts below are a 2026-09-23 snapshot, not current state.

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

### Event-driven engineering tool schedule

These checks are cloud-executed by event-driven GitHub Actions workflows. They are **not cron jobs** and do not count toward Research Automation Health schedule coverage or the 2026-09-27 natural Pionex / Weekly Training acceptance evidence.

| Tool | Trigger | Mode / evidence |
| --- | --- | --- |
| actionlint `1.7.12` + ShellCheck | Pull requests; only changed workflow YAML files are linted | Blocking `workflow-static` PR validation. The actionlint binary is checksum-verified before use. |
| pip-audit `2.10.1` | Dedicated `security-visibility-dependencies.yml` on every pull request and every push to `main` | Informational / non-blocking dependency security visibility. Audits the pinned installed runtime set, emits CycloneDX JSON plus the frozen audited requirements list, and retains the artifact for 30 days. No automatic dependency fix or update is authorized. |

This event-driven schedule adds no provider, R2, holdout, model, source-switch, deployment or trading authority. A vulnerability finding is evidence for dependency review; it does not authorize automatic remediation or merge. PR #512 merged the dependency-security workflow on main `25537c61`; post-merge run `36214047453` succeeded and uploaded artifact `10896777315` (digest `sha256:cd4709f02c413289a6058e7f6365d0f1eedf8c87c903ece232e6655abfede14c`, 30-day retention).
## Event chains and CI

- Research Signal Layer V0.2 completion can trigger Signal Quality, subject to same-repository main/success lineage checks. Quality retains its daily fallback and exact-evidence deduplication.
- Pages listens to selected upstream workflow completions as well as relevant pushes and its daily fallback. Each run must satisfy the workflow's explicit event filters. PR builds do not deploy.
- Pages PR #478 shares one production concurrency group with `queue: max`, `cancel-in-progress: false` (up to 100 pending runs). Deployment rechecks current main SHA and content hash; production browser checks run after a real deployment.
- CI, CodeQL and Freeze Guard are engineering checks. Workflow success, deployment success, schedule health and research acceptance are separate claims. Non-blocking type/security visibility does not become a required gate through this map.
- Dependabot is review-only; the historical dependency batch is recorded in [September 22 triage](OPEN_PR_TRIAGE_2026_09_22.md).

## Manual and historical workflows

A workflow_dispatch declaration means a manual entrypoint exists; it does not authorize using it. Live Paper coordinator/recovery stay manual and bounded. Completed one-shot ZEC development does not become rerunnable. Historical frozen proof workflows remain validation-only. See [PROJECT_STATUS.md](../PROJECT_STATUS.md#retired-historical-workflow-inventory) and the exact receipt before any action.

The 25 entries below were API registrations with no corresponding workflow file on the observed main at the 2026-09-23 snapshot. They are distinct from the 17 retired validation workflows still preserved in source. As recorded in PR #497, all 25 removed-file registrations were disabled through the GitHub UI on 2026-09-25 and individually read back as disabled; run history was preserved. This is dated evidence and does not replace a new live check. Preserve history and do not re-enable automatically. The dynamic `dynamic/dependabot/dependabot-updates` entry is excluded.

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


## Removed registrations disabled (2026-09-25)

On main `f9296aca33858c907b42e825db8a9d334df1986e`, all 25 listed `.github/workflows/<path>` files were rechecked through the Repository Contents API and returned 404. The authorized GitHub Actions UI operation was then applied to each exact registration ID in the table. Each workflow showed `Disable workflow` before the change, returned `Workflow disabled successfully.`, and showed `Enable workflow` afterward. Result: **25/25 disabled and read back**. No workflow source file or run was deleted; existing run history remains available. The dynamic Dependabot registration and the 17 source-preserved retired workflows were not changed.

## Verification order

1. Re-resolve main, then inspect the exact natural schedule event/run and head SHA.
2. Check queue/build/deploy/browser conclusions separately; a skipped job is not a successful execution of that job.
3. Check the subsequent Health result and its evidence. Keep a missing/delayed slot visible instead of relabeling push or workflow_run as schedule success.
4. Before altering cadence, collect at least seven days of schedule metadata, including missing observations and nominal-slot ambiguity. Run count alone does not prove provider/R2 usage or cost.
5. Keep existing versions and expiry gates. New runtime scope or a successor window requires its exact versioned authority.
