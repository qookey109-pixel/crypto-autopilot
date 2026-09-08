# 歷史回填恢復提案 V0.1

狀態：PROPOSED_NOT_AUTHORITY / EXECUTION_NOT_AUTHORIZED_BY_THIS_DOCUMENT

## 已核對證據（2026-09-08）

- 正式 repository：`qookey109-pixel/crypto-autopilot`。
- 本次遠端 main：`0a353c6ea56d322d81edb6580865b6daf85547fa`，PR #231 已合併；CI 與 V0.10 Freeze Guard 通過。
- 現行 config：`config/binance_usdm_detailed_history_v0_1_2.json`。
- 現行 receipt：`research/receipts/2026-08-29-binance-usdm-crypto-core-100-v0-1-2-authority.json`。
- 正式範圍為 100 個 Crypto 標的、10 個 shard；250 個標的是已被取代的 V0.1.1。
- 歷史工作流 run [34188345285](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34188345285)，job `101941110302`，使用 V0.1.2 config/receipt，於 2026-09-08T04:51:39Z 拋出資料品質錯誤。
- 已有日誌診斷：`BNXUSDT`、monthly `2022-08`、`15m`，2688 rows，1 gap，288 missing bars，misaligned=0，invalid_candle=0。
- 已核對 archive SHA-256：`a3351bdf83dad7f503fb5732c88c85253101954c47b0cdb6791a11d61b131543`。缺口涵蓋的精確時刻、官方原因與其他分區缺口尚未核對；288 根只代表 72 小時缺失間隔，不能推斷為停牌。
- `scripts/run_binance_detailed_history.py:733`–736 選取第一個未完成 shard；453 行的 future 失敗會中止物化。失敗未新增完成紀錄，所以不能宣稱下次自動轉往下一批。
- 現有批次完成率未知；本次未存取 R2 狀態或 provider K 線。

## 建議的最小恢復設計

保留現行 100 標的、分區計畫及所有資料品質門檻。新增版本化的「失敗批次紀錄與公平輪替」執行附錄，解決第一個失敗 shard 阻塞其餘批次的問題；這不會修復 BNX 缺口，也不會使資料集提早成為 COMPLETE。

1. 一次既有排程仍只嘗試一個 shard，維持六小時間隔、GitHub-hosted serialized runner、2026-10-01T00:00:00Z 到期與 FREE-ONLY 8 GB gate。
2. 以獨立、versioned namespace 記錄不可變 attempt receipt 及可驗證的游標。每筆綁定原 catalog SHA、config SHA、新執行附錄 SHA、run ID、shard index、結果與有限長度的 aggregate diagnostic。
3. 選擇未完成且尚未嘗試的最小 shard；全部未完成 shard 都嘗試過後，再按最久未嘗試排序，index 作同序決勝。有效失敗紀錄不能被當成完成紀錄。
4. 僅捕捉明確的 K 線完整性拒絕作為可紀錄的 shard 品質失敗。授權、時窗、R2 headroom、checksum、狀態綁定衝突及未分類錯誤維持全流程停止；不得吞掉所有 exception。
5. 品質失敗仍使該次 workflow 回傳非零，讓健康監控保留告警；其餘 shard 留待後續既有排程。失敗報告須明示 `dataset_complete=false`。
6. attempt receipt 寫入前重查 headroom，immutable exact-byte equality、SHA readback、游標最後更新。部分寫入或游標衝突必須停止並供人工檢視。
7. 所有 10 個原定 shard 都有有效 PASS receipt 才能標示 COMPLETE；任何缺口都會繼續阻擋資料集訓練。

原 R2 catalog、既有資料與完成狀態不重新建立、不覆蓋、不改標的身份。BNXUSDT 仍在原定資料集；排除、替換、插值、跨來源拼接或改範圍不包含在本提案。

## 具體交付與版本授權 gate

擬新增檔名（尚未建立、尚未生效）：

- `config/binance_usdm_history_recovery_v0_1.json`：綁定 V0.1.2 原 config 與 receipt，定義 attempt schema、namespace、輪替演算法、錯誤分類及原截止日。
- `research/receipts/2026-09-08-binance-usdm-history-recovery-v0-1-authority.json`：SHA 綁定上列 config 與原 catalog 綁定規則，明確授權新增 attempt metadata 的 R2 讀寫及輪替行為；執行前須經 protected-main 審查合併。
- `src/crypto_autopilot/history_recovery.py` 與對應 synthetic tests：純函式的 next-shard 選擇、狀態驗證及錯誤分類。
- 於目前 main 的 `scripts/run_binance_detailed_history.py` 接入附錄；沿用原 workflow，僅增加明確附錄參數，不能增加第二條排程。同步 PROJECT_STATUS 與相關驗證。

需在隔離的 main 基準實作；本機 `codex/research-context-v0-1` 包含舊版檔案與使用者 dirty changes，不可直接以該 checkout 覆蓋遠端版本。

## 驗收條件

- Synthetic 三批案例：batch 0 品質失敗後選 batch 1；batch 1 PASS 後選 batch 2；batch 2 PASS 後再選 batch 0，總完成數一直是 2/3。
- 全部失敗時公平輪替；全部成功才 COMPLETE；重複/越界 shard、catalog/config SHA 錯配與偽造 PASS 拒絕。
- headroom 不足、過期或 authority 未生效時零 provider/R2 write；checksum 與授權錯誤不得誤分類成可繼續的資料缺口。
- interrupted receipt/pointer write、duplicate run 與 immutable byte conflict 的 synthetic store 測試。
- 生效前不執行 production workflow；合併後以既有排程證明輪替，不能以單元測試推斷歷史完成。

## 完成時間與本次界線

撤回先前的 250 標的、25 批與 9/14 完成估算。現行是 10 批；完成時間取決於已完成批數、每次成功耗時及所有缺口能否合法解決。cron 時間是預定觸發時刻，不能保證準時啟動或完成。

本次僅新增這份工程提案。未更改 runtime、排程、config、receipt、R2 或 provider 資料；未開啟 holdout、模擬或實盤。下一個工作是按本提案完成版本化附錄、實作與 synthetic 驗證，再交付可審查的 PR；本文件本身不授予 production 執行權。
