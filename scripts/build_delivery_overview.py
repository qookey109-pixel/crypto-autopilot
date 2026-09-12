"""Build the dated homepage from repository evidence; no network or authority changes."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read_json(path: str, root: Path = ROOT) -> dict:
    return json.loads((root / path).read_text(encoding="utf-8"))


def overview(root: Path = ROOT) -> tuple[str, str, dict]:
    index = read_json("research/status/simulation-readiness-v0-1.json", root)
    btc = read_json(index["btc_fixed_sample"]["formal_receipt"], root)
    history = index["binance_core_100_history"]
    evidence = read_json(history["progress_evidence"], root)
    report = evidence["report"]
    bnx = read_json(history["bnx_repair_evidence"], root)
    ctk = read_json(index["ctk_diagnosis"]["evidence"], root)
    if (index.get("authority") is not False or index["overall"] != "NOT_READY"
            or index["full_simulation_ready"] is not False
            or index["full_universe_ready"] is not False
            or not index["safety_boundary"]
            or any(index["safety_boundary"].values())):
        raise ValueError("Unexpected readiness or authority; review required")
    if (btc["status"] != "PASS" or btc["scope"] != "BTC_FIXED_27_DAY_ENGINE_VALIDATION_ONLY"
            or btc["full_universe_ready"] is not False
            or btc["full_simulation_ready"] is not False):
        raise ValueError("Fixed BTC receipt cannot promote full readiness")
    if (report["provider"] != "binance_usdm" or report["dataset_complete"] is not False
            or report["dataset_status"] != "IN_PROGRESS"
            or evidence["run_id"] != history["latest_formal_run_id"]
            or report["shards_complete"] != history["completed_shards"]
            or report["shard_count"] != history["total_shards"]
            or not 0 <= report["shards_complete"] < report["shard_count"]
            or report["diagnostic"] != {**report["diagnostic"], **history["current_blocker"]}
            or not report["authority"] or any(report["authority"].values())):
        raise ValueError("History index disagrees with aggregate evidence")
    if (bnx["status"] != "PASS_REPAIR_EVIDENCE_FROZEN"
            or not bnx["interpretation"]["authority_bound_shard_3_published"]):
        raise ValueError("BNX publication evidence missing")
    if hashlib.sha256((root / ctk["report_path"]).read_bytes()).hexdigest() != ctk["report_sha256"]:
        raise ValueError("CTK report hash mismatch")
    if any(ctk["authority"].values()):
        raise ValueError("CTK observation grants no exception authority")
    stamp = html.escape(index["verified_at_utc"])
    run = history["latest_formal_run_id"]
    count = history["completed_shards"]
    sample_run = btc["workflow_run_id"]
    summary = f'''      <section class="panel readiness-summary" aria-labelledby="readiness-heading">
        <h3 id="readiness-heading">9/15 模擬測試準備</h3>
        <p><strong>完整模擬尚未就緒 · NOT_READY</strong>；BTC 固定樣本已通過。</p>
        <div class="delivery-metrics" aria-label="目前已核實進度">
          <article><p>BTC 27 天模擬</p><strong>已完成 · {btc['executed_trade_count']} 筆成交</strong><p>僅驗證固定樣本；已停止自動重跑。</p></article>
          <article><p>Binance Core 100</p><strong>{count}/10 分片</strong><p>BNX 修復已完成；CTK、LIT 仍有缺口。</p></article>
          <article><p>Pionex 研究候選池</p><strong>{index['pionex_research_universe']['selected_candidate_markets']} 個候選</strong><p>完整歷史與資產分類尚未完成。</p></article>
          <article><p>BTC Funding</p><strong>{index['pionex_funding']['observation_count']} 筆已核實</strong><p>對應固定樣本期間。</p></article>
        </div>
        <p>優先處理：CTK 原因核對與精確資料規則、LIT 缺口、Pionex 歷史範圍與分類。</p>
        <p>證據核對時間（UTC）：{stamp}。下列 Actions 狀態只代表工作流程結果。</p>
        <p id="cloud-run-updated">雲端執行狀態尚未載入。</p>
        <ul id="cloud-run-list" class="cloud-run-list" aria-live="polite"></ul>
        <details><summary>查看資料證據與後續步驟</summary>
          <p><a href="https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/{sample_run}" target="_blank" rel="noopener noreferrer">BTC 模擬報告 ↗</a> · <a href="https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/{run}" target="_blank" rel="noopener noreferrer">8/10 與 CTK 缺口 ↗</a> · <a href="https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/34677544161" target="_blank" rel="noopener noreferrer">BNX 正式修復 ↗</a></p>
          <p>CTK 三週期缺口已描述，尚未證實成因；不得補假 K 線。V0.12 視窗已結束，缺失時槽仍保留。固定樣本通過不代表全市場策略有效。</p>
        </details>
      </section>'''
    cadence = read_json("config/history_cadence_v0_1.json", root)
    rows = []
    labels = {
        "binance-usdm-detailed-history-v0-1.yml": ("歷史補齊", "每日偶數小時 :23；至 10/1 08:00 前", "一次一分片；缺口仍須修復"),
        "binance-usdm-detailed-training-v0-1.yml": ("研究訓練", "每週日 12:37", "完整資料通過才訓練"),
        "research-signal-layer-v0-2.yml": ("研究訊號", "每日 10:17", "結構化研究訊號收集"),
        "research-signal-quality-v0-1.yml": ("訊號品質", "每日 10:47", "檢查來源與資料鏈"),
        "research-automation-health-v0-2.yml": ("排程健康", "每日偶數小時 :57", "目前因歷史補齊失敗而告警"),
        "pionex-alternative-assets-observability-v0-2.yml": ("Pionex 商品觀測", "9/13、9/20、9/27 11:53", "只觀測商品 metadata，未抓完整歷史"),
        "provider-equivalence-v0-12-successor-metadata-capture.yml": ("V0.12 metadata", "視窗已於 9/12 12:00 結束", "最後工作流程成功但 capture 跳過；未達完整 PASS"),
    }
    declared = read_json("config/project_convergence_v0_1.json", root)["scheduled_workflows"]
    inventory = {item["workflow"]: item["cron_utc"] for group in declared.values() for item in group}
    if set(inventory) != set(labels):
        raise ValueError("Schedule inventory changed; review display labels")
    for name, (label, timing, detail) in labels.items():
        actual = re.findall(r'^\s+- cron: "([^"]+)"', (root / ".github/workflows" / name).read_text(), re.M)
        if actual != inventory[name]:
            raise ValueError(f"Schedule index disagrees with workflow: {name}")
        if name.startswith("binance-usdm-detailed-history") and actual != [cadence["cron"]]:
            raise ValueError("History cadence authority mismatch")
        rows.append(f'<tr><th scope="row">{label}</th><td>{timing}</td><td>{detail}</td></tr>')
    schedule = '''      <section class="panel" aria-label="目前雲端排程">
        <h3>後續排程（臺灣時間）</h3>
        <p>由 GitHub Actions 雲端執行；時間為預定觸發時間，可能延遲。資料缺口不會因增加執行頻率而自動消失。</p>
        <div class="table-wrap"><table><thead><tr><th>作業</th><th>預定時間</th><th>條件與狀態</th></tr></thead><tbody>''' + "\n".join(rows) + '''</tbody></table></div>
        <p>BTC 固定模擬 V0.1 已完成並退役。Pionex Reach、分類、Universe、Funding 與 Context Forward 是人工限定流程；沒有新增自動排程。</p>
        <p><a href="https://github.com/qookey109-pixel/crypto-autopilot/blob/main/docs/OPERATIONS_HANDOFF_2026_09_12.md" target="_blank" rel="noopener noreferrer">最新交接與待辦 ↗</a></p>
      </section>'''
    progress = {
        "schema": "qookey-dashboard-history-progress-v0.1", "authority": False,
        "snapshotType": "SECRET_FREE_GITHUB_ACTIONS_RUN_REPORT",
        "sourceRunId": run, "sourceUrl": evidence["source_url"],
        "observedAtUtc": report["observed_at_utc"], "status": report["dataset_status"],
        "provider": report["provider"], "mode": report["mode"],
        "shardCount": report["shard_count"], "shardsComplete": count,
        "lastShardIndex": report["shard_index"],
        "safetyBoundary": {key: False for key in (
            "holdoutAccessed", "sourceSwitchAuthorized", "automaticModelPromotionAuthorized",
            "tradePlanAuthorized", "realMoneyOrderAuthorized", "liveTradingAuthorized")},
    }
    return summary, schedule, progress


def build(site: Path, root: Path = ROOT) -> None:
    summary, schedule, progress = overview(root)
    path = site / "index.html"
    content = path.read_text(encoding="utf-8")
    for label, replacement in (("OVERVIEW", summary), ("SCHEDULE", schedule)):
        pattern = rf'<!-- DELIVERY_{label}_START -->.*?<!-- DELIVERY_{label}_END -->'
        content, count = re.subn(pattern, lambda _: f'<!-- DELIVERY_{label}_START -->\n{replacement}\n      <!-- DELIVERY_{label}_END -->', content, flags=re.S)
        if count != 1:
            raise ValueError(f"Expected exactly one {label} block")
    path.write_text(content, encoding="utf-8")
    (site / "data/history-progress.json").write_text(json.dumps(progress, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    build(parser.parse_args().site)
