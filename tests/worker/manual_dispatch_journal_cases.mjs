import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { DatabaseSync } from "node:sqlite";
import { prepareDispatchJournal, readConfirmedDispatch, sendApprovedManualJob } from "../../workers/paper-gateway/manual-dispatch-journal.mjs";
import { prepareEnvelopeSchema, reserveEnvelope } from "../../workers/paper-gateway/atomic-envelope.mjs";

export function openDispatchStorage(file) {
  const db = new DatabaseSync(file);
  return {
    close: () => db.close(),
    sql: { exec(statement, ...args) {
      const stmt = db.prepare(statement);
      if (/^SELECT| RETURNING /.test(statement)) {
        const rows = stmt.all(...args);
        return { toArray: () => rows };
      }
      stmt.run(...args);
      return { toArray: () => [] };
    } },
    transactionSync(action) {
      db.exec("BEGIN IMMEDIATE");
      try { const result = action(); db.exec("COMMIT"); return result; }
      catch (error) { db.exec("ROLLBACK"); throw error; }
    },
  };
}

test("prepaid sender retains intent across response loss and restart; only confirmed results can be read", async t => {
  const dir = mkdtempSync(join(tmpdir(), "manual-paper-dispatch-"));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  const file = join(dir, "journal.sqlite");
  let storage = openDispatchStorage(file);
  t.after(() => storage.close());
  prepareDispatchJournal(storage, true);
  prepareEnvelopeSchema(storage, true);
  const at = Date.parse("2026-11-23T00:07:00Z");
  let now = at, attempt = 0, posted = 0;
  const path = ".github/workflows/live-paper-run-recovery-v0-1.yml";
  const repository = "qookey109-pixel/crypto-autopilot", sha = "b".repeat(40);
  const policy = { writerId: "crypto-autopilot:live-paper-run-recovery-v0-1", workflowId: "361556331",
    jobName: "reconcile", repository, repositoryId: "1336841226", sha, workflowSha: sha,
    workflowPath: path, workflowRef: repository + "/" + path + "@refs/heads/main",
    approvedInputs: { run_id: "live-paper-run-v0-1-" + "a".repeat(64) } };
  const unit = { worker: 1, github: 0, provider: 0, r2a: 0, r2b: 0, bytes: 0,
    d1queries: 0, d1read: 0, d1write: 0, d1bytes: 0, doReq: 1, doGbMs: 1, doRead: 5, doWrite: 5, doBytes: 4096 };
  const caps = Object.fromEntries(Object.entries(unit).map(([k,v]) => [k, v * 100]));
  caps.github = 2;
  const budget = { scope: "shared-test-account", policyHash: "c".repeat(64), startsMs: at, endsMs: at + 4000000, caps };
  const operations = ["DISPATCH_INTENT_INSERT", "GITHUB_DISPATCH_POST", "DISPATCH_RESULT_INSERT", "DISPATCH_RECEIPT_LOOKUP"];
  const prepay = kind => {
    assert.ok(operations.includes(kind));
    const id = "attempt-" + (++attempt);
    return reserveEnvelope(storage, { enabled: true, policy: budget, nowMs: now,
      claim: { writer: "dispatcher", slot: id, run: id, cost: { ...unit, github: Number(kind === "GITHUB_DISPATCH_POST") } } }) === "RESERVED";
  };
  const options = () => ({ enabled: true, storage, policy, slotMs: now, clock: () => now, prepay });
  const read = id => readConfirmedDispatch({ enabled: true, storage, runId: id, prepay });
  const loseReply = async () => { posted++; throw Error("lost after dispatch"); };
  assert.equal(await sendApprovedManualJob({ ...options(), enabled: false, deliver: loseReply }), "DISABLED");
  assert.equal(await sendApprovedManualJob({ ...options(), deliver: loseReply }), "REVIEW_REQUIRED");
  storage.close(); storage = openDispatchStorage(file);
  assert.equal(await sendApprovedManualJob({ ...options(), deliver: loseReply }), "ALREADY_ATTEMPTED");
  assert.equal(await read("222"), null);
  assert.equal(posted, 1);

  now += 900000;
  const body = { workflow_run_id: 222, run_url: "https://api.github.com/repos/" + repository + "/actions/runs/222",
    html_url: "https://github.com/" + repository + "/actions/runs/222" };
  const deliver = async request => {
    posted++;
    assert.equal(request.url, "https://api.github.com/repos/" + repository + "/actions/workflows/361556331/dispatches");
    assert.deepEqual(request.request.inputs, { ...policy.approvedInputs, repair_missing_result_seals: false });
    return { status: 200, body };
  };
  const attempts = await Promise.all([sendApprovedManualJob({ ...options(), deliver }), sendApprovedManualJob({ ...options(), deliver })]);
  assert.deepEqual(attempts.sort(), ["ALREADY_ATTEMPTED", "RECORDED"]);
  storage.close(); storage = openDispatchStorage(file);
  assert.equal(posted, 2);
  const receipt = await read("222");
  assert.deepEqual(receipt.response, body);
  assert.equal(receipt.request.inputs.repair_missing_result_seals, false);
  assert.equal(receipt.sourceSha, sha);
  assert.equal(await readConfirmedDispatch({ enabled: true, storage, runId: "222", prepay: () => false }), null);
  assert.throws(() => storage.sql.exec("UPDATE paper_dispatch_intent_v1 SET sha='changed'"), /IMMUTABLE/);
  assert.throws(() => storage.sql.exec("DELETE FROM paper_dispatch_result_v1"), /IMMUTABLE/);
  now += 900000;
  assert.equal(await sendApprovedManualJob({ ...options(), deliver }), "BUDGET_BLOCKED");
  assert.equal(posted, 2);
  assert.equal(storage.sql.exec("SELECT github FROM envelope_scope").toArray()[0].github, 2);
});
