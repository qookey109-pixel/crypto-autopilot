# Local Workspace Reconciliation Receipt — 2026-09-24

Observed: 2026-09-23 19:34 UTC / 2026-09-24 03:34 Asia/Taipei. Repository: `qookey109-pixel/crypto-autopilot`. Current main observed at `c06b46b61f6a26c7a8130cfd82b7c3408e29ed67`.

## Scope and evidence basis

This receipt makes the old 78-path workspace inventory portable for future maintainers and cloud models. Its source is the read-only checkpoint in the original checkout at `handoffs/2026-09-23-project-checkpoint/local-files.md` and `reconciliation-plan.md`. That checkpoint records 78 paths and a byte comparison against main `87ad32fd8f29a0c34bbf61ad11694fe4ef29df51` on 2026-09-23. The byte classes and Git status below are **historical checkpoint values**; they have not been recomputed against current main `c06b46b61f6a26c7a8130cfd82b7c3408e29ed67`.

This receipt re-evaluates package outcomes against merged current-main work: C1 through PR #493, C4 through PR #491, and C5 through PR #492. C2 and C3 remain deferred. A read-only audit hashed the 78 paths in the current checkout and compared Git blob IDs with the complete recursive tree at `c06b46b`. Repeat the status and hash checks immediately before any later local file operation.

## Counts

| Measure | Count | Meaning |
| --- | ---: | --- |
| Inventory paths | 78 | Full path list below |
| Baseline byte classes | 12 MATCH_MAIN, 2 MATCH_MAIN_OTHER_PATH, 31 DIFF_MAIN, 33 LOCAL_ONLY | Compared to the 2026-09-23 checkpoint main, not current main |
| Current byte classes (78 paths) | 15 MATCH_CURRENT_MAIN, 2 MATCH_CURRENT_MAIN_OTHER_PATH, 34 DIFF_CURRENT_MAIN, 27 LOCAL_ONLY | Git blob hashes compared to the complete, non-truncated recursive tree at `c06b46b` |
| Current local status | 91 entries: 15 modified, 76 untracked | All 78 inventory path/status pairs still match the checkpoint; 13 newer untracked handoff files are additional |
| Disposition groups | A: 14, B: 29, C: 21, D: 14 | Groups and package outcomes below |

Group totals reconcile: 14 + 29 + 21 + 14 = 78.

## Package outcomes

| Package | Paths | Current disposition |
| --- | ---: | --- |
| A — already present | 14 | Same bytes at the 2026-09-23 baseline, including two relocated paths; do not re-import. Recheck current blob before proposing local cleanup. |
| B — superseded | 29 | A newer/current-main implementation or path already covers the observed local version; do not restore the old version. Recheck the actual current local diff before cleanup. |
| C1 — unified Work Item intake | 8 | Integrated by PR #493. The mixed README path also contains the deferred C3 preview proposal and needs its own diff review. |
| C4 — signal-ingest parsing | 3 | Integrated by PR #491; do not copy the old module wholesale over current main. |
| C5 — quality authority validation | 3 | Integrated by PR #492; preserve current-main dedupe, source binding, freshness, and NO_CHANGE behavior. |
| C2 — Agent Arena | 3 | Deferred; no current authorized comparison set or distinct operational route. Keep local sources as proposals. |
| C3 — synthetic Daily Research preview | 4 | Deferred; old Paper report schema is superseded by current Daily Opportunity Engine and Strategy Router. Keep local sources as proposals. |
| D — history and recovery | 14 | Preserve as historical/recovery material; never treat as current authority or execute automatically. |

## Local file disposition matrix

Current Git status matches the 78 checkpoint records; the baseline byte class is dated 2026-09-23, while the current-byte result was freshly compared with main `c06b46b`. “Modified” and “untracked” do not alone establish that a path is safe to reset or remove.

| Local path | Current Git status | Byte class at 2026-09-23 baseline | Current byte result vs main `c06b46b` | Matching / comparison path | Group | Current disposition |
| --- | --- | --- | --- | --- | --- | --- |
| `.DS_Store` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | D | 保留為歷史／recovery；不當成 current authority，不由此紀錄移除。 |
| `.github/ISSUE_TEMPLATE/config.yml` | untracked | LOCAL_ONLY | MATCH_CURRENT_MAIN | .github/ISSUE_TEMPLATE/config.yml | C | C1 已由 PR #493 整合；不整檔回灌；混合／清理操作須先逐檔重比與取得核准。 |
| `.github/ISSUE_TEMPLATE/work-item.yml` | untracked | LOCAL_ONLY | MATCH_CURRENT_MAIN | .github/ISSUE_TEMPLATE/work-item.yml | C | C1 已由 PR #493 整合；不整檔回灌；混合／清理操作須先逐檔重比與取得核准。 |
| `.github/pull_request_template.md` | untracked | LOCAL_ONLY | MATCH_CURRENT_MAIN | .github/pull_request_template.md | C | C1 已由 PR #493 整合；不整檔回灌；混合／清理操作須先逐檔重比與取得核准。 |
| `.github/workflows/dashboard-github-pages.yml` | modified | DIFF_MAIN | DIFF_CURRENT_MAIN | .github/workflows/dashboard-github-pages.yml (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `.github/workflows/research-automation-health-v0-1.yml` | untracked | DIFF_MAIN | DIFF_CURRENT_MAIN | .github/workflows/research-automation-health-v0-1.yml (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `.github/workflows/research-signal-layer-v0-2.yml` | untracked | MATCH_MAIN | MATCH_CURRENT_MAIN | .github/workflows/research-signal-layer-v0-2.yml | A | 2026-09-23 基線與 main 同路徑或改路徑 bytes 相同；不回灌。任何清理前須對 current main blob 重驗。 |
| `.github/workflows/research-signal-quality-v0-1.yml` | untracked | DIFF_MAIN | DIFF_CURRENT_MAIN | .github/workflows/research-signal-quality-v0-1.yml (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `AGENTS.md` | modified | DIFF_MAIN | DIFF_CURRENT_MAIN | AGENTS.md (內容不同) | C | C1 已由 PR #493 整合；不整檔回灌；混合／清理操作須先逐檔重比與取得核准。 |
| `PROJECT_STATUS.md` | modified | DIFF_MAIN | DIFF_CURRENT_MAIN | PROJECT_STATUS.md (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `README.md` | modified | DIFF_MAIN | DIFF_CURRENT_MAIN | README.md (內容不同) | C | C1 已由 PR #493 整合；C3 deferred，保存本地候選；不整檔回灌；混合／清理操作須先逐檔重比與取得核准。 |
| `config/engineering_workflow_v0_1.json` | untracked | LOCAL_ONLY | DIFF_CURRENT_MAIN | config/engineering_workflow_v0_1.json (內容不同) | C | C1 已由 PR #493 整合；不整檔回灌；混合／清理操作須先逐檔重比與取得核准。 |
| `config/pionex_historical_research_pool_v0_1.json` | untracked | MATCH_MAIN | MATCH_CURRENT_MAIN | config/pionex_historical_research_pool_v0_1.json | A | 2026-09-23 基線與 main 同路徑或改路徑 bytes 相同；不回灌。任何清理前須對 current main blob 重驗。 |
| `config/post_window_research_successor_schedule_v0_1.json` | untracked | MATCH_MAIN | MATCH_CURRENT_MAIN | config/post_window_research_successor_schedule_v0_1.json | A | 2026-09-23 基線與 main 同路徑或改路徑 bytes 相同；不回灌。任何清理前須對 current main blob 重驗。 |
| `config/research_automation_health_v0_1.json` | untracked | MATCH_MAIN | MATCH_CURRENT_MAIN | config/research_automation_health_v0_1.json | A | 2026-09-23 基線與 main 同路徑或改路徑 bytes 相同；不回灌。任何清理前須對 current main blob 重驗。 |
| `config/research_signal_layer_v0_1.json` | untracked | MATCH_MAIN | MATCH_CURRENT_MAIN | config/research_signal_layer_v0_1.json | A | 2026-09-23 基線與 main 同路徑或改路徑 bytes 相同；不回灌。任何清理前須對 current main blob 重驗。 |
| `config/research_signal_layer_v0_2.json` | untracked | MATCH_MAIN | MATCH_CURRENT_MAIN | config/research_signal_layer_v0_2.json | A | 2026-09-23 基線與 main 同路徑或改路徑 bytes 相同；不回灌。任何清理前須對 current main blob 重驗。 |
| `config/research_signal_quality_v0_1.json` | untracked | DIFF_MAIN | DIFF_CURRENT_MAIN | config/research_signal_quality_v0_1.json (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `docs/AGENT_ARENA_V0_1.md` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | C | C2 deferred，保存本地候選；不整檔回灌；混合／清理操作須先逐檔重比與取得核准。 |
| `docs/CONTINUOUS_LEARNING_ROADMAP_V0_1.md` | untracked | DIFF_MAIN | DIFF_CURRENT_MAIN | docs/CONTINUOUS_LEARNING_ROADMAP_V0_1.md (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `docs/DAILY_RESEARCH_PREVIEW_V0_1.md` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | C | C3 deferred，保存本地候選；不整檔回灌；混合／清理操作須先逐檔重比與取得核准。 |
| `docs/DATA_OVERVIEW.md` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | D | 保留為歷史／recovery；不當成 current authority，不由此紀錄移除。 |
| `docs/DATA_RETENTION_POLICY_V0_1.md` | modified | DIFF_MAIN | DIFF_CURRENT_MAIN | docs/DATA_RETENTION_POLICY_V0_1.md (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `docs/ENGINEERING_WORKFLOW_V0_1.md` | untracked | LOCAL_ONLY | DIFF_CURRENT_MAIN | docs/ENGINEERING_WORKFLOW_V0_1.md (內容不同) | C | C1 已由 PR #493 整合；不整檔回灌；混合／清理操作須先逐檔重比與取得核准。 |
| `docs/HISTORY_BACKFILL_RECOVERY_PROPOSAL_V0_1.md` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | D | 保留為歷史／recovery；不當成 current authority，不由此紀錄移除。 |
| `docs/PIONEX_HISTORICAL_RESEARCH_POOL_V0_1.md` | untracked | DIFF_MAIN | DIFF_CURRENT_MAIN | docs/PIONEX_HISTORICAL_RESEARCH_POOL_V0_1.md (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `docs/RESEARCH_AUTOMATION_HANDOFF_V0_1.md` | modified | DIFF_MAIN | DIFF_CURRENT_MAIN | docs/RESEARCH_AUTOMATION_HANDOFF_V0_1.md (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `docs/RESEARCH_AUTOMATION_HEALTH_V0_1.md` | untracked | DIFF_MAIN | DIFF_CURRENT_MAIN | docs/RESEARCH_AUTOMATION_HEALTH_V0_1.md (內容不同) | C | C5 已由 PR #492 整合；不整檔回灌；混合／清理操作須先逐檔重比與取得核准。 |
| `docs/RESEARCH_AUTOMATION_SCHEDULE_V0_1.md` | modified | DIFF_MAIN | DIFF_CURRENT_MAIN | docs/RESEARCH_AUTOMATION_SCHEDULE_V0_1.md (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `docs/RESEARCH_SIGNAL_LAYER_V0_1.md` | untracked | DIFF_MAIN | DIFF_CURRENT_MAIN | docs/RESEARCH_SIGNAL_LAYER_V0_1.md (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `docs/RESEARCH_SIGNAL_LAYER_V0_2.md` | untracked | DIFF_MAIN | DIFF_CURRENT_MAIN | docs/RESEARCH_SIGNAL_LAYER_V0_2.md (內容不同) | C | C4 已由 PR #491 整合；不整檔回灌；混合／清理操作須先逐檔重比與取得核准。 |
| `handoffs/2026-09-16-operations-schedule/changed-files.json` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | D | 保留為歷史／recovery；不當成 current authority，不由此紀錄移除。 |
| `handoffs/2026-09-16-operations-schedule/github-observation.json` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | D | 保留為歷史／recovery；不當成 current authority，不由此紀錄移除。 |
| `handoffs/2026-09-16-operations-schedule/prepared-changes.patch` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | D | 保留為歷史／recovery；不當成 current authority，不由此紀錄移除。 |
| `handoffs/2026-09-16-operations-schedule/prepared-source-snapshot.tar.gz` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | D | 保留為歷史／recovery；不當成 current authority，不由此紀錄移除。 |
| `handoffs/2026-09-16-operations-schedule/schedule-proposal.json` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | D | 保留為歷史／recovery；不當成 current authority，不由此紀錄移除。 |
| `handoffs/2026-09-23-core100-fingerprint-v0-2-proposal.md` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | D | 保留為歷史／recovery；不當成 current authority，不由此紀錄移除。 |
| `handoffs/2026-09-23-github-actions-automation-inventory.md` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | D | 保留為歷史／recovery；不當成 current authority，不由此紀錄移除。 |
| `handoffs/2026-09-23-latest-audit-and-next-steps.md` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | D | 保留為歷史／recovery；不當成 current authority，不由此紀錄移除。 |
| `research/receipts/2026-08-24-research-automation-health-v0-1-authority.json` | untracked | MATCH_MAIN | MATCH_CURRENT_MAIN | research/receipts/2026-08-24-research-automation-health-v0-1-authority.json | A | 2026-09-23 基線與 main 同路徑或改路徑 bytes 相同；不回灌。任何清理前須對 current main blob 重驗。 |
| `research/receipts/2026-09-10-pionex-historical-research-pool-v0-1-authority.json` | untracked | MATCH_MAIN | MATCH_CURRENT_MAIN | research/receipts/2026-09-10-pionex-historical-research-pool-v0-1-authority.json | A | 2026-09-23 基線與 main 同路徑或改路徑 bytes 相同；不回灌。任何清理前須對 current main blob 重驗。 |
| `scripts/build_dashboard_authority_snapshot.py` | modified | MATCH_MAIN | MATCH_CURRENT_MAIN | scripts/build_dashboard_authority_snapshot.py | A | 2026-09-23 基線與 main 同路徑或改路徑 bytes 相同；不回灌。任何清理前須對 current main blob 重驗。 |
| `scripts/build_research_calendar_projection.py` | untracked | DIFF_MAIN | DIFF_CURRENT_MAIN | scripts/build_research_calendar_projection.py (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `scripts/check_research_automation_health.py` | untracked | DIFF_MAIN | DIFF_CURRENT_MAIN | scripts/check_research_automation_health.py (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `scripts/check_research_signal_quality.py` | untracked | DIFF_MAIN | DIFF_CURRENT_MAIN | scripts/check_research_signal_quality.py (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `scripts/preview_daily_research.py` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | C | C3 deferred，保存本地候選；不整檔回灌；混合／清理操作須先逐檔重比與取得核准。 |
| `scripts/run_research_signal_layer_v0_2.py` | untracked | DIFF_MAIN | DIFF_CURRENT_MAIN | scripts/run_research_signal_layer_v0_2.py (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `scripts/validate_dashboard_static.py` | modified | DIFF_MAIN | DIFF_CURRENT_MAIN | scripts/validate_dashboard_static.py (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `src/crypto_autopilot/agent_arena.py` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | C | C2 deferred，保存本地候選；不整檔回灌；混合／清理操作須先逐檔重比與取得核准。 |
| `src/crypto_autopilot/daily_research_preview.py` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | C | C3 deferred，保存本地候選；不整檔回灌；混合／清理操作須先逐檔重比與取得核准。 |
| `src/crypto_autopilot/history/archive_repair.py` | untracked | MATCH_MAIN | MATCH_CURRENT_MAIN | src/crypto_autopilot/history/archive_repair.py | A | 2026-09-23 基線與 main 同路徑或改路徑 bytes 相同；不回灌。任何清理前須對 current main blob 重驗。 |
| `src/crypto_autopilot/research_automation_health.py` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `src/crypto_autopilot/research_signal_ingest_v0_2.py` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | C | C4 已由 PR #491 整合；不整檔回灌；混合／清理操作須先逐檔重比與取得核准。 |
| `src/crypto_autopilot/research_signal_layer.py` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `src/crypto_autopilot/research_signal_quality.py` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | C | C5 已由 PR #492 整合；不整檔回灌；混合／清理操作須先逐檔重比與取得核准。 |
| `tests/test_agent_arena.py` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | C | C2 deferred，保存本地候選；不整檔回灌；混合／清理操作須先逐檔重比與取得核准。 |
| `tests/test_archive_repair.py` | untracked | MATCH_MAIN | MATCH_CURRENT_MAIN | tests/test_archive_repair.py | A | 2026-09-23 基線與 main 同路徑或改路徑 bytes 相同；不回灌。任何清理前須對 current main blob 重驗。 |
| `tests/test_daily_research_preview.py` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | C | C3 deferred，保存本地候選；不整檔回灌；混合／清理操作須先逐檔重比與取得核准。 |
| `tests/test_engineering_workflow_v0_1.py` | untracked | LOCAL_ONLY | DIFF_CURRENT_MAIN | tests/test_engineering_workflow_v0_1.py (內容不同) | C | C1 已由 PR #493 整合；不整檔回灌；混合／清理操作須先逐檔重比與取得核准。 |
| `tests/test_research_automation_health.py` | untracked | DIFF_MAIN | DIFF_CURRENT_MAIN | tests/test_research_automation_health.py (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `tests/test_research_automation_schedule_config.py` | untracked | DIFF_MAIN | DIFF_CURRENT_MAIN | tests/test_research_automation_schedule_config.py (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `tests/test_research_calendar_projection.py` | untracked | DIFF_MAIN | DIFF_CURRENT_MAIN | tests/test_research_calendar_projection.py (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `tests/test_research_signal_ingest_v0_2.py` | untracked | DIFF_MAIN | DIFF_CURRENT_MAIN | tests/test_research_signal_ingest_v0_2.py (內容不同) | C | C4 已由 PR #491 整合；不整檔回灌；混合／清理操作須先逐檔重比與取得核准。 |
| `tests/test_research_signal_layer.py` | untracked | DIFF_MAIN | DIFF_CURRENT_MAIN | tests/test_research_signal_layer.py (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `tests/test_research_signal_quality.py` | untracked | DIFF_MAIN | DIFF_CURRENT_MAIN | tests/test_research_signal_quality.py (內容不同) | C | C5 已由 PR #492 整合；不整檔回灌；混合／清理操作須先逐檔重比與取得核准。 |
| `web/README.md` | modified | DIFF_MAIN | DIFF_CURRENT_MAIN | web/README.md (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `web/app.js` | modified | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `web/assets/cloud-garden-v4.jpg` | untracked | MATCH_MAIN_OTHER_PATH | MATCH_CURRENT_MAIN_OTHER_PATH | web/assets/images/cloud-garden-v4.jpg | A | 2026-09-23 基線與 main 同路徑或改路徑 bytes 相同；不回灌。任何清理前須對 current main blob 重驗。 |
| `web/assets/market-orbit-v2.jpg` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | D | 保留為歷史／recovery；不當成 current authority，不由此紀錄移除。 |
| `web/assets/research-constellation-v1.jpg` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | D | 保留為歷史／recovery；不當成 current authority，不由此紀錄移除。 |
| `web/assets/research-orbit-v3.jpg` | untracked | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | D | 保留為歷史／recovery；不當成 current authority，不由此紀錄移除。 |
| `web/data/dashboard.json` | modified | DIFF_MAIN | DIFF_CURRENT_MAIN | web/data/dashboard.json (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `web/data/research-calendar.json` | untracked | DIFF_MAIN | DIFF_CURRENT_MAIN | web/data/research-calendar.json (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `web/data/research-evidence.json` | untracked | MATCH_MAIN | MATCH_CURRENT_MAIN | web/data/research-evidence.json | A | 2026-09-23 基線與 main 同路徑或改路徑 bytes 相同；不回灌。任何清理前須對 current main blob 重驗。 |
| `web/data/strategy.json` | untracked | DIFF_MAIN | DIFF_CURRENT_MAIN | web/data/strategy.json (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `web/index.html` | modified | DIFF_MAIN | DIFF_CURRENT_MAIN | web/index.html (內容不同) | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `web/styles.css` | modified | LOCAL_ONLY | LOCAL_ONLY | 無相同路徑或相同 bytes | B | 該基線版本已被 main 更新／取代；不回灌。任何還原或移除前須重新比對 current main 與本地差異。 |
| `web/variables.css` | modified | MATCH_MAIN_OTHER_PATH | MATCH_CURRENT_MAIN_OTHER_PATH | web/assets/css/variables.css | A | 2026-09-23 基線與 main 同路徑或改路徑 bytes 相同；不回灌。任何清理前須對 current main blob 重驗。 |

## Exact duplicate candidates (approval required)

Read-only Git blob and file-mode comparison against the complete current-main tree found 17 exact local copies: all 17 have matching content and file mode. Fifteen untracked files match the same main path or its relocated path; two modified tracked files match main content. This is evidence for a proposed cleanup only; it does not authorize modifying the original checkout.

The **15 untracked exact-duplicate paths proposed for a separate removal approval** are:

- `.github/ISSUE_TEMPLATE/config.yml`
- `.github/ISSUE_TEMPLATE/work-item.yml`
- `.github/pull_request_template.md`
- `.github/workflows/research-signal-layer-v0-2.yml`
- `config/pionex_historical_research_pool_v0_1.json`
- `config/post_window_research_successor_schedule_v0_1.json`
- `config/research_automation_health_v0_1.json`
- `config/research_signal_layer_v0_1.json`
- `config/research_signal_layer_v0_2.json`
- `research/receipts/2026-08-24-research-automation-health-v0-1-authority.json`
- `research/receipts/2026-09-10-pionex-historical-research-pool-v0-1-authority.json`
- `src/crypto_autopilot/history/archive_repair.py`
- `tests/test_archive_repair.py`
- `web/assets/cloud-garden-v4.jpg` → identical main path `web/assets/images/cloud-garden-v4.jpg`
- `web/data/research-evidence.json`

The two exact matches that are tracked and modified relative to the old checkout are excluded from this proposal: `scripts/build_dashboard_authority_snapshot.py` matches the same main path, and `web/variables.css` matches `web/assets/css/variables.css`. Keep them unchanged until a separate branch/checkout reconciliation is approved.

## 13 post-checkpoint local handoff files

The 13 untracked paths below were added after the 78-path inventory baseline. They are outside A/B/C/D and remain preserved for separate review:

- `handoffs/2026-09-23-project-checkpoint/README.md`
- `handoffs/2026-09-23-project-checkpoint/cloud-scheduled-check-prompt.md`
- `handoffs/2026-09-23-project-checkpoint/github-observation.json`
- `handoffs/2026-09-23-project-checkpoint/handoff-connector-recheck.json`
- `handoffs/2026-09-23-project-checkpoint/handoff-recheck-2026-09-23.json`
- `handoffs/2026-09-23-project-checkpoint/latest-verification.json`
- `handoffs/2026-09-23-project-checkpoint/local-files.json`
- `handoffs/2026-09-23-project-checkpoint/local-files.md`
- `handoffs/2026-09-23-project-checkpoint/pr-479-final-checks.json`
- `handoffs/2026-09-23-project-checkpoint/preservation-check.json`
- `handoffs/2026-09-23-project-checkpoint/reconciliation-plan.md`
- `handoffs/2026-09-23-project-checkpoint/scheduled-check-prompt.md`
- `handoffs/2026-09-24-follow-up-schedule.md`

## Next action and boundary

The reconciliation decisions are recorded; physical cleanup is still pending. The 15 untracked exact duplicates above form one precise proposed removal batch. Before applying it, repeat the main SHA, working-tree status, Git blob hash, and mode checks, then obtain explicit approval for those exact paths. Do not reset or remove the two modified tracked matches as part of that batch. The other 76 current status entries—including all D paths, the seven deferred C2/C3 paths, and 13 later handoff files—remain untouched. Any broader cleanup needs its own exact path list and review; never use `git reset`, `git clean`, bulk move, or bulk removal.

This document adds no provider, R2, holdout, source-switch, model-promotion, training, schedule, deployment, or trading authority.
