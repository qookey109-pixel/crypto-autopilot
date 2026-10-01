## Cloud Paper — #665 保存精簡合併後狀態（2026-10-01）

查核基準 main：`bbd3cccf2841219104cffef46ad2d5aa9ff87648`。PR [#665](https://github.com/qookey109-pixel/crypto-autopilot/pull/665) 已合併；修復後 head `49e27a3257f9163c9c39e996b57ca850af273f9f`。PR CI [36726001018](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36726001018)：Python 3.12／3.13 通過，Ruff 通過（1,638 tests），CodeQL [36726000835](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36726000835)、SBOM [36726000872](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36726000872) 通過。合併 main CI [36726499079](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36726499079) 的兩個 Python jobs 成功、workflow-static skipped；CodeQL [36726499004](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36726499004)、SBOM [36726499003](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36726499003)、Freeze Guard [36726499085](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36726499085) 成功。

- #665 將 step tick evidence 改為以 ID 與完整摘要引用獨立 immutable tick；保留舊 frozen coordinator/recovery V0.1 及舊資料讀取，增加 V0.3/V0.2 successor。舊 tick 缺失時恢復診斷回歸亦已修復。
- 同一合成 entry／exit／no-trade fixture：#661 為 157,367 bytes，#665 為 116,608 bytes，減少 40,759 bytes（約 25.9%）；相較 #658 的 206,181 bytes，累計減少約 43.4%。profile artifact：[run 36726001018](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36726001018/artifacts/11101819985)。物件數仍為 26；介面讀取計數依 fixture 不變。這是合成 canonical JSON/store-interface 量測，不代表 R2 實際 bytes、費用或帳戶 headroom；successor verification 是否增加真實 R2 read/write 成本仍待 production-equivalent evidence。
- Main push Pages [36726499028](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36726499028) 僅 build 成功，deploy/browser-production skipped；其後自然 Health 觸發 Pages [36795028772](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36795028772)，build、deploy、browser-production 均成功。
- 自然 Health [36767233711](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36767233711) 與 [36794986771](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36794986771) 均成功；各自 Maintenance 的 inspect 成功、propose 因 `MAIN_CHANGED` 失敗：[36767360524](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36767360524)、[36795028849](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36795028849)。過時 PR #664 已關閉保留歷史；目前待下一次自然 Health → Maintenance 以 current main 產生新 evidence snapshot。
- 已核對正式策略時間框為 market context 4H、setup 60M、entry 15M；目前 `cloud_market_v0_1.py` 只抓 60M，因此另兩個 frame 尚未接入。Pionex 官方 [Klines API](https://pionex-doc.gitbook.io/apidocs/restful/markets/get-klines) 列有 15M、60M、4H，單次 limit 上限 500；這證明端點支援，不等於本專案已驗證可用或已授權呼叫。Breadth 合約另要求固定 23 市場，membership coverage 仍未驗證；現有 capture 最多選 5 市場。TOTAL3／BTC dominance 仍缺具名、時間對齊、條款與費用可接受的來源。未做 provider request，source switch 與正式策略 gate 不變。
- Cloud Paper 仍 disabled／NOT_RUN／NOT_WIRED／NOT_CONFIGURED；D1 未 provision、正式 registry 空、Core100 品質 REJECT。帳戶級費用、R2/D1完整 writer coverage、用量 freshness、headroom 與資料來源缺口仍未解決。一次性 Billing／Usage／bootstrap 不重跑；holdout、source switch、promotion、實盤保持關閉。
- 下一步：完成可刷新且能涵蓋所有 writers 的零費用／額度證據與最小保存成本核算；逐欄確認策略所需即時資料、暖機及持倉期間事件完整性；再接通正式 PAPER 入口並用雲端 CI 驗證交易、不交易、拒絕、重播與恢復。達標前不啟用模擬排程。

CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER；0 USD；PAPER／LIVE-PAPER ONLY。

## Cloud Paper Historical Checkpoint — 2026-09-30 (#662 merged)

Historical evidence basis: GitHub `main=919941f2f8d8db77b0bc8372727de46d8406867f`; open PRs at that checkpoint = 0. This is the snapshot after #662, not a permanent latest-main claim. Resolve GitHub main at read time.

- #661 delivered the prepared V0.2 compact loop-report reference. The matched synthetic three-slot profile is 26 objects and 157,367 canonical JSON bytes, 48,814 bytes (~23.7%) below the #658 baseline. This does not establish production R2 usage, charges, or account headroom.
- #662 synchronized status and storage-lineage documentation. Cloud Paper remains disabled; production cycle NOT_RUN; entrypoint NOT_WIRED; natural schedule NOT_CONFIGURED; D1 unprovisioned; production strategy registry empty; Core100 quality REJECT.
- Account-wide zero-cost evidence, usage freshness, complete writer coverage, and D1/R2 headroom remain unproven. Consumed one-time Billing/Usage/bootstrap authorities must not be rerun. No provider/D1/R2 access or runtime/schedule activation occurred.
- Next: assess a compatible `live-run-step` to `live-tick` reference format, retaining old-schema reads, hash lineage, continuation, recovery, replay, and fail-closed partial-write diagnosis; verify public-data gaps and official source terms.
- Boundaries remain CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER, 0 USD/month, PAPER/LIVE-PAPER ONLY. Holdout, source switch, promotion, real-money orders, and live trading stay closed.

## Cloud Paper Current Checkpoint — 2026-09-30 20:44 Asia/Taipei

Evidence basis: GitHub `main=4b12f0c9ad508e09d712320111f2e12423b69aca`; no open PRs. Cloud Paper remains disabled.

- PR #660 completed the writer/reader/recovery lineage inventory. PR [#661](https://github.com/qookey109-pixel/crypto-autopilot/pull/661) merged the prepared V0.2 compact report reference at `ebf812426dffb0e600fdcb2dcabf05e3f3642be6`. PR Python 3.12/3.13, Ruff, workflow-static, CodeQL and Dependency/SBOM checks passed.
- Post-merge main CI [36716389946](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36716389946), CodeQL [36716389968](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36716389968), Dependency/SBOM [36716389930](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36716389930) and Freeze Guard [36716390111](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36716390111) passed. Main-push workflow-static skipped; Pages did not run because no website files changed.
- The same synthetic three-slot entry/exit/no-trade fixture decreased from 206,181 to 157,367 canonical JSON bytes (48,814 bytes / about 23.7% less); object count remains 26. The `cloud-report` aggregate decreased from 70,352 to 21,538 bytes. See [#658 baseline artifact](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36710655801/artifacts/11094147043) and [#661 profile artifact](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36716119165/artifacts/11095802879). These are synthetic serialized sizes, not production R2 usage, charges, or account headroom.
- V0.2 reports reference the persisted `live-run-step` by `step_id`; legacy embedded V0.1 reports remain readable in tests. No production object migration, provider/D1/R2 call, runtime activation, or schedule change occurred.
- Cloud Paper activation=false; production cycle NOT_RUN; entrypoint NOT_WIRED; natural schedule NOT_CONFIGURED; D1 unprovisioned; production registry empty; Core100 quality REJECT. Account-wide zero-cost, usage freshness, all-writer coverage, and headroom remain unproven.
- Next work: assess safe `live-run-step` → `live-tick` reference minimization with legacy/recovery/hash/partial-write coverage, and reconcile missing public-data fields against official sources and acquisition terms. No Binance-to-Pionex relabeling or source-switch bypass.
- Boundaries remain CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER, 0 USD, PAPER/LIVE-PAPER ONLY. Holdout, source switch, promotion, real-money orders and live trading stay closed. Do not rerun consumed one-time Billing/Usage/bootstrap authorities or rewrite frozen evidence.

## Cloud Paper Current Checkpoint — 2026-09-30 19:52 Asia/Taipei

Evidence basis：PR #658 合併後 main `7424ccfbaf0362f588410de037e593f0105745a0`；open PRs at checkpoint = 0. The synthetic profile below is not production/R2 usage, and Cloud Paper remains disabled.

- PR [#658](https://github.com/qookey109-pixel/crypto-autopilot/pull/658) 加入既有合成 fixture 的保存量測與 CI artifact。PR head `75e766a534e29b89be1ab96dce860964bfe66ef8)；PR CI #36710655801、CodeQL #36710655868、Dependency/SBOM #36710655876 成功。合併 main `7424ccfbaf0362f588410de037e593f0105745a0) 的 CI #36710934061、Freeze Guard #36710934128、CodeQL #36710934055、Dependency/SBOM #36710933979 成功；workflow-static 因 main push 而 skipped。Pages 未觸發，因本批未改網站檔案。
- CI artifact [11094147043](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36710655801/artifacts/11094147043)，名稱 `cloud-paper-storage-profile-36710655801-1`，2,671 bytes。每個 fixture 皆通過既有斷言；報告標示 `SYNTHETIC_ENGINEERING_ONLY)、provider/R2/D1 requests=0。
- 合成不交易／恢復／結算失敗各為 10 objects、33,433 canonical JSON bytes；重播／重啟為 18 objects、59,327 bytes；合成入場→出場→下一輪不交易為 26 objects、206,181 bytes（3 個 slot）。後者按類別：cloud-report 70,352 bytes、live-run-step 48,778、live-tick 40,714、live-state 39,310；合計 199,154 bytes，屬優先檢查的高佔比類別。這只是大小 profile；尚未證明內容可互相替代，也未確認所有 production readers／恢復契約。
- 上述 byte 數由現有記憶體測試 store 的實際 canonical JSON 序列化計算；不含 R2 metadata、外部 writers、D1、服務端條件寫入檢查或真實帳戶 headroom。gzip 僅估算，不能當作已壓縮或節費。不得據此推算已降低 production 儲存量。
- 下一步：盤點四大類物件的 writers、readers、immutable/hash lineage 與 restart/partial-write dependencies；先證明可用引用取代重複 payload，再做版本相容的最小保存修正及同一 CI 前後比較。Cloud Paper activation=false、正式循環 NOT_RUN、entrypoint NOT_WIRED、natural schedule NOT_CONFIGURED；D1 未 provision、registry 空、Core100 品質仍為 REJECT。零費用與全帳戶 headroom 仍須以獨立 evidence 證明。
- 維持 CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER、0 USD、PAPER/LIVE-PAPER ONLY；holdout、source switch、promotion、真實下單與 live trading 維持關閉。不得重跑已消耗的一次性 Billing/Usage/bootstrap authority，也不得改寫 frozen evidence。

## Cloud Paper Current Checkpoint — 2026-09-30 15:06 Asia/Taipei

Evidence-basis live main before this docs PR: `c9e220cb6f2191e6fb0dd50a5918a62971360e8e`; open PRs = 0. Re-read main after merge.

- PR #654 merged D1 post-admission evidence freshness/UTC-day revalidation. PR CI #36680835582, CodeQL #36680835575 and Dependency/SBOM #36680835567 passed. Post-merge main CI #36681001425, Freeze Guard #36681001474, Dependency/SBOM #36681001359 and CodeQL #36681001327 passed.
- D1 remains unprovisioned; migrations are prepare-only. No production Cloud Paper cycle or Cloudflare runtime call was performed by PR #654.
- Most recent Pages deployment evidence: run #36676578296 on main `89dd07a26ebad0d780b009eb5051b16d53fe75e6`; build, deploy, browser-production passed, 42 desktop/mobile checks. PR #654 changed no Pages inputs.
- Natural Health #36676258650 succeeded. Triggered Maintenance #36676302904 stopped at propose with `OBSERVATION_CHANGED`; classify as safe stop, not PASS or NO_CHANGE.
- R2 V0.3 run #36593296360 remains a consumed one-time partial analytics snapshot. It reports one bucket, 16,304 objects, 616,541,780 bytes; 125,309 aggregated operations without a timestamp. Full resource/writer inventory, D1 usage, metered charges, freshness, headroom and zero cost remain UNKNOWN. Do not rerun consumed Billing/Usage/bootstrap authorities.
- Cloud Paper activation=false; production cycle NOT_RUN; entrypoint NOT_WIRED; natural schedule NOT_CONFIGURED; registry empty; Core100 model quality REJECT; macro regime unavailable.
- Ordered objective and completion criteria: [Cloud Paper delivery goal](docs/CLOUD_PAPER_SHORT_TERM_DELIVERY_V0_1.md). First synchronize state; then decide cost/freshness/storage feasibility without repeating consumed audits; only after a bounded successor authority and evidence can controlled PAPER acceptance and natural scheduling proceed.
- Open issues #224 and #111 require relevance/staleness reconciliation against live authority before closure or reopening; issues do not authorize execution.
- Boundaries: CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER, 0 USD, PAPER/LIVE-PAPER ONLY; holdout, source switch, promotion, real-money orders and live trading remain closed.

### Historical checkpoints (preserved below)

### 歷史查核紀錄（依原日期與 SHA 解讀）

# Project Status

## Cloud Paper R2 Usage Audit V0.3 result (2026-09-29)

Evidence-basis main: `2516a80c32fa04b9789bef379b108eb50c87fd49`; this records the audit authority and code SHA. `CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER`.

- Zero-network readiness [run 36592944801](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36592944801) passed `READY` with Cloudflare requests=0 and boolean-only configuration checks.
- One-time V0.3 [run 36593296360](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36593296360), attempt 1 on this main, succeeded at the workflow level and reported `READY_FOR_REVIEW / R2_METRICS_CAPTURED_REVIEW_ONLY` after exactly one accepted Cloudflare GraphQL request. [Artifact 11045150561](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36593296360/artifacts/11045150561) is 1,126 bytes with digest `sha256:581514f59892b84520e52ef463e00210e4175952cc0d54af7fda42b18c71c1be`; its safe result receipt is [here](research/receipts/2026-09-29-cloud-paper-r2-usage-audit-v0-3-result.json).
- The 30-day R2 operations aggregation returned 6 action-type groups and 125,309 requests; freshness is unknown because the query omits datetime. R2 storage returned 1,298 groups. The latest-per-returned-bucket aggregate represents one returned bucket: 16,304 objects, 616,541,780 total bytes (612,538,247 payload + 4,003,533 metadata), zero uploads; latest snapshot 2026-09-29 15:20 UTC.
- This is partial R2 analytics evidence only. D1, invoices/metered billing, zero cost, complete bucket inventory, shared writer coverage, and headroom remain unknown. The 8 GB ceiling is not a headroom measurement. V0.3 authority is consumed and must never be rerun. Cloud Paper remains disabled; FREE-ONLY / 0 USD and PAPER/LIVE-PAPER-only boundaries remain in force.
- Next: prepare any further D1/billing/inventory evidence as a separate least-privilege, versioned stage; do not broaden the current read token or infer activation from this run.

## Cloud Paper Usage Audit V0.2 result (2026-09-29)

Evidence-basis parent main: `21d37a44c6f3c5bba340908705488a05e7a5f7c7`; resolve live `main` before further action. `CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER`.

- Zero-network V0.2 readiness [run 36584082320](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36584082320), attempt 1 on that main, passed: Account ID Secret and Variable both present and matching, read-only token Secret present, Cloudflare requests 0. This proves configuration parity only.
- One-time V0.2 [run 36584465739](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36584465739), attempt 1 on the same main, returned `REVIEW_REQUIRED / DATASET_COVERAGE_INCOMPLETE` after exactly one Cloudflare GraphQL request. Job summary and [artifact 11041290995](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36584465739/artifacts/11041290995) (digest `sha256:9ece6ff0a937f930d1137b2539052833bb5d94960dff8c1e50cce4cdbdadc258`) record: D1 rows `EMPTY_UNVERIFIED / 0`, D1 storage `EMPTY_UNVERIFIED / 0`, R2 operations `LIMIT_REACHED / 10000`, R2 storage `PRESENT / 1297` groups. Report upload succeeded despite the expected workflow failure.
- The empty D1 datasets are **not** proof of zero D1 usage or no other D1 databases. R2 operations hit the query cap, so no complete operation total or storage-byte aggregate was reported. Account-wide cost, billing charges, external writers and safe headroom remain `UNKNOWN`. Cloud Paper activation, D1 provisioning, writes and natural execution remain disabled. Do not rerun V0.1 or V0.2; both one-time authorities are consumed.
- Immutable safe [result receipt](research/receipts/2026-09-29-cloud-paper-usage-audit-v0-2-result.json) preserves run/attempt/head/artifact identity and the bounded result. Next: design a separate query with R2 operations grouped only by action type, as in Cloudflare's [official R2 example](https://developers.cloudflare.com/r2/platform/metrics-analytics/), and separately prove D1 account inventory and actual billed charges before any activation claim.


## Cloud Paper Usage Audit V0.2 successor authority (2026-09-29)

This change adds a separately versioned V0.2 successor to consumed V0.1. Its config, script, synthetic tests, zero-network readiness workflow, and one-time diagnostic workflow become executable authority only after protected-main merge. At that pre-run checkpoint V0.2 had **not** been dispatched; the later run is recorded above. Run V0.2 readiness first; it requires Account ID Secret/Variable parity and read-only token presence without printing values or making Cloudflare requests. Only a fresh `READY` on current main permits one V0.2 dispatch. Any first dispatch consumes that authority, including a failure; never rerun V0.1 or V0.2.

V0.2 reports per-dataset state and group count for D1 rows/storage and R2 operations/storage. Empty remains `EMPTY_UNVERIFIED`, not zero usage. An HTTP or GraphQL error remains `REVIEW_REQUIRED`. Cloudflare analytics cannot prove invoice charges or all external writers, so `zero_cost_conclusion=UNKNOWN`, Cloud Paper activation, D1 provisioning, writes, and natural execution remain closed. See [V0.2 protocol](docs/CLOUD_PAPER_USAGE_AUDIT_V0_2.md) and `config/cloud_paper_usage_audit_v0_2.json`. `CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER`.


## Cloud Paper readiness and maintenance checkpoint (2026-09-29)

Evidence-basis parent main: `c3096a61b025bd995e6f4fa0e9cea963e302b533`; resolve live `main` before any new action. `CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER`.

- [PR #637](https://github.com/qookey109-pixel/crypto-autopilot/pull/637) separated Account ID Variable and read-only Token Secret presence from API permission, usage evidence, and budget activation. Its first controlled [readiness run #3](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36578030997) failed before any Cloudflare request because the new script had no checkout. That runner log rendered the Account ID variable; preserve the failure evidence without reproducing the value.
- [PR #638](https://github.com/qookey109-pixel/crypto-autopilot/pull/638) added checkout and passes only boolean presence flags into the runner. Controlled [readiness run #4](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36578765856), attempt 1 on `c3096a6`, succeeded: `state=READY`, both configuration-presence flags true, Cloudflare requests 0, API permission `NOT_CHECKED_NO_NETWORK`, usage evidence `NOT_CHECKED_BY_READINESS`, budget activation `NOT_AUTHORIZED_BY_READINESS`. Its log shows presence booleans only. Post-merge CI, CodeQL, Dependency/SBOM and Freeze Guard passed.
- Natural [Health run 36574961612](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36574961612) succeeded. Triggered [Maintenance run 36575038880](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36575038880) had inspect success and propose `MAIN_CHANGED` because old Draft [#633](https://github.com/qookey109-pixel/crypto-autopilot/pull/633) diverged from current main. #633 was closed without merge and its stale delivery branch deleted. This failed Maintenance attempt remains evidence; it is not a completed natural acceptance.
- One-time Billing run 36513941565 and one-time Usage Audit run 36558934727 remain consumed. Usage Audit is still `REVIEW_REQUIRED / DATASET_EMPTY_UNVERIFIED`; account-wide zero cost and headroom are unproven. Cloud Paper activation and natural execution remain disabled. Prepare a separately versioned successor audit with per-dataset completeness before any further Cloudflare query.

## Latest Cloud Paper checkpoint — Usage Audit V0.1 result (2026-09-29)

Reviewed parent main: `f46cba365bd6e43f2c1389b376dda75776178d53`; the SHA records the evidence basis, not the later main after this documentation update. `CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER`.

- **Billing:** readiness [run 36513736040](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36513736040) reported `READY`, with zero Cloudflare requests. One-time subscription snapshot [run 36513941565](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36513941565) succeeded; its secret-free report says one listed `r2_paid` subscription, state `Paid`, listed price total `USD 0.00`. It excludes invoices and metered charges; account-wide zero cost is **not proven**. Preserve run and report; do not rerun.
- **Usage readiness:** [run 36558774279](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36558774279) succeeded on this main with `READY`, zero Cloudflare requests, `one_time_authority_consumed=false`, and `secret_values_printed=false`.
- **Readiness diagnostic:** The zero-network check reports Account ID Variable and read-only Token Secret presence separately. `READY` means configuration names are present only; API permissions, account-wide usage, and budget activation remain unverified by this check.
- **One-time Usage Audit:** [run 36558934727](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36558934727), attempt 1 on main `f46cba365bd6e43f2c1389b376dda75776178d53`, completed with workflow failure because the report status is `REVIEW_REQUIRED`. It made exactly one Cloudflare GraphQL request. Secret-free artifact [cloud-paper-usage-audit-36558934727-1](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36558934727) (420 bytes, digest `sha256:99feaf49cbf2f77df719be926043c8287e5c537a95dc9e2236ef5d7c295e0561`) reports reason `DATASET_EMPTY_UNVERIFIED`, `zero_cost_conclusion=UNKNOWN`, `account_identifiers_persisted=false`, `raw_response_persisted=false`, and `activation=REMAINS_DISABLED`.
- The report's safe reason code does not name which dataset was empty. The reviewed code checks D1 rows, D1 storage, R2 operations, and R2 storage, and returns the same reason if any one is empty; no dataset counts or raw response were retained. Thus the exact empty dataset is **UNKNOWN**. Preserve this failure and do not rerun V0.1; its one-time authority is consumed.
- **Product state:** Cloud Paper remains disabled. The production strategy registry is empty, Core100 quality `REJECT`, macro regime `REGIME_UNAVAILABLE`, D1 unprovisioned, migrations prepare-only, and there is no production execution workflow or natural schedule. Usage and subscription snapshots do not satisfy zero-cost proof, measured headroom, controlled main acceptance, or activation authority.
- **Next engineering step:** prepare a separately versioned successor audit/report that records per-dataset completeness and group counts while keeping account identifiers and raw responses out of artifacts. Validate it synthetically in cloud CI. Any future live query needs its own versioned authority merged to main and fresh readiness; do not rerun the consumed V0.1 workflow.

Maintain `FREE-ONLY / 0 USD`, PAPER/LIVE-PAPER only, and all holdout, source-switch, promotion, real-money, live-trading, and automatic activation gates closed.

---

## Historical checkpoint before Usage Audit V0.1 (2026-09-29)

This update was prepared against main `414cf9a0a3b60612f9d1e09d7c5d29d76b05455e`; the SHA is the reviewed parent, not a claim that it remains latest after this documentation change. Current formal authority remains live `main`. Execution mode: `CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER`.

- **Billing credential setup:** the repository Actions variable `CLOUDFLARE_ACCOUNT_ID` and read-only Billing token are configured according to the user-confirmed GitHub settings state. Billing readiness run [36513736040](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36513736040) reported `READY`, zero Cloudflare requests, and no secret values printed.
- **One-time Billing evidence:** run [36513941565](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36513941565), attempt 1, succeeded on main `414cf9a0a3b60612f9d1e09d7c5d29d76b05455e`; artifact [cloud-paper-billing-evidence-36513941565-1](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36513941565) records `READY_FOR_BILLING_REVIEW`, one listed subscription, and listed subscription price total `USD 0.00` (state `Paid`, rate plan `r2_paid`). The snapshot excludes invoices and all metered charges, so **account-wide zero cost is not proven**. Preserve this run; do not rerun the one-time workflow.
- **Usage evidence:** the user has confirmed the separate read-only Usage token and Account ID variable are configured. The only known Usage Readiness result remains the earlier [run 36471242643](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36471242643), which predates that setup and reported `BLOCKED_MISSING_READ_ONLY_CREDENTIAL` with zero Cloudflare requests. It is stale for the current credential state; latest readiness still needs to be run. The one-time Usage Audit has no run in the reviewed Actions history and remains unconsumed. Run the zero-network [Usage Audit Readiness workflow](https://github.com/qookey109-pixel/crypto-autopilot/actions/workflows/cloud-paper-usage-audit-readiness-v0-1.yml); dispatch the one-time [Usage Audit](https://github.com/qookey109-pixel/crypto-autopilot/actions/workflows/cloud-paper-usage-audit-v0-1.yml) only if that fresh result is `READY`, then preserve its report and never rerun it.
- **Product state:** Cloud Paper activation remains disabled. The production strategy registry is empty, Core100 quality is `REJECT`, macro regime is `REGIME_UNAVAILABLE`, D1 is unprovisioned and migrations remain prepare-only. There is no production execution workflow or natural schedule. Billing and usage snapshots alone do not satisfy budget proof, controlled main acceptance, or implementation-bound activation gates.
- **Open documentation PR:** PR [#633](https://github.com/qookey109-pixel/crypto-autopilot/pull/633) contains a dated Cloud Maintenance snapshot and is not current Cloud Paper evidence; do not merge it as the current status. Its historical evidence must remain intact.

Keep `FREE-ONLY / 0 USD`, PAPER/LIVE-PAPER only. Holdout, source switch, promotion, real-money orders, live trading and automatic activation remain closed.

---

## Status history


Updated: 2026-09-29. Repository main is the current authority.

## Previous billing checkpoint — PR #630 merged (superseded)

Evidence-basis parent main: `e2e4a911b1fa62c35c6e16a3eb4850e68d23f090`; this stored SHA is not a latest-main claim. PR [#630](https://github.com/qookey109-pixel/crypto-autopilot/pull/630) merged a one-time read-only subscription snapshot contract and workflow. PR-head CI [36496143905](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36496143905), CodeQL [36496143925](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36496143925), Dependency/SBOM [36496143898](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36496143898), and retired-workflow guard [36496143862](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36496143862) passed. Post-merge main CI [36496372548](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36496372548), CodeQL [36496372401](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36496372401), Dependency/SBOM [36496372521](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36496372521), and Freeze Guard [36496372302](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36496372302) passed. Main-push workflow-static was skipped because it is PR-only.

The new authority is limited to a single account subscriptions GET with a separate Account Billing Read token. Billing readiness run [36497596228](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36497596228) on main `d4580c1142f9ddadb92cacc810f29bc1988a39df` completed with summary `BLOCKED_MISSING_BILLING_READ_ONLY_CREDENTIAL`; it performed zero Cloudflare requests, printed no secret values, and did not consume the one-time audit. The required credential configuration was unavailable to the run. The separate D1/R2 usage readiness [36471242643](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36471242643) remains `BLOCKED_MISSING_READ_ONLY_CREDENTIAL`, also with zero Cloudflare requests. Neither audit has been dispatched. Subscription prices do not prove invoice totals or zero cost.

Cloud Paper activation remains false. Production strategy registry is empty, Core100 quality is `REJECT`, macro context is `REGIME_UNAVAILABLE`, D1 is unprovisioned, and migrations are prepare-only. No Cloud Paper execution workflow, natural schedule, or controlled main acceptance exists. Account-wide usage freshness, external writer coverage, billing records, and D1 storage calibration remain open. FREE-ONLY / 0 USD, PAPER/LIVE-PAPER only; holdout, source switch, promotion, and real-money trading remain closed.

Updated: 2026-09-29 (the checkpoint above is current; later sections retain dated historical evidence).

## Historical Cloud Paper checkpoint — 2026-09-29 (superseded by current checkpoint)

Product-code evidence basis remains PR #622 merged to main `cb22d3c3905a079eb754f0fab6d917923512f624`. Documentation/status PRs #623–#626 subsequently merged; current main is `9d897b6d4fb7f7c783170c4c3bbf7bcbc4ca1e08`, with no open PRs at this checkpoint. These documentation PRs changed no runtime or authority. PR #624's main CI [36488331170](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36488331170) passed Python 3.12/3.13; CodeQL [36488331191](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36488331191), Dependency/SBOM [36488331181](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36488331181), and Freeze Guard [36488331166](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36488331166) passed. Workflow-static was skipped because no workflow changed.

PR #626 is documentation-only: it merged the post-#625 status refresh at exact head `279a5e56130912506b7c7b43e77815280a69e463` to main `9d897b6d4fb7f7c783170c4c3bbf7bcbc4ca1e08`. Post-merge CI [36490182195](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36490182195), CodeQL [36490182214](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36490182214), Dependency/SBOM [36490182254](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36490182254), and Freeze Guard [36490182675](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36490182675) succeeded. Pages [36490182321](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36490182321) build succeeded; deploy and browser-production were skipped for the documentation-only change. No runtime or authority changed.

PR #625 is documentation-only: it merged the status update to main `5efdc045690b320aed47a68e5ff52f0119f912a0`. Post-merge CI [36489202470](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36489202470), CodeQL [36489202296](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36489202296), Dependency/SBOM [36489202158](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36489202158), and Freeze Guard [36489202435](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36489202435) succeeded. Pages run [36489202281](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36489202281) built successfully; deploy and production-browser jobs were skipped for the documentation-only change, and workflow-static was skipped because no workflow changed.

PR #622 added a CI-only qualified fixture through the same `CloudPaperNoTradeComposition.run_slot` path: entry, exit, account advancement, persistence, then a subsequent `NO_TRADE`. PR #624 documents current CI coverage for no-trade/rejection, invalid data/budget, replay, concurrent reservation, and recovery/partial settlement. This verifies synthetic engineering paths only. Production registry is empty; Core100 quality is `REJECT`; macro regime is `REGIME_UNAVAILABLE`; Dashboard state remains `NOT_RUN`.

PR #618's latest verified Pages build/deploy and 14/14 desktop/mobile browser checks are tied to product commit `6deabddd7f925b6d586b9565a9f6641105a2fd29`. PRs #622–#624 do not modify the Dashboard or its runtime projection.

PR #616 storage envelope: 256 KiB/object, 2 MiB/run, 192 MiB/day and 6,241,124,352 theoretical bytes over 31 days; warning at 6.4 GB and fail-closed at projected 8 GB. This is not measured account usage. Evidence retention remains append-only; deletion is not authorized. Account-wide usage/freshness, all-writer coverage and D1 storage calibration remain unverified.

Activation remains disabled. The latest account-usage readiness [36471242643](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36471242643) is `BLOCKED_MISSING_READ_ONLY_CREDENTIAL`, with zero Cloudflare requests; one-time audit authority remains unconsumed and no newer readiness run exists. D1 is unprovisioned, migrations are prepare-only, no production execution workflow or natural schedule exists, and controlled main acceptance has not run. Configure the Actions account ID variable and read-only token secret out of band; run zero-network readiness, and dispatch the one-time audit only if readiness is `READY`. Keep FREE-ONLY / 0 USD and all research/trading boundaries in force.

Repository `main` is formal authority and must be resolved live at read time. Exact versioned configs, receipts, immutable run evidence, and merged code remain the detailed authority for each scope.

## Current authority semantics

- Repository: `qookey109-pixel/crypto-autopilot`.
- Current Operations companion: `research/status/current-operations-v0-3.json`.
- Current Operations V0.3 stores an **evidence-basis parent SHA**, not a self-referential latest-main claim.
- Evidence-basis parent for this status version: `09dfb0d79b88dc56f3cb582c91d8091617437ce2`, the reviewed main commit after PR #426 merged and passed post-merge CI / Freeze Guard / CodeQL / Pages.
- Current mode: **PAPER / LIVE-PAPER ONLY**. Public live market data and simulated live-paper execution/persistence are separate from real trading authority.
- FREE-ONLY cloud/runtime budget: **0 USD/month**.

For present-tense operations read `CURRENT_STATUS.md` first, then resolve the Repository's live `main`. Dated prose and dashboard fixtures are evidence/projections, not substitutes for live Repository authority.

## Current lifecycle

`History COMPLETE -> Training COMPLETED -> Model Quality REJECT -> Threshold Replay COMPLETED / NO SUPPORTED THRESHOLD CHANGE -> Strategy Validation CLOSED -> Holdout CLOSED -> Promotion CLOSED -> REAL TRADING CLOSED / LIVE-PAPER SEPARATELY AUTHORIZED`

### Core100 History and training

- Detailed Core100 History acquisition is complete: `10/10` governed shards.
- Historical reacquisition is not required solely because the trained model was rejected by quality gates.
- Training run `34918219864`: workflow `success`, report `PASS` (legacy V0.1 baseline).
- The separately authorized Core100 fingerprint V0.2 bootstrap [run `36110721415`](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36110721415) completed on main `41c79994a82a30d938774ff540c97767c0ad01d6`; report status `PASS`, stage `CORE100_FINGERPRINT_V0_2_BASELINE_PUBLISHED`, model-quality gate `REJECT`. It used dataset fingerprint `91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876`, experiment fingerprint `12ff384302785645144832115114a88f726bcc4ce51caa56497bec1209c76ed7`, and runtime guard fingerprint `c6733aab1c4f598ce3f4be36fa1b9058757459d1de4ef7394a4d0568c3d41d79`. The secret-free report artifact is [10860768638](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36110721415/artifacts/10860768638). Three immutable outputs and the latest pointer passed SHA-256 readback; provider requests were zero and holdout was not accessed. The one-time authority is consumed. No promotion, source switch, threshold change, trade plan, order or live trading is authorized.
- 100 symbols; 14,274 dataset partition objects; 18,235,427 rows; 249,228 examples.
- Dataset fingerprint: `91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876`.
- All folds ready: `true`.

Training/pipeline completion is separate from model-quality acceptance.

### Model quality and threshold replay

Current model-quality result: **REJECT**.

Exact read-only replay run `34936331199` completed successfully on the same dataset fingerprint:

- thresholds evaluated: `0.50, 0.51, 0.52, 0.53, 0.54, 0.55`;
- `supported_thresholds=[]`;
- `threshold_change_supported=false`;
- configured threshold remains unchanged;
- automatic model promotion remains disabled.

The replay is diagnostic-only and grants no provider request, R2 write, holdout, promotion, trade-plan, order, or live-trading authority.

## Pionex validation state

Pionex is the final calibration / execution-environment provenance target; Binance USD-M remains the large-scale learning database. The providers remain provenance-separated.

Current workflow: `.github/workflows/pionex-validation-materialization-v0-2.yml`

Repository materialization state: **COMPLETE / PASS**.

- final successful run: `35054729471`;
- run head SHA: `5eaf57133d013fad030681182b379a02d915766e`;
- report stage: `PIONEX_VALIDATION_DATASET_MATERIALIZED_V0_2`;
- selected markets: `197`;
- partitions: `682`;
- provider requests: `1,534`;
- artifact: `10430054351`;
- artifact digest: `sha256:5f8c3406ee5dc9a491cd800241c1cc7e2dd66bc98fa292da1c8bb05535dede55`;
- manifest key: `market-data/pionex/validation-dataset-v0.2/runs/run=github-35054729471-1/manifest.json`;
- manifest SHA-256: `192eddd1c69dd435d2ea12a0bf68e05e1cbc1a0fd512f4321f631755c61ca225`;
- R2 latest pointer written last: `true`;
- completion evidence: `research/receipts/2026-09-16-pionex-validation-materialization-v0-2-completion.json`.

The completed dataset preserves explicit provider-coverage states. It does **not** claim complete 197-market multiyear history, and it did not perform Core100 Pionex training.

The repair lineage remains narrow and provider-native:

- PR #321 preserved bounds-only invalid-candle historical boundaries without repair/fabrication;
- PR #332 introduced V0.2 native `1D -> logical 1W` construction;
- PR #334 preserved explicit `NO_PROVIDER_HISTORY_BEFORE_CUTOFF` zero-history coverage;
- PR #335 preserved explicit provider-latest-before-cutoff trailing coverage without interpolation or splicing;
- PR #337 recorded the successful V0.2 materialization completion evidence.

Authority after PASS remains unchanged:

- public Pionex futures K-lines: authorized only for the governed validation scope;
- R2 validation-dataset writes: authorized only for the governed validation scope;
- private API/account data: unauthorized;
- replacement holdout access: unauthorized;
- training: unauthorized;
- source switch: unauthorized;
- promotion: unauthorized;
- formal real-money trade plan / real-money orders / real live trading: unauthorized.
- public-market-data live-paper simulation is governed separately by `config/live_paper_simulation_v0_1.json` and does not change the validation-dataset authority above.

**Materialization PASS is not Model Quality PASS.** Strategy Validation, Holdout, Promotion, and Trading remain closed because the Core100 model-quality result remains **REJECT** and threshold replay supports no threshold change.

## Technical-debt cleanup

PR #322 merged the first control-plane convergence batch:

- current-operations entrypoint plus machine-readable companion;
- README / PROJECT_STATUS / SECURITY / AGENTS convergence;
- current-main PR triage;
- Research Automation Health count derived from exact Repository schedule inventory rather than a magic `7`;
- first fail-closed Dashboard current-operations overlay implementation.

The control plane must keep present-tense Current Operations later than historical authority/readiness projections, so dated September 13 `8/10 / Training skipped / PR #292` text and older V0.1 Pionex pending-dispatch text cannot return during deployment.

P2 quality/dependency/security visibility is now established through non-blocking Quality Visibility V0.2, non-blocking mypy semantic type visibility, review-only Dependabot proposals, and non-blocking CodeQL SARIF artifacts. The first mypy baseline reported 261 type errors and remains informational only; no type/security threshold is a required gate. Large-module refactoring remains deferred under TD-009.

Tracking: `docs/TECH_DEBT_REGISTER_2026_09_17.md`. Current PR navigation: `docs/OPEN_PR_TRIAGE_2026_09_22.md` / `research/status/open-pr-triage-v0-7.json`.

## Open work that matters now

- Pionex Validation Materialization V0.2 is **COMPLETE / PASS** on run `35054729471`; this closes the materialization task only, not downstream research gates.
- Core100 remains **Model Quality REJECT** and threshold replay still supports **no threshold change**; Strategy Validation, replacement holdout, Promotion and real trading remain closed.
- ZEC MACD V0.2 historical evidence is preserved on current main as **execution PASS / strategy evidence REJECT**. No V0.1/V0.2 reexecution authority was revived.
- ZEC Strategy V0.3 completed its governed one-shot historical development execution: 64 candidates × 4 folds = 256/256 cells. Selection result is **NO_ELIGIBLE_DEVELOPMENT_CANDIDATE**; no champion was frozen. Fresh confirmation, holdout, promotion and trading remain unopened.
- ZEC V0.4 is also complete: 24/24 development cells, **NO_ELIGIBLE_DEVELOPMENT_CANDIDATE**, no champion and no fresh confirmation. See `research/receipts/2026-09-21-zec-v0-4-development-completion-v0-1.json`.
- External Capability Registry candidates have downstream evaluation receipts and a convergence index. Candidate inventory status does not imply runtime approval.
- Operator messaging now has a provider-neutral offline path: parser -> status resolver -> local CLI for `help`, `status` and `paper_status`; no Telegram/network/secret/trading authority is implied.
- The 2026-09-22 triage snapshot recorded a reviewed open pull-request backlog of zero; it is historical. PR #478 merged the Pages queue guard, PR #477 merged the typing cleanup, and PR #479 merged the project checkpoint/runbook as `8ca0962933b18d4607b2f4ad9a3b7588a4f4db25`. The live open-PR query immediately after #479 returned zero; always resolve live GitHub PRs before acting. The #326–#331 dependency batch has been reviewed: #447/#448 merged the compatible current-main action updates, while incompatible/freeze-crossing proposals were closed without merge. Older architecture-generation and draft-salvage PRs remain historical references.

Historical CI success on an old branch is not sufficient merge evidence after main advances. Any newly opened PR must be evaluated against live `main`.

## Binding safety and governance

- Live Paper Simulation V0.1 permits current public Pionex market data, simulated paper fills/lifecycle/account updates, and explicit paper-state persistence only; it has no private exchange-order path.
- Replacement holdout `2026-08-28` through `2026-09-03` remains `FROZEN_UNOPENED`.
- `source_switch_authorized=false`.
- Pionex-native and Binance USD-M evidence remain provider-separated and must never be relabeled.
- **Equivalence V0.1** remains a definitive FAIL; thresholds and scope are frozen and must not be regraded.
- No martingale, loss-doubling, or unlimited averaging down.
- Render Free / Frankfurt remains the proven public-metadata transport leg where applicable.
- Render must never receive R2 credentials.
- R2 credentials stay inside the authorized GitHub Actions secret boundary only. CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER applies to all project work; never access local files or use a local runtime.
- Frozen receipts/configs/evidence must not be rewritten to make later stages appear successful.
- Dashboards are derived evidence projections, not authority.
- Backtests and research metrics are evidence, not proof of future profitability.

## Reproducibility and CI hardening lineage

These markers preserve the reviewed engineering-hardening lineage required by repository authority tests; they do not add runtime authority.

- Dependency reproducibility uses `requirements/ci-constraints.txt` and validates the supported **Python 3.12 and Python 3.13** matrix, including jobs `test (3.12)` and `test (3.13)`.
- Production-critical GitHub Actions are pinned to **immutable 40-character commit SHAs**; the Python 3.13 runtime path remains explicitly validated.
- PR #136 and PR #137 established the constrained dependency/reproducibility hardening baseline; PR #140 continued the reviewed workflow hardening lineage.
- `D1_DATABASE_ID` is intentionally not a secret placeholder in `.env.example`; PR #141 records the related environment/authority cleanup lineage.
- Ruff is constrained as `ruff==0.16.0` and CI enforces core correctness classes `E4`, `E7`, and `E9`.
- PR #142 and PR #143 preserve the reviewed CI `pull_request` validation and supported Python matrix lineage.
- Issue #139 remains historical engineering context for this reproducibility-hardening sequence.

## Retired historical workflow inventory

Exactly **17 historical workflows** remain retired evidence/validation paths and must not be silently reactivated:

- `historical-backfill-pilot.yml`
- `diagnose-v0-2-self-hosted-mac-binance-transport.yml`
- `binance-2025-r2-pilot.yml`
- `binance-vision-live-proof.yml`
- `binance-vision-r2-proof.yml`
- `binance-funding-r2-v0-2-preflight.yml`
- `binance-funding-r2-v0-2-materialize.yml`
- `m1b-m1a-dataset-upload.yml`
- `m1b-r2-roundtrip.yml`
- `binance-2025-coverage-scan.yml`
- `binance-funding-source-proof.yml`
- `binance-funding-coverage.yml`
- `binance-max-coverage-discovery.yml`
- `m1a-acquisition.yml`
- `pionex-binance-equivalence-proof.yml`
- `pionex-binance-equivalence-v0-1-forensics.yml`
- `historical-universe-long-horizon-review.yml`

## Frozen historical lineage and dashboard compatibility markers

The dashboard and retired-workflow validators intentionally preserve these historical stage names. They do not override current operations or grant new authority.

- **V0.8 HISTORICAL** — frozen prepared cutover evidence only.
- **V0.10 FINAL ATOMIC METADATA CAPTURE CUTOVER EFFECTIVE** — historical effective authority.
- **V0.2 SELF-HOSTED SCHEDULE RETIRED** — self-hosted metadata scheduling remains retired.
- **V0.10 GITHUB-HOSTED SCHEDULE RETIRED** — V0.10 GitHub-hosted schedule remains retired.
- **V0.12 SUCCESSOR METADATA WINDOW** — frozen successor metadata-only lineage. Its bounded window is historical; current projections must not call it an active execution path.
- **REPLACEMENT HOLDOUT FROZEN_UNOPENED** — replacement holdout remains unopened.
- **HISTORICAL UNIVERSE MEMBERSHIP NOT_READY** — full-universe historical membership remains not ready.
- **TRADE-KLINE W1 MATERIALIZATION NOT_AUTHORIZED** — retired long-horizon pilot remains unable to materialize W1 trade-kline data.

## Current navigation

1. `CURRENT_STATUS.md`
2. `research/status/current-operations-v0-3.json`
3. `PROJECT_STATUS.md`
4. `README.md`
5. `AGENTS.md`
6. current versioned config/receipt/run evidence
7. `docs/TECH_DEBT_REGISTER_2026_09_17.md`
8. `docs/OPEN_PR_TRIAGE_2026_09_22.md`

## Preserved pre-convergence snapshot

The pre-PR-#322 long-form root documents remain exactly recoverable from historical parent main `f5cf74292fca262ba72c4e0b36f8d757dfb82531`:

- README blob: `0ce5c87ec4da228a6eb3d9a66ef2e8364661df58`
- PROJECT_STATUS blob: `0815abd975c5c708fbb9578dff400733e1ff6275`

Their old present-tense `8/10 / Training SKIPPED` statements are historical evidence and must not be treated as current operations.


## Automation V2 Batch 2 — external research and website projection

Automatic Operations V0.5 is the current schedule classification. Repository/Health retain eight cron declarations, while seven are current-effective; the eighth is the expired frozen V0.12 declaration. V0.4 preserves the prior unclassified eight-workflow state, and V0.2 remains byte-stable because the History Cadence authority binds it as frozen evidence.

This batch adds a versioned, read-only external-source change watch and a
non-authoritative automation schedule projection.

- Resource Hub Supply Chain V0.2: daily `01:13 UTC` / `09:13 Asia/Taipei`;
  unchanged source commits return `NO_CHANGE` without rebuilding candidates.
- Changed Resource Hub candidates remain `REVIEW_REQUIRED`; automatic install,
  runtime, adapter creation and pull-request creation remain closed.
- Dashboard Pages adds a daily `04:43 UTC` / `12:43 Asia/Taipei` backstop and
  business-content hash deduplication so rebuild timestamps alone do not cause
  a deployment.
- The website projects active, waiting-authority and planned schedules
  separately through `web/data/operations-schedule.json` with
  `authority=false`.
- ZEC V0.3 remains `0/256` development cells and
  `offline_development_runner_authorized=false`.
- Hourly multi-asset Paper scheduling remains waiting for a separate authority.
- Core100 History is complete 10/10 and its acquisition cron is retired; only bounded manual diagnosis/repair remains.
- Core100 Training remains scheduled with experiment-fingerprint `NO_CHANGE` deduplication active.

This batch does not open replacement holdout, source switching, automatic model
promotion, formal trade plans, real-money orders or live real trading.


## Automation V2 P1 — Core100 lifecycle cleanup (effective on reviewed merge)

This branch prepares the next protected-main lifecycle cleanup without changing
the completed research result:

- Core100 History remains **10/10 COMPLETE** and
  `history_reacquisition_required=false`.
- The old `:23 every two hours` History cron is removed on merge.
- Generic History `auto / discover / backfill` entrypoints are retired; only
  the already-bounded diagnosis and BNX repair modes remain available.
- The 2026-09-12 History cadence config, receipt and exact old workflow bytes
  remain frozen historical evidence. The old receipt is not rewritten.
- Automatic Operations V0.4 contains **8 repository cron workflows** after the
  History schedule retirement.
- Core100 weekly Training remains scheduled, but V0.3 of the runner computes an
  experiment fingerprint from the governed dataset plus model-affecting Git
  blobs. An exact match returns `NO_CHANGE`, performs no training and writes
  nothing to R2.
- The first dedupe baseline is the already-successful run `34918219864` on
  dataset fingerprint
  `91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876`.
  The model-affecting inputs were verified byte-identical between that run head
  and reviewed main before this change.

This P1 change adds no provider scope, no new R2 scope, no holdout access, no
source switch, no automatic model promotion, no formal trade plan, no
real-money orders and no live real trading.


## Core100 Training Fingerprint V0.2 — preparation and one-time baseline

The preparation audit found that V0.1 omitted `features/advanced.py`, allowing that code change to be invisible to its fingerprint. The 31-path import closure was classified as 14 result-identity paths and 17 runtime-guard paths; the original preparation documents and receipt remain historical evidence and were not rewritten.

PR #504 supplied the versioned one-time authority and PR #505 merged the separately reviewed successor execution path. The only authorized bootstrap [run `36110721415`](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36110721415) completed on 2026-09-25. Its report artifact is [10860768638](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36110721415/artifacts/10860768638). The report is `PASS` for baseline publication, with model-quality gate `REJECT`; all folds were ready, but not all beat naive log loss and not all base-cost average returns were positive. The run processed the existing 10/10 dataset (14,274 partitions; 18,235,427 rows), performed zero provider requests, and did not access holdout.

Dataset fingerprint: `91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876`. Experiment fingerprint: `12ff384302785645144832115114a88f726bcc4ce51caa56497bec1209c76ed7`. Runtime guard fingerprint: `c6733aab1c4f598ce3f4be36fa1b9058757459d1de4ef7394a4d0568c3d41d79`. Three immutable V0.2 objects (model, metrics, manifest) were written and readback-verified; the V0.2 latest pointer was written last and SHA-256 readback passed. The V0.1 pointer was left untouched. The one-time authority is consumed and the run must not be repeated. Future scheduled V0.2 runs are comparison-only under the successor contract. No threshold change, model promotion, source switch, trade plan, real-money order or live trading follows from this pipeline result.


## Automation V3 P2 — schedule and freshness convergence

- Provider Equivalence V0.12 is a frozen critical path, so its cron declaration is
  preserved byte-for-byte even though the bounded 2026-09-04 through 2026-09-12
  window has expired. Its window gate makes post-window execution ineffective;
  replay/backfill stays closed.
- Automatic Operations V0.5 classifies eight Repository cron declarations:
  seven current-effective plus one expired frozen V0.12 declaration.
- Research Automation Health V0.2 remains the exact eight-declaration monitor and
  is the single source for freshness thresholds / effective periods used by the
  seven current-effective Dashboard jobs.
- CI requires Repository cron declarations, Automatic Operations, Health monitoring,
  and the seven-job website effective subset to obey the exact 8 / 8 / 7 + 1 relation.
- The Dashboard exposes Repo declaration / Health / current-effective / Website
  counts while remaining `authority=false`.
- This convergence adds no provider, R2, holdout, source-switch, promotion,
  trade-plan, real-money-order, or live-real-trading authority.


## Automation V3 P3 — dashboard operations monitoring

- Cloud execution projection is upgraded to `qookey-cloud-run-status-v0.2`.
- The monitor derives its eight cron declarations from Automatic Operations V0.5
  and Research Automation Health V0.2 instead of a six-workflow hard-coded list.
- It preserves the current lifecycle split: seven `CURRENT_EFFECTIVE` schedules
  plus the frozen expired V0.12 cron declaration.
- Each row exposes operation ID, authority state/path, latest automatic schedule
  run ID, exact head SHA, evidence time, execution state, freshness state, and
  GitHub evidence links.
- Workflow success is never converted into a research/trading/business PASS.
  Business result stays `UNKNOWN_FROM_GITHUB_RUN_METADATA` unless a separate
  governed artifact/receipt surface is added later.
- The collector reads GitHub Actions metadata only: no workflow logs, artifacts,
  provider data, R2 objects, holdout, private APIs, or trading surfaces.
- The checked-in fixture contains no invented run IDs, SHAs, or evidence times;
  the GitHub Pages build refreshes those fields from live GitHub metadata.


## Automation V3 P5 — ZEC V0.4 regime-activation preregistration

- V0.3 remains **256/256 COMPLETE / NO_ELIGIBLE_DEVELOPMENT_CANDIDATE**.
- V0.4 does not loosen the V0.3 selection gate and does not promote the V0.3 diagnostic leader.
- The new hypothesis tests whether a small causal 4h bull-regime activation layer can reduce the strong time-regime dependence seen in V0.3.
- Candidate matrix is reduced to **2 MACD × 3 activation regimes = 6 candidates**, across the same four annual development folds = **24 cells**.
- Account-risk sweep is removed; risk is fixed at 1% for edge discovery.
- ATR extreme guard and 2.5ATR/Bollinger stop are fixed to reduce degrees of freedom.
- Fresh confirmation remains unopened.
- This phase is **contract validation only**: no runner, workflow dispatch, provider read, R2 access, holdout access, source switch, promotion or trading authority is added.


## ZEC V0.4 one-shot development authority

PR #418 prepares a **manual one-shot** execution authority for the already
preregistered 24-cell V0.4 development study.

- authority id: `zec-v0-4-development-20260921-v0-1`
- authority is ineffective until explicit protected-main merge of PR #418;
- merge does not auto-dispatch;
- one later manual `workflow_dispatch` is the only execution path;
- one run / one attempt maximum; retry or rerun requires a new versioned authority;
- source is bounded to 48 public Binance Vision ZECUSDT 15m monthly archives plus 48 checksums;
- development remains `2022-08-01 <= t < 2026-08-01`;
- fresh confirmation remains unopened;
- aggregate-only report is allowed; raw candles and raw trades are not persisted;
- R2 / holdout / source switch / promotion / trade plan / real-money / live trading remain closed.


## ZEC V0.4 development completion

- One-shot development run `35618367238` completed successfully on main `dd12300b294f2a868389c49a877be97a41a3ebe8`.
- Full preregistered matrix completed: **6 candidates × 4 folds = 24/24 cells**.
- All 6 candidates satisfied the minimum trade-count gate.
- **0/6** candidates had positive worst-fold return.
- Selection result: **NO_ELIGIBLE_DEVELOPMENT_CANDIDATE**.
- No champion was frozen.
- Diagnostic leader `zec-v0-4-04` had worst-fold return `-8.12511401%`.
- The V0.4 bull-regime activation hypothesis did not establish cross-fold robustness.
- Fresh confirmation remains unopened.
- V0.3/V0.4 selection thresholds are not loosened from this outcome.
- R2 / holdout / source switch / promotion / trade plan / real-money / live trading remain closed.


## Reliability convergence through PR #423

The current protected-main reliability layer now includes three merged changes:

- PR #421: Research Signal Quality runs after successful Research Signal Layer completion on same-repository `main`, retains the 10:47 Asia/Taipei fallback, and uses exact immutable-run dedupe without opening R2 list/write authority.
- PR #422: Dashboard GitHub Pages validates the built site with pinned Playwright Chromium on desktop and mobile; production browser validation is gated on an actual Pages deployment.
- PR #423: Live Paper Coordinator V0.2 requires a deterministic atomic run-slot claim before any new provider call.

Live Paper run-slot details:

- Coordinator contract: `config/live_paper_run_coordinator_v0_2.json`.
- Claim contract: `config/live_paper_run_claim_v0_1.json`.
- Slot identity: `run_id + sequence + previous_step_id + previous_state_id`.
- R2 conditional create uses S3-compatible `IfNoneMatch="*"`; a 412/precondition conflict fails closed.
- Claim conflicts have no automatic retry, expiry or takeover.
- Recovery treats unresolved claims without a complete verified step as `REVIEW_REQUIRED`.
- Complete verified steps missing only the result seal remain repairable without provider access.
- Fully committed identical requests replay with zero new provider calls.
- Coordinator execution remains manual `workflow_dispatch` only; no schedule was added.
- Private exchange APIs, holdout access, real-money orders and real live trading remain closed.

PR #423 post-merge CI, CodeQL, Dashboard GitHub Pages and V0.10 Critical Path Freeze Guard all completed successfully.

## Cloud Paper Loop V0.1 — implementation in progress

The complete simulation product is tracked by `research/status/cloud-paper-delivery-v0-1.json` and `config/cloud_paper_loop_v0_1.json`. PR #611 merged bounded account-wide D1/R2 Analytics audit preparation and zero-network readiness. Readiness run [36471242643](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36471242643) reported `BLOCKED_MISSING_READ_ONLY_CREDENTIAL`: zero Cloudflare requests, no secret values printed, and one-time audit authority unconsumed. Do not dispatch the one-time audit until zero-network readiness is READY.

PR #614 merged the versioned qualified-strategy adapter, validating registry eligibility, current Pionex evidence and router route, candidate time against the last closed bar, strategy receipt/implementation hashes, and paper equity/risk sizing. PR #622 then added the missing synthetic integration case: a test-only qualified fixture travels through the same composition for entry, exit, account advancement, persistence, and the next `NO_TRADE` slot. This closes a CI path-coverage gap; the production registry remains empty and Core100 quality remains `REJECT`. Neither PR adds an execution workflow, schedule, provider/R2/D1 authority, or production strategy.

PR #622 head CI passed Python 3.12/3.13, workflow-static, CodeQL, and Dependency/SBOM. Post-merge CI [36485948145](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36485948145), CodeQL [36485948118](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36485948118), Dependency/SBOM [36485948349](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36485948349), and Freeze Guard [36485948205](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36485948205) succeeded. Main-push `workflow-static` was skipped because workflows were unchanged.

Activation remains disabled. Account-wide usage/freshness evidence and all-writer coverage are unproven; D1 is not provisioned or wired; controlled main acceptance has not run; and no production execution workflow or natural schedule exists. PR #616 has since defined the report/object ceilings, append-only growth envelope, 6.4 GB warning, and projected 8 GB fail-closed stop. Production usage verification, D1 calibration, account-wide writer coverage, controlled acceptance, and execution schedule remain incomplete. Keep empty-registry `NO_TRADE` and all fail-closed controls.

