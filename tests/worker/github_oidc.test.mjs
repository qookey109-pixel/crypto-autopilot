import { test } from "node:test";
import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";
import { DatabaseSync } from "node:sqlite";
import { readFileSync } from "node:fs";
import { claimJobSlot } from "../../workers/paper-gateway/d1-job-claim.mjs";
import { checkJobMetadata } from "../../workers/paper-gateway/github-metadata.mjs";
import { readJobMetadata } from "../../workers/paper-gateway/github-metadata-reader.mjs";
import { admitScheduledJob, processingSlot } from "../../workers/paper-gateway/synthetic-admission.mjs";
import { verifyGithubJob } from "../../workers/paper-gateway/github-oidc.mjs";
import { readGithubKeys } from "../../workers/paper-gateway/github-keys.mjs";

globalThis.crypto ??= webcrypto;

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

test("signature, repository and run claims must agree", async () => {
  const key = await crypto.subtle.generateKey(
    { name: "RSASSA-PKCS1-v1_5", modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: "SHA-256" },
    true, ["sign", "verify"],
  );
  const jwk = { ...await crypto.subtle.exportKey("jwk", key.publicKey), kid: "fixture", alg: "RS256", use: "sig" };
  const policy = {
    audience: "paper-test",
    repository: "owner/repo",
    repositoryId: "123",
    workflowRef: "owner/repo/.github/workflows/paper.yml@refs/heads/main",
    workflowSha: "a".repeat(40),
    sha: "a".repeat(40),
    subject: "repo:owner/repo:ref:refs/heads/main",
  };
  const claims = {
    iss: "https://token.actions.githubusercontent.com",
    aud: policy.audience, sub: policy.subject,
    repository: policy.repository, repository_id: policy.repositoryId,
    workflow_ref: policy.workflowRef, workflow_sha: policy.workflowSha, sha: policy.sha,
    ref: "refs/heads/main", ref_type: "branch", runner_environment: "github-hosted",
    event_name: "schedule", run_id: "100", run_attempt: "1", check_run_id: "101",
    iat: 1000, nbf: 1000, exp: 1300, jti: "fixture-jti",
  };
  const encode = (value) => Buffer.from(JSON.stringify(value)).toString("base64url");
  const header = encode({ alg: "RS256", typ: "JWT", kid: "fixture", x5t: "fixture-thumbprint" });
  const payload = encode(claims);
  const input = header + "." + payload;
  const signature = Buffer.from(await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5", key.privateKey, new TextEncoder().encode(input),
  )).toString("base64url");
  const token = input + "." + signature;
  const options = { enabled: true, policy, now: 1100, fetchKeys: async () => ({ keys: [jwk] }) };
  const accepted = await verifyGithubJob(token, options);
  assert.equal(accepted?.runId, "100");
  assert.equal(accepted?.checkRunId, "101");
  assert.equal(accepted?.eventName, "schedule");
  assert.equal(accepted?.repositoryId, "123");
  assert.equal(await verifyGithubJob(token, { ...options, policy: { ...policy, repositoryId: "999" } }), null);
  assert.equal(await verifyGithubJob(header + "." + encode({ ...claims, run_id: "102" }) + "." + signature, options), null);
  assert.equal(await verifyGithubJob(token, { ...options, now: 1400 }), null);
  const sign = async (h, p) => {
    const data = h + "." + p;
    const signed = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", key.privateKey, new TextEncoder().encode(data));
    return data + "." + Buffer.from(signed).toString("base64url");
  };
  const impossibleInterval = encode({ ...claims, nbf: 1105, exp: 1103 });
  assert.equal(await verifyGithubJob(await sign(header, impossibleInterval), options), null);
  const duplicate = Buffer.from(JSON.stringify(claims).replace('"run_id":"100"', '"run_id":"100","run_id":"100"')).toString("base64url");
  assert.equal(await verifyGithubJob(await sign(header, duplicate), options), null);
  const forbidden = encode({ alg: "RS256", typ: "JWT", kid: "fixture", jku: "https://attacker.example/keys" });
  assert.equal(await verifyGithubJob(await sign(forbidden, payload), options), null);
  const escapedDuplicate = Buffer.from(JSON.stringify(claims).replace('"run_id":"100"', '"run_id":"100","run\\u005fid":"100"')).toString("base64url");
  assert.equal(await verifyGithubJob(await sign(header, escapedDuplicate), options), null);
  assert.equal(await verifyGithubJob(token, { ...options, fetchKeys: async () => ({ keys: [jwk, jwk] }) }), null);
  assert.equal(await verifyGithubJob(token, { ...options, fetchKeys: async () => ({ keys: [{ ...jwk, n: "AQ" }] }) }), null);
  assert.equal((await verifyGithubJob(token, { ...options, fetchKeys: async () => ({ keys: [{ ...jwk, x5c: ["fixture"] }] }) }))?.runId, "100");
  assert.equal(await verifyGithubJob(token, { ...options, fetchKeys: async () => { throw Error("offline"); } }), null);
});

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
  sql.exec(readFileSync(new URL("../../migrations/paper_gateway_job_claim_candidate_v0_1.sql", import.meta.url), "utf8"));
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
    return { success: true, meta: { changes: Number(result.changes), total_attempts: 1, rows_read: 1, rows_written: Number(result.changes) } };
  } }) }) };
  const claim = { repositoryId: "123", runId: "100", attempt: "1", checkRunId: "101", writerId: "paper", slotId: "slot:1000" };
  assert.equal(await claimJobSlot(binding, claim), "DISABLED");
  assert.equal(calls, 0);
  assert.equal(await claimJobSlot(binding, claim, { enabled: true, limits: { rowsRead: 8, rowsWritten: 1 } }), "CLAIMED");
  assert.equal(await claimJobSlot(binding, claim, { enabled: true, limits: { rowsRead: 8, rowsWritten: 1 } }), "DUPLICATE_OR_CONFLICT");
  assert.equal(await claimJobSlot(binding, { ...claim, runId: "102", checkRunId: "103" }, { enabled: true, limits: { rowsRead: 8, rowsWritten: 1 } }), "DUPLICATE_OR_CONFLICT");
  loseResponse = true;
  const next = { ...claim, runId: "104", checkRunId: "105", slotId: "slot:2000" };
  assert.equal(await claimJobSlot(binding, next, { enabled: true, limits: { rowsRead: 8, rowsWritten: 1 } }), "REVIEW_REQUIRED");
  loseResponse = false;
  assert.equal(await claimJobSlot(binding, next, { enabled: true, limits: { rowsRead: 8, rowsWritten: 1 } }), "DUPLICATE_OR_CONFLICT");
  assert.equal(sql.prepare("SELECT COUNT(*) AS n FROM paper_job_claim_v0_1").get().n, 2);
  assert.throws(() => sql.exec("UPDATE paper_job_claim_v0_1 SET slot_id='slot:3000'"), /PAPER_JOB_CLAIM_IMMUTABLE/);
  assert.throws(() => sql.exec("DELETE FROM paper_job_claim_v0_1"), /PAPER_JOB_CLAIM_IMMUTABLE/);
  sql.prepare("INSERT OR REPLACE INTO paper_job_claim_v0_1 VALUES (?, ?, ?, ?, ?, ?)")
    .run("123", "999", "1", "998", "paper", "slot:1000");
  assert.equal(sql.prepare("SELECT run_id FROM paper_job_claim_v0_1 WHERE slot_id = ?").get("slot:1000").run_id, "100");
  sql.prepare("INSERT OR REPLACE INTO paper_job_claim_v0_1 VALUES (?, ?, ?, ?, ?, ?)")
    .run("123", "100", "1", "101", "paper", "slot:9999");
  assert.equal(sql.prepare("SELECT slot_id FROM paper_job_claim_v0_1 WHERE run_id = ?").get("100").slot_id, "slot:1000");
  assert.equal(sql.prepare("SELECT COUNT(*) AS n FROM paper_job_claim_v0_1").get().n, 2);
  const before = calls;
  assert.equal(await claimJobSlot(binding, { ...claim, writerId: "bad';drop" }, { enabled: true, limits: { rowsRead: 8, rowsWritten: 1 } }), "INVALID");
  assert.equal(calls, before);
  sql.close();
});

test("D1 claim rejects unknown or repeated attempt metadata", async () => {
  const claim = { repositoryId: "123", runId: "100", attempt: "1", checkRunId: "101", writerId: "paper", slotId: "slot:1000" };
  for (const result of [
    { success: true, meta: { changes: 1 } },
    { success: true, meta: { changes: 1, total_attempts: 1, rows_read: 9, rows_written: 1 } },
    { success: true, meta: { changes: 1, total_attempts: 1, rows_read: 1, rows_written: 2 } },
    { success: true, meta: { changes: 1, total_attempts: 2 } },
    { success: true, meta: { changes: 2, total_attempts: 1 } },
    { success: false, meta: { changes: 1, total_attempts: 1 } },
  ]) {
    let calls = 0;
    const db = { prepare: () => ({ bind: () => ({ run: async () => { calls++; return result; } }) }) };
    assert.equal(await claimJobSlot(db, claim, { enabled: true, limits: { rowsRead: 8, rowsWritten: 1 } }), "REVIEW_REQUIRED");
    assert.equal(calls, 1);
  }
});

test("signed job identity must match current exact run and job metadata", () => {
  const sha = "a".repeat(40);
  const policy = { repositoryId: "123", workflowId: "456", workflowPath: ".github/workflows/paper.yml", jobName: "paper",
    sha, maxAgeSeconds: 600, allowedEvents: ["schedule", "workflow_dispatch"] };
  const identity = { runId: "100", checkRunId: "101", eventName: "schedule", repositoryId: "123" };
  const run = { id: 100, workflow_id: 456, path: policy.workflowPath, head_sha: sha, head_branch: "main",
    run_attempt: 1, status: "in_progress", event: "schedule", created_at: "2026-01-01T00:00:00Z",
    repository: { id: 123 } };
  const job = { id: 101, run_id: 100, run_attempt: 1, head_sha: sha, name: "paper",
    status: "in_progress", started_at: "2026-01-01T00:00:10Z", completed_at: null };
  const now = Date.parse("2026-01-01T00:02:00Z");
  assert.equal(checkJobMetadata(identity, run, job, policy, now), true);
  assert.equal(checkJobMetadata({ ...identity, eventName: "workflow_dispatch" }, run, job, policy, now), false);
  assert.equal(checkJobMetadata({ ...identity, repositoryId: "999" }, run, job, policy, now), false);
  for (const alteredRun of [
    { ...run, id: 102 }, { ...run, workflow_id: 999 }, { ...run, head_sha: "b".repeat(40) },
    { ...run, head_branch: "other" }, { ...run, status: "completed" }, { ...run, run_attempt: 2 },
    { ...run, event: "pull_request" }, { ...run, repository: { id: 999 } },
    { ...run, created_at: "invalid" }, { ...run, created_at: "2025-12-31T23:00:00Z" },
  ]) assert.equal(checkJobMetadata(identity, alteredRun, job, policy, now), false);
  for (const alteredJob of [
    { ...job, id: 999 }, { ...job, run_id: 999 }, { ...job, run_attempt: 2 },
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
    subject: "repo:owner/repo:ref:refs/heads/main", writerId: "paper", maxAgeSeconds: 600,
    maxScheduleDelaySeconds: 180, admissionCosts: { workerRequests: 1, githubRequests: 4, d1Queries: 1, d1RowsRead: 8, d1RowsWritten: 1, d1StorageBytes: 4096 } };
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
  const job = { id: 101, run_id: 100, run_attempt: 1, head_sha: sha, name: "paper",
    status: "in_progress", started_at: "2026-01-01T00:07:40Z", completed_at: null };
  let fetches = 0, writes = 0;
  let invalidRun = false, staleMain = false;
  const fetcher = async url => {
    fetches++;
    if (url === "https://token.actions.githubusercontent.com/.well-known/jwks")
      return new Response(JSON.stringify({ keys: [jwk] }));
    if (url.endsWith("/actions/runs/100")) return new Response(JSON.stringify(invalidRun ? { ...run, head_sha: "b".repeat(40) } : run));
    if (url.endsWith("/actions/jobs/101")) return new Response(JSON.stringify(job));
    if (url.endsWith("/branches/main")) return new Response(JSON.stringify({ commit: { sha: staleMain ? "b".repeat(40) : sha } }));
    throw Error("unexpected path");
  };
  const sql = new DatabaseSync(":memory:");
  sql.exec(readFileSync(new URL("../../migrations/paper_gateway_job_claim_candidate_v0_1.sql", import.meta.url), "utf8"));
  const db = { prepare: statement => ({ bind: (...args) => ({ run: async () => {
    writes++; return { success: true, meta: { changes: Number(sql.prepare(statement).run(...args).changes), total_attempts: 1, rows_read: 1, rows_written: 1 } };
  } }) }) };
  const config = { enabled: true, policy, token, githubToken: "synthetic-only-token", fetcher, db, clock: () => now };
  assert.equal((await admitScheduledJob({ ...config, enabled: false, reserve: async () => { throw Error("must not reserve"); } })).status, "DISABLED");
  assert.equal(fetches, 0); assert.equal(writes, 0);
  const incomplete = { ...policy, admissionCosts: { ...policy.admissionCosts, d1RowsRead: undefined } };
  assert.equal((await admitScheduledJob({ ...config, policy: incomplete, reserve: async () => { throw Error("must not reserve"); } })).status, "INVALID");
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
    lateWrites++; return { success: true, meta: { changes: 1, total_attempts: 1, rows_read: 1, rows_written: 1 } };
  } }) }) };
  const lateResult = await admitScheduledJob({ ...config, db: delayedDb,
    clock: () => (++clockReads < 3 ? now : base + 301000), reserve: async () => true });
  assert.equal(lateResult.status, "REVIEW_REQUIRED");
  assert.equal(lateWrites, 1);
  run.created_at = "2026-01-01T00:06:30Z";
  job.started_at = "2026-01-01T00:07:00Z";
  const accepted = await admitScheduledJob({ ...config, reserve: async () => true });
  assert.equal(accepted.status, "CLAIMED");
  assert.equal(accepted.slotId, "slot:" + base);
  assert.equal((await admitScheduledJob({ ...config, reserve: async () => true })).status, "DUPLICATE_OR_CONFLICT");
  assert.equal(writes, 2);
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
