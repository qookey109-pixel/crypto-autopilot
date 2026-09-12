# Qookey Crypto Autopilot — 2026-09-12 最新交接

核對時間：2026-09-12 18:40（Asia/Taipei；10:40 UTC）。
此文件是當次審查快照，不是額外執行權限。後續先重新讀 GitHub main。

## 專案與正式狀態

- Repository：[qookey109-pixel/crypto-autopilot](https://github.com/qookey109-pixel/crypto-autopilot)
- 網站：[Research Space](https://qookey109-pixel.github.io/crypto-autopilot/)
- 本次核實 main：`2ff32d55fbcddd54053c1338467e835b11a7c5a8`（PR #284）。
- main [CI 34686556594](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34686556594)：PASS。
- main [Pages 34686556593](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34686556593)：PASS；審查時線上首頁仍顯示 7/10。
- 完整研究池：**NOT_READY**。
- 固定 BTC 27 天模擬：**BTC_FIXED_SAMPLE_READY**；只驗證該樣本的引擎流程。
- PAPER-ONLY / FREE-ONLY；每月 runtime 預算 0 USD。
- 本次更新位於 `codex/data-schedule-handoff-20260912`，須 PR、CI、exact-SHA 核准後合併。尚未合併前，不宣稱線上網站已更新。

## 資料整理

| 類別 | 已核對結果 | 限制／下一步 |
| --- | --- | --- |
| Pionex BTC 樣本 | 2026-08-01 至 08-28 exclusive；15M 2592、60M 648、4H 162 rows | 僅固定 27 天；非全歷史 |
| Pionex BTC Funding | 81 observations；run 34563641025 | 僅固定 BTC 期間 |
| 固定 BTC 模擬 | run 34615465566；28 plans、15 成交、13 rejected；正式 receipt PASS | V0.1 已退役，不能再自動重跑；不證明泛化 |
| Pionex 候選池 | run 34563615657：197 個候選，含 Crypto Core 100 | 候選選取不是歷史完成；分類仍待核實 |
| Pionex Historical Reach | run 34563589773：FAIL | 工程修正後無新正式 execution evidence；不能宣稱 provider earliest |
| Binance Core 100 | 最新 run 34680188351：8/10；分片 4 品質拒絕 | CTK 2025-04 15m 缺 41；LIT 2025-12 15m 缺 70 仍未解除 |
| BNX 修復 | run 34677544161；shard 3 正式發布且 receipt/hash 已凍結於 main | 15m/1h/4h bundle 修復通過；不是全池完成 |
| CTK V0.3 | run 34687012733：三週期缺口形狀已描述 | 不代表修復、不代表已證明 relaunch；exception 尚未授權 |
| V0.12 metadata | 視窗已於 9/12 12:00 臺灣時間結束 | 兩個缺失時槽不可回補，完整 194-slot PASS 不可達 |
| Context Forward | 9/12 12:00 至 9/19 12:00 前，一次人工限定採集 authority | 本次最新 main 人工 run 查詢未見執行；4 小時 cron 尚未授權 |

BTC 財務摘要依正式固定樣本 receipt：net PnL 1.65797823 USD、
max drawdown 4.9329167%、fees 2.56775057 USD、funding 0.08082691 USD。
這些是歷史固定樣本結果，不能當每日推薦或未來獲利承諾。
該次 kill switch 未設定／未觸發；不能說該 run 已驗證 kill-switch 觸發路徑。
最大持有 720 分鐘曾觸發 3 次。歷史報告保持原樣。

## CTK 證據差異：REVIEW_REQUIRED

實際重新下載 artifact `10295164694`（992 bytes），ZIP SHA-256 與 GitHub digest 一致：

- ZIP：`f143781a10711cd02be2f082b9795d78baa89bd210a1853339a6d2240c1630dd`
- report.json（2853 bytes）：`ae2169273e7aadd9d5b645c3095a19c1ce66d24a12a48a704ca8caad5f2d5cdc`

舊 Handoff 的 ZIP `d2c4547d…`、report `fa32c264…` 與下載內容不一致。
本次保留原敘述於新 evidence 的 discrepancy 欄位；不修改舊 Handoff 或歷史 FAIL。

三個缺口均在 **2025-04-30**：
15m 00:00–10:15（41 根）、1h 00:00–10:00（10 根）、4h 00:00–08:00（2 根）。
各為一個內部缺口，沒有 duplicate／misalignment／invalid candle timestamp。
此為 archive shape 證據；成因仍需來源佐證，不能直接宣告 contract relaunch 已證實。
不得 forward fill、插值或製造假 K 線；generic gap validation 仍 fail closed。

新增證據：

- `research/receipts/2026-09-12-ctk-lifecycle-v0-3-run-34687012733-evidence.json`
- `research/receipts/2026-09-12-ctk-lifecycle-v0-3-run-34687012733-report.json`
- `research/receipts/2026-09-12-history-run-34680188351-log-observation.json`

歷史進度來源是 GitHub job log 的 aggregate report extract，沒有冒充原 artifact bytes 或 R2 readback。

## 雲端排程（Asia/Taipei）

| 作業 | 正式觸發 | 最新觀察與依賴 |
| --- | --- | --- |
| Core 100 歷史補齊 | 每兩小時，偶數小時 :23；至 10/1 08:00 前 | serialized，一次一分片；run 34680188351 仍因 CTK FAIL |
| Core 100 訓練 | 每週日 12:37 | 完整資料才訓練；下一次預定 9/13，若仍 8/10 不等於可訓練 |
| Research Signal V0.2 | 每日 10:17 | run 34680106835 success；不代表策略有效 |
| Signal Quality V0.1 | 每日 10:47 | run 34680519803 success |
| Automation Health V0.2 | 每兩小時，偶數小時 :57 | run 34674926711 failure，原因為歷史 quality rejection；監測正常告警 |
| Pionex Alternative Assets | 9/13、9/20、9/27 11:53 | 商品 metadata／分類候選觀測，不是 K 線補齊 |
| V0.12 metadata | 視窗已結束 | run 34673261420 success，但 capture job skipped；不算 capture PASS |
| Dashboard | main 相關變更與已列入的 cloud workflow 完成後 | metadata 刷新與資料完成數分開；完成數由已核對 evidence 投影 |
| BTC fixed simulation V0.1 | 已退役；僅 PR regression | 已保留 PASS；不恢復成功 main CI 後自動重跑 |
| Universe / Funding / Reach / classification / Context Forward | 各自正式 authority 下的人工限定流程 | 不建立第二套排程，不把手動流程寫成已自動執行 |
| Codex `crypto` 追蹤 | 本次讀到 **PAUSED**，原設定每小時 | 是本機應用程式追蹤，非專案 GitHub runtime；沒有自行恢復 |

GitHub cron 是預定觸發時間，不保證準點。七份 workflow 檔仍含 cron，其中 V0.12 已到期；
「七份 cron 設定存在」不能寫成七個工作都仍可執行。
實際 observed run 間隔有延遲；既有 FREE-ONLY gate、128 attempts 與 330 分鐘上限維持。
原始不可變 receipt 若記載六小時，是被 cadence V0.1 附錄取代的歷史記錄。

### 排程優化判斷

這次先修正排程說明與網站證據來源，不增加 provider/R2 請求頻率。
歷史 run 現在在幾分鐘內因確定缺口失敗；加密 cron 只會更快消耗 attempts，無法補出不存在的資料。
先解決 CTK／LIT 准入與分段語義，再評估 run budget 是否需另立版本。
完整訓練是 weekly；若資料在 9/13 的觸發後才完成，下個週期為 9/20，會超過 9/15。
資料完成後應核對現有 manual training 的 authority／參數與成本，再決定是否人工觸發；本次沒有觸發。

## 本次修正與驗證範圍

1. 同步 PROJECT_STATUS、README、Automation Index 與最新 readiness index。
2. 將首頁簡化為 BTC 模擬、8/10 分片、197 候選、81 Funding 四項。
3. Homepage／history-progress 由 `scripts/build_delivery_overview.py` 從同一份 index 與 receipts 產生；
   count、來源、provider、交易邊界與 CTK report hash 不一致時 build 失敗。
4. 明確顯示 V0.12 到期／capture skipped，以及 BTC fixed sample 已完成退役。
5. 補充離線 regression tests；PR CI 與 Pages build 驗證後才請 exact-SHA merge。
6. 沒有更改 production 資料、provider 呼叫、R2、holdout、真實訂單、frozen 品質閾值或既有 runtime cron。
7. 原本本機 dirty tree 保留；使用獨立 clone 準備交付。

## 9/15 能否完成

**完整研究池 NOT_READY，無法依目前證據保證 9/15 全部完成。**
固定 BTC Paper / Simulation 已有正式完成證據，這部分不用重做。
剩餘 P0：CTK／LIT 資料品質、Pionex 完整範圍與分類／實體化、完整策略訓練與 evaluation evidence。
P1：手動階段的雲端接續、weekly training 時程、到期 metadata 路線的 successor 決策。
網站與文件可在本次 PR 合併後更新；這不會自行使完整模擬變成 READY。

## 下一個最小 bounded task

完成 CTK 資料缺口成因的**唯讀證據核對**，以本次核實 report hashes 為起點。
若來源支持 exact lifecycle exception，再準備版本化提案與 training segmentation tests：
wrong symbol／timeframe／timestamp／額外缺口都拒絕，
rolling windows／returns／labels 不跨 segment。
新 exception 必須經 exact-SHA PR 合併成正式 authority 後，才可供 production materializer 使用。
若缺乏成因證據，保留 CTK FAIL，不放寬 generic gate。

人工流程精確連結：

- [Pionex Reach](https://github.com/qookey109-pixel/crypto-autopilot/actions/workflows/pionex-historical-reach-v0-3.yml)
- [Pionex 分類](https://github.com/qookey109-pixel/crypto-autopilot/actions/workflows/pionex-asset-classification-execution-v0-1.yml)
- [Context Forward](https://github.com/qookey109-pixel/crypto-autopilot/actions/workflows/context-forward-capture-execution-v0-1.yml)
- [Core 100 training](https://github.com/qookey109-pixel/crypto-autopilot/actions/workflows/binance-usdm-detailed-training-v0-1.yml)

這些是入口，不代表本次已啟動。每次先查最新 authority、有效期、既有成功次數，再決定是否可執行。

## 新聊天接續提示詞

繼續 qookey109-pixel/crypto-autopilot。先讀最新 GitHub main、
PROJECT_STATUS.md、README.md、docs/OPERATIONS_HANDOFF_2026_09_12.md、
research/status/simulation-readiness-v0-1.json 與對應 receipts。
先查 codex/data-schedule-handoff-20260912 的 PR、exact head/base、CI 與合併狀態，避免重做。
當次核對基準 main 2ff32d55fbcddd54053c1338467e835b11a7c5a8；
BTC fixed sample 已 READY 並退役，Core 100 最後核實 8/10，BNX bundle 已正式發布。
CTK V0.3 僅 shape characterized，舊 Handoff hashes 與本次下載不同，應以可核實 artifact 證據核對。
先做 CTK 成因唯讀核對，再準備 exact exception / training segmentation 的版本化提案。
不要自動 merge、恢復 BTC fixed workflow、加第二套排程或把工作成功當資料完成。
保留歷史 FAIL；PAPER-ONLY / FREE-ONLY、不讀 holdout、不讀 secrets、不存取未授權 R2、
不做 provider relabel/source switch/live trading。完成後給 exact-SHA PR gate 和更新 Handoff。
