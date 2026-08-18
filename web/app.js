const FALLBACK = {
  snapshotLabel: "Safe fixture snapshot",
  project: { marketCount: 15, fundingMonths: 1010 },
  pipeline: [],
  gates: [],
  markets: []
};

const state = { data: FALLBACK };

function badgeClass(status) {
  if (["PASS", "READY", "AUTHORIZED"].includes(status)) return "pass";
  if (["PENDING", "IN_PROGRESS", "NOT_READY"].includes(status)) return "pending";
  if (["BLOCKED", "NOT_AUTHORIZED", "FAIL"].includes(status)) return "danger";
  return "neutral";
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
      <span class="badge ${badgeClass(item.status)}">${item.status}</span>
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
      <span class="badge ${badgeClass(item.status)}">${item.status}</span>
    </div>
  `).join("");
}

function renderAllGates(items) {
  const root = document.querySelector("#all-gates");
  root.innerHTML = items.map(item => `
    <div class="gate ${item.tone || "pending"}">
      <strong>${item.name}</strong>
      <small>${item.detail}</small>
      <span class="badge ${badgeClass(item.status)}">${item.status}</span>
    </div>
  `).join("");
}

function renderMarkets(items) {
  const root = document.querySelector("#market-table");
  root.innerHTML = items.map(item => `
    <tr>
      <td><strong>${item.symbol}</strong></td>
      <td class="${item.trade === "PASS" ? "cell-pass" : "cell-pending"}">${item.trade}</td>
      <td class="${item.mark === "PASS" ? "cell-pass" : "cell-pending"}">${item.mark}</td>
      <td class="${item.funding === "PASS" ? "cell-pass" : "cell-pending"}">${item.funding}</td>
      <td><span class="provider-tag ${item.provider === "PIONEX" ? "pionex" : "binance"}">${item.provider}</span></td>
      <td><span class="badge ${badgeClass(item.status)}">${item.status}</span></td>
    </tr>
  `).join("");
}

function render(data) {
  state.data = data;
  document.querySelector("#snapshot-label").textContent = data.snapshotLabel;
  document.querySelector("#market-count").textContent = data.project.marketCount.toLocaleString();
  document.querySelector("#funding-months").textContent = data.project.fundingMonths.toLocaleString();
  renderPipeline(data.pipeline || []);
  renderCriticalGates(data.gates || []);
  renderAllGates(data.gates || []);
  renderMarkets(data.markets || []);
}

async function loadData() {
  try {
    const response = await fetch("./data/dashboard.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    render(data);
  } catch (error) {
    console.error("Dashboard fixture load failed", error);
    render(FALLBACK);
    document.querySelector("#snapshot-label").textContent = "Fixture unavailable";
  }
}

const titles = {
  overview: "Overview",
  "data-health": "Data Health",
  signals: "Signals",
  positions: "Paper Positions",
  trades: "Paper Trades",
  performance: "Performance Center",
  backtests: "Backtests",
  gates: "Risk & Gates"
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
