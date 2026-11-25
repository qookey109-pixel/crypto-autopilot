import { test } from "node:test";
import assert from "node:assert/strict";
import signedJobCases from "./signed_job_cases.mjs";
import { webcrypto } from "node:crypto";
import { DatabaseSync } from "node:sqlite";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { claimJobSlot } from "../../workers/paper-gateway/d1-job-claim.mjs";
import { createIngressReservation, prepareEnvelopeSchema, reserveEnvelope, snapshotEnvelopes } from "../../workers/paper-gateway/atomic-envelope.mjs";
import { conservativeRemaining } from "../../workers/paper-gateway/lagged-usage.mjs";
import { checkJobMetadata } from "../../workers/paper-gateway/github-metadata.mjs";
import { readJobMetadata } from "../../workers/paper-gateway/github-metadata-reader.mjs";
import { admitManualJob, admitScheduledJob, processingSlot, processingSlotForJob } from "../../workers/paper-gateway/synthetic-admission.mjs";
import { verifyGithubJob } from "../../workers/paper-gateway/github-oidc.mjs";
import { readGithubKeys } from "../../workers/paper-gateway/github-keys.mjs";

globalThis.crypto ??= webcrypto;

const legacySchema = readFileSync(new URL("../../migrations/paper_gateway_job_claim_candidate_v0_1.sql", import.meta.url), "utf8");
const clockSchema = readFileSync(new URL("../../migrations/paper_gateway_job_claim_clock_candidate_v0_2.sql", import.meta.url), "utf8");

const scopeSchema = readFileSync(new URL("../../migrations/paper_gateway_manual_job_scope_candidate_v0_3.sql", import.meta.url), "utf8");

function installJobClaimSchema(db) {
  db.exec(legacySchema);
  db.exec(clockSchema);
  db.exec(scopeSchema);
}

test("unconfigured verifier fails closed without fetching keys", async () => {
  let calls = 0;
  const result = await verifyGithubJob("invalid", {
    enabled: false,
    fetchKeys: async () => { calls++; throw new Error("unexpected fetch"); },
  });
  assert.equal(result, null);
  assert.equal(calls, 0);
});

test("malformed tokens fail closed without fetching keys", async () => {
  let calls = 0;
  const result = await verifyGithubJob("not-a-jwt", {
    enabled: true,
    policy: {},
    now: 0,
    fetchKeys: async () => { calls++; throw new Error("unexpected fetch"); },
  });
  assert.equal(result, null);
  assert.equal(calls, 0);
});

test("signature, repository and run claims must agree", () => signedJobCases.test());

test("key reader stays closed until enabled and pins HTTPS origin", async () => {
  let count = 0;
  const fakeFetch = async (url, options) => {
    count++;
    assert.equal(url, "https://token.actions.githubusercontent.com/.well-known/jwks");
    assert.equal(options.redirect, "manual");
    return new Response(JSON.stringify({ keys: [{ kid: "fixture" }] }), { status: 200 });
  };
  assert.equal(await readGithubKeys({ enabled: false, fetcher: fakeFetch }), null);
  assert.equal(count, 0);
  assert.deepEqual(await readGithubKeys({ enabled: true, fetcher: fakeFetch }), { keys: [{ kid: "fixture" }] });
  assert.equal(count, 1);
});

test("key reader rejects redirects, malformed JSON, oversize and failures", async () => {
  for (const fakeFetch of [
    async () => new Response("", { status: 302, headers: { Location: "https://attacker.example" } }),
    async () => new Response("{broken"),
    async () => new Response('{"keys":[],"keys":[]}'),
    async () => new Response("x".repeat(65537)),
    async () => { throw Error("unavailable"); },
  ]) assert.equal(await readGithubKeys({ enabled: true, fetcher: fakeFetch }), null);
});

test("D1 claim adapter rejects duplicates and preserves ambiguous committed writes", async () => {
  const sql = new DatabaseSync(":memory:");
  installJobClaimSchema(sql);
  // Synthetic SQLite query plans are engineering evidence, not D1 billing.
  const queryPlans = [
    ["SELECT 1 FROM paper_job_claim_v0_1 WHERE repository_id=? AND run_id=? AND attempt=? AND check_run_id=? AND writer_id=?", ["123", "100", "1", "101", "paper"]],
    ["SELECT 1 FROM paper_job_claim_v0_1 WHERE repository_id=? AND writer_id=? AND slot_id=?", ["123", "paper", "slot:1000"]],
  ];
  for (const [query, params] of queryPlans) {
    const plan = sql.prepare("EXPLAIN QUERY PLAN " + query).all(...params);
    assert.ok(plan.some(row => /SEARCH .* USING (?:COVERING )?INDEX/i.test(row.detail)), JSON.stringify(plan));
    assert.ok(!plan.some(row => /SCAN paper_job_claim_v0_1/i.test(row.detail)), JSON.stringify(plan));
  }
  let calls = 0;
  let loseResponse = false;
  const binding = { prepare: statement => ({ bind: (...args) => ({ run: async () => {
    calls++;
    const result = sql.prepare(statement).run(...args);
    if (loseResponse) throw Error("response lost after commit");
    return { success: true, meta: { changes: Number(result.changes), total_attempts: 1, rows_read: 1, rows_written: Number(result.changes), size_after: 1024 } };
  } }) }) };
  const claim = { repositoryId: "123", runId: "100", attempt: "1", checkRunId: "101", writerId: "paper", slotId: "slot:1000", observedAtMs: 1000 };
  assert.equal(await claimJobSlot(binding, claim), "DISABLED");
  assert.equal(calls, 0);
  assert.equal(await claimJobSlot(binding, claim, { enabled: true, limits: { rowsRead: 8, rowsWritten: 4, maxDatabaseBytes: 2048 } }), "CLAIMED");
  assert.equal(await claimJobSlot(binding, claim, { enabled: true, limits: { rowsRead: 8, rowsWritten: 4, maxDatabaseBytes: 2048 } }), "DUPLICATE_OR_CONFLICT");
  assert.equal(await claimJobSlot(binding, { ...claim, runId: "102", checkRunId: "103" }, { enabled: true, limits: { rowsRead: 8, rowsWritten: 4, maxDatabaseBytes: 2048 } }), "DUPLICATE_OR_CONFLICT");
  loseResponse = true;
  const next = { ...claim, runId: "104", checkRunId: "105", slotId: "slot:2000", observedAtMs: 2000 };
  assert.equal(await claimJobSlot(binding, next, { enabled: true, limits: { rowsRead: 8, rowsWritten: 4, maxDatabaseBytes: 2048 } }), "REVIEW_REQUIRED");
  loseResponse = false;
  assert.equal(await claimJobSlot(binding, next, { enabled: true, limits: { rowsRead: 8, rowsWritten: 4, maxDatabaseBytes: 2048 } }), "DUPLICATE_OR_CONFLICT");
  assert.equal(sql.prepare("SELECT COUNT(*) AS n FROM paper_job_claim_v0_1").get().n, 2);
  assert.throws(() => sql.exec("UPDATE paper_job_claim_v0_1 SET slot_id='slot:3000'"), /PAPER_JOB_CLAIM_IMMUTABLE/);
  assert.throws(() => sql.exec("DELETE FROM paper_job_claim_v0_1"), /PAPER_JOB_CLAIM_IMMUTABLE/);
  sql.prepare("INSERT OR REPLACE INTO paper_job_claim_v0_1 (repository_id,run_id,attempt,check_run_id,writer_id,slot_id,observed_at_ms) VALUES (?, ?, ?, ?, ?, ?, ?)")
    .run("123", "999", "1", "998", "paper", "slot:1000", 2000);
  assert.equal(sql.prepare("SELECT run_id FROM paper_job_claim_v0_1 WHERE slot_id = ?").get("slot:1000").run_id, "100");
  sql.prepare("INSERT OR REPLACE INTO paper_job_claim_v0_1 (repository_id,run_id,attempt,check_run_id,writer_id,slot_id,observed_at_ms) VALUES (?, ?, ?, ?, ?, ?, ?)")
    .run("123", "100", "1", "101", "paper", "slot:9999", 9999);
  assert.equal(sql.prepare("SELECT slot_id FROM paper_job_claim_v0_1 WHERE run_id = ?").get("100").slot_id, "slot:1000");
  assert.equal(sql.prepare("SELECT COUNT(*) AS n FROM paper_job_claim_v0_1").get().n, 2);
  const before = calls;
  assert.equal(await claimJobSlot(binding, { ...claim, writerId: "bad';drop" }, { enabled: true, limits: { rowsRead: 8, rowsWritten: 4, maxDatabaseBytes: 2048 } }), "INVALID");
  assert.equal(calls, before);
  sql.close();
});

test("a reopened claim database rejects clock rollback across writers", async t => {
  const directory = mkdtempSync(join(tmpdir(), "paper-claim-clock-"));
  t.after(() => rmSync(directory, { recursive: true, force: true }));
  const file = join(directory, "claims.sqlite");
  const limits = { rowsRead: 8, rowsWritten: 4, maxDatabaseBytes: 2048 };
  const claim = { repositoryId: "123", runId: "11", attempt: "1", checkRunId: "12",
    writerId: "paper", slotId: "slot:1000", observedAtMs: 1300 };
  function submit(db, data) {
    const binding = { prepare: sql => ({ bind: (...args) => ({ run: async () => {
      const { changes } = db.prepare(sql).run(...args);
      return { success: true, meta: { changes, total_attempts: 1,
        rows_read: 2, rows_written: changes ? 4 : 0, size_after: 1024 } };
    } }) }) };
    return claimJobSlot(binding, data, { enabled: true, limits });
  }

  const first = new DatabaseSync(file);
  try {
    first.exec(legacySchema);
    assert.equal(await submit(first, claim), "REVIEW_REQUIRED");
    first.exec(clockSchema);
    assert.equal(await submit(first, claim), "REVIEW_REQUIRED");
    first.exec(scopeSchema);
    assert.equal(await submit(first, claim), "CLAIMED");
  } finally { first.close(); }

  const restarted = new DatabaseSync(file);
  try {
    const other = { ...claim, writerId: "second", runId: "21", checkRunId: "22" };
    assert.equal(await submit(restarted, { ...other, observedAtMs: 1299 }), "DUPLICATE_OR_CONFLICT");
    assert.equal(restarted.prepare("SELECT COUNT(*) AS n FROM paper_job_claim_v0_1").get().n, 1);
    assert.equal(await submit(restarted, other), "CLAIMED");
    assert.equal(await submit(restarted, other), "DUPLICATE_OR_CONFLICT");
    for (const predicate of ["observed_at_ms > 1300", "observed_at_ms IS NULL"]) {
      const plan = restarted.prepare("EXPLAIN QUERY PLAN SELECT 1 FROM paper_job_claim_v0_1 " +
        "INDEXED BY paper_job_observed_clock_v0_2 WHERE " + predicate).all();
      assert.ok(plan.some(row => /SEARCH .* USING COVERING INDEX paper_job_observed_clock_v0_2/.test(row.detail)));
    }
  } finally { restarted.close(); }

  const legacy = new DatabaseSync(":memory:");
  try {
    legacy.exec(legacySchema);
    legacy.exec("INSERT INTO paper_job_claim_v0_1 VALUES ('123','5','1','6','paper','slot:500')");
    legacy.exec(clockSchema);
    legacy.exec(scopeSchema);
    assert.equal(await submit(legacy, claim), "DUPLICATE_OR_CONFLICT");
    assert.equal(legacy.prepare("SELECT observed_at_ms FROM paper_job_claim_v0_1").get().observed_at_ms, null);
    assert.throws(() => legacy.exec("INSERT INTO paper_job_claim_v0_1 " +
      "(repository_id,run_id,attempt,check_run_id,writer_id,slot_id) VALUES ('123','7','1','8','paper','slot:700')"),
      /PAPER_JOB_CLOCK_REQUIRED/);
  } finally { legacy.close(); }
});

test("D1 claim rejects an empty write allowance before accessing the binding", async () => {
  const claim = { repositoryId: "123", runId: "100", attempt: "1", checkRunId: "101", writerId: "paper", slotId: "slot:1000", observedAtMs: 1000 };
  let calls = 0;
  const db = { prepare: () => { calls++; throw new Error("unexpected database access"); } };
  const limits = { rowsRead: 8, rowsWritten: 0, maxDatabaseBytes: 2048 };
  assert.equal(await claimJobSlot(db, claim, { enabled: true, limits }), "INVALID");
  assert.equal(calls, 0);
});

test("D1 claim rejects unknown or repeated attempt metadata", async () => {
  const claim = { repositoryId: "123", runId: "100", attempt: "1", checkRunId: "101", writerId: "paper", slotId: "slot:1000", observedAtMs: 1000 };
  for (const result of [
    { success: true, meta: { changes: 1 } },
    { success: true, meta: { changes: 1, total_attempts: 1, rows_read: 9, rows_written: 1 } },
    { success: true, meta: { changes: 1, total_attempts: 1, rows_read: 1, rows_written: 0 } },
    { success: true, meta: { changes: 0, total_attempts: 1, rows_read: 1, rows_written: 1, size_after: 1024 } },
    { success: true, meta: { changes: 1, total_attempts: 1, rows_read: 1, rows_written: 1, size_after: 2049 } },
    { success: true, meta: { changes: 1, total_attempts: 1, rows_read: 1, rows_written: 2 } },
    { success: true, meta: { changes: 1, total_attempts: 2 } },
    { success: true, meta: { changes: 2, total_attempts: 1 } },
    { success: false, meta: { changes: 1, total_attempts: 1 } },
  ]) {
    let calls = 0;
    const db = { prepare: () => ({ bind: () => ({ run: async () => { calls++; return result; } }) }) };
    assert.equal(await claimJobSlot(db, claim, { enabled: true, limits: { rowsRead: 8, rowsWritten: 4, maxDatabaseBytes: 2048 } }), "REVIEW_REQUIRED");
    assert.equal(calls, 1);
  }
});

test("signed job identity must match current exact run and job metadata", () => {
  const sha = "a".repeat(40);
  const policy = { repositoryId: "123", workflowId: "456", workflowPath: ".github/workflows/paper.yml", jobName: "paper",
    sha, maxAgeSeconds: 600, allowedEvents: ["schedule", "workflow_dispatch"] };
  const identity = { runId: "100", runAttempt: "1", checkRunId: "101", eventName: "schedule", repositoryId: "123" };
  const run = { id: 100, workflow_id: 456, path: policy.workflowPath, head_sha: sha, head_branch: "main",
    run_attempt: 1, status: "in_progress", event: "schedule", created_at: "2026-01-01T00:00:00Z",
    repository: { id: 123 } };
  const job = { id: 101, run_id: 100, run_attempt: 1, head_sha: sha, name: "paper",
    status: "in_progress", started_at: "2026-01-01T00:00:10Z", completed_at: null };
  const now = Date.parse("2026-01-01T00:02:00Z");
  assert.equal(checkJobMetadata(identity, run, job, policy, now), true);
  const { run_attempt: omittedAttempt, ...documentedJob } = job;
  assert.equal(omittedAttempt, 1);
  assert.equal(checkJobMetadata(identity, run, documentedJob, policy, now), true);
  assert.equal(checkJobMetadata({ ...identity, runAttempt: "2" }, run, documentedJob, policy, now), false);
  assert.equal(checkJobMetadata({ ...identity, runAttempt: undefined }, run, documentedJob, policy, now), false);
  assert.equal(checkJobMetadata({ ...identity, eventName: "workflow_dispatch" }, run, job, policy, now), false);
  assert.equal(checkJobMetadata({ ...identity, repositoryId: "999" }, run, job, policy, now), false);
  for (const alteredRun of [
    { ...run, id: 102 }, { ...run, workflow_id: 999 }, { ...run, head_sha: "b".repeat(40) },
    { ...run, head_branch: "other" }, { ...run, status: "completed" }, { ...run, run_attempt: 2 },
    { ...run, event: "pull_request" }, { ...run, repository: { id: 999 } },
    { ...run, created_at: "invalid" }, { ...run, created_at: "2025-12-31T23:00:00Z" },
  ]) assert.equal(checkJobMetadata(identity, alteredRun, job, policy, now), false);
  for (const alteredJob of [
    { ...job, id: 999 }, { ...job, run_id: 999 }, { ...job, run_attempt: 2 }, { ...job, run_attempt: null },
    { ...job, head_sha: "b".repeat(40) }, { ...job, status: "completed" },
    { ...job, name: "other" }, { ...job, started_at: "2026-01-01T00:05:00Z" },
  ]) assert.equal(checkJobMetadata(identity, run, alteredJob, policy, now), false);
  assert.equal(checkJobMetadata(identity, run, job, policy, now + 3600000), false);
});

test("metadata reader makes only fixed signed-ID GitHub requests", async () => {
  const calls = [];
  const fetcher = async (url, options) => {
    calls.push(url);
    assert.equal(options.method, "GET");
    assert.equal(options.redirect, "manual");
    assert.equal(options.headers.Authorization, "Bearer synthetic-only-token");
    return new Response(JSON.stringify({ id: calls.length }), { status: 200 });
  };
  const config = { repository: "owner/repo", identity: { runId: "100", checkRunId: "101" }, token: "synthetic-only-token", fetcher };
  assert.equal(await readJobMetadata({ ...config, enabled: false }), null);
  assert.deepEqual(calls, []);
  assert.deepEqual(await readJobMetadata({ ...config, enabled: true }), { run: { id: 1 }, job: { id: 2 }, main: { id: 3 } });
  assert.deepEqual(calls, [
    "https://api.github.com/repos/owner/repo/actions/runs/100",
    "https://api.github.com/repos/owner/repo/actions/jobs/101",
    "https://api.github.com/repos/owner/repo/branches/main",
  ]);
  assert.equal(await readJobMetadata({ ...config, enabled: true, identity: { runId: "../bad", checkRunId: "101" } }), null);
  assert.equal(calls.length, 3);
  let failures = 0;
  assert.equal(await readJobMetadata({ ...config, enabled: true, fetcher: async () => {
    failures++; return new Response("", { status: 302, headers: { Location: "https://attacker.example" } });
  } }), null);
  assert.equal(failures, 1);
});

test("signed identity and metadata precede a prepaid one-time slot claim", async () => {
  const base = Date.parse("2026-01-01T00:07:00Z");
  const now = base + 60000;
  const pair = await crypto.subtle.generateKey(
    { name: "RSASSA-PKCS1-v1_5", modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: "SHA-256" },
    true, ["sign", "verify"]);
  const jwk = { ...await crypto.subtle.exportKey("jwk", pair.publicKey), kid: "fixture", alg: "RS256", use: "sig" };
  const sha = "a".repeat(40);
  const policy = { repository: "owner/repo", repositoryId: "123", workflowId: "456",
    workflowPath: ".github/workflows/paper.yml", workflowRef: "owner/repo/.github/workflows/paper.yml@refs/heads/main",
    workflowSha: sha, sha, jobName: "paper", audience: "paper-test",
    subject: "repo:owner@77/repo@123:ref:refs/heads/main", writerId: "paper", databaseBytesBefore: 1024, maxAgeSeconds: 600,
    maxScheduleDelaySeconds: 180, admissionCosts: { workerRequests: 1, githubRequests: 4, d1Queries: 1, d1RowsRead: 8, d1RowsWritten: 4, d1StorageBytes: 4096 } };
  const claims = { iss: "https://token.actions.githubusercontent.com", aud: policy.audience, sub: policy.subject,
    repository: policy.repository, repository_id: policy.repositoryId, workflow_ref: policy.workflowRef,
    workflow_sha: sha, sha, ref: "refs/heads/main", ref_type: "branch", runner_environment: "github-hosted",
    event_name: "schedule", run_id: "100", run_attempt: "1", check_run_id: "101",
    iat: Math.floor(base / 1000), nbf: Math.floor(base / 1000), exp: Math.floor(base / 1000) + 300, jti: "fixture" };
  const enc = x => Buffer.from(JSON.stringify(x)).toString("base64url");
  const message = enc({ alg: "RS256", typ: "JWT", kid: "fixture" }) + "." + enc(claims);
  const signature = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", pair.privateKey, new TextEncoder().encode(message));
  const token = message + "." + Buffer.from(signature).toString("base64url");
  const run = { id: 100, workflow_id: 456, path: policy.workflowPath, head_sha: sha, head_branch: "main",
    run_attempt: 1, status: "in_progress", event: "schedule", created_at: "2026-01-01T00:07:30Z", repository: { id: 123 } };
  const job = { id: 101, run_id: 100, head_sha: sha, name: "paper",
    status: "in_progress", started_at: "2026-01-01T00:07:40Z", completed_at: null };
  let fetches = 0, writes = 0;
  let invalidRun = false, staleMain = false;
  const githubToken = "ghs_fixture." + "x".repeat(700) + ".signature";
  const fetcher = async (url, options) => {
    fetches++;
    if (url.startsWith("https://api.github.com/"))
      assert.equal(options.headers.Authorization, "Bearer " + githubToken);
    if (url === "https://token.actions.githubusercontent.com/.well-known/jwks")
      return new Response(JSON.stringify({ keys: [jwk] }));
    if (url.endsWith("/actions/runs/100")) return new Response(JSON.stringify(invalidRun ? { ...run, head_sha: "b".repeat(40) } : run));
    if (url.endsWith("/actions/jobs/101")) return new Response(JSON.stringify(job));
    if (url.endsWith("/branches/main")) return new Response(JSON.stringify({ commit: { sha: staleMain ? "b".repeat(40) : sha } }));
    throw Error("unexpected path");
  };
  const sql = new DatabaseSync(":memory:");
  installJobClaimSchema(sql);
  const db = { prepare: statement => ({ bind: (...args) => ({ run: async () => {
    writes++;
    const changes = Number(sql.prepare(statement).run(...args).changes);
    return { success: true, meta: { changes, total_attempts: 1, rows_read: 1, rows_written: changes, size_after: 1024 } };
  } }) }) };
  const config = { enabled: true, policy, token, githubToken, fetcher, db, clock: () => now };
  // Integrate the finite envelope with admission. The SQLite and clock are synthetic.
  const ingressSql = new DatabaseSync(":memory:");
  const ingressStorage = {
    sql: { exec: (statement, ...args) => {
      const stmt = ingressSql.prepare(statement);
      if (/^SELECT/.test(statement)) return { toArray: () => stmt.all(...args) };
      stmt.run(...args); return { toArray: () => [] };
    } },
    transactionSync: fn => {
      ingressSql.exec("BEGIN");
      try { const value = fn(); ingressSql.exec("COMMIT"); return value; }
      catch (error) { ingressSql.exec("ROLLBACK"); throw error; }
    },
  };
  assert.equal(prepareEnvelopeSchema(ingressStorage, true), "PREPARED");
  let ingressId = 0;
  const ingressPolicy = { scope: "ingress", policyHash: "c".repeat(64), startsMs: base, endsMs: base + 300000,
    caps: { worker: 2, github: 8, provider: 0, r2a: 0, r2b: 0, bytes: 0,
      d1queries: 2, d1read: 16, d1write: 8, d1bytes: 8192, doReq: 2, doGbMs: 2, doRead: 2, doWrite: 2, doBytes: 2 } };
  assert.throws(() => createIngressReservation({ enabled: true, storage: ingressStorage,
    policy: ingressPolicy, clock: () => now, nextId: () => "attempt-x",
    admissionCosts: policy.admissionCosts }), /overhead required/);
  const ingress = createIngressReservation({ enabled: true, storage: ingressStorage,
    policy: ingressPolicy, clock: () => now, nextId: () => "attempt-" + (++ingressId), admissionCosts: policy.admissionCosts,
    ledgerOverhead: { doReq: 1, doGbMs: 1, doRead: 1, doWrite: 1, doBytes: 1 } });
  assert.equal((await admitScheduledJob({ ...config, token: "invalid", reserve: ingress })).status, "IDENTITY_BLOCKED");
  assert.equal((await admitScheduledJob({ ...config, token: "invalid", reserve: ingress })).status, "IDENTITY_BLOCKED");
  assert.equal((await admitScheduledJob({ ...config, reserve: ingress })).status, "BUDGET_BLOCKED");
  assert.equal(fetches, 0); assert.equal(writes, 0);
  assert.equal(ingressSql.prepare("SELECT COUNT(*) AS n FROM envelope_claim").get().n, 2);
  assert.equal(ingressSql.prepare("SELECT github FROM envelope_scope").get().github, 8);
  assert.equal(ingressSql.prepare("SELECT doWrite FROM envelope_scope").get().doWrite, 2);
  ingressSql.close();
  assert.equal((await admitScheduledJob({ ...config, enabled: false, reserve: async () => { throw Error("must not reserve"); } })).status, "DISABLED");
  assert.equal(fetches, 0); assert.equal(writes, 0);
  const incomplete = { ...policy, admissionCosts: { ...policy.admissionCosts, d1RowsRead: undefined } };
  assert.equal((await admitScheduledJob({ ...config, policy: incomplete, reserve: async () => { throw Error("must not reserve"); } })).status, "INVALID");
  const underfunded = { ...policy, admissionCosts: { ...policy.admissionCosts, d1RowsWritten: 1 } };
  assert.equal((await admitScheduledJob({ ...config, policy: underfunded, reserve: async () => { throw Error("must not reserve"); } })).status, "INVALID");
  let reserved;
  assert.equal((await admitScheduledJob({ ...config, reserve: async envelope => { reserved = envelope; return false; } })).status, "BUDGET_BLOCKED");
  assert.deepEqual(reserved, policy.admissionCosts);
  assert.equal(fetches, 0); assert.equal(writes, 0);
  invalidRun = true;
  assert.equal((await admitScheduledJob({ ...config, reserve: async () => true })).status, "IDENTITY_BLOCKED");
  assert.equal(writes, 0);
  invalidRun = false;
  staleMain = true;
  assert.equal((await admitScheduledJob({ ...config, reserve: async () => true })).status, "IDENTITY_BLOCKED");
  assert.equal(writes, 0);
  staleMain = false;
  let clockReads = 0, lateWrites = 0;
  const delayedDb = { prepare: () => ({ bind: () => ({ run: async () => {
    lateWrites++; return { success: true, meta: { changes: 1, total_attempts: 1, rows_read: 1, rows_written: 1, size_after: 1024 } };
  } }) }) };
  const lateResult = await admitScheduledJob({ ...config, db: delayedDb,
    clock: () => (++clockReads < 3 ? now : base + 301000), reserve: async () => true });
  assert.equal(lateResult.status, "REVIEW_REQUIRED");
  assert.equal(lateWrites, 1);
  assert.equal(clockReads, 3);

  // A backwards step after the committed claim cannot release work.
  const rollbackSql = new DatabaseSync(":memory:");
  installJobClaimSchema(rollbackSql);
  let rollbackWrites = 0, rollbackReads = 0;
  const rollbackDb = { prepare: statement => ({ bind: (...args) => ({ run: async () => {
    rollbackWrites++;
    const changes = Number(rollbackSql.prepare(statement).run(...args).changes);
    return { success: true, meta: { changes, total_attempts: 1, rows_read: 1,
      rows_written: changes, size_after: 1024 } };
  } }) }) };
  const times = [now, now + 1000, now + 500];
  const rolledBack = await admitScheduledJob({ ...config, db: rollbackDb,
    clock: () => times[rollbackReads++], reserve: async () => true });
  assert.equal(rolledBack.status, "REVIEW_REQUIRED");
  assert.equal(rollbackReads, 3);
  assert.equal(rollbackWrites, 1);
  assert.equal(rollbackSql.prepare("SELECT COUNT(*) AS n FROM paper_job_claim_v0_1").get().n, 1);
  assert.equal((await admitScheduledJob({ ...config, db: rollbackDb, reserve: async () => true })).status,
    "DUPLICATE_OR_CONFLICT");
  assert.equal(rollbackSql.prepare("SELECT COUNT(*) AS n FROM paper_job_claim_v0_1").get().n, 1);
  rollbackSql.close();
  run.created_at = "2026-01-01T00:06:30Z";
  job.started_at = "2026-01-01T00:07:00Z";
  const accepted = await admitScheduledJob({ ...config, reserve: async () => true });
  assert.equal(accepted.status, "CLAIMED");
  assert.equal(accepted.slotId, "slot:" + base);
  assert.equal((await admitScheduledJob({ ...config, reserve: async () => true })).status, "DUPLICATE_OR_CONFLICT");
  assert.equal(writes, 2);

  const project = "qookey109-pixel/crypto-autopilot";
  for (const [index, [writer, workflowId, file, jobName, start]] of [
    ["research-signal-layer-v0-2", "340924790", "research-signal-layer-v0-2.yml", "collect", "2026-11-22T02:17:00Z"],
    ["binance-usdm-detailed-training-v0-1", "340899183", "binance-usdm-detailed-training-v0-1.yml", "train", "2026-11-22T04:37:00Z"],
  ].entries()) {
    const runId = 200 + index;
    const checkId = 300 + index;
    const at = Date.parse(start);
    const path = ".github/workflows/" + file;
    const fixed = { ...policy, repository: project, repositoryId: "1336841226", workflowId,
      workflowPath: path, workflowRef: project + "/" + path + "@refs/heads/main", jobName,
      subject: "repo:qookey109-pixel@297143956/crypto-autopilot@1336841226:ref:refs/heads/main",
      writerId: "crypto-autopilot:" + writer };
    const seconds = at / 1000;
    const identity = { ...claims, sub: fixed.subject, repository: project, repository_id: fixed.repositoryId,
      workflow_ref: fixed.workflowRef, run_id: String(runId), check_run_id: String(checkId),
      iat: seconds, nbf: seconds, exp: seconds + 300 };
    const signed = enc({ alg: "RS256", typ: "JWT", kid: "fixture" }) + "." + enc(identity);
    const sig = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", pair.privateKey, new TextEncoder().encode(signed));
    const observed = { ...run, id: runId, workflow_id: Number(workflowId), path,
      repository: { id: Number(fixed.repositoryId) }, created_at: start };
    const activeJob = { ...job, id: checkId, run_id: runId, name: jobName, started_at: start };
    const registered = { ...config, policy: fixed, token: signed + "." + Buffer.from(sig).toString("base64url"),
      clock: () => at + 60000, reserve: async () => true,
      fetcher: async url => {
        if (url.endsWith("/jwks")) return Response.json({ keys: [jwk] });
        if (url.endsWith("/actions/runs/" + runId)) return Response.json(observed);
        if (url.endsWith("/actions/jobs/" + checkId)) return Response.json(activeJob);
        if (url.endsWith("/branches/main")) return Response.json({ commit: { sha } });
        throw Error("unexpected fixture path");
      } };
    assert.equal(processingSlotForJob(fixed, at + 600000, at + 600000, start), at);
    assert.equal(processingSlotForJob(fixed, at, at + 600001, start), null);
    assert.equal(processingSlotForJob(fixed, at, at, new Date(at - 1000).toISOString()), null);
    assert.equal(processingSlotForJob(fixed, at, at, new Date(at + 1000).toISOString()), null);
    if (jobName === "train") {
      const monday = at + 86400000;
      assert.equal(processingSlotForJob(fixed, monday, monday, new Date(monday).toISOString()), null);
    }
    const before = writes;
    const otherScheduledWriter = jobName === "train" ? "research-signal-layer-v0-2" : "binance-usdm-detailed-training-v0-1";
    for (const other of ["crypto-autopilot:" + otherScheduledWriter, "unknown", "crypto-autopilot:live-paper-run-recovery-v0-1", "crypto-autopilot:live-paper-run-coordinator-v0-1"]) {
      assert.equal((await admitScheduledJob({ ...registered, policy: { ...fixed, writerId: other } })).status, "SLOT_BLOCKED");
    }
    assert.equal(writes, before);
    assert.deepEqual(await admitScheduledJob(registered), { status: "CLAIMED", slotId: "slot:" + at });
    const row = sql.prepare("SELECT slot_id FROM paper_job_claim_v0_1 WHERE writer_id=?").get(fixed.writerId);
    assert.equal(row.slot_id, "slot:" + at);
    assert.equal((await admitScheduledJob(registered)).status, "DUPLICATE_OR_CONFLICT");
  }

  const target = "live-paper-run-v0-1-" + "d".repeat(64);
  const inputPath = "research/inputs/live-paper/synthetic-example.json";
  // Numeric workflow IDs below are fixtures. The real IDs and dispatcher
  // receipt must be obtained independently before any production binding.
  for (const [index, [writer, jobName, sentInputs, expectedInputs]] of [
    ["live-paper-run-coordinator-v0-1", "run-one-step", { input_path: inputPath }, { input_path: inputPath }],
    ["live-paper-run-recovery-v0-1", "reconcile", { run_id: target }, { run_id: target, repair_missing_result_seals: false }],
    ["live-paper-run-recovery-v0-1", "reconcile", { run_id: target, repair_missing_result_seals: true },
      { run_id: target, repair_missing_result_seals: true }],
  ].entries()) {
    const at = Date.parse("2026-11-23T00:07:00Z") + index * 900000;
    const runId = 401 + index, checkId = 501 + index;
    const workflowId = writer.includes("coordinator") ? "601" : "602";
    const path = ".github/workflows/" + writer + ".yml";
    const api = "https://api.github.com/repos/" + project;
    const manualDispatch = {
      apiVersion: "2026-03-10", method: "POST", url: api + "/actions/workflows/" + workflowId + "/dispatches",
      sourceSha: sha, slotMs: at, sentAtMs: at + 100, receivedAtMs: at + 1400,
      request: { ref: "main", inputs: sentInputs }, status: 200,
      response: { workflow_run_id: runId, run_url: api + "/actions/runs/" + runId,
        html_url: "https://github.com/" + project + "/actions/runs/" + runId },
    };
    const fixed = { ...policy, repository: project, repositoryId: "1336841226", writerId: "crypto-autopilot:" + writer,
      workflowId, workflowPath: path, workflowRef: project + "/" + path + "@refs/heads/main", jobName,
      subject: "repo:qookey109-pixel@297143956/crypto-autopilot@1336841226:ref:refs/heads/main",
      approvedInputs: expectedInputs, manualDispatch };
    const identity = { ...claims, sub: fixed.subject, repository: project, repository_id: fixed.repositoryId,
      workflow_ref: fixed.workflowRef, run_id: String(runId), check_run_id: String(checkId), event_name: "workflow_dispatch",
      iat: at / 1000, nbf: at / 1000, exp: at / 1000 + 300 };
    const message = enc({ alg: "RS256", typ: "JWT", kid: "fixture" }) + "." + enc(identity);
    const sig = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", pair.privateKey, new TextEncoder().encode(message));
    const stamp = new Date(at + 1000).toISOString().replace(".000Z", "Z");
    const observed = { ...run, id: runId, repository: { id: Number(fixed.repositoryId) },
      workflow_id: Number(workflowId), path, event: "workflow_dispatch", created_at: stamp,
      display_title: "audit only", inputs: { repair_missing_result_seals: true } };
    const activeJob = { ...job, id: checkId, run_id: runId, name: jobName, started_at: stamp };
    const manual = { ...config, policy: fixed, token: message + "." + Buffer.from(sig).toString("base64url"),
      clock: () => at + 3000, reserve: async () => true,
      fetcher: async url => {
        if (url.endsWith("/jwks")) return Response.json({ keys: [jwk] });
        if (url.endsWith("/actions/runs/" + runId)) return Response.json(observed);
        if (url.endsWith("/actions/jobs/" + checkId)) return Response.json(activeJob);
        if (url.endsWith("/branches/main")) return Response.json({ commit: { sha } });
        throw Error("unexpected path");
      } };
    const before = writes;
    const wrongInputs = jobName === "reconcile"
      ? [{ ...expectedInputs, repair_missing_result_seals: !expectedInputs.repair_missing_result_seals },
         { run_id: target, repair_missing_result_seals: "false" }, { run_id: target.replace(/d$/, "c") }]
      : [{ input_path: inputPath.replace("synthetic-example", "other") },
         { input_path: inputPath.replace("synthetic-example", "../escape") }];
    for (const change of [
      { manualDispatch: null }, { approvedInputs: null },
      ...[ { ...sentInputs, unexpected: true }, ...(jobName === "reconcile"
        ? [{ run_id: target, repair_missing_result_seals: "true" }, { run_id: "bad" }]
        : [{ input_path: "research/inputs/live-paper/../escape.json" }]) ]
        .map(inputs => ({ approvedInputs: inputs, manualDispatch: { ...manualDispatch, request: { ref: "main", inputs } } })), { manualDispatch: { ...manualDispatch, status: 204 } },
      { manualDispatch: { ...manualDispatch, response: { ...manualDispatch.response, workflow_run_id: runId + 1 } } },
      { manualDispatch: { ...manualDispatch, response: { ...manualDispatch.response, html_url: "https://example.org/" } } },
      { manualDispatch: { ...manualDispatch, sourceSha: "e".repeat(40) } },
      { manualDispatch: { ...manualDispatch, sentAtMs: at - 1 } },
      { manualDispatch: { ...manualDispatch, receivedAtMs: at + 3001 } },
      { manualDispatch: { ...manualDispatch, sentAtMs: at + 2000, receivedAtMs: at + 2200 } },
      { manualDispatch: { ...manualDispatch, slotMs: at - 900000 } },
      { manualDispatch: { ...manualDispatch, request: { ref: "dev", inputs: sentInputs } } },
      ...wrongInputs.map(inputs => ({ manualDispatch: { ...manualDispatch, request: { ref: "main", inputs } } })),
    ]) assert.deepEqual(await admitManualJob({ ...manual, policy: { ...fixed, ...change } }), { status: "DISPATCH_SCOPE_BLOCKED" });
    assert.deepEqual(await admitScheduledJob(manual), { status: "IDENTITY_BLOCKED" });
    assert.equal((await admitManualJob({ ...manual, policy: { ...fixed, admissionCosts: {
      ...fixed.admissionCosts, d1StorageBytes: 1 } } })).status, "BUDGET_BLOCKED");
    assert.equal(writes, before);
    const operationScope = { sourceSha: sha, inputs: expectedInputs };
    assert.deepEqual(await admitManualJob(manual), { status: "CLAIMED", slotId: "slot:" + at, operationScope });
    assert.deepEqual(await admitManualJob(manual), { status: "DUPLICATE_OR_CONFLICT" });
    assert.equal(sql.prepare("SELECT operation_scope_json FROM paper_job_claim_v0_1 WHERE run_id=?")
      .get(String(runId)).operation_scope_json, JSON.stringify(operationScope));
  }
  assert.equal(sql.prepare("SELECT COUNT(*) AS n FROM paper_job_claim_v0_1 WHERE operation_scope_json IS NOT NULL").get().n, 3);
  assert.throws(() => sql.exec("INSERT INTO paper_job_claim_v0_1 " +
    "(repository_id,run_id,attempt,check_run_id,writer_id,slot_id,observed_at_ms) " +
    "VALUES ('123','6','1','7','crypto-autopilot:live-paper-run-recovery-v0-1','slot:1000',1000)"), /PAPER_JOB_SCOPE_INVALID/);

  sql.close();
});

test("processing slot honors V0.5 freshness, UTC boundary and clock continuity", () => {
  const at = s => Date.parse(s);
  const start = at("2026-01-01T00:07:00Z");
  assert.equal(processingSlot(start + 600000, start + 600000), start);
  assert.equal(processingSlot(start + 600001, start + 600001), null);
  assert.equal(processingSlot(at("2026-01-01T00:00:00Z"), at("2026-01-01T00:00:00Z")), null);
  assert.equal(processingSlot(start + 10000, start + 9999), null);
  assert.equal(processingSlot(start + 899999, start + 900000), null);
  assert.equal(processingSlot(NaN, start), null);
});

test("atomic finite envelope rejects duplicate, overrun and policy drift", async () => {
  const db = new DatabaseSync(":memory:");
  let failUpdate = false, calls = 0;
  const storage = {
    sql: { exec: (sql, ...args) => {
      calls++;
      if (failUpdate && sql.startsWith("UPDATE")) throw new Error("synthetic commit failure");
      const stmt = db.prepare(sql);
      if (/^SELECT/.test(sql)) return { toArray: () => stmt.all(...args) };
      stmt.run(...args);
      return { toArray: () => [] };
    } },
    transactionSync: fn => {
      db.exec("BEGIN");
      try { const value = fn(); db.exec("COMMIT"); return value; }
      catch (error) { db.exec("ROLLBACK"); throw error; }
    },
  };
  assert.equal(prepareEnvelopeSchema(storage), "DISABLED");
  assert.equal(calls, 0);
  assert.equal(prepareEnvelopeSchema(storage, true), "PREPARED");
  const caps = { worker: 5, github: 8, provider: 2, r2a: 3, r2b: 6, bytes: 100, d1queries: 4, d1read: 4, d1write: 3, d1bytes: 100, doReq: 5, doGbMs: 5, doRead: 5, doWrite: 5, doBytes: 5 };
  const cost = { worker: 2, github: 4, provider: 1, r2a: 2, r2b: 2, bytes: 20, d1queries: 2, d1read: 2, d1write: 1, d1bytes: 20, doReq: 2, doGbMs: 2, doRead: 2, doWrite: 2, doBytes: 2 };
  const policy = { scope: "test", policyHash: "a".repeat(64), startsMs: 1000, endsMs: 2000, caps };
  const claim = { writer: "paper", slot: "slot:1", run: "run:1", cost };
  const run = (c = claim, p = policy, nowMs = 1500) =>
    reserveEnvelope(storage, { enabled: true, policy: p, claim: c, nowMs });
  assert.equal(run(), "RESERVED");
  assert.equal(run(), "DUPLICATE");
  assert.equal(run({ ...claim, slot: "slot:2", run: "run:2" }), "BUDGET_BLOCKED");
  assert.equal(run(claim, { ...policy, policyHash: "b".repeat(64) }), "POLICY_MISMATCH");
  assert.equal(run(claim, { ...policy, caps: { ...caps, r2a: 99 } }), "POLICY_MISMATCH");
  assert.equal(run(claim, { ...policy, endsMs: 3000 }), "POLICY_MISMATCH");
  assert.equal(run(claim, { ...policy, scope: "other-scope" }), "SCOPE_MISMATCH");
  assert.equal(db.prepare("SELECT COUNT(*) AS n FROM envelope_scope").get().n, 1);
  assert.equal(run(claim, policy, 2000), "INVALID");
  for (const key of Object.keys(caps)) {
    const zero = Object.fromEntries(Object.keys(caps).map(k => [k, 0]));
    zero[key] = caps[key] - cost[key] + 1;
    const extraClaim = { ...claim, writer: "over-" + key, slot: "s-" + key, run: "r-" + key, cost: zero };
    assert.equal(run(extraClaim), "BUDGET_BLOCKED", key);
  }
  const missing = { ...cost };
  delete missing.d1queries;
  assert.equal(run({ ...claim, cost: missing }), "INVALID");

  const alternate = { ...claim, writer: "other", slot: "slot:2", run: "run:2",
    cost: { worker: 1, github: 1, provider: 0, r2a: 1, r2b: 1, bytes: 1, d1queries: 1, d1read: 0, d1write: 0, d1bytes: 1, doReq: 1, doGbMs: 1, doRead: 1, doWrite: 1, doBytes: 1 } };
  failUpdate = true;
  assert.equal(run(alternate), "REVIEW_REQUIRED");
  assert.equal(db.prepare("SELECT COUNT(*) AS n FROM envelope_claim").get().n, 1);
  failUpdate = false;
  assert.equal(run(alternate), "RESERVED");
  assert.equal(db.prepare("SELECT r2a FROM envelope_scope").get().r2a, 3);
  const snap = snapshotEnvelopes(storage, { enabled: true, scope: "test", nowMs: 1500 });
  assert.equal(snap.status, "READY_FOR_REVIEW");
  assert.equal(snap.reservations.length, 2);
  assert.deepEqual(snap.reservations[0].envelope, cost);
  assert.equal(snap.reservations[0].closedMs, null);
  const counters = Object.fromEntries(Object.keys(caps).map(k => [k, { used: 0, cap: 10000, margin: 0,
    periodStartMs: 0, periodEndMs: 2000, measuredThroughMs: 1400 }]));
  const reconciled = conservativeRemaining({ enabled: true, nowMs: 1500, observedAtMs: 1490,
    maxObservationAgeMs: 100, maxDataLagMs: 1000, completeCoverage: true, counters, ...snap });
  assert.equal(reconciled.status, "READY_FOR_REVIEW");
  assert.equal(reconciled.remaining.r2a, 9997);
  assert.throws(() => db.exec("UPDATE envelope_claim SET reserved_ms=0"), /IMMUTABLE/);
  assert.throws(() => db.exec("DELETE FROM envelope_claim"), /IMMUTABLE/);
  // SQLite REPLACE may bypass DELETE triggers when recursive_triggers is off.
  // Each uniqueness conflict must preserve the original immutable reservation.
  db.exec("PRAGMA recursive_triggers=OFF");
  const columns = Object.keys(cost).join(", ");
  db.exec(`INSERT OR REPLACE INTO envelope_claim SELECT scope, writer, 'slot:attacker', run, reserved_ms, ${columns} FROM envelope_claim WHERE writer='paper'`);
  assert.equal(db.prepare("SELECT slot FROM envelope_claim WHERE writer='paper'").get().slot, "slot:1");
  db.exec(`INSERT OR REPLACE INTO envelope_claim SELECT scope, writer, slot, 'run:attacker', reserved_ms, ${columns} FROM envelope_claim WHERE writer='paper'`);
  assert.equal(db.prepare("SELECT run FROM envelope_claim WHERE writer='paper'").get().run, "run:1");
  assert.equal(snapshotEnvelopes(storage, { enabled: true, scope: "test", nowMs: 1500 }).status, "READY_FOR_REVIEW");
  db.exec("UPDATE envelope_scope SET r2a=0");
  assert.equal(snapshotEnvelopes(storage, { enabled: true, scope: "test", nowMs: 1500 }).status, "REVIEW_REQUIRED");
  db.close();
});

test("lagged account counters charge every open or watermark-spanning reservation", () => {
  const names = ["worker", "github", "provider", "r2a", "r2b", "bytes", "d1queries", "d1read", "d1write", "d1bytes", "doReq", "doGbMs", "doRead", "doWrite", "doBytes"];
  const envelope = n => Object.fromEntries(names.map(k => [k, n]));
  const counters = Object.fromEntries(names.map(k => [k, { used: 10, cap: 100, margin: 5,
    periodStartMs: 0, periodEndMs: 2000, measuredThroughMs: 1000 }]));
  const reservations = [
    { id: "before", reservedMs: 100, closedMs: 999, envelope: envelope(20) },
    { id: "spanning", reservedMs: 500, closedMs: 1100, envelope: envelope(7) },
    { id: "open", reservedMs: 100, closedMs: null, envelope: envelope(11) },
    { id: "new", reservedMs: 1100, closedMs: 1200, envelope: envelope(3) },
  ];
  const args = { enabled: true, nowMs: 1500, observedAtMs: 1490,
    maxObservationAgeMs: 100, maxDataLagMs: 1000, ledgerAsOfMs: 1500,
    completeCoverage: true, counters, reservations };
  assert.deepEqual(conservativeRemaining(args), { status: "READY_FOR_REVIEW", remaining: envelope(64) });
  assert.equal(conservativeRemaining({ ...args, ledgerAsOfMs: 1499 }).status, "INVALID");
  assert.equal(conservativeRemaining({ ...args, completeCoverage: false }).status, "INVALID");
  assert.equal(conservativeRemaining({ ...args, maxDataLagMs: 100 }).status, "INVALID");
  assert.equal(conservativeRemaining({ ...args, reservations: [...reservations, reservations[0]] }).status, "INVALID");
  const limited = structuredClone(counters);
  limited.r2a.cap = 35;
  assert.equal(conservativeRemaining({ ...args, counters: limited }).status, "BUDGET_BLOCKED");
  limited.r2a.cap = 100;
  limited.r2a.measuredThroughMs = 1600;
  assert.equal(conservativeRemaining({ ...args, counters: limited }).status, "INVALID");
  assert.equal(conservativeRemaining({ ...args, nowMs: 2000, ledgerAsOfMs: 2000, observedAtMs: 2000 }).status, "INVALID");
  assert.equal(conservativeRemaining({ ...args, enabled: false }).status, "DISABLED");
});
