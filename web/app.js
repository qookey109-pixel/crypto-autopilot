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
      <td>${number(item.entry_price, 8)}</td>
      <td>${number(item.exit_price, 8)}</td>
      <td>${escapeHtml(item.exit_reason)}</td>
      <td class="${Number(item.net_pnl_usd) >= 0 ? "cell-pass" : "cell-pending"}">${number(item.net_pnl_usd)} USD</td>
      <td>${number(item.r_multiple)}</td>
    </tr>`).join("") : '<tr><td colspan="6">目前沒有模擬成交</td></tr>';
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
    render(mergeOperationalStatus(data, operational));
    renderPaperTraining(paperTraining);
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
  positions: "模擬持倉",
  trades: "模擬交易",
  performance: "績效中心",
  backtests: "回測",
  gates: "風險與閘門"
};

function activateView(view) {
  const target = document.querySelector(`#view-${view}`);
  if (!target) return;
  const hero = document.querySelector(".mint-hero");
  if (hero) hero.classList.toggle("is-hidden", view !== "overview");
  document.querySelectorAll(".nav-item").forEach(item => {
    const active = item.dataset.view === view;
    item.classList.toggle("active", active);
    if (active) item.setAttribute("aria-current", "page");
    else item.removeAttribute("aria-current");
  });
  document.querySelectorAll(".view").forEach(item => item.classList.remove("active"));
  target.classList.add("active");
  document.querySelector("#page-title").textContent = titles[view] || view;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

document.querySelectorAll(".nav-item, .view-link").forEach(button => {
  button.addEventListener("click", () => activateView(button.dataset.view));
});

document.querySelector("#refresh-button").addEventListener("click", loadData);
loadData();
