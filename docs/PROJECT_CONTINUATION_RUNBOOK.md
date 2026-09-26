# 專案接續與排程手冊

更新：2026-09-26。適用任何能讀取 Repository 與 GitHub metadata 的模型.
這是操作與交接規格；正式權限由即時 `main` 的版本化 config／receipt 決定。
無法取得工具、來源或權限時，回報缺口，不能靠舊聊天補出成功結果。

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
| 自 2026-09-23 起取得至少 7 天觀測後 | 整理 delay／missing／cancelled／重複／duration；列 coverage、樣本量、未知值，再提 cadence 建議 |
| 2026-10-01 08:00 之後 | 確認 Pionex window 轉 EXPIRED；authority 未變時預期有效 6／到期 2；不延期或建立 successor |

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
- 下一步：CLOUD-01 自然驗收已完成；維持既有 Health / Maintenance 行為，不再補跑驗收。下一個固定檢查點是 2026-09-27 的 Pionex bounded observability 與 Weekly Training 自然 schedule。Core100 V0.2 一次性 bootstrap 已完成且模型品質保持 `REJECT`；禁止 rerun、放寬門檻、推論 promotion 或 source switch。Auto-merge 仍只對逐 PR、通過 exact head/base、必要 review／CI 與 authority boundary 的交付使用。

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
- 未加入新 artifact 儲存；metadata 證據放 Actions summary。至少七天完整觀測後才提出 cadence 建議，不自動改頻率。
- 本文件標記內資料是上次「實質變更」的證據基準；最新狀態需讀本輪 summary 和 live main。

<!-- cloud-maintenance:v0.1:begin -->
<!-- record:eyJldmlkZW5jZSI6IHsiY292ZXJhZ2UiOiBbeyJjb21wbGV0ZSI6IHRydWUsICJmaWx0ZXJzIjogeyJicmFuY2giOiAibWFpbiIsICJjcmVhdGVkIjogIj49MjAyNi0wOS0xMlQxMzoyNTo1OC44MzIwNzBaIiwgImV2ZW50IjogInNjaGVkdWxlIn0sICJwYWdlcyI6IDEsICJwYXRoIjogIi9hY3Rpb25zL3dvcmtmbG93cy9yZXNlYXJjaC1zaWduYWwtbGF5ZXItdjAtMi55bWwvcnVucyIsICJyb3dzIjogMTR9LCB7ImNvbXBsZXRlIjogdHJ1ZSwgImZpbHRlcnMiOiB7ImJyYW5jaCI6ICJtYWluIiwgImNyZWF0ZWQiOiAiPj0yMDI2LTA5LTEyVDEzOjI1OjU4LjgzMjA3MFoiLCAiZXZlbnQiOiAic2NoZWR1bGUifSwgInBhZ2VzIjogMSwgInBhdGgiOiAiL2FjdGlvbnMvd29ya2Zsb3dzL3Jlc2VhcmNoLXNpZ25hbC1xdWFsaXR5LXYwLTEueW1sL3J1bnMiLCAicm93cyI6IDE0fSwgeyJjb21wbGV0ZSI6IHRydWUsICJmaWx0ZXJzIjogeyJicmFuY2giOiAibWFpbiIsICJjcmVhdGVkIjogIj49MjAyNi0wOS0xMlQxMzoyNTo1OC44MzIwNzBaIiwgImV2ZW50IjogInNjaGVkdWxlIn0sICJwYWdlcyI6IDEsICJwYXRoIjogIi9hY3Rpb25zL3dvcmtmbG93cy9yZXNlYXJjaC1hdXRvbWF0aW9uLWhlYWx0aC12MC0yLnltbC9ydW5zIiwgInJvd3MiOiA3M30sIHsiY29tcGxldGUiOiB0cnVlLCAiZmlsdGVycyI6IHsiYnJhbmNoIjogIm1haW4iLCAiY3JlYXRlZCI6ICI+PTIwMjYtMDktMTJUMTM6MjU6NTguODMyMDcwWiIsICJldmVudCI6ICJzY2hlZHVsZSJ9LCAicGFnZXMiOiAxLCAicGF0aCI6ICIvYWN0aW9ucy93b3JrZmxvd3MvYmluYW5jZS11c2RtLWRldGFpbGVkLXRyYWluaW5nLXYwLTEueW1sL3J1bnMiLCAicm93cyI6IDJ9LCB7ImNvbXBsZXRlIjogdHJ1ZSwgImZpbHRlcnMiOiB7ImJyYW5jaCI6ICJtYWluIiwgImNyZWF0ZWQiOiAiPj0yMDI2LTA5LTEyVDEzOjI1OjU4LjgzMjA3MFoiLCAiZXZlbnQiOiAic2NoZWR1bGUifSwgInBhZ2VzIjogMSwgInBhdGgiOiAiL2FjdGlvbnMvd29ya2Zsb3dzL3Bpb25leC1hbHRlcm5hdGl2ZS1hc3NldHMtb2JzZXJ2YWJpbGl0eS12MC0yLnltbC9ydW5zIiwgInJvd3MiOiAyfSwgeyJjb21wbGV0ZSI6IHRydWUsICJmaWx0ZXJzIjogeyJicmFuY2giOiAibWFpbiIsICJjcmVhdGVkIjogIj49MjAyNi0wOS0xMlQxMzoyNTo1OC44MzIwNzBaIiwgImV2ZW50IjogInNjaGVkdWxlIn0sICJwYWdlcyI6IDEsICJwYXRoIjogIi9hY3Rpb25zL3dvcmtmbG93cy9yZXNvdXJjZS1odWItc3VwcGx5LWNoYWluLXYwLTIueW1sL3J1bnMiLCAicm93cyI6IDV9LCB7ImNvbXBsZXRlIjogdHJ1ZSwgImZpbHRlcnMiOiB7ImJyYW5jaCI6ICJtYWluIiwgImNyZWF0ZWQiOiAiPj0yMDI2LTA5LTEyVDEzOjI1OjU4LjgzMjA3MFoiLCAiZXZlbnQiOiAic2NoZWR1bGUifSwgInBhZ2VzIjogMSwgInBhdGgiOiAiL2FjdGlvbnMvd29ya2Zsb3dzL2Rhc2hib2FyZC1naXRodWItcGFnZXMueW1sL3J1bnMiLCAicm93cyI6IDZ9LCB7ImNvbXBsZXRlIjogdHJ1ZSwgImZpbHRlcnMiOiB7fSwgInBhZ2VzIjogMSwgInBhdGgiOiAiL2FjdGlvbnMvcnVucy8zNjIzMjk5MTk0My9hdHRlbXB0cy8xL2pvYnMiLCAicm93cyI6IDN9LCB7ImNvbXBsZXRlIjogdHJ1ZSwgImZpbHRlcnMiOiB7ImJhc2UiOiAibWFpbiIsICJzdGF0ZSI6ICJvcGVuIn0sICJwYWdlcyI6IDEsICJwYXRoIjogIi9wdWxscyIsICJyb3dzIjogMX0sIHsiY29tcGxldGUiOiB0cnVlLCAiZmlsdGVycyI6IHt9LCAicGFnZXMiOiAxLCAicGF0aCI6ICIvY29tbWl0cy9kN2U4NThiNjQ1NmE5NDQ0NDExODRhMjgzNDgxYWMwYWJiYjI2NjBkL2NoZWNrLXJ1bnMiLCAicm93cyI6IDV9LCB7ImNvbXBsZXRlIjogdHJ1ZSwgImZpbHRlcnMiOiB7ImJhc2UiOiAibWFpbiIsICJzdGF0ZSI6ICJvcGVuIn0sICJwYWdlcyI6IDEsICJwYXRoIjogIi9wdWxscyIsICJyb3dzIjogMX1dLCAibWFpbl9zaGEiOiAiZmQ2ODY1MDQ3MjE4OGU2Y2RkZWQ0ZDRlNmFhNWIxYTQ1Mjc3NGY3MiIsICJvYnNlcnZlZF9hdF91dGMiOiAiMjAyNi0wOS0yNlQxMzoyNTo1OC44MzIwNzArMDA6MDAiLCAicHJzIjogeyI1MzIiOiB7ImJhc2UiOiAiZmQ2ODY1MDQ3MjE4OGU2Y2RkZWQ0ZDRlNmFhNWIxYTQ1Mjc3NGY3MiIsICJjaGVja3MiOiBbeyJjb25jbHVzaW9uIjogInN1Y2Nlc3MiLCAibmFtZSI6ICJ0ZXN0ICgzLjEzKSIsICJzdGF0dXMiOiAiY29tcGxldGVkIn0sIHsiY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgIm5hbWUiOiAidGVzdCAoMy4xMikiLCAic3RhdHVzIjogImNvbXBsZXRlZCJ9LCB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJuYW1lIjogIndvcmtmbG93LXN0YXRpYyIsICJzdGF0dXMiOiAiY29tcGxldGVkIn0sIHsiY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgIm5hbWUiOiAiQ29kZVFMIHZpc2liaWxpdHkgKFB5dGhvbikiLCAic3RhdHVzIjogImNvbXBsZXRlZCJ9LCB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJuYW1lIjogImRlcGVuZGVuY3ktc2VjdXJpdHkiLCAic3RhdHVzIjogImNvbXBsZXRlZCJ9XSwgImhlYWQiOiAiZDdlODU4YjY0NTZhOTQ0NDQxMTg0YTI4MzQ4MWFjMGFiYmIyNjYwZCJ9fSwgInNvdXJjZSI6IHsiY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgImNyZWF0ZWRfYXQiOiAiMjAyNi0wOS0yNlQxMzoyNDozNFoiLCAiZXZlbnQiOiAic2NoZWR1bGUiLCAiaGVhZF9zaGEiOiAiZmQ2ODY1MDQ3MjE4OGU2Y2RkZWQ0ZDRlNmFhNWIxYTQ1Mjc3NGY3MiIsICJpZCI6IDM2MjQ1MDYzMDQ3LCAicnVuX2F0dGVtcHQiOiAxLCAicnVuX3N0YXJ0ZWRfYXQiOiAiMjAyNi0wOS0yNlQxMzoyNDozNFoiLCAic3RhdHVzIjogImNvbXBsZXRlZCJ9LCAid29ya2Zsb3dzIjogeyJiaW5hbmNlLXVzZG0tZGV0YWlsZWQtdHJhaW5pbmctdjAtMS55bWwiOiB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJjcmVhdGVkX2F0IjogIjIwMjYtMDktMjBUMDk6MjU6MDZaIiwgImV2ZW50IjogInNjaGVkdWxlIiwgImhlYWRfc2hhIjogIjUyOTVmN2QxZDhkMWJmNDZlNjY1NTE0NDUyMmM2MmExMjMzYjljYzMiLCAiaWQiOiAzNTUwMjI0OTg0NiwgInJ1bl9hdHRlbXB0IjogMSwgInJ1bl9zdGFydGVkX2F0IjogIjIwMjYtMDktMjBUMDk6MjU6MDZaIiwgInN0YXR1cyI6ICJjb21wbGV0ZWQifSwgImRhc2hib2FyZC1naXRodWItcGFnZXMueW1sIjogeyJjb25jbHVzaW9uIjogInN1Y2Nlc3MiLCAiY3JlYXRlZF9hdCI6ICIyMDI2LTA5LTI2VDA5OjMwOjMzWiIsICJldmVudCI6ICJzY2hlZHVsZSIsICJoZWFkX3NoYSI6ICJmZDY4NjUwNDcyMTg4ZTZjZGRlZDRkNGU2YWE1YjFhNDUyNzc0ZjcyIiwgImlkIjogMzYyMzI5OTE5NDMsICJydW5fYXR0ZW1wdCI6IDEsICJydW5fc3RhcnRlZF9hdCI6ICIyMDI2LTA5LTI2VDA5OjMwOjMzWiIsICJzdGF0dXMiOiAiY29tcGxldGVkIn0sICJwaW9uZXgtYWx0ZXJuYXRpdmUtYXNzZXRzLW9ic2VydmFiaWxpdHktdjAtMi55bWwiOiB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJjcmVhdGVkX2F0IjogIjIwMjYtMDktMjBUMDg6NTA6MTJaIiwgImV2ZW50IjogInNjaGVkdWxlIiwgImhlYWRfc2hhIjogIjUyOTVmN2QxZDhkMWJmNDZlNjY1NTE0NDUyMmM2MmExMjMzYjljYzMiLCAiaWQiOiAzNTUwMDY1MjE1MCwgInJ1bl9hdHRlbXB0IjogMSwgInJ1bl9zdGFydGVkX2F0IjogIjIwMjYtMDktMjBUMDg6NTA6MTJaIiwgInN0YXR1cyI6ICJjb21wbGV0ZWQifSwgInByb3ZpZGVyLWVxdWl2YWxlbmNlLXYwLTEyLXN1Y2Nlc3Nvci1tZXRhZGF0YS1jYXB0dXJlLnltbCI6IG51bGwsICJyZXNlYXJjaC1hdXRvbWF0aW9uLWhlYWx0aC12MC0yLnltbCI6IHsiY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgImNyZWF0ZWRfYXQiOiAiMjAyNi0wOS0yNlQxMzoyNDozNFoiLCAiZXZlbnQiOiAic2NoZWR1bGUiLCAiaGVhZF9zaGEiOiAiZmQ2ODY1MDQ3MjE4OGU2Y2RkZWQ0ZDRlNmFhNWIxYTQ1Mjc3NGY3MiIsICJpZCI6IDM2MjQ1MDYzMDQ3LCAicnVuX2F0dGVtcHQiOiAxLCAicnVuX3N0YXJ0ZWRfYXQiOiAiMjAyNi0wOS0yNlQxMzoyNDozNFoiLCAic3RhdHVzIjogImNvbXBsZXRlZCJ9LCAicmVzZWFyY2gtc2lnbmFsLWxheWVyLXYwLTIueW1sIjogeyJjb25jbHVzaW9uIjogInN1Y2Nlc3MiLCAiY3JlYXRlZF9hdCI6ICIyMDI2LTA5LTI2VDA3OjQ3OjUwWiIsICJldmVudCI6ICJzY2hlZHVsZSIsICJoZWFkX3NoYSI6ICIzNGQxYTAzNzRmNWUyM2YxYzMzOGU0YzlhYmViMDI0ZGEzMzIyMDY4IiwgImlkIjogMzYyMjc4Njc5MDcsICJydW5fYXR0ZW1wdCI6IDEsICJydW5fc3RhcnRlZF9hdCI6ICIyMDI2LTA5LTI2VDA3OjQ3OjUwWiIsICJzdGF0dXMiOiAiY29tcGxldGVkIn0sICJyZXNlYXJjaC1zaWduYWwtcXVhbGl0eS12MC0xLnltbCI6IHsiY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgImNyZWF0ZWRfYXQiOiAiMjAyNi0wOS0yNlQwODowMDo0MVoiLCAiZXZlbnQiOiAic2NoZWR1bGUiLCAiaGVhZF9zaGEiOiAiMzRkMWEwMzc0ZjVlMjNmMWMzMzhlNGM5YWJlYjAyNGRhMzMyMjA2OCIsICJpZCI6IDM2MjI4NDk2ODcxLCAicnVuX2F0dGVtcHQiOiAxLCAicnVuX3N0YXJ0ZWRfYXQiOiAiMjAyNi0wOS0yNlQwODowMDo0MVoiLCAic3RhdHVzIjogImNvbXBsZXRlZCJ9LCAicmVzb3VyY2UtaHViLXN1cHBseS1jaGFpbi12MC0yLnltbCI6IHsiY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgImNyZWF0ZWRfYXQiOiAiMjAyNi0wOS0yNlQwNjowNjoyN1oiLCAiZXZlbnQiOiAic2NoZWR1bGUiLCAiaGVhZF9zaGEiOiAiOTFhYjc2YzgzMDdjMDA0NzBiZDE3NWQ3ZGMzYzViYzcwOGJkMzM5MyIsICJpZCI6IDM2MjIyNzU0NDE1LCAicnVuX2F0dGVtcHQiOiAxLCAicnVuX3N0YXJ0ZWRfYXQiOiAiMjAyNi0wOS0yNlQwNjowNjoyN1oiLCAic3RhdHVzIjogImNvbXBsZXRlZCJ9fX0sICJzY2hlbWEiOiAiY2xvdWQtcHJvamVjdC1tYWludGVuYW5jZS12MC4xIiwgInNlbWFudGljIjogeyJuZXh0X2FjdGlvbiI6ICJcdTU3ZjdcdTg4NGMgQ0xPVUQtMDFcdWZmMWFcdTRlZTUgY3VycmVudCBtYWluIFx1ODIwN1x1NzNmZVx1NjcwOSBvcGVuIFBSIFx1NzBiYVx1NmU5Nlx1ZmYwY1x1NWI4Y1x1NjIxMFx1OTZmMlx1N2FlZlx1N2RhZFx1OGI3N1x1ODFlYVx1NzEzNlx1OWE1N1x1NjUzNlx1MzAwMiIsICJwcnMiOiBbeyJjaGVja3MiOiAiU1VDQ0VTUyIsICJoZWFkIjogImQ3ZTg1OGI2NDU2YTk0NDQ0MTE4NGEyODM0ODFhYzBhYmJiMjY2MGQiLCAibnVtYmVyIjogNTMyLCAic3RhdGUiOiAiRFJBRlQifV0sICJzb3VyY2VfaGVhbHRoIjogeyJjb25jbHVzaW9uIjogInN1Y2Nlc3MiLCAic3RhdHVzIjogImNvbXBsZXRlZCJ9LCAid29ya2Zsb3dzIjogW3siY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgImhlYWx0aCI6ICJIRUFMVEhZX0NPTkRJVElPTkFMIiwgImpvYnMiOiBbXSwgInJlZ2lzdHJhdGlvbiI6ICJhY3RpdmUiLCAid29ya2Zsb3ciOiAiYmluYW5jZS11c2RtLWRldGFpbGVkLXRyYWluaW5nLXYwLTEueW1sIn0sIHsiY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgImhlYWx0aCI6ICJIRUFMVEhZIiwgImpvYnMiOiBbWyJidWlsZCIsICJzdWNjZXNzIl0sIFsiZGVwbG95IiwgInN1Y2Nlc3MiXSwgWyJicm93c2VyLXByb2R1Y3Rpb24iLCAic3VjY2VzcyJdXSwgInJlZ2lzdHJhdGlvbiI6ICJhY3RpdmUiLCAid29ya2Zsb3ciOiAiZGFzaGJvYXJkLWdpdGh1Yi1wYWdlcy55bWwifSwgeyJjb25jbHVzaW9uIjogInN1Y2Nlc3MiLCAiaGVhbHRoIjogIkhFQUxUSFkiLCAiam9icyI6IFtdLCAicmVnaXN0cmF0aW9uIjogImFjdGl2ZSIsICJ3b3JrZmxvdyI6ICJwaW9uZXgtYWx0ZXJuYXRpdmUtYXNzZXRzLW9ic2VydmFiaWxpdHktdjAtMi55bWwifSwgeyJjb25jbHVzaW9uIjogIlVOS05PV04iLCAiaGVhbHRoIjogIkVYUEVDVEVEX1NUT1AiLCAiam9icyI6IFtdLCAicmVnaXN0cmF0aW9uIjogImFjdGl2ZSIsICJ3b3JrZmxvdyI6ICJwcm92aWRlci1lcXVpdmFsZW5jZS12MC0xMi1zdWNjZXNzb3ItbWV0YWRhdGEtY2FwdHVyZS55bWwifSwgeyJjb25jbHVzaW9uIjogInN1Y2Nlc3MiLCAiaGVhbHRoIjogIkhFQUxUSFkiLCAiam9icyI6IFtdLCAicmVnaXN0cmF0aW9uIjogImFjdGl2ZSIsICJ3b3JrZmxvdyI6ICJyZXNlYXJjaC1hdXRvbWF0aW9uLWhlYWx0aC12MC0yLnltbCJ9LCB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJoZWFsdGgiOiAiSEVBTFRIWSIsICJqb2JzIjogW10sICJyZWdpc3RyYXRpb24iOiAiYWN0aXZlIiwgIndvcmtmbG93IjogInJlc2VhcmNoLXNpZ25hbC1sYXllci12MC0yLnltbCJ9LCB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJoZWFsdGgiOiAiSEVBTFRIWSIsICJqb2JzIjogW10sICJyZWdpc3RyYXRpb24iOiAiYWN0aXZlIiwgIndvcmtmbG93IjogInJlc2VhcmNoLXNpZ25hbC1xdWFsaXR5LXYwLTEueW1sIn0sIHsiY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgImhlYWx0aCI6ICJIRUFMVEhZIiwgImpvYnMiOiBbXSwgInJlZ2lzdHJhdGlvbiI6ICJhY3RpdmUiLCAid29ya2Zsb3ciOiAicmVzb3VyY2UtaHViLXN1cHBseS1jaGFpbi12MC0yLnltbCJ9XX19 -->

### 雲端維護觀測（非執行權限）

- 此次證據基準 main：`fd68650472188e6cdded4d4e6aa5b1a452774f72`；不是永久最新 main。
- 語意摘要：`c50cdd23d8d9eed486798f7edee192f72face72eebd84dd9e8f30c654c554ab7`。
- 本機工作：EXCLUDED_BY_USER；研究結果：UNKNOWN_FROM_METADATA。
- 每次接續先重查 main；本區塊保留上次實質變更證據，不因時間戳更新。


觸發此輪的 Health：**success** （completed）；[run 36245063047, attempt 1](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36245063047)。
來源結果獨立保留；後續成功執行不覆蓋此次失敗。

| 工作 | 狀態 | 證據 |
| --- | --- | --- |
| `binance-usdm-detailed-training-v0-1.yml` | HEALTHY_CONDITIONAL / success / registration=active  | [run 35502249846](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/35502249846) |
| `dashboard-github-pages.yml` | HEALTHY / success / registration=active build=success; deploy=success; browser-production=success | [run 36232991943](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36232991943) |
| `pionex-alternative-assets-observability-v0-2.yml` | HEALTHY / success / registration=active  | [run 35500652150](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/35500652150) |
| `provider-equivalence-v0-12-successor-metadata-capture.yml` | EXPECTED_STOP / UNKNOWN / registration=active  | UNKNOWN／無適用 run |
| `research-automation-health-v0-2.yml` | HEALTHY / success / registration=active  | [run 36245063047](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36245063047) |
| `research-signal-layer-v0-2.yml` | HEALTHY / success / registration=active  | [run 36227867907](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36227867907) |
| `research-signal-quality-v0-1.yml` | HEALTHY / success / registration=active  | [run 36228496871](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36228496871) |
| `resource-hub-supply-chain-v0-2.yml` | HEALTHY / success / registration=active  | [run 36222754415](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36222754415) |
| PR #532 | DRAFT / SUCCESS | [PR](https://github.com/qookey109-pixel/crypto-autopilot/pull/532) |

下一步：執行 CLOUD-01：以 current main 與現有 open PR 為準，完成雲端維護自然驗收。
<!-- cloud-maintenance:v0.1:end -->
