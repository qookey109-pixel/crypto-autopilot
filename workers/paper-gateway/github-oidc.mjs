// Prototype only: never connect this verifier to a credential-holding service
// until server-owned policy, key retrieval, replay prevention and budgets are authorized.
function parseUnique(text) {
  let i = 0;
  function ws() { while (/\s/.test(text[i] || "") && i < text.length) i++; }
  function string() {
    if (text[i] !== '"') throw Error("string");
    const start = i++;
    while (i < text.length) {
      if (text[i] === '"') { i++; return JSON.parse(text.slice(start, i)); }
      if (text[i] === "\\") { i += 2; } else { i++; }
    }
    throw Error("unterminated");
  }
  function value(depth) {
    if (depth > 16) throw Error("depth");
    ws();
    if (text[i] === "{") {
      i++; ws(); const seen = new Set();
      if (text[i] === "}") { i++; return; }
      for (;;) {
        ws(); const k = string();
        if (seen.has(k) || seen.size >= 128) throw Error("duplicate");
        seen.add(k); ws();
        if (text[i++] !== ":") throw Error("colon");
        value(depth + 1); ws();
        if (text[i] === "}") { i++; return; }
        if (text[i++] !== ",") throw Error("comma");
      }
    }
    if (text[i] === "[") {
      i++; ws(); if (text[i] === "]") { i++; return; }
      for (;;) {
        value(depth + 1); ws();
        if (text[i] === "]") { i++; return; }
        if (text[i++] !== ",") throw Error("comma");
      }
    }
    if (text[i] === '"') { string(); return; }
    const m = text.slice(i).match(/^(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/);
    if (!m) throw Error("value");
    i += m[0].length;
  }
  value(0); ws(); if (i !== text.length) throw Error("trailing");
  return JSON.parse(text);
}
function decode(part) {
  if (!/^[A-Za-z0-9_-]+$/.test(part) || part.length % 4 === 1) throw Error("base64");
  const raw = atob(part.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - part.length % 4) % 4));
  return Uint8Array.from(raw, c => c.charCodeAt(0));
}
const textDecoder = new TextDecoder("utf-8", { fatal: true });
const positive = x => typeof x === "string" && /^[1-9][0-9]{0,19}$/.test(x);
export async function verifyGithubJob(token, { enabled = false, policy, now, fetchKeys } = {}) {
  if (enabled !== true) return null;
  try {
    if (typeof token !== "string" || token.length > 32768 || !policy ||
        !Number.isSafeInteger(now) || typeof fetchKeys !== "function") return null;
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const header = parseUnique(textDecoder.decode(decode(parts[0])));
    const claims = parseUnique(textDecoder.decode(decode(parts[1])));
    if (!header || !claims || Array.isArray(header) || Array.isArray(claims) ||
        header.alg !== "RS256" || header.typ !== "JWT" ||
        typeof header.kid !== "string" || !/^[A-Za-z0-9_-]{1,128}$/.test(header.kid) ||
        ("x5t" in header && (typeof header.x5t !== "string" || !/^[A-Za-z0-9_-]{1,128}$/.test(header.x5t))) ||
        Object.keys(header).some(k => !["alg", "typ", "kid", "x5t"].includes(k))) return null;
    const pairs = [
      ["iss", "https://token.actions.githubusercontent.com"], ["aud", policy.audience],
      ["sub", policy.subject], ["repository", policy.repository],
      ["repository_id", policy.repositoryId], ["workflow_ref", policy.workflowRef],
      ["workflow_sha", policy.workflowSha], ["sha", policy.sha],
      ["ref", "refs/heads/main"], ["ref_type", "branch"],
      ["runner_environment", "github-hosted"], ["run_attempt", "1"],
    ];
    if (pairs.some(([k, v]) => typeof v !== "string" || !v || claims[k] !== v) ||
        !["schedule", "workflow_dispatch"].includes(claims.event_name) ||
        !positive(claims.run_id) || !positive(claims.check_run_id) ||
        typeof claims.jti !== "string" || !claims.jti || claims.jti.length > 256 ||
        !["iat", "nbf", "exp"].every(k => Number.isSafeInteger(claims[k])) ||
        claims.iat > now + 30 || claims.nbf > now + 30 || claims.exp <= now ||
        claims.exp <= claims.iat || claims.exp - claims.iat > 600) return null;
    const set = await fetchKeys();
    if (!set || !Array.isArray(set.keys) || set.keys.length > 32) return null;
    const keys = set.keys.filter(k => k && k.kid === header.kid);
    if (keys.length !== 1) return null;
    const jwk = keys[0];
    if (jwk.kty !== "RSA" || jwk.alg !== "RS256" || jwk.use !== "sig" ||
        jwk.e !== "AQAB" || typeof jwk.n !== "string" || decode(jwk.n).length < 256 ||
        ["d","p","q","dp","dq","qi","oth"].some(k => k in jwk)) return null;
    const key = await crypto.subtle.importKey("jwk", jwk,
      { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
    const valid = await crypto.subtle.verify("RSASSA-PKCS1-v1_5", key, decode(parts[2]),
      new TextEncoder().encode(parts[0] + "." + parts[1]));
    if (!valid) return null;
    return { runId: claims.run_id, checkRunId: claims.check_run_id, jti: claims.jti };
  } catch { return null; }
}
