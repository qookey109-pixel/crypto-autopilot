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

export function coordinatorGitObjects(sha, path, blob) {
  const base = "https://api.github.com/repos/qookey109-pixel/crypto-autopilot/git/";
  const treeId = i => String(i + 1).padStart(40, "0");
  const objects = new Map([[base + "commits/" + sha, { sha, tree: { sha: treeId(0) } }]]);
  const parts = path.split("/");
  for (const [i, name] of parts.entries()) {
    const entry = i + 1 === parts.length
      ? { path: name, mode: "100644", type: "blob", sha: blob, size: 97 }
      : { path: name, mode: "040000", type: "tree", sha: treeId(i + 1) };
    objects.set(base + "trees/" + treeId(i), { sha: treeId(i), truncated: false, tree: [entry] });
  }
  objects.set(base.replace(/git\/$/, "branches/main"), { commit: { sha } });
  objects.set("https://raw.githubusercontent.com/qookey109-pixel/crypto-autopilot/" + sha +
    "/config/live_paper_coordinator_input_registry_v0_1.json", { schema: "qookey-live-paper-coordinator-input-registry-v0.1", workflow_id: "361536775",
      approved_inputs: [{ input_path: path, blob_sha: blob }] });
  return objects;
}

test("coordinator requires the approved regular blob at the exact commit before recording intent", async t => {
  const storage = openDispatchStorage(":memory:");
  t.after(() => storage.close());
  prepareDispatchJournal(storage, true);
  const at = Date.parse("2026-11-23T00:07:00Z");
  const repository = "qookey109-pixel/crypto-autopilot", sha = "b".repeat(40), inputBlobSha = "c".repeat(40);
  const path = "research/inputs/live-paper/case.json";
  const workflowPath = ".github/workflows/live-paper-run-coordinator-v0-1.yml";
  const policy = { repository, repositoryId: "1336841226", sha, workflowSha: sha, workflowId: "361536775",
    workflowPath, workflowRef: repository + "/" + workflowPath + "@refs/heads/main",
    writerId: "crypto-autopilot:live-paper-run-coordinator-v0-1", jobName: "run-one-step",
    approvedInputs: { input_path: path }, inputBlobSha };
  let posts = 0;
  for (const flaw of ["wrong commit", "missing", "symlink parent", "symlink leaf", "different blob",
    "off main", "unlisted", "conflicting registry", "wrong policy workflow", "hint only", "duplicate", "truncated", "wrong tree", "oversize", "redirect", "no digest", "budget", "expired after debit", "rollback before intent"]) {
    const objects = coordinatorGitObjects(sha, path, inputBlobSha);
    const [commit, root, , , leaf, main, registry] = [...objects.values()];
    if (flaw === "off main") main.commit.sha = inputBlobSha;
    if (flaw === "unlisted") registry.approved_inputs = [];
    if (flaw === "no digest") delete registry.approved_inputs[0].blob_sha;
    if (flaw === "wrong policy workflow") registry.workflow_id = "361556331";
    if (flaw === "conflicting registry") registry.approved_inputs.push({ input_path: path, blob_sha: sha });
    if (flaw === "hint only") registry.approved_inputs[0].blob_sha = sha;
    if (flaw === "wrong commit") commit.sha = inputBlobSha;
    if (flaw === "missing") leaf.tree = [];
    if (flaw === "symlink parent") root.tree[0].mode = "120000";
    if (flaw === "symlink leaf") leaf.tree[0].mode = "120000";
    if (flaw === "different blob") leaf.tree[0].sha = sha;
    if (flaw === "duplicate") leaf.tree.push({ ...leaf.tree[0] });
    if (flaw === "truncated") root.truncated = true;
    if (flaw === "wrong tree") root.sha = sha;
    let paid = 0, fetched = 0, now = at;
    const status = await sendApprovedManualJob({ enabled: true, storage, policy: flaw === "no digest"
      ? { ...policy, inputBlobSha: undefined } : policy, slotMs: at, clock: () => now,
      prepay(kind) {
        if (flaw === "rollback before intent" && kind === "DISPATCH_INTENT_INSERT") { now = at; return true; }
        assert.equal(kind, "GITHUB_INPUT_METADATA_GET");
        if (flaw === "expired after debit") now = at + 600001;
        if (flaw === "rollback before intent") now = at + 250;
        paid++;
        return flaw !== "budget" || paid < 3;
      },
      fetcher(url, options) {
        fetched++;
        assert.equal(fetched, paid);
        assert.equal(options.method, "GET");
        assert.equal(options.redirect, "manual");
        assert.ok(objects.has(url));
        if (flaw === "redirect") return new Response(null, { status: 302 });
        if (flaw === "oversize") return new Response(" ".repeat(131073));
        return Response.json(objects.get(url));
      },
      deliver() { posts++; },
    });
    const expected = ["expired after debit", "rollback before intent"].includes(flaw) ? "SLOT_BLOCKED" : "INPUT_BLOCKED";
    assert.equal(status, flaw === "budget" ? "BUDGET_BLOCKED" : expected, flaw);
    assert.equal(fetched, paid - Number(["budget", "expired after debit"].includes(flaw)));
    assert.equal(storage.sql.exec("SELECT COUNT(*) AS n FROM paper_dispatch_intent_v1").toArray()[0].n, 0);
  }
  assert.equal(posts, 0);
  storage.sql.exec("INSERT INTO paper_dispatch_intent_v1 VALUES (?, ?, ?, ?, ?, ?)", policy.writerId, at,
    policy.workflowId, sha, JSON.stringify(policy.approvedInputs), at);
  storage.sql.exec("INSERT INTO paper_dispatch_result_v1 VALUES (?, ?, ?, ?, ?)", "42", policy.writerId, at, at, at);
  assert.equal(await readConfirmedDispatch({ enabled: true, storage, runId: "42", prepay: () => true }), null);
});
