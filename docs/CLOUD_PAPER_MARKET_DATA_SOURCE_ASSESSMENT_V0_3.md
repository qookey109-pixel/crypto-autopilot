# Cloud Paper 市場資料來源評估 V0.3

查核時間：2026-10-01 17:35 Asia/Taipei  
Repository evidence basis：main `e5f4004b65b8ba43616d64a4cd5c56f9259928f8`  
評估範圍：補充 V0.1／V0.2 的全球市場欄位來源審查。只查 Repository 與來源官方文件；沒有呼叫市場資料端點、建立 API key、讀取 Cloudflare 用量或修改任何執行權限。

## 結論

**目前沒有合格且已核准的來源可供 Cloud Paper 使用 TOTAL3、BTC dominance 與 breadth。正式流程維持 `REGIME_UNAVAILABLE` 並 fail closed。**

本文件是來源資格評估，不是 provider-fetch、source-switch、R2/D1、預算、策略、排程、Cloud Paper activation 或交易授權。來源被列為候選，不代表允許接入。

## 欄位定義與現況

| 欄位 | 所需語意 | 已核對來源 | 狀態與缺口 |
|---|---|---|---|
| TOTAL3 | 按研究契約排除 BTC 與 ETH 的總市值；必須定義資產範圍、計價幣別與同一時間基準 | Pionex public market endpoints；CoinGecko；CoinPaprika | Pionex 個別交易市場不能代表全球市值。CoinGecko／CoinPaprika 的全球快照文件未證明提供同一契約定義的 BTC+ETH 排除值。不可用 total cap 減去近似 BTC/ETH 數值冒充。**不可用** |
| BTC dominance | provider 定義的 BTC 市值占全球加密資產市值比例，附資料更新時間 | CoinPaprika `/v1/global` 文件列有 `bitcoin_dominance_percentage`；CoinGecko 全球市場資料候選 | CoinPaprika 欄位符合「BTC dominance」候選語意，但計算範圍、update timestamp 對齊、持續保存權與本專案來源授權未通過。CoinGecko Demo 對所需全球端點的方案資格未被目前官方 plan 資料明確證實，且保存條款未解。**候選、未核准** |
| Breadth | 固定 23 個合約成員、相同完成時間格線、等權重；不得缺成員或跨來源補值 | Pionex 23-member universe + public klines | Pionex 有所需週期的端點文件，但完整 member coverage、對齊、連續 bar、freshness、request budget 與 adapter 接線尚未驗證。全球匯總 API 不提供此固定合約的逐成員 Pionex-native breadth。**未驗證／不可用** |
| 4H regime bars | BTC/ETH 與 23 個 breadth 成員的已收盤 4H bar | Pionex Klines | 官方 API 文件列出 4H；正式 Cloud Paper adapter 目前只抓 60M。支援端點不等於已驗收的 capture。**尚未接入** |
| 60M setup bars | 候選市場已收盤 60M bar | Pionex Klines | adapter 目前支援此週期，但候選取樣／正式外部請求仍受 disabled runtime 與預算 gate 限制。**程式存在，正式未執行** |
| 15M entry bars | 候選市場已收盤 15M bar | Pionex Klines | 官方 API 文件列出 15M；Cloud Paper adapter 尚未接入。**尚未接入** |
| 持倉期間成交／退出證據 | 能完整覆蓋上一個已驗證狀態至本輪的 public trade tape，不能以最新報價推測中途停損 | Pionex recent trades | 既有 adapter 有 fail-closed 的 tape completeness guard；需要正式授權與受控回讀才能成為 production evidence。**尚未正式驗收** |

## 來源評估

### Pionex 公開市場端點

官方 Klines 文件列出 15M、60M、4H 週期。這只證明端點功能與參數存在；本專案尚未證明 23 成員完整覆蓋、同步格線、暖機數、錯過 slot／持倉期間恢復所需的資料完整性或正式請求成本。Pionex 公開交易行情也不會提供 TOTAL3／全球 BTC dominance。

不需要 Pionex 私有 API key 來補全球市場指標；私有帳戶權限不會改變 public market endpoint 的欄位範圍。

官方來源：
- [Pionex Klines](https://pionex-doc.gitbook.io/apidocs/restful/markets/get-klines)
- [Pionex API basic info](https://pionex-doc.gitbook.io/apidocs/restful/general/basic)

### CoinGecko Demo

官方 pricing 頁列出 Demo 為 $0、10,000 calls/month、100 calls/min、from-60-second freshness，且需 attribution。方案總端點數為 60+；目前 pricing 對照資料未能確定本專案所需的具體 Global Market Cap endpoint 是否包含於 Demo，因此不可把 plan 的總端點數當成端點可用證據。

CoinGecko API Terms 限制 Data 的 cache/storage、複製與衍生使用，並要求停止使用時刪除已保存的 Data；本專案的決策追溯與恢復要求可能需要保存來源依據及摘要。未取得可留存資料與衍生摘要的明確許可前，不能把它用於 Cloud Paper、decision receipt 或 Dashboard。免費 call credits 也不證明帳戶的實際剩餘量或零費用風險。

判定：`ASSESSMENT_ONLY / NOT_APPROVED`。

官方來源：
- [CoinGecko API pricing](https://www.coingecko.com/en/api/pricing)
- [CoinGecko API Terms of Service](https://www.coingecko.com/en/api_terms)
- [CoinGecko global market data documentation changelog](https://docs.coingecko.com/changelog/10122018)

### CoinPaprika Free API

官方 API 文件索引列出 `GET /global`；官方 pricing 頁列出 Free 為 $0/month、20,000 calls/month、約 2,000 assets 與非商業用途，且更新間隔最高約 10 分鐘。官方 API Terms 將 Free 授權限於個人及非商業用途，要求標示 “Powered by CoinPaprika”，並限制超出授權目的複製、修改、衍生或分發資料。

`/global` 文件候選包含 `market_cap_usd`、`volume_24h_usd`、`bitcoin_dominance_percentage`、加密貨幣數量及 `last_updated`。若假設每個 15 分鐘 slot 僅一次 global request，理論需求為 96 calls/day、2,880 calls/30 days；這只是算術上限，不包含其他 workflow、重試、價格或 breadth 請求，也不證明共享帳戶額度、帳務、資料授權或 request 可用性。現階段沒有呼叫 API，也沒有使用 API key。

該來源不直接提供本專案所需 TOTAL3 與固定 23-market Pionex breadth；透過額外 endpoint 衍生 TOTAL3 還需驗證欄位範圍、時間對齊、授權及預算。個人／非商業適用性及衍生資料保存範圍亦尚未完成專案審核。

判定：`PARTIAL_FIELD_CANDIDATE / NOT_APPROVED`。不得只因方案標示免費而新增來源、接入交易循環或建立外部存取排程。

官方來源：
- [CoinPaprika API documentation](https://api.coinpaprika.com/)
- [CoinPaprika API pricing](https://coinpaprika.com/api/pricing/)
- [CoinPaprika API Terms of Use](https://coinpaprika.com/api-terms-of-use/)

### HTML／瀏覽器擷取

API Resource Hub 中的 Scrapling、Playwright 等是擷取工具候選，不是資料授權或 provider。不得以爬蟲繞過登入、付費牆、反機器人、rate limit、robots 規則或使用條款。CoinPaprika 網站一般 Terms 禁止未授權的 scraping；不可因其另有 API 就把網站爬取視為 API 使用替代。

每個網頁來源需先取得公開 URL、明確自動化許可、欄位語意／時間、更新與完整性證據、保留權限、速率上限、parser 版本和停止規則。完成前狀態保持 `UNVERIFIED / NOT_APPROVED`；不建立 scraper、不讀取 live endpoint、不作 fallback。

來源：[CoinPaprika website Terms of Use](https://coinpaprika.com/terms-of-use/)。

## request budget 與最小保存

既有完整輸入設計上界為最多 46 requests/slot（23 個 breadth、5 個 60M、5 個 15M、3 個共用市場資料與最多 10 個持倉 execution-frame 請求），即 4,416/day、132,480/rolling 30 days；現有 Cloud Paper authority 是 18 requests/run。這是不同範圍的設計需求，不是 provider 額度或共享帳戶用量。不得藉由刪除 breadth 成員、降頻後仍宣稱原策略契約滿足，或加用其他 provider 冒充 Pionex-native。

即時行情可按需在記憶體使用；但正式決策若需要跨重啟追溯，仍需保存合法且必要的來源、時間、欄位／版本及最小決策證據。hash 不能讓未保存的內容重新可讀，也不能取代來源授權。模擬帳戶、持倉、成交／費用、slot claim、防重、恢復與必要 audit trail 仍必須持久化。不得因縮減行情物件而刪除 frozen 證據或失敗收據。

## 欄位狀態總表

| 輸入 | 當前分類 |
|---|---|
| Pionex crypto perpetual 60M candles | adapter 支援；正式外部取數未啟用 |
| Pionex 4H bars / 23-market breadth | 端點支援候選；adapter、完整性與預算未驗證 |
| Pionex 15M bars | 端點支援候選；adapter 未接入 |
| BTC dominance | CoinPaprika 欄位候選；CoinGecko Demo eligibility／保存權未確認；兩者均未核准 |
| TOTAL3 | 無符合研究契約且已核准來源 |
| 持倉期間成交 tape | fail-closed adapter guard 存在；尚無正式受控驗收 |
| HTML scrape | 無已核准來源與自動化權限 |
| CoinGecko／CoinPaprika 歷史序列 | 未核准作日常執行／決策證據持久化來源 |

## 下一步與停機條件

1. 維持 Cloud Paper `activation=false`、正式循環 `NOT_RUN`、自然 schedule `NOT_CONFIGURED`。
2. 完成提供 TOTAL3 且具有清楚授權、保存權、更新時間、免費上限與完整涵蓋的候選來源審查；目前沒有通過項目。
3. 以固定的 23-market membership 及 exact time grid，完成 Pionex 4H／60M／15M 歷史暖機、來源時間、新鮮度、持倉 tape completeness 的 contract 與 request budget；不可發真實請求直到另行版本化授權進入 main。
4. 先證明 Account-wide Cloudflare、provider quota、runner 與共享 writer usage 的新鮮度及零費用。若只能取得不完整或過時證據，維持停用。
5. 之後再分離工程合成 CI、正式 main 受控 PAPER acceptance 和首次自然 schedule evidence；任一項不可替代另一項。

## 固定邊界

CLOUD_ONLY / LOCAL_FILES_EXCLUDED_BY_USER；FREE-ONLY / 0 USD；PAPER / LIVE-PAPER ONLY。Holdout、source switch、model promotion、自動 promotion、真實下單與 live trading 維持關閉。一切消耗型一次性 authority 不重跑；frozen evidence 不修改。

V0.3 僅更新來源審查與欄位分類；不改程式、模型、strategy eligibility、budget authority、provider secret、frozen contract 或 execution/schedule configuration。
