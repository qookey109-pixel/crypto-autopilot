const FALLBACK = {
  snapshotLabel: "安全測試資料快照",
  project: { marketCount: 15, fundingMonths: 1010 },
  pipeline: [],
  gates: [],
  markets: [],
  calendar: []
};

const state = { data: FALLBACK };

const STATUS_LABELS = {
  PASS: "通過 · PASS",
  READY: "已就緒 · READY",
  AUTHORIZED: "已授權 · AUTHORIZED",
  PREPARED: "已準備 · PREPARED",
  WAITING_AUTHORITY: "等待授權 · WAITING_AUTHORITY",
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
  if (["PREPARED", "WAITING_AUTHORITY", "PENDING", "IN_PROGRESS", "NOT_READY", "REVIEW_REQUIRED", "SCOPE_REDUCTION_REQUIRED"].includes(status)) return "pending";
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
      <span class="badge ${badgeClass(item.status)}" title="Authority 狀態碼：${escapeHtml(item.status)}">${escapeHtml(displayStatus(item.status))}</span>
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
      <span class="badge ${badgeClass(item.status)}" title="Authority 狀態碼：${escapeHtml(item.status)}">${escapeHtml(displayStatus(item.status))}</span>
    </div>
  `).join("");
}

function renderAllGates(items) {
  const root = document.querySelector("#all-gates");
  root.innerHTML = items.map(item => `
    <div class="gate ${item.tone || "pending"}">
      <strong>${escapeHtml(item.name)}</strong>
      <small>${escapeHtml(item.detail)}</small>
      <span class="badge ${badgeClass(item.status)}" title="Authority 狀態碼：${escapeHtml(item.status)}">${escapeHtml(displayStatus(item.status))}</span>
    </div>
  `).join("");
}

function renderMarkets(items) {
  const root = document.querySelector("#market-table");
  root.innerHTML = items.map(item => `
    <tr>
      <td><strong>${escapeHtml(item.symbol)}</strong></td>
      <td class="${item.trade === "PASS" ? "cell-pass" : "cell-pending"}">${escapeHtml(displayStatus(item.trade))}</td>
      <td class="${item.mark === "PASS" ? "cell-pass" : "cell-pending"}">${escapeHtml(displayStatus(item.mark))}</td>
      <td class="${item.funding === "PASS" ? "cell-pass" : "cell-pending"}">${escapeHtml(displayStatus(item.funding))}</td>
      <td><span class="provider-tag ${item.provider === "PIONEX" ? "pionex" : "binance"}">${escapeHtml(item.provider)}</span></td>
      <td><span class="badge ${badgeClass(item.status)}" title="Authority 狀態碼：${escapeHtml(item.status)}">${escapeHtml(displayStatus(item.status))}</span></td>
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
  if (value === null || value === undefined || value === "") return "—";
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

function formatTrustedTime(value, missingLabel = "尚未提供") {
  const formatted = formatTradeTime(value);
  return formatted === "—" ? missingLabel : `${formatted}（台北）`;
}

function calendarTiming(item, now = Date.now()) {
  const startsAt = item.startsAtUtc ? Date.parse(item.startsAtUtc) : NaN;
  const endsAt = item.endsAtUtc ? Date.parse(item.endsAtUtc) : NaN;
  const targetAt = item.targetAtUtc ? Date.parse(item.targetAtUtc) : NaN;
  if (item.kind === "dependency") return { label: "依賴閘門", className: "dependency" };
  if (Number.isFinite(targetAt)) {
    return now > targetAt
      ? { label: "目標日已到 · 待驗證", className: "waiting" }
      : { label: "工程目標", className: "target" };
  }
  if (Number.isFinite(startsAt) && now < startsAt) return { label: "尚未開始", className: "upcoming" };
  if (Number.isFinite(endsAt) && now > endsAt) return { label: "時段已結束 · 待證據", className: "waiting" };
  if ((!Number.isFinite(startsAt) || now >= startsAt) && (!Number.isFinite(endsAt) || now <= endsAt)) {
    return { label: "進行中", className: "active" };
  }
  return { label: "等待條件", className: "waiting" };
}

function renderCalendar(calendar) {
  const root = document.querySelector("#research-calendar");
  const generatedAt = document.querySelector("#calendar-generated-at");
  if (!root) return;
  const items = Array.isArray(calendar?.items) ? calendar.items : [];
  if (!items.length) {
    root.innerHTML = '<li class="calendar-loading"><strong>研究時程暫時無法讀取</strong><small>請以 Repository authority 為準</small></li>';
    if (generatedAt) generatedAt.textContent = "行事曆投影：尚未提供";
    return;
  }
  if (generatedAt) {
    generatedAt.textContent = `行事曆投影：${formatTrustedTime(calendar.projectionGeneratedAtUtc)}`;
  }
  root.innerHTML = items.map(item => {
    const timing = calendarTiming(item);
    return `
      <li class="calendar-card ${timing.className}">
        <div class="calendar-card-top">
          <span>${escapeHtml(item.windowLabel)}</span>
          <span class="badge ${badgeClass(item.status)}">${escapeHtml(displayStatus(item.status))}</span>
        </div>
        <strong>${escapeHtml(item.title)}</strong>
        <small>${escapeHtml(item.detail)}</small>
        <em>${escapeHtml(timing.label)}</em>
      </li>
    `;
  }).join("");
}

function renderEquityChart(report) {
  const chart = document.querySelector("#paper-equity-chart");
  const line = document.querySelector("#paper-equity-line");
  const area = document.querySelector("#paper-equity-area");
  const note = document.querySelector("#paper-equity-note");
  if (!chart || !line || !area || !note) return;
  const values = (Array.isArray(report?.equityCurve) ? report.equityCurve : [])
    .map(Number)
    .filter(Number.isFinite);
  if (values.length < 2) {
    chart.classList.add("no-data");
    chart.setAttribute("aria-label", "尚無可繪製的模擬資產曲線");
    line.setAttribute("d", "M0 150 H800");
    area.setAttribute("d", "M0 150 H800 V230 H0 Z");
    note.textContent = "完成至少一筆模擬成交後，才顯示真實產生的資產曲線。";
    return;
  }
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const spread = maximum - minimum;
  const x = index => (index / (values.length - 1)) * 800;
  const y = value => spread === 0 ? 130 : 220 - ((value - minimum) / spread) * 180;
  const path = values.map((value, index) => `${index === 0 ? "M" : "L"}${x(index).toFixed(2)} ${y(value).toFixed(2)}`).join(" ");
  chart.classList.remove("no-data");
  chart.setAttribute("aria-label", `模擬資產曲線，共 ${values.length} 個已記錄節點`);
  line.setAttribute("d", path);
  area.setAttribute("d", `${path} L800 230 L0 230 Z`);
  note.textContent = `Trade-close equity · ${values.length} 個已記錄節點`;
}

function renderPaperTraining(report) {
  const observedAt = document.querySelector("#paper-observed-at");
  if (!report || report.mode !== "PAPER_TRAINING_ONLY") {
    if (observedAt) observedAt.textContent = "Paper 觀測：尚未完成";
    return;
  }
  const authority = report.authority || {};
  if (authority.liveTradingAuthorized === true || authority.realMoneyOrderAuthorized === true) {
    console.error("Unsafe paper-training projection rejected");
    if (observedAt) observedAt.textContent = "Paper 觀測：資料契約未通過";
    return;
  }
  const metrics = report.metrics || {};
  const status = report.status || "PREPARED";
  if (observedAt) {
    observedAt.textContent = `Paper 觀測：${formatTrustedTime(report.observedAtUtc, "尚未完成")}`;
  }
  document.querySelector("#paper-training-status").textContent = displayStatus(status);
  document.querySelector("#paper-training-summary").textContent =
    `${number(metrics.trade_count, 0)} 筆模擬交易 · 淨損益 ${number(metrics.net_pnl_usd)} USD · ${report.runId || "fixture"}`;
  document.querySelector("#paper-return").textContent = `${number(metrics.return_pct)}%`;
  document.querySelector("#paper-win-rate").textContent = `${number(Number(metrics.win_rate || 0) * 100)}%`;
  document.querySelector("#paper-profit-factor").textContent = metrics.profit_factor == null ? "—" : number(metrics.profit_factor);
  document.querySelector("#paper-drawdown").textContent = `${number(metrics.max_drawdown_pct)}%`;
  document.querySelector("#paper-performance-note").textContent = report.interpretation || "Paper-only research evidence.";
  renderEquityChart(report);

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

function researchEvidenceIsSafe(evidence) {
  if (!evidence || evidence.schema !== "qookey-dashboard-research-evidence-v0.1") return false;
  if (evidence.authority !== false || evidence.mode !== "PAPER_ONLY_READ_ONLY") return false;
  const boundary = evidence.safetyBoundary || {};
  const requiredFalse = [
    "providerReadsPerformed",
    "r2ReadsPerformed",
    "r2WritesPerformed",
    "holdoutAccessed",
    "backtestAdmissionAuthorized",
    "tradePlanAuthorized",
    "realMoneyOrderAuthorized",
    "liveTradingAuthorized"
  ];
  return requiredFalse.every(key => boundary[key] === false)
    && Array.isArray(evidence.positions)
    && Array.isArray(evidence.backtests);
}

function renderResearchEvidence(evidence) {
  const safe = researchEvidenceIsSafe(evidence);
  const positions = safe ? evidence.positions : [];
  const backtests = safe ? evidence.backtests : [];
  const positionsState = safe ? String(evidence.positionsState || "NOT_READY") : "NOT_READY";
  const backtestsState = safe ? String(evidence.backtestsState || "NOT_AUTHORIZED") : "NOT_AUTHORIZED";
  const positionsBadge = document.querySelector("#positions-state");
  const backtestsBadge = document.querySelector("#backtests-state");
  const evidenceTime = document.querySelector("#evidence-generated-at");
  if (positionsBadge) {
    positionsBadge.textContent = displayStatus(positionsState);
    positionsBadge.className = `badge ${badgeClass(positionsState)}`;
  }
  if (backtestsBadge) {
    backtestsBadge.textContent = displayStatus(backtestsState);
    backtestsBadge.className = `badge ${badgeClass(backtestsState)}`;
  }
  if (evidenceTime) {
    evidenceTime.textContent = `研究投影：${safe ? formatTrustedTime(evidence.projectedAtUtc) : "資料契約未通過"}`;
  }

  const positionsRoot = document.querySelector("#paper-position-table");
  if (positionsRoot) {
    positionsRoot.innerHTML = positions.length ? positions.map(item => `
      <tr>
        <td><strong>${escapeHtml(item.symbol)}</strong></td>
        <td>${escapeHtml(item.side)}</td>
        <td><time>${formatTradeTime(item.openedAtUtc ?? item.opened_at_utc)}</time></td>
        <td>${number(item.entryPrice ?? item.entry_price, 8)}</td>
        <td>${number(item.referencePrice ?? item.reference_price, 8)}</td>
        <td class="${Number(item.unrealizedPnlUsd ?? item.unrealized_pnl_usd) >= 0 ? "cell-pass" : "cell-pending"}">${number(item.unrealizedPnlUsd ?? item.unrealized_pnl_usd)} USD</td>
        <td>${number(item.stopPrice ?? item.stop_price, 8)}</td>
        <td>${escapeHtml(item.lifecycleState ?? item.lifecycle_state)}</td>
      </tr>`).join("") : '<tr><td colspan="8">目前尚無正式模擬持倉資料；未提供資料時不推算持倉。</td></tr>';
  }

  const backtestsRoot = document.querySelector("#backtest-table");
  if (backtestsRoot) {
    backtestsRoot.innerHTML = backtests.length ? backtests.map(item => `
      <tr>
        <td><strong>${escapeHtml(item.name)}</strong></td>
        <td>${escapeHtml(item.provider)}</td>
        <td>${escapeHtml(item.datasetAuthority)}</td>
        <td>${escapeHtml(item.period)}</td>
        <td>${escapeHtml(item.strategyVersion)}</td>
        <td><code>${escapeHtml(item.runSha)}</code></td>
        <td><span class="badge ${badgeClass(item.admission)}">${escapeHtml(displayStatus(item.admission))}</span></td>
        <td>${escapeHtml(item.resultStatus)}</td>
      </tr>`).join("") : '<tr><td colspan="8">目前沒有取得正式 backtest admission 的證據；不從其他研究結果自行推定。</td></tr>';
  }
}

function renderStrategy(projection) {
  if (!projection || projection.schema !== "qookey-dashboard-strategy-projection-v0.1") return;
  if (projection.authority !== false) throw new Error("Strategy projection must remain non-authoritative");
  const boundary = projection.safetyBoundary || {};
  if (Object.values(boundary).some(value => value !== false)) {
    throw new Error("Strategy projection safety boundary rejected");
  }
  const strategy = projection.baseline || {};
  const setText = (id, value) => {
    const element = document.querySelector(`#${id}`);
    if (element) element.textContent = value;
  };
  const timeframes = strategy.timeframes || {};
  const sstate = strategy.sstate || {};
  const score = strategy.score || {};
  const risk = strategy.risk || {};
  const exit = strategy.exit || {};
  const direction = String(strategy.direction || "LONG_ONLY");
  setText("strategy-name", strategy.name || "SState Intraday Wave");
  setText("strategy-mode", `${String(strategy.mode || "paper").toUpperCase()} · ${direction}`);
  setText("strategy-version", `V${strategy.version || "0.1.0"} · Repository config`);
  setText("strategy-context-timeframe", timeframes.market_context || "4H");
  setText("strategy-setup-timeframe", timeframes.setup || "60M");
  setText("strategy-entry-timeframe", timeframes.entry || "15M");
  setText("strategy-states", (sstate.allowed_states || []).join(" · "));
  setText("strategy-probability", `${number(Number(sstate.minimum_probability || 0) * 100, 0)}%`);
  setText("strategy-samples", number(sstate.minimum_samples, 0));
  setText("strategy-min-score", number(score.minimum_entry_score, 0));
  setText("strategy-risk", `${number(Number(risk.risk_fraction_per_trade || 0) * 100, 2)}% equity`);
  setText("strategy-leverage", `${number(risk.max_leverage, 1)}x`);
  setText("strategy-daily-trades", `${number(strategy.max_new_trades_per_day, 0)} 筆`);
  setText("strategy-daily-loss", `-${number(risk.daily_loss_limit_r, 0)}R`);
  setText("strategy-partial", `+${number(exit.partial_at_r, 1)}R · ${number(Number(exit.partial_fraction || 0) * 100, 0)}%`);
  setText("strategy-runner", `${number(Number(exit.runner_fraction || 0) * 100, 0)}%`);
  setText("strategy-holding", `${number(exit.max_holding_hours, 0)} 小時`);

  const labels = {
    sstate_quality: "SState 品質",
    historical_probability: "歷史機率",
    trend_1h: "1H 趨勢",
    entry_15m: "15m 進場",
    reward_risk: "報酬／風險",
    liquidity_funding: "流動性／Funding"
  };
  const root = document.querySelector("#strategy-score-list");
  if (root) {
    root.innerHTML = Object.entries(score.weights || {}).map(([key, value]) => `
      <div class="strategy-score-row">
        <span>${escapeHtml(labels[key] || key)}</span>
        <progress class="strategy-score-progress" max="100" value="${Math.max(0, Math.min(100, Number(value) || 0))}" aria-label="${escapeHtml(labels[key] || key)}權重"></progress>
        <strong>${number(value, 0)}</strong>
      </div>
    `).join("");
  }
  const summary = projection.summary || {};
  const researchLayer = (projection.analysisLayers || []).find(layer => layer.id === "research_loop") || {};
  const status = String(researchLayer.status || "NOT_READY");
  setText(
    "strategy-research-status",
    status === "PREPARED_RESEARCH_ONLY" ? "PREPARED · SYNTHETIC ONLY" : displayStatus(status)
  );
  setText("strategy-research-candidates", number(summary.candidateCount, 0));
  setText("strategy-research-families", number(summary.familyCount, 0));
  setText("strategy-research-horizons", number(summary.horizonCount, 0));
  setText("strategy-edge-methods", number(summary.edgeMethodCount, 0));
  const layers = document.querySelector("#strategy-analysis-layers");
  if (layers) {
    layers.innerHTML = (projection.analysisLayers || []).map(layer => `
      <div class="analysis-layer">
        <div>
          <strong>${escapeHtml(layer.name)}</strong>
          <small>${escapeHtml(layer.detail)}</small>
        </div>
        <span class="badge ${badgeClass(String(layer.status || "NOT_READY"))}">${escapeHtml(layer.status || "NOT_READY")}</span>
      </div>
    `).join("");
  }
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
  document.querySelector("#dashboard-generated-at").textContent =
    `投影建立：${formatTrustedTime(data.generatedAtUtc)}`;
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
  const refreshButton = document.querySelector("#refresh-button");
  refreshButton?.setAttribute("aria-busy", "true");
  if (refreshButton) refreshButton.disabled = true;
  try {
    const data = await fetchJson("./data/dashboard.json");
    let operational = null;
    let paperTraining = null;
    let researchEvidence = null;
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
    try {
      researchEvidence = await fetchJson("./data/research-evidence.json");
      if (!researchEvidenceIsSafe(researchEvidence)) throw new Error("Research evidence contract rejected");
    } catch (error) {
      console.warn("Research evidence projection unavailable", error);
    }
    try {
      const strategy = await fetchJson("./data/strategy.json");
      renderStrategy(strategy);
    } catch (error) {
      console.warn("Strategy projection unavailable", error);
    }
    try {
      const calendar = await fetchJson("./data/research-calendar.json");
      if (calendar.authority !== false) throw new Error("Calendar projection must remain non-authoritative");
      renderCalendar(calendar);
    } catch (error) {
      console.warn("Research calendar projection unavailable", error);
      renderCalendar(null);
    }
    render(mergeOperationalStatus(data, operational));
    renderPaperTraining(paperTraining);
    renderResearchEvidence(researchEvidence);
  } catch (error) {
    console.error("Dashboard snapshot load failed", error);
    render(FALLBACK);
    renderCalendar(null);
    renderPaperTraining(null);
    renderResearchEvidence(null);
    document.querySelector("#snapshot-label").textContent = "狀態快照暫時無法讀取";
  } finally {
    refreshButton?.removeAttribute("aria-busy");
    if (refreshButton) refreshButton.disabled = false;
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

function viewFromLocation() {
  const requested = window.location.hash.replace(/^#/, "");
  return Object.hasOwn(titles, requested) ? requested : "overview";
}

function activateView(view, { updateHistory = false } = {}) {
  const target = document.querySelector(`#view-${view}`);
  if (!target) return;
  const isOverview = view === "overview";
  document.body.classList.toggle("subview-active", !isOverview);
  document.querySelectorAll(".nav-item").forEach(item => {
    const active = item.dataset.view === view;
    item.classList.toggle("active", active);
    if (active) item.setAttribute("aria-current", "page");
    else item.removeAttribute("aria-current");
    if (active) item.scrollIntoView({ block: "nearest", inline: "center" });
  });
  document.querySelectorAll(".view").forEach(item => item.classList.remove("active"));
  target.classList.add("active");
  document.querySelector("#page-title").textContent = titles[view] || view;
  document.title = `${titles[view] || view}｜Qookey Crypto Autopilot`;
  if (updateHistory) {
    const targetUrl = view === "overview"
      ? `${window.location.pathname}${window.location.search}`
      : `#${view}`;
    window.history.pushState({ view }, "", targetUrl);
  }
  window.scrollTo({ top: 0, left: 0, behavior: "auto" });
}

document.querySelectorAll(".nav-item, .view-link").forEach(button => {
  button.addEventListener("click", event => {
    event.preventDefault();
    activateView(button.dataset.view, { updateHistory: true });
  });
});

document.querySelectorAll(".table-wrap").forEach((wrap, index) => {
  const title = wrap.closest(".panel")?.querySelector("h3")?.textContent?.trim() || `資料表 ${index + 1}`;
  wrap.tabIndex = 0;
  wrap.setAttribute("role", "region");
  wrap.setAttribute("aria-label", `${title}；在較窄的畫面可左右滑動查看完整欄位。`);
});

window.addEventListener("popstate", () => activateView(viewFromLocation()));
window.addEventListener("hashchange", () => activateView(viewFromLocation()));
document.querySelector("#refresh-button").addEventListener("click", loadData);
activateView(viewFromLocation());
loadData();
