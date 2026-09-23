# Qookey Crypto Autopilot 雲端排程提示詞

用途：ChatGPT 網頁端雲端 Scheduled task，建議每 6 小時。**此檔只是已備妥的提示詞；建立並讀回任務前，不能宣稱雲端排程已啟用。** 執行來源只限 GitHub，與使用者電腦是否開機無關。可使用的模型應沿用本提示詞和 GitHub current main，不依賴先前對話或本地路徑。

```text
請以繁體中文唯讀健檢 GitHub Repository qookey109-pixel/crypto-autopilot，使用連接的 GitHub 來源與 GitHub Actions metadata。每輪先記錄 UTC/Asia-Taipei 查核時間，重新取得 main exact SHA、open PR 的 exact head/base/draft/merged/checks；依序讀 current main 的 CURRENT_STATUS.md、PROJECT_STATUS.md、README.md、AGENTS.md、相關 versioned config/receipt。若 docs/PROJECT_CONTINUATION_RUNBOOK.md 與 docs/GITHUB_ACTIONS_OPERATING_MAP.md 已合併到 main，沿用其工作 ID、排程圖與證據格式；若仍只在草稿 PR，該 PR 僅作提案導航，不當正式執行 authority。main 或來源不可讀就標 UNKNOWN，勿猜。

從 current main workflow 檔辨認所有 cron；依 current main 的 config/research_automation_health_v0_2.json 或已合併 successor，檢查 active window、allowed_events、allowed_conclusions、max_age_seconds。每個相關 run 記 workflow path/ID、event、run ID/attempt、head SHA、nominal slot 與不確定性、created/start/completed（可取得時）、status/conclusion、policy 版本與證據 URL。查詢須注意 pagination、event filter 和可見時間範圍；若工具只能看 PR-triggered runs，不能推論自然 schedule。API 403、rate limit、資料缺頁或工具不支援，標 UNKNOWN/BLOCKED_PERMISSION，報告缺少的證據。

特別追蹤 #478 合併後的自然 Pages schedule，再查其後的 Health schedule。Pages build、deploy、browser-production 各記結論；push/PR/workflow_run 的成功、skipped job、較早的 Health run 不能代替自然排程成功。區分名義 cron 時間、GitHub 建立 run 的時間、queue delay 與 policy freshness；無法唯一配對 slot 就說明歧義。只在有新自然證據時更新原問題；已通知的相同失敗與單純 pending/running 保持安靜。

每輪查當下 open PR，不固定假設任何既有 PR 仍 open。PR #479 已合併到 main；後續只能把 current main 當 authority，新的 PR 必須重新讀 exact head/base/draft/merged/checks。查 9/27 11:53 台北後 Pionex bounded observability 的最後自然 slot、9/27 12:37 後 Core100 weekly Training 自然 slot；10/1 08:00 台北後確認 Pionex window 到期。至少累積七天實際 metadata coverage、樣本與缺失後，才提頻率建議；日期經過本身不代表七天證據完整。Training workflow success 不代表模型 PASS/NO_CHANGE，沒有可讀報告時列 UNKNOWN。provider/R2 用量同理。

這是純雲端任務，沒有本機 checkout：本地 78 項 reconciliation、Core100 fingerprint V0.2 本地提案和 recovery 檔不可讀，標 LOCAL_ONLY_UNAVAILABLE；不要聲稱已核對或自行重新建構這些成果。可指出 TD-010～TD-014 下一項及精確阻礙，但不自動做本地整合。25 個 removed-file Actions registration 的停用已有使用者授權，但既有連線缺 Actions:write、0/25 成功；本唯讀任務不反覆重試、也不要求 token。

FREE-ONLY、0 USD/month、PAPER/LIVE-PAPER ONLY。Core100 History、Pionex V0.2、ZEC V0.3/V0.4 已完成，勿重跑；replacement holdout FROZEN_UNOPENED、source_switch_authorized=false、Live Paper automatic_schedule_authorized=false。不要讀 logs/artifacts/R2/holdout/secrets，不新增 provider 請求、不裝工具、不編輯程式、開 PR、push、merge、dispatch/rerun/cancel/disable workflow、改 cron、部署、啟用 training/promotion/交易。日期、排程與模型切換不增加 execution authority。

只在有意義的新進展、完成、新故障、恢復或需要使用者決策時通知；沒有變化保持安靜。通知格式：查核時間與 main SHA、已確認變化及證據 URL、仍等待或未知、下一個可行動項目。將 PR/merge、自然 schedule、部署與研究結論分開。若連接的 GitHub 工具無法完成關鍵查詢，說明哪個 API/權限缺口，不把缺證據寫成健康。
```
