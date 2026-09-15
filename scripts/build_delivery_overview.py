"""Build the homepage from repository evidence without granting runtime authority."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CURRENT_OPERATIONS = "research/status/current-operations-v0-3.json"


def read_json(path: str, root: Path = ROOT) -> dict:
    return json.loads((root / path).read_text(encoding="utf-8"))


def _validate_current(current: dict) -> tuple[dict, dict, dict]:
    if current.get("schema") != "qookey-current-operations-v0.3":
        raise ValueError("Unexpected current-operations schema")
    if current.get("repository_authority") != "RESOLVE_MAIN_LIVE_AT_READ_TIME":
        raise ValueError("Repository authority semantics changed")
    if current.get("mode") != "PAPER_ONLY":
        raise ValueError("Homepage projection must remain PAPER_ONLY")

    basis = current.get("evidence_basis") or {}
    if basis.get("semantics") != "REPOSITORY_MAIN_REVIEWED_BEFORE_THIS_STATUS_VERSION":
        raise ValueError("Evidence-basis semantics changed")
    if basis.get("is_latest_main_claim") is not False:
        raise ValueError("Homepage cannot project a self-referential latest-main claim")

    core = current.get("core100") or {}
    quality = core.get("model_quality_gate") or {}
    replay = core.get("threshold_replay") or {}
    if core.get("history_status") != "COMPLETE":
        raise ValueError("Core100 history is not complete")
    if (core.get("history_complete_shards"), core.get("history_total_shards")) != (10, 10):
        raise ValueError("Core100 shard state changed")
    if core.get("training_workflow_conclusion") != "success" or core.get("training_report_status") != "PASS":
        raise ValueError("Core100 training state changed")
    if quality.get("status") != "REJECT" or quality.get("automatic_promotion") is not False:
        raise ValueError("Core100 model-quality boundary changed")
    if replay.get("workflow_conclusion") != "success":
        raise ValueError("Threshold replay is not complete")
    if replay.get("supported_thresholds") != [] or replay.get("threshold_change_supported") is not False:
        raise ValueError("Threshold replay unexpectedly supports a change")
    if replay.get("configured_threshold_changed") is not False:
        raise ValueError("Configured threshold changed")

    pionex = current.get("pionex_validation") or {}
    if pionex.get("repository_materialization_status") != "PENDING_MANUAL_DISPATCH":
        raise ValueError("Pionex validation state changed")
    authority = pionex.get("authority") or {}
    if authority.get("public_pionex_kline_reads") is not True:
        raise ValueError("Pionex public validation read authority changed")
    if authority.get("r2_validation_dataset_writes") is not True:
        raise ValueError("Pionex validation R2 authority changed")
    for key in (
        "private_api",
        "account_data",
        "replacement_holdout_access",
        "training",
        "source_switch",
        "automatic_model_promotion",
        "formal_trade_plan",
        "real_money_orders",
        "live_trading",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"Unsafe Pionex homepage projection boundary: {key}")

    gates = current.get("gates") or {}
    if gates.get("holdout") != "FROZEN_UNOPENED":
        raise ValueError("Holdout boundary changed")
    if gates.get("source_switch_authorized") is not False or gates.get("live_trading") != "CLOSED":
        raise ValueError("Trading/source-switch boundary changed")
    return core, replay, pionex


def _validate_historical_sample(root: Path) -> tuple[dict, dict]:
    """Keep the dated readiness file as historical BTC sample evidence only."""
    index = read_json("research/status/simulation-readiness-v0-1.json", root)
    if index.get("authority") is not False:
        raise ValueError("Historical readiness projection cannot be authority")
    if index.get("full_simulation_ready") is not False or index.get("full_universe_ready") is not False:
        raise ValueError("Historical readiness unexpectedly claims full readiness")
    if not index.get("safety_boundary") or any(index["safety_boundary"].values()):
        raise ValueError("Historical readiness safety boundary changed")

    btc = read_json(index["btc_fixed_sample"]["formal_receipt"], root)
    if btc.get("status") != "PASS" or btc.get("scope") != "BTC_FIXED_27_DAY_ENGINE_VALIDATION_ONLY":
        raise ValueError("BTC fixed-sample evidence changed")
    if btc.get("full_universe_ready") is not False or btc.get("full_simulation_ready") is not False:
        raise ValueError("BTC fixed sample cannot promote full readiness")
    return index, btc


def overview(root: Path = ROOT) -> tuple[str, str, dict, dict]:
    current = read_json(CURRENT_OPERATIONS, root)
    core, replay, pionex = _validate_current(current)
    historical, btc = _validate_historical_sample(root)

    training_run = int(core["training_run_id"])
    replay_run = int(replay["run_id"])
    pionex_run = int(pionex["previous_run_id"])
    sample_run = int(btc["workflow_run_id"])
    current_date = html.escape(str(current["updated_date"]))

    summary = f'''      <section class="panel readiness-summary" aria-labelledby="readiness-heading">
        <h3 id="readiness-heading">9/16 目前作業狀態</h3>
        <p><strong>Core100 資料與訓練已完成；Model Quality REJECT</strong>。完整策略驗證、holdout、promotion 與 trading 仍關閉。</p>
        <div class="delivery-metrics" aria-label="目前已核實進度">
          <article><p>BTC 27 天固定樣本</p><strong>已完成 · {btc['executed_trade_count']} 筆成交</strong><p>歷史 engine validation only；不代表全市場策略有效。</p></article>
          <article><p>Binance Core 100</p><strong>10/10 · COMPLETE</strong><p>不得因 model-quality REJECT 自動重啟歷史取得。</p></article>
          <article><p>Core100 Training</p><strong>COMPLETED · PASS</strong><p>Run {training_run}；pipeline PASS 與 model-quality acceptance 分離。</p></article>
          <article><p>Pionex Validation</p><strong>PENDING MANUAL DISPATCH</strong><p>PR #321 boundary fix 已進 Repository；仍需新的 Repository-current run。</p></article>
        </div>
        <p>模型品質閘門：<strong>REJECT</strong>。Threshold replay run {replay_run} 已完成；0.50–0.55 沒有 supported threshold change，configured threshold 保持不變。</p>
        <p>Pionex 前次 run {pionex_run} fail-closed；新的 materialization 必須從 dispatch 當下的 Repository live <code>main</code> 執行，不能把 status evidence-basis SHA 當成 latest-main claim。</p>
        <p>Current Operations 更新日期：{current_date}。下列 Actions 狀態只代表工作流程結果。</p>
        <p id="cloud-run-updated">雲端執行狀態尚未載入。</p>
        <ul id="cloud-run-list" class="cloud-run-list" aria-live="polite"></ul>
        <details><summary>查看資料證據與後續步驟</summary>
          <p><a href="https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/{sample_run}" target="_blank" rel="noopener noreferrer">BTC 固定樣本 ↗</a> · <a href="https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/{training_run}" target="_blank" rel="noopener noreferrer">Core100 Training ↗</a> · <a href="https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/{replay_run}" target="_blank" rel="noopener noreferrer">Threshold Replay ↗</a> · <a href="https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/{pionex_run}" target="_blank" rel="noopener noreferrer">Pionex 前次 fail-closed run ↗</a></p>
          <p>較舊的進度敘述保留於 Repository 歷史證據，不再作為 present-tense homepage state。V0.12 bounded metadata window 已結束。</p>
        </details>
      </section>'''

    cadence = read_json("config/history_cadence_v0_1.json", root)
    labels = {
        "binance-usdm-detailed-history-v0-1.yml": (
            "Core100 歷史補齊",
            "每日偶數小時 :23；bounded schedule 至 10/1 08:00 前",
            "目前 10/10 COMPLETE；排程不得把 model-quality REJECT 解讀成重新取得歷史資料的理由",
        ),
        "binance-usdm-detailed-training-v0-1.yml": (
            "Core100 研究訓練",
            "每週日 12:37",
            "目前 training 已完成；model-quality = REJECT；例行觸發不授權 promotion",
        ),
        "research-signal-layer-v0-2.yml": ("研究訊號", "每日 10:17", "結構化研究訊號收集"),
        "research-signal-quality-v0-1.yml": ("訊號品質", "每日 10:47", "檢查來源與資料鏈"),
        "research-automation-health-v0-2.yml": (
            "排程健康",
            "每日偶數小時 :57",
            "依 Repository exact schedule inventory 監控；manual run 不算 automation health",
        ),
        "pionex-alternative-assets-observability-v0-2.yml": (
            "Pionex 商品觀測",
            "9/20、9/27 11:53（9/13 已過）",
            "只觀測商品 metadata；與 Pionex Validation Dataset materialization 分離",
        ),
        "provider-equivalence-v0-12-successor-metadata-capture.yml": (
            "V0.12 metadata",
            "視窗已於 9/12 12:00 結束",
            "HISTORICAL；保留 schedule registration lineage，不是目前 active execution path",
        ),
    }
    declared = read_json("config/project_convergence_v0_1.json", root)["scheduled_workflows"]
    inventory = {item["workflow"]: item["cron_utc"] for group in declared.values() for item in group}
    if set(inventory) != set(labels):
        raise ValueError("Schedule inventory changed; review display labels")

    rows: list[str] = []
    for name, (label, timing, detail) in labels.items():
        actual = re.findall(
            r'^\s+- cron: "([^"]+)"',
            (root / ".github/workflows" / name).read_text(encoding="utf-8"),
            re.M,
        )
        if actual != inventory[name]:
            raise ValueError(f"Schedule index disagrees with workflow: {name}")
        if name.startswith("binance-usdm-detailed-history") and actual != [cadence["cron"]]:
            raise ValueError("History cadence authority mismatch")
        rows.append(f'<tr><th scope="row">{label}</th><td>{timing}</td><td>{detail}</td></tr>')

    schedule = '''      <section class="panel" aria-label="目前雲端排程">
        <h3>後續排程（臺灣時間）</h3>
        <p>由 GitHub Actions 雲端執行；時間為預定觸發時間，可能延遲。排程存在不代表目前 lifecycle stage 尚未完成。</p>
        <div class="table-wrap"><table><thead><tr><th>作業</th><th>預定時間</th><th>條件與狀態</th></tr></thead><tbody>''' + "\n".join(rows) + '''</tbody></table></div>
        <p>Pionex Validation Dataset V0.1 是 manual-only workflow，目前仍等待新的 Repository-current materialization；沒有新增自動排程，也沒有 holdout/training/source-switch/trading authority。</p>
        <p><a href="https://github.com/qookey109-pixel/crypto-autopilot/blob/main/CURRENT_STATUS.md" target="_blank" rel="noopener noreferrer">Current Operations ↗</a></p>
      </section>'''

    progress = {
        "schema": "qookey-dashboard-history-progress-v0.2",
        "authority": False,
        "snapshotType": "CURRENT_OPERATIONS_PROJECTION",
        "source": CURRENT_OPERATIONS,
        "status": "COMPLETE",
        "provider": "binance_usdm",
        "mode": "current_operations",
        "shardCount": 10,
        "shardsComplete": 10,
        "historyReacquisitionRequired": False,
        "trainingRunId": training_run,
        "modelQualityStatus": "REJECT",
        "safetyBoundary": {
            "holdoutAccessed": False,
            "sourceSwitchAuthorized": False,
            "automaticModelPromotionAuthorized": False,
            "tradePlanAuthorized": False,
            "realMoneyOrderAuthorized": False,
            "liveTradingAuthorized": False,
        },
    }

    web_current = {
        "schema": "qookey-current-operations-web-v0.3",
        "authority": False,
        "mode": "PAPER_ONLY",
        "repositoryAuthority": current["repository_authority"],
        "evidenceBasisParentMainSha": current["evidence_basis"]["parent_main_sha"],
        "evidenceBasisIsLatestMainClaim": False,
        "updatedDate": current["updated_date"],
        "historyStatus": core["history_status"],
        "historyCompleteShards": core["history_complete_shards"],
        "historyTotalShards": core["history_total_shards"],
        "trainingStatus": "COMPLETED_PASS",
        "trainingRunId": training_run,
        "modelQualityStatus": core["model_quality_gate"]["status"],
        "thresholdReplayRunId": replay_run,
        "thresholdChangeSupported": replay["threshold_change_supported"],
        "pionexValidationStatus": pionex["repository_materialization_status"],
        "holdoutState": current["gates"]["holdout"],
        "sourceSwitchAuthorized": current["gates"]["source_switch_authorized"],
        "liveTradingAuthorized": False,
    }
    return summary, schedule, progress, web_current


def build(site: Path, root: Path = ROOT) -> None:
    summary, schedule, progress, web_current = overview(root)
    path = site / "index.html"
    content = path.read_text(encoding="utf-8")
    for label, replacement in (("OVERVIEW", summary), ("SCHEDULE", schedule)):
        pattern = rf'<!-- DELIVERY_{label}_START -->.*?<!-- DELIVERY_{label}_END -->'
        content, count = re.subn(
            pattern,
            lambda _: f'<!-- DELIVERY_{label}_START -->\n{replacement}\n      <!-- DELIVERY_{label}_END -->',
            content,
            flags=re.S,
        )
        if count != 1:
            raise ValueError(f"Expected exactly one {label} block")

    if "./assets/js/current-operations.js" not in content:
        script_pattern = r'(\s*<script src="\./assets/js/app\.js[^"]*" defer></script>)'
        content, count = re.subn(
            script_pattern,
            r'\1\n  <script src="./assets/js/current-operations.js?v=current-ops-v0-3" defer></script>',
            content,
            count=1,
        )
        if count != 1:
            raise ValueError("Expected exactly one app.js script tag")

    path.write_text(content, encoding="utf-8")
    data_dir = site / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "history-progress.json").write_text(
        json.dumps(progress, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (data_dir / "current-operations.json").write_text(
        json.dumps(web_current, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    build(parser.parse_args().site)
