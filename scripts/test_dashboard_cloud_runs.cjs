/* DOM contract tests, no browser, network, credentials or generated files. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../web/assets/js/app.js'), 'utf8');
const render = source.slice(source.indexOf('function renderCloudRuns('), source.indexOf('async function loadData()'));
const element = () => ({ children: [], textContent: '', append(child) { this.children.push(child); }, replaceChildren() { this.children = []; } });
const list = element();
const time = element();
const context = vm.createContext({ Date, formatTrustedTime: String, document: {
  getElementById: id => id === 'cloud-run-list' ? list : time, createElement: element,
} });
vm.runInContext(render, context);
const report = { schema: 'qookey-cloud-run-status-v0.1', authority: false,
  simulationReady: false, observedAtUtc: new Date().toISOString(), runs: {
    history: { state: 'WORKFLOW_SUCCESS', sourceUrl: 'https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/123' },
    funding: { state: '<script>bad</script>', sourceUrl: 'javascript:alert(1)' },
  } };
context.renderCloudRuns(report);
assert.equal(list.children.length, 6);
assert.match(list.children[0].children[0].textContent, /流程成功/);
assert.doesNotMatch(list.children[0].children[0].textContent, /COMPLETE|資料完成/);
assert.equal(list.children[0].children[0].rel, 'noopener noreferrer');
assert.equal(list.children[3].children[0].href, undefined);
assert.match(list.children[3].children[0].textContent, /待核實/);
context.renderCloudRuns({ ...report, observedAtUtc: '2020-01-01T00:00:00Z' });
assert.match(time.textContent, /較舊快照/);
for (const invalid of [null, { ...report, authority: true }, { ...report, simulationReady: true },
  { ...report, observedAtUtc: 'invalid' }, { ...report, observedAtUtc: '2999-01-01T00:00:00Z' }]) {
  context.renderCloudRuns(invalid);
  assert.equal(list.children.length, 0);
  assert.match(time.textContent, /不可核實/);
}
console.log('PASS: cloud status DOM, URL safety, stale/future rejection, no dataset-completion inference');
