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

function renderPipeline(items) {
  const root = document.querySelector("#pipeline-list");
  root.innerHTML = items.map(item => `
    <div class="pipeline-row">
      ${statusDot(item.status)}
      <div>
        <strong>${item.name}</strong>
        <span>${item.detail}</span>
      </div>
      <span class="badge ${badgeClass(item.status)}" title="Authority 狀態碼：${item.status}">${displayStatus(item.status)}</span>
    </div>
  `).join("");
}

function renderCriticalGates(items) {
  const selected = items.filter(item => item.critical);
  const root = document.querySelector("#critical-gates");
  root.innerHTML = selected.map(item => `
    <div class="gate ${item.tone || "pending"}">
      <strong>${item.name}</strong>
      <small>${item.detail}</small>
      <span class="badge ${badgeClass(item.status)}" title="Authority 狀態碼：${item.status}">${displayStatus(item.status)}</span>
    </div>
  `).join("");
}

function renderAllGates(items) {
  const root = document.querySelector("#all-gates");
  root.innerHTML = items.map(item => `
    <div class="gate ${item.tone || "pending"}">
      <strong>${item.name}</strong>
      <small>${item.detail}</small>
      <span class="badge ${badgeClass(item.status)}" title="Authority 狀態碼：${item.status}">${displayStatus(item.status)}</span>
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
    try {
      operational = await fetchJson("./data/operational-status.json");
    } catch (error) {
      console.warn("Operational status projection unavailable", error);
    }
    render(mergeOperationalStatus(data, operational));
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

document.querySelectorAll(".nav-item").forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach(item => item.classList.remove("active"));
    document.querySelectorAll(".view").forEach(view => view.classList.remove("active"));
    button.classList.add("active");
    const view = button.dataset.view;
    document.querySelector(`#view-${view}`).classList.add("active");
    document.querySelector("#page-title").textContent = titles[view] || view;
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
});

document.querySelector("#refresh-button").addEventListener("click", loadData);
loadData();