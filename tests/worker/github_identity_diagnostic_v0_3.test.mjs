import { test } from "node:test";
import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";
import { runDiagnostic } from "../../scripts/oidc/github_identity_diagnostic_v0_3.mjs";
globalThis.crypto ??= webcrypto;

const repo = "qookey109-pixel/crypto-autopilot";
const path = ".github/workflows/cloud-paper-github-identity-diagnostic-v0-3.yml";
const now = Date.parse("2026-11-10T02:00:00Z");
const sha = "a".repeat(40);
const env = { GITHUB_RUN_ID: "100", GITHUB_REPOSITORY_ID: "123", GITHUB_SHA: sha,
  GITHUB_EVENT_NAME: "workflow_dispatch", GITHUB_REF: "refs/heads/main", GITHUB_REPOSITORY: repo,
  GITHUB_RUN_ATTEMPT: "1", CONFIRM_DIAGNOSTIC: "true", GITHUB_TOKEN: "ghs_fixture." + "x".repeat(700) + ".signature",
  ACTIONS_ID_TOKEN_REQUEST_TOKEN: "fixture-request-token",
  ACTIONS_ID_TOKEN_REQUEST_URL: "https://pipelines.actions.githubusercontent.com/fixture" };

test("disabled or incorrect context performs no network operations", async () => {
  let calls = 0;
  const fetcher = async () => { calls++; throw Error("unexpected"); };
  assert.equal((await runDiagnostic({ env, fetcher })).status, "DISABLED");
  for (const change of [{ GITHUB_REF: "refs/heads/other" }, { GITHUB_RUN_ATTEMPT: "2" },
    { CONFIRM_DIAGNOSTIC: "false" }, { ACTIONS_ID_TOKEN_REQUEST_URL: "https://attacker.example/fixture" }])
    assert.equal((await runDiagnostic({ enabled: true, env: { ...env, ...change }, fetcher })).status,
      "BLOCKED_CONTEXT");
  assert.equal(calls, 0);
});

test("context failure returns only fixed field names, never values", async () => {
  const privateValue = "sensitive token value / +";
  const result = await runDiagnostic({ enabled: true, env: { ...env,
    ACTIONS_ID_TOKEN_REQUEST_TOKEN: privateValue }, fetcher: async () => { throw Error("unexpected"); } });
  assert.deepEqual(result, { status: "BLOCKED_CONTEXT", failed: ["oidc_request_token"] });
  assert.equal(JSON.stringify(result).includes(privateValue), false);
});

test("header-injection and oversized tokens stop before a request", async () => {
  let calls = 0;
  const fetcher = async () => { calls++; throw Error("unexpected"); };
  for (const token of ["", "bad\r\nInjected: value", "x".repeat(8193)]) {
    const report = await runDiagnostic({ enabled: true, env: { ...env, GITHUB_TOKEN: token }, fetcher });
    assert.equal(report.status, "BLOCKED_CONTEXT");
    assert.ok(report.failed.includes("github_token"));
  }
  assert.equal(calls, 0);
});

test("history rejection happens before requesting an identity token", async () => {
  let calls = 0;
  const fetcher = async url => {
    calls++; assert.match(url, /actions\/workflows\//);
    return new Response(JSON.stringify({ total_count: 2, workflow_runs: [] }));
  };
  assert.equal((await runDiagnostic({ enabled: true, env, fetcher, clock: () => now })).status, "BLOCKED_HISTORY");
  assert.equal(calls, 1);
});

test("signed job and metadata must correlate on current main", async () => {
  const pair = await crypto.subtle.generateKey(
    { name: "RSASSA-PKCS1-v1_5", modulusLength: 2048, publicExponent: new Uint8Array([1,0,1]), hash: "SHA-256" },
    true, ["sign", "verify"]);
  const jwk = { ...await crypto.subtle.exportKey("jwk", pair.publicKey), kid: "fixture", alg: "RS256", use: "sig" };
  const claims = { iss: "https://token.actions.githubusercontent.com",
    aud: "qookey-cloud-paper-github-identity-diagnostic-v0-3", sub: "repo:" + repo + ":ref:refs/heads/main",
    repository: repo, repository_id: "123", workflow_ref: repo + "/" + path + "@refs/heads/main",
    workflow_sha: sha, sha, ref: "refs/heads/main", ref_type: "branch", runner_environment: "github-hosted",
    event_name: "workflow_dispatch", run_id: "100", run_attempt: "1", check_run_id: "101",
    iat: now / 1000 - 10, nbf: now / 1000 - 10, exp: now / 1000 + 300, jti: "fixture" };
  const enc = x => Buffer.from(JSON.stringify(x)).toString("base64url");
  const data = enc({ alg: "RS256", typ: "JWT", kid: "fixture" }) + "." + enc(claims);
  const sig = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", pair.privateKey, new TextEncoder().encode(data));
  const jwt = data + "." + Buffer.from(sig).toString("base64url");
  const row = { id: 100, workflow_id: 456, path, head_sha: sha, head_branch: "main", run_attempt: 1,
    status: "in_progress", event: "workflow_dispatch", created_at: "2026-11-10T01:59:00Z",
    repository: { id: 123 } };
  const job = { id: 101, run_id: 100, head_sha: sha, name: "diagnostic", status: "in_progress",
    started_at: "2026-11-10T01:59:10Z", completed_at: null };
  const calls = [];
  let badMain = false;
  const fetcher = async url => {
    calls.push(url);
    if (url.includes("/actions/workflows/")) return new Response(JSON.stringify({ total_count: 1, workflow_runs: [row] }));
    if (url.startsWith("https://pipelines.actions.githubusercontent.com/")) return new Response(JSON.stringify({ value: jwt }));
    if (url === "https://token.actions.githubusercontent.com/.well-known/jwks") return new Response(JSON.stringify({ keys: [jwk] }));
    if (url.endsWith("/actions/runs/100")) return new Response(JSON.stringify(row));
    if (url.endsWith("/actions/jobs/101")) return new Response(JSON.stringify(job));
    if (url.endsWith("/branches/main")) return new Response(JSON.stringify({ commit: { sha: badMain ? "b".repeat(40) : sha } }));
    throw Error("unexpected");
  };
  const options = { enabled: true, env, fetcher, clock: () => now };
  assert.deepEqual(await runDiagnostic(options), { status: "IDENTITY_CORRELATION_OBSERVED" });
  assert.equal(calls.length, 6);
  badMain = true;
  assert.deepEqual(await runDiagnostic(options), { status: "REVIEW_REQUIRED", stage: "metadata_or_clock" });
});
