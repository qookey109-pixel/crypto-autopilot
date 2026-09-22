/* DOM contract tests, no browser, network, credentials or generated files. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../web/assets/js/app.js'), 'utf8');
const render = source.slice(source.indexOf('function renderCloudRuns('), source.indexOf('async function loadData()'));
const element = () => ({
  children: [],
  textContent: '',
  className: '',
  append(child) { this.children.push(child); },
  replaceChildren() { this.children = []; },
});
const list = element();
const time = element();
const context = vm.createContext({
  Date,
  formatTrustedTime: String,
  document: {
    getElementById: id => id === 'cloud-run-list' ? list : time,
    createElement: element,
  },
});
vm.runInContext(render, context);

const modern = {
  schema: 'qookey-cloud-run-status-v0.2',
  authority: false,
  mode: 'GITHUB_ACTIONS_METADATA_ONLY',
  observedAtUtc: new Date().toISOString(),
  summary: {
    repositoryCronDeclarationCount: 2,
    monitoredCronDeclarationCount: 2,
    currentEffectiveScheduleCount: 1,
    expiredScheduleCount: 1,
    pendingScheduleCount: 0,
    expiredFrozenCronDeclarationCount: 1,
  },
  safetyBoundary: {
    providerReadsPerformed: false,
    r2ReadsPerformed: false,
    r2WritesPerformed: false,
    artifactReadsPerformed: false,
    logReadsPerformed: false,
    holdoutAccessed: false,
    sourceSwitchAuthorized: false,
    tradePlanAuthorized: false,
    realMoneyOrderAuthorized: false,
    liveTradingAuthorized: false,
  },
  items: [
    {
      operationId: 'resource-hub-change-watch-v0-2',
      title: '外部資源追蹤',
      workflow: 'resource-hub-supply-chain-v0-2.yml',
      lifecycleState: 'CURRENT_EFFECTIVE',
      authorityState: 'SCHEDULED_READ_ONLY',
      authorityUrl: 'https://github.com/qookey109-pixel/crypto-autopilot/blob/main/config/resource_hub_supply_chain_v0_2.json',
      freshnessState: 'FRESH',
      businessResult: { status: 'UNKNOWN_FROM_GITHUB_RUN_METADATA' },
      latestAutomaticRun: {
        state: 'WORKFLOW_SUCCESS',
        runId: 123,
        headSha: 'a'.repeat(40),
        evidenceTimeUtc: '2026-09-21T04:00:00Z',
        sourceUrl: 'https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/123',
      },
    },
    {
      operationId: 'provider-equivalence-v0-12-successor-metadata-capture',
      title: 'V0.12 successor metadata capture',
      workflow: 'provider-equivalence-v0-12-successor-metadata-capture.yml',
      lifecycleState: 'EXPIRED_BOUNDED_FROZEN_CRON_DECLARATION',
      authorityState: 'HISTORICAL_WINDOW_ENDED',
      authorityUrl: 'javascript:alert(1)',
      freshnessState: 'EXPIRED_WINDOW',
      businessResult: { status: 'UNKNOWN_FROM_GITHUB_RUN_METADATA' },
      latestAutomaticRun: {
        state: '<script>bad</script>',
        runId: null,
        headSha: 'invalid',
        evidenceTimeUtc: null,
        sourceUrl: 'javascript:alert(1)',
      },
    },
  ],
};

context.renderCloudRuns(modern);
assert.equal(list.children.length, 2);
assert.match(time.textContent, /宣告 2 \/ 監控 2 \/ 有效 1 \/ 到期 1/);
assert.match(list.children[0].children[1].textContent, /Job resource-hub-change-watch-v0-2/);
assert.match(list.children[0].children[2].textContent, /Latest automatic run #123 · SHA aaaaaaaa · 流程成功 · 新鮮/);
assert.match(list.children[0].children[3].textContent, /2026-09-21T04:00:00Z/);
assert.match(list.children[0].children[4].textContent, /GitHub run metadata 無法判定/);
assert.equal(list.children[0].children[5].children.length, 2);
assert.equal(list.children[0].children[5].children[0].rel, 'noopener noreferrer');
assert.equal(list.children[0].children[5].children[1].rel, 'noopener noreferrer');
assert.equal(list.children[1].children[5].children.length, 0);
assert.doesNotMatch(list.children[0].children[2].textContent, /COMPLETE|資料完成/);

context.renderCloudRuns({
  ...modern,
  summary: {
    ...modern.summary,
    currentEffectiveScheduleCount: 0,
    expiredScheduleCount: 2,
  },
});
assert.equal(list.children.length, 2);
assert.match(time.textContent, /宣告 2 \/ 監控 2 \/ 有效 0 \/ 到期 2/);

context.renderCloudRuns({
  ...modern,
  summary: { ...modern.summary, monitoredCronDeclarationCount: 1 },
});
assert.equal(list.children.length, 0);
assert.match(time.textContent, /inventory 不一致/);

const legacy = {
  schema: 'qookey-cloud-run-status-v0.1',
  authority: false,
  simulationReady: false,
  observedAtUtc: new Date().toISOString(),
  runs: {
    history: {
      state: 'WORKFLOW_SUCCESS',
      sourceUrl: 'https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/456',
    },
  },
};
context.renderCloudRuns(legacy);
assert.equal(list.children.length, 6);
assert.match(list.children[0].children[0].textContent, /流程成功/);
assert.equal(list.children[0].children[0].rel, 'noopener noreferrer');

for (const invalid of [
  null,
  { ...modern, authority: true },
  { ...modern, mode: 'PROVIDER_DATA' },
  { ...modern, observedAtUtc: 'invalid' },
  { ...modern, observedAtUtc: '2999-01-01T00:00:00Z' },
  { ...modern, safetyBoundary: { ...modern.safetyBoundary, r2ReadsPerformed: true } },
]) {
  context.renderCloudRuns(invalid);
  assert.equal(list.children.length, 0);
  assert.match(time.textContent, /不可核實/);
}

console.log('PASS: cloud monitoring V0.2, legacy V0.1 compatibility, URL safety, inventory convergence, no business-result inference');
