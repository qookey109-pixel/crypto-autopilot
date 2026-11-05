// Prepared only: caller must provide server-owned repository, token and a
// signature-verified identity. No route, production fetch or permission is enabled.
import { parseUnique } from "./github-oidc.mjs";
const id = x => typeof x === "string" && /^[1-9][0-9]{0,15}$/.test(x);
const repoPattern = /^[A-Za-z0-9][A-Za-z0-9-]{0,38}\/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$/;
const MAX_BYTES = 131072;
async function readOne(fetcher, url, token) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 5000);
  let reader;
  try {
    const response = await fetcher(url, {
      method: "GET", redirect: "manual", signal: controller.signal,
      headers: { Authorization: "Bearer " + token, Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28" },
    });
    if (response.status !== 200 || !response.body) return null;
    const length = response.headers.get("content-length");
    if (length !== null && (!/^[0-9]+$/.test(length) || Number(length) > MAX_BYTES)) return null;
    reader = response.body.getReader();
    const chunks = []; let total = 0;
    for (;;) {
      const part = await reader.read();
      if (part.done) break;
      total += part.value.byteLength;
      if (total > MAX_BYTES) return null;
      chunks.push(part.value);
    }
    const bytes = new Uint8Array(total); let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
    const result = parseUnique(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
    return result && typeof result === "object" && !Array.isArray(result) ? result : null;
  } catch { return null; }
  finally {
    clearTimeout(timer);
    if (reader) { try { await reader.cancel(); } catch {} }
  }
}
export async function readJobMetadata({ enabled = false, repository, identity, token, fetcher = fetch } = {}) {
  if (enabled !== true) return null;
  if (typeof repository !== "string" || !repoPattern.test(repository) ||
      !identity || !id(identity.runId) || !id(identity.checkRunId) ||
      typeof token !== "string" || !/^[A-Za-z0-9_\-]{1,512}$/.test(token) ||
      typeof fetcher !== "function") return null;
  const base = "https://api.github.com/repos/" + repository + "/actions/";
  const run = await readOne(fetcher, base + "runs/" + identity.runId, token);
  if (!run) return null;
  const job = await readOne(fetcher, base + "jobs/" + identity.checkRunId, token);
  return job ? { run, job } : null;
}
