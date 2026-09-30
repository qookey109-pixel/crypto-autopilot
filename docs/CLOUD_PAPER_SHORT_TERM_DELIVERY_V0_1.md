# Crypto Autopilot — 完整模擬循環交付目標

## 即時進度掃描、問題統整與依序收斂計畫 — 2026-09-30 11:10 Asia/Taipei

Repository：[qookey109-pixel/crypto-autopilot](https://github.com/qookey109-pixel/crypto-autopilot)  
正式 authority：GitHub `main`。本次查核 main：`c8d0475360e968d518109d7201a34a6dc3d295ab`（`docs: refresh Cloud Paper delivery goal`）；查核時 open PR = 0。PR-head、push、Pages、自然排程與正式 Paper runtime 證據分開判讀。

### 專案完成目標

交付一個可在免費雲端條件下受控運作、資料可追溯且可恢復的 **PAPER 模擬產品**：

**已授權公開行情 → 來源／時間／完整度檢查 → 最多五個受治理候選 → 正式策略資格 → 風控與組合檢查 → 模擬成交，或記錄有明確原因的 `NO_TRADE` → 預算保留與 slot claim → 不可變保存、回讀與中斷恢復 → Dashboard 呈現可追溯結果。**

正式策略 registry 可以為空。模型為 `REJECT`、行情／來源不足、風控不符或預算未知時，正確結果是安全拒絕或 `NO_TRADE`，不可用 CI 測試策略、放寬門檻、補值或未授權來源製造正式交易。虛擬帳戶 USD 10,000 僅能初始化一次。策略表現研究和工程循環驗收分開。

### 即時進度掃描

查核來源包括即時 main/ref、open PR 搜尋、最近 Actions runs、`PROJECT_STATUS.md`、`CURRENT_STATUS.md`、README、Operations map、現行本目標及未合併分支差異。

**已完成的工程基礎**
- 版本化 Cloud Paper loop 契約、Pionex 公開行情 adapter、受治理市場候選、策略資格 gate，以及 risk／portfolio／paper composition 已存在於 main。
- 雲端 synthetic CI 已有 test-only 入場／出場、帳戶延續、空 registry `NO_TRADE`、資料與風控拒絕、slot 重複／競爭、reservation、部分寫入審核與受限 recovery 證據。這證明合成路徑，不等於正式 runtime 已執行。
- #647/#648/#649 的狀態及目標文件變更已合併；main `c8d0475` 的 push CI [36662486206](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36662486206)、CodeQL [36662486200](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36662486200)、Dependency/SBOM [36662486162](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36662486162)、Freeze Guard [36662486223](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36662486223) 均成功。這些是 main push checks；若某個 PR 的 Pages 工作流未觸發，不能解讀為部署成功。
- 目前沒有 open PR。舊 #644 已關閉未合併，過時檢查不算 PASS。

**尚未交付的產品狀態**
- Cloud Paper `activation=false`；正式 cycle `NOT_RUN`；Cloud Paper 自然排程 `NOT_ESTABLISHED`。
- production strategy registry 空、Core100 品質 `REJECT`、macro context `REGIME_UNAVAILABLE`。系統可以安全地輸出 `NO_TRADE`，但不得宣稱策略已有效或已獲利。
- Billing V0.1、Usage V0.1/V0.2、R2 Usage V0.3 均為已消耗的一次性 evidence authority，禁止重跑或以新 workflow 名稱重取同範圍資料。
- 最新 R2 V0.3 是部分觀測：30 日 operations 共 125,309 requests、無資料 freshness timestamp；storage 聚合僅代表一個 returned bucket，16,304 objects、616,541,780 bytes，觀測時間 2026-09-29 15:20 UTC。D1 使用量、完整 bucket inventory、全部 writers、invoice/metered cost、零費用與真實 headroom 均 `UNKNOWN`。8 GB 專案上限是政策值，不是已測 headroom。
- 現有 60 秒 budget freshness gate 尚無已驗證來源能保證水位。CloudBudgetGuard 使用 caller 提供的 snapshot，未提供跨 run 的持久原子 reservation ledger；freshness、reservation coverage 不足時必須在任何外部 I/O 前 fail closed。
- D1 migration 為 prepare-only；production D1/R2 尚未 provision／讀寫，append-only 長期容量與恢復尚未由真實雲端驗收。
- regime 欄位仍有資料來源缺口：Pionex 不提供 TOTAL3／BTC dominance；CMC 候選的等價性、授權、金融用途與儲存／展示許可未通過；Pionex breadth 23 市場仍待 membership、完整度、時間對齊和 freshness 驗證。不得自動換源、拼接或縮小 universe 來湊資料。
- 最近查到的自然排程中有 Research Automation Health 成功紀錄，但沒有 qualifying Cloud Paper 自然 Paper cycle。手動 dispatch 不能替代自然 schedule。
- 專案目標的文件入口曾被重複同步；`CURRENT_STATUS.md`／Operations map 的頂端快照比目前 main 舊。文件狀態需於本次目標更新合併後依同一 current SHA 收斂，歷史紀錄維持原樣。
- 遠端分支 `codex/dashboard-cloud-paper-usage-v03` 比 main ahead 3 commits、behind 0，僅修改靜態 validator 與 `web/data/cloud-paper-loop.json`，尚無 PR，沒有前端更新、測試與 CI 驗收。此分支是未驗收候選變更，不得列為已完成；先審查後再補齊或另作決定，不覆寫分支或直接納入 main。
- Pionex bounded observability expiry 是獨立於 Cloud Paper 啟動的現行權限時點；2026-10-01 08:00 台北到期查核依當時 authority 執行，不自動延期、不補跑歷史 slot，也不以其觀測取代 Paper acceptance。

### 問題與改善摘要

1. **狀態文件漂移：**頂端 checkpoint 仍包含舊 main、PR 和 pending 敘述。應有一份 current checkpoint 指向同一 SHA；舊快照留作歷史，不改寫。
2. **Dashboard 契約落後：**validator／UI 對 V0.2/V0.3 使用量證據沒有一致雙版本支援，可能拒絕新證據或顯示舊內容。Partial、null、UNKNOWN 不可投影成零或 PASS。
3. **預算與持久性缺口：**單次 caller snapshot 不足以保證跨 workflow/run 原子化預算。reservation、settlement、slot claim、ledger 容量、失敗和重播語義需端到端可證。
4. **零費用無證據閉環：**現有 Billing/R2 結果無法核對所有計費 meter、D1、整個帳戶的 resources/writers 與 headroom。需要先決定可靠證據來源和費用 gate 的可證明範圍；資料不足就保持 blocked。
5. **市場 regime 資料缺口：**欄位定義、硬性 gate、來源權限及時間對齊未收斂。不可把候選 API 或未授權來源視為可用。
6. **正式受控與自然執行不存在：**尚無正式 D1/R2 state、受控 main Paper cycle 或 Cloud Paper 自然排程。需先過成本、來源、策略資格、資料持續性與版本化權限 gate。
7. **未合併分支沒有交付閉環：**V0.3 Dashboard 候選停在 validator/data，需完成 UI、fixture/test、雲端 CI，再根據結果決定是否合併。

### 依序排程與完成標準

工作按依賴連續推進，不用固定等待期拖延可獨立的合成工程。失敗先在同一批修正並保留證據。任何 Cloudflare live query、資源建立／寫入或排程啟用，必須有範圍吻合且已合併 main 的獨立版本化 authority；使用者的合併授權不替代該 authority。

| 順序 | 優先度 | 工作 | 完成標準／停線 |
|---|---|---|---|
| 0 | P0，立即 | **目標與 current status 收斂。** 更新本目標，接著同步 `CURRENT_STATUS.md`、`PROJECT_STATUS.md`、Operations map 與機器狀態索引。 | 全部指向同一查核 SHA；open PR、最新 workflow、post-merge checks、舊證據、自然排程和 runtime 分開。凍結／歷史證據只追加新快照，不改舊內容。 |
| 1 | P0，下一個工程切片 | **完成 Dashboard V0.2/V0.3 雙版本相容。** 先審查既有 remote branch，決定如何保留其 validator/data 工作；完成 JS projection、static validator、synthetic fixtures、繁中 snapshot、browser regression。 | V0.2、V0.3、null、partial、缺欄位、錯 run/artifact、UNKNOWN 有測例；unknown 不顯示 0/PASS；Dashboard 顯示 evidence run/time/basis 並保持 activation disabled。CI、CodeQL、SBOM 和適用的 Pages build/deploy/browser 依 exact SHA 驗證。 |
| 2 | P0 | **補 durable shared budget/reservation。** 將 run-scoped guard 缺口列成可驗收契約，收斂所有授權 provider/D1/R2 I/O 前的 reservation、原子 slot claim、settlement 和 immutable ledger。 | 同一 slot 競爭僅一方成功；外部 I/O 前預留可追溯；相同 settlement replay 冪等、衝突停為 `REVIEW_REQUIRED`；部分寫入保留證據；snapshot stale/incomplete、額度不足或未列 writer 時零外部呼叫。 |
| 3 | P0 | **把恢復與容量納入同一 persistence 驗收。** 檢查 account genesis、ledger append、pointer 更新、讀回、restart replay、partial write 和 ledger 自身寫入預算。 | USD 10,000 初始化僅一次；append-only write 先過單 run/day/31-day 限額；競爭／中斷恢復可重現；不刪除或覆寫 frozen records。只有 synthetic 測試，尚不代表 production 容量已校準。 |
| 4 | P0，決策 gate | **收斂帳務、用量、完整資源與 headroom 的證據方案。** 對每個必要 API/UI 來源記權限、資料期間、水位/延遲、分頁、request/response cap、費用 meter 覆蓋、blind spots。 | 逐項判定可證明／不能證明；零費用、D1/R2 usage、全部 bucket/database、共同 writers、freshness/headroom 均有可核對 evidence。無法完整證明時保留 `COST_GATE_BLOCKED`；不擴權、不重跑已消耗 audit、不自動 dispatch。 |
| 5 | P0 | **收斂市場資料契約。** 列出候選、必要 regime/context 欄位、定義、來源與授權、資料時間、完整度、連續性和請求預算，判定每項是執行硬 gate 或非必要顯示。 | 只有已授權來源可餵入 Router；TOTAL3/BTC dominance/breadth 未通過即 unavailable，按版本化契約輸出 `DATA_INSUFFICIENT` 或 `NO_TRADE`。不 fallback、不拼接、不更改 frozen research scope。 |
| 6 | P0 | **端到端合成 CI 收斂。** 對行情 → 候選 → eligibility → risk → paper lifecycle → reservation → immutable save/readback → restart/replay → Dashboard 建立單一矩陣。 | 覆蓋正向 test-only cycle、正常無策略 NO_TRADE、模型 REJECT、stale/gapped data、budget exhausted/unknown writer、slot race、partial write、restart、idempotency；Python 3.12/3.13、Ruff、freeze/governance、static、CodeQL、SBOM 按定位通過。不得連 production secrets 或外部服務。 |
| 7 | P0 外部 gate | **若且僅若 phase 4 找到資訊增益，制定 successor evidence authority。** 已消耗 Billing V0.1/Usage V0.1/V0.2/R2 V0.3 永不重跑。 | 新 authority 要限定最小 read permissions、allowlisted endpoints、期限、calls/pages/bytes、零 retry/fallback、去識別輸出、one-shot/consumption、失敗語義；先 merge config/receipt/code/readiness，未符合 authority 不 dispatch。若官方證據不能證明成本或 headroom，停止在 blocked。 |
| 8 | P0 外部 gate | **Production state 與一次性 controlled PAPER acceptance。** 只有 cost/headroom、來源、策略資格或合法 NO_TRADE、耐久 reservation/recovery 均通過，再經版本化授權。 | 在正式 main 執行一次；驗證 genesis 不重複、有限資料、預算、slot idempotency、paper open/exit/NO_TRADE、實際 read/write upper bound、保存回讀和恢復。任一 unknown/partial 即停止，不 provision/寫入。 |
| 9 | P1 外部 gate | **受控成功後才啟用 Cloud Paper 自然排程。** 排程是 runtime authority，與研究 Health/Pionex observability schedule 分開。 | 新 authority 已 merged、concurrency group 共用、期限與 request/storage 上限明確；自然 `event=schedule` run 至少完整驗證一次，包含 SHA、slot、行情 freshness、候選／拒絕原因、budget、持倉延續、ledger 回讀與 Dashboard。手動 dispatch 不算自然驗收。 |
| 10 | P1，結案 | **部署與交接收尾。** 對需要網站變更的 SHA 核對 Pages build/deploy/browser；同步 README、current status、Operations map、機器狀態、runbook。 | 提供明確 DONE/BLOCKED/UNKNOWN/NOT_RUN 表；工程 CI、Pages、成本、runtime、自然排程及模型研究獨立結論。保留可查的 PR/run/artifact/receipt，無未處理 open PR 或未核實分支狀態。 |

### 工作邊界與不要做的事

- 全程 `CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER`；不讀寫或依賴本機 checkout、shell、terminal 或本機排程。
- `FREE-ONLY / 0 USD per month`；不升級、不加付款方式，也不以不明用量冒險啟用 runtime。
- 僅 `PAPER / LIVE-PAPER`；real-money orders 與 live trading 維持關閉。
- 一次性 Billing V0.1、Usage V0.1/V0.2、R2 V0.3、Core100 bootstrap 和其他已消耗 authority 不重跑。
- frozen authority、receipt、artifact、holdout、Equivalence 門檻與歷史 evidence 不修改；新權限用新版本，不竄改舊證據。
- holdout=`FROZEN_UNOPENED`、source switch=false、promotion=false、正式策略 registry 空／Core100 REJECT 狀態照實記錄；不降門檻、不要求每天交易、不輸出或索取 secret value。
- 不建立或啟用 Cloud Paper schedule、D1/R2 provision/write 或新 Cloudflare query，除非對應版本化 authority 已合併。文件、PR、合併授權和 readiness PASS 均不等於 operation authority。
- `WORKFLOW SUCCESS`、合成交易、舊 SHA 的 Pages success、手動 run 均不替代正式自然 Paper acceptance。

### 結案判準

1. **工程完整：**合成正向、NO_TRADE、拒絕、併發、額度、保存、回讀和恢復路徑通過 main CI。
2. **產品呈現：**Dashboard 保留真實 run/schema/UNKNOWN，Pages 對需要部署的 current main SHA 驗證成功。
3. **成本可證：**所有相關 meter、帳務期間、D1/R2 用量、全資源/writer coverage、新鮮度與 headroom 可核對；不能證明就明確標記 `COST_GATE_BLOCKED`，不宣稱零費用或開啟 runtime。
4. **受控 Paper 完整：**有版本化 authority、合格來源或合法 NO_TRADE、固定 budget、單次 genesis、冪等 slot、immutable persistence/readback/recovery 的正式 main 證據。
5. **自然運作已驗收：**符合 authority 的自然 schedule run 證明配置與 runtime 正常；沒有 qualifying run 時只能寫「已配置、待首跑」，不能結案為無人值守運作 PASS。
6. **研究狀態獨立：**Core100 REJECT 不阻擋工程級 NO_TRADE 產品，但不代表模型通過、獲利或取得任何交易權。

### 本輪交付與下一步

這次掃描的查核 SHA 為 `c8d0475360e968d518109d7201a34a6dc3d295ab`。本文件此次只更新目標與排序，不授予任何新外部執行權限。下一個實作切片為：**先收斂 current-status 文件，再完成 Dashboard V0.2/V0.3 投影；先檢查並收尾未合併分支 `codex/dashboard-cloud-paper-usage-v03`，不得將它算作完成。**

---

> 下方以分隔線後的資料為先前查核紀錄與 frozen/歷史 evidence，保持原文，不代表最新狀態。新增紀錄附於文末；不要改寫歷史收據或把舊 SHA 證據升格為 current-main evidence。

---

## 歷史查核快照（2026-09-30 10:24 Asia/Taipei；由本節取代）

### 雲端用量／帳務證據界線（新查核結果）

以下只界定後續可設計的證據來源；**未建立新憑證、未呼叫 Cloudflare API、未授權 live query**。

- **R2 Analytics GraphQL：**官方資料集支援 operations／storage 聚合，最長查詢時間為 31 天，須以 `accountTag` 限定帳戶。聚合資料不是完整 bucket 清單，亦不能證明所有其他 workflow、外部 API token 或使用者寫入者。若回傳資料沒有足以符合既有 freshness gate 的時間戳，仍是 `FRESHNESS_UNKNOWN`。
- **R2 bucket inventory REST：**`GET /accounts/{account_id}/r2/buckets`；需要 `Workers R2 Storage Read`（或更廣的 Write，不建議）。必須枚舉 `default`、`eu`、`us`、`fedramp`、`fedramp-high` 五個 jurisdiction；每頁最多 1,000，依 cursor 續查。新 successor 上限建議每 jurisdiction 最多 10 頁，故全 endpoint 最多 50 requests；任何 jurisdiction 未完整遍歷或仍有 cursor 即 `R2_BUCKET_PAGINATION_INCOMPLETE`，不得宣稱全帳戶 bucket inventory complete。只保留 bucket count、jurisdiction、storage class 和經必要最小化的非敏感識別；不列 object/key、不讀取 object。
- **D1 inventory REST：**`GET /accounts/{account_id}/d1/database`；需要 `D1 Read`；API 每頁最多 10,000，回傳 total count/page metadata。新 successor 上限建議 5 pages、最多 50,000 records。超出上限、total_count 不一致、權限不足或非完整頁均輸出 `D1_INVENTORY_INCOMPLETE`。僅 inventory 不證明 rows/storage usage。
- **D1/R2 usage GraphQL：**分別使用官方 D1／R2 analytics datasets，固定明確 UTC 期間（最多 31 天）、帳戶 tag、指標欄位 allowlist 和嚴格 response bytes 上限；不使用 bucket/database 名稱維度時不得推論逐資源完整度。只觀測 aggregate，不寫入。官方文件沒有確認每個 dataset 都能提供 ≤60 秒 freshness，因此不能假設滿足專案現行 freshness gate。
- **Billing usage API：**官方列出 `GET /accounts/{account_id}/billable/usage` V2 Alpha / Restricted，日期範圍最多 31 天，也明示包含免費額度內的 meter usage；但目前文件指出 cost/pricing 欄位在 billing integration 完成前可能缺席。故此 endpoint 是用量候選，單獨不足以證明總費用為零。V1 為 Alpha/Deprecated，不當首選。
- **Billing history／invoice：**官方 REST 文件列出 account billing history 與 unpaid invoice API，但必須另外驗證所需 permission、分頁與期間完整性、歷史 invoice/adjustment/credit/correction 覆蓋，以及 current-cycle 未結算 usage。只有 subscriptions 的列示價格 USD 0、沒有 unpaid invoices 或 analytics usage 均不足以單獨證明總成本 USD 0。若官方 API 或目前 token 權限不能形成完整可核對集合，保留 `BILLING_COVERAGE_UNKNOWN`，改由帳戶持有人核對 Cloudflare 帳單頁面，不擴權。
- **不可混淆的時間概念：**API response time、資料最新 bucket/day、Cloudflare ingestion/update watermark、invoice billing period 和目前計算時間需分欄記錄；不能把 run 啟動時間當來源資料 freshness。
- **請求與資料上限建議：**新帳戶 evidence successor 每次不超過 64 個 HTTP/GraphQL 呼叫（R2 inventory 50 + D1 inventory 5 + analytics 1 + billing usage 1 + history/invoice candidate 最多 7）；單一 response 建議 ≤1 MiB、artifact ≤256 KiB、不留 raw response／token／帳戶識別值。每個候選 endpoint 的具體日期窗口、分頁與 request upper-bound 必須在 config、程式與 synthetic CI 三方一致；超過即中止、不 retry、不自動切換 endpoint。這是待審設計上限，尚非 authority。
- **費用 gate：**免費額度應按 Cloudflare 帳戶實際 plan、目前週期、服務別 meter、R2 storage/operations/egress、D1 rows/storage、Workers/Pages/其他已啟用產品、全部共同 writers 與延遲 invoice 一起核算。任何用量、項目、帳務覆蓋或 watermark 未知即 `ZERO_COST_NOT_PROVEN`。

### 問題與停止碼索引

| 問題 | 顯示／記錄狀態 | 允許的下一步 |
|---|---|---|
| #644 base 落後 main、舊檢查 action_required | `STALE_MAIN / CHECKS_NOT_RUN_OR_UNKNOWN` | 新生成 docs snapshot 後新分支／PR；舊 PR 不覆蓋、不合併 |
| 一次性 audit 已 dispatch | `CONSUMED_DO_NOT_RERUN` | 保存 artifact／receipt；僅在資訊缺口明確、範圍不同時設計 successor |
| Bucket／D1 pagination 被 cap 擋住 | `*_PAGINATION_INCOMPLETE` | 保持 unknown；先評估是否需要新 authority，不自動加 cap 或重試 |
| 缺時間戳、timestamp 超 freshness | `FRESHNESS_UNKNOWN`／`FRESHNESS_EXPIRED` | 禁止使用該快照作 reservation/headroom 證據 |
| Billing usage V2 無 cost 欄位 | `BILLING_COST_FIELDS_ABSENT` | 不推論零費用；查經核准的帳單證據來源 |
| token 權限／Analytics schema/API 變化 | `PERMISSION_BLOCKED`／`SCHEMA_REVIEW_REQUIRED` | 零後續 request，保留 sanitized 診斷 |
| Cloud Paper 預算、來源或策略資格未知 | `BLOCKED_BUDGET`／`DATA_INSUFFICIENT`／`STRATEGY_NOT_ELIGIBLE` | 不下新倉、不啟動 runtime |
| reservation/persistence 部分寫入或狀態衝突 | `REVIEW_REQUIRED` | 保留 claim、ledger 和 artifact；人工核對，不自動 replay I/O |

### 固定完成與安全條件

- 執行環境：`CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER`；不讀寫或依賴本機 checkout、shell、terminal 或本機 schedule。
- 雲端方案：`FREE-ONLY / 0 USD per month`。零費用證據不完整時不可存取／部署或啟用 runtime；不升級、不加付款方式作 fallback。
- 交易範圍：`PAPER / LIVE-PAPER ONLY`；real-money orders 與 live trading 關閉。
- Holdout = `FROZEN_UNOPENED`；`source_switch_authorized=false`；promotion=false；不調 Core100 門檻。
- Core100 = `REJECT`；正式策略 registry 空；macro context = `REGIME_UNAVAILABLE`。
- frozen authorities、reports、artifacts、receipts 不修改；已消耗的一次性 audit/bootstrap 不重跑；不輸出／索取 secret values。
- 不以手動 workflow_dispatch 冒充自然 schedule；不補跑歷史 slot；不因「workflow SUCCESS」就宣稱交易策略有效。
- 新 provider、D1/R2 存取、帳務 audit、正式 loop 和 schedule 各需當前 main 上清楚版本化授權；文件、issue、PR 草稿和計畫不授予執行權。

### 本目標結案定義

1. **工程整合 PASS：**端到端合成有交易／無交易／拒絕／保存回讀／重播／恢復測試全通過必要 CI。
2. **文件與 Dashboard PASS：**狀態 schema 及 UI 可顯示舊／新 evidence 和所有 UNKNOWN，不虛構零值；Pages 部署驗證通過（僅網站變更需部署）。
3. **FREE-ONLY evidence PASS：**合併後、另有版本化授權的 live read-only evidence 完整覆蓋使用量、帳務、全 bucket/database、freshness、共同 writer 與足夠 headroom；若官方來源不能證明，標示未達成本 gate，不能宣稱已啟用。
4. **受控 PAPER acceptance PASS：**只有在上述條件和正式策略 authority 都允許時才跑；驗證初始化一次、paper position lifecycle、immutable save/read-back/recovery 和 budget/request upper bounds。
5. **自然運作 PASS：**schedule workflow 已授權並啟用，至少一個 qualifying 自然 run 核對完成；否則僅為「已配置、待首跑」。
6. **策略研究結論獨立：**Core100 的 `REJECT` 不阻擋 NO_TRADE 工程完成；不代表目標要求交易或獲利，也不藉此改為 PASS。

> 這份目標是工程排序與驗收條件，不是 Cloudflare live query、資源建立、付費、排程啟用、策略 promotion 或交易授權。

## 目前狀態索引

- 最新 GitHub main：`98a92e74e923273d436c29add3c8679000df614e`（2026-09-30 查核）。
- #644：仍 open；現有記錄的 head/base 已落後 main，舊 checks 不視為通過，須重新核實或重建。
- #645：已合併至上述 main；該 PR 首次 V0.3 dashboard projection 嘗試失敗，最終合併版本保留 V0.2 投影，因此相容性問題仍待修。
- 本文件版本不授予任何新的 Cloudflare API 呼叫或 runtime authority。


---

- 文件日期：2026-09-29
- 本次文件查核基準：parent main `798a23753d9008a0f01d66d6b2296f5c4734f3c5`；此文件不授予 runtime 或資料存取權限。
- PR #628 exact head `3e2c67b0848eb541c43f54a47f7c6edb267a5632` 的 CI [36493558502](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36493558502)、CodeQL [36493558486](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36493558486)、Dependency/SBOM [36493558471](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36493558471) 通過；main CI [36493744676](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36493744676)、CodeQL [36493744613](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36493744613)、Dependency/SBOM [36493744586](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36493744586)、Freeze Guard [36493744563](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36493744563) 均成功。此 PR 未改網站，Pages 未觸發。
- PR #628 加入 repo-source-only D1 REST client 邊界檢查；帳戶級用量新鮮度與外部 writer 覆蓋仍未證明。
- Repository：[qookey109-pixel/crypto-autopilot](https://github.com/qookey109-pixel/crypto-autopilot)
- 文件定位：交付範圍與驗收清單；不授予新的 runtime 或資料存取權限。
- 歷史證據基準：PR #614 合併至 main `abda84a45de66dc214be40ce05ee0c2ccb79e415`；PR #618 Dashboard 部署證據維持獨立記錄。
- 狀態：Cloud Paper 持續實作，activation disabled。PR #614 已接通資格門控 adapter；PR #622 用 test-only fixture 驗證同一 composition 的入場／出場／帳戶延續／保存／後續 `NO_TRADE`。正式策略 registry 仍空，正式循環為 `NOT_RUN`。

## 最新雲端預算門檻 — 2026-09-29

- readiness 歷史查核基準 main：`d4580c1142f9ddadb92cacc810f29bc1988a39df`。接續時重新查詢 main 與 open PR，不把此快照當成即時狀態。
- 帳單唯讀 readiness：[run 36497596228](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36497596228)，`workflow_dispatch`、main、attempt 1，workflow conclusion `SUCCESS`；報告為 `BLOCKED_MISSING_BILLING_READ_ONLY_CREDENTIAL`。Cloudflare requests=0，secret values printed=false，一次性 audit authority 未消耗。
- D1/R2 用量 readiness：[run 36471242643](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36471242643)，報告為 `BLOCKED_MISSING_READ_ONLY_CREDENTIAL`，Cloudflare requests=0，一次性 usage audit 未消耗。
- 下一個可執行門檻：在 GitHub Actions out-of-band 設定 account ID 與對應 read-only credentials，之後先跑零網路 readiness；只有 `READY` 才能各自執行一次性唯讀 audit。不得重跑消耗或結果不明的 audit。
- Cloud Paper 維持 activation disabled；沒有 Cloudflare API 請求、D1/R2 使用量校準、正式受控循環或自然模擬排程。

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

以下未勾選項目保留作正式受控驗收；上方合成 CI 矩陣已通過的情境不需重新列為未實作。CI 通過不代表帳戶級 freshness 或外部 writer coverage 已證明。

- [ ] 每次外部操作前檢查本次、每日及適用帳期額度。
- [ ] 用量證據缺漏、過期或覆蓋不完整時，在外部存取前停止。
- [ ] 行情與 R2 使用同一個 run-scoped reservation guard；接線不一致時在任何存取前拒絕。
- [ ] 並行執行不造成超額預留或重複寫入。
- [ ] 同一 slot 重複執行不重複成交或推進帳戶。
- [ ] 重新啟動後延續已驗證帳戶，不重新初始化資金。
- [ ] 部分寫入或狀態衝突輸出 `REVIEW_REQUIRED`，保留證據。
- [ ] secret 不出現在 log、artifact、報告或 Repository。
- [x] 既有工程 GitHub CI 通過（#622/#624/#628；本批修正仍須由本批 CI 獨立驗證）。

**交付物：** 接線修正、相關回歸測試、檢查結果及未解阻塞。合成測試的用量快照不等於正式帳戶用量證據。

## 4. 第二批：完整流程可驗收

**優先度：P0。**

### 工作範圍

串接既有行情轉換、候選、策略資格、風控、模擬核心、保存與報告。使用合成資料驗證交易路徑；正式資格判定維持現有規則。

### 驗收清單

- [x] 合成正向路徑通過：qualified fixture 經同一 composition 完成模擬入場、出場、帳戶更新、保存及下一輪 `NO_TRADE`（PR #622 CI；僅測試資料，不是 production 策略）。
- [x] 合成 CI 已覆蓋無候選／空策略及模型 `REJECT` 的明確拒絕與零新倉（上方矩陣；不是正式 runtime 驗收）。
- [x] 既有合成 CI 已覆蓋過期、未收盤、缺漏或不連續 K 線拒絕（上方矩陣）；本批另補空成交列表拒絕。
- [ ] 風險超限、來源失效及額度不足時停止相關操作。
- [x] 合成 CI 已覆蓋重播、重啟恢復及部分結算失敗（#624 矩陣）；正式儲存恢復仍待受控驗收。
- [ ] 報告可追溯資料來源、時間、run、slot、狀態識別碼及實際讀寫次數。
- [x] 既有版本的 Python 3.12／3.13、Ruff 與適用治理檢查已通過（本批變更須另外通過其 exact-head CI）。

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
- [x] PR #618 已交付帳戶、持倉及損益的證據投影；未知值維持 null，不顯示成零。
- [x] PR #618 的 Pages build、deploy、桌機及手機驗證通過（14/14）；這是該產品版本證據，不宣稱本次後端修改已重新部署。
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

已完成的工程工作：PR #624 整理合成驗收矩陣，PR #628 將 Repository D1 REST client 邊界及 guarded query order 納入 CI。這不代表帳戶外部 writer 已受控。本批修正 slot／實際時間混用與空成交列表，回歸測試由本批 GitHub CI 驗證；後續仍需完整帳戶 writer inventory 與 production query metadata 校準。現有 4,000 rows/query、384 query reservations/day、16 KiB/statement 是 policy/test envelope，並非 Cloudflare production calibration。不得因合成 CI 通過就宣稱 production usage/headroom 完成。

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

- D1 ledger 只接受 canonical 15-minute slot ID，實際 `now_ms` 必須在該 slot 的 `[scheduled_at_ms, scheduled_at_ms + 600000]` 範圍內。名義 slot 用於去重；freshness、UTC 帳期與 reservation timestamp 使用實際時間。拒絕任意 slot、提早啟動、過期 slot 或把歷史 slot 重新編號。
- rolling query 使用實際 `reserved_at_ms` 索引，窗口為最多 31 天；每 15 分鐘最多一個唯一 slot。計入最多 10 分鐘延遲與窗口端點，保守上界為 31 × 96 + 1 = **2,977** 筆 ledger slot。跨 UTC 日的延遲可能令當日來源 slot 多於 96；實際每日／帳期請求及 bytes 上限照常生效，不增加預算。
- 單次 guard ceiling 設為 **4,000 rows**，包括最多 2,977 筆 slot 與 1,023 rows 的額外保留空間；超過 ceiling 時 fail closed。GitHub CI 的 SQLite `EXPLAIN QUERY PLAN` 檢查索引路徑，合成測試驗證 canonical slot 與日容量算式。
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

Cloudflare API **尚未呼叫**。billing readiness [36497596228](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36497596228) 已執行，報告為 `BLOCKED_MISSING_BILLING_READ_ONLY_CREDENTIAL`，Cloudflare requests=0，一次性 audit 未消耗；結果不會證明 invoice 總額、所有計量產品、外部 writer 覆蓋或零成本。零費用結論仍需 fresh account-wide usage、帳單與完整 writer coverage 證據。Cloud Paper runtime、D1/R2 寫入與排程仍關閉。

## 2026-09-29 有界修正：slot 時間與成交完整性

- `scheduled_at_ms` 是名義排程時間，必須符合既有 7/22/37/52 分 slot；`tick_ms` 是實際啟動、行情與 lifecycle 時間。延遲啟動須顯式傳入兩者；省略 schedule 參數只保留原 exact-tick 呼叫相容性，不推算或補跑歷史 slot。
- composition 與 D1 ledger 在外部操作前驗證 600 秒上限；用量 freshness 和帳期按實際時間驗證，未放寬 60 秒用量 freshness。報告與 claim 加記 `scheduled_at_ms`，歷史報告回讀不要求新增欄位。
- 空 recent-trades 回應輸出 `TRADE_TAPE_EMPTY_UNPROVEN`，不以 order book 代替成交期間證據；持倉遇到此錯誤保留 prior state 與未完成 claim，不結算、不自動重跑。
- 回歸覆蓋延遲啟動、未來／過期證據、錯誤／過期 slot、重複 slot、空成交列表及持倉不推進。原正向 fixture 改為明確的合成成交紀錄。
- 本批僅修正未啟用的工程路徑與文件；activation、正式 registry、frozen 證據、費用上限與既有 cron 不變。驗證狀態以本批 PR exact-head GitHub checks 為準，不預先聲稱通過。
