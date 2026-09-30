# Cloud Paper 保存 lineage 查核 — 2026-09-30

## V0.2 compact report follow-up — PR #661 merged 2026-09-30

Evidence basis: parent main `4ce6bbfbb3e8507c9273fb538568d316d156157b`; merge commit/main `4b12f0c9ad508e09d712320111f2e12423b69aca`; PR head `ebf812426dffb0e600fdcb2dcabf05e3f3642be6`. PR #661 passed Python 3.12/3.13, Ruff, workflow-static, CodeQL and Dependency/SBOM. Post-merge main CI #36716389946, CodeQL #36716389968, Dependency/SBOM #36716389930 and Freeze Guard #36716390111 passed; Pages was not triggered.

The new `qookey-cloud-paper-loop-report-v0.2` stores a `step_id` reference rather than duplicating the full `coordinator.run_step`. Reader logic still accepts V0.1 embedded reports and verifies the referenced immutable step, state, and result seal. No previous object was migrated, deleted, or rewritten.

Matched synthetic three-slot entry/exit/next-no-trade fixture:
- V0.1 baseline: 26 objects, 206,181 canonical JSON bytes; cloud-report 70,352 bytes.
- V0.2: 26 objects, 157,367 canonical JSON bytes; cloud-report 21,538 bytes.
- Difference: 48,814 bytes (about 23.7%) in this synthetic serialization profile only; not production R2 usage, request count, or fee savings.

The first lineage item (external report → coordinator step payload) is complete as a prepared storage-schema change. The next candidate is step → tick reference, which must preserve V0.1/V0.2 reads, recovery verification, digest lineage, complete ledger coverage, replay/restart and partial-write diagnosis. Do not remove the embedded tick or state payload until those readers and recovery paths are proven equivalent.

Cloud Paper remains disabled; D1 is unprovisioned; no provider, D1 or R2 call and no schedule/runtime activation occurred. Account-wide zero cost, freshness, all-writer coverage and headroom remain unproven. Synthetic results do not authorize production savings claims or activation.


查核基準：GitHub `main=bcdbecf48d2c38f2f999aa054115253b9a816f92`。本文件根據該 SHA 的 writer、reader、recovery 程式與既有合成 profile 整理。沒有呼叫 provider、D1 或 R2；沒有改變 activation、預算或排程 authority。

## 已量測的高佔比物件

PR #658 的合成「入場→出場→下一輪不交易」fixture 共 26 objects、206,181 canonical JSON bytes：

| kind | aggregate bytes | 現有用途 |
|---|---:|---|
| `cloud-report` | 70,352 | 外層市場／決策／帳戶報告，`cloud-result` 以 digest 指向 |
| `live-run-step` | 48,778 | coordinator 的不可變步驟、候選與內嵌 tick evidence |
| `live-tick` | 40,714 | 每次 tick 的獨立不可變證據 |
| `live-state` | 39,310 | 初始、前一及下一帳戶狀態 |
| 其餘 kinds | 7,027 | slot/result/run/claim/seal 等關聯證據 |

這是現有記憶體 store 對 canonical JSON 的計數，不等同 R2 bytes、request 數、帳戶用量或費用。

## Writer → reader → recovery 關係

### 1. Slot claim 與外層結果指標

- `cloud_loop_v0_1.run_cloud_step` 在市場／provider 操作前以 `put_json_if_absent("cloud-slot", slot, ...)` 建立 slot claim；其中連結名義 slot、實際 tick、前一 slot/state 與 run name。
- 完成後先寫入並回讀 `cloud-report`，再以 `cloud-result` 記錄 slot → report digest 指標。結果指標是 commit marker；缺指標、digest 不符或 claim 衝突都不能視為已提交。
- `latest_committed_slot` 完整列舉 slot/result/step/state 命名空間，檢查涵蓋數、前後狀態與步驟鏈；不得因減少列舉而忽略 orphan／缺件。

### 2. Coordinator 的持久化物件

`run_coordinator_v0_1.coordinate_live_paper_run_step` 將下列物件寫入 append-only store：

- `live-run`：run header，連到初始 state。
- `live-state`：初始 state 與每次已計算的 next state。
- `live-run-claim`：該步驟 request／slot 的 claim。
- `live-tick`：獨立保存完整 tick report。
- `live-run-step`：保存 coordinator 步驟，當前 schema 亦嵌入完整 `tick_report` 及 candidate specs。
- `live-run-result`：request → step 的完成 seal。

同一個 `tick_report` 會出現在獨立 `live-tick` 與 `live-run-step.tick_report`；其中 `next_state` 又完整出現在內嵌 tick 與獨立 `live-state`。這些是候選重複 payload，但目前都被完整性檢查使用。

### 3. Reader 與恢復依賴

- `cloud_loop_v0_1.committed_report` 先核對 `cloud-result` 指標及 `cloud-report` digest，再驗證報告中的 coordinator step；它要求該 step 與獨立 `live-run-step` 完全相同、next state 可由獨立 `live-state` 驗證，並確認 `live-run-result` seal 指向同一 step。
- 下一輪的 `run_cloud_step` 從已驗證報告取得前一步，並使用其 tick report 的 next state 延續帳戶。
- `run_recovery_v0_1` 檢查 run header、state、連續 step、claim、result seal，以及獨立 `live-tick` 與 step 內嵌 tick 的 canonical equality。它只允許在其餘證據完整時補建缺失 seal；不能重寫 state／step／tick，也不能重跑 provider。
- `cloud_composition_v0_1.recover_completed_slot` 先驗 D1 證據與 reservation，再讀取完整 committed report，對帳 report digest 並保留完整 reservation；恢復不會重放該 slot 或釋放額度。

因此，現在不能只刪除外層 report 的 step、step 的 tick，或 tick 的 next state；現行回讀、hash、跨物件一致性與恢復契約會拒絕這種不完整紀錄。

## 可執行的最小化順序

1. **先改外層 report 的重複 step payload。** 新增 successor report schema，以已提交的 `live-run-step` identity/reference 取代完整 `coordinator.run_step`；讀取器仍支援既有 V0.1 報告，並在讀取時依 reference 驗證獨立 step、state 與 seal。新 schema 必須定義其 digest／commit pointer 規則，且保留可供 Dashboard 使用的穩定報告欄位。
2. **再評估 step 對 tick 的引用。** 這需要 successor step schema 與 recovery reader 同時支援舊的 embedded tick、新的 `tick_id`/digest 引用、next-state linkage，以及部分寫入診斷；未通過前保留目前雙份證據。
3. **最後評估 state 內嵌重複。** 只有證明既有 hash identity、舊報告讀取、下一輪 continuation 與 recovery repair 完全等價後才移除 payload。
4. 每一階段以同一組現有 fixture 比較每種 kind 的 objects、canonical bytes、重播／重啟／故障恢復結果及讀取次數。新增缺件、hash 不符、舊 schema、重複 slot、seal 缺失與部分寫入的 fail-closed regression。
5. 確認沒有既有 reader、網站投影或治理工具依賴被移除欄位，再分批交付；**不遷移、刪除或重寫既有 V0.1/frozen objects**。

## 驗收界線與未證明事項

- profile 與 lineage inventory 只驗證工程 fixture 結構。任何「節省 R2 用量／費用」結論須等待正式受控驗收與可信帳戶級用量證據。
- schema 修正不得更改候選資格、策略／風控、slot identity、reservation 上限或實際外部操作預算。
- 未經獨立版本化 authority 與零費用/headroom 證據，不啟用 Cloud Paper、D1 provisioning、R2 寫入或自然模擬排程。
- 保持 `FREE-ONLY / 0 USD`、`PAPER / LIVE-PAPER ONLY`；holdout、source switch、promotion、真實下單與 live trading 維持關閉。
