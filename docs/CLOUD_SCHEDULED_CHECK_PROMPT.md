# Qookey Crypto Autopilot：純雲端接續提示詞

更新：2026-09-25。排程平台採 GitHub Actions：既有 Health 每兩小時，
Cloud Maintenance V0.1 接收其自然完成事件。不是另一個 ChatGPT/Codex 本機排程。
本提示詞本身不會啟用排程；只有 main 合併、權限檢查和兩次自然執行證據才能完成驗收。

以下可直接交給任何模型：

```text
你正在接續 qookey109-pixel/crypto-autopilot。全部資料與操作都在 GitHub／雲端；
禁止讀写本機檔案、使用本機終端機或排程、依賴本機 checkout／recovery／聊天記憶。
GitHub-hosted runner 的暫存 checkout 可以使用。沒有 GitHub 工具則回報
BLOCKED_CAPABILITY，停止操作，不假裝有存取能力。

依序執行，不跳步：
1. 記錄 UTC／台北時間，透過 GitHub 解析 main exact SHA；讀取該 SHA 的
   CURRENT_STATUS.md、PROJECT_STATUS.md、README.md、AGENTS.md、
   docs/PROJECT_CONTINUATION_RUNBOOK.md 及本次相關 versioned config／receipt。
   SHA 無法解析就停止。文件的 evidence-basis SHA 不是 latest main。
2. 查 live open PR、exact head/base、draft、merged 與 checks，包含 #496／#497。
   已有相同工作就接續，不重開。#496 是舊準備成果；#501–#504 已交付 V0.2 提案、collector 及一次性授權。#505 是待驗證的實作草稿；只有 exact-head CI、合併到 main 與執行門檻通過後才能考慮一次手動 bootstrap。
   25 個歷史 workflow 已停用，#497 保存紀錄；不得沿用舊 0/25 說法重做。
   本機清理為 EXCLUDED_BY_USER，不是等待取得本機檔案。
3. 讀已合併的 Cloud Maintenance V0.1 contract／receipt 及最新自然 run summary。
   尚未合併時只審查，不啟用。Health 保持唯讀；自動修復由固定程式執行，
   僅限 CURRENT_STATUS.md 和接續手冊的 generated blocks 及一個 draft PR。
4. 按手冊 CLOUD-01 驗收：CI、merge、自然 schedule、deploy、研究結論分開。
   已知 Health `36099624753` 成功、維護 `36099661460` 的 inspect 成功而 propose `BLOCKED_PERMISSION`；這輪不算成功驗收。需確認 GitHub 建立 PR 權限的決策，再取得兩次不同自然 Health 來源的成功維護回合，並有 NO_CHANGE／零 commit 證據。
   push／PR／手動 run／skipped job 不可冒充自然成功或模型 PASS。
5. 遇錯按 CLOUD-02 交接：列 code、證據 URL、main／head、缺少資料、最小下一步。
   403 不重試、不索取 token、不自動擴權；main 改變或人工修改就停止寫入。
6. 9/27 台北 11:53 後查 Pionex 最後自然 slot，12:37 後查 Training；
   10/1 08:00 後查 Pionex window 到期。過期不補跑、不延期。
   至少七天完整 metadata coverage 才提 cadence 建議。
7. 只處理一張可開始的工作卡：目的、前置、精確来源、編號步驟、可改範圍、
   雲端驗證、停止條件、交付證據。程式邏輯修正需使用者指派，不由定時模型猜測執行。

每次交付：
- 時間、main SHA、CLOUD_ONLY。
- 已完成：ID、變更、GitHub CI／run／PR URL。
- 等待或未知：原因、缺少證據。
- PR／merge／自然 schedule／部署／研究結果：各自狀態。
- 唯一下一步：工作卡及可直接執行的步驟。
- 本機資料：EXCLUDED_BY_USER；沒有本機依賴。

FREE-ONLY 0 USD/month；PAPER／LIVE-PAPER ONLY。
Core100 History、Pionex V0.2、ZEC V0.3/V0.4 已完成，不重跑。
holdout FROZEN_UNOPENED；source_switch_authorized=false。
不得新增 provider／R2 存取、訓練、promotion、交易、paid fallback，
不得自動 merge、部署、dispatch/rerun/cancel/disable 或修改 cron。
模型或排程不會增加權限；沒有足夠工具時，正確結果是停止並列出缺口。
```

自動程序只在有語意變更時提出文件草稿；每輪完整 metadata 留在 Actions summary。
原有 ChatGPT 個人任務如仍存在，不應宣稱已被本次修改、停用或驗證。
