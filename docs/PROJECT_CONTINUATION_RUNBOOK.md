# 專案接續與排程手冊

更新：2026-09-24。適用任何能讀取 Repository 與 GitHub metadata 的模型。
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

### 本地未合併成果

以下位置相對於使用者原始 checkout，**不在 main**，不可當 execution authority。換機／純雲端模型若無法取得，將該項標為 UNKNOWN 並交接精確路徑，不宣稱已讀、不重做已知完成的盤點。不要尋找或依賴先前 `/tmp` 副本。

| 工作 | 本地成果位置 | 已完成／仍待處理 |
| --- | --- | --- |
| TD-011 | `docs/LOCAL_WORKSPACE_RECONCILIATION_2026_09_24.md`; original checkpoint remains in `handoffs/2026-09-23-project-checkpoint/` in the dirty checkout | All 78 outcomes and current-main blob/mode classifications are documented; all 78 status pairs still match the checkpoint, with 13 newer untracked handoff files. There are 15 untracked exact duplicates proposed as one cleanup batch; two tracked exact matches are excluded. C1/C4/C5 are integrated by PRs #493/#491/#492; C2/C3 are deferred. The original working tree remains dirty. Any local deletion requires explicit approval and final repeated status/hash checks. |
| TD-012 | 原本地提案仍保留於 handoffs/2026-09-23-core100-fingerprint-v0-2-proposal.md；Repository 準備文件見 [V0.2 review](CORE100_TRAINING_FINGERPRINT_V0_2.md)、[config](../config/core100_training_fingerprint_v0_2.json)、[receipt](../research/receipts/2026-09-24-core100-training-fingerprint-v0-2-prepared.json) | 31-path closure 分為 14 個 result-identity 與 17 個 runtime-guard 檔；純記憶體 comparator 與合成行為測試已準備，仍為 PREPARED_NOT_ACTIVE。下一步準備 successor cutover proposal，納入新模組／collector 的 import inventory、真實環境取證及 legacy baseline 處置。V0.1 runner 未修改；任何啟用仍需另有版本化 authority |
| 最新交接 | `handoffs/2026-09-23-project-checkpoint/README.md` | main／PR／驗證快照、原工作區狀態與新聊天接續文字；仍需 live 查核 |

Signal ingest parsing hardening 和 Quality V0.1 authority validation 分別由 [PR #491](https://github.com/qookey109-pixel/crypto-autopilot/pull/491) 與 [PR #492](https://github.com/qookey109-pixel/crypto-autopilot/pull/492) 合併，合併後 CI、CodeQL、Freeze Guard、Pages deploy 與 browser-production 均成功。不要把舊模組整檔覆蓋 current main，也不要移植舊的 Quality evaluator；main 的 dedupe、source-run binding、freshness 與單指標 `NO_CHANGE` 讀取契約已保留。C1 unified planning overlay 的單一 Work Item form、contract、模板與 AGENTS/README 導覽由 [PR #493](https://github.com/qookey109-pixel/crypto-autopilot/pull/493) 整合。C2 Agent Arena 仍無具體比較集合／使用路徑，且 registry 已能保存不可變證據、scorecard 已提供 research-priority ranking；C3 的舊 synthetic preview 使用舊 Paper report schema，而 main 已有 Daily Opportunity Engine 和 Strategy Router，兩項都先保留本地、不移植。舊 Health V0.1 cron 與缺少 #478 的 Pages workflow不可回灌。

## 2. 每次接續的固定流程

1. 記錄 UTC／Asia/Taipei 查核時間、Repository，先解析 GitHub `main` exact SHA。有 checkout 才記錄工作區、分支、HEAD 與 dirty 狀態；雲端沒有 checkout 就明記 `NO_LOCAL_CHECKOUT`，不得假設本地檔案可讀。main 解析失敗則標記 `UNKNOWN`，停止依賴最新 authority 的工作。
2. 依上表讀入口及本次涉及的版本化檔案。文件內 evidence-basis SHA 是歷史查核基準，不是最新 main。
3. 取得 live open PR，再讀相關 PR exact head/base、draft／merged、checks。已有相同工作就接續；已完成工作不重做。
4. 判定模式：**排程健檢**只讀 Repository／Actions metadata；**使用者指派的整理工作**依明確範圍編輯、驗證與交付。排程或待辦本身不授予寫入／merge／dispatch 權限。
5. 排程健檢只指出一個下一步，不自行實作。使用者指派的整理工作才選一個可執行項目；遇外部等待或權限缺口，留下證據並繼續不相依項目；不反覆重試已知 403、不增加平行工作流。
6. 執行有檔案權限的整理工作時，修改前查該檔是否被 frozen receipt／hash 綁定。原工作區有 dirty／recovery 時，在隔離 current-main checkout 改動；未提交內容不得自動帶入。純雲端健檢不需要 checkout。
7. 以項目驗收證據結束。文件檢查連結、矛盾及相關既有檢查；行為改動加必要回歸測試。保留實際命令、結果、未驗證事項。
8. 交接記錄「完成、等待、下一動作」。PR 建立、CI 通過、合併、部署、自然 schedule 通過必須分開。

## 3. 排程分工

### GitHub：執行已合併的研究與網站工作

名義時間及 expiry 以 [Actions map](GITHUB_ACTIONS_OPERATING_MAP.md#scheduled-operations) 導航，再核對當下 workflow／config。不要由 Codex 再 dispatch，也不要建立平行 cron。

### 雲端模型健檢：建議每 6 小時

使用可在雲端執行、可讀 GitHub Repository／Actions metadata 的排程服務。[自足的雲端提示詞](CLOUD_SCHEDULED_CHECK_PROMPT.md)可直接用於建立任務；排程是否建立和執行須以該服務的任務與 run history 查核，本手冊不宣稱某個個人排程已啟用。提示詞不依賴本機電腦、`/tmp`、聊天記憶或特定模型。雲端可讀 current main 的 78 項逐檔 reconciliation receipt 與 fingerprint V0.2 preparation 文件；原始 dirty checkout 的即時檔案狀態仍是 local-only。無 checkout 時，將實際本地檔案檢視標為 `LOCAL_ONLY_UNAVAILABLE`，不能聲稱已比對當前 bytes 或執行 cleanup。

每輪順序：

1. 更新 main／open PR／checks metadata。
2. 依 current main 的 `config/research_automation_health_v0_2.json` 或其已合併 successor，比對全部 cron workflow 的 active window、allowed events、allowed conclusions、freshness。先查 successor，不能永遠沿用 V0.2。
3. 查 Pages 自然 `schedule`，分別查 build／deploy／browser-production job metadata；再查它之後的 Health `schedule`。較早的 Health 或其他事件成功不能當作恢復。
4. 檢查到期與每週節點，再更新等待項目的證據。沒有新變更時，不自創整理工作。

### 近期工作節點

日期僅是檢查時點。較晚執行時查該日期之後的 metadata，不補跑。

| 時點（台北） | 工作與完成條件 |
| --- | --- |
| 雲端排程啟用後每 6 小時 | 唯讀健檢；Pages 自然 run `35843351924` 已成功，且其後自然 Health run `35870216734` 已 `PASS`、`alerts=0`。TD-010 已完成，後續只做正常健康監控並在新故障／恢復時更新 |
| 下一個可執行的整理回合 | 等待使用者對 [15 個 untracked exact-duplicate paths](LOCAL_WORKSPACE_RECONCILIATION_2026_09_24.md) 的明確移除決定；同意後執行前重查 main、status、hash。未獲核准前不碰原 checkout。其餘 76 個狀態項保留待後續逐項審核；D、C2/C3 與 13 個後續 handoff 檔保留。PR #494 已合併，但 V0.2 仍 PREPARED_NOT_ACTIVE；啟用前另需版本化 cutover authority，不得改 runner、訓練或接觸 R2 |
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
- 相同問題用 `workflow + event + latest relevant run + conclusion + expiry state` 去重，另記首次告警及恢復。只有查核時間不同不是新進展。
- metadata-only 健檢不讀 logs／artifacts。沒有 report 證據時，Training success 不能推出 PASS／NO_CHANGE；provider／R2 用量維持 UNKNOWN。

## 5. 執行界線

- 排程健檢預設不編輯程式、不 push／PR／merge、不 dispatch／rerun／cancel、不停用 workflow。若允許自動整理，須在排程提示詞另定檔案範圍、驗收與交付界線。
- 25 個 removed-file registration 的停用已獲使用者授權，但現有 API credential 回應 403、UI 顯示 workflow 不存在；查核時 0/25 成功。需具 Actions:write 的可用連線才續辦；再次核對 exact ID／path 仍不在 main，逐項讀回 state，保留 run history。
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
原工作區與 recovery：有權限才記位置／異動；雲端無存取時填 NO_LOCAL_CHECKOUT
```

新模型先跑第 2 節，再依 [CURRENT_STATUS.md](../CURRENT_STATUS.md) 接續。舊 Handoff 保留歷史，新查核追加時間與來源。
