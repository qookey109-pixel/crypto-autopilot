## Checkpoint before status sync — 2026-10-01

Evidence basis before this documentation update: GitHub main `05c71e360d4e79d6d418f17fa8ba22fa1eb4bf4a`; open PRs = 0. PRs [#669](https://github.com/qookey109-pixel/crypto-autopilot/pull/669), [#670](https://github.com/qookey109-pixel/crypto-autopilot/pull/670), and [#671](https://github.com/qookey109-pixel/crypto-autopilot/pull/671) are merged. The [V0.2 request-budget assessment](CLOUD_PAPER_REQUEST_BUDGET_ASSESSMENT_V0_2.md) records the request envelope, code-derived warmup minima, strategy-router boundaries, and unresolved source, quota, freshness, and persistence questions. Post-merge Python 3.12/3.13, CodeQL, Dependency/SBOM and Freeze Guard passed; workflow-static was skipped because workflows were unchanged.

- The design envelope is 36 requests/slot, 3,456/day and 103,680/rolling 30 days, above the unchanged V0.1 limit of 18/run and 1,728/day. It is an arithmetic bound, not an observed provider allowance or usage.
- Code-derived minima are 21 closed 4H bars for breadth/regime, 200 each for 60M and 15M full technical snapshots, and 21 where the default structure range is used. The six research-router families share the full technical and regime gates; some also use market structure. This does not certify unknown future production strategy inputs while the registry is empty.
- The 15M freshness proposal can be exceeded by delayed starts. Cross-run reuse of breadth requires durable storage with additional cost and recovery paths. No cache or external access/activation was performed.
- Cloud Paper remains disabled, its production entrypoint is not wired, no natural schedule is configured, D1 is unprovisioned, registry is empty, Core100 quality is REJECT, and macro regime is unavailable. Account-wide zero-cost/headroom and complete writer coverage remain unproven. Do not rerun consumed one-time Billing/Usage/bootstrap stages.
- Next: establish compliant time-aligned market-context/breadth sources, authoritative provider and shared-account budget evidence, and complete R2/D1 cost/writer coverage; then size a successor envelope that fits the FREE-ONLY guard before considering a controlled acceptance.

## Historical checkpoint — 2026-09-30 (#662 merged)

Historical evidence basis: GitHub `main=919941f2f8d8db77b0bc8372727de46d8406867f`; open PRs at that checkpoint = 0. Resolve main live; these earlier blocks retain their original SHA as historical checkpoints.

- #661 completed the first compatible storage minimization: V0.2 loop reports reference the persisted step by `step_id`, while legacy V0.1 reports remain readable. The matched synthetic profile decreased from 206,181 to 157,367 canonical JSON bytes (~23.7%); this is not production R2 or fee evidence.
- #662 synchronized current status and storage-lineage documentation. No provider, D1, or R2 call occurred; Cloud Paper remains disabled and no natural simulation schedule is configured.
- Remaining gates: fresh account-wide usage and zero-cost evidence, full writer coverage, D1/R2 headroom, formal entrypoint, production registry qualification, and controlled main PAPER acceptance. Core100 remains REJECT.
- Next storage slice: evaluate compact `live-run-step` references to independent `live-tick` evidence with legacy reader, digest, continuation, recovery, replay, and partial-write regression coverage. Independently reconcile missing market fields with compliant official public sources and terms.
- Preserve CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER, 0 USD/month, PAPER/LIVE-PAPER ONLY; do not reopen holdout, source switch, promotion, real trading, or consumed one-time audits.

# Crypto Autopilot — 完整雲端模擬產品交付目標

## Current checkpoint — 2026-09-30 20:44 Asia/Taipei

Evidence basis: GitHub main `4b12f0c9ad508e09d712320111f2e12423b69aca`; open PRs = 0. Cloud Paper remains disabled and no production cycle ran.

- PR #660 completed the storage lineage inventory. PR [#661](https://github.com/qookey109-pixel/crypto-autopilot/pull/661) implemented the first compatible minimization: V0.2 reports reference the immutable persisted step by `step_id`; V0.1 embedded reports remain readable.
- Exact-head PR CI passed Python 3.12/3.13, full tests, Ruff/workflow static, CodeQL and SBOM. Post-merge main CI [36716389946](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36716389946), CodeQL [36716389968](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36716389968), SBOM [36716389930](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36716389930), and Freeze Guard [36716390111](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36716390111) passed. Pages was not triggered; no website files changed.
- The matched synthetic three-slot entry/exit/no-trade fixture is 26 objects in both versions; canonical JSON bytes fell from 206,181 to 157,367 (48,814 fewer; about 23.7%). The report aggregate fell from 70,352 to 21,538 bytes. [#658 baseline](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36710655801/artifacts/11094147043) and [#661 result](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36716119165/artifacts/11095802879) are synthetic CI evidence only. They do not prove R2 savings, real charges, account-wide usage, or headroom.
- No old objects were migrated or rewritten; #661 did not access a provider, D1 or R2 and did not enable a runtime or schedule.
- Remaining P0 gates: fresh account-wide cost/usage evidence, data freshness and complete writer inventory, D1/R2 headroom proof, formal production entrypoint and controlled main PAPER acceptance. Billing/Usage one-time authorities are consumed and must not be rerun.
- Next engineering slice: evaluate `live-run-step` → `live-tick` reference minimization while keeping old schema reads, recovery, digest lineage, idempotency and partial-write fail-closed behavior. In parallel, record actual missing strategy inputs and evaluate official public exchange API/JSON/CSV/HTML candidates one by one. Scraping is only a compliant public-source candidate; it cannot bypass authentication, limits, source-switch authority, or provider provenance.
- AI Resource Hub is an engineering/catalog reference, not a market-data feed. Reuse only reviewed patterns (structured source metadata, health/freshness evidence, deterministic fallback and browser tests); do not import an entire app or treat catalog listings as a provider/free-tier approval.

## Storage profile result — 2026-09-30 19:52 Asia/Taipei

Evidence basis: post-PR #658 main `7424ccfbaf0362f588410de037e593f0105745a0`; no open PRs at that checkpoint. The synthetic storage profiler is implemented in `scripts/measure_cloud_paper_storage_v0_1.py`, run by existing GitHub CI and uploaded as artifact [11094147043](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36710655801/artifacts/11094147043). PR #658 head `75e766a534e29b89be1ab96dce860964bfe66ef8) is merged.

| Existing synthetic fixture | Final objects | Canonical JSON bytes |
|---|---:|---:|
| no-trade | 10 | 33,433 |
| entry → exit → next no-trade (3 slots) | 26 | 206,181 |
| replay/restart | 18 | 59,327 |
| verified recovery | 10 | 33,433 |
| failed settlement | 10 | 33,433 |

The three-slot entry/exit fixture assigns 70,352 bytes to `cloud-report`, 48,778 to `live-run-step`, 40,714 to `live-tick`, and 39,310 to `live-state` (199,154 bytes combined). Treat these as high-size inspection candidates, not proven duplicates: the next step is a writer/reader/recovery lineage inventory before any schema change. Synthetic store calls do not represent actual R2 operations. The report excludes service metadata, external writers and D1; gzip is an estimate only. It establishes no production savings, account headroom, zero-cost conclusion or activation permission.

PR #658 PR checks passed: CI #36710655801, CodeQL #36710655868, Dependency/SBOM #36710655876. Post-merge main CI #36710934061, Freeze Guard #36710934128, CodeQL #36710934055 and Dependency/SBOM #36710933979 passed; workflow-static skipped on push and Pages did not run because no site files changed.

Next: map canonical writers/readers and recovery requirements for those four object kinds; design a backward-compatible minimal reference/schema change only where replacement is proven; compare baseline and revised profile on the same fixtures. Production cost evidence, D1 provisioning, controlled PAPER acceptance, natural schedule, and dashboard runtime projection remain separate incomplete gates.


## 歷史進度基準 — 2026-09-30 15:06 Asia/Taipei

Repository：[`qookey109-pixel/crypto-autopilot`](https://github.com/qookey109-pixel/crypto-autopilot)  
查核基準：`main=c9e220cb6f2191e6fb0dd50a5918a62971360e8e`；查核時 open PR = 0。Repository main 是正式 authority；此節記錄本次查核的 basis，不宣稱此文件合併後仍是最新 main。以下計畫按依賴順序連續執行，小批 PR、雲端 CI、合併後回讀 main；卡在外部證據時先完成不依賴它的工作，不以手動 run 代替自然排程證據，也不把未知標成通過。

## 一、完整完成目標

交付一套在 GitHub／雲端 runner 上可安全維持的 Cloud PAPER 模擬產品：

**公開行情 → 候選與資格判斷 → 風控及組合准入 → PAPER 回合 → 防重保存與中斷恢復 → 可追溯報告 → Dashboard 投影。**

系統必須同時正確處理合格候選與正常不交易。當 registry 空、模型品質拒絕、行情不足或權限／用量 evidence 不足時，結果應是明確的 `NO_TRADE`、`DATA_UNAVAILABLE`、`REVIEW_REQUIRED` 或 `NOT_ENABLED`，不建立倉位，也不將拒絕中的策略用測試交易偽裝成正式成果。此交付證明工程循環與治理成立，不證明策略獲利，不授予 LIVE 或真實下單權限。

### 完成定義

1. 每次外部請求前都有新鮮、同一 UTC 日且可追溯的預算證據與 reservation；過期、缺漏、超額、競爭或部分寫入均 fail closed。
2. 用量／費用／容量的資料來源、刷新延遲、涵蓋範圍、全部已知 writers 與剩餘 headroom 可證明符合 `0 USD/month`；Cloudflare analytics 缺欄位時不得用查詢時間冒充資料 freshness，不得把部分 bucket 當完整帳戶。
3. PAPER loop 由一個正式受控入口串接已存在的 adapter、registry、risk、portfolio、composition、ledger、slot claim、persistence、recovery 與 report；同 slot 冪等、不同 slot 不重複成交，中斷後只從已驗證狀態恢復。
4. 有雲端 CI 的正向路徑與各種拒絕／恢復路徑，以及一個正式 main 的受控驗收結果。沒有合格策略時，正式驗收應可產生可讀的零新倉結果；合成策略只可在測試 fixture，不可充作 production eligibility。
5. 排程在版本化 authority、預算及受控驗收通過後才可啟用；初次自然 run 需以 schedule event、exact SHA、slot、artifact/report 與 read-back 證據確認。漏掉的 slot 不補跑。除非觀測本身是明確驗收條件，無須等待固定七天才可完成工程交付。
6. Dashboard 綁定正式 report identity，清楚分辨正常不交易、資料不足、系統故障、檢視中及未啟用；未知資產、損益、用量與 headroom 顯示 UNKNOWN/null 而非 0。完成 Pages deploy 後做 desktop/mobile production browser 驗證。
7. 目前每批有 exact base/head/diff、必要 review、CI 和治理 checks；合併後確認 live main、適用 checks、部署與分支清理。文件、機器索引與程式狀態同步，舊收據和 frozen evidence 原樣保留。


## 本輪目標修訂：即時行情、最小必要保存與多種公開擷取方式 — 2026-09-30

查核基準 main：`921239d173f7e3ef548ef3354fc8b430cbbe37ef`；open PR=0。#655/#656 文件同步與 Maintenance 結果分類已合併，不重列為未完成的第一批。本節更新工程目標與來源評估，不變更任何 frozen 契約、依賴、runtime、資料來源或排程權限。既有 Cloud Paper activation=false；正式入口、D1 建立與受控循環仍待完成。

### 1. 保存目標：即時取用，保留能恢復與說明決策的最小證據

日常循環按需取得公開行情與必要的近期已收盤 K 線；預設在雲端 runner 記憶體內使用後釋放。研究用歷史資料與日常模擬帳戶分開管理，不要求每輪下載或持續擴張歷史資料庫。

| 類別 | 目標保存方式 | 不可省略的條件 |
|---|---|---|
| 最新報價、深度、未用於決策的行情 | 當輪暫存，預設不長期保存原始回應 | 記錄必要來源、資料時間、品質結果；被用於成交或決策的部分依下一列處理 |
| 近期已收盤 K 線與指標暖機資料 | 按需、有上限取得；不每輪重複持久化整段資料 | 驗證完整區間、收盤、連續性、時區與 holdout 邊界；無法再次取得不能假設可重現 |
| 實際決策／模擬成交所依據的資料 | 保存規範化的最小輸入切片、指標值、資格與風控結果、來源／程式／設定版本 | 必須足以驗證宣稱的決策或成交；hash 只能校驗已有內容，不能取代已丟棄資料或宣稱完整重播 |
| 模擬帳戶、持倉、成交、費用、損益 | 持久化，保持不可變事件與已驗證狀態鏈 | 重啟延續帳戶；平台沒有本專案的虛擬帳戶，不能向平台重新取得 |
| slot claim、預算 reservation／settlement、恢復紀錄 | 持久化必要狀態，完整性檢查與回讀保留 | 不因節省儲存而破壞原子性、防重或部分寫入辨識 |
| 回測／訓練歷史與已驗證成果 | 獨立研究資料範圍；按版本追溯 | 既有 frozen 資料與收據保留，不因本目標自動刪除；未來清理另立保存規則 |
| Dashboard 衍生資料 | 精簡投影，引用正式報告 identity | 不複製全部行情；未知值不能顯示成 0 |

策略穩定後，日常執行可以不依賴大型研究歷史庫，但仍需策略的暖機資料、持倉事件證據與驗證紀錄。行情不完整時停止推進持倉，不能用目前價格推測離線期間的觸價順序、成交或損益。

正式修改保存格式前，先列出現有每種寫入物件、reader、恢復依賴及是否 frozen。不得直接刪欄位；必要時新增 successor schema，驗證新舊報告相容。2 MiB/run 是目前預算上限，不是每輪必須寫滿或必須保留全部行情。節省量需以新舊報告實測比較，不能先聲稱已降低用量。

### 2. 資料取得不限定 API，但依用途與證據選擇

公開 API 不一定需要 API key；網頁上的資料也可能來自公開 JSON 介面。取得方式和資料供應者是兩個不同維度，同一平台改用另一端點或 HTML 仍須審查契約，不能自動繞過原有來源限制。

| 方式 | 適合用途 | 採用前必要查核 |
|---|---|---|
| 官方公開 API／公開 JSON／CSV／RSS | 結構化行情、資料下載、公告 | 文件與端點、欄位、資料時間、覆蓋、限速、存取條件、免費用量 |
| 公開靜態 HTML 擷取 | 平台公告、規格、公開表格；行情用途另驗 | 固定欄位映射、symbol／market type／單位、頁面延遲、完整性、版面變動 |
| 雲端 headless browser | 必須 JavaScript 渲染且無合適結構化來源的公開頁面 | timeout、頁數、子請求、資源下載與 runner 成本；只能擷取明確欄位 |
| WebSocket | 未來需要串流的獨立候選 | 斷線、序號、補齊與持續運行成本；本次不引入常駐服務 |

優先保留已驗證且符合用途的 adapter；網頁／瀏覽器是明確評估的候選，不是故障時自動 fallback。研究及展示擷取通過，不代表符合策略或成交的精度與完整性要求。只抓當輪所需頁面，不做全站 crawl。

每個候選來源必須登記：用途、provider、URL/端點、取得方法、parser 版本、symbol 映射、時區、source timestamp、retrieved_at、單位與精度、資料區間／分頁完整性、更新延遲、請求與位元組上限、存取條件、可保存範圍，以及停止原因。來源時間缺漏維持 UNKNOWN，不用查詢時間冒充。價格、缺失欄位及失敗回應不得由 LLM 猜測或補零。

使用允許的公開存取方式；遇到登入、付費牆、CAPTCHA、403/429 或來源限制，記錄受阻並停止。此計畫不採用反偵測、代理輪換或繞過限制來維持執行，也不放寬 provider/source-switch 邊界。瀏覽器的子請求與依賴成本仍納入共享預算；開源工具並不自動等於零執行成本。

### 3. AI Resource Hub 參考結果

資源庫入口：[AI Resource Hub](https://qookey109-pixel.github.io/ai-resource-hub/)。本次網站抓取工具無法讀取首頁，改讀同專案的 [resources.json](https://github.com/qookey109-pixel/ai-resource-hub/blob/main/data/resources.json)，並查閱以下上游文件／程式。目錄是候選索引，不是資料品質或免費額度保證。

| 資源 | 本專案可借鏡的部分 | 本輪採用決定 |
|---|---|---|
| [Scrapling](https://github.com/D4Vinci/Scrapling) | Python parser／明確 selector、靜態與動態擷取分層 | 靜態公開頁面擷取候選；不先新增依賴。交易欄位不得靠 adaptive selector 靜默換欄位，版面漂移應拒絕 |
| [Playwright MCP](https://github.com/microsoft/playwright-mcp) | 結構化頁面檢視與瀏覽器操作 | 研究動態頁面與驗證擷取欄位的參考；正式排程若需要瀏覽器，優先沿用既有 Playwright 能力，不新增 LLM/MCP 常駐服務 |
| [Fincept Terminal](https://github.com/Fincept-Corporation/FinceptTerminal) | 多格式 parser、欄位映射、來源與輸出正規化 | 借鏡接口分層，不整套導入、不複製程式碼；依賴或代碼採用前再審查授權 |
| [Firecrawl MCP](https://github.com/firecrawl/firecrawl-mcp-server) | 網頁擷取／結構化結果的接口設計 | 研究候選；託管方案有限額與額外依賴，零費用與正式行情用途未驗證，不接入 runtime |
| [Public APIs](https://github.com/public-apis/public-apis)、[free-for.dev](https://github.com/ripienaar/free-for-dev) | 搜尋來源和免費服務的索引 | 逐個回到服務官方文件確認，不把清單標籤當免費或可用證據 |

實際程式查閱：
- Fincept [FeedScraper.cpp](https://github.com/Fincept-Corporation/FinceptTerminal/blob/main/fincept-qt/src/services/feeds/FeedScraper.cpp) 支援 JSON/CSV/XML/RSS 類欄位映射，可借鏡 parser 與統一輸出的分離；其中缺少時間時補現在時間的展示行為，不適用本專案 source freshness。
- Fincept [fii_dii_scraper.py](https://github.com/Fincept-Corporation/FinceptTerminal/blob/main/fincept-qt/scripts/fii_dii_scraper.py) 是特定股票市場資料擷取範例，不是 Pionex adapter。其缺值轉 0、錯誤回空陣列的處理不可照搬；本專案需要區分失敗、缺值、完整空結果與有效 0。
- 上述工具尚未對 Pionex 行情相容性作實測；本批沒有執行平台爬取、安裝、來源切換或新增雲端排程。

### 4. 納入主線的下一批工作與完成標準

1. **最小保存盤點（P0）：** 列每個物件的用途、reader、恢復依賴、目前位元組／操作數與可精簡項；明確保留必要決策輸入與狀態。依現有程式與合成 fixture 開始，不新增外部存取。
2. **來源與方法矩陣（P1，可與 P0 獨立準備）：** 優先一個真正缺資料的指標／公開頁面，核對原始來源、時間、完整性與成本。結果為可提出具體 adapter 或明確不適用，不湊來源、不重寫已完成 client。
3. **小批保存實作與雲端驗收（P0）：** 針對盤點結果改最少物件；新舊 schema 相容、重播、重啟、部分寫入、決策追溯通過；列出修改前後實測，不削減保護性讀寫。
4. **重算完整循環成本（P0）：** 將行情擷取、瀏覽器子請求（若採用）、預算帳本、寫入、回讀、恢復與儲存增長一併計入。成本查核仍須解決完整 inventory/writer/freshness，不能因少存行情就跳過。
5. **正式接線與啟用：** 依既有順序完成 successor authority、受控 main acceptance、首次自然 schedule、Dashboard。任何新增來源或保存契約須先完成必要版本化授權；此目標文檔不授予外部執行權。

目標回歸項目：缺 source timestamp、locale／單位錯誤、不同市場同名 symbol、頁面漂移、部分表格／分頁、未收盤 K 線、403/429／來源不可用，以及最小保存後仍能恢復與說明決策。以合成 fixture 在 GitHub CI 驗證；即時外部驗收另依有界授權執行。

完整交付仍要求正式循環、持久化回讀、首次自然排程及 Dashboard 證據。安全停用或文件 CI 綠燈只能記為受阻／工程準備完成，不算完整自動循環交付。


## 二、截至 c9e220c 的歷史現況（後續狀態見最新查核）

- 即時 main：`c9e220cb6f2191e6fb0dd50a5918a62971360e8e`；目前沒有 open PR。
- PR #654「D1 usage evidence before each query」已合併。PR head `2117448a00edf599d08c8d6fb27596ba9cf0a0ab`；PR CI #36680835582、CodeQL #36680835575、Dependency/SBOM #36680835567 成功。合併後 main CI #36681001425、Freeze Guard #36681001474、Dependency/SBOM #36681001359、CodeQL #36681001327 均成功。修正會在 shared admission 前檢查證據、成功預留後再檢查 freshness/UTC 日，避免過期或換日後查目標資料；無效時保留既有 reservation 並停止目標 query。
- 這個修正只有來源與合成 CI 證據；D1 仍未 provision，migration 仍 prepare-only，沒有 Cloudflare runtime 外部 I/O，不能推論 production usage 已驗證。
- PR #653 所在 main `89dd07a26ebad0d780b009eb5051b16d53fe75e6` 的 Cloud Paper Dashboard Pages build/deploy/browser-production run #36676578296 成功；同 SHA CI #36676578303 成功。PR #654 是 D1 guard 程式變更，沒有新 Pages 部署需求。Dashboard deploy success 不是 PAPER runtime acceptance。
- 自然 Health #36676258650 成功；其 Maintenance run #36676302904 的 inspect 成功、propose 以 `OBSERVATION_CHANGED` 停止。保留此安全停止結果；不可放寬觀測一致性、不可把它當作本次 NO_CHANGE 驗收。
- R2 Usage V0.3 唯一 run #36593296360 已消耗：一個 returned bucket、16,304 objects、616,541,780 bytes；30 日 operation aggregation 為 125,309 requests、6 groups，但沒 timestamp。這僅是部分 analytics evidence。完整 bucket inventory、全部 writers、D1 使用量、metered charges、freshness、headroom 與零費用皆 UNKNOWN；billing V0.1、Usage V0.1/V0.2、Usage V0.3 與 Core100 V0.2 一次性 authority 都不可 rerun。
- 正式 Cloud Paper `activation=false`、production cycle `NOT_RUN`、entrypoint `NOT_WIRED`、自然 schedule `NOT_CONFIGURED`；D1 未 provision。正式策略 registry 空、Core100 模型品質 `REJECT`、macro regime `REGIME_UNAVAILABLE`。因此尚無正式 paper cycle；不可稱作已執行 `NO_TRADE`。
- 最近 main CI 的型別資訊性診斷為 42（protected 18、一般 cleanup candidates 24），nonblocking。不得觸碰 protected 項、放寬檢查或用大量 `Any`／ignore 讓數字下降。
- GitHub open issues 尚有 #224（9/5 的排程 delivery observation）與 #111（FREE-ONLY 架構）。這些是規劃層，不是 authority；第一批排程需檢查 #224 是否已過時及 #111 是否已由現行方案取代，整理時保留歷史連結。

## 三、待改善問題與風險

### P0 — 阻擋安全啟用

1. **雲端成本和用量 evidence 不足。** 已消耗的一次性 run 不重跑。需要先判斷官方來源可否提供帳戶層級 D1/R2 resource inventory、usage、invoice/metered charges、全部 writers 和可靠 freshness。若來源不能證明本專案政策要求，記錄具體欄位差距與 `COST_GATE_BLOCKED`，不擴大 token、不反覆做同等 audit、不啟用 runtime。
2. **長期保存與 D1 ledger 自身成本未校準。** 既有 policy envelope：R2 約 2 MiB/run、96 slots/day、31 天理論 6,241,124,352 bytes；警告 6.4 GB、8 GB hard stop。這是 policy arithmetic，並非實際用量或安全 headroom。D1 每日 reservation policy 為最多 384 次 admission/target query、3,072,000 rows read、7,680 rows written、12,582,912 bytes storage-growth envelope，均為 synthetic/policy estimate；migration 未套用，ledger 自我增長未量測。
3. **production PAPER entrypoint 尚未接線。** 已有模組與 synthetic end-to-end 測試，但沒有正式 runtime run、D1 服務、受控 main acceptance 或自然 schedule。只能在 authority、零費用證據及持久化 headroom 全部過關後接線。
4. **市場 context 仍有資料缺口。** Pionex public OHLCV 不會提供 TOTAL3、BTC dominance 或市場 breadth 所需全域脈絡；API key 不是解法。來源授權、指標定義、時間對齊及免費限額未證明前維持 unavailable；不得把 Binance 資料標成 Pionex-native，也不得以未驗證 source 補值。

### P1 — 交付完整性與可維運性

5. **狀態入口和機器索引落後 live main。** `CURRENT_STATUS.md`、`PROJECT_STATUS.md`、Cloud Paper delivery JSON、Current Operations JSON 的 current checkpoint 仍引用 #654 前 SHA／PR #622 時代資訊。此次以 PR 同步 current state；只增加/取代 present-tense checkpoint，舊 audit、收據、frozen 區段仍作歷史證據。
6. **Maintenance 的最新自然鏈需正確分類。** #36676302904 是 `OBSERVATION_CHANGED`，不是 propose PASS 或 NO_CHANGE。後續驗收以當時的 exact main 和自然 Health trigger 作證；不可 manual dispatch 補算、不在來源變動時強行出 PR。
7. **Dashboard 需與正式 cycle evidence 同源。** 目前網站 Pages 已成功部署，但 Cloud Paper runtime 尚未執行。下一版只投影正式 report、來源快照時間與可追溯 identity；不同狀態不混為一類，也不把空值顯示為 0。
8. **舊 issue / 技術債須收斂而不擴張。** 更新 #224、#111 的狀態或關聯前先讀完整 issue 和現行 authority；關閉/標記過時必須有明確理由。工程改善限於最新 CI 支持、行為不變的小批次。
9. **排程觀測只能驗證真實觸發。** schedule run 必須看 event、run attempt、head SHA、job、artifact/report、slot 和 read-back；手動補跑不能替代自然 schedule。七日觀測僅在要作 cadence/reliability 結論時需要，不作工程交付的無條件等待。

## 四、依序執行排程

採連續、依賴式小批交付；時間不設無意義的等待日，外部 authority/credential/資料不可用時以精確 blocker 停住該外部操作，其餘獨立工作繼續。

| 順序 | 優先度 | 工作批次 | 驗收、停止條件與產物 |
|---|---|---|---|
| 1 | 已完成 #655/#656 | **狀態與目標同步 PR（保留當時交付範圍）**：本目標、CURRENT_STATUS、PROJECT_STATUS、machine delivery/operations checkpoint 同步至 main `c9e220c`；登記 #654 及新 CI；清楚區分已完成、blocked、NOT_RUN 與歷史。 | PR diff 只改現況入口與本目標；JSON parse/static validator、必要 docs CI 通過；精確 head/base/checks 核對後合併並回讀 main。不可改 frozen receipts/config。 |
| 2 | P0，緊接 | **單次可行性決策：cost/freshness/inventory/writer coverage/storage-growth。** 只用已保存 evidence 與官方文件/API 欄位契約設計，不執行重複或未授權 Cloudflare query。把每個必要量列為 source、permission、range、freshness、上限、writer coverage、盲區。 | 產出明確 `READY_TO_PROPOSE_SUCCESSOR_AUTHORITY` 或 `COST_GATE_BLOCKED`；若官方能力不可能達到 gate，直接列出需由使用者/服務端提供的非秘密證據，不製作無效重複 audit。 |
| 3 | P0，可平行準備 | **预算與 persistence 守門核對。** 驗證 provider/D1/R2 每個 target I/O 的 reserve→request→settle、post-admission freshness、UTC rollover、共享 slot concurrency、duplicate replay、partial write recovery、ledger growth 與硬停。#654 D1 二次 freshness guard 已完成，針對性回歸以其合併證據為準。 | 雲端 CI 覆蓋所有已識別 repository writers；unknown/stale/over-budget 時外部 requests=0；同 slot 最多一位勝者；partial write 不釋放 reservation。帳戶外 writers 未證實須維持 UNKNOWN。 |
| 4 | P0，依賴第 2、3 項 | **建立 successor authority 與受控 PAPER acceptance。** 只有資料路徑/費用/headroom 可證明符合 FREE-ONLY，才提出新版本 config/receipt 並 merge；每項外部操作前確認精確版本 authority。最小執行一次正式 main non-access preflight，再經獨立 gate 授權執行受控 paper cycle。 | 報告列 exact main/run/attempt/slot/source/artifact/read-write counts/state IDs。registry 為空或模型 REJECT 時只能零新倉並記原因；成功 workflow 不代表交易有效。任何出現付費、未知預算、部分寫入、錯誤來源時停止並保留報告。 |
| 5 | P1，受控 acceptance 後 | **自然排程與狀態回讀。** 只有第 4 項通過且排程本身在版本 authority 內才啟用；不新增超出 authority 的頻率。確認第一個自然 schedule run、slot idempotency、artifact/ledger read-back； missed slot 不補跑。 | natural `event=schedule`、exact SHA、attempt、report、寫入與回讀身分均匹配。沒有自然 run就標 `CONFIGURED_WAITING_FIRST_NATURAL_RUN`，不宣稱 unattended acceptance。 |
| 6 | P1，和第 4–5 項併同 | **Dashboard 真實循環呈現。** 將正式 report 接至已部署 Pages，採用 V0.2/V0.3 相容與固定 identity gate；更新狀態、來源與 freshness 欄位。 | Pages build/deploy 成功，desktop/mobile production browser 都讀到 exact report identity；NO_TRADE、資料不足、review、未啟用各有明確原因，未知值顯示 UNKNOWN。 |
| 7 | P1，最終收尾 | **安全、issue 與文件收斂。** 最小 workflow permissions、secrets-only、端點 allowlist、預算 gate 順序、全部 repository writers、並行和恢復測試；檢查 #224/#111 和所有未結 issue，更新主狀態/README/runbook/operations。 | 確認沒有 stale current-state claim、重複 ticket、舊 PR 被冒充 open；所有 claim 指向 exact immutable run/PR/main SHA。外部 writer unknown 明確保留，不做完整性推論。 |
| 8 | P2，不阻塞主線 | **小批型別技債。** 僅根據最新 diagnostics 選不改行為的一般 cleanup；最多兩批、每批最多兩個來源檔。 | 新舊行為回歸通過、diagnostics 真下降、不用 Any/ignore/關檢查；不合適就記錄 deferred，不湊改動。 |

## 五、測試與交付矩陣

雲端 CI 必須驗證以下類別；既有合格測試沿用，不重建重複 harness：

- 可合格測試 fixture：候選→資格→風控→portfolio→paper entry/exit→account advance→immutable persistence→下一 slot。
- 正常拒絕：空 registry、Core100 REJECT、regime unavailable、資料過期/不連續/未收盤、holdout 邊界、超限及 source 失效；不得建立新倉。
- 重播與競爭：完全相同 slot/read request 不重複寫入；不同 usage report 不可 settlement replay；共享 reservation 和 slot claim 原子化。
- 時間/用量：UTC 日切、admission 後證據過期、usage evidence 不匹配、request headroom、R2 8 GB hard stop、D1 rows/storage budget 耗盡。
- 部分寫入/恢復：保留不可變證據、reservation 不錯誤釋放、latest pointer 只在最後寫、重啟不重複成交。
- 工作流安全：schedule/dispatch 分離、permissions 最小化、secret 不輸出、外部呼叫前完成 gate；等待 platform approval 的 checks 標為 waiting，不當作成功。
- CI 使用現行 Python 3.12/3.13、Ruff、治理/freeze guard、適用 workflow static、CodeQL、Dependency/SBOM。每個 PR 和 main push 的 evidence 分開記錄；Pages browser 只在真的 deploy 後判成功。

## 六、固定界線

- `CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER`；不讀寫本機 repository、不用本機終端機或本機排程。
- Cloud/runtime 每月預算固定 `0 USD`；不升級付費方案、不新增付款方式。若免費額度、headroom、實際計費或資料 freshness 無法證明，就保持停用。
- PAPER / LIVE-PAPER ONLY。真實下單、live trading、private exchange account/order API 關閉。
- Replacement holdout 保持 `FROZEN_UNOPENED`；source switch=false；promotion=false。Core100 仍 `REJECT`，threshold 不因小目標改變。
- R2/Cloudflare Billing、Cloud Usage V0.1/V0.2/V0.3 和一次性 bootstrap 等已消耗 authority 不 rerun；不得改寫 frozen receipts 或歷史測試證據。
- 不跨來源冒充 provenance；不降低資格/風控門檻、不湊 trades、不增加 leverage、不用人工資料填補未驗證市場指標。
- 版本 authority merge main 前，不呼叫新增 Cloudflare API、不 provision/migrate D1、不寫生產 R2、不啟用 PAPER runtime/schedule。

## 七、最終結案交付

只有在以下證據齊全後，才能標為「雲端模擬循環已完成」：

1. live main 的目標和狀態入口一致、必要 CI 全綠。
2. 0 USD 的帳戶使用、免費額度、所有已知 writers、可用容量與 freshness 有可審核證據；啟用所需的每一項 UNKNOWN 已被證據消除；若只能安全不啟用，應列受阻，不算完整循環完成。
3. versioned budget/persistence authority 及實際 workflow 的外部 I/O 順序一致。
4. controlled main PAPER acceptance 與最少一個可追溯正式結果；不合格時可驗證地零倉/不交易。
5. 若要宣稱自動運作，首個自然 schedule run 的輸入、slot、報告、狀態回讀均成立；否則只可稱「已配置、待首次自然觸發」。
6. Dashboard production build/deploy/browser 顯示該正式結果。
7. 清楚報告策略品質仍為 REJECT、研究/實盤權限仍關閉；不宣稱獲利或策略有效。

在以上未齊前，專案狀態為 `IMPLEMENTATION_IN_PROGRESS` 或明確 blocker，不宣稱完成。

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
