const FALLBACK = {
  snapshotLabel: "安全測試資料快照",
  project: { marketCount: 15, fundingMonths: 1010 },
  pipeline: [],
  gates: [],
  markets: []
};

const state = { data: FALLBACK };

const STATUS_LABELS = {
  PASS: "通過 · PASS",
  READY: "已就緒 · READY",
  AUTHORIZED: "已授權 · AUTHORIZED",
  PREPARED: "已準備 · PREPARED",
  PENDING: "等待中 · PENDING",
  IN_PROGRESS: "進行中 · IN_PROGRESS",
  NOT_READY: "尚未就緒 · NOT_READY",
  REVIEW_REQUIRED: "需要審查 · REVIEW_REQUIRED",
  SCOPE_REDUCTION_REQUIRED: "需縮減範圍 · SCOPE_REDUCTION_REQUIRED",
  BLOCKED: "已阻擋 · BLOCKED",
  NOT_AUTHORIZED: "未授權 · NOT_AUTHORIZED",
  FAIL: "失敗 · FAIL"
};

function badgeClass(status) {
  if (["PASS", "READY", "AUTHORIZED"].includes(status)) return "pass";
  if (["PREPARED", "PENDING", "IN_PROGRESS", "NOT_READY", "REVIEW_REQUIRED", "SCOPE_REDUCTION_REQUIRED"].includes(status)) return "pending";
  if (["BLOCKED", "NOT_AUTHORIZED", "FAIL"].includes(status)) return "danger";
  return "neutral";
}

function displayStatus(status) {
  return STATUS_LABELS[status] || status;
}

function statusDot(status) {
  const className = ["PASS", "READY", "AUTHORIZED"].includes(status) ? "safe" : "";
  return `<span class="status-dot ${className}"></span>`;
}

function pipelineRow(item) {
  return `
    <div class="pipeline-row">
      ${statusDot(item.status)}
      <div>
        <strong>${escapeHtml(item.name)}</strong>
        <span>${escapeHtml(item.detail)}</span>
      </div>
      <span class="badge ${badgeClass(item.status)}" title="Authority 狀態碼：${escapeHtml(item.status)}">${displayStatus(item.status)}</span>
    </div>
  `;
}

function renderPipeline(items) {
  const root = document.querySelector("#pipeline-list");
  const visible = items.slice(0, 6);
  const remaining = items.slice(6);
  root.innerHTML = visible.map(pipelineRow).join("") + (remaining.length ? `
    <details class="pipeline-more">
      <summary>展開其餘 ${remaining.length} 項 authority 與準備狀態</summary>
      <div>${remaining.map(pipelineRow).join("")}</div>
    </details>
  ` : "");
}

function renderCriticalGates(items) {
  const selected = items.filter(item => item.critical).slice(0, 4);
  const root = document.querySelector("#critical-gates");
  root.innerHTML = selected.map(item => `
    <div class="gate ${item.tone || "pending"}">
      <strong>${escapeHtml(item.name)}</strong>
      <small>${escapeHtml(item.detail)}</small>
      <span class="badge ${badgeClass(item.status)}" title="Authority 狀態碼：${escapeHtml(item.status)}">${displayStatus(item.status)}</span>
    </div>
  `).join("");
}

function renderAllGates(items) {
  const root = document.querySelector("#all-gates");
  root.innerHTML = items.map(item => `
    <div class="gate ${item.tone || "pending"}">
      <strong>${escapeHtml(item.name)}</strong>
      <small>${escapeHtml(item.detail)}</small>
      <span class="badge ${badgeClass(item.status)}" title="Authority 狀態碼：${escapeHtml(item.status)}">${displayStatus(item.status)}</span>
    </div>
  `).join("");
}

function renderMarkets(items) {
  const root = document.querySelector("#market-table");
  root.innerHTML = items.map(item => `
    <tr>
      <td><strong>${item.symbol}</strong></td>
      <td class="${item.trade === "PASS" ? "cell-pass" : "cell-pending"}">${displayStatus(item.trade)}</td>
      <td class="${item.mark === "PASS" ? "cell-pass" : "cell-pending"}">${displayStatus(item.mark)}</td>
      <td class="${item.funding === "PASS" ? "cell-pass" : "cell-pending"}">${displayStatus(item.funding)}</td>
      <td><span class="provider-tag ${item.provider === "PIONEX" ? "pionex" : "binance"}">${item.provider}</span></td>
      <td><span class="badge ${badgeClass(item.status)}" title="Authority 狀態碼：${item.status}">${displayStatus(item.status)}</span></td>
    </tr>
  `).join("");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function number(value, digits = 2) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toLocaleString("zh-TW", { maximumFractionDigits: digits }) : "—";
}

function formatTradeTime(value) {
  const raw = String(value ?? "").trim();
  const numeric = /^\d+$/.test(raw) ? Number(raw) : NaN;
  const date = Number.isFinite(numeric) ? new Date(numeric) : new Date(raw);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("zh-TW", {
    timeZone: "Asia/Taipei",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

function renderPaperTraining(report) {
  if (!report || report.mode !== "PAPER_TRAINING_ONLY") return;
  const authority = report.authority || {};
  if (authority.liveTradingAuthorized === true || authority.realMoneyOrderAuthorized === true) {
    console.error("Unsafe paper-training projection rejected");
    return;
  }
  const metrics = report.metrics || {};
  const status = report.status || "PREPARED";
  document.querySelector("#paper-training-status").textContent = displayStatus(status);
  document.querySelector("#paper-training-summary").textContent =
    `${number(metrics.trade_count, 0)} 筆模擬交易 · 淨損益 ${number(metrics.net_pnl_usd)} USD · ${report.runId || "fixture"}`;
  document.querySelector("#paper-return").textContent = `${number(metrics.return_pct)}%`;
  document.querySelector("#paper-win-rate").textContent = `${number(Number(metrics.win_rate || 0) * 100)}%`;
  document.querySelector("#paper-profit-factor").textContent = metrics.profit_factor == null ? "—" : number(metrics.profit_factor);
  document.querySelector("#paper-drawdown").textContent = `${number(metrics.max_drawdown_pct)}%`;
  document.querySelector("#paper-performance-note").textContent = report.interpretation || "Paper-only research evidence.";

  const signals = report.latestCandidates || [];
  document.querySelector("#paper-signal-table").innerHTML = signals.length ? signals.map(item => `
    <tr>
      <td><strong>${escapeHtml(item.symbol)}</strong></td>
      <td>${number(item.score)}</td>
      <td><span class="badge ${item.eligible ? "pass" : "pending"}">${item.eligible ? "候選" : "略過"}</span></td>
      <td>${number(item.reference_price, 8)}</td>
      <td>${number(item.stop_price, 8)}</td>
      <td>${number(item.target_price, 8)}</td>
    </tr>`).join("") : '<tr><td colspan="6">目前沒有已完成暖機的候選訊號</td></tr>';

  const trades = report.paperTrades || [];
  document.querySelector("#paper-trade-table").innerHTML = trades.length ? trades.slice(-50).reverse().map(item => `
    <tr>
      <td><strong>${escapeHtml(item.symbol)}</strong></td>
      <td><time>${formatTradeTime(item.entry_time_ms ?? item.entryTimeMs ?? item.signal_time_ms)}</time></td>
      <td><time>${formatTradeTime(item.exit_time_ms ?? item.exitTimeMs ?? item.entry_time_ms ?? item.signal_time_ms)}</time></td>
      <td>${number(item.entry_price, 8)}</td>
      <td>${number(item.exit_price, 8)}</td>
      <td>${escapeHtml(item.exit_reason)}</td>
      <td class="${Number(item.net_pnl_usd) >= 0 ? "cell-pass" : "cell-pending"}">${number(item.net_pnl_usd)} USD</td>
      <td>${number(item.r_multiple)}</td>
    </tr>`).join("") : '<tr><td colspan="8">目前沒有模擬成交</td></tr>';
}


function renderStrategy(strategy) {
  if (!strategy) return;
  const setText = (selector, value) => { const node = document.querySelector(selector); if (node) node.textContent = value; };
  const timeframe = strategy.timeframes || {}, sstate = strategy.sstate || {}, score = strategy.score || {}, risk = strategy.risk || {}, exit = strategy.exit || {};
  setText("#strategy-version", `V${strategy.version || "0.1.0"}`); setText("#strategy-mode", `${strategy.mode === "paper" ? "PAPER-ONLY" : strategy.mode} · ${strategy.direction || "LONG_ONLY"}`); setText("#strategy-universe", `${Number(strategy.universe_target || 0)} 個候選市場`);
  setText("#strategy-context-timeframe", timeframe.market_context || "—"); setText("#strategy-setup-timeframe", timeframe.setup || "—"); setText("#strategy-entry-timeframe", timeframe.entry || "—"); setText("#strategy-states", (sstate.allowed_states || []).join(" / ")); setText("#strategy-probability", `${number(Number(sstate.minimum_probability || 0) * 100)}%（背景閘門）`); setText("#strategy-samples", `${number(sstate.minimum_samples || 0, 0)} 筆`);
  setText("#strategy-min-score", `${number(score.minimum_entry_score || 0, 0)} / 100`);
  const weights = score.weights || {}, labels = { sstate_quality: "SState 品質", historical_probability: "歷史機率", trend_1h: "1H 趨勢", entry_15m: "15m 進場", reward_risk: "報酬／風險", liquidity_funding: "流動性／Funding" }, root = document.querySelector("#strategy-score-list");
  if (root) root.innerHTML = Object.entries(weights).map(([key, value]) => `<div class="strategy-score-row"><span>${labels[key] || key}</span><strong>${number(value, 0)}</strong><div class="strategy-score-track"><i style="width:${Math.max(0, Math.min(100, Number(value) * 4))}%"></i></div></div>`).join("");
  setText("#strategy-risk", `${number(Number(risk.risk_fraction_per_trade || 0) * 100)}% equity / 交易`); setText("#strategy-leverage", `${number(risk.max_leverage || 0)}x 上限 · 結構停損 ≤ ${number(risk.max_structural_stop_atr || 0)} ATR`); setText("#strategy-daily-trades", `${number(strategy.max_new_trades_per_day || 0, 0)} 筆新交易`); setText("#strategy-daily-loss", `每日停止於 -${number(risk.daily_loss_limit_r || 0)}R`); setText("#strategy-partial", `+${number(exit.partial_at_r || 0)}R 先實現 ${number(Number(exit.partial_fraction || 0) * 100)}%`); setText("#strategy-runner", `Runner ${number(Number(exit.runner_fraction || 0) * 100)}%`); setText("#strategy-holding", `最長持有 ${number(exit.max_holding_hours || 0, 0)} 小時`);
}

function upsertByName(items, additions) {
  const merged = [...items];
  additions.forEach(addition => {
    const index = merged.findIndex(item => item.name === addition.name);
    if (index >= 0) {
      merged[index] = addition;
    } else {
      merged.push(addition);
    }
  });
  return merged;
}

function mergeOperationalStatus(data, operational) {
  if (!operational || operational.authority !== false) return data;
  const merged = {
    ...data,
    project: {
      ...(data.project || {}),
      operationalStatus: operational.project || {},
    },
    pipeline: upsertByName(data.pipeline || [], operational.pipelineItems || []),
    gates: upsertByName(data.gates || [], operational.gateItems || []),
    operationalStatus: operational,
  };
  return merged;
}

function render(data) {
  state.data = data;
  document.querySelector("#snapshot-label").textContent = data.snapshotLabel;
  document.querySelector("#market-count").textContent = Number(data.project.marketCount || 0).toLocaleString("zh-TW");
  const fundingMonths = data.project.fundingMonthsObserved ?? data.project.fundingMonths ?? 0;
  document.querySelector("#funding-months").textContent = Number(fundingMonths).toLocaleString("zh-TW");
  renderPipeline(data.pipeline || []);
  renderCriticalGates(data.gates || []);
  renderAllGates(data.gates || []);
  renderMarkets(data.markets || []);
}

async function fetchJson(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}

async function loadData() {
  try {
    const data = await fetchJson("./data/dashboard.json");
    let operational = null;
    let paperTraining = null;
    try {
      operational = await fetchJson("./data/operational-status.json");
    } catch (error) {
      console.warn("Operational status projection unavailable", error);
    }
    try {
      paperTraining = await fetchJson("./data/paper-training.json");
    } catch (error) {
      console.warn("Paper training projection unavailable", error);
    }
    let strategy = null;
    try {
      strategy = await fetchJson("./data/strategy.json");
    } catch (error) {
      console.warn("Strategy projection unavailable", error);
    }
    render(mergeOperationalStatus(data, operational));
    renderPaperTraining(paperTraining);
    renderStrategy(strategy);
  } catch (error) {
    console.error("Dashboard snapshot load failed", error);
    render(FALLBACK);
    document.querySelector("#snapshot-label").textContent = "狀態快照暫時無法讀取";
  }
}

const titles = {
  overview: "總覽",
  "data-health": "資料健康度",
  signals: "交易訊號",
  strategy: "策略",
  positions: "模擬持倉",
  trades: "模擬交易",
  performance: "績效中心",
  backtests: "回測",
  gates: "風險與閘門"
};

function activateView(view) {
  const target = document.querySelector(`#view-${view}`);
  if (!target) return;
  const isOverview = view === "overview";
  const hero = document.querySelector(".mint-hero");
  if (hero) hero.classList.toggle("is-hidden", !isOverview);
  document.body.classList.toggle("subview-active", !isOverview);
  document.querySelectorAll(".nav-item").forEach(item => {
    const active = item.dataset.view === view;
    item.classList.toggle("active", active);
    if (active) item.setAttribute("aria-current", "page");
    else item.removeAttribute("aria-current");
  });
  document.querySelectorAll(".view").forEach(item => item.classList.remove("active"));
  target.classList.add("active");
  document.querySelector("#page-title").textContent = titles[view] || view;
  window.scrollTo({ top: 0, left: 0, behavior: "instant" });
}

document.querySelectorAll(".nav-item, .view-link").forEach(button => {
  button.addEventListener("click", () => activateView(button.dataset.view));
});

document.querySelector("#refresh-button").addEventListener("click", loadData);
loadData();
