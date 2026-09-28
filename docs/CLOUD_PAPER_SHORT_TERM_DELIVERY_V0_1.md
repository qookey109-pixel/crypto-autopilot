# Crypto Autopilot 短期交付目標

- 文件日期：2026-09-28
- Repository：[qookey109-pixel/crypto-autopilot](https://github.com/qookey109-pixel/crypto-autopilot)
- 文件定位：交付範圍與驗收清單；不授予新的 runtime 或資料存取權限。
- 狀態：計畫文件。各批狀態以最新 main、PR checks 與版本化證據為準。

## 最新驗收證據狀態 — 2026-09-28

以下是證據分層；下方 `[ ]` 是**完整交付門檻**，不代表相關工程或合成測試完全沒有完成。

| 項目 | 工程／合成證據 | 正式產品狀態 |
|---|---|---|
| 行情、候選、Paper loop、保存 | 已合併；完整循環 CI 與 empty-registry `NO_TRADE` 合成路徑通過 | 尚無正式 execution workflow 或受控 main run |
| Provider／R2 guard | 共用 run-scoped guard 與 adapter hooks 已合併；合成檢查通過 | 帳戶級用量、freshness、全 writer coverage 未證明 |
| D1 ledger | slot reservation 與成功結果 readback 後 settlement 已合併；失敗保留 reservation | D1 未 provision／bind；rows budget 仍未跨 query/run 協調；settlement recovery 未完成 |
| 端到端正向路徑 | machine status 記錄 synthetic full-cycle CI `PASS` | 不能推論模型資格、策略獲利或可產生正式交易 |
| Dashboard | main Pages build、deploy、browser-production 已驗證 | Cloud Paper runtime 未啟用，網站尚無正式循環報告可投影 |
| Global context | CMC candidate 與指標映射僅 proposal | 未授權、未呼叫；`REGIME_UNAVAILABLE` 維持預期 fail-closed 狀態 |
| 排程與交易資格 | 不適用 | 排程尚未建立；模型 `REJECT`、production strategy registry 為空，因此正式只可 `NO_TRADE` |

查核基準：PR [#590](https://github.com/qookey109-pixel/crypto-autopilot/pull/590) 合併後 main `e3f94cd4b2d5a7262cc76382b93ae27316d44395`；合併後 Python 3.12／3.13、CodeQL、Freeze Guard、依賴安全、Pages build／deploy／browser-production 通過。這些結果不替代帳戶用量證據、受控 runtime acceptance 或自然排程驗收。

## 1. 本輪目標

完成一個**可保存、可恢復、可追溯、看得懂**的雲端模擬循環：

**公開行情 → 候選 → 策略資格與風控 → 模擬交易或拒絕 → 保存 → 報告 → Dashboard。**

沒有合格策略時，正常輸出 `NO_TRADE` 與原因。正式環境不得使用測試策略或被拒絕模型製造交易。

## 2. 執行原則

- 開始每批前重新解析最新 `main`、開放 PR、目前狀態及當前版本化契約。
- 沿用已完成模組與驗收證據，只補足尚未打通的缺口。
- 分三批交付；每批必要 GitHub 雲端 CI 通過後，依既有授權合併並回讀 main。
- 前置條件未完成時，精確記錄阻塞；可獨立完成的工作繼續。
- 不以固定日曆等待作為本輪完成條件。

## 3. 第一批：預算與保存可靠

**優先度：P0，併入 P1 針對性安全檢查。**

### 工作範圍

完成行情請求、共享預算預留與持久化流程的接線，確保額度檢查涵蓋每一個實際外部操作。檢查 workflow 權限、secret 邊界、並行寫入及預算繞過風險。

### 驗收清單

- [ ] 每次外部操作前檢查本次、每日及適用帳期額度。
- [ ] 用量證據缺漏、過期或覆蓋不完整時，在外部存取前停止。
- [ ] 行情與 R2 使用同一個 run-scoped reservation guard；接線不一致時在任何存取前拒絕。
- [ ] 並行執行不造成超額預留或重複寫入。
- [ ] 同一 slot 重複執行不重複成交或推進帳戶。
- [ ] 重新啟動後延續已驗證帳戶，不重新初始化資金。
- [ ] 部分寫入或狀態衝突輸出 `REVIEW_REQUIRED`，保留證據。
- [ ] secret 不出現在 log、artifact、報告或 Repository。
- [ ] 必要 GitHub 雲端 CI 通過。

**交付物：** 接線修正、相關回歸測試、檢查結果及未解阻塞。合成測試的用量快照不等於正式帳戶用量證據。

## 4. 第二批：完整流程可驗收

**優先度：P0。**

### 工作範圍

串接既有行情轉換、候選、策略資格、風控、模擬核心、保存與報告。使用合成資料驗證交易路徑；正式資格判定維持現有規則。

### 驗收清單

- [ ] 合成正向路徑通過：候選 → 風控 → 模擬入場 → 出場 → 帳戶更新 → 下一輪。
- [ ] 無候選、無合格策略及模型 `REJECT` 均輸出明確原因且零新倉。
- [ ] 過期、未收盤、缺漏或不連續資料按契約拒絕。
- [ ] 風險超限、來源失效及額度不足時停止相關操作。
- [ ] 重播不重複成交，恢復後帳戶結果一致。
- [ ] 報告可追溯資料來源、時間、run、slot、狀態識別碼及實際讀寫次數。
- [ ] 必要 Python 3.12／3.13、Ruff、治理及相關檢查通過。

**交付物：** 一組完整雲端 CI 驗收證據，以及可追溯的循環報告範例。

## 5. 第三批：狀態與缺口清楚

**優先度：P1。**

### Dashboard

首頁依真實證據區分以下狀態：

| 狀態 | 必須說明 |
|---|---|
| 正常無交易 | 已完成檢查及未交易原因 |
| 資料不足 | 缺少、過期或無效的資料，以及受影響步驟 |
| 系統故障 | 失敗步驟、是否部分寫入及恢復狀態 |
| 尚未啟用 | 尚缺的啟用條件，不呈現虛構循環結果 |

### 資料缺口

沿用既有工作清單，每個缺少指標記錄：

- 指標定義及用途。
- 候選來源與官方證據連結。
- 免費額度、請求預算及費用是否已驗證。
- 歷史涵蓋、資料時間、更新頻率與對齊要求。
- 儲存／展示授權及目前可用狀態。

Public APIs、free-for.dev 僅作候選發現入口；實際採用須核對來源官方資訊。未完成驗證的來源保持不可用，不進行網路擷取或替代切換。

### 驗收清單

- [ ] Dashboard 顯示最後循環、證據時間與明確原因。
- [ ] 帳戶、持倉及損益只投影已驗證證據；未知值不顯示成零。
- [ ] Pages build、deploy、桌機及手機驗證通過。
- [ ] 目前狀態與接續手冊同步更新。

**交付物：** 可理解的 Dashboard、資料缺口清單及最新交接文件。

## 6. 完成判定

以下結果分別記錄，不互相替代：

| 里程碑 | 通過條件 |
|---|---|
| 工程整合完成 | 三批必要實作、雲端 CI 與網站驗證完成 |
| 正式受控驗收完成 | 當前 authority、零費用證據與啟用條件具備後，main 受控循環及保存回讀通過 |
| 自然排程確認 | 已啟用排程出現 qualifying 自然 run，且報告與副作用證據已核對 |

自然 run 尚未出現時，記錄「首次自然執行待確認」。不得以手動執行替代，也不得宣稱無人值守運作已驗收。

## 7. 本輪不納入

- Hindsight 或新的 Agent／記憶平台。
- 新策略研究、調參、模型 promotion。
- 非必要 UI 美化、型別清理或大型重構。
- 七天觀測及額外日曆查核等待。

TradingAgents 保留既有研究定位，後續另行評估。

## 8. 固定邊界

- 全程 GitHub／GitHub-hosted runner；本機檔案、終端機及排程排除。
- `0 USD/month`、`PAPER / LIVE-PAPER ONLY`。
- 不開實盤、holdout、source switch 或自動 promotion。
- 一次性 bootstrap 不重跑；frozen 證據不改寫。
- 原有 runtime expiry 與安全保護維持有效。
- 新範圍如需 authority，先以 successor 契約合併至 main，再執行。

## 9. 下一個可直接開始的工作

PR [#579](https://github.com/qookey109-pixel/crypto-autopilot/pull/579) 將 Pionex 行情與 R2 保存接到同一 run-scoped guard；PR [#585](https://github.com/qookey109-pixel/crypto-autopilot/pull/585) 加上 D1 usage-evidence preflight 與 per-slot reservation interface；PR [#587](https://github.com/qookey109-pixel/crypto-autopilot/pull/587) 完成 concrete D1 evidence guard、composition preflight 及 Cloudflare D1 REST client 的逐 query guard。#587 的 PR head 與 post-merge 必要 CI 均通過。

PR #590 將成功 settlement 接在 Paper 完整寫入及 readback 之後；若運行或 settlement 失敗，完整 reservation 保留。這不是故障恢復完成：現有 D1 query guard 仍只在單一 instance 累計，沒有跨執行的 D1 rows-read reservation；未確認 settlement 結果時也沒有自動恢復流程。可信的帳戶級 D1 usage evidence source、所有 D1 writers 覆蓋、production runner binding、D1 provisioning、R2 account-wide usage/headroom 仍未證明。

因此 P0 預算與保存批次仍未完成，不啟用 runtime、不做受控 main acceptance。下一批應先解決跨執行 D1 rows-read/write reservation 與 settlement 的結果恢復，再完成有 freshness watermark 的帳戶級 usage source 和所有 writer coverage。只有證明 96 slots/day 在 FREE-ONLY 預算下可行，才可進行正式 D1/R2 驗收；不得把合成證據當成正式用量，也不得以降低 25,000/query 上界讓算式通過。
## 10. D1／R2 預算可行性查核 — 2026-09-28

### D1 用量來源與 freshness

Cloudflare 官方提供 D1 Analytics GraphQL datasets，可查 accountTag 範圍內的 rows read、rows written 與 database storage；metrics 保留 31 天。官方示例按日期彙總，文件未承諾資料會在目前契約要求的 60 秒 freshness window 內更新，也沒有在此契約中提供可直接視為即時帳戶快照的 watermark。因此 GraphQL Analytics 是**可信來源候選**，目前不是可直接注入 `D1UsageSnapshot` 的 production evidence source。整合前須證明彙總邊界、更新延遲、所有 D1 database 覆蓋及 freshness watermark；未知一律阻止存取。

- [Cloudflare D1 metrics and analytics](https://developers.cloudflare.com/d1/observability/metrics-analytics/)
- [Cloudflare D1 billing analytics](https://developers.cloudflare.com/d1/observability/billing/)
- [Cloudflare D1 query response metadata](https://developers.cloudflare.com/api/resources/d1/subresources/database/methods/query/)

D1 query API 的 `meta.rows_read`／`meta.rows_written` 是單次查詢執行後回報的精確計數，可用於雲端量測 query 成本；它本身不是執行前的保證，不能替代 pre-access reservation。

### 查詢容量推導

目前 nominal schedule 為 96 slots／UTC day。目標完整循環每 slot 至少有 D1 reservation 與 settlement 兩次查詢，即 192 queries／day。沿用目前每次 query 預留上界 25,000 rows read，保守 envelope 為 **4,800,000 rows read／day**，高於專案 D1 safety ceiling **4,000,000 rows／day**。這是 guard 上界乘以目標查詢數，不是實測用量；但足以證明目前上界不能作為 96-slot 啟用的容量證據。現有 composition 尚未呼叫 settlement，故不能用它目前只有 reservation 的成本推稱完整預留／結算已可運行。

R2 的契約上界也需保留共享餘量：2 MiB × 96 slots × 31 days = **6.24 GB／31 days**，對 8 GB 專案 hard stop 僅留下 **1.76 GB** 給其他 writers；Class A 預留為 380,928／31 days，仍須與全帳戶其他 writers 合併核算。這些都是既有 per-slot envelope 的推導，不是實際使用量。

### 啟用前的必過條件

1. 用實際 SQL／索引與 D1 query metadata 建立每種 query 的有界 rows-read／rows-written 預留；預留操作本身的成本也要入帳。不可只把 25,000 改小來讓算式通過。
2. 將每 slot reservation、所有 D1 writer 的共享預留、成功 settlement 與失敗保留／恢復放進同一個原子且可稽核的方案；未確認副作用時不得釋放保留額度。
3. 取得具 freshness watermark 的帳戶級 baseline，證明 D1/R2 全 writer coverage 及保留給本專案的 headroom；合成 fixture 只驗證邏輯，不能當成帳戶證據。
4. 以以上證據重算 96 slots/day 是否仍符合 0 USD safety ceiling，再進行正式受控循環。若不能證明容量，保持 `activation.enabled=false`，不要用手動 dispatch 或降低 guard 上界假裝完成。

這項查核補充了第 9 節的下一個工程工作，不改寫任何 frozen receipt、既有預算 authority 或 runtime 權限。
