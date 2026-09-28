# 專案接續與排程手冊

更新：2026-09-29。適用任何能讀取 Repository 與 GitHub metadata 的模型.
這是操作與交接規格；正式權限由即時 `main` 的版本化 config／receipt 決定。
無法取得工具、來源或權限時，回報缺口，不能靠舊聊天補出成功結果。

## Cloud Paper 短期交付狀態 — 2026-09-29（PR #605 合併後）

本次文件更新前 main：`b1fe413b08550802a69f3fcaa64cf815a4bcc1c1`；PR #605 exact head `73482e126fc7b038d7fc975ead25e4c487e3551a` 已合併，查核時 open PR = 0。短期範圍見 [Cloud Paper short-term delivery](CLOUD_PAPER_SHORT_TERM_DELIVERY_V0_1.md)，狀態機見 [cloud-paper-delivery-v0-1.json](../research/status/cloud-paper-delivery-v0-1.json)。

- #590/#595：成功保存及 readback 後 settlement；相同用量 settlement 可冪等重送，不確定結果保留完整 reservation。
- #599：預設關閉的 verified-result recovery audit，驗證 immutable R2 result/report 後記錄 D1 audit receipt；保留完整 reservation，不 settlement、不釋放額度。#600 核對 result pointer slot identity 與 `COMMITTED` 狀態。
- #603：prepare-only per-UTC-day shared D1 rows reservation。每日最多 384 次 query reservation，每次涵蓋 admission statement 與目標 query；政策最大 envelope 為 3,072,000 rows read／7,680 rows written。
- #605：在同一原子 ledger 加入 shared storage-growth reservation；每次 query reservation 涵蓋兩個 statement 各 16 KiB，每日上限 12,582,912 bytes。這是保守 policy envelope，非 Cloudflare 生產 storage 增量量測。
- PR-head Python 3.12／3.13、Ruff/相關預算檢查、workflow-static、CodeQL、Dependency/SBOM 通過；合併後 main `b1fe413b08550802a69f3fcaa64cf815a4bcc1c1` 的 Python 3.12／3.13、V0.10 Freeze Guard、CodeQL、Dependency/SBOM 通過，workflow-static skipped（workflow 未變更）。SQLite CI 為合成驗證，非 production D1 用量測量。
- 兩個 D1 shared-budget migration 都 prepare-only，未套用；D1 未 provision，未執行 production D1/R2/provider request。
- 未完成：可信且及時的 account-wide D1/R2 usage source、所有 D1 writers coverage、storage envelope 與 Cloudflare 實際 size 行為核對、FREE-ONLY 合併容量證明、production runner binding、正式受控 main acceptance。execution workflow／自然 Cloud Paper schedule 尚未建立；`activation.enabled=false`。
- 官方 Cloudflare D1 GraphQL analytics 範例以 date 維度聚合，文件未承諾符合 60 秒 freshness；不直接視為 pre-access snapshot。D1 query API 的 `meta.rows_read`／`rows_written` 和 `size_after` 是單次查詢後回報值，可協助校準實際成本，但本身不能在查詢前證明帳戶級 baseline 或其他 database/writer 覆蓋。[Metrics and analytics](https://developers.cloudflare.com/d1/observability/metrics-analytics/) · [Query D1 Database](https://developers.cloudflare.com/api/resources/d1/subresources/database/methods/query/)
- 最近已驗證 Pages production build/deploy/browser 仍是 run [36414262259](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36414262259)（SHA `9753c6b3`）；#603/#605 無 dashboard 改動。PR #604 文件更新的 Pages build pass、deploy/browser skipped，未提供新 production deployment evidence。
- Core100 bootstrap [run 36110721415](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36110721415) 已唯一一次完成：report `PASS / CORE100_FINGERPRINT_V0_2_BASELINE_PUBLISHED`、quality `REJECT`、zero provider requests、holdout 未存取、immutable objects／latest pointer readback 成功。一次性 authority 已消耗，不得 rerun。
- 模型仍 `REJECT`、production registry 空、macro regime `REGIME_UNAVAILABLE`；有效正式結果仍是 `NO_TRADE`。維持 0 USD、PAPER／LIVE-PAPER ONLY、holdout/source switch/promotion/real-money trading 關閉。

下一批：確認 production account usage 的權威來源與 freshness，完成 D1 writer inventory/coverage 證明並校準 storage envelope；再核算含 admission、settlement、recovery/retry 的總預留。通過前不套用 migration、不 provision、不做正式受控驗收、不啟用 schedule。

## 1. 固定入口

| 問題 | 主要入口 |
| --- | --- |
| 目前進度、下一步 | [CURRENT_STATUS.md](../CURRENT_STATUS.md) |
| 治理、研究階段、歷史證據 | [PROJECT_STATUS.md](../PROJECT_STATUS.md)，再讀該階段 config／receipt |
| 模組與產品架構 | [README.md](../README.md) |
| Agent 規則 | [AGENTS.md](../AGENTS.md) |
| 排程、事件、歷史 workflow | [Actions operating map](GITHUB_ACTIONS_OPERATING_MAP.md) |
| 整理工作的狀態與驗收 | [既有技術債登記表](TECH_DEBT_REGISTER_2026_09_17.md#current-cleanup-order) |
| 原工作區 78 項逐檔處置 | [Local workspace reconciliation receipt](LOCAL_WORKSPACE_RECONCILIATION_2026_09_24.md) |

本手冊沒有第二份待辦資料庫。GitHub intake 使用單一 [Work Item 表單](../.github/ISSUE_TEMPLATE/work-item.yml)，其 contract 與規則見 [Engineering Workflow](ENGINEERING_WORKFLOW_V0_1.md)；issue、label、PR 與本手冊都不授予 execution authority。舊 AGENTS、草稿 PR 與本地提案不能替代 current main。

### 歷史本地成果（EXCLUDED_BY_USER）

以下表格只保存歷史脈絡。自 2026-09-25 起，使用者要求全部工作在線上完成：不得讀寫本機檔案、使用本機終端機、要求上傳本機 recovery 或補做本機清理。這些工作統一為 EXCLUDED_BY_USER，不是雲端阻礙；已整合到 GitHub 的文件可依 exact main SHA 讀取。

| 工作 | 本地成果位置 | 已完成／仍待處理 |
| --- | --- | --- |
| TD-011 | `docs/LOCAL_WORKSPACE_RECONCILIATION_2026_09_24.md`; original checkpoint remains in `handoffs/2026-09-23-project-checkpoint/` in the dirty checkout | All 78 outcomes and current-main blob/mode classifications are documented; all 78 status pairs still match the checkpoint, with 13 newer untracked handoff files. There are 15 untracked exact duplicates proposed as one cleanup batch; two tracked exact matches are excluded. C1/C4/C5 are integrated by PRs #493/#491/#492; C2/C3 are deferred. The original working tree remains dirty. Local cleanup is now EXCLUDED_BY_USER; no future cloud task may inspect or delete these files. |
| TD-012 | 原本地提案仍保留於 handoffs/2026-09-23-core100-fingerprint-v0-2-proposal.md；Repository 準備文件見 [V0.2 review](CORE100_TRAINING_FINGERPRINT_V0_2.md)、[config](../config/core100_training_fingerprint_v0_2.json)、[receipt](../research/receipts/2026-09-24-core100-training-fingerprint-v0-2-prepared.json) | 準備階段的 31-path closure 與 comparator 證據保持歷史狀態。PR #504/#505 已分別提供一次性 authority 和 successor implementation；bootstrap run `36110721415` 已完成，報告為 `PASS`、模型品質為 `REJECT`，V0.2 baseline 與 latest pointer 回讀驗證通過。一次性權限已消耗，禁止 rerun；future scheduled runs are comparison-only under the merged contract. |
| 歷史交接快照 | `handoffs/2026-09-23-project-checkpoint/README.md` | 僅保存當時 main／PR／驗證與工作區脈絡；不可視為最新狀態，操作前必須查 live GitHub |

Signal ingest parsing hardening 和 Quality V0.1 authority validation 分別由 [PR #491](https://github.com/qookey109-pixel/crypto-autopilot/pull/491) 與 [PR #492](https://github.com/qookey109-pixel/crypto-autopilot/pull/492) 合併，合併後 CI、CodeQL、Freeze Guard、Pages deploy 與 browser-production 均成功。不要把舊模組整檔覆蓋 current main，也不要移植舊的 Quality evaluator；main 的 dedupe、source-run binding、freshness 與單指標 `NO_CHANGE` 讀取契約已保留。C1 unified planning overlay 的單一 Work Item form、contract、模板與 AGENTS/README 導覽由 [PR #493](https://github.com/qookey109-pixel/crypto-autopilot/pull/493) 整合。C2 Agent Arena 仍無具體比較集合／使用路徑，且 registry 已能保存不可變證據、scorecard 已提供 research-priority ranking；C3 的舊 synthetic preview 使用舊 Paper report schema，而 main 已有 Daily Opportunity Engine 和 Strategy Router，兩項都先保留本地、不移植。舊 Health V0.1 cron 與缺少 #478 的 Pages workflow不可回灌。

## 2. 每次接續的固定流程

1. 記錄 UTC／Asia/Taipei 查核時間、Repository，先解析 GitHub `main` exact SHA。一律記 `CLOUD_ONLY / LOCAL_WORK_EXCLUDED_BY_USER`；只能使用 GitHub 或 GitHub-hosted runner 的暫存 checkout，禁止存取使用者本機檔案。main 解析失敗則標記 `UNKNOWN`，停止依賴最新 authority 的工作。
2. 依上表讀入口及本次涉及的版本化檔案。文件內 evidence-basis SHA 是歷史查核基準，不是最新 main。
3. 取得 live open PR，再讀相關 PR exact head/base、draft／merged、checks。已有相同工作就接續；已完成工作不重做。
4. 判定模式：**排程健檢**只讀 Repository／Actions metadata；**使用者指派的整理工作**依明確範圍編輯、驗證與交付。排程或待辦本身不授予權限；Cloud Maintenance V0.1 合併後只授予指定文件區塊及草稿 PR 權限，沒有 merge／dispatch 權限。
5. 一般模型健檢只指出一個下一步；已合併的固定維護程式可依 Cloud Maintenance V0.1 建立文件草稿 PR。使用者指派的整理工作才選一個可執行項目；遇外部等待或權限缺口，留下證據並繼續不相依項目；不反覆重試已知 403、不增加平行工作流。
6. 執行有檔案權限的整理工作時，修改前查該檔是否被 frozen receipt／hash 綁定。只透過 GitHub 線上分支／API 編輯，由 GitHub-hosted runner 測試；不存取使用者 checkout 或未提交內容。
7. 以項目驗收證據結束。文件檢查連結、矛盾及相關既有檢查；行為改動加必要回歸測試。保留實際命令、結果、未驗證事項。
8. 交接記錄「完成、等待、下一動作」。PR 建立、CI 通過、合併、部署、自然 schedule 通過必須分開。

## 3. 排程分工

### GitHub：執行已合併的研究與網站工作

名義時間及 expiry 以 [Actions map](GITHUB_ACTIONS_OPERATING_MAP.md#scheduled-operations) 導航，再核對當下 workflow／config。不要由 Codex 再 dispatch，也不要建立平行 cron。

### GitHub 雲端維護：接在既有 Health 之後

既有 Health V0.2 在台北偶數小時 :57 名義執行，維持唯讀。
Cloud Project Maintenance V0.1 使用 workflow_run completion，不另建 cron，
也不依賴 ChatGPT 個人排程、特定模型或使用者電腦。

新 workflow／contract／receipt 合併到 main 後才生效；啟用與驗收分開。
inspect job 只有讀權限；propose job 重新讀取 current main／來源證據，
只允許兩個指定區塊和 draft PR。模型提示詞見 [CLOUD_SCHEDULED_CHECK_PROMPT.md](CLOUD_SCHEDULED_CHECK_PROMPT.md)。

每轮將即時 main、來源 run、PR checks、Actions pagination coverage 保存於
GitHub run summary，不新增 artifact／cache／外部儲存。
無實質狀態改變不 commit；文件保留上次狀態變更的證據，不假裝永遠是最新快照。
main 或來源改變、人工修改、分頁不足、403 或 schema successor 均停止發佈。

<a id="accelerated-delivery-2026-09-27"></a>
### 今天完成交付 — 2026-09-27

依使用者最新指示，**今天完成已準備的文件與 UI 交付**。取消本輪額外七天觀測與 10/1 到期查核，不再將兩者列為等待工作或交付前置條件；先前 9/30 收尾計畫由此取代。既有 workflow 的 cron、有效窗口與 expiry guard 依 main 契約執行，這項取消只針對追加人工查核。

9/27 15:18 審查時，自然 Pionex／Core100／Pages 證據缺席，Health freshness 仍有缺口。以現有證據結束本輪人工觀測，結果保留 MISSING／DELAYED／UNKNOWN，自然驗收 NOT ESTABLISHED。這是已完成查核但驗收證據不足，不能把 manual dispatch 算成自然證據或宣稱 scheduler failure。文件／UI 在必要檢查通過後直接交付；不新增等待窗口。

| 順序 | 今天的工作與完成條件 |
| --- | --- |
| 1 | 在 #532 整合本流程、自然觀測及 #533 的原始 generated snapshot；重查 current head/base、必要 review／CI，通過後合併。 |
| 2 | main 讀回確認 #533 兩個 generated blocks 原樣整合後，關閉重複 #533，保留 PR／commits／run 證據並刪除已結束交付分支。 |
| 3 | 審閱 #534 的五個 UI／驗證檔案，必要時以 merge commit 同步 main，雲端 CI 通過後合併；核對 Pages build／deploy／browser-production 與桌面／手機結果。 |
| 4 | 確認 main、PR 處置、分支及實際部署；交付完成事項和保留的證據缺口。CI／部署有未解阻礙就明確標示未完成；不把研究品質或自然驗收未過改寫成通過。 |

TD-007、fingerprint-bound 路徑、重構、新研究與 Pionex failure-artifact 設計列既有 intake／技術債下一輪，今天不以增加工程範圍延後交付。只有已重現且阻擋本次交付的故障進入修正。

使用者既有逐 PR 合併授權可由接續代理在 exact head/base、review/checks、差異與 authority 核對通過後使用。Cloud Maintenance 固定程式仍只維護 generated blocks／Draft PR，沒有新增合併或執行權限。本流程沿用 CLOUD-01／CLOUD-02 與現有 Work Item；未建立個人／本機排程、平行 cron 或額外自動合併器。模型品質仍為 REJECT，0 USD 與 PAPER／LIVE-PAPER ONLY 等現行界線有效。

### 近期工作節點

日期僅是檢查時點。較晚執行時查該日期之後的 metadata，不補跑。

### Core100 fingerprint V0.2 one-time baseline — completed

The single authorized bootstrap [run `36110721415`](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36110721415) completed on main `41c79994a82a30d938774ff540c97767c0ad01d6`. Its report artifact is [10860768638](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36110721415/artifacts/10860768638). Report status/stage: `PASS / CORE100_FINGERPRINT_V0_2_BASELINE_PUBLISHED`; model-quality gate: `REJECT`. It read 14,274 governed partitions / 18,235,427 rows, performed zero provider requests, and did not access holdout. Three immutable model/metrics/manifest objects were written with SHA-256 readback checks; the latest pointer was written last and verified by SHA-256 readback. Dataset fingerprint: `91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876`; experiment fingerprint: `12ff384302785645144832115114a88f726bcc4ce51caa56497bec1209c76ed7`; runtime guard fingerprint: `c6733aab1c4f598ce3f4be36fa1b9058757459d1de4ef7394a4d0568c3d41d79`. One-time authority is consumed; do not rerun. This result changes no promotion, source-switch, holdout, order, or live-trading authority.

The report was recovered from the completed GitHub job log, which prints the same `report.json` uploaded as the artifact. The artifact is retained on GitHub Actions; use its report for future verification.

| 時點（台北） | 工作與完成條件 |
| --- | --- |
| 既有 Health 自然完成後 | 唯讀健檢；Pages 自然 run `35843351924` 已成功，且其後自然 Health run `35870216734` 已 `PASS`、`alerts=0`。TD-010 已完成，後續只做正常健康監控並在新故障／恢復時更新 |
| Cloud Maintenance V0.1 自然驗收 | **COMPLETE**。權限決定前的兩組 `BLOCKED_PERMISSION` 僅保留歷史、不計入。權限變更後三組自然 Health → Maintenance 鏈 `36168047712` → `36168107765`、`36193834603` → `36193882301`、`36206764619` → `36206794716` 均完成 `inspect` / `propose`；後兩組明確為 `NO_CHANGE / commits_created=0`。第一組建立 generated-block-only draft PR #509，經核准 CI 後合併為 `1e5234fc7b37572a178ee6d06b10214a50263258`。未使用 dispatch／rerun 補算；研究結果仍為 `UNKNOWN_FROM_METADATA`。 |
| 2026-09-27 11:53 之後 | 核對 Pionex bounded observability 最後名義 slot 的自然 schedule；保留 missing／delayed／failure |
| 2026-09-27 12:37 之後 | 核對 Weekly Training 自然 schedule；只從 metadata 確認 workflow 結論，無 report 就不判定 NO_CHANGE／模型 PASS |
| 原七天追加觀測 | **CANCELLED_BY_USER（9/27）**。本輪不再追加觀測或調頻評估；保留已取得的 dated metadata，不以不足七天的樣本宣稱七天驗收完成。 |
| 原 10/1 到期追加查核 | **CANCELLED_BY_USER（9/27）**。不列待辦；既有 runtime window／expiry guard 照原 authority 執行，未延長或停用。 |

「名義時間已過」與「超過 policy freshness」必須分開。這些工作節點不會另建立排程。

## 4. 證據與錯誤處理

每次觀測保留以下欄位於接續任務紀錄；若要保存檔案，依該次寫入權限處理。不得提交 credentials 或敏感 logs。

```text
observed_at_utc / observed_at_taipei:
repository / main_sha / source_paths_at_sha:
item_id / status: DONE | READY | WAITING_EVIDENCE | BLOCKED_PERMISSION | UNKNOWN | DEFERRED
pr_number / head_sha / base_sha / draft / merged / checks:
workflow_path / workflow_id / event / run_id / run_attempt / head_sha:
nominal_slot_utc / nominal_slot_confidence:
created_at / run_started_at / completed_at_if_available / status / conclusion:
build / deploy / browser: SUCCESS | FAILURE | SKIPPED | PENDING | UNKNOWN
policy_path / policy_main_sha / freshness / active_window:
coverage: queried interval, pages fetched, filters, missing responses
evidence_urls / changed_since_previous / next_action / blocker:
```

- 記 pagination／event filters；只有第一頁不能稱完整清冊。PR-only connector 的結果不能回答 schedule 健康。
- `created_at` 是 GitHub 建立 run 時間；名義 slot 不唯一就列候選／UNKNOWN，不能硬配最近 slot。
- `updated_at` 不等於 completed_at；可取 job metadata 的完成時間，否則留空。started−created 是 queue delay，不能稱 cron delay。
- API 403／rate-limit／連線失敗／缺頁：列 UNKNOWN 或 BLOCKED_PERMISSION，不可當「零失敗／不存在／完成」。不索取 token，不 dump secrets。
- queued／in_progress 不是成功，SKIPPED 不是實際執行成功；只有 policy 明列允許 skipped 才能用於該健康判斷。
- 維護摘要分別保存「觸發此輪的 Health 結論」及「查核時最新 workflow 狀態」。即使查核時已有更新的成功 Health，觸發來源的 failure／cancelled／timed_out／skipped／未知結論仍轉 CLOUD-02；不得以更新成功覆蓋該次失敗。
- 相同問題用 `workflow + event + latest relevant run + conclusion + expiry state` 去重，另記首次告警及恢復。只有查核時間不同不是新進展。
- metadata-only 健檢不讀 logs／artifacts。沒有 report 證據時，Training success 不能推出 PASS／NO_CHANGE；provider／R2 用量維持 UNKNOWN。

## 5. 執行界線

- 一般模型健檢保持唯讀。僅已合併 Cloud Maintenance V0.1 的固定程式可更新指定區塊及 draft PR；不修改程式、不 merge／dispatch／rerun／cancel／disable，不改 cron。
- 2026-09-25：TD-014 的 25 個 removed-file workflow registrations 已依 [Actions operating map](GITHUB_ACTIONS_OPERATING_MAP.md#removed-registrations-disabled-2026-09-25) 完成停用，25/25 均讀回停用狀態；操作紀錄 PR #497，run history 保留。需要使用現況時另行查核；不沿用早期 0/25 或 403 阻礙重做停用，Cloud Maintenance 程式不具停用權限。
- Core100 History、Pionex V0.2、ZEC V0.3／V0.4 不重跑。V0.2 one-time bootstrap run `36110721415` 已消耗其授權，絕不可 rerun；保留其 V0.2 namespace 與舊 V0.1 pointer。Future scheduled fingerprint runs are comparison-only; no additional training or R2 write is authorized by this completed bootstrap.
- FREE-ONLY；PAPER／LIVE-PAPER ONLY；replacement holdout FROZEN_UNOPENED；source_switch_authorized=false。不新增 provider／R2 存取、paid service、promotion、策略／風控變更或實盤。
- 更換模型或聊天不提升權限。缺必要工具時交接阻礙及下一步，不改寫驗收條件。

## 6. 每次交付格式

```text
專案與查核時間：
模式及 main SHA：
已完成（項目 ID、變更、驗證命令／結果、證據）：
等待／未知（原因、缺少哪項證據）：
PR / merge / deployment / natural schedule：各自狀態
下一個可開始的工作（檔案、步驟、驗收、停止條件）：
執行環境：CLOUD_ONLY；本機與 recovery：EXCLUDED_BY_USER；本次不讀寫本機
```

新模型先跑第 2 節，再依 [CURRENT_STATUS.md](../CURRENT_STATUS.md) 接續。舊 Handoff 保留歷史，新查核追加時間與來源。

## 7. 雲端工作卡（沿用既有 Work Item intake）

### CLOUD-01 — 交付與自然排程驗收

- 目的：以 live current main 與現有 open PR 為準完成維護自然驗收；維護交付本身已合併，不從歷史 PR 重建待辦。
- 前置：讀 live main、Cloud Maintenance V0.1 contract／receipt、open PR。
- 起點：在本次 run summary／PR 填 exact main、head、base 及證據 URL，禁止使用固定舊 SHA。
- 步驟：
  1. 先查 current main 與所有 live open PR 的 exact head/base/draft/merged/checks；#496/#497 等舊 PR 僅保留歷史證據，不固定投影成目前待辦。
  2. 若本輪 maintenance 產生 draft PR，查該 PR 的 Python 3.12／3.13、Ruff、workflow-static 與相關治理檢查；沒有 live PR 就不得用已合併舊 PR 代替。
  3. 需要合併的 live PR 才列 WAITING_USER_MERGE；缺檢查列 UNKNOWN，GitHub 要批准 CI 時列 WAITING_CI_APPROVAL。
  4. 合併後查首次自然 Health schedule 的 completion 是否觸發維護 inspect／propose；不 dispatch 補證據。
  5. 再查第二個不同自然 Health run；驗證維護兩次完整完成，其中無變化回合 NO_CHANGE 且 commits_created=0。
- 驗收：兩組 source run ID／attempt、main／head、兩個 job 結果、產生的 draft PR 或 NO_CHANGE 摘要；人工檢查 generated-block-only diff。
- 停止：main 前進、衝突、人工編輯、來源不可信、缺權限／資料、CI 失敗時轉 CLOUD-02；不得自動擴權。
- 交付：完成／等待／未知分列。CI、merge、維護自然執行、研究結果分開。
- 下一步：本段 2026-09-27 Pionex／Weekly Training 排程是歷史檢查點，不能當作目前待辦或補跑歷史 slot。現在的 Cloud Paper 交付狀態與下一批以本手冊頂端的 PR #605 checkpoint 為準；Core100 V0.2 一次性 bootstrap 已完成、品質保持 `REJECT`，禁止 rerun、放寬門檻、推論 promotion 或 source switch。Auto-merge 僅用於逐 PR 核對 exact head/base、必要 review／CI 與 authority boundary 後的交付。

### CLOUD-02 — 異常與程式缺陷交接

- 目的：提供可由下一模型執行的最小工作卡，不自動修改研究程式。
- 來源：本次 GitHub run summary、exact main／相關 PR checks 與當前 policy。
- 步驟：
  1. 抄錄固定錯誤代碼、run URL、main SHA、缺失欄位；不下載 logs／artifact、不索取 secrets。
  2. 403／CI 待批准：列所缺權限與使用者操作位置；不重試或切換 token。
  3. MAIN_CHANGED：重查 main；已有維護 PR 基底落後就交由使用者審查／合併或明確處置，機器人不 rebase／force-push。
  4. MANUAL_EDIT：保留原文和現有 PR，列出衝突路徑，不覆寫。
  5. 程式缺陷：使用既有 Work Item 欄位寫明預期與實際、重現 fixture、允許檔案、最小修正、雲端測試與驗收。自動程序只輸出工作卡，不開 issue／貼 label。
- 驗收：下一模型可從 GitHub 取得全部輸入；缺任一來源標 UNKNOWN，不能靠聊天或本機補齊。
- 界線：不得 provider／R2／holdout／training／promotion／source-switch／交易，不修改 frozen evidence。
- 下一步：只有使用者指派修正後，才在線上分支修改並走 GitHub CI。

## 8. 維護規格與停止方式

- Contract：[Cloud Maintenance V0.1](../config/cloud_project_maintenance_v0_1.json)。
- Workflow：[`cloud-project-maintenance-v0-1.yml`](../.github/workflows/cloud-project-maintenance-v0-1.yml)。
- 每輪執行使用 standard GitHub-hosted Ubuntu；不需要模型 API 或新 secrets。
- 自動只更新本手冊與 CURRENT_STATUS 的以下標記區塊，其他文字不可動。
- 長效憑證、paid fallback、自動部署、修改 Actions settings 均不在範圍。
- 若 GitHub 不允許 token 建 draft PR，維持 BLOCKED_PERMISSION；沒有權限就不宣稱排程全部完成。
- 要停止此功能，可由使用者停用這個 maintenance workflow；Health 繼續唯讀。
  程式不自行停用、刪除 workflow 或刪除歷史 run。
- GitHub 本身排程延遲／停用時，內部 listener 無法獨立喚醒；本方案不宣稱外部全天候監控。
- 未加入新 artifact 儲存；metadata 證據放 Actions summary。本輪七天追加觀測／cadence 評估已由使用者取消；cron 依現行設定。
- 本文件標記內資料是上次「實質變更」的證據基準；最新狀態需讀本輪 summary 和 live main。

<!-- cloud-maintenance:v0.1:begin -->
<!-- record:eyJldmlkZW5jZSI6IHsiY292ZXJhZ2UiOiBbeyJjb21wbGV0ZSI6IHRydWUsICJmaWx0ZXJzIjogeyJicmFuY2giOiAibWFpbiIsICJjcmVhdGVkIjogIj49MjAyNi0wOS0xMlQxODowNjoxNy43NDQyNDJaIiwgImV2ZW50IjogInNjaGVkdWxlIn0sICJwYWdlcyI6IDEsICJwYXRoIjogIi9hY3Rpb25zL3dvcmtmbG93cy9yZXNlYXJjaC1zaWduYWwtbGF5ZXItdjAtMi55bWwvcnVucyIsICJyb3dzIjogMTR9LCB7ImNvbXBsZXRlIjogdHJ1ZSwgImZpbHRlcnMiOiB7ImJyYW5jaCI6ICJtYWluIiwgImNyZWF0ZWQiOiAiPj0yMDI2LTA5LTEyVDE4OjA2OjE3Ljc0NDI0MloiLCAiZXZlbnQiOiAic2NoZWR1bGUifSwgInBhZ2VzIjogMSwgInBhdGgiOiAiL2FjdGlvbnMvd29ya2Zsb3dzL3Jlc2VhcmNoLXNpZ25hbC1xdWFsaXR5LXYwLTEueW1sL3J1bnMiLCAicm93cyI6IDE0fSwgeyJjb21wbGV0ZSI6IHRydWUsICJmaWx0ZXJzIjogeyJicmFuY2giOiAibWFpbiIsICJjcmVhdGVkIjogIj49MjAyNi0wOS0xMlQxODowNjoxNy43NDQyNDJaIiwgImV2ZW50IjogInNjaGVkdWxlIn0sICJwYWdlcyI6IDEsICJwYXRoIjogIi9hY3Rpb25zL3dvcmtmbG93cy9yZXNlYXJjaC1hdXRvbWF0aW9uLWhlYWx0aC12MC0yLnltbC9ydW5zIiwgInJvd3MiOiA3M30sIHsiY29tcGxldGUiOiB0cnVlLCAiZmlsdGVycyI6IHsiYnJhbmNoIjogIm1haW4iLCAiY3JlYXRlZCI6ICI+PTIwMjYtMDktMTJUMTg6MDY6MTcuNzQ0MjQyWiIsICJldmVudCI6ICJzY2hlZHVsZSJ9LCAicGFnZXMiOiAxLCAicGF0aCI6ICIvYWN0aW9ucy93b3JrZmxvd3MvYmluYW5jZS11c2RtLWRldGFpbGVkLXRyYWluaW5nLXYwLTEueW1sL3J1bnMiLCAicm93cyI6IDJ9LCB7ImNvbXBsZXRlIjogdHJ1ZSwgImZpbHRlcnMiOiB7ImJyYW5jaCI6ICJtYWluIiwgImNyZWF0ZWQiOiAiPj0yMDI2LTA5LTEyVDE4OjA2OjE3Ljc0NDI0MloiLCAiZXZlbnQiOiAic2NoZWR1bGUifSwgInBhZ2VzIjogMSwgInBhdGgiOiAiL2FjdGlvbnMvd29ya2Zsb3dzL3Bpb25leC1hbHRlcm5hdGl2ZS1hc3NldHMtb2JzZXJ2YWJpbGl0eS12MC0yLnltbC9ydW5zIiwgInJvd3MiOiAyfSwgeyJjb21wbGV0ZSI6IHRydWUsICJmaWx0ZXJzIjogeyJicmFuY2giOiAibWFpbiIsICJjcmVhdGVkIjogIj49MjAyNi0wOS0xMlQxODowNjoxNy43NDQyNDJaIiwgImV2ZW50IjogInNjaGVkdWxlIn0sICJwYWdlcyI6IDEsICJwYXRoIjogIi9hY3Rpb25zL3dvcmtmbG93cy9yZXNvdXJjZS1odWItc3VwcGx5LWNoYWluLXYwLTIueW1sL3J1bnMiLCAicm93cyI6IDV9LCB7ImNvbXBsZXRlIjogdHJ1ZSwgImZpbHRlcnMiOiB7ImJyYW5jaCI6ICJtYWluIiwgImNyZWF0ZWQiOiAiPj0yMDI2LTA5LTEyVDE4OjA2OjE3Ljc0NDI0MloiLCAiZXZlbnQiOiAic2NoZWR1bGUifSwgInBhZ2VzIjogMSwgInBhdGgiOiAiL2FjdGlvbnMvd29ya2Zsb3dzL2Rhc2hib2FyZC1naXRodWItcGFnZXMueW1sL3J1bnMiLCAicm93cyI6IDZ9LCB7ImNvbXBsZXRlIjogdHJ1ZSwgImZpbHRlcnMiOiB7fSwgInBhZ2VzIjogMSwgInBhdGgiOiAiL2FjdGlvbnMvcnVucy8zNjIzMjk5MTk0My9hdHRlbXB0cy8xL2pvYnMiLCAicm93cyI6IDN9LCB7ImNvbXBsZXRlIjogdHJ1ZSwgImZpbHRlcnMiOiB7ImJhc2UiOiAibWFpbiIsICJzdGF0ZSI6ICJvcGVuIn0sICJwYWdlcyI6IDEsICJwYXRoIjogIi9wdWxscyIsICJyb3dzIjogM30sIHsiY29tcGxldGUiOiB0cnVlLCAiZmlsdGVycyI6IHt9LCAicGFnZXMiOiAxLCAicGF0aCI6ICIvY29tbWl0cy9kN2U4NThiNjQ1NmE5NDQ0NDExODRhMjgzNDgxYWMwYWJiYjI2NjBkL2NoZWNrLXJ1bnMiLCAicm93cyI6IDV9LCB7ImNvbXBsZXRlIjogdHJ1ZSwgImZpbHRlcnMiOiB7fSwgInBhZ2VzIjogMSwgInBhdGgiOiAiL2NvbW1pdHMvYWZmZTg3ZWZiMTFlYTQwNTUwMzM0OWRmNzQxOWI3ZTg0OTVjN2FiYy9jaGVjay1ydW5zIiwgInJvd3MiOiAxMX0sIHsiY29tcGxldGUiOiB0cnVlLCAiZmlsdGVycyI6IHsiYmFzZSI6ICJtYWluIiwgInN0YXRlIjogIm9wZW4ifSwgInBhZ2VzIjogMSwgInBhdGgiOiAiL3B1bGxzIiwgInJvd3MiOiAzfV0sICJtYWluX3NoYSI6ICJmZDY4NjUwNDcyMTg4ZTZjZGRlZDRkNGU2YWE1YjFhNDUyNzc0ZjcyIiwgIm9ic2VydmVkX2F0X3V0YyI6ICIyMDI2LTA5LTI2VDE4OjA2OjE3Ljc0NDI0MiswMDowMCIsICJwcnMiOiB7IjUzMiI6IHsiYmFzZSI6ICJmZDY4NjUwNDcyMTg4ZTZjZGRlZDRkNGU2YWE1YjFhNDUyNzc0ZjcyIiwgImNoZWNrcyI6IFt7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJuYW1lIjogInRlc3QgKDMuMTMpIiwgInN0YXR1cyI6ICJjb21wbGV0ZWQifSwgeyJjb25jbHVzaW9uIjogInN1Y2Nlc3MiLCAibmFtZSI6ICJ0ZXN0ICgzLjEyKSIsICJzdGF0dXMiOiAiY29tcGxldGVkIn0sIHsiY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgIm5hbWUiOiAid29ya2Zsb3ctc3RhdGljIiwgInN0YXR1cyI6ICJjb21wbGV0ZWQifSwgeyJjb25jbHVzaW9uIjogInN1Y2Nlc3MiLCAibmFtZSI6ICJDb2RlUUwgdmlzaWJpbGl0eSAoUHl0aG9uKSIsICJzdGF0dXMiOiAiY29tcGxldGVkIn0sIHsiY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgIm5hbWUiOiAiZGVwZW5kZW5jeS1zZWN1cml0eSIsICJzdGF0dXMiOiAiY29tcGxldGVkIn1dLCAiaGVhZCI6ICJkN2U4NThiNjQ1NmE5NDQ0NDExODRhMjgzNDgxYWMwYWJiYjI2NjBkIn0sICI1MzQiOiB7ImJhc2UiOiAiZmQ2ODY1MDQ3MjE4OGU2Y2RkZWQ0ZDRlNmFhNWIxYTQ1Mjc3NGY3MiIsICJjaGVja3MiOiBbeyJjb25jbHVzaW9uIjogInNraXBwZWQiLCAibmFtZSI6ICJicm93c2VyLXByb2R1Y3Rpb24iLCAic3RhdHVzIjogImNvbXBsZXRlZCJ9LCB7ImNvbmNsdXNpb24iOiAic2tpcHBlZCIsICJuYW1lIjogImRlcGxveSIsICJzdGF0dXMiOiAiY29tcGxldGVkIn0sIHsiY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgIm5hbWUiOiAidGVzdCAoMy4xMikiLCAic3RhdHVzIjogImNvbXBsZXRlZCJ9LCB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJuYW1lIjogImRlcGVuZGVuY3ktc2VjdXJpdHkiLCAic3RhdHVzIjogImNvbXBsZXRlZCJ9LCB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJuYW1lIjogIndvcmtmbG93LXN0YXRpYyIsICJzdGF0dXMiOiAiY29tcGxldGVkIn0sIHsiY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgIm5hbWUiOiAidGVzdCAoMy4xMykiLCAic3RhdHVzIjogImNvbXBsZXRlZCJ9LCB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJuYW1lIjogInZhbGlkYXRlLXByZXBhcmVkLWN1dG92ZXIiLCAic3RhdHVzIjogImNvbXBsZXRlZCJ9LCB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJuYW1lIjogIkNvZGVRTCB2aXNpYmlsaXR5IChQeXRob24pIiwgInN0YXR1cyI6ICJjb21wbGV0ZWQifSwgeyJjb25jbHVzaW9uIjogInN1Y2Nlc3MiLCAibmFtZSI6ICJidWlsZCIsICJzdGF0dXMiOiAiY29tcGxldGVkIn0sIHsiY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgIm5hbWUiOiAic21va2UiLCAic3RhdHVzIjogImNvbXBsZXRlZCJ9LCB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJuYW1lIjogInNuYXBzaG90IiwgInN0YXR1cyI6ICJjb21wbGV0ZWQifV0sICJoZWFkIjogImFmZmU4N2VmYjExZWE0MDU1MDMzNDlkZjc0MTliN2U4NDk1YzdhYmMifX0sICJzb3VyY2UiOiB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJjcmVhdGVkX2F0IjogIjIwMjYtMDktMjZUMTg6MDU6MDlaIiwgImV2ZW50IjogInNjaGVkdWxlIiwgImhlYWRfc2hhIjogImZkNjg2NTA0NzIxODhlNmNkZGVkNGQ0ZTZhYTViMWE0NTI3NzRmNzIiLCAiaWQiOiAzNjI2MTI5NDc3NCwgInJ1bl9hdHRlbXB0IjogMSwgInJ1bl9zdGFydGVkX2F0IjogIjIwMjYtMDktMjZUMTg6MDU6MDlaIiwgInN0YXR1cyI6ICJjb21wbGV0ZWQifSwgIndvcmtmbG93cyI6IHsiYmluYW5jZS11c2RtLWRldGFpbGVkLXRyYWluaW5nLXYwLTEueW1sIjogeyJjb25jbHVzaW9uIjogInN1Y2Nlc3MiLCAiY3JlYXRlZF9hdCI6ICIyMDI2LTA5LTIwVDA5OjI1OjA2WiIsICJldmVudCI6ICJzY2hlZHVsZSIsICJoZWFkX3NoYSI6ICI1Mjk1ZjdkMWQ4ZDFiZjQ2ZTY2NTUxNDQ1MjJjNjJhMTIzM2I5Y2MzIiwgImlkIjogMzU1MDIyNDk4NDYsICJydW5fYXR0ZW1wdCI6IDEsICJydW5fc3RhcnRlZF9hdCI6ICIyMDI2LTA5LTIwVDA5OjI1OjA2WiIsICJzdGF0dXMiOiAiY29tcGxldGVkIn0sICJkYXNoYm9hcmQtZ2l0aHViLXBhZ2VzLnltbCI6IHsiY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgImNyZWF0ZWRfYXQiOiAiMjAyNi0wOS0yNlQwOTozMDozM1oiLCAiZXZlbnQiOiAic2NoZWR1bGUiLCAiaGVhZF9zaGEiOiAiZmQ2ODY1MDQ3MjE4OGU2Y2RkZWQ0ZDRlNmFhNWIxYTQ1Mjc3NGY3MiIsICJpZCI6IDM2MjMyOTkxOTQzLCAicnVuX2F0dGVtcHQiOiAxLCAicnVuX3N0YXJ0ZWRfYXQiOiAiMjAyNi0wOS0yNlQwOTozMDozM1oiLCAic3RhdHVzIjogImNvbXBsZXRlZCJ9LCAicGlvbmV4LWFsdGVybmF0aXZlLWFzc2V0cy1vYnNlcnZhYmlsaXR5LXYwLTIueW1sIjogeyJjb25jbHVzaW9uIjogInN1Y2Nlc3MiLCAiY3JlYXRlZF9hdCI6ICIyMDI2LTA5LTIwVDA4OjUwOjEyWiIsICJldmVudCI6ICJzY2hlZHVsZSIsICJoZWFkX3NoYSI6ICI1Mjk1ZjdkMWQ4ZDFiZjQ2ZTY2NTUxNDQ1MjJjNjJhMTIzM2I5Y2MzIiwgImlkIjogMzU1MDA2NTIxNTAsICJydW5fYXR0ZW1wdCI6IDEsICJydW5fc3RhcnRlZF9hdCI6ICIyMDI2LTA5LTIwVDA4OjUwOjEyWiIsICJzdGF0dXMiOiAiY29tcGxldGVkIn0sICJwcm92aWRlci1lcXVpdmFsZW5jZS12MC0xMi1zdWNjZXNzb3ItbWV0YWRhdGEtY2FwdHVyZS55bWwiOiBudWxsLCAicmVzZWFyY2gtYXV0b21hdGlvbi1oZWFsdGgtdjAtMi55bWwiOiB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJjcmVhdGVkX2F0IjogIjIwMjYtMDktMjZUMTg6MDU6MDlaIiwgImV2ZW50IjogInNjaGVkdWxlIiwgImhlYWRfc2hhIjogImZkNjg2NTA0NzIxODhlNmNkZGVkNGQ0ZTZhYTViMWE0NTI3NzRmNzIiLCAiaWQiOiAzNjI2MTI5NDc3NCwgInJ1bl9hdHRlbXB0IjogMSwgInJ1bl9zdGFydGVkX2F0IjogIjIwMjYtMDktMjZUMTg6MDU6MDlaIiwgInN0YXR1cyI6ICJjb21wbGV0ZWQifSwgInJlc2VhcmNoLXNpZ25hbC1sYXllci12MC0yLnltbCI6IHsiY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgImNyZWF0ZWRfYXQiOiAiMjAyNi0wOS0yNlQwNzo0Nzo1MFoiLCAiZXZlbnQiOiAic2NoZWR1bGUiLCAiaGVhZF9zaGEiOiAiMzRkMWEwMzc0ZjVlMjNmMWMzMzhlNGM5YWJlYjAyNGRhMzMyMjA2OCIsICJpZCI6IDM2MjI3ODY3OTA3LCAicnVuX2F0dGVtcHQiOiAxLCAicnVuX3N0YXJ0ZWRfYXQiOiAiMjAyNi0wOS0yNlQwNzo0Nzo1MFoiLCAic3RhdHVzIjogImNvbXBsZXRlZCJ9LCAicmVzZWFyY2gtc2lnbmFsLXF1YWxpdHktdjAtMS55bWwiOiB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJjcmVhdGVkX2F0IjogIjIwMjYtMDktMjZUMDg6MDA6NDFaIiwgImV2ZW50IjogInNjaGVkdWxlIiwgImhlYWRfc2hhIjogIjM0ZDFhMDM3NGY1ZTIzZjFjMzM4ZTRjOWFiZWIwMjRkYTMzMjIwNjgiLCAiaWQiOiAzNjIyODQ5Njg3MSwgInJ1bl9hdHRlbXB0IjogMSwgInJ1bl9zdGFydGVkX2F0IjogIjIwMjYtMDktMjZUMDg6MDA6NDFaIiwgInN0YXR1cyI6ICJjb21wbGV0ZWQifSwgInJlc291cmNlLWh1Yi1zdXBwbHktY2hhaW4tdjAtMi55bWwiOiB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJjcmVhdGVkX2F0IjogIjIwMjYtMDktMjZUMDY6MDY6MjdaIiwgImV2ZW50IjogInNjaGVkdWxlIiwgImhlYWRfc2hhIjogIjkxYWI3NmM4MzA3YzAwNDcwYmQxNzVkN2RjM2M1YmM3MDhiZDMzOTMiLCAiaWQiOiAzNjIyMjc1NDQxNSwgInJ1bl9hdHRlbXB0IjogMSwgInJ1bl9zdGFydGVkX2F0IjogIjIwMjYtMDktMjZUMDY6MDY6MjdaIiwgInN0YXR1cyI6ICJjb21wbGV0ZWQifX19LCAic2NoZW1hIjogImNsb3VkLXByb2plY3QtbWFpbnRlbmFuY2UtdjAuMSIsICJzZW1hbnRpYyI6IHsibmV4dF9hY3Rpb24iOiAiXHU1N2Y3XHU4ODRjIENMT1VELTAxXHVmZjFhXHU0ZWU1IGN1cnJlbnQgbWFpbiBcdTgyMDdcdTczZmVcdTY3MDkgb3BlbiBQUiBcdTcwYmFcdTZlOTZcdWZmMGNcdTViOGNcdTYyMTBcdTk2ZjJcdTdhZWZcdTdkYWRcdThiNzdcdTgxZWFcdTcxMzZcdTlhNTdcdTY1MzZcdTMwMDIiLCAicHJzIjogW3siY2hlY2tzIjogIlNVQ0NFU1MiLCAiaGVhZCI6ICJkN2U4NThiNjQ1NmE5NDQ0NDExODRhMjgzNDgxYWMwYWJiYjI2NjBkIiwgIm51bWJlciI6IDUzMiwgInN0YXRlIjogIkRSQUZUIn0sIHsiY2hlY2tzIjogIkNPTVBMRVRFRF9XSVRIX1NLSVBTIiwgImhlYWQiOiAiYWZmZTg3ZWZiMTFlYTQwNTUwMzM0OWRmNzQxOWI3ZTg0OTVjN2FiYyIsICJudW1iZXIiOiA1MzQsICJzdGF0ZSI6ICJEUkFGVCJ9XSwgInNvdXJjZV9oZWFsdGgiOiB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJzdGF0dXMiOiAiY29tcGxldGVkIn0sICJ3b3JrZmxvd3MiOiBbeyJjb25jbHVzaW9uIjogInN1Y2Nlc3MiLCAiaGVhbHRoIjogIkhFQUxUSFlfQ09ORElUSU9OQUwiLCAiam9icyI6IFtdLCAicmVnaXN0cmF0aW9uIjogImFjdGl2ZSIsICJ3b3JrZmxvdyI6ICJiaW5hbmNlLXVzZG0tZGV0YWlsZWQtdHJhaW5pbmctdjAtMS55bWwifSwgeyJjb25jbHVzaW9uIjogInN1Y2Nlc3MiLCAiaGVhbHRoIjogIkhFQUxUSFkiLCAiam9icyI6IFtbImJ1aWxkIiwgInN1Y2Nlc3MiXSwgWyJkZXBsb3kiLCAic3VjY2VzcyJdLCBbImJyb3dzZXItcHJvZHVjdGlvbiIsICJzdWNjZXNzIl1dLCAicmVnaXN0cmF0aW9uIjogImFjdGl2ZSIsICJ3b3JrZmxvdyI6ICJkYXNoYm9hcmQtZ2l0aHViLXBhZ2VzLnltbCJ9LCB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJoZWFsdGgiOiAiSEVBTFRIWSIsICJqb2JzIjogW10sICJyZWdpc3RyYXRpb24iOiAiYWN0aXZlIiwgIndvcmtmbG93IjogInBpb25leC1hbHRlcm5hdGl2ZS1hc3NldHMtb2JzZXJ2YWJpbGl0eS12MC0yLnltbCJ9LCB7ImNvbmNsdXNpb24iOiAiVU5LTk9XTiIsICJoZWFsdGgiOiAiRVhQRUNURURfU1RPUCIsICJqb2JzIjogW10sICJyZWdpc3RyYXRpb24iOiAiYWN0aXZlIiwgIndvcmtmbG93IjogInByb3ZpZGVyLWVxdWl2YWxlbmNlLXYwLTEyLXN1Y2Nlc3Nvci1tZXRhZGF0YS1jYXB0dXJlLnltbCJ9LCB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJoZWFsdGgiOiAiSEVBTFRIWSIsICJqb2JzIjogW10sICJyZWdpc3RyYXRpb24iOiAiYWN0aXZlIiwgIndvcmtmbG93IjogInJlc2VhcmNoLWF1dG9tYXRpb24taGVhbHRoLXYwLTIueW1sIn0sIHsiY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgImhlYWx0aCI6ICJIRUFMVEhZIiwgImpvYnMiOiBbXSwgInJlZ2lzdHJhdGlvbiI6ICJhY3RpdmUiLCAid29ya2Zsb3ciOiAicmVzZWFyY2gtc2lnbmFsLWxheWVyLXYwLTIueW1sIn0sIHsiY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgImhlYWx0aCI6ICJIRUFMVEhZIiwgImpvYnMiOiBbXSwgInJlZ2lzdHJhdGlvbiI6ICJhY3RpdmUiLCAid29ya2Zsb3ciOiAicmVzZWFyY2gtc2lnbmFsLXF1YWxpdHktdjAtMS55bWwifSwgeyJjb25jbHVzaW9uIjogInN1Y2Nlc3MiLCAiaGVhbHRoIjogIkhFQUxUSFkiLCAiam9icyI6IFtdLCAicmVnaXN0cmF0aW9uIjogImFjdGl2ZSIsICJ3b3JrZmxvdyI6ICJyZXNvdXJjZS1odWItc3VwcGx5LWNoYWluLXYwLTIueW1sIn1dfX0= -->

### 雲端維護觀測（非執行權限）

- 此次證據基準 main：`fd68650472188e6cdded4d4e6aa5b1a452774f72`；不是永久最新 main。
- 語意摘要：`ec96eba34a7a87181ca905d1c3cf5633c5fa9f90fac249e85433702828d46c69`。
- 本機工作：EXCLUDED_BY_USER；研究結果：UNKNOWN_FROM_METADATA。
- 每次接續先重查 main；本區塊保留上次實質變更證據，不因時間戳更新。


觸發此輪的 Health：**success** （completed）；[run 36261294774, attempt 1](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36261294774)。
來源結果獨立保留；後續成功執行不覆蓋此次失敗。

| 工作 | 狀態 | 證據 |
| --- | --- | --- |
| `binance-usdm-detailed-training-v0-1.yml` | HEALTHY_CONDITIONAL / success / registration=active  | [run 35502249846](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/35502249846) |
| `dashboard-github-pages.yml` | HEALTHY / success / registration=active build=success; deploy=success; browser-production=success | [run 36232991943](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36232991943) |
| `pionex-alternative-assets-observability-v0-2.yml` | HEALTHY / success / registration=active  | [run 35500652150](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/35500652150) |
| `provider-equivalence-v0-12-successor-metadata-capture.yml` | EXPECTED_STOP / UNKNOWN / registration=active  | UNKNOWN／無適用 run |
| `research-automation-health-v0-2.yml` | HEALTHY / success / registration=active  | [run 36261294774](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36261294774) |
| `research-signal-layer-v0-2.yml` | HEALTHY / success / registration=active  | [run 36227867907](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36227867907) |
| `research-signal-quality-v0-1.yml` | HEALTHY / success / registration=active  | [run 36228496871](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36228496871) |
| `resource-hub-supply-chain-v0-2.yml` | HEALTHY / success / registration=active  | [run 36222754415](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36222754415) |
| PR #532 | DRAFT / SUCCESS | [PR](https://github.com/qookey109-pixel/crypto-autopilot/pull/532) |
| PR #534 | DRAFT / COMPLETED_WITH_SKIPS | [PR](https://github.com/qookey109-pixel/crypto-autopilot/pull/534) |

下一步：執行 CLOUD-01：以 current main 與現有 open PR 為準，完成雲端維護自然驗收。
<!-- cloud-maintenance:v0.1:end -->

## Cloud Paper product delivery — September 27

Current priority is the approved full cloud simulation loop, tracked by [delivery status](../research/status/cloud-paper-delivery-v0-1.json) and [bounded contract](../config/cloud_paper_loop_v0_1.json). Execute the five batches in order: contract → public-market adapter → persistent simulation → controlled activation → dashboard. CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER applies. Reuse the existing Work Item intake; this section is navigation, not a second queue. Do not use completed UI/document delivery as proof of product completion. Production NO_TRADE with an empty approved registry is valid; synthetic trading evidence belongs only in cloud CI. Initial account creation must contain zero trades. Activation needs separate exact implementation/CI/free-only/controlled-main evidence. Existing cron declarations and runtime expiry gates are unchanged during preparation.
