const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const app = fs.readFileSync("web/assets/js/app.js", "utf8");
const fn = app.slice(app.indexOf("function renderPaperTraining("), app.indexOf("function researchEvidenceIsSafe("));
function harness() {
  const nodes = new Map();
  let curve;
  const document = { querySelector: id => {
    if (!nodes.has(id)) nodes.set(id, { textContent: "old", innerHTML: "old" });
    return nodes.get(id);
  }};
  const render = new Function("document", "renderEquityChart", "number", "displayStatus",
    "formatTrustedTime", "escapeHtml", "formatTradeTime", fn + ";return renderPaperTraining;")(
      document, r => curve = r, v => String(Number(v || 0)), s => s, s => s, String, String);
  return { nodes, render, curve: () => curve };
}
function report() {
  return { mode: "PAPER_TRAINING_ONLY", status: "PASS", observedAtUtc: new Date().toISOString(),
    authority: { formalTradePlanAuthorized: false, sourceSwitchAuthorized: false,
      realMoneyOrderAuthorized: false, liveTradingAuthorized: false },
    metrics: { return_pct: 2 }, latestCandidates: [{ symbol: "BTC_USDT_PERP" }] };
}
const badReports = [
  null, { ...report(), status: "WAITING_AUTHORITY" }, { ...report(), observedAtUtc: null },
  { ...report(), observedAtUtc: "2999-01-01T00:00:00Z" }, { ...report(), authority: {} },
  { ...report(), authority: { ...report().authority, liveTradingAuthorized: true } }
];
for (const [index, bad] of badReports.entries()) {
  test("unavailable or rejected report clears prior view: " + index, () => {
    const h = harness(); h.render(report()); h.render(bad);
    for (const id of ["paper-return", "paper-win-rate", "paper-profit-factor", "paper-drawdown"]) {
      assert.equal(h.nodes.get("#" + id).textContent, "—");
    }
    assert.ok(!h.nodes.get("#paper-signal-table").innerHTML.includes("BTC_USDT_PERP"));
    assert.equal(h.curve(), null);
  });
}
test("fresh report renders metrics and candidate", () => {
  const h = harness(); h.render(report());
  assert.equal(h.nodes.get("#paper-return").textContent, "2%");
  assert.ok(h.nodes.get("#paper-signal-table").innerHTML.includes("BTC_USDT_PERP"));
});
test("stale observation does not render current candidate", () => {
  const h = harness(); h.render({ ...report(), observedAtUtc: "2020-01-01T00:00:00Z" });
  assert.ok(!h.nodes.get("#paper-signal-table").innerHTML.includes("BTC_USDT_PERP"));
});
