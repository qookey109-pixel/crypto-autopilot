# 專案接續與排程手冊

更新：2026-09-25。適用任何能讀取 Repository 與 GitHub metadata 的模型。
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
| TD-012 | 原本地提案仍保留於 handoffs/2026-09-23-core100-fingerprint-v0-2-proposal.md；Repository 準備文件見 [V0.2 review](CORE100_TRAINING_FINGERPRINT_V0_2.md)、[config](../config/core100_training_fingerprint_v0_2.json)、[receipt](../research/receipts/2026-09-24-core100-training-fingerprint-v0-2-prepared.json) | 31-path closure 分為 14 個 result-identity 與 17 個 runtime-guard 檔；純記憶體 comparator 與合成行為測試已準備，仍為 PREPARED_NOT_ACTIVE。下一步準備 successor cutover proposal，納入新模組／collector 的 import inventory、真實環境取證及 legacy baseline 處置。V0.1 runner 未修改；任何啟用仍需另有版本化 authority |
| 最新交接 | `handoffs/2026-09-23-project-checkpoint/README.md` | main／PR／驗證快照、原工作區狀態與新聊天接續文字；仍需 live 查核 |

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

| 時點（台北） | 工作與完成條件 |
| --- | --- |
| 既有 Health 自然完成後 | 唯讀健檢；Pages 自然 run `35843351924` 已成功，且其後自然 Health run `35870216734` 已 `PASS`、`alerts=0`。TD-010 已完成，後續只做正常健康監控並在新故障／恢復時更新 |
| Cloud Maintenance V0.1 首兩次自然驗收 | PR #498 已合併。自然 Health `36099624753` 成功後觸發維護 `36099661460`；inspect 成功，propose 回報 `BLOCKED_PERMISSION`。兩次成功自然維護驗收仍為 0/2。先核對 GitHub Actions 建立 PR 的設定與權限決策；不得以手動 dispatch／rerun 代替自然證據。其後取得兩個不同自然 Health 來源、完整 inspect／propose、至少一次 `NO_CHANGE` 且 `commits_created=0`。研究結果仍為 `UNKNOWN_FROM_METADATA`。 |
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
- Core100 History、Pionex V0.2、ZEC V0.3／V0.4 不重跑。fingerprint V0.2 準備不得覆寫舊 baseline、觸發訓練或建 R2 client。
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

- 目的：將維護程式交付為可審查 PR，合併後確認自然執行；不自動合併。
- 前置：讀 live main、Cloud Maintenance V0.1 contract／receipt、open PR。
- 起點：在本次 run summary／PR 填 exact main、head、base 及證據 URL，禁止使用固定舊 SHA。
- 步驟：
  1. 查 #497 整理紀錄及 #496 fingerprint PR。已合併則記 merge SHA；未合併則保留等待，不重做。
  2. 查維護交付 PR 的 Python 3.12／3.13、Ruff、workflow-static 與相關治理檢查。
  3. 需合併時列為 WAITING_USER_MERGE；缺檢查列 UNKNOWN，GitHub 要批准 CI 時列 WAITING_CI_APPROVAL。
  4. 合併後查首次自然 Health schedule 的 completion 是否觸發維護 inspect／propose；不 dispatch 補證據。
  5. 再查第二個不同自然 Health run；驗證維護兩次完整完成，其中無變化回合 NO_CHANGE 且 commits_created=0。
- 驗收：兩組 source run ID／attempt、main／head、兩個 job 結果、產生的 draft PR 或 NO_CHANGE 摘要；人工檢查 generated-block-only diff。
- 停止：main 前進、衝突、人工編輯、來源不可信、缺權限／資料、CI 失敗時轉 CLOUD-02；不得自動擴權。
- 交付：完成／等待／未知分列。CI、merge、維護自然執行、研究結果分開。
- 下一步：Cloud Maintenance V0.1 的 `BLOCKED_PERMISSION` 需先取得 GitHub 設定決策，之後才驗收兩次自然執行。Fingerprint V0.2 的提案與一次性授權已由 #501–#504 交付；審查草稿 PR #505 的 exact-head CI、successor contract／implementation receipt 與寫入失敗紀錄。#505 合併之前不得 dispatch；合併後的一次性執行仍須依版本化授權及即時 main 查核。

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
<!-- record:eyJldmlkZW5jZSI6IHsiY292ZXJhZ2UiOiBbeyJjb21wbGV0ZSI6IHRydWUsICJmaWx0ZXJzIjogeyJicmFuY2giOiAibWFpbiIsICJjcmVhdGVkIjogIj49MjAyNi0wOS0xMVQxMjoyMjo0Ny4yNTI3NTdaIiwgImV2ZW50IjogInNjaGVkdWxlIn0sICJwYWdlcyI6IDEsICJwYXRoIjogIi9hY3Rpb25zL3dvcmtmbG93cy9yZXNlYXJjaC1zaWduYWwtbGF5ZXItdjAtMi55bWwvcnVucyIsICJyb3dzIjogMTR9LCB7ImNvbXBsZXRlIjogdHJ1ZSwgImZpbHRlcnMiOiB7ImJyYW5jaCI6ICJtYWluIiwgImNyZWF0ZWQiOiAiPj0yMDI2LTA5LTExVDEyOjIyOjQ3LjI1Mjc1N1oiLCAiZXZlbnQiOiAic2NoZWR1bGUifSwgInBhZ2VzIjogMSwgInBhdGgiOiAiL2FjdGlvbnMvd29ya2Zsb3dzL3Jlc2VhcmNoLXNpZ25hbC1xdWFsaXR5LXYwLTEueW1sL3J1bnMiLCAicm93cyI6IDE0fSwgeyJjb21wbGV0ZSI6IHRydWUsICJmaWx0ZXJzIjogeyJicmFuY2giOiAibWFpbiIsICJjcmVhdGVkIjogIj49MjAyNi0wOS0xMVQxMjoyMjo0Ny4yNTI3NTdaIiwgImV2ZW50IjogInNjaGVkdWxlIn0sICJwYWdlcyI6IDEsICJwYXRoIjogIi9hY3Rpb25zL3dvcmtmbG93cy9yZXNlYXJjaC1hdXRvbWF0aW9uLWhlYWx0aC12MC0yLnltbC9ydW5zIiwgInJvd3MiOiA3NH0sIHsiY29tcGxldGUiOiB0cnVlLCAiZmlsdGVycyI6IHsiYnJhbmNoIjogIm1haW4iLCAiY3JlYXRlZCI6ICI+PTIwMjYtMDktMTFUMTI6MjI6NDcuMjUyNzU3WiIsICJldmVudCI6ICJzY2hlZHVsZSJ9LCAicGFnZXMiOiAxLCAicGF0aCI6ICIvYWN0aW9ucy93b3JrZmxvd3MvYmluYW5jZS11c2RtLWRldGFpbGVkLXRyYWluaW5nLXYwLTEueW1sL3J1bnMiLCAicm93cyI6IDJ9LCB7ImNvbXBsZXRlIjogdHJ1ZSwgImZpbHRlcnMiOiB7ImJyYW5jaCI6ICJtYWluIiwgImNyZWF0ZWQiOiAiPj0yMDI2LTA5LTExVDEyOjIyOjQ3LjI1Mjc1N1oiLCAiZXZlbnQiOiAic2NoZWR1bGUifSwgInBhZ2VzIjogMSwgInBhdGgiOiAiL2FjdGlvbnMvd29ya2Zsb3dzL3Bpb25leC1hbHRlcm5hdGl2ZS1hc3NldHMtb2JzZXJ2YWJpbGl0eS12MC0yLnltbC9ydW5zIiwgInJvd3MiOiAyfSwgeyJjb21wbGV0ZSI6IHRydWUsICJmaWx0ZXJzIjogeyJicmFuY2giOiAibWFpbiIsICJjcmVhdGVkIjogIj49MjAyNi0wOS0xMVQxMjoyMjo0Ny4yNTI3NTdaIiwgImV2ZW50IjogInNjaGVkdWxlIn0sICJwYWdlcyI6IDEsICJwYXRoIjogIi9hY3Rpb25zL3dvcmtmbG93cy9yZXNvdXJjZS1odWItc3VwcGx5LWNoYWluLXYwLTIueW1sL3J1bnMiLCAicm93cyI6IDR9LCB7ImNvbXBsZXRlIjogdHJ1ZSwgImZpbHRlcnMiOiB7ImJyYW5jaCI6ICJtYWluIiwgImNyZWF0ZWQiOiAiPj0yMDI2LTA5LTExVDEyOjIyOjQ3LjI1Mjc1N1oiLCAiZXZlbnQiOiAic2NoZWR1bGUifSwgInBhZ2VzIjogMSwgInBhdGgiOiAiL2FjdGlvbnMvd29ya2Zsb3dzL2Rhc2hib2FyZC1naXRodWItcGFnZXMueW1sL3J1bnMiLCAicm93cyI6IDV9LCB7ImNvbXBsZXRlIjogdHJ1ZSwgImZpbHRlcnMiOiB7fSwgInBhZ2VzIjogMSwgInBhdGgiOiAiL2FjdGlvbnMvcnVucy8zNjEyMDMxNTEyOS9hdHRlbXB0cy8xL2pvYnMiLCAicm93cyI6IDN9LCB7ImNvbXBsZXRlIjogdHJ1ZSwgImZpbHRlcnMiOiB7ImJhc2UiOiAibWFpbiIsICJzdGF0ZSI6ICJvcGVuIn0sICJwYWdlcyI6IDEsICJwYXRoIjogIi9wdWxscyIsICJyb3dzIjogMH0sIHsiY29tcGxldGUiOiB0cnVlLCAiZmlsdGVycyI6IHt9LCAicGFnZXMiOiAxLCAicGF0aCI6ICIvY29tbWl0cy9hNzg5YzFjYzcwZjQ4ODYzNTJjN2Y1NTgyZWYwZDZiYzUwYTMxYzVlL2NoZWNrLXJ1bnMiLCAicm93cyI6IDh9LCB7ImNvbXBsZXRlIjogdHJ1ZSwgImZpbHRlcnMiOiB7fSwgInBhZ2VzIjogMSwgInBhdGgiOiAiL2NvbW1pdHMvMWFhNzlmYTkxNzE5MDY1MDQ1YzQzYWNlMmMyNjk3N2QxMjE2ZDg1YS9jaGVjay1ydW5zIiwgInJvd3MiOiA0fSwgeyJjb21wbGV0ZSI6IHRydWUsICJmaWx0ZXJzIjogeyJiYXNlIjogIm1haW4iLCAic3RhdGUiOiAib3BlbiJ9LCAicGFnZXMiOiAxLCAicGF0aCI6ICIvcHVsbHMiLCAicm93cyI6IDB9XSwgIm1haW5fc2hhIjogIjQxYzc5OTk0YTgyYTMwZDkzODc3NGZmNTQwYzk3NzY3YzBhZDAxZDYiLCAib2JzZXJ2ZWRfYXRfdXRjIjogIjIwMjYtMDktMjVUMTI6MjI6NDcuMjUyNzU3KzAwOjAwIiwgInBycyI6IHsiNDk2IjogeyJiYXNlIjogImY5Mjk2YWNhMzM4NThjOTA3YjQyZTgyNWRiOGE5ZDMzNGRmMTk4NmUiLCAiY2hlY2tzIjogW3siY29uY2x1c2lvbiI6ICJza2lwcGVkIiwgIm5hbWUiOiAiYnJvd3Nlci1wcm9kdWN0aW9uIiwgInN0YXR1cyI6ICJjb21wbGV0ZWQifSwgeyJjb25jbHVzaW9uIjogInNraXBwZWQiLCAibmFtZSI6ICJkZXBsb3kiLCAic3RhdHVzIjogImNvbXBsZXRlZCJ9LCB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJuYW1lIjogInNuYXBzaG90IiwgInN0YXR1cyI6ICJjb21wbGV0ZWQifSwgeyJjb25jbHVzaW9uIjogInN1Y2Nlc3MiLCAibmFtZSI6ICJ0ZXN0ICgzLjEzKSIsICJzdGF0dXMiOiAiY29tcGxldGVkIn0sIHsiY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgIm5hbWUiOiAid29ya2Zsb3ctc3RhdGljIiwgInN0YXR1cyI6ICJjb21wbGV0ZWQifSwgeyJjb25jbHVzaW9uIjogInN1Y2Nlc3MiLCAibmFtZSI6ICJidWlsZCIsICJzdGF0dXMiOiAiY29tcGxldGVkIn0sIHsiY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgIm5hbWUiOiAiQ29kZVFMIHZpc2liaWxpdHkgKFB5dGhvbikiLCAic3RhdHVzIjogImNvbXBsZXRlZCJ9LCB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJuYW1lIjogInRlc3QgKDMuMTIpIiwgInN0YXR1cyI6ICJjb21wbGV0ZWQifV0sICJoZWFkIjogImE3ODljMWNjNzBmNDg4NjM1MmM3ZjU1ODJlZjBkNmJjNTBhMzFjNWUifSwgIjQ5NyI6IHsiYmFzZSI6ICJmOTI5NmFjYTMzODU4YzkwN2I0MmU4MjVkYjhhOWQzMzRkZjE5ODZlIiwgImNoZWNrcyI6IFt7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJuYW1lIjogInRlc3QgKDMuMTIpIiwgInN0YXR1cyI6ICJjb21wbGV0ZWQifSwgeyJjb25jbHVzaW9uIjogInN1Y2Nlc3MiLCAibmFtZSI6ICJ3b3JrZmxvdy1zdGF0aWMiLCAic3RhdHVzIjogImNvbXBsZXRlZCJ9LCB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJuYW1lIjogInRlc3QgKDMuMTMpIiwgInN0YXR1cyI6ICJjb21wbGV0ZWQifSwgeyJjb25jbHVzaW9uIjogInN1Y2Nlc3MiLCAibmFtZSI6ICJDb2RlUUwgdmlzaWJpbGl0eSAoUHl0aG9uKSIsICJzdGF0dXMiOiAiY29tcGxldGVkIn1dLCAiaGVhZCI6ICIxYWE3OWZhOTE3MTkwNjUwNDVjNDNhY2UyYzI2OTc3ZDEyMTZkODVhIn19LCAic291cmNlIjogeyJjb25jbHVzaW9uIjogInN1Y2Nlc3MiLCAiY3JlYXRlZF9hdCI6ICIyMDI2LTA5LTI1VDEyOjIxOjE4WiIsICJldmVudCI6ICJzY2hlZHVsZSIsICJoZWFkX3NoYSI6ICI0MWM3OTk5NGE4MmEzMGQ5Mzg3NzRmZjU0MGM5Nzc2N2MwYWQwMWQ2IiwgImlkIjogMzYxMzQ0NDA0NTYsICJydW5fYXR0ZW1wdCI6IDEsICJydW5fc3RhcnRlZF9hdCI6ICIyMDI2LTA5LTI1VDEyOjIxOjE4WiIsICJzdGF0dXMiOiAiY29tcGxldGVkIn0sICJ3b3JrZmxvd3MiOiB7ImJpbmFuY2UtdXNkbS1kZXRhaWxlZC10cmFpbmluZy12MC0xLnltbCI6IHsiY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgImNyZWF0ZWRfYXQiOiAiMjAyNi0wOS0yMFQwOToyNTowNloiLCAiZXZlbnQiOiAic2NoZWR1bGUiLCAiaGVhZF9zaGEiOiAiNTI5NWY3ZDFkOGQxYmY0NmU2NjU1MTQ0NTIyYzYyYTEyMzNiOWNjMyIsICJpZCI6IDM1NTAyMjQ5ODQ2LCAicnVuX2F0dGVtcHQiOiAxLCAicnVuX3N0YXJ0ZWRfYXQiOiAiMjAyNi0wOS0yMFQwOToyNTowNloiLCAic3RhdHVzIjogImNvbXBsZXRlZCJ9LCAiZGFzaGJvYXJkLWdpdGh1Yi1wYWdlcy55bWwiOiB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJjcmVhdGVkX2F0IjogIjIwMjYtMDktMjVUMDk6NDY6MjlaIiwgImV2ZW50IjogInNjaGVkdWxlIiwgImhlYWRfc2hhIjogIjQxYzc5OTk0YTgyYTMwZDkzODc3NGZmNTQwYzk3NzY3YzBhZDAxZDYiLCAiaWQiOiAzNjEyMDMxNTEyOSwgInJ1bl9hdHRlbXB0IjogMSwgInJ1bl9zdGFydGVkX2F0IjogIjIwMjYtMDktMjVUMDk6NDY6MjlaIiwgInN0YXR1cyI6ICJjb21wbGV0ZWQifSwgInBpb25leC1hbHRlcm5hdGl2ZS1hc3NldHMtb2JzZXJ2YWJpbGl0eS12MC0yLnltbCI6IHsiY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgImNyZWF0ZWRfYXQiOiAiMjAyNi0wOS0yMFQwODo1MDoxMloiLCAiZXZlbnQiOiAic2NoZWR1bGUiLCAiaGVhZF9zaGEiOiAiNTI5NWY3ZDFkOGQxYmY0NmU2NjU1MTQ0NTIyYzYyYTEyMzNiOWNjMyIsICJpZCI6IDM1NTAwNjUyMTUwLCAicnVuX2F0dGVtcHQiOiAxLCAicnVuX3N0YXJ0ZWRfYXQiOiAiMjAyNi0wOS0yMFQwODo1MDoxMloiLCAic3RhdHVzIjogImNvbXBsZXRlZCJ9LCAicHJvdmlkZXItZXF1aXZhbGVuY2UtdjAtMTItc3VjY2Vzc29yLW1ldGFkYXRhLWNhcHR1cmUueW1sIjogbnVsbCwgInJlc2VhcmNoLWF1dG9tYXRpb24taGVhbHRoLXYwLTIueW1sIjogeyJjb25jbHVzaW9uIjogInN1Y2Nlc3MiLCAiY3JlYXRlZF9hdCI6ICIyMDI2LTA5LTI1VDEyOjIxOjE4WiIsICJldmVudCI6ICJzY2hlZHVsZSIsICJoZWFkX3NoYSI6ICI0MWM3OTk5NGE4MmEzMGQ5Mzg3NzRmZjU0MGM5Nzc2N2MwYWQwMWQ2IiwgImlkIjogMzYxMzQ0NDA0NTYsICJydW5fYXR0ZW1wdCI6IDEsICJydW5fc3RhcnRlZF9hdCI6ICIyMDI2LTA5LTI1VDEyOjIxOjE4WiIsICJzdGF0dXMiOiAiY29tcGxldGVkIn0sICJyZXNlYXJjaC1zaWduYWwtbGF5ZXItdjAtMi55bWwiOiB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJjcmVhdGVkX2F0IjogIjIwMjYtMDktMjVUMDc6NTQ6MzhaIiwgImV2ZW50IjogInNjaGVkdWxlIiwgImhlYWRfc2hhIjogIjQxYzc5OTk0YTgyYTMwZDkzODc3NGZmNTQwYzk3NzY3YzBhZDAxZDYiLCAiaWQiOiAzNjExMDA3NTM0MSwgInJ1bl9hdHRlbXB0IjogMSwgInJ1bl9zdGFydGVkX2F0IjogIjIwMjYtMDktMjVUMDc6NTQ6MzhaIiwgInN0YXR1cyI6ICJjb21wbGV0ZWQifSwgInJlc2VhcmNoLXNpZ25hbC1xdWFsaXR5LXYwLTEueW1sIjogeyJjb25jbHVzaW9uIjogInN1Y2Nlc3MiLCAiY3JlYXRlZF9hdCI6ICIyMDI2LTA5LTI1VDA4OjExOjU4WiIsICJldmVudCI6ICJzY2hlZHVsZSIsICJoZWFkX3NoYSI6ICI0MWM3OTk5NGE4MmEzMGQ5Mzg3NzRmZjU0MGM5Nzc2N2MwYWQwMWQ2IiwgImlkIjogMzYxMTE2MjE2NjcsICJydW5fYXR0ZW1wdCI6IDEsICJydW5fc3RhcnRlZF9hdCI6ICIyMDI2LTA5LTI1VDA4OjExOjU4WiIsICJzdGF0dXMiOiAiY29tcGxldGVkIn0sICJyZXNvdXJjZS1odWItc3VwcGx5LWNoYWluLXYwLTIueW1sIjogeyJjb25jbHVzaW9uIjogInN1Y2Nlc3MiLCAiY3JlYXRlZF9hdCI6ICIyMDI2LTA5LTI1VDA2OjA3OjI2WiIsICJldmVudCI6ICJzY2hlZHVsZSIsICJoZWFkX3NoYSI6ICJiNWZjMGQxMzhkOWNkMTk2N2ZmZGY3MmQ0ODE2OTUzOTc1MjJhMmJhIiwgImlkIjogMzYxMDE0NjgyOTEsICJydW5fYXR0ZW1wdCI6IDEsICJydW5fc3RhcnRlZF9hdCI6ICIyMDI2LTA5LTI1VDA2OjA3OjI2WiIsICJzdGF0dXMiOiAiY29tcGxldGVkIn19fSwgInNjaGVtYSI6ICJjbG91ZC1wcm9qZWN0LW1haW50ZW5hbmNlLXYwLjEiLCAic2VtYW50aWMiOiB7Im5leHRfYWN0aW9uIjogIlx1NTdmN1x1ODg0YyBDTE9VRC0wMVx1ZmYxYVx1NWJlOVx1NjdlNVx1NjVlMlx1NjcwOSBQUiBcdTgyMDdcdTk2ZjJcdTdhZWZcdTdkYWRcdThiNzdcdTlhNTdcdTY1MzZcdWZmMWJmaW5nZXJwcmludCBcdTUyMDdcdTYzZGJcdTUwYzVcdTZlOTZcdTUwOTlcdTYzZDBcdTY4NDhcdTMwMDIiLCAicHJzIjogW3siY2hlY2tzIjogIkNPTVBMRVRFRF9XSVRIX1NLSVBTIiwgImhlYWQiOiAiYTc4OWMxY2M3MGY0ODg2MzUyYzdmNTU4MmVmMGQ2YmM1MGEzMWM1ZSIsICJudW1iZXIiOiA0OTYsICJzdGF0ZSI6ICJNRVJHRUQifSwgeyJjaGVja3MiOiAiU1VDQ0VTUyIsICJoZWFkIjogIjFhYTc5ZmE5MTcxOTA2NTA0NWM0M2FjZTJjMjY5NzdkMTIxNmQ4NWEiLCAibnVtYmVyIjogNDk3LCAic3RhdGUiOiAiTUVSR0VEIn1dLCAic291cmNlX2hlYWx0aCI6IHsiY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgInN0YXR1cyI6ICJjb21wbGV0ZWQifSwgIndvcmtmbG93cyI6IFt7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJoZWFsdGgiOiAiSEVBTFRIWV9DT05ESVRJT05BTCIsICJqb2JzIjogW10sICJyZWdpc3RyYXRpb24iOiAiYWN0aXZlIiwgIndvcmtmbG93IjogImJpbmFuY2UtdXNkbS1kZXRhaWxlZC10cmFpbmluZy12MC0xLnltbCJ9LCB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJoZWFsdGgiOiAiSEVBTFRIWSIsICJqb2JzIjogW1siYnVpbGQiLCAic3VjY2VzcyJdLCBbImRlcGxveSIsICJzdWNjZXNzIl0sIFsiYnJvd3Nlci1wcm9kdWN0aW9uIiwgInN1Y2Nlc3MiXV0sICJyZWdpc3RyYXRpb24iOiAiYWN0aXZlIiwgIndvcmtmbG93IjogImRhc2hib2FyZC1naXRodWItcGFnZXMueW1sIn0sIHsiY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgImhlYWx0aCI6ICJIRUFMVEhZIiwgImpvYnMiOiBbXSwgInJlZ2lzdHJhdGlvbiI6ICJhY3RpdmUiLCAid29ya2Zsb3ciOiAicGlvbmV4LWFsdGVybmF0aXZlLWFzc2V0cy1vYnNlcnZhYmlsaXR5LXYwLTIueW1sIn0sIHsiY29uY2x1c2lvbiI6ICJVTktOT1dOIiwgImhlYWx0aCI6ICJFWFBFQ1RFRF9TVE9QIiwgImpvYnMiOiBbXSwgInJlZ2lzdHJhdGlvbiI6ICJhY3RpdmUiLCAid29ya2Zsb3ciOiAicHJvdmlkZXItZXF1aXZhbGVuY2UtdjAtMTItc3VjY2Vzc29yLW1ldGFkYXRhLWNhcHR1cmUueW1sIn0sIHsiY29uY2x1c2lvbiI6ICJzdWNjZXNzIiwgImhlYWx0aCI6ICJIRUFMVEhZIiwgImpvYnMiOiBbXSwgInJlZ2lzdHJhdGlvbiI6ICJhY3RpdmUiLCAid29ya2Zsb3ciOiAicmVzZWFyY2gtYXV0b21hdGlvbi1oZWFsdGgtdjAtMi55bWwifSwgeyJjb25jbHVzaW9uIjogInN1Y2Nlc3MiLCAiaGVhbHRoIjogIkhFQUxUSFkiLCAiam9icyI6IFtdLCAicmVnaXN0cmF0aW9uIjogImFjdGl2ZSIsICJ3b3JrZmxvdyI6ICJyZXNlYXJjaC1zaWduYWwtbGF5ZXItdjAtMi55bWwifSwgeyJjb25jbHVzaW9uIjogInN1Y2Nlc3MiLCAiaGVhbHRoIjogIkhFQUxUSFkiLCAiam9icyI6IFtdLCAicmVnaXN0cmF0aW9uIjogImFjdGl2ZSIsICJ3b3JrZmxvdyI6ICJyZXNlYXJjaC1zaWduYWwtcXVhbGl0eS12MC0xLnltbCJ9LCB7ImNvbmNsdXNpb24iOiAic3VjY2VzcyIsICJoZWFsdGgiOiAiSEVBTFRIWSIsICJqb2JzIjogW10sICJyZWdpc3RyYXRpb24iOiAiYWN0aXZlIiwgIndvcmtmbG93IjogInJlc291cmNlLWh1Yi1zdXBwbHktY2hhaW4tdjAtMi55bWwifV19fQ== -->

### 雲端維護觀測（非執行權限）

- 此次證據基準 main：`41c79994a82a30d938774ff540c97767c0ad01d6`；不是永久最新 main。
- 語意摘要：`235151009c8800446ac38a449e3427a2bdde530a13316789766e96e09185784c`。
- 本機工作：EXCLUDED_BY_USER；研究結果：UNKNOWN_FROM_METADATA。
- 每次接續先重查 main；本區塊保留上次實質變更證據，不因時間戳更新。


觸發此輪的 Health：**success** （completed）；[run 36134440456, attempt 1](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36134440456)。
來源結果獨立保留；後續成功執行不覆蓋此次失敗。

| 工作 | 狀態 | 證據 |
| --- | --- | --- |
| `binance-usdm-detailed-training-v0-1.yml` | HEALTHY_CONDITIONAL / success / registration=active  | [run 35502249846](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/35502249846) |
| `dashboard-github-pages.yml` | HEALTHY / success / registration=active build=success; deploy=success; browser-production=success | [run 36120315129](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36120315129) |
| `pionex-alternative-assets-observability-v0-2.yml` | HEALTHY / success / registration=active  | [run 35500652150](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/35500652150) |
| `provider-equivalence-v0-12-successor-metadata-capture.yml` | EXPECTED_STOP / UNKNOWN / registration=active  | UNKNOWN／無適用 run |
| `research-automation-health-v0-2.yml` | HEALTHY / success / registration=active  | [run 36134440456](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36134440456) |
| `research-signal-layer-v0-2.yml` | HEALTHY / success / registration=active  | [run 36110075341](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36110075341) |
| `research-signal-quality-v0-1.yml` | HEALTHY / success / registration=active  | [run 36111621667](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36111621667) |
| `resource-hub-supply-chain-v0-2.yml` | HEALTHY / success / registration=active  | [run 36101468291](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36101468291) |
| PR #496 | MERGED / COMPLETED_WITH_SKIPS | [PR](https://github.com/qookey109-pixel/crypto-autopilot/pull/496) |
| PR #497 | MERGED / SUCCESS | [PR](https://github.com/qookey109-pixel/crypto-autopilot/pull/497) |

下一步：執行 CLOUD-01：審查既有 PR 與雲端維護驗收；fingerprint 切換僅準備提案。
<!-- cloud-maintenance:v0.1:end -->
