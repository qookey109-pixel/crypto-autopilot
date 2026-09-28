# Crypto Autopilot 短期交付目標

- 文件日期：2026-09-29
- 本次文件查核基準：PR #629 後 main `0d135a6ca67a72f5071d295293477ba6196e249b`；此文件不授予 runtime 或資料存取權限。
- PR #628 exact head `3e2c67b0848eb541c43f54a47f7c6edb267a5632` 的 CI [36493558502](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36493558502)、CodeQL [36493558486](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36493558486)、Dependency/SBOM [36493558471](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36493558471) 通過；main CI [36493744676](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36493744676)、CodeQL [36493744613](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36493744613)、Dependency/SBOM [36493744586](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36493744586)、Freeze Guard [36493744563](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36493744563) 均成功。此 PR 未改網站，Pages 未觸發。
- PR #628 加入 repo-source-only D1 REST client 邊界檢查；帳戶級用量新鮮度與外部 writer 覆蓋仍未證明。
- Repository：[qookey109-pixel/crypto-autopilot](https://github.com/qookey109-pixel/crypto-autopilot)
- 文件定位：交付範圍與驗收清單；不授予新的 runtime 或資料存取權限。
- 歷史證據基準：PR #614 合併至 main `abda84a45de66dc214be40ce05ee0c2ccb79e415`；PR #618 Dashboard 部署證據維持獨立記錄。
- 狀態：Cloud Paper 持續實作，activation disabled。PR #614 已接通資格門控 adapter；PR #622 用 test-only fixture 驗證同一 composition 的入場／出場／帳戶延續／保存／後續 `NO_TRADE`。正式策略 registry 仍空，正式循環為 `NOT_RUN`。

## 保存上限與耗盡政策 — PR #616 merged

- Versioned policy: `config/cloud_paper_storage_policy_v0_1.json`; it defines limits only and grants no activation, provisioning, schedule, or data-access authority.
- Existing guard limits are formalized: 256 KiB per report/object, 2 MiB per run, 192 MiB/day at 96 slots, and a theoretical 6,241,124,352 bytes per 31 days.
- The guard exposes a warning at 6.4 GB (80% of the 8 GB project hard stop) and blocks writes whose projected storage reaches 8 GB. Stale, incomplete, or unknown account-wide evidence still blocks before external access.
- Retention is indefinite and append-only. Automatic or manual deletion is not authorized; partial writes retain evidence and require `REVIEW_REQUIRED`.
- PR #616 merged to main `c0041d89a58b2f8c5a0e27341d2365691eafa5e3`; post-merge CI run `36478324594`, Dependency/SBOM `36478324445`, and Freeze Guard `36478324502` passed. CodeQL [36478324500](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36478324500) passed. These limits are a project policy envelope, not production account usage evidence or a capacity guarantee. Account-wide usage freshness, all-writer coverage, D1 calibration and production acceptance remain open.

## 最新驗收證據狀態 — PR #628 合併後（產品循環證據仍以 #622／#624）

| 項目 | 工程／合成證據 | 正式產品狀態 |
|---|---|---|
| 行情、候選、Paper loop、保存 | PR #614 接通資格門控 adapter；PR #622 讓合格 synthetic fixture 經同一 composition 驗證入場、出場、帳戶更新、保存及下一輪 | 正式 registry 空、模型 `REJECT`，沒有正式交易；正向交易證據僅限 CI fixture |
| 候選資格與資料 lineage | 檢查 Pionex evidence、router route、策略 receipt/implementation SHA、equity/sizing；候選時間綁定已收盤 bar | Pionex global context 為 `REGIME_UNAVAILABLE`；不得用未授權來源替代 |
| Provider／R2 guard | Shared run-scoped guard 與 R2 adapter hooks 已合併 | 帳戶級用量、freshness 與所有 writer coverage 未證明 |
| D1 ledger | #599/#600 recovery audit；#603 rows reservation；#605 storage-growth reservation；#628 CI enforces the repository D1 REST source boundary and guarded query order | migrations prepare-only；D1 未 provision/bind；account-wide usage freshness、external writer coverage、儲存校準與 FREE-ONLY headroom 未證明 |
| 帳戶用量 audit | #611 bounded Analytics audit workflow 與零網路 readiness 已合併 | readiness [36471242643](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36471242643) 為 `BLOCKED_MISSING_READ_ONLY_CREDENTIAL`；Cloudflare requests=0；一次性 audit 未執行、權限未消耗 |
| R2 容量保護 | PR #616 定義 256 KiB/object、2 MiB/run、192 MiB/day、6,241,124,352 theoretical bytes/31 days；guard 在 6.4 GB 回報 WARNING，projected 8 GB 起 fail closed | 正式用量、freshness 與全 writer coverage 未驗證；政策不授權刪除 |
| Dashboard | PR #618 已合併並部署；Pages build/deploy 通過，正式站桌機／手機共 14 項瀏覽器檢查通過。投影明確區分 `NOT_RUN`、空策略登錄、`REGIME_UNAVAILABLE`、`BLOCKED_BUDGET` 與未知容量 | production runtime 尚未啟用；帳戶用量不顯示為 0，正式帳戶與持倉數值維持 null |
| 排程與運作驗收 | 合成完整循環 CI 已通過 | 沒有正式 execution workflow 或自然 Paper schedule；controlled main acceptance 未執行 |

PR #618 的 Dashboard 部署與 14/14 桌機／手機瀏覽器驗證屬於其產品 commit 的證據。PR #622 head `aac48898dfa4e69589c7c369a73a919b07b63c95` 的 Python 3.12／3.13、workflow-static、CodeQL、Dependency/SBOM 通過；合併 main `cb22d3c3905a079eb754f0fab6d917923512f624` 後 CI、CodeQL、Dependency/SBOM、Freeze Guard 通過，main-push workflow-static 因未修改 workflow 而跳過。這些是工程／合成 CI 證據，不代表 production runtime、策略品質或自然排程已驗收。

PR #611 readiness 缺少 read-only credential；未發出 Cloudflare request，亦未消耗一次性 audit authority。GitHub Actions 設定 `CLOUDFLARE_ACCOUNT_ID` variable 和 `CLOUDFLARE_READONLY_API_TOKEN` secret 後，先跑零網路 readiness；未得 `READY` 不執行一次性 audit。

## Cloud CI 工程驗收矩陣 — main `9527d2c`

下列情境由 GitHub CI 的 Python 3.12／3.13 全套測試驗證；PR #622 加入正向 qualified fixture，合併後測試 run [36485948145](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36485948145) 通過，PR #624 合併後 main CI [36488331170](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36488331170) 的兩個 Python job 也通過。這些是合成／假 client 證據，不代表 Cloudflare 帳戶、正式交易或自然排程已驗收。

| 情境 | 代表性 CI 測試 | 狀態與界線 |
|---|---|---|
| qualified 正向循環 | `test_qualified_fixture_completes_entry_exit_and_no_trade_through_composition` | PASS：同一 composition 入場、出場、帳戶更新、保存，再進下一 slot `NO_TRADE`；fixture 僅在測試 |
| 正常不交易／資格拒絕 | `test_enabled_empty_registry_composes_to_audited_no_trade`；`test_empty_production_registry_returns_normal_no_trade`；`test_core100_quality_reject_blocks_registry_before_external_work` | PASS：空 registry 安全輸出 no trade；Core100 `REJECT` 在外部工作前拒絕 |
| 行情／預算拒絕 | `test_missing_duplicate_unclosed_and_stale_bars_rejected`；`test_holdout_guard_precedes_any_request`；`test_missing_account_wide_evidence_blocks_before_reservation` | PASS：無效／過期資料、frozen window 或用量證據缺口 fail closed |
| 重播與重複 slot | `test_duplicate_slot_rejected_before_provider_or_r2_replay`；`test_identical_settlement_retry_is_idempotent_but_mismatch_is_rejected` | PASS：相同 slot 不重複 provider/R2 I/O；不同用量重送遭拒 |
| 並行 reservation | `test_concurrent_duplicate_slot_cannot_double_reserve`；`test_shared_daily_reservations_coordinate_independent_guard_instances` | PASS：合成 D1 ledger 單一 slot 不會雙重預留；不代表全帳戶 writer 都已共用此 ledger |
| 重啟恢復／部分結算 | `test_restart_recovery_verifies_result_and_keeps_full_reservation`；`test_failed_settlement_keeps_reserved_slot_and_does_not_replay_io` | PASS：核對 immutable 結果並保留完整 reservation；失敗時不自動重播 I/O 或釋放額度 |

## 2026-09-27／28 自然排程旁證

- Pionex [run 36309712506](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36309712506)：`REVIEW_REQUIRED`，catalog diff `PASS`、新增／移除皆為 0；保留安全分類結果。
- Core100 [run 36311651477](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36311651477)：精確指紋 `NO_CHANGE`，無訓練、無 provider request、無 R2 寫入。
- Health [run 36400618100](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36400618100) 和其 Cloud Maintenance [run 36400671117](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36400671117) 成功並更新當時的 #578 草稿；該草稿後續已關閉且未合併，不能列為目前待審項目。

以上屬於既有研究、觀測和網站流程的自然排程證據，**不是 Cloud Paper execution workflow 或自然模擬排程驗收**。

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

- [x] 合成正向路徑通過：qualified fixture 經同一 composition 完成模擬入場、出場、帳戶更新、保存及下一輪 `NO_TRADE`（PR #622 CI；僅測試資料，不是 production 策略）。
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

### 正式候選接線現況

PR #614 已將版本化資格門控 adapter 接入 composition；PR #622 進一步以 test-only qualified fixture 經相同 orchestration 驗證入場、出場、帳戶延續、持久化及下一輪 `NO_TRADE`。工程接線的 CI 路徑已覆蓋；production registry 仍空，Core100 為 `REJECT`，正式環境不會使用測試策略建立交易。此結果不改變資格規則、策略品質或交易權限。

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

PR #622 已完成 qualified synthetic candidate 經完整 composition 的 CI 覆蓋。Cloud Paper 仍不可啟用：帳戶用量 readiness [36471242643](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36471242643) 因缺少 read-only credential 而在零 Cloudflare request 下回報 `BLOCKED_MISSING_READ_ONLY_CREDENTIAL`；不得執行一次性 usage audit，直到零網路 readiness 回報 `READY`。credential 由使用者在 GitHub Actions Settings 以 variable／secret 設定，不得在聊天或 PR 傳送值。

仍可獨立完成的工程工作：按 acceptance matrix 核對 replay、並行 slot、部分寫入、恢復、拒絕路徑與每次外部操作的 budget guard 測試覆蓋；掃描 Repository 中所有 D1/R2 writer，逐一核對是否確實使用共享 guard；整理 D1 reservation、settlement、recovery SQL 的讀寫與儲存量界限。現有 4,000 rows/query、384 query reservations/day、16 KiB/statement 是 policy/test envelope，並非 Cloudflare production calibration。不得因合成 CI 通過就宣稱 production usage/headroom 完成。

PR #616 已定義報告大小、每日成長上限、容量警示與 8 GB fail-closed stop；append-only 保存，沒有刪除權限。仍需可信帳戶級 freshness evidence、所有 writer coverage、D1/R2 免費額度與容量證明，以及 96 slots/day 加 settlement/recovery/retry 的總需求。條件具備後才依獨立受控驗收 authority 執行正式 main 循環並驗證保存回讀；自然排程另以真正 schedule run 驗收。

## 10. D1／R2 預算可行性查核 — updated 2026-09-29 (original review 2026-09-28)

### D1 用量來源與 freshness

Cloudflare 官方提供 D1 Analytics GraphQL datasets，可查 accountTag 範圍內的 rows read、rows written 與 database storage；metrics 保留 31 天。官方示例按日期彙總，文件未承諾資料會在目前契約要求的 60 秒 freshness window 內更新，也沒有在此契約中提供可直接視為即時帳戶快照的 watermark。因此 GraphQL Analytics 是**可信來源候選**，目前不是可直接注入 `D1UsageSnapshot` 的 production evidence source。整合前須證明彙總邊界、更新延遲、所有 D1 database 覆蓋及 freshness watermark；未知一律阻止存取。

- [Cloudflare D1 metrics and analytics](https://developers.cloudflare.com/d1/observability/metrics-analytics/)
- [Cloudflare D1 billing analytics](https://developers.cloudflare.com/d1/observability/billing/)
- [Cloudflare D1 query response metadata](https://developers.cloudflare.com/api/resources/d1/subresources/database/methods/query/)

D1 query API 的 `meta.rows_read`／`meta.rows_written` 是單次查詢執行後回報的精確計數，可用於雲端量測 query 成本；它本身不是執行前的保證，不能替代 pre-access reservation。

### 查詢容量推導

歷史初始 guard 曾預留 25,000 rows/query，已由 PR #592 的 4,000/query 上界取代。原始 96 × 2 × 25,000 = 4,800,000 rows/day 高於 4,000,000 safety ceiling；這只是歷史 guard 上界，並非 D1 production measurement。

PR #592 加入結構性上界：

- D1 ledger 只接受與 `cloud_loop_v0_1.slot_id(now_ms)` 相同的 canonical 15-minute slot，拒絕任意 slot ID 或非排程時間。
- rolling query 使用 `reserved_at_ms` 索引，窗口為最多 31 天；每 15 分鐘最多一個唯一 slot，因此目標完整窗口最多掃描 31 × 96 = **2,976** 筆 ledger slot。
- 單次 guard ceiling 設為 **4,000 rows**，包括最多 2,976 筆 slot 與 1,024 rows 的額外保留空間；超過 ceiling 時 fail closed。GitHub CI 的 SQLite `EXPLAIN QUERY PLAN` 檢查索引路徑，合成測試驗證 canonical slot 與日容量算式。
- PR #603 shared guard 每個 query call 先原子預留 admission statement 與目標 statement，各最多 4,000 rows read／10 rows written。384 次預留/day 的 envelope 是 **3,072,000 rows read／7,680 rows written**，低於 4,000,000／75,000 safety ceiling；算術餘額為 928,000／67,320，但不等於可用 account headroom。透過 shared client 的 reservation、settlement、recovery/retry 均消耗同一 384 次上限；reservation 不退額。
- PR #605 對 admission statement 與目標 statement各預留 16,384 bytes growth；384 次/day 的政策上限為 **12,582,912 bytes/day**。該值尚未用 Cloudflare production `size_after` metadata 校準；也須核對 ledger admission/reservation 本身的 storage growth 是否已被包入。

這是政策上界與 SQLite 合成 CI，不是 Cloudflare production measurement。PR #605 的 storage-growth reservation code 已合併，但尚未校準 Cloudflare 實際用量；可信 usage freshness source、所有 D1 writers coverage 與 account-wide D1/R2 headroom 仍未完成。不得因合成測試通過就 provisioning 或啟用 runtime。

R2 的契約上界也需保留共享餘量：2 MiB × 96 slots × 31 days = **6.24 GB／31 days**，對 8 GB 專案 hard stop 僅留下 **1.76 GB** 給其他 writers；Class A 預留為 380,928／31 days，仍須與全帳戶其他 writers 合併核算。這些都是既有 per-slot envelope 的推導，不是實際使用量。由於循環證據採 append-only 且不自動刪除，PR #616 已定義每輪報告大小、成長上限、容量警示與 8 GB hard stop，budget guard 在新增寫入前 fail closed 並回報 `BLOCKED_BUDGET_STORAGE_HARD_STOP`；仍須在取得授權的正式用量證據後驗證觸發時結果。這項政策不授權刪除 frozen 證據。

### 啟用前的必過條件

1. 以 Cloudflare production query metadata 核對 admission 與目標 SQL 的 rows-read／rows-written 上界，並將 reservation statement 本身的成本納入；SQLite 合成結果不能當 production measurement。
2. 將每 slot rows/storage reservation、所有 D1 writer 的共享預留、成功 settlement 與失敗保留／恢復放進同一個原子且可稽核的方案；以受限的 production query evidence 校準 reserve 大小，未確認副作用時不得釋放保留額度。
3. 取得具 freshness watermark 的帳戶級 baseline，證明 D1/R2 全 writer coverage 及保留給本專案的 headroom；合成 fixture 只驗證邏輯，不能當成帳戶證據。
4. 以以上證據重算 96 slots/day 是否仍符合 0 USD safety ceiling，再進行正式受控循環。若不能證明容量，保持 `activation.enabled=false`，不要用手動 dispatch 或降低 guard 上界假裝完成。

這項查核補充了第 9 節的下一個工程工作，不改寫任何 frozen receipt、既有預算 authority 或 runtime 權限。


## 帳戶方案證據缺口 — PR #630 已合併

查核基準為 parent main `e2e4a911b1fa62c35c6e16a3eb4850e68d23f090`。PR [#630](https://github.com/qookey109-pixel/crypto-autopilot/pull/630) 以 exact head `e204e4062b448f2d19a5bf98afbe3986dc1dded9` 合併。PR-head CI [36496143905](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36496143905)、CodeQL [36496143925](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36496143925)、Dependency/SBOM [36496143898](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36496143898) 與 retired-workflow guard [36496143862](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36496143862) 通過。合併 main 為 `e2e4a911b1fa62c35c6e16a3eb4850e68d23f090`；main CI [36496372548](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36496372548)、CodeQL [36496372401](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36496372401)、Dependency/SBOM [36496372521](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36496372521) 與 Freeze Guard [36496372302](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36496372302) 通過；main 上 PR-only workflow-static skipped。

新增合約與 workflow 是一次、只讀、單一 Cloudflare subscriptions GET，使用獨立 secret `CLOUDFLARE_BILLING_READONLY_API_TOKEN`（Account Billing Read）。零網路 readiness 先檢查變數／secret 是否存在；只有 `READY` 才可使用一次性 audit。既有 D1/R2 用量 audit 的合約與一次性次數沒有改動。

Cloudflare API **尚未呼叫**。billing readiness 尚未執行；結果不會證明 invoice 總額、所有計量產品、外部 writer 覆蓋或零成本。零費用結論仍需 fresh account-wide usage、帳單與完整 writer coverage 證據。Cloud Paper runtime、D1/R2 寫入與排程仍關閉。
