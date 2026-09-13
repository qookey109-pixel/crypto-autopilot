# Qookey Crypto Autopilot — 資料、排程與網站交接

核對日期：2026-09-13；基準時間 23:04 Asia/Taipei（15:04 UTC）。
這是有日期的審查快照，不是執行授權；後續必須重新核對 GitHub main。

## 1. 專案資訊與結論

- Repository：[qookey109-pixel/crypto-autopilot](https://github.com/qookey109-pixel/crypto-autopilot)
- 網站：[Qookey](https://qookey109-pixel.github.io/crypto-autopilot/)
- 核實 main：`d775fbd2ad01834635b8f82391933ac7141e7408`，PR #292 合併。
- main [CI](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34762214321)、
  [Pages](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34762214329)、
  [Freeze Guard](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34762214349) 均 success。
- **完整研究池／完整模擬：NOT_READY。固定 BTC 樣本：READY，限引擎驗證。**
- 無法保證 9/15 全部完成。程式檢查成功不代表資料齊全、訓練完成或策略有效。
- 本次分支：`codex/operations-refresh-20260913`。網站修改須 PR、CI、
  使用者批准 exact head 後才能合併部署。本文件不表示已部署。

## 2. 資料分類

| 類別 | 目前證據 | 狀態與限制 |
| --- | --- | --- |
| 已正式完成：固定 BTC | [模擬 34615465566](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34615465566)；15 成交、13 rejected | 27 天固定樣本 PASS；V0.1 已退役，不重跑 |
| 已正式完成：BTC 原生樣本 | [34513815680](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34513815680)；15M 2592、60M 648、4H 162 rows | Pionex，2026-08-01 至 08-28 exclusive；不是全歷史 |
| 已正式完成：Funding | [34563641025](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34563641025)；81 observations | 僅固定 BTC 範圍，不是全候選池 Funding |
| 已正式完成：BNX bundle | [34677544161](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34677544161)；main 凍結 publication receipt/hash | shard 3 已發布；本次未讀 R2，沒有重新認證 R2 現況 |
| 部分完成：Core 100 | [34756244643](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34756244643)；8/10 | dataset IN_PROGRESS；失敗分片不算完成 |
| 已執行失敗：CVC 1h | 同上；2025-05，736 rows，1 gap，缺 8 根 | 跑在合併前 c7990a63；不是 PR #292 規則失效證據 |
| 已執行失敗：LIT 1h | [34739234352](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34739234352)；2025-12，727 rows，缺 17 根 | 新規則合併後 production 接受結果尚待核實 |
| 候選／診斷：Pionex pool | [34563615657](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34563615657)；197 個候選 | 不是 197 份已完成歷史；分類仍需正式證據 |
| 已執行失敗：Pionex Reach | [34563589773](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34563589773) FAIL | 不可推論 provider earliest；未見更新的 main dispatch |
| 觀測成功：替代資產 | [34747992983](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34747992983) success | metadata-only；不是股票／ETF／金屬 K 線完成 |
| 已準備／待限定執行 | 分類、Context Forward 的個別 versioned configs | 最新 main dispatch 清單未見新執行；不擴張成自動採集 |
| 未取得新執行 authority | 大規模 Pionex 歷史、持續 Paper successor、holdout | 不能靠候選池或網站自行放行 |

歷史 BTC net PnL 約 +1.65797823 USD、drawdown 約 4.93%；只屬固定樣本。
不可宣稱未來獲利、泛化有效或可實盤。固定樣本未觸發 kill switch，
不能以該 run 取代 kill-switch 故障路徑測試。

## 3. 缺口規則與不可重做事項

已存在 training segmentation、training 前品質／BNX lineage 再驗證，
不重做 PR #286、#289 的同類引擎。
目前 lifecycle policy 有七筆 exact archive allowance：

| Symbol／月份 | Interval | 缺根數 |
| --- | --- | --- |
| CTKUSDT／2025-04 | 15m、1h、4h | 41、10、2 |
| CVCUSDT／2025-05 | 15m、1h | 34、8 |
| LITUSDT／2025-12 | 15m、1h | 70、17 |

Config：`config/binance_usdm_lifecycle_gap_policy_v0_1.json`。
SHA-256：`863b3eda37c51f33343015cddbe05d0de3b6fd6d75ec8dcef13d190d2e026716`。
source 與 config 維持既有 exact-match 測試；本次未修改它們。
分類是 USER_AUTHORIZED_LIFECYCLE_GAP；causal_claim=NOT_ASSERTED。
保留 raw gaps，不補假 K 線，不放寬未知 4h 缺口；features/targets/context 不跨 segment。
七筆 allowance 已合併不等於七處正式資料已完成。舊 FAIL、舊 receipt、舊 Handoff 保留。

## 4. 後續排程（臺灣時間）

| 作業 | 現行排程／條件 | 本次核對 |
| --- | --- | --- |
| Core 100 History | 每兩小時，偶數小時 :23；9 月限定，10/1 08:00 到期 | serialized、每輪一 shard；最新 8/10，尚無 post-PR292 scheduled evidence |
| Core 100 Training | 每週日 12:37，complete-data gate 通過才訓練 | [34750015232](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34750015232) success 但 report=SKIPPED；下次 9/20 |
| Research Signal | 每日 10:17 | [34745384761](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34745384761) success |
| Signal Quality | 每日 10:47 | [34745789186](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34745789186) success |
| Automation Health | 每兩小時，偶數小時 :57 | [34756817356](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34756817356) failure；History FAILED、Training HEALTHY_CONDITIONAL |
| Pionex alternative assets | 9/20、9/27 11:53；9/13 已有 run | metadata-only，不是歷史補齊 |
| V0.12 metadata | 已於 9/12 12:00 結束 | EXPECTED_STOP；缺失時槽不可補寫、不可改成完整 PASS |
| Dashboard | main 指定路徑 push／列入監控的 workflow 完成 | 雲端更新 Actions metadata；完成數仍由 reviewed receipts/index 產生 |
| 固定 BTC Simulation V0.1 | 已退役，保留 regression | 不恢復成功 main CI 後自動重跑 |
| Reach／Universe／Funding／分類／Context Forward | 個別 authority 下的人工限定流程 | 本次未觸發，未新增 cron |
| Codex crypto 追蹤 | 已更新提示詞；保留 PAUSED 與每小時設定 | 每輪依最新 main 與最新 Handoff 核實，不綁定舊 PR；未恢復執行 |

GitHub Actions 的預定時間不是執行保證；最近 History 建立間隔約 3h54m、
6h36m、7h07m。不能從 created_at 精確推回是哪個 cron slot，也不能證明延遲的根因。
七份 workflow 保有 cron 宣告，其中 V0.12 已到期，不能說七項皆仍有效執行。

舊 Handoff 所稱「Core100 Run Watch」：這次可見的本機排程中未找到同名紀錄；
不能證實其他雲端／帳號上的追蹤存在或不存在，不把它寫成正在運作。
本機與雲端排程須分開；需要本機檔案的桌面排程依賴電腦及應用程式持續運行，
參考 [OpenAI 官方排程文件](https://learn.chatgpt.com/docs/automations?surface=app)。

## 5. 問題與優化排序

| 等級 | 問題 | 已做／下一步 |
| --- | --- | --- |
| P0／BLOCKED | 全池資料不完整，不能進完整模擬 | 等並核對新正式 History 報告；不是等 CI |
| P0／REVIEW_REQUIRED | Pionex Reach、分類、歷史實體化尚未完成 | 後續分開確認有效 authority 與限定執行 gate |
| P1／REVIEW_REQUIRED | 訓練下一輪在 9/20，超過 9/15 | 資料齊全後另審截止日前限定訓練 authority；目前不手動 trigger |
| P1／REVIEW_REQUIRED | History 實際執行間隔不規律 | 先檢查 run head、排隊與 production report；不盲目加密 cron 消耗 attempts |
| P1／BLOCKED | V0.12 完整 194-slot PASS 不可達 | 保留歷史失敗；若後續仍依賴它，正式提出 successor，不回填歷史 |
| P2／修正中 | 首頁仍指向舊 CTK 未授權說明／9/12 Handoff | 本次更新 generator、readiness index、狀態文件及新 Handoff |
| P2／已修正 | Codex 追蹤內容同步 | 已改為每輪重新解析最新 main／Handoff；保留暫停，不重複建立 |

本次排程優化是移除狀態誤導、揭露真正依賴與期限，沒有加快 production cron。
完整 9/15 達標不能保證；固定 BTC Paper 已完成，可保留為已驗證基線。

## 6. 本次網站修改與檢查

線上核對時已顯示 8/10，並非還停在 7/10；但仍顯示 9/12 舊 CTK 說明。
維持四張簡明卡片：BTC、Core100、Pionex 候選、Funding。
更新最後拒絕與新政策待核實文字，增加訓練 SKIPPED／9/20 風險及最新 Handoff 連結。
新增 policy hash／allowance count／禁止以 policy promotion 取代資料完成的投影測試。
網站只讀取衍生資料，沒有新增 broker、risk engine、資料 provider 或訂單接口。

本機離線驗證：797 個 unittest PASS；8 個 dashboard Node tests PASS；
dashboard static safety PASS；git diff --check PASS。
本機預覽另做首頁與展開明細互動驗證。PR CI 結果以交付時 exact-head checks 為準。
新版本尚未合併／部署，不宣稱線上已更新。

關鍵新增證據：

- `research/receipts/2026-09-13-history-run-34756244643-log-observation.json`
- `research/receipts/2026-09-13-operations-github-observation-v0-1.json`

這些是 GitHub metadata／無秘密日誌摘要，不冒充 artifact bytes digest 或 R2 readback。
沒有本輪 R2 用量／物件現況認證、Render 新 transport proof 或 provider 新診斷。
本機原始 dirty tree 保留；修改只在獨立 clone 準備。
PR #290 仍 OPEN，head `2ef43a7c4859fcb47a9bed984a58f75b2f87cf05`，
僅舊交接文件；本次不改、不合併，也不把它當 runtime authority。

## 7. 下一個最小 bounded task

本次 PR exact-head 核准及合併後，唯讀核對第一個跑在 PR #292 main 或合法
後繼 main 的 scheduled Core100 History（workflow ID 340899181）。
讀取 job／artifact／secret-free report，核對 head、shards_complete、
dataset status、CVC/LIT 1h 的 exact SHA／rows／gap。未知缺口仍拒絕。
若 10/10，必須有 complete manifest／receipts 的正式證據才標 COMPLETE。
若缺少可公開核實的 completion evidence，明確 BLOCKED，不自行進 R2。
不啟動、重跑 History／Training，不新增排程、不自行 merge。

## 8. 新聊天接續內容

繼續 qookey109-pixel/crypto-autopilot。先讀最新 GitHub main、
PROJECT_STATUS.md、README.md、docs/OPERATIONS_HANDOFF_2026_09_13.md、
research/status/simulation-readiness-v0-1.json 與對應 versioned authority。
上次 main d775fbd2ad01834635b8f82391933ac7141e7408；先查
codex/operations-refresh-20260913 的 PR 狀態、exact head 和 CI，避免重做。
Core100 最後 8/10；最新 History 34756244643 跑在 pre-PR292 c7990a63。
新政策七筆 exact allowances 已合併，但尚無 post-PR292 正式補齊結果。
BNX 發布與固定 BTC PASS 保留，不重新做；BTC execution 已退役。
Training 34750015232 實際 SKIPPED，下一次例行 9/20，不能保證 9/15 全池完成。
優先核對新 scheduled History 的 report／receipts，不以 CI／workflow success
替代完成，不預先放寬未觀察 4h gap。所有修改 branch→tests→PR→CI；
merge 需要使用者批准 exact current head。PAPER-ONLY／FREE-ONLY；
不讀 holdout／秘密／未授權 R2，不做 source switch、provider relabel、
synthetic/fill、model promotion、trade plan 或 live order。
