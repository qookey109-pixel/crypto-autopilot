# Cloud Paper 市場資料來源與預算缺口評估 V0.1

查核基準：GitHub main `e2324b8bccf2b1bb9b767ec408aa254db9b247e9`（2026-10-01）。

本文件是來源與工程範圍評估，不是 provider-fetch、R2/D1、source-switch、策略、排程或交易授權。查核只讀 Repository 與官方文件，沒有呼叫市場資料端點、建立 API key 或讀取雲端用量。

## 已確認的產品需求與現況

- `config/strategy_v0_1.json` 指定 market context `4H`、setup `60M`、entry `15M`。
- `config/market_regime_breadth_research_v0_1.json` 需要同一明確行情來源的 BTC/ETH 收盤價、TOTAL3、BTC dominance，以及固定成員、等權重、時間對齊的 breadth；任何 member 缺 bar 都要讓該 regime 不可用。
- 固定 Pionex breadth 候選有 23 個永續市場；完整 partition、時間格線與 freshness 尚未驗證。正式策略 registry 仍空，Core100 品質為 `REJECT`。
- `src/crypto_autopilot/paper/cloud_market_v0_1.py` 目前最多選 5 個市場，每市場只取 240 根 `60M` K 線。未接入 4H／15M capture，亦不會把 Pionex 價格冒稱 TOTAL3 或 BTC dominance。
- 既有 Cloud Paper 操作契約的單輪上限是 18 次請求（3 次 universe/market calls、5 次 hourly candle、10 次 execution-frame requests）。這不證明 endpoint 配額，也不是已核實的帳戶預算。

## Pionex 官方公開 Klines 適配性

官方 Klines 文件列出 `15M`、`60M`、`4H`、`1D` 等 interval；每次請求 weight 為 1，`limit` 範圍 1–500，`endTime` 可用來界定查詢終點。該 API 基本資訊將簽章憑證要求限定於 PRIVATE requests，故公開行情候選不需要使用者提供交易 API key。這些文件只證明端點與參數受支援；本 Repository 尚未以實際端點回應證明可用性、完整性、延遲或涵蓋範圍。

來源：
- [Pionex Get Klines](https://pionex-doc.gitbook.io/apidocs/restful/markets/get-klines)
- [Pionex Basic Info / private request authentication](https://pionex-doc.gitbook.io/apidocs/restful/general/basic)

### 請求量差額

若正式循環每 15 分鐘執行一次、每輪選 5 個候選，且要取得：

- 固定 23 市場的 4H regime/breadth；
- 5 個候選各自的 60M setup 與 15M entry；
- symbols、tickers、book tickers 三項共用市場資料；
- 每個 open position 的 order book 與 recent trades execution frame（最多 5 個 positions、每個 2 次 public requests）；

行情與候選輸入需 `23 + 5 + 5 + 3 = 36` 次請求／輪；這還沒包含現有 Live-Paper feed 對每個 open position 讀 order book 與 recent trades 的兩次請求。依既有最多五個 positions 的預算包絡，完整上界為 `36 + 2 × 5 = 46` 次／輪，按 96 輪／日為 4,416 次／日、132,480 次／rolling 30 days。這是設計上界，不是實際用量或 provider 免費配額；若未來新增 macro provider，其請求也尚未計入。

即使 4H breadth 只在每根新 4H 收盤後更新，也需要定義快取／持久化與新鮮度、runner 中斷恢復及同輪 request burst。舊值不得被當作新行情；不得因預算不合而漏掉 breadth 成員、跨來源補值或降低策略門檻。必須先產生新的 bounded request contract，逐端點標示每輪／每日／月度最大次數、資料時間、重試上限及 budget hook，再談 runtime wiring。

## 全球市場指標候選：CoinGecko Demo

CoinGecko 官方 pricing 頁目前列 Demo 為零費用、10,000 calls/month、100 calls/min、資料新鮮度標示 from 60 sec、需 attribution。這只能說明公布的方案上限，不能證明專案已註冊、實際剩餘 credits、可商用範圍或允許持久化。

官方 API Terms 指出：
- 使用範圍依選定 plan 與條款而定；
- 使用需標示 attribution；
- 不得超出或規避呼叫限制；
- Data caching/storage 受到限制，且條款限制複製、儲存、衍生或翻譯 Data，包括 hashed/derived information，除非另有明確允許；
- 停止 API 使用時有刪除已取得資料的要求。

這與本專案要保存決策輸入來源、時間、摘要及可恢復證據存在明顯衝突風險。因此 Demo 暫列為「技術候選、使用條款未核准」，不得納入正式循環、Dashboard、雜湊收據或任何排程，除非先取得可留存的書面條款確認，並完成資料保留／刪除、對外 attribution 與零費用方案審查。不能只以低於 10,000 calls 推定合法可用或長期零成本。

來源：
- [CoinGecko API pricing](https://www.coingecko.com/en/api/pricing)
- [CoinGecko API Terms of Service](https://www.coingecko.com/en/api_terms)

## HTML / 瀏覽器擷取與 AI Resource Hub

可從 AI Resource Hub 評估 Scrapling、Playwright 等工具的工程做法；資源目錄本身不是行情 provider、授權或免費用量證明。擷取公開頁面也不能繞過登入、反機器人限制、rate limit、服務條款或資料授權。若考慮任一網頁來源，先確認公開 URL、允許的自動化用途、robots/條款、更新與時間欄位、引用標示、完整性、request cap 及 parser 版本。未確認前標為 `UNVERIFIED`，不得接入 fallback。

## 目前逐欄分類

| 欄位／輸入 | 候選來源 | 狀態 | 阻擋 |
|---|---|---|---|
| Pionex BTC/ETH、candidate candles 60M | Pionex public Klines | 端點文件支援；本專案限量 60M adapter 已有程式 | 實際 capture 尚未授權／驗收；無正式來源回讀證據 |
| 4H market context | Pionex public Klines | 文件支援 | 目前 adapter 未接入 |
| 15M entry | Pionex public Klines | 文件支援 | 目前 adapter 未接入 |
| 23 市場 4H breadth | Pionex public Klines | 端點候選 | 固定成員 coverage、連續 bar、對齊及 request budget 未驗證 |
| TOTAL3 | CoinGecko/global aggregate 或其他 provider | 未核准／未驗證 | 定義、同時間點方法、授權與保存限制 |
| BTC dominance | CoinGecko/global aggregate 或其他 provider | 未核准／未驗證 | 定義、資料 freshness、條款與保存限制 |
| funding、open interest、derivative index | Pionex public endpoints | client 有相關部分方法 | 目前目標策略必要欄位尚未逐項確認；不可視為 macro 指標替代品 |
| HTML scraped fields | 待選來源 | 未驗證 | 條款、parser、更新、欄位語義與速率上限 |

## 建議依序處理

1. 先維持正式 Cloud Paper 停用。不要增加 GitHub secrets、provider fallback 或 schedule。
2. 定義 market-input successor contract：來源、欄位、4H/60M/15M 時間格線、暖機數量、固定 breadth 成員、request 上限與每次請求前的 budget callback。
3. 將 36 requests/slot 的初始上界與可能的 4H 快取策略交由零費用預算核算；涵蓋其他 writers、每日/月度 provider cap、R2/D1 寫讀、重試與 readback。若可行性無法證明就保持停用。
4. 只用固定合成 fixtures 在 GitHub CI 驗證完整／缺漏／過期／錯格／重複行情及 budget stop；不為測試呼叫真實 provider。
5. 對 TOTAL3/BTC dominance 先完成來源與條款審查。CoinGecko Demo 在 hash、保存與 attribution 限制未釐清前不可採用。網頁擷取須另做來源條款審核。
6. 新版程式與 authority 合併至 main 後，才依新 authority 執行一筆有上限的受控 PAPER 驗收；自然 schedule 證據另外記錄，不用手動 run 代替。

本評估沒有修改策略資格、權重、風控、frozen evidence、provider authority、source switch、Cloud Paper activation 或排程。

**當前結論：** Pionex 可支援所需 K 線週期，但現行 adapter 與 18-request contract 還不能同時滿足固定 breadth 加候選多週期；全球 macro 欄位仍無可核准來源。先處理 request budget 與條款／來源判定，之後才能安全接線。

## 2026-10-01 official rate-limit clarification

Pionex's [official rate-limit documentation](https://pionex-doc.gitbook.io/apidocs/restful/general/rate-limit) states a maximum of 10 requests per second per IP across endpoints. Treat this as a published burst-rate ceiling, not as an aggregate daily/monthly allowance, a zero-cost guarantee, or authorization to fetch. Shared endpoint weights, complete breadth availability, quota/allowance beyond the rate limit, and account-wide use remain unknown. Any future authorized client must serialize and pace requests below the published ceiling, stop on HTTP 429, and must not automatically retry. The existing 18 requests/run and 1,728/day authority is unchanged; this correction does not authorize any external request.
