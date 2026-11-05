import { test } from "node:test";
import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";
import { verifyGithubJob } from "../../workers/paper-gateway/github-oidc.mjs";

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
  assert.equal(await verifyGithubJob(token, { ...options, fetchKeys: async () => ({ keys: [jwk, jwk] }) }), null);
  assert.equal(await verifyGithubJob(token, { ...options, fetchKeys: async () => { throw Error("offline"); } }), null);
});
