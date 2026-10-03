const FALLBACK = {
  snapshotLabel: "安全空白資料快照",
  project: { marketCount: null, fundingMonths: null },
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
  ACTIVE: "運作中 · ACTIVE",
  ACTIVE_BACKSTOP: "運作中 · 補查",
  SCHEDULED_READ_ONLY: "已排程 · 唯讀",
  ACTIVE_CONTENT_HASH_DEDUP: "運作中 · 內容去重",
  ACTIVE_UNTIL_ORIGINAL_EXPIRY: "運作中 · 原期限",
  COMPLETE_CRON_RETIREMENT_PENDING: "已完成 · 待退役排程",
  RETIRED_COMPLETE_MANUAL_REPAIR_ONLY: "已完成 · 排程退役",
  SCHEDULED_NEEDS_FINGERPRINT_DEDUPE: "已排程 · 待指紋去重",
  ACTIVE_FINGERPRINT_DEDUP: "運作中 · 指紋去重",
  WAITING_SCHEDULE_AUTHORITY: "等待排程授權",
  WAITING_EXECUTION_AUTHORITY: "等待執行授權",
  PLANNED_NOT_SCHEDULED: "規劃中 · 未排程",
  WAITING_FIRST_RUN: "等待首次執行 · WAITING_FIRST_RUN",
  BASELINE_CREATED: "基準已建立 · BASELINE_CREATED",
  PREPARED: "已準備 · PREPARED",
  PAPER_BASELINE: "舊 Paper 基線",
  RESEARCH_ONLY: "研究限定",
  PREPARED_RESEARCH_ONLY: "已準備 · 研究限定",
  PREPARED_NOT_ACTIVE: "已準備 · 未啟用",
  FRAMEWORK_ONLY: "僅框架",
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
  if (["PASS", "READY", "AUTHORIZED", "BASELINE_CREATED", "ACTIVE", "ACTIVE_BACKSTOP", "SCHEDULED_READ_ONLY", "ACTIVE_CONTENT_HASH_DEDUP", "ACTIVE_UNTIL_ORIGINAL_EXPIRY", "RETIRED_COMPLETE_MANUAL_REPAIR_ONLY", "ACTIVE_FINGERPRINT_DEDUP"].includes(status)) return "pass";
  if (["PREPARED", "PAPER_BASELINE", "RESEARCH_ONLY", "PREPARED_RESEARCH_ONLY", "PREPARED_NOT_ACTIVE", "FRAMEWORK_ONLY", "WAITING_AUTHORITY", "WAITING_FIRST_RUN", "PENDING", "IN_PROGRESS", "NOT_READY", "REVIEW_REQUIRED", "SCOPE_REDUCTION_REQUIRED", "COMPLETE_CRON_RETIREMENT_PENDING", "SCHEDULED_NEEDS_FINGERPRINT_DEDUPE", "WAITING_SCHEDULE_AUTHORITY", "WAITING_EXECUTION_AUTHORITY", "PLANNED_NOT_SCHEDULED"].includes(status)) return "pending";
  if (["BLOCKED", "NOT_AUTHORIZED", "FAIL"].includes(status)) return "danger";
  return "neutral";
}

function displayStatus(status) {
  return STATUS_LABELS[status] || status;
}

function statusDot(status) {
  const className = ["PASS", "READY", "AUTHORIZED", "ACTIVE", "ACTIVE_BACKSTOP", "SCHEDULED_READ_ONLY", "ACTIVE_CONTENT_HASH_DEDUP", "ACTIVE_UNTIL_ORIGINAL_EXPIRY", "RETIRED_COMPLETE_MANUAL_REPAIR_ONLY", "ACTIVE_FINGERPRINT_DEDUP"].includes(status) ? "safe" : "";
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

function alternativeAssetsProjectionIsSafe(projection) {
  if (!projection || projection.schema !== "qookey-pionex-alternative-assets-projection-v0.2") return false;
  if (projection.authority !== false || projection.mode !== "METADATA_ONLY_READ_ONLY") return false;
  const boundary = projection.safety_boundary || {};
  if (!Object.keys(boundary).length || Object.values(boundary).some(value => value !== false)) return false;
  const actual = projection.actual_catalog;
  return actual === null || (typeof actual === "object" && !Array.isArray(actual) && !("markets" in actual));
}

function renderAlternativeAssets(projection) {
  const safe = alternativeAssetsProjectionIsSafe(projection);
  const status = safe ? String(projection.status || "WAITING_FIRST_RUN") : "NOT_READY";
  const registry = safe ? (projection.candidate_registry || {}) : {};
  const counts = registry.counts_by_class || {};
  const actual = safe ? projection.actual_catalog : null;
  const reference = safe
    ? projection.capacity_candidate_max?.scenarios?.reference?.canonical_gb
    : null;
  const setText = (id, value) => {
    const element = document.querySelector(`#${id}`);
    if (element) element.textContent = value;
  };
  const badge = document.querySelector("#alternative-assets-status");
  if (badge) {
    badge.textContent = displayStatus(status);
    badge.className = `badge ${badgeClass(status)}`;
  }
  if (!safe) {
    for (const id of [
      "alternative-assets-candidates",
      "alternative-assets-matched",
      "alternative-assets-equity",
      "alternative-assets-funds",
      "alternative-assets-metals",
      "alternative-assets-capacity",
    ]) {
      setText(id, "—");
    }
    setText("alternative-assets-observed-at", "目錄觀測：暫不可核實");
    setText(
      "alternative-assets-note",
      "Alternative-assets projection 暫不可核實；不以 0 代替缺少資料。"
    );
    return;
  }
  setText("alternative-assets-candidates", number(registry.total, 0));
  setText("alternative-assets-matched", number(actual?.matched_market_count, 0));
  setText("alternative-assets-equity", number(counts.us_equity_token, 0));
  setText("alternative-assets-funds", number(counts.etf_or_fund_token, 0));
  setText("alternative-assets-metals", number(counts.metal_or_other_asset, 0));
  setText(
    "alternative-assets-capacity",
    Number.isFinite(Number(reference)) ? `${number(reference, 2)} GB` : "—"
  );
  setText(
    "alternative-assets-observed-at",
    `目錄觀測：${actual ? formatTrustedTime(actual.observed_at_utc) : "尚未執行"}`
  );
  const nextRun = safe ? formatTrustedTime(projection.next_scheduled_run_utc) : "尚未提供";
  const actualNote = actual
    ? `本次新增 ${number(actual.added_count, 0)}、缺席 ${number(actual.removed_count, 0)}；缺席不等於下架。`
    : "實際交集會在首輪 Pionex metadata 驗證後產生。";
  setText(
    "alternative-assets-note",
    `下一次排程：${nextRun}；${actualNote} 容量只是規劃估算，未授權下載 K 線。`
  );
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


function operationsScheduleIsSafe(projection) {
  if (!projection || projection.schema !== "qookey-automation-schedule-projection-v0.1") return false;
  if (projection.authority !== false || projection.timezone !== "Asia/Taipei") return false;
  if (!Array.isArray(projection.items)) return false;
  const inventory = projection.sourceStatus?.scheduleInventory;
  if (inventory) {
    const repositoryCount = Number(inventory.repositoryScheduledWorkflowCount);
    const monitoredCount = Number(inventory.monitoredScheduledWorkflowCount);
    const projectedCount = Number(inventory.projectedScheduledJobCount);
    const effectiveCount = Number(inventory.currentEffectiveScheduledWorkflowCount);
    const expiredCount = Number(inventory.expiredFrozenCronDeclarationCount);
    const counts = [repositoryCount, monitoredCount, projectedCount, effectiveCount, expiredCount];
    if (inventory.state !== "CONVERGED_WITH_EXPIRED_FROZEN_DECLARATION"
        || !counts.every(Number.isInteger)
        || repositoryCount !== monitoredCount
        || projectedCount !== effectiveCount
        || repositoryCount !== effectiveCount + expiredCount
        || expiredCount !== 1) return false;
  }
  const boundary = projection.safetyBoundary || {};
  return Object.keys(boundary).length > 0 && Object.values(boundary).every(value => value === false);
}

function renderOperationsSchedule(projection) {
  const root = document.querySelector("#operations-schedule");
  const generated = document.querySelector("#operations-schedule-generated-at");
  const sourceSummary = document.querySelector("#external-source-summary");
  const zecSummary = document.querySelector("#zec-matrix-summary");
  if (!root) return;

  if (!operationsScheduleIsSafe(projection)) {
    root.innerHTML = '<li class="calendar-loading"><strong>自動化排程暫時無法核實</strong><small>請以 Repository authority 為準</small></li>';
    if (generated) generated.textContent = "排程投影：尚未提供";
    if (sourceSummary) sourceSummary.textContent = "外部來源狀態：尚未提供";
    if (zecSummary) zecSummary.textContent = "ZEC V0.3：等待 authority";
    return;
  }

  const inventory = projection.sourceStatus?.scheduleInventory || null;
  if (generated) {
    const countText = inventory
      ? ` · Repo 宣告 ${number(inventory.repositoryScheduledWorkflowCount, 0)} / Health ${number(inventory.monitoredScheduledWorkflowCount, 0)} / 目前有效 ${number(inventory.currentEffectiveScheduledWorkflowCount, 0)} / Website ${number(inventory.projectedScheduledJobCount, 0)}`
      : "";
    generated.textContent = `排程投影：${formatTrustedTime(projection.projectionGeneratedAtUtc)}${countText}`;
  }
  const resource = projection.sourceStatus?.resourceHub || {};
  const registry = projection.sourceStatus?.externalCapabilityRegistry || {};
  const zec = projection.sourceStatus?.zecV0_3 || {};
  const baseline = String(resource.baselineCommit || "");
  if (sourceSummary) {
    sourceSummary.textContent =
      `外部來源：Resource Hub 每日唯讀追蹤 · baseline ${baseline ? baseline.slice(0, 8) : "—"} · Capability Registry ${number(registry.candidateCount, 0)} 個候選；來源不變不重評。`;
  }
  if (zecSummary) {
    zecSummary.textContent =
      `ZEC V0.3：${number(zec.completedCells, 0)}/${number(zec.expectedCells, 0)} cells · ${displayStatus(String(zec.state || "WAITING_EXECUTION_AUTHORITY"))}。`;
  }

  root.innerHTML = projection.items.map(item => `
    <li class="calendar-card">
      <div class="calendar-card-top">
        <span>${escapeHtml(item.local_schedule || "未排程")}</span>
        <span class="badge ${badgeClass(String(item.status || "NOT_READY"))}">${escapeHtml(displayStatus(String(item.status || "NOT_READY")))}</span>
      </div>
      <strong>${escapeHtml(item.title)}</strong>
      <small>${escapeHtml(item.detail)}</small>
      <em>${escapeHtml((item.trigger || []).join(" + ") || "等待新版 authority")}</em>
    </li>
  `).join("");
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
    note.textContent = "此區等待持續模擬的成交曲線；固定 BTC 樣本結果請見首頁摘要。";
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
  const authority = report?.authority || {};
  const unsafe = ["formalTradePlanAuthorized", "sourceSwitchAuthorized",
    "realMoneyOrderAuthorized", "liveTradingAuthorized"].some(key => authority[key] !== false);
  const observed = Date.parse(report?.observedAtUtc);
  if (!report || report.mode !== "PAPER_TRAINING_ONLY" ||
      report.status === "WAITING_AUTHORITY" || unsafe ||
      !Number.isFinite(observed) || observed > Date.now()) {
    if (observedAt) observedAt.textContent = "Paper 觀測：尚未完成";
    document.querySelector("#paper-training-status").textContent = "持續模擬未啟動 · 等待資料與執行授權";
    document.querySelector("#paper-training-summary").textContent = "此區顯示持續模擬；已完成的固定 BTC 樣本請見首頁摘要。";
    for (const id of ["paper-return", "paper-win-rate", "paper-profit-factor", "paper-drawdown"]) {
      document.querySelector("#" + id).textContent = "—";
    }
    document.querySelector("#paper-performance-note").textContent = "尚無可用模擬績效；不以 0% 代替缺少資料。";
    document.querySelector("#paper-signal-table").innerHTML = '<tr><td colspan="6">每日關注尚未啟動；沒有可用的當前候選。</td></tr>';
    document.querySelector("#paper-trade-table").innerHTML = '<tr><td colspan="8">尚無通過檢查的模擬成交資料。</td></tr>';
    renderEquityChart(null);
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

  const signals = Date.now() - observed <= 3600000 ? (report.latestCandidates || []) : [];
  document.querySelector("#paper-signal-table").innerHTML = signals.length ? signals.map(item => `
    <tr>
      <td><strong>${escapeHtml(item.symbol)}</strong></td>
      <td>${number(item.score)}</td>
      <td><span class="badge ${item.eligible ? "pass" : "pending"}">${item.eligible ? "候選" : "略過"}</span></td>
      <td>${number(item.reference_price, 8)}</td>
      <td>${number(item.stop_price, 8)}</td>
      <td>${number(item.target_price, 8)}</td>
    </tr>`).join("") : '<tr><td colspan="6">目前沒有新鮮且可用的候選訊號（觀測限一小時內）</td></tr>';

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
  setText("strategy-mode", `${String(strategy.mode || "paper").toUpperCase()} · Legacy baseline ${direction}`);
  setText("strategy-version", `V${strategy.version || "0.1.0"} · Legacy baseline config`);
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
  setText("strategy-research-families", number(summary.routerFamilyCount ?? summary.familyCount, 0));
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
  document.querySelector("#market-count").textContent = number(data.project?.marketCount, 0);
  const fundingMonths = data.project?.fundingMonthsObserved ?? data.project?.fundingMonths;
  document.querySelector("#funding-months").textContent = number(fundingMonths, 0);
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


function historyProgressIsSafe(progress) {
  if (!progress || progress.authority !== false || progress.provider !== "binance_usdm") return false;
  const boundary = progress.safetyBoundary || {};
  if (!Object.keys(boundary).length || Object.values(boundary).some(value => value !== false)) return false;

  if (progress.schema === "qookey-dashboard-history-progress-v0.2") {
    return progress.snapshotType === "CURRENT_OPERATIONS_PROJECTION"
      && progress.status === "COMPLETE"
      && progress.mode === "current_operations"
      && progress.shardCount === 10
      && progress.shardsComplete === 10
      && progress.historyReacquisitionRequired === false
      && Number.isInteger(progress.trainingRunId)
      && progress.modelQualityStatus === "REJECT";
  }

  if (progress.schema !== "qookey-dashboard-history-progress-v0.1") return false;
  if (progress.snapshotType !== "SECRET_FREE_GITHUB_ACTIONS_RUN_REPORT") return false;
  if (progress.status !== "IN_PROGRESS" || progress.mode !== "backfill") return false;
  if (progress.shardCount !== 10 || !Number.isInteger(progress.shardsComplete) || progress.shardsComplete < 0 || progress.shardsComplete > progress.shardCount) return false;
  if (!Number.isInteger(progress.lastShardIndex) || progress.lastShardIndex < 1 || progress.lastShardIndex > progress.shardCount) return false;
  if (typeof progress.sourceUrl !== "string" || !progress.sourceUrl.startsWith("https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/")) return false;
  return true;
}

function renderHomeSummary(data, strategy, paper, calendar, historyProgress) {
  const setText = (id, text) => {
    const element = document.getElementById(id);
    if (element) element.textContent = text;
  };
  const project = data?.project || {};
  const snapshotTime = data?.generatedAtUtc ? formatTrustedTime(data.generatedAtUtc) : "快照時間未提供";
  const paperTime = paper?.observedAtUtc ? formatTrustedTime(paper.observedAtUtc) : "時間未提供";
  setText("home-updated", snapshotTime);
  setText("home-paper-observed", `模擬觀測時間：${paperTime}`);

  const history = calendar?.items?.find(item => item.id === "detailed-history-backfill" || item.title === "Crypto Core 100 歷史回補" || item.detail?.includes("10 個可續跑分片"));
  const historyAuthorized = Boolean(history && String(history.status || "").startsWith("AUTHORIZED"));
  const historySnapshotSafe = historyProgressIsSafe(historyProgress);
  const currentHistoryComplete = project.core100HistoryState === "COMPLETE_10_OF_10"
    || (historySnapshotSafe && historyProgress.status === "COMPLETE" && historyProgress.shardsComplete === 10);
  const historySource = document.querySelector("#home-history-source");
  if (currentHistoryComplete) {
    const trainingRunId = project.core100TrainingRunId ?? historyProgress?.trainingRunId;
    setText("home-history-state", "10/10 分片 · COMPLETE");
    setText(
      "home-history-detail",
      trainingRunId
        ? `Core100 歷史資料已完成；Training run ${trainingRunId} 已完成。Model Quality REJECT 不會自動重啟歷史資料取得。`
        : "Core100 歷史資料已完成；Model Quality REJECT 不會自動重啟歷史資料取得。"
    );
    if (historySource) {
      historySource.href = "https://github.com/qookey109-pixel/crypto-autopilot/blob/main/CURRENT_STATUS.md";
      historySource.textContent = "查看 Current Status ↗";
    }
  } else if (historySnapshotSafe && historyProgress.status === "IN_PROGRESS") {
    setText("home-history-state", `${historyProgress.shardsComplete}/${historyProgress.shardCount} 分片 · 進行中`);
    setText("home-history-detail", `最後核實分片 #${historyProgress.lastShardIndex}；${formatTrustedTime(historyProgress.observedAtUtc)} 的 GitHub Actions 報告快照，不是即時 R2 查詢。`);
    if (historySource) {
      historySource.href = historyProgress.sourceUrl;
      historySource.textContent = "查看最後核實報告 ↗";
    }
  } else {
    setText("home-history-state", historyAuthorized ? "已授權 · 完成數待核對" : "狀態待核實");
    setText("home-history-detail", historyAuthorized
      ? "Crypto Core 100 依固定 10 分片由雲端補齊；首頁不宣稱未核對的完成數。"
      : "無法由目前安全投影核實歷史補齊狀態，請查看雲端執行紀錄。");
    if (historySource) {
      historySource.href = "https://github.com/qookey109-pixel/crypto-autopilot/actions/workflows/binance-usdm-detailed-history-v0-1.yml";
      historySource.textContent = "查看雲端補齊紀錄 ↗";
    }
  }

  const safe = strategy?.schema === "qookey-dashboard-strategy-projection-v0.1"
    && strategy.authority === false
    && strategy.safetyBoundary
    && Object.keys(strategy.safetyBoundary).length > 0
    && Object.values(strategy.safetyBoundary).every(value => value === false);
  const research = safe ? strategy.analysisLayers?.find(layer => layer.id === "research_loop") : null;
  const researchStatus = research?.status || project.strategyResearchLoopState;
  if (researchStatus === "PREPARED_RESEARCH_ONLY") {
    const summary = strategy?.summary || {};
    const routerFamilyCount = summary.routerFamilyCount ?? summary.familyCount;
    const counts = [summary.candidateCount, routerFamilyCount, summary.horizonCount, summary.edgeMethodCount];
    const hasCounts = counts.every(value => Number.isFinite(value));
    setText("home-research-state", "框架就緒，實績待驗證");
    setText("home-research-detail", hasCounts
      ? `${summary.candidateCount} 個研究候選 · ${routerFamilyCount} 個 Router 策略家族 · ${summary.horizonCount} 個週期 · ${summary.edgeMethodCount} 種驗證；僅 research / paper 語意。`
      : "目前以合成資料驗證研究流程；尚無可據以推薦投資的實際策略成果。");
  } else {
    setText("home-research-state", safe ? "查看最新研究紀錄" : "研究資料暫不可用");
    setText("home-research-detail", safe
      ? "策略頁保留目前的研究狀態與驗證條件。"
      : "無法核實目前研究狀態，請稍後重新整理。");
  }

  const candidates = Array.isArray(paper?.latestCandidates) ? paper.latestCandidates : [];
  const paperReady = paper?.status === "READY" && paper?.authority?.paperCandidateGenerationAuthorized === true;
  setText("home-candidate-state", paperReady && candidates.length > 0 ? `已產生 ${candidates.length} 筆模擬候選` : "尚無核實的每日推薦");
  setText("home-candidate-detail", paperReady && candidates.length > 0
    ? "候選僅供 Paper 研究觀測，不等同投資建議或交易計畫。"
    : "目前模擬候選生成尚未取得授權；網站不會把研究候選冒充每日投資推薦。");
}

function renderCloudRuns(report) {
  const list = document.getElementById("cloud-run-list");
  const time = document.getElementById("cloud-run-updated");
  if (!list || !time) return;
  list.replaceChildren();

  const observed = Date.parse(report?.observedAtUtc);
  const future = Number.isFinite(observed) && observed > Date.now() + 300000;
  const legacy = report?.schema === "qookey-cloud-run-status-v0.1"
    && report.authority === false
    && report.simulationReady === false;
  const boundary = report?.safetyBoundary || {};
  const modern = report?.schema === "qookey-cloud-run-status-v0.2"
    && report.authority === false
    && report.mode === "GITHUB_ACTIONS_METADATA_ONLY"
    && Array.isArray(report.items)
    && Object.keys(boundary).length > 0
    && Object.values(boundary).every(value => value === false);

  if ((!legacy && !modern) || !Number.isFinite(observed) || future) {
    time.textContent = "雲端狀態暫不可核實，請查看 GitHub 執行紀錄。";
    return;
  }

  const stale = Date.now() - observed > 30 * 60 * 60 * 1000;
  if (modern) {
    const summary = report.summary || {};
    const declared = Number(summary.repositoryCronDeclarationCount);
    const monitored = Number(summary.monitoredCronDeclarationCount);
    const effective = Number(summary.currentEffectiveScheduleCount);
    const expired = Number(
      summary.expiredScheduleCount ?? summary.expiredFrozenCronDeclarationCount
    );
    const pending = Number(summary.pendingScheduleCount ?? 0);
    const frozenExpired = Number(summary.expiredFrozenCronDeclarationCount);
    if (![declared, monitored, effective, expired, pending, frozenExpired]
          .every(Number.isInteger)
        || declared !== monitored
        || declared !== effective + expired + pending
        || frozenExpired > expired
        || report.items.length !== declared) {
      time.textContent = "雲端狀態暫不可核實：排程 inventory 不一致。";
      return;
    }
    const pendingText = pending > 0 ? ` / 待開始 ${pending}` : "";
    time.textContent =
      `${stale ? "較舊快照" : "最後核對"}：${formatTrustedTime(report.observedAtUtc)} · 宣告 ${declared} / 監控 ${monitored} / 有效 ${effective} / 到期 ${expired}${pendingText}。`;

    const states = {
      WORKFLOW_SUCCESS: "流程成功",
      WORKFLOW_FAILED: "流程失敗",
      RUNNING: "執行或排隊中",
      CANCELLED: "已取消",
      TIMED_OUT: "逾時",
      SKIPPED: "已略過",
      UNVERIFIED: "待核實"
    };
    const freshness = {
      FRESH: "新鮮",
      STALE: "已過 freshness",
      RUNNING: "執行中",
      WAITING_FIRST_SCHEDULE: "等待首次自然排程",
      NO_AUTOMATIC_RUN: "尚無自動 run",
      EXPIRED_WINDOW: "時窗已結束",
      NOT_APPLICABLE: "不適用",
      UNVERIFIED: "待核實"
    };

    for (const row of report.items) {
      const latest = row?.latestAutomaticRun || {};
      const item = document.createElement("li");
      item.className = "cloud-run-card";

      const title = document.createElement("strong");
      title.textContent = String(row?.title || row?.workflow || "未命名 workflow");
      item.append(title);

      const authority = document.createElement("small");
      authority.textContent =
        `Job ${String(row?.operationId || "—")} · Authority ${String(row?.authorityState || "—")} · ${String(row?.lifecycleState || "—")}`;
      item.append(authority);

      const run = document.createElement("small");
      const runId = Number.isInteger(latest.runId) ? `#${latest.runId}` : "—";
      const sha = typeof latest.headSha === "string" && /^[0-9a-f]{40}$/.test(latest.headSha)
        ? latest.headSha.slice(0, 8) : "—";
      run.textContent =
        `Latest automatic run ${runId} · SHA ${sha} · ${states[latest.state] || "待核實"} · ${freshness[row?.freshnessState] || "待核實"}`;
      item.append(run);

      const evidence = document.createElement("small");
      evidence.textContent =
        `Evidence ${latest.evidenceTimeUtc ? formatTrustedTime(latest.evidenceTimeUtc) : "尚未提供"}`;
      item.append(evidence);

      const business = document.createElement("small");
      business.className = "cloud-run-business";
      business.textContent = row?.businessResult?.status === "UNKNOWN_FROM_GITHUB_RUN_METADATA"
        ? "Business result：GitHub run metadata 無法判定；需另讀正式 artifact / receipt。"
        : "Business result：待核實。";
      item.append(business);

      const links = document.createElement("span");
      links.className = "cloud-run-links";
      const safeRunUrl = typeof latest.sourceUrl === "string"
        && /^https:\/\/github\.com\/qookey109-pixel\/crypto-autopilot\/actions\/runs\/[0-9]+$/.test(latest.sourceUrl);
      if (safeRunUrl) {
        const runLink = document.createElement("a");
        runLink.textContent = "Run ↗";
        runLink.href = latest.sourceUrl;
        runLink.target = "_blank";
        runLink.rel = "noopener noreferrer";
        links.append(runLink);
      }
      const safeAuthorityUrl = typeof row?.authorityUrl === "string"
        && /^https:\/\/github\.com\/qookey109-pixel\/crypto-autopilot\/blob\/main\/[A-Za-z0-9._\/-]+$/.test(row.authorityUrl);
      if (safeAuthorityUrl) {
        const authorityLink = document.createElement("a");
        authorityLink.textContent = "Authority ↗";
        authorityLink.href = row.authorityUrl;
        authorityLink.target = "_blank";
        authorityLink.rel = "noopener noreferrer";
        links.append(authorityLink);
      }
      item.append(links);
      list.append(item);
    }
    for (const row of report.diagnosticRuns || []) {
      const latest = row?.latestRun || {};
      const item = document.createElement("li");
      item.className = "cloud-run-card";

      const title = document.createElement("strong");
      title.textContent = String(row?.title || "Cloud 診斷 workflow");
      item.append(title);

      const runId = Number.isInteger(latest.runId) ? `#${latest.runId}` : "尚無 run";
      const attempt = Number.isInteger(latest.runAttempt) ? latest.runAttempt : "—";
      const state = {
        WORKFLOW_SUCCESS: "workflow 成功",
        WORKFLOW_FAILED: "workflow 失敗",
        RUNNING: "執行或排隊中",
        CANCELLED: "已取消",
        TIMED_OUT: "逾時",
        SKIPPED: "已略過",
        QUERY_FAILED: "GitHub 查詢失敗",
        NO_RUN: "尚無可核實 run",
        UNVERIFIED: "待核實"
      }[latest.state] || "待核實";
      const run = document.createElement("small");
      run.textContent = `最新 GitHub 執行 ${runId} · attempt ${attempt} · ${state}`;
      item.append(run);

      const evidence = document.createElement("small");
      evidence.textContent = `建立時間 ${latest.createdAtUtc ? formatTrustedTime(latest.createdAtUtc) : "尚未提供"} · 僅含 GitHub run metadata，不含帳務報告內容`;
      item.append(evidence);

      const links = document.createElement("span");
      links.className = "cloud-run-links";
      const safeRunUrl = typeof latest.sourceUrl === "string"
        && /^https:\/\/github\.com\/qookey109-pixel\/crypto-autopilot\/actions\/runs\/[0-9]+$/.test(latest.sourceUrl);
      if (safeRunUrl) {
        const runLink = document.createElement("a");
        runLink.textContent = "查看 workflow / 報告 ↗";
        runLink.href = latest.sourceUrl;
        runLink.target = "_blank";
        runLink.rel = "noopener noreferrer";
        links.append(runLink);
      }
      item.append(links);
      list.append(item);
    }

    if (!report.items.length) {
      const empty = document.createElement("li");
      empty.textContent = "目前沒有可核實的自動排程執行資料。";
      list.append(empty);
    }
    return;
  }

  // V0.1 compatibility for previously deployed snapshots.
  time.textContent = `${stale ? "較舊快照" : "最後核對"}：${formatTrustedTime(report.observedAtUtc)}。作業完成後由雲端更新。`;
  const labels = {
    history: "Binance 歷史補齊",
    reach: "Pionex 歷史探測",
    universe: "Pionex 候選池",
    funding: "Pionex Funding",
    health: "排程健康",
    simulation: "BTC 模擬測試"
  };
  const states = {
    WORKFLOW_SUCCESS: "流程成功",
    WORKFLOW_FAILED: "需修復",
    RUNNING: "執行或排隊中",
    CANCELLED: "已取消",
    TIMED_OUT: "逾時",
    UNVERIFIED: "待核實"
  };
  for (const [key, label] of Object.entries(labels)) {
    const row = report.runs?.[key] || {};
    const item = document.createElement("li");
    const link = document.createElement("a");
    const safeUrl = typeof row.sourceUrl === "string"
      && /^https:\/\/github\.com\/qookey109-pixel\/crypto-autopilot\/actions\/runs\/[0-9]+$/.test(row.sourceUrl);
    link.textContent = `${label} · ${states[row.state] || "待核實"}`;
    if (safeUrl) {
      link.href = row.sourceUrl;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    }
    item.append(link);
    list.append(item);
  }
}

function cloudPaperUsageVersion(budget) {
  const contracts = {
    "cloud_paper_usage_audit_v0_2": {
      "version": "V0.2",
      "budget_state": "REVIEW_REQUIRED_V0_2_DATASET_COVERAGE_INCOMPLETE",
      "d1_state": "UNKNOWN_EMPTY_UNVERIFIED",
      "fields": {
        "authority": "cloud_paper_usage_audit_v0_2",
        "status": "REVIEW_REQUIRED",
        "reason_code": "DATASET_COVERAGE_INCOMPLETE",
        "run_id": 36584465739,
        "attempt": 1,
        "run_head_sha": "21d37a44c6f3c5bba340908705488a05e7a5f7c7",
        "artifact_id": 11041290995,
        "artifact_name": "cloud-paper-usage-audit-v0-2-36584465739-1",
        "artifact_sha256": "9ece6ff0a937f930d1137b2539052833bb5d94960dff8c1e50cce4cdbdadc258",
        "cloudflare_requests": 1,
        "d1_rows_state": "EMPTY_UNVERIFIED",
        "d1_storage_state": "EMPTY_UNVERIFIED",
        "r2_operations_state": "LIMIT_REACHED",
        "r2_operations_group_count": 10000,
        "r2_storage_state": "PRESENT",
        "r2_storage_group_count": 1297,
        "account_wide_cost": "UNKNOWN",
        "complete_storage_byte_aggregate": "UNKNOWN",
        "shared_writer_coverage": "UNKNOWN",
        "storage_headroom": "UNKNOWN"
      }
    },
    "cloud-paper-r2-usage-audit-v0.3": {
      "version": "V0.3",
      "budget_state": "REVIEW_REQUIRED_V0_3_R2_METRICS_PARTIAL",
      "d1_state": "UNKNOWN_NOT_QUERIED_BY_V0_3",
      "fields": {
        "authority": "cloud-paper-r2-usage-audit-v0.3",
        "status": "READY_FOR_REVIEW",
        "reason_code": "R2_METRICS_CAPTURED_REVIEW_ONLY",
        "run_id": 36593296360,
        "attempt": 1,
        "run_head_sha": "2516a80c32fa04b9789bef379b108eb50c87fd49",
        "artifact_id": 11045150561,
        "artifact_name": "cloud-paper-r2-usage-audit-v0-3-36593296360-1",
        "artifact_sha256": "581514f59892b84520e52ef463e00210e4175952cc0d54af7fda42b18c71c1be",
        "cloudflare_requests": 1,
        "d1_rows_state": "NOT_QUERIED_IN_V0_3",
        "d1_storage_state": "NOT_QUERIED_IN_V0_3",
        "r2_operations_state": "PRESENT",
        "r2_operations_group_count": 6,
        "r2_operations_total_requests": 125309,
        "r2_operations_freshness": "UNKNOWN_QUERY_OMITS_DATETIME_DIMENSION",
        "r2_storage_state": "PRESENT",
        "r2_storage_group_count": 1298,
        "returned_bucket_group_count": 1,
        "object_count": 16304,
        "payload_bytes": 612538247,
        "metadata_bytes": 4003533,
        "total_bytes": 616541780,
        "upload_count": 0,
        "latest_snapshot_utc": "2026-09-29T15:20:00Z",
        "account_wide_cost": "UNKNOWN",
        "complete_storage_byte_aggregate": "UNKNOWN",
        "shared_writer_coverage": "UNKNOWN",
        "storage_headroom": "UNKNOWN"
      }
    }
  };
  const evidence = budget?.usage_audit_evidence;
  const contract = evidence && Object.hasOwn(contracts, evidence.authority) ? contracts[evidence.authority] : null;
  if (!contract || !Object.entries(contract.fields).every(([key, value]) => evidence[key] === value)) return null;
  if (budget.monthly_budget_usd !== 0 || budget.state !== "BLOCKED_BUDGET"
    || budget.account_wide_usage_evidence !== contract.budget_state
    || budget.d1_free_tier_usage_evidence !== contract.d1_state
    || budget.zero_cost_conclusion !== "UNKNOWN"
    || budget.account_wide_writer_coverage !== "UNKNOWN") return null;
  return contract.version;
}

function cloudPaperBillingEvidenceIsValid(evidence) {
  const subscription = evidence?.subscription_snapshot;
  const planReview = subscription?.rate_plan_id_documentation_check;
  const usage = evidence?.billable_usage_snapshot;
  const expected = [
    evidence?.updated_date === "2026-10-02",
    evidence?.authority === "cloud-paper-billing-evidence-v0.1",
    evidence?.total_cloudflare_http_requests === 2,
    evidence?.account_wide_cost === "UNKNOWN",
    evidence?.account_wide_writer_coverage === "UNKNOWN",
    evidence?.writer_inventory_state === "INCOMPLETE_USER_EXPECTS_ADDITIONAL_SERVICES_LATER",
    evidence?.zero_cost_conclusion === "NOT_PROVEN",
    evidence?.authority_consumed === true,
    evidence?.rerun_authorized === false,
    evidence?.cloud_paper_activation === "REMAINS_DISABLED",
    subscription?.run_id === 36513941565,
    subscription?.event === "workflow_dispatch",
    subscription?.workflow_conclusion === "success",
    subscription?.run_head_sha === "414cf9a0a3b60612f9d1e09d7c5d29d76b05455e",
    subscription?.artifact_id === 11009764477,
    subscription?.artifact_digest === "sha256:7a2d8c5dce415392614c90266ebc8e7625e40cc2e92a19bc457c8cd9fd7d3338",
    subscription?.artifact_expires_at_utc === "2026-10-06T02:43:49Z",
    subscription?.attempt === 1,
    subscription?.observed_date === "2026-10-01",
    subscription?.report_status === "READY_FOR_BILLING_REVIEW",
    subscription?.rate_plan_id === "r2_paid",
    subscription?.state === "Paid",
    subscription?.listed_price_usd === 0,
    subscription?.listed_subscription_price_total_usd === 0,
    subscription?.invoices_included === false,
    subscription?.metered_charges_included === false,
    subscription?.complete_account_product_coverage === false,
    subscription?.all_writers_established === false,
    planReview?.classification === "UNMAPPED_DOCUMENTED_ENUM_REQUIRES_REVIEW",
    planReview?.additional_cloudflare_request_performed === false,
    usage?.run_id === 36852292356,
    usage?.event === "workflow_dispatch",
    usage?.workflow_conclusion === "success",
    usage?.run_head_sha === "54c099254303512eba7f8f2b57dcd98124b17348",
    usage?.artifact_id === 11156336210,
    usage?.artifact_digest === "sha256:aafc0e4c58bdb8d25426a390c1d9689ce77324ef2c780d91e6fcc2f90c1bbcbf",
    usage?.attempt === 1,
    usage?.observed_at_utc === "2026-10-01T10:57:13.348117Z",
    usage?.report_reason_code === "USAGE_ROWS_CAPTURED_REVIEW_REQUIRED_FOR_SCOPE",
    usage?.response_row_count === 42,
    usage?.every_row_has_billed_cost_fields === true,
    usage?.reported_billed_cost_total === 0,
    usage?.currency === "USD",
    usage?.fixed_subscription_charges_included === false,
    usage?.daily_provider_data_may_lag === true,
    usage?.complete_account_usage_coverage === "UNKNOWN_UNTIL_REVIEWED",
    usage?.cloudflare_http_requests_performed === 1,
    evidence?.total_cloudflare_http_requests === 2,
    evidence?.account_wide_cost === "UNKNOWN",
    evidence?.account_wide_writer_coverage === "UNKNOWN",
    evidence?.writer_inventory_state === "INCOMPLETE_USER_EXPECTS_ADDITIONAL_SERVICES_LATER",
    evidence?.zero_cost_conclusion === "NOT_PROVEN",
    evidence?.authority_consumed === true,
    evidence?.rerun_authorized === false,
    evidence?.cloud_paper_activation === "REMAINS_DISABLED"
  ];
  return expected.every(Boolean)
    && subscription?.run_url === "https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36513941565"
    && usage?.run_url === "https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/36852292356";
}

function renderCloudPaperLoop(data) {
  const usageVersion = cloudPaperUsageVersion(data?.budget);
  const billingEvidenceValid = cloudPaperBillingEvidenceIsValid(data?.billing_evidence);
  const status = document.querySelector("#cloud-paper-status");
  const detail = document.querySelector("#cloud-paper-detail");
  const traceStatus = document.querySelector("#cloud-paper-trace-status");
  const traceDetail = document.querySelector("#cloud-paper-trace-detail");
  const set = (selector, value) => {
    const node = document.querySelector(selector);
    if (node) node.textContent = value;
  };
  const valid = data
    && data.schema === "qookey-cloud-paper-dashboard-v0.1"
    && data.authority === false
    && data.activation?.enabled === false
    && data.strategy?.registry_status === "EMPTY_NO_ELIGIBLE_STRATEGIES"
    && data.latest_run?.status === "NOT_RUN"
    && data.latest_run?.decision_trace_status === "NOT_AVAILABLE_NO_OFFICIAL_RUN"
    && data.market?.provider === "PIONEX_PUBLIC"
    && data.market?.pionex_public_market_data_api_key_required === false
    && data.market?.unavailable_fields?.includes("ALIGNED_BREADTH")
    && data.market?.breadth_coverage?.membership_state === "PREPARED_CANDIDATE_MEMBERSHIP_ONLY_COVERAGE_UNVERIFIED"
    && data.market?.breadth_coverage?.coverage_verified === false
    && data.model_quality === "REJECT"
    && usageVersion !== null
    && (billingEvidenceValid || data.billing_evidence === undefined)
    && data.budget?.reservation_guard === "PROVIDER_R2_GUARD_IMPLEMENTED_RUNTIME_NOT_ACTIVATED"
    && data.budget?.d1_reservation_ledger === "SHARED_LEDGER_CODE_PREPARED_MIGRATIONS_NOT_APPLIED_D1_NOT_PROVISIONED"
    && data.budget?.storage_capacity?.state === "USAGE_PARTIAL_BLOCKED"
    && data.budget?.storage_capacity?.usage_evidence === "PARTIAL_R2_EVIDENCE_NOT_ZERO_OR_COMPLETE"
    && data.budget?.storage_capacity?.measured_storage_bytes === null
    && data.budget?.storage_capacity?.report_object_max_bytes === 262144
    && data.budget?.storage_capacity?.per_run_growth_max_bytes === 2097152
    && data.budget?.storage_capacity?.per_utc_day_growth_max_bytes === 201326592
    && data.budget?.storage_capacity?.max_31_day_growth_bytes === 6241124352
    && data.budget?.storage_capacity?.warning_threshold_bytes === 6400000000
    && data.budget?.storage_capacity?.hard_stop_bytes === 8000000000
    && data.budget?.storage_capacity?.all_writer_coverage_proven === false
    && data.account?.initialized === false
    && data.account?.planned_initial_equity_usd === 10000
    && ["confirmed_equity_usd", "open_position_count", "realized_pnl_usd", "unrealized_pnl_usd"].every(key => data.account[key] === null)
    && data.boundary?.paper_only === true
    && ["real_money_orders", "live_trading", "holdout_access", "source_switch", "model_promotion"].every(key => data.boundary[key] === false)
    && /^[a-f0-9]{40}$/.test(data.evidence_basis_main_sha)
    && typeof data.observed_at_utc === "string" && Number.isFinite(Date.parse(data.observed_at_utc))
    && data.production?.entrypoint_workflow === "NOT_WIRED"
    && data.production?.natural_schedule === "NOT_CONFIGURED";
  if (!valid) {
    if (status) status.textContent = "無法核實";
    if (status) status.className = "badge danger";
    if (detail) detail.textContent = "循環狀態投影缺失或契約不符；不顯示為已執行。";
    if (traceStatus) {
      traceStatus.textContent = "無法核實";
      traceStatus.className = "badge danger";
    }
    if (traceDetail) traceDetail.textContent = "逐市場決策軌跡投影缺失或契約不符。";
    set("#cloud-paper-last-run", "未核實");
    set("#cloud-paper-candidates", "未核實");
    set("#cloud-paper-regime", "未核實");
    set("#cloud-paper-account", "未核實");
    set("#cloud-paper-positions", "未核實");
    set("#cloud-paper-budget", "BLOCKED_BUDGET · 無法核實");
    set("#cloud-paper-storage-capacity", "用量未知 · 不顯示為 0");
    set("#cloud-paper-evidence-observed", "投影查核時間：未核實");
    set("#cloud-paper-evidence-snapshot", "來源資料時間：未核實");
    set("#cloud-paper-billing-detail", "最新帳務快照缺失或契約不符；零費用與帳戶 writer 覆蓋仍未核實。");
    const billingRunLinks = document.querySelectorAll("#cloud-paper-billing-run, #cloud-paper-usage-run");
    billingRunLinks.forEach(link => { link.hidden = true; link.removeAttribute("href"); });
    const link = document.querySelector("#cloud-paper-evidence-run");
    if (link) { link.hidden = true; link.removeAttribute("href"); }
    return;
  }
  if (status) {
    status.textContent = "已實作 · 尚未啟用";
    status.className = "badge neutral";
  }
  if (detail) {
    const evidence = data.budget.usage_audit_evidence;
    const coverage = usageVersion === "V0.3"
      ? "R2 30 天操作共 125,309 次，操作 freshness 未知；單一回傳 bucket 有 16,304 個物件、616,541,780 bytes，D1 未查詢。"
      : "R2 操作資料達 10,000 組上限，storage 回傳 1,297 組；D1 空結果未驗證。";
    detail.textContent = `正式循環尚未啟用，沒有正式 run。${usageVersion} 部分用量查核（run ${evidence.run_id} / attempt ${evidence.attempt} / SHA ${evidence.run_head_sha}）：${coverage} 完整帳戶用量、總費用、共同 writer 與安全額度仍未知。共享 provider/R2 守門程式已實作，但 runtime 尚未啟用。D1 migrations 尚未套用且 D1 未 provision。策略登錄為空、模型品質 REJECT，不會建立倉位；已消耗查核禁止重跑。`;
  }
  if (traceStatus) {
    traceStatus.textContent = "尚無正式循環報告";
    traceStatus.className = "badge neutral";
  }
  if (traceDetail) {
    traceDetail.textContent = "最新正式 run 為 NOT_RUN；逐市場決策軌跡尚無資料。合成 CI 證據不會投影成正式市場決策。";
  }
  set("#cloud-paper-last-run", "尚未執行");
  set("#cloud-paper-candidates", "尚未執行 · 空策略登錄，沒有合格候選");
  set("#cloud-paper-regime", "REGIME_UNAVAILABLE · 缺 TOTAL3 / BTC dominance；23 市場 breadth 覆蓋未驗證");
  set("#cloud-paper-account", "尚未初始化");
  set("#cloud-paper-positions", "持倉與損益尚無正式證據");
  set("#cloud-paper-budget", `BLOCKED_BUDGET · ${usageVersion} 部分用量證據待查`);
  set("#cloud-paper-storage-capacity", usageVersion === "V0.3"
    ? "部分觀測 616,541,780 bytes（1 bucket）· 完整用量/headroom 未知 · 硬停 8.0 GB"
    : "實際 bytes/headroom 未知 · R2 1,297 組 · 硬停 8.0 GB");
  set("#cloud-paper-evidence-observed", `投影查核時間：${data.observed_at_utc} · basis ${data.evidence_basis_main_sha}`);
  set("#cloud-paper-evidence-snapshot", usageVersion === "V0.3"
    ? `來源儲存快照：${data.budget.usage_audit_evidence.latest_snapshot_utc} · 操作用量 freshness 未知`
    : "來源資料：V0.2 不完整查核；不能證明 freshness");
  const billingEvidence = data.billing_evidence;
  if (billingEvidenceValid) {
    const billing = billingEvidence.subscription_snapshot;
    const usage = billingEvidence.billable_usage_snapshot;
    set("#cloud-paper-billing-detail",
      `帳單方案查核（${billing.observed_date}）：${billing.rate_plan_id} / ${billing.state}，顯示訂閱價格 ${billing.listed_subscription_price_total_usd} USD；此 rate-plan 標籤不在目前文件列舉中，須人工釐清。帳務用量（${usage.observed_at_utc}）：42 筆回報的用量成本合計 ${usage.reported_billed_cost_total.toFixed(2)} USD，但不含固定訂閱費，且完整帳戶覆蓋未知。零費用未證明；目前寫入者盤點不完整，預期未來會新增服務。`);
    const billingRun = document.querySelector("#cloud-paper-billing-run");
    if (billingRun) {
      billingRun.href = billing.run_url;
      billingRun.hidden = false;
    }
    const usageRun = document.querySelector("#cloud-paper-usage-run");
    if (usageRun) {
      usageRun.href = usage.run_url;
      usageRun.hidden = false;
    }
  } else {
    set("#cloud-paper-billing-detail",
      "此歷史投影未包含 Cloudflare 計費快照；費用及完整帳戶 writer 覆蓋仍未知。");
    const billingRunLinks = document.querySelectorAll("#cloud-paper-billing-run, #cloud-paper-usage-run");
    billingRunLinks.forEach(link => { link.hidden = true; link.removeAttribute("href"); });
  }
  const link = document.querySelector("#cloud-paper-evidence-run");
  if (link) {
    const evidence = data.budget.usage_audit_evidence;
    link.href = `https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/${evidence.run_id}/artifacts/${evidence.artifact_id}`;
    link.textContent = `查看 ${usageVersion} 用量證據 ↗`;
    link.hidden = false;
  }
}


function renderCloudPaperReadiness(data) {
  const status = document.getElementById("cloud-paper-readiness-status");
  const list = document.getElementById("cloud-paper-readiness-list");
  const engineering = document.getElementById("cloud-paper-engineering");
  const runtime = document.getElementById("cloud-paper-runtime");
  const source = document.getElementById("cloud-paper-readiness-source");
  const link = document.getElementById("cloud-paper-engineering-run");
  if (!status || !list || !engineering || !runtime || !source || !link) return;
  // Clear the prior successful projection before validating a refresh.
  list.replaceChildren();
  link.hidden = true;
  link.removeAttribute("href");
  status.textContent = "無法核實";
  engineering.textContent = "工程驗收：未核實";
  runtime.textContent = "正式執行與排程：未核實";
  source.textContent = "啟用條件來源：未核實";
  const ids = ["ACCOUNT_COVERAGE", "COST_AND_HEADROOM", "PRODUCTION_BACKEND", "PRODUCTION_CYCLE", "NATURAL_SCHEDULE"];
  const states = ["UNCONFIRMED", "UNCONFIRMED", "UNPROVISIONED_UNVERIFIED", "NOT_RUN", "NOT_CONFIGURED"];
  const sha = value => typeof value === "string" && /^[0-9a-f]{40}$/.test(value);
  const positiveInt = value => Number.isSafeInteger(value) && value > 0;
  const safe = data?.schema === "qookey-cloud-paper-readiness-v0.1"
    && data.authority === false && data.is_latest_main_claim === false
    && data.status === "NOT_ENABLED"
    && data.source === "research/status/current-operations-v0-3.json"
    && data.evidence_kind === "REPOSITORY_STATUS_NOT_RUNTIME_EVIDENCE"
    && sha(data.evidence_basis_parent_main_sha)
    && data.engineering?.status === "SUCCESS_SYNTHETIC_ONLY"
    && sha(data.engineering.head_sha) && positiveInt(data.engineering.ci_run_id)
    && positiveInt(data.engineering.runtime_tests)
    && data.runtime?.entrypoint === "NOT_WIRED"
    && data.runtime.cycle === "NOT_RUN" && data.runtime.schedule === "NOT_CONFIGURED"
    && data.runtime.activated === false
    && data.future_writers_require_registration_before_first_write === true
    && Array.isArray(data.blockers) && data.blockers.length === ids.length
    && data.blockers.every((row, index) => row?.id === ids[index] && row.state === states[index]);
  if (!safe) return;
  status.textContent = "尚未啟用 · 5 項待完成";
  engineering.textContent = `工程驗收：${data.engineering.runtime_tests} 項整合測試通過；合成資料驗證，未代表正式帳戶已執行。`;
  runtime.textContent = "正式入口未接通；正式循環未執行；自然排程未配置。";
  const reasons = [
    "共享帳戶：目前哪些服務使用額度尚未確認；未來新增服務須先登錄並分配預算。",
    "費用與容量：完整帳戶費用、剩餘額度及資料新鮮度尚未證明；未證明不等於額度不足。",
    "保存與防重：資料庫尚未建立；實際計量、一次執行憑證與保護尚待驗證。",
    "正式循環：需先完成受控雲端驗收，確認帳戶保存、回讀與下一輪延續。",
    "自動排程：需在前述條件完成後啟用，再獨立核對首次自然執行。",
  ];
  for (const reason of reasons) {
    const item = document.createElement("li");
    item.textContent = reason;
    list.appendChild(item);
  }
  source.textContent = `啟用條件來源：Repository 狀態紀錄，依據 ${data.evidence_basis_parent_main_sha.slice(0,12)}；非行情或用量的新鮮度證據。`;
  link.href = `https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/${data.engineering.ci_run_id}`;
  link.hidden = false;
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
    let strategy = null;
    let researchCalendar = null;
    let operationsSchedule = null;
    let historyProgress = null;
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
      strategy = await fetchJson("./data/strategy.json");
      renderStrategy(strategy);
    } catch (error) {
      console.warn("Strategy projection unavailable", error);
    }
    try {
      const calendar = await fetchJson("./data/research-calendar.json");
      if (calendar.authority !== false) throw new Error("Calendar projection must remain non-authoritative");
      researchCalendar = calendar;
      renderCalendar(calendar);
    } catch (error) {
      console.warn("Research calendar projection unavailable", error);
      renderCalendar(null);
    }
    try {
      operationsSchedule = await fetchJson("./data/operations-schedule.json");
      renderOperationsSchedule(operationsSchedule);
    } catch (error) {
      console.warn("Automation schedule projection unavailable", error);
      renderOperationsSchedule(null);
    }
    try {
      const progress = await fetchJson("./data/history-progress.json");
      if (!historyProgressIsSafe(progress)) throw new Error("History progress projection contract rejected");
      historyProgress = progress;
    } catch (error) {
      console.warn("History progress projection unavailable", error);
    }
    try {
      const alternativeAssets = await fetchJson("./data/alternative-assets.json");
      renderAlternativeAssets(alternativeAssets);
    } catch (error) {
      console.warn("Alternative-assets projection unavailable", error);
      renderAlternativeAssets(null);
    }
    render(mergeOperationalStatus(data, operational));
    renderCloudPaperReadiness(data?.cloudPaperReadiness);
    renderHomeSummary(data, strategy, paperTraining, researchCalendar, historyProgress);
    renderPaperTraining(paperTraining);
    renderResearchEvidence(researchEvidence);
    try { renderCloudRuns(await fetchJson("./data/cloud-runs.json")); }
    catch { renderCloudRuns(null); }
    try { renderCloudPaperLoop(await fetchJson("./data/cloud-paper-loop.json")); }
    catch { renderCloudPaperLoop(null); }
  } catch (error) {
    console.error("Dashboard snapshot load failed", error);
    render(FALLBACK);
    renderHomeSummary(null, null, null, null, null);
    renderCloudRuns(null);
    renderCloudPaperLoop(null);
    renderCloudPaperReadiness(null);
    renderCalendar(null);
    renderOperationsSchedule(null);
    renderPaperTraining(null);
    renderResearchEvidence(null);
    renderAlternativeAssets(null);
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
