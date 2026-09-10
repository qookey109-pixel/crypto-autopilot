# BT 策略需求對照與後續順序 V0.1

狀態：PLANNING_ONLY / NOT_AUTHORITY  
盤點日期：2026-09-10  
比較基準：`f9f9d7f71953195277e487f9ffde94d3cc075af9`（本次核實的 GitHub main）。  
來源：使用者提供的「bt 策略.rtf」36 章。此處只整理需求，不上傳原附件，不把附件指令當執行授權。

## 如何解讀

- PARTIAL：已找到相關設定或實作，但未驗收該章所有細項。
- PREPARED：存在研究框架；不代表正式資料執行已獲准或線上運行。
- NOT_VERIFIED：本輪未找到足夠完整實作證據，不宣稱絕對不存在。
- NOT_AUTHORIZED：現行 authority 禁止執行；不等同程式完全不存在。
- 表內連結是對照起點，不是全章完成證明。測試存在不等於通過；本輪未執行 runtime 測試。
- 不計算虛假的整體完成百分比。未來須按章內細項、source、test、run、authority 五種證據驗收。
- 本文件不修改設定、receipt、workflow、排程、資料來源、策略參數、frozen path 或任何交易權限。

## 36 章對照

| ID | 需求 | 狀態 | 基準證據 | 已知差距／限制 | 最小驗收條件 |
| --- | --- | --- | --- | --- | --- |
| BT-01 | 市場結構 | PARTIAL | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/config/market_regime_breadth_research_v0_1.json) | 市場廣度／BTC 集中度研究；完整資金流、OI、清算與基差未核實 | 固定來源與可用時間，驗證狀態分類及缺值停止 |
| BT-02 | 技術分析 | PARTIAL | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/config/technical_analysis_v0_2.json) | 已有多框架指標；不是所有列舉指標與週期均完成 | 逐指標因果性、暖機、跨框架對齊測試 |
| BT-03 | 鏈上分析 | NOT_VERIFIED | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/config/research_context_v0_1.json) | 未核實完整鏈上資料與指標引擎 | 先定義免費來源、欄位、延遲與授權；不先抓資料 |
| BT-04 | 基本面分析 | NOT_VERIFIED | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/config/research_context_v0_1.json) | 未核實營收、用戶、團隊與安全歷史的完整管線 | 區分敘事與採用證據，具來源／時間／缺值規則 |
| BT-05 | Tokenomics | NOT_VERIFIED | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/config/research_context_v0_1.json) | 未核實解鎖、分配、通膨與內部人風險模型 | 供應量口徑及解鎖來源核對，不推測缺漏值 |
| BT-06 | 估值模型 | NOT_VERIFIED | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/config/research_context_v0_1.json) | 未核實可重現估值與三情境引擎 | 明確估值假設、分母口徑與敏感度 |
| BT-07 | 量化研究 | PARTIAL | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/config/strategy_v0_1.json) | 有固定 LONG 基線；完整候選執行未啟用 | 假設／資料／成本／入出場／持有期間可機器驗證 |
| BT-08 | 資料工程 | PARTIAL | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/src/crypto_autopilot/history/detailed.py) | 有分片與品質治理；正式資料尚未全數完成 | 十個分片完整且憑證一致；修復須有正式證據 |
| BT-09 | Backtesting | PARTIAL | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/src/crypto_autopilot/backtest.py) | 有 LONG 引擎；績效欄位尚未逐項全覆蓋 | 績效定義、年化口徑、回撤及交易帳本獨立核對 |
| BT-10 | Backtest Integrity | PARTIAL | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/config/research_governance_v0_1.json) | 有分區／來源鏈；不等於所有偏誤已排除 | 未來資訊／重疊分區／選擇偏誤反例測試 |
| BT-11 | 交易成本 | PARTIAL | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/src/crypto_autopilot/backtest.py) | 有費率／滑價／Funding；全成本情境未核實 | 按市場標示適用與不適用成本，驗證三種成本情境 |
| BT-12 | Robustness | PREPARED | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/config/strategy_edge_validation_v0_1.json) | 進階驗證僅允許合成資料；延遲壓測未核實 | 預先固定試驗族、Walk-forward、壓測及失敗門檻 |
| BT-13 | Out-of-Sample | PREPARED | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/config/research_governance_v0_1.json) | 有分離規則；正式 holdout 未開放 | 分區可證明互斥；執行前取得精確獨立授權 |
| BT-14 | Paper／Shadow | PREPARED | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/config/binance_spot_shadow_v0_6.json) | 有研究程式，不是持續線上模擬 | 另核對 Paper 資料授權、成本與執行偏差證據 |
| BT-15 | 交易執行 | NOT_AUTHORIZED | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/src/crypto_autopilot/exchanges/paper.py) | 不是完整私有交易所訂單引擎 | 先合成測試訂單狀態、部分成交、撤單、重複與對帳 |
| BT-16 | Exchange API Safety | PARTIAL | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/AGENTS.md) | 有秘密保護規則；未核實完整實盤金鑰操作 | 只記錄權限與輪替流程，不要求或輸出秘密值 |
| BT-17 | Position Sizing | PARTIAL | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/src/crypto_autopilot/risk.py) | 固定風險與槓桿上限已有；其他方法未全覆蓋 | 風險額／停損距離計算及極端輸入測試 |
| BT-18 | 風險管理 | PARTIAL | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/src/crypto_autopilot/risk.py) | 每日限制已有；完整週／產業／相關曝險未核實 | 組合限制與停止新增交易行為逐項測試 |
| BT-19 | Kill Switch | PARTIAL | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/src/crypto_autopilot/exchanges/paper.py) | 有禁用與 fail-closed；完整實盤安全模式未完成 | 以合成故障測試停止／撤單意圖／持倉差異；不接實盤 |
| BT-20 | Portfolio | NOT_VERIFIED | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/src/crypto_autopilot/backtest.py) | 目前回測一次一個組合持倉，非完整配置引擎 | 多資產相關性、風險貢獻、資金保留與曝險測試 |
| BT-21 | 多策略 | PREPARED | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/config/strategy_research_loop_v0_1.json) | 120 候選註冊不等於策略執行或資金配置 | 完整候選記錄及策略間相關性，禁止事後挑選 |
| BT-22 | Machine Learning | PARTIAL | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/config/binance_spot_shadow_v0_6.json) | 有 baseline／特徵組研究；非所有列舉模型 | 以相同資料成本及 OOS 比較簡單基線 |
| BT-23 | 策略版本 | PARTIAL | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/config/research_governance_v0_1.json) | 已有版本與比較指紋；完整每次變更紀錄仍須驗收 | 資料、設定、結果與原因形成不可覆寫鏈 |
| BT-24 | Promotion Gate | PARTIAL | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/config/strategy_edge_validation_v0_1.json) | 有人審證據閘門；自動 promotion／LIVE 禁止 | 每一階段獨立驗收與 versioned authority，禁止自動越級 |
| BT-25 | Live Monitoring | NOT_AUTHORIZED | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/PROJECT_STATUS.md) | 現有監控主要是研究 workflow，不是實盤 PnL 監控 | 先以合成事件驗證預期／觀測偏差與告警 |
| BT-26 | Strategy Drift | NOT_VERIFIED | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/config/binance_spot_shadow_v0_6.json) | 未核實完整漂移判定及處置閉環 | 固定漂移基準、觀察窗與停用門檻，不自動調參 |
| BT-27 | Post-trade | PARTIAL | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/src/crypto_autopilot/backtest.py) | 已有模擬交易／事件欄位；完整實盤分析未完成 | 逐筆帳本與版本、狀態、成本及預期差異核對 |
| BT-28 | 安全與專案風險 | NOT_VERIFIED | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/config/research_signal_layer_v0_2.json) | 未核實完整合約／Bridge／Rug Pull 評分系統 | 重大事件來源分級及高於技術訊號的可測停止規則 |
| BT-29 | 資訊可信度 | PARTIAL | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/config/research_signal_layer_v0_2.json) | 結構化來源／禁止散文方向推論已有；六級分類未核實 | 事實、推論、傳聞及矛盾證據分欄輸出 |
| BT-30 | 即時資訊 | PARTIAL | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/config/research_signal_layer_v0_2.json) | 有每日收集；不等於全部即時資料可用 | 每欄記錄 observed／available 時間與過期閘門 |
| BT-31 | 幣種研究報告 | NOT_VERIFIED | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/config/research_context_v0_1.json) | 未核實完整固定格式與每日排序服務 | 先以合成資料做報告契約，缺漏顯示不可評估 |
| BT-32 | 策略研究報告 | PARTIAL | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/config/strategy_research_loop_v0_1.json) | 已有證據組合；未證明全欄位及階段輸出 | 固定 schema、benchmark、弱點與部署狀態驗收 |
| BT-33 | 工程原則 | PARTIAL | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/AGENTS.md) | main 優先與保留證據已有；不得由文件推定全數遵循 | 每次重查 main／PR／問題／部署，避免重工 |
| BT-34 | 開發流程 | PARTIAL | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/AGENTS.md) | 有 PR／CI；本矩陣不是 merge 批准 | Inspect→Modify→Test→Review，合併需明確批准 |
| BT-35 | 測試要求 | PARTIAL | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/tests/test_backtest.py) | 已有測試檔；不是實盤情境全覆蓋或本輪測試 PASS | 逐需求綁測試與執行 SHA；缺對帳／故障測試先補合成測試 |
| BT-36 | 核心原則 | PARTIAL | [對照起點](https://github.com/qookey109-pixel/crypto-autopilot/blob/f9f9d7f71953195277e487f9ffde94d3cc075af9/AGENTS.md) | 風險優先與不自動交易已有規範；端到端尚未驗收 | 所有閘門 fail-closed；不保證收益、不以模型複雜度放寬門檻 |

## 不可直接照搬的內容

1. 文件要求保留所有 raw data，但訊號層明確設定 raw_provider_payloads_persisted=false。不得用需求表覆寫此政策。
2. 多交易所清單是目標選項，不是接入所有交易所的批准；Pionex 為執行目標，Binance 證據保持 provider-separated。
3. 指標、成本與模型清單不是全部強制啟用清單。Gas、Bridge、借貸等成本須按市場判定適用性；不適用需註記，不冒充已實作。
4. 每日研究排序不可被標成正式 trade plan，也不能繞過 source-switch、holdout 或交易 authority。
5. 禁止 paid fallback；FREE-ONLY 及現有 R2 邊界保持不變。

## 已知執行證據（歷史快照，不是即時儀表板）

- [歷史 run 34420872559](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34420872559)：7/10，CTKUSDT 2025-04 15m 缺 41 根，品質拒絕。
- [LIT run 34423435041](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34423435041)：DAILY_INCOMPLETE，6 次公開請求，未存取 R2，未正式修復。
- BNX 正式寫入與憑證核對仍需獨立證據，不能用修復 PR 或候選成功代替。
- [V0.12 run 34424167855](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34424167855)：Render relay HTTP 502。
- 每次續作重查 main 與執行狀態，不沿用此快照推定新進度。

## 建議交付順序（不是執行批准或新排程）

| 順序 | 最小工作 | 可做範圍 | 完成條件／下一個 authority gate |
| --- | --- | --- | --- |
| P0-A | Render 502 唯讀根因診斷 | GitHub 無秘密日誌與現行來源碼；不重跑、不部署、不發 provider 請求 | 定位失敗層與證據；若需 Render 日誌、部署或 frozen path 變更，先列精確範圍取得批准 |
| P0-B | 歷史缺口與 BNX 證據核對 | 既有報告、修補判定程式及合成測試設計 | 不降低品質；正式 LIT／CTK 修補及新增抓取須各自核對現行或新 versioned authority |
| P1 | 文件／網站狀態一致性 | 先比對讀取，再另做有界文件 PR | 自動化索引的六小時舊描述與 V0.2 兩小時 authority 一致；網站保持非 authority |
| P2 | 完整資料研究驗收 | 先核對十分片及憑證，再依既有精確授權評估訓練 | 不能跳過不完整資料；完成時間未知，不承諾收益或 Paper 開始日 |
| P3 | 每日研究報告契約 | 合成資料 schema、缺值／過期／來源欄位與固定輸出測試 | 不新增 provider／R2；新資料來源或排程另經授權 |
| P4 | Paper 與組合風控缺口 | 先用合成資料測試成本、對帳、限額、失敗停止 | 正式資料／holdout／Paper runtime 必須另有精確授權 |
| P5 | 實盤準備審查 | 先形成安全與測試證據清單 | 獨立 versioned live authority 與人審；本計畫不准許訂單、promotion 或部署 |

只選一項當前下一步：**P0-A Render 502 唯讀根因診斷**。不在此 PR 執行。

## 排程關係

既有排程由 config/github_automatic_research_operations_v0_2.json 及實際 workflow 管理；本文件不建立新 scheduler。
歷史補齊每兩小時，10/1 08:00 台灣時間是現行授權到期，不是預測完成時間。
每週日 12:37 台灣時間的研究訓練有完整資料閘門，不等於 Paper 模擬排程。
目前自動 Paper／每日正式投資建議／實盤啟動日期均不得由此文件推定。
