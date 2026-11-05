import { test } from "node:test";
import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";
import { DatabaseSync } from "node:sqlite";
import { claimJobSlot } from "../../workers/paper-gateway/d1-job-claim.mjs";
import { checkJobMetadata } from "../../workers/paper-gateway/github-metadata.mjs";
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
  sql.exec(`CREATE TABLE paper_job_claim_v0_1 (
    repository_id TEXT NOT NULL, run_id TEXT NOT NULL, attempt TEXT NOT NULL,
    check_run_id TEXT NOT NULL, writer_id TEXT NOT NULL, slot_id TEXT NOT NULL,
    PRIMARY KEY (repository_id, run_id, attempt, check_run_id, writer_id),
    UNIQUE (repository_id, writer_id, slot_id))`);
  let calls = 0;
  let loseResponse = false;
  const binding = { prepare: statement => ({ bind: (...args) => ({ run: async () => {
    calls++;
    const result = sql.prepare(statement).run(...args);
    if (loseResponse) throw Error("response lost after commit");
    return { success: true, meta: { changes: Number(result.changes), total_attempts: 1 } };
  } }) }) };
  const claim = { repositoryId: "123", runId: "100", attempt: "1", checkRunId: "101", writerId: "paper", slotId: "slot:1000" };
  assert.equal(await claimJobSlot(binding, claim), "DISABLED");
  assert.equal(calls, 0);
  assert.equal(await claimJobSlot(binding, claim, { enabled: true }), "CLAIMED");
  assert.equal(await claimJobSlot(binding, claim, { enabled: true }), "DUPLICATE_OR_CONFLICT");
  assert.equal(await claimJobSlot(binding, { ...claim, runId: "102", checkRunId: "103" }, { enabled: true }), "DUPLICATE_OR_CONFLICT");
  loseResponse = true;
  const next = { ...claim, runId: "104", checkRunId: "105", slotId: "slot:2000" };
  assert.equal(await claimJobSlot(binding, next, { enabled: true }), "REVIEW_REQUIRED");
  loseResponse = false;
  assert.equal(await claimJobSlot(binding, next, { enabled: true }), "DUPLICATE_OR_CONFLICT");
  assert.equal(sql.prepare("SELECT COUNT(*) AS n FROM paper_job_claim_v0_1").get().n, 2);
  const before = calls;
  assert.equal(await claimJobSlot(binding, { ...claim, writerId: "bad';drop" }, { enabled: true }), "INVALID");
  assert.equal(calls, before);
  sql.close();
});

test("D1 claim rejects unknown or repeated attempt metadata", async () => {
  const claim = { repositoryId: "123", runId: "100", attempt: "1", checkRunId: "101", writerId: "paper", slotId: "slot:1000" };
  for (const result of [
    { success: true, meta: { changes: 1 } },
    { success: true, meta: { changes: 1, total_attempts: 2 } },
    { success: true, meta: { changes: 2, total_attempts: 1 } },
    { success: false, meta: { changes: 1, total_attempts: 1 } },
  ]) {
    let calls = 0;
    const db = { prepare: () => ({ bind: () => ({ run: async () => { calls++; return result; } }) }) };
    assert.equal(await claimJobSlot(db, claim, { enabled: true }), "REVIEW_REQUIRED");
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
