# Qookey Crypto Autopilot — 9/11 Audit / Schedule / Handoff

本文件是工程交接，不是歷史資料完成憑證，也不另授予執行權限。

## 專案與交付

- Repository: https://github.com/qookey109-pixel/crypto-autopilot
- Website: https://qookey109-pixel.github.io/crypto-autopilot/
- 本次讀取的遠端 main：`6a7aad2aa4c9d8445209d77b32a4c1698d9984ef`。
- PR #263、#264、#265 已整合；不可重做這次整合。
- 交付分支：`codex/simulation-reliability-20260911`；須 PR 審核合併，禁止自動 merge。
- 交付 [PR #266](https://github.com/qookey109-pixel/crypto-autopilot/pull/266) 已建立但未合併；report/schema/test 改善已在 head `6d139d0fc9279bc9d4c94d1f83fbe07ff7ed786c` 通過完整 PR CI。後續文件 commit 會移動 head，最終 head 仍以 PR 為準。
- 原本 `codex/research-context-v0-1` dirty tree 保留；修改在隔離工作樹進行。
- 本文件不自我宣稱已合併；精確交付 commit / PR / CI 以交付 PR 與最終訊息核對。
- 目標：9/15 paper / simulation，不啟用 live trading、真實資金或帳戶 API。

## Final Audit

| 分類 | 狀態 | 已確認／剩餘工作 |
| --- | --- | --- |
| main 與整合 | DONE | main CI [34563519111](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34563519111)、Pages [34563519082](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34563519082) 成功；不等同資料完成 |
| Pionex BTC 歷史 | PARTIAL | [34513815680](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34513815680) 為 8/1–8/28 exclusive 的 27 天；15M 2592、60M 648、4H 162；不是多年／全市場 |
| Pionex Funding | DONE（capture） | [34563641025](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34563641025) 81 筆原生 funding；simulation admission 另行版本化 |
| Pionex 150+ 候選池 | PARTIAL | [34563615657](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34563615657) 611 live PERP、559 eligible、197 selected；profile 30/99/68；不是已補齊 197 份歷史 |
| 資產分類 | BLOCKED（evidence） | fallback `crypto` 並非已核實分類；WTI/BRENTOIL/XAUT/PAXG 等需 registry 複核；不能把所有候選視為已核實 crypto core |
| Pionex Reach | PARTIAL | [34563589773](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34563589773) FAIL；已修 weekly close 邊界、無秘密診斷、interval 獨立診斷；真實重跑尚未完成 |
| Binance Core 100 | PARTIAL | [34594667095](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34594667095)，9/11 11:34 UTC：7/10，shard 8，LITUSDT 2025-12 15m 缺 70 根，品質拒絕 |
| 其他缺口 | BLOCKED（evidence） | [34563890638](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34563890638) CTKUSDT 2025-04 15m 缺 41；[34545772874](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34545772874) BNXUSDT 2022-08 1h 缺 72；BNX 15m 正式 publication/hash 核對本輪未核實 |
| 模擬主引擎 | DONE（synthetic regression） | 既有 canonical backtest、fee/slippage/funding、risk、kill switch、position/ledger adapter 保留；合成測試不是正式樣本結果 |
| 固定 BTC report contract | DONE（PR validation） | 明列 kill switch 設定/觸發、max holding 設定/觸發、gross/net PnL 與 costs/drawdown；NO_SIGNAL/NO_TRADE/EXECUTION_FAILED 共用一致 outcome schema，未取得結果用 `null` 而非假 0；未新增第二套 engine |
| 固定 BTC 雲端模擬 | PARTIAL | 新 authority + CI-success 事件流程已實作，待最終 head 審核合併和正式樣本執行；READY 僅限定 27 天 BTC 引擎驗證 |
| Render / metadata / health | BLOCKED（runtime evidence） | 最新 metadata [34593620982](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34593620982) 與 health [34595985298](https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34595985298) 失敗；不得把先前 502 推測成這次已確認原因 |
| 文件／網站 | PARTIAL | 更新 current index、標記舊 snapshot、7/10 投影、新增事件驅動雲端狀態；新網站待 PR 合併部署 |
| API key／付費方案 | NOT NEEDED | 本階段公共行情不需要 Pionex 私人 API；0 USD/month；不用新的 provider、付費 runtime 或帳戶權限 |

### 修復順序

1. P0：固定 BTC report/schema 已補齊並通過 PR CI；下一 gate 是確認最終 PR head → 使用者批准合併 → 當下 main push CI → 雲端真實樣本模擬 → 驗證正式 ledger/cost/report artifact。
2. P1：合併 Reach 安全修復後取得新五 interval 報告；不覆寫舊 FAIL。
3. P1：候選池分類複核 → 依 30/99/68 分層、實測 reach 制定 materialization authority → hash/schema/gap 驗證。
4. P1：逐項核對 Binance 缺口，不用 zero-fill、偷偷排除或 provider switch 製造 COMPLETE。
5. P1：依最新安全日誌診斷 metadata/health；V0.12 到期後不得延長舊窗口或補造舊 slot。
6. P2：整理重疊 PR、歷史文件與 website detail；不重構已驗證 SState core。

## Latest Schedule

全部專案 runtime 在 GitHub-hosted runner／GitHub Pages；Render 只保留授權 transport。
下表是讀取 workflow 的設定，不是保證 GitHub 準點開跑。加快採用事件接續，
而不是在相同 provider 缺資料時無上限提高重試次數。

| 作業 | 觸發／臺灣時間 | Input → Output | 失敗處理／批准 |
| --- | --- | --- | --- |
| V0.12 metadata | 9/12 12:00 前，每小時 :17/:47 | frozen metadata contract → immutable slot evidence | serialized、stale fail closed；自動，窗口不能自行延長 |
| Research Signal V0.2 | 每日 10:17 | public research sources → research receipt | FREE-ONLY/headroom、失敗報告；自動，不生成 live order |
| Signal Quality V0.1 | 每日 10:47 | signal evidence → quality report | 缺失／過期 fail closed；自動 |
| Automation Health V0.2 | 每日偶數小時 :57 | GitHub run metadata → health report | 不因此啟動 provider 或 R2；自動 |
| Binance Core100 history | 9/9–9/30 UTC，每日偶數小時 :23 臺灣時間 | one bounded shard → quality/receipt | 每次一 shard、serialized；資料拒絕不算 COMPLETE；自動，10/1 08:00 到期 |
| Binance detailed training | 週日 12:37 | 已完整 admitted Core100 → research training report | 資料不完整不訓練；不 promotion；自動條件式 |
| Pionex alternatives observability | 9/13、20、27 11:53（9/4、6 已過） | public metadata → catalog/diff | metadata only，不是歷史補齊；自動 |
| Reach V0.3 | 手動 GitHub dispatch | bounded BTC public requests → metadata PASS/FAIL | ≤105 requests、0 retries、全 interval 必須成功；main 現行 scope，修復後需新執行證據 |
| Universe / Funding | 手動 GitHub dispatch | 3 snapshot calls / ≤3 funding calls → reports | 現有成功證據可用，不重跑充當進度；無 R2 |
| Context Forward | 9/12 12:00–9/19 12:00，一次手動 | current versioned capture → bounded report | 尚無每四小時自動 authority |
| **新增 BTC simulation** | **審核合併後，當下 main 的 push CI 成功事件** | pinned funding ZIP + exact 3 R2 Parquets → simulated ledger/report artifact | 最多 20 個 workflow run 序號內、attempt 1、9/16 08:00 前；超限 fail closed，0 R2 list/write、0 provider；需合併新 authority |
| **改善 Pages 更新** | **上述 Reach/Universe/Funding/history/health/BTC 流程結束事件** | 6 組 GitHub run metadata → cloud-runs.json → Pages | main/repo/event 篩選；API 失敗顯示待核實；不讀 artifact/log/R2；待合併 |

現行有 7 個 cron workflow。新 BTC/Pages 使用事件，沒有新增 cron、self-hosted 或 Render 排程。
BTC run number 包含 GitHub 建立的 skipped executions；20 是上限，不承諾 20 次成功。
超限或到期後需結束／取代這個版本，不得重跑來繞過 budget。新的 event workflow
不會直接把 197 市場歷史蒐集自動啟動。

既有 Codex 提醒 `crypto` 已更新，保留 ACTIVE、每小時一次、read-only。
現在追蹤 #266、真實 BTC simulation、Reach、全池與缺口證據；只在重要變化通知。
完成後通知一次並停止；9/16 08:00 仍未完成則通知 NOT_READY/blockers 並停止截止日追蹤。
未建立第二份提醒。它不是 GitHub 資料執行引擎；桌面 project-scoped 排程需
電腦／App 開啟，不能把它冒充獨立雲端服務（[官方排程說明](https://learn.chatgpt.com/docs/automations?surface=app)）。

## 架構與 Simulation Readiness

| Stage | Input → Output | Authority / failure / tests | 9/15 evidence |
| --- | --- | --- | --- |
| Acquisition | Pionex/Binance 分離 → bounded candle/funding | versioned provider scope；no silent fallback；history/funding tests | REVIEW：BTC 有、197 全史無 |
| Validation | bytes/receipt → verified candle/funding | SHA/size/schema/continuity；不合格停止；adapter/funding tests | PASS（測試），正式新 run 待驗 |
| Features | 15M/60M/4H → causal context/setup/entry | 原 adapter；next-bar only；technical/simulation tests | PASS（測試） |
| Research/Strategy | causal features → LONG simulation plans | 僅 research/simulation，不改正式 SState；無 signal 不能強迫交易 | PASS（測試） |
| Training | admitted dataset → research model | Core100 completeness gate，no promotion | REVIEW：全資料尚未完成 |
| Evaluation | plans + costs → historical evaluation | 27-day sample 不代表 generalization；walk-forward 全池未完成 | REVIEW |
| Risk | equity/stop/limits → sizing/entry/exit | finite checks、3x cap、daily loss/entry limit、kill switch；risk/backtest tests | PASS（測試） |
| Paper Portfolio | trades/funding → positions/ledger/PnL/drawdown | canonical backtest，5bps fee/2bps slippage 為明示模型假設，不是假稱實際成交費率 | PASS（測試），正式樣本 REVIEW |
| Reporting | simulation result → JSON artifact | scope 固定、full_universe_ready=false；controls + gross/net PnL + null-safe outcome schema；read-only website | PASS（測試），雲端新 run REVIEW |
| CI | PR source → lint/unit/budget/Pages | 3.12/3.13 雲端矩陣；失敗不得宣稱完成 | PR head `6d139d0f`：CI run `34612721171` SUCCESS；Python 3.12/3.13、Ruff、690 tests、兩個 R2 budget gates PASS；其餘 PR workflow 亦 SUCCESS；Pages deploy 在 PR 依設計 skip |

**FULL SIMULATION: NOT_READY。** 不能保證 9/15 完成所有歷史與全池驗證；
provider 可用性、缺口和未執行的真實樣本結果不能由程式測試代替。
本輪可交付的是可審核、可在雲端執行的固定 BTC 端到端驗證，以及 Reach
修復與更清楚的狀態視圖。個別 `READY` 必須同時閱讀其 scope。

## Website

- 首頁先回答：是否就緒、已核實資料、下一步；證據／歷史細節可展開。
- 新雲端狀態只標示「流程成功／需修復／待核實」，絕不當成 dataset COMPLETE。
- GitHub URL allowlist、DOM textContent、舊／無法核實快照提示，沒有 browser secret。
- 7/10 是 9/11 11:34 UTC 已核實 receipt 投影；新的 run 狀態不偷偷更新分片完成數。
- WebKit 26.5：1440px 桌面／390px 手機皆無水平溢位，明細展開與策略導覽 PASS、0 JavaScript errors；並非實際 Safari App 驗證。新版本正式部署仍待合併。
- `node scripts/test_dashboard_cloud_runs.cjs` 驗證 URL allowlist、過期／未來快照、錯誤狀態清除；已加入 Pages CI。
- 本輪沒有為了外觀新增圖片、外部 AI runtime 或第三方登入依賴。

## 未合併 PR 整理

讀到 13 個 open PR：#262/#261/#260/#258/#257/#256/#255（draft），
#249/#220/#199/#168/#167/#166（open）。前三份仍是舊堆疊 base。
這份清單不等於已確認所有內容可刪除；逐項比較 main tree/diff 後才標示 superseded。
本輪不自動合併或關閉這些 PR，避免丟失獨立研究內容。

## 重要檔案與邊界

- `PROJECT_STATUS.md`、`README.md`、`SECURITY.md`：最新入口；舊快照明確標示歷史。
- `config/simulation_btc_execution_v0_1.json` + 同日 execution authority receipt：僅新 main 合併後的 bounded read。
- `scripts/run_simulation_btc_v0_1.py`：GitHub context、ZIP SHA、exact object hashes、budget/time gates；report 明列 controls、gross/net PnL 與一致 outcome schema。
- `src/crypto_autopilot/paper/simulation_funding_v0_1.py`：只集中既有 canonical fixed-sample BacktestConfig，不新增 broker/risk engine。
- `src/crypto_autopilot/history/pionex_reach_v0_3.py`：整根 candle 不跨 holdout，失敗安全診斷。
- `scripts/build_cloud_run_status.py`：只讀 GitHub metadata，不是新 authority。
- Funding artifact `10185206308`：ZIP SHA256 `90a52badad147e407e7dca4f88a607c647c2fec467e185eb31556f2714879095`；實際下載／成員與 hash 仍由 cloud runner fail-closed 驗證。
- R2 三個精確物件總 105694 bytes/run、零 retry、零 list/write；Cloudflare skill 指引用於收窄 R2 存取。
- 保留所有歷史 FAIL/receipt、Equivalence FAIL、source_switch=false、frozen holdout；0 USD runtime、無 live order。
- 設計參考：[GitHub workflow_run](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run)、[Cloudflare boto3](https://developers.cloudflare.com/r2/examples/aws/boto3/)。

## 新聊天接續提示詞

> 接手 qookey109-pixel/crypto-autopilot。先讀 GitHub 最新 main、PROJECT_STATUS、README、docs/SIMULATION_CLOUD_HANDOFF_2026_09_11.md 與本次交付 PR 的 exact head/CI；不要沿用這份 handoff 的 main SHA 當最新。保留原本 dirty tree，延續 codex/simulation-reliability-20260911，不重做已合併 #263/#264/#265。先確認 bounded BTC execution PR 的最終 head 是否經使用者批准合併及雲端真實樣本 run 是否成功；report contract 已要求 kill switch/max holding 設定與觸發、gross/net PnL、cost/drawdown 及 NO_SIGNAL/NO_TRADE/EXECUTION_FAILED 一致 null-safe schema。只有 scope=BTC_FIXED_27_DAY_ENGINE_VALIDATION_ONLY 的 READY 不等於全池 READY。接著完成 Reach 新報告、197 候選分類審查、分層 materialization authority 與資料核對；Binance 7/10 和 BNX/LIT/CTK 缺口必須用正式 receipt 證明。遵循 branch→commit→push→PR→CI，未獲新的明確批准不可 merge。歷史證據不改寫、holdout 不開、provider 不換標、0 USD、無真實交易。檢查→修正→測試→CI；最終更新 audit/readiness/schedule/handoff，不能用 synthetic PASS 或 workflow success 冒充資料完成。不在聊天要求 API key。
