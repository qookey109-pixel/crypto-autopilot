# 本機成果 GitHub 備份與雲端接續

此快照為歷史保存，authority=false；不要將 files/ 整包覆蓋 main，也不要執行其中的舊 workflow。
正式線上版本仍以 repository main 為準。

## 保存範圍

- 86 個檔案（含 4 張網站圖片）：未提交修改、未追蹤程式/文件，以及兩個僅存在本機的提交所產生的最終檔案內容。
- 本機 HEAD：7acfd6c7e1c1a9803520281e64970387f70695e8。
- GitHub 已驗證的還原基準：ddce0c7a6e7742387bf9b33bde834e5c38b5f7b3。
- 在該基準上覆蓋 files/ 的相對路徑，可還原此次備份範圍；不需依賴不存在於 GitHub 的本機 commit。
- MANIFEST.json 提供每個檔案的 SHA-256 與 Git blob SHA。原始檔案內容未修改。
- .DS_Store、Git 忽略檔案、環境/快取/憑證不包含在快照。不能將本快照視為整台電腦或整個目錄的完整備份。

## 後續執行偏好

使用者要求：後續專案作業在網路上執行，以 GitHub 為程式來源。
正式排程與測試使用 GitHub-hosted Actions，資料留在既有授權的 R2，網站使用 GitHub Pages。
不要新增本機常駐程序、self-hosted runner，或要求這份本機 checkout 開機才能執行排程。
本備份沒有建立新的執行排程，也沒有移動或刪除本機檔案。

## 已完成

PR #231 診斷與 PR #232 批次輪替已合併。
備份當下 main：2fb58aa84d5675a05207f61f8fc651cd8acd7f68。
PR #232 合併後 CI、Freeze Guard、網站部署已通過。
現行 Crypto Core 為 100 個標的、10 個 shard；舊版 250 標的檔案僅作歷史保存。

## 尚未完成的 BNX 修復

files/src/crypto_autopilot/history/archive_repair.py 及 files/tests/test_archive_repair.py
是尚未整合的離線候選修復器；已在隔離的 main 依賴及 Python 3.13 下通過 9 個 synthetic tests。
它可在已有、經 checksum 驗證的同來源日檔完整提供缺口資料時產生候選；
重疊 OHLCV 必須一致，月內所有 timestamp 必須完整。
沒有取得生產日檔，沒有修改 R2，不能宣稱 BNXUSDT 的 288 根缺口已修復。
這兩個檔案不在 main 的執行路徑內；需單獨建立 main 基準的修復 PR 與雲端驗證。
下一個工作：準備限定 BNXUSDT 2022-08 15m 的日/月檔比對執行契約，
明確界定 public archive reads、FREE-ONLY gate、輸出及候選審查，再依版本授權執行。
不要為了成功而插值、排除標的、改門檻或將 Binance 資料標成 Pionex。

## 新工作接續內容

延續 qookey109-pixel/crypto-autopilot，僅以最新 main 為正式 authority。
讀取本備份 MANIFEST 與說明，只移植已審查的新增成果，不回退現行 main。
後續測試與 runtime 使用雲端。先處理 BNXUSDT 歷史缺口，保留所有 failed shard
與原始 evidence；holdout、source-switch、模型升級、模擬及實盤各自遵循現行版本授權。
本機刪除是另一步；先確認忽略檔案有無需要另存的內容，本次並未授權刪除。
