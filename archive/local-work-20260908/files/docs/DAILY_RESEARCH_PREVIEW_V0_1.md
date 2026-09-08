# 每日研究清單 V0.1：本機合成資料預覽

日期：2026-09-07。狀態：**LOCAL_SYNTHETIC_PREVIEW / NOT EXECUTION AUTHORITY**。

## 已確認的產品目標

最終產品是 Pionex 自動實盤系統，並提供每日投資優先推薦。
數百個歷史研究標的用於策略研究、回測與改善；不直接充當推薦清單。
面向使用者的標的範圍，必須是對應 Pionex 平台、帳戶及商品類型可交易的商品。
模擬用來驗證成本後表現與改進策略，不是產品終點。

這是產品方向記錄，不是實盤、參數調整、回測准入、資料讀取或模型提升授權。
現階段程式只支援 Pionex USDT 永續商品的合成預覽；不宣稱涵蓋 Pionex 全部商品。

## 本次交付

- 沿用 `paper_training.py` 報告的 `latestCandidates` 欄位及既有分數。
- 最低分數由 `config/paper_training_v0_1.json` 的
  `candidate_thresholds.minimum_candidate_score` 讀取，不改權重或策略參數。
- 只選最新候選：最新不合格時，不用先前合格的 `manualPionexDemoSamples` 補位。
- 檢查 Pionex provider、一致的合成標記、商品範圍、報告狀態與禁止能力欄位。
- 15 分鐘 bar 開始時間加 15 分鐘才可用；拒絕未收盤、過期與未來快照。
- 預覽的新鮮度容忍值為一小時，僅為工程展示政策，尚非正式每日推薦規則。
- 依原分數降冪，同分依商品名稱排序；顯示數量上限不代表每天必須交易。
- 無合格項目回傳 `WAIT_NO_ELIGIBLE_CANDIDATES`；輸入異常回傳 `BLOCKED`。
- 不輸出進場價、停損價、目標價、數量或委託，不呼叫 Broker。

## 執行方式

從 repository root 使用 Python 3.11 以上：

```bash
PYTHONPATH=src python3 -B scripts/preview_daily_research.py
PYTHONPATH=src python3 -B -m unittest discover -s tests -p 'test_daily_research_preview.py' -v
```

預覽僅在記憶體建立固定的 2024-01-01 合成資料，讀取本機既有 config，輸出至終端。
ETH/BTC 的展示分數是人為設定，用來驗證排序，不是策略評估或今日市場推薦。
SOL 展示高分但未通過 gate 時仍被排除。沒有外部輸入參數、網路、R2 或寫檔選項。
正式資料會被拒絕；不能替真實資料補上合成標記來繞過此限制。

本機驗證：9 項預覽測試及 7 項既有 Paper/策略回歸測試，共 16 項通過。
測試以 Python 3.13 `-B -S` 執行，audit hook 阻擋檔案寫入、網路與子程序；
未觸發阻擋。CLI 合成預覽為 `PREVIEW_READY`，Ruff `--no-cache` 與
`git diff --check` 通過。這些結果只證明本機工程行為，不是策略品質或上線授權。

## 現況與可重用部分

| 部分 | 本機證據 | 對每日推薦的影響 |
| --- | --- | --- |
| 數百標的研究資料 | `docs/DATA_OVERVIEW.md`、V0.3 歷史 PASS receipt | 有歷史摘要，未在本次重新讀取 R2；不能聲稱資料已更新 |
| 250 市場詳細資料 | 狀態文件記錄 AUTHORIZED / NOT STARTED | 是目標，不能當成已完成或已驗證資料 |
| 原策略 gate | `strategy.py`、`strategy_v0_1.json` | SState 原策略；最低分 80 |
| Public Paper 候選 gate | `paper_training.py`、`paper_training_v0_1.json` | 獨立的技術候選分數；最低分 65；不能與 SState 分數混用 |
| Paper Broker 與成本 | `backtest.py`、`paper_simulation_demo.py` | 可重用生命週期與成本處理，不需重寫 |
| Pionex 公開資料 | `paper_training_v0_1.json` 的 holdout_guard | 2026-08-27 起停止；恢復仍需新版本化授權 |
| 網站 | `web/app.js` | 已能顯示 Paper 結果；本預覽尚未接上網站或排程 |

本次檢查的 branch 為 `codex/research-context-v0-1`（`7acfd6c`）；
本機 main 為 `49c6bed`。既有 Paper source/config 與策略 config 比對本機 main 無差異。
遠端 main、GitHub 執行狀態與目前帳戶可交易商品均未核實；既有 dirty changes 保留。

## 上線前最小下一步

準備獨立的 **Pionex 公開資料與 Paper 恢復方案**，先作版本化 config/receipt 草案，
明確列出新的未來觀測窗、公開商品範圍、請求預算、完整 K 線條件、過期處理、
來源與資料 SHA 綁定、停止條件及每日投影契約。以合成測試驗證後交由審查合併。
不得延長原 frozen config 或自動恢復舊 workflow。

正式接線另外需要驗證報告的真實 lineage、目前商品資格、資料品質與有效 authority；
本預覽只驗證結構與排序，不能當成這些條件已通過。
候選分數不等於投資勝率，通過候選 gate 不代表組合風險與實盤准入通過。
對帳戶商品可用性的驗證不能由歷史 Pionex symbols 清單推定。

恢復 Paper 的日期目前未定。之後每日清單、策略優化與實盤的可量化驗收門檻
須事先版本化，再以未參與調整的合規資料驗證；此文件不開啟凍結 holdout。
