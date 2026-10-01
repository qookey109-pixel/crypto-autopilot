# Cloud Paper 市場資料來源評估 V0.2 — CoinMarketCap Keyless

查核基準：GitHub `main=fec65f685b30b17b2d9662d27775837d4e32f094`（2026-10-01）。本文件是 V0.1 的後續候選評估；V0.1、frozen receipt 與既有 market/request contracts 不修改。

本次只讀 GitHub Repository 與 CoinMarketCap 官方 API 文件／條款；沒有呼叫行情端點、建立帳戶或 API key、讀取 Cloudflare、R2 或 D1。文件不授予 provider fetch、資料保存、source switch、預算、排程或交易權限。

## 結論

**CoinMarketCap Keyless 可列為全球行情欄位的技術候選，但目前不能核准進入 Cloud Paper。**

理由：

1. 官方文件列出 Keyless `GET /v1/global-metrics/quotes/latest`，不需 key，並標示約每 5 分鐘更新；但請求共用 IP rate pool，官方沒有在此 keyless 文件提供可用來證明專案上限的固定日／月配額。它不能作為可預算的 0 USD 生產服務保證。
2. 回應中的 `altcoin_market_cap` 定義為排除 Bitcoin 的市值，並非專案所需的排除 BTC 與 ETH 的 TOTAL3。不得直接將其重命名成 TOTAL3。
3. 回應包含 `total_market_cap`、`btc_dominance`、`eth_dominance` 與 quote-level `last_updated`；理論上可研究由總市值與雙 dominance 推導 ex-BTC/ETH 市值，但目前官方 schema 未證明 dominance 與 quote 市值使用同一資料時間、同一資產母體及可接受的指標方法。因此不得把推導結果當成已驗證 TOTAL3。
4. Keyless 的無帳戶呼叫與官方 API 使用條款之間，尚未確認適用哪一組 license。CMC 個人條款限制非 caching 的資料儲存以及向第三方提供或彙整內容；商業條款則將資料使用限定在符合條款的產品及授權範圍。這些條款是否允許本專案把來源值、摘要或衍生值保存作決策／重播證據，需先取得適用性與保留方式的明確確認，不能自行作法律推定。
5. 目前沒有來源請求、回應、coverage、timestamp、freshness、完整性、條款適用或實際用量的專案證據。

## 欄位與來源判定

| 需求 | CMC Keyless 欄位 | 本次判定 | 尚缺證據 |
|---|---|---|---|
| BTC dominance | `btc_dominance` | 技術上有欄位；未核准 | 專案可用性、時間語義、使用條款、保存權及 refresh/rate cap |
| ETH dominance | `eth_dominance` | 技術上有欄位；未核准 | 同上；需與其他 quote 欄位做時間對齊 |
| TOTAL3（排除 BTC、ETH） | `altcoin_market_cap` | **不符合定義**；該欄位只排除 BTC | 不得直接採用 |
| 推導 ex-BTC/ETH 市值 | `total_market_cap` + 雙 dominance | 待研究，非已驗證 TOTAL3 | 同一時間點、同一資產母體、精度、資料時間、CMC 方法及保存條款 |
| Request allowance | Keyless shared IP pool | 未知 | 固定 numeric limit、錯誤行為、專案可取得的 headroom；遇 429 必須停止，不得重試繞過 |
| 原始／衍生資料保存 | Keyless response | 未核准 | 適用 license、必要 cache 範圍與期限、衍生證據保存權、刪除要求 |

## 用量核算提醒

如果每個 15 分鐘 slot 都呼叫一次 macro endpoint，設計頻率將是 96 次／日、約 2,880 次／30 日。這只是本專案假設下的呼叫算術，不是 CMC Keyless 配額或服務承諾；該路徑的共用 IP 限流沒有提供可供本專案鎖定的固定額度。

降低呼叫次數必須先有 freshness 規則與可恢復快取契約。跨 runner 持久化快取涉及額外 R2／D1 存取和資料保存權，不因「只快取」而自動授權。未具備可信來源時間、可用 budget hook 及合法保存方式時，該欄位仍應為 `UNKNOWN/UNAVAILABLE`，策略應 fail closed。

## 後續驗證門檻

在任何真實請求之前，需另外完成並核准一份 successor authority，至少包括：

- **條款：** 確認 Keyless endpoint 適用的條款、個人非商業用途、 attribution、暫存與決策證據保留限制；如有不確定，向 CMC 取得可保存的書面答覆。
- **語義：** 用固定離線 schema fixture 驗證資料欄位、百分比單位、quote 資料時間與 dominance 時間一致性。不得以 live fetch 代替條款／預算核准。
- **TOTAL3：** 僅在官方定義確認資產母體和時間一致後，才評估以 total cap 與 BTC/ETH dominance 推導；先將它標示為來源衍生指標，不能偽稱原生 TOTAL3。
- **預算：** 得到能由本專案遵守的 request 上限或核准可控的 keyless／keyed方案；把單輪、每日、rolling 30-day、429、runner 重複與其他共享 IP 使用一併計算。不能只靠 no-key 推定零費用。
- **證據保存：** 僅保存獲條款允許、且支援必要決策與恢復的最小內容；如果只能暫存而不能留存，便不可用於依賴持久證據的正式交易循環。
- **合法擷取：** 不以 HTML/browser scraping 規避 Keyless rate limit、登入要求或條款；若改評估網頁來源，需個別確認其條款、robots、頻率與自動化許可。
- **驗證流程：** 先用 GitHub CI 合成 fixture 驗證缺欄、錯時間、過期、429/錯誤、超額、來源中斷與 fail-closed。任何真實 endpoint 請求仍須獨立 authority，不能由本文件或 CI 推得。

若任一門檻無法證明，保持 CMC 欄位不可用；繼續評估其他官方且合規的來源，不放寬 regime、策略資格、風控或來源隔離。

## 固定界線

正式 Cloud Paper、provider access、Cloudflare／R2／D1、cache、schedule、source switch、策略變更與任何真實交易操作均未獲本文件授權。0 USD、PAPER／LIVE-PAPER ONLY、holdout closed、Core100 `REJECT` 持續有效。不要 rerun 已消耗的一次性稽核或為取得自然排程證據補 dispatch。

## 官方來源

- [CMC Global Metrics endpoint](https://coinmarketcap.com/api/documentation/pro-api-reference/global-metrics) — endpoint、欄位描述與更新頻率。
- [CMC Keyless Public API](https://coinmarketcap.com/api/documentation/pro-api-reference/keyless-public-api) — no-key supported route 及共享 IP pool。
- [CMC response schemas](https://coinmarketcap.com/api/documentation/pro-api-reference/~schemas) — global metrics / quote 欄位結構與定義。
- [CMC Personal API Terms](https://pro.coinmarketcap.com/user-agreement-personal/) — 個人條款與資料使用限制。
- [CMC Commercial API Terms](https://pro.coinmarketcap.com/user-agreement-commercial/) — 商業 API 授權範圍。

**狀態：** `ASSESSMENT_ONLY / NOT_APPROVED / NO_EXTERNAL_ACCESS_PERFORMED`.
