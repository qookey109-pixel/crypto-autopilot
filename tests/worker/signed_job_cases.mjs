import { verifyGithubJob } from "../../workers/paper-gateway/github-oidc.mjs";

function base64url(bytes) {
  return btoa(String.fromCharCode(...new Uint8Array(bytes)))
    .replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
}

function equal(actual, expected) {
  if (actual !== expected) throw new Error("Unexpected signed job verification result");
}

export default {
  async test() {
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
      subject: "repo:owner@77/repo@123:ref:refs/heads/main",
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
    const encode = (value) => base64url(new TextEncoder().encode(JSON.stringify(value)));
    const header = encode({ alg: "RS256", typ: "JWT", kid: "fixture", x5t: "fixture-thumbprint" });
    const payload = encode(claims);
    const input = header + "." + payload;
    const signature = base64url(await crypto.subtle.sign(
      "RSASSA-PKCS1-v1_5", key.privateKey, new TextEncoder().encode(input),
    ));
    const token = input + "." + signature;
    const options = { enabled: true, policy, now: 1100, fetchKeys: async () => ({ keys: [jwk] }) };
    const accepted = await verifyGithubJob(token, options);
    equal(accepted?.runId, "100");
    equal(accepted?.runAttempt, "1");
    equal(accepted?.checkRunId, "101");
    equal(accepted?.eventName, "schedule");
    equal(accepted?.repositoryId, "123");
    equal(await verifyGithubJob(token, { ...options, policy: { ...policy, repositoryId: "999" } }), null);
    equal(await verifyGithubJob(header + "." + encode({ ...claims, run_id: "102" }) + "." + signature, options), null);
    equal(await verifyGithubJob(token, { ...options, now: 1400 }), null);
    const sign = async (h, p) => {
      const data = h + "." + p;
      const signed = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", key.privateKey, new TextEncoder().encode(data));
      return data + "." + base64url(signed);
    };
    const impossibleInterval = encode({ ...claims, nbf: 1105, exp: 1103 });
    equal(await verifyGithubJob(await sign(header, impossibleInterval), options), null);
    const duplicate = base64url(new TextEncoder().encode(JSON.stringify(claims).replace('"run_id":"100"', '"run_id":"100","run_id":"100"')));
    equal(await verifyGithubJob(await sign(header, duplicate), options), null);
    const forbidden = encode({ alg: "RS256", typ: "JWT", kid: "fixture", jku: "https://attacker.example/keys" });
    equal(await verifyGithubJob(await sign(forbidden, payload), options), null);
    const escapedDuplicate = base64url(new TextEncoder().encode(JSON.stringify(claims).replace('"run_id":"100"', '"run_id":"100","run\\u005fid":"100"')));
    equal(await verifyGithubJob(await sign(header, escapedDuplicate), options), null);
    equal(await verifyGithubJob(token, { ...options, fetchKeys: async () => ({ keys: [jwk, jwk] }) }), null);
    equal(await verifyGithubJob(token, { ...options, fetchKeys: async () => ({ keys: [{ ...jwk, n: "AQ" }] }) }), null);
    equal((await verifyGithubJob(token, { ...options, fetchKeys: async () => ({ keys: [{ ...jwk, x5c: ["fixture"] }] }) }))?.runId, "100");
    equal(await verifyGithubJob(token, { ...options, fetchKeys: async () => { throw Error("offline"); } }), null);
  },
};
